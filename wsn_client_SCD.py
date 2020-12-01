"""
client application for edge computing device
coded functions as below
- BLE sensor device; BOSCH SCD 110 scan & connect using bluepy.btle
- server connect using asyncio
- getting server message and run routine upon the message
- setting sensor mode configuration
- start or stop sensor running called STE; Short Time Experiment
- getting sensor STE data
- getting sensor memory data using BDT; Block Data Transfer

by Inho Byun, Researcher/KAIST
   inho.byun@gmail.com
                    started 2020-11-05
                    last updated 2020-12-01
"""
import asyncio
from bluepy.btle import Scanner, DefaultDelegate, UUID, Peripheral
import datetime
import socket
import struct
import sys
import time

#############################################
# target definitions to interface BOSCH SCD
#############################################
#
# target device identifiers
#
TARGET_MANUFA_UUID = "a6022158" # AD Type Value: 0xFF
TARGET_DEVICE_NAME = "SCD-"     # AD Type Value: 0x09
#############################################
# Services of BOSCH SCD
#############################################
#
# service handle
#
SCD_DEVICE_NAME_HND   = 3     # R,  uuid: 00002a00-0000-1000-8000-00805f9b34fb
SCD_SYSTEM_ID_HND     = 11    # R,  uuid: 00002a23-0000-1000-8000-00805f9b34fb
SCD_SERIAL_NUM_HND    = 13    # R,  uuid: 00002a25-0000-1000-8000-00805f9b34fb
SCD_FW_REVISION_HND   = 15    # R,  uuid: 00002a26-0000-1000-8000-00805f9b34fb
SCD_HW_REVISION_HND   = 17    # R,  uuid: 00002a27-0000-1000-8000-00805f9b34fb
SCD_SW_REVISION_HND   = 19    # R,  uuid: 00002a28-0000-1000-8000-00805f9b34fb
SCD_MANUFA_NAME_HND   = 21    # R,  uuid: 00002a29-0000-1000-8000-00805f9b34fb
SCD_IF_VERSION_HND    = 24    # R,  uuid: 02a65821-0001-1000-2000-b05cb05cb05c
SCD_TEST_RESULT_HND   = 26    # R,  uuid: 02a65821-0002-1000-2000-b05cb05cb05c
SCD_SET_MODE_HND      = 28    # RW, uuid: 02a65821-0003-1000-2000-b05cb05cb05c
SCD_SET_GEN_CMD_HND   = 30    # RW, uuid: 02a65821-0004-1000-2000-b05cb05cb05c
SCD_STE_CONFIG_HND    = 35    # RW, uuid: 02a65821-1001-1000-2000-b05cb05cb05c
SCD_STE_RESULT_HND    = 37    # RN, uuid: 02a65821-1002-1000-2000-b05cb05cb05c
SCD_BDT_CONTROL_HND   = 41    # W,  uuid: 02a65821-3001-1000-2000-b05cb05cb05c
SCD_BDT_STATUS_HND    = 43    # R,  uuid: 02a65821-3002-1000-2000-b05cb05cb05c
SCD_BDT_DATA_FLOW_HND = 45    # RN, uuid: 02a65821-3003-1000-2000-b05cb05cb05c
#
# MAX constant of BOSCH SCD
#
SCD_MAX_MTU     = 65                # MAX SCD Comm. Packet size
SCD_MAX_FLASH   = 0x0b0000          # 11*16**4 = 720896 = 704K

#
# Some constant parameters
#
SCAN_TIME       = 8.    # scanning duration for BLE devices 
STE_RUN_TIME    = 3.    # STE rolling time in secconds for SENSOR data recording
STE_FREQUENCY   = (400, 800, 1600, 3200, 6400)  # of STE result 400 / 800 / 1600 / 3200 / 6400 Hz
#
# global variables
#
gTargetDevice   = None  # target device object 
gScannedCount   = 0     # count of scanned BLE devices
# STE - Short Time Experiment
gSTEcfgMode     = bytes(35)  # Sensor Mode
gSTEnotiCnt     = 0     # count of notifications from connected device
gSTEstartTime   = 0.    # notification start timestamp
gSTElastTime    = 0.    # last notification timestamp
gSTElastData    = None    # last notification data
gSTEisDataSent  = False # flag wether notification data has been sent
gSTEisRolling   = False # flag wether STE is on rolling
# BDT - Block Data Transfer
gBDTnotiCnt     = 0
gBDTstartTime   = 0.   
gBDTlastTime    = 0.
gBDTdata        = bytearray(SCD_MAX_FLASH)
gBDTcrc32       = bytearray(4)
gBDTisRolling   = False
# IDLE
gIDLElastTime   = 0.    # last BLE traffic on connection
gIDLEinterval   = 60.   # time interval to make BLE traffic to keep connection


#############################################
# target definitions to TCP Server
#############################################
#
# target TCP Server identifiers
#
##TCP_HOST_NAME   = "127.0.0.1"       # TEST Host Name
##TCP_HOST_NAME   = "10.2.2.3"        # TEST Host Name
##TCP_HOST_NAME   = "192.168.0.3"     # TEST Host Name
TCP_HOST_NAME   = "125.131.73.31"   # Default Host Name
TCP_PORT        = 8088              # Default TCP Port Name
##TCP_TX_INTERVAL     = 1.            # time interval to send notification to host      
TCP_DEV_READY_MSG   = 'DEV_READY'
TCP_DEV_CLOSE_MSG   = 'DEV_CLOSE'
TCP_STE_START_MSG   = 'STE_START'
TCP_STE_STOP_MSG    = 'STE_STOP'
TCP_STE_REQ_MSG     = 'STE_REQ'
TCP_BDT_START_MSG   = 'BDT_START'
TCP_BDT_REQ_MSG     = 'BDT_REQ'
#
# global variables
#
gTCPrxMsg           = None

#############################################
# handle to receive command message
#############################################
#
async def tcp_RX_message(tx_msg, loop):
    global TCP_HOST_NAME
    global TCP_PORT
    global gTCPrxMsg

    reader, writer = await asyncio.open_connection(TCP_HOST_NAME, TCP_PORT)

    print('\n>>>>>\nAIO C-> receive command...')

    if tx_msg != None:
        print('AIO C-> [TX] try...')
        writer.write(tx_msg.encode())
        await writer.drain()
        print('AIO C-> [TX] "%r" sent' % tx_msg)
    print('AIO C-> [RX] try...')
    rx_data = None
    try:
        rx_data = await asyncio.wait_for ( reader.read(512), timeout=300.0 )
    except asyncio.TimeoutError:
        pass 
    if rx_data != None:
        gTCPrxMsg = rx_data.decode()
        print('AIO C-> [RX] "%r"' % gTCPrxMsg)

    print('AIO C-> close the socket\n<<<<<')
    writer.close()

#############################################
# handle to send data
#############################################
#
async def tcp_TX_data(tx_msg, loop):
    global TCP_HOST_NAME
    global TCP_PORT
    global TCP_STE_REQ_MSG
    global gTCPrxMsg

    reader, writer = await asyncio.open_connection(TCP_HOST_NAME, TCP_PORT)

    print('\n>>>>>\nAIO C-> send data...')

    print('AIO C-> [RX] try...')
    rx_msg = None
    try:
        rx_data = await asyncio.wait_for ( reader.read(512), timeout=1.0 )
    except asyncio.TimeoutError:
        print('AIO C-> [RX] no data')
        pass
    else:
        rx_msg = rx_data.decode()
        print('AIO C-> [RX] "%r"' % rx_msg)

    if tx_msg == None:
        tx_msg = input('AIO C-> input data to server: ')
    print('AIO C-> [tx] try...')
    tx_data = tx_msg.encode()
    writer.write(tx_data)
    await writer.drain()        
    print('AIO C-> [tx] "%r" sent' % tx_msg)

    print('AIO C-> close the socket\n<<<<<')
    writer.close()

#############################################
# functions definition
#############################################
# STE(Short Time Experiment) mode configuration (35 bytes) 
#
def SCD_set_STE_config( p, is_writing = False ):
    global gSTEcfgMode

    if p == None:
        return

    STE_mode = bytearray(35)
    #
    time_bytes = struct.pack('<l', int(time.time()))
    STE_mode[ 0: 4]  = bytes( time_bytes[0:4] )  # [ 0~ 3] Unix time
    #
    mode  = 0xf0
    mode |= 0x01 # 01 sensor En/Disable - accelerometer
    mode |= 0x02 # 02 sensor En/Disable - magnetometer
    mode |= 0x04 # 04 sensor En/Disable - light
    mode |= 0x08 # 08 sensor En/Disable - temperature
    STE_mode[ 4: 5] = bytes(struct.pack('<h',mode))
    #
    mode  = 0x00 # ?0 data rate - accelerometer ODR 400Hz
    #ode  = 0x01 # ?1 data rate - accelerometer ODR 800Hz
    #ode  = 0x02 # ?2 data rate - accelerometer ODR 1600Hz
    #ode  = 0x03 # ?3 data rate - accelerometer ODR 3200Hz
    #ode  = 0x04 # ?4 data rate - accelerometer ODR 6400Hz
    #ode |= 0x00 # 0? data rate - light sensor ODR 100ms(10Hz)
    #ode |= 0x10 # 1? data rate - light sensor ODR 800ms(1.25Hz)
    STE_mode[ 5: 6] = bytes(struct.pack('<h',mode))
    #
    STE_mode[ 6: 8]  = b'\xE4\x07'          # [ 6~ 7] accelerometer threshold
    STE_mode[12:16]  = b'\x00\x00\x00\x00'  # [12~15] light sensor threshold low
    STE_mode[16:20]  = b'\xE8\xE4\xF5\x05'  # [16~19] light sensor threshold high
    STE_mode[20:22]  = b'\x80\x57'          # [20~21] magnetometer threshold
    STE_mode[26:28]  = b'\x80\xF3'          # [26~27] temperature threshold low
    STE_mode[28:30]  = b'\x00\x2D'          # [28~29] temperature threshold high
    #
    #ode  = 0xf0 # F0 sensor raw value to flash - nothing
    #ode |= 0x01 # 01 sensor raw value to flash - accelerometer
    #ode |= 0x02 # 02 sensor raw value to flash - magnetometer
    #ode |= 0x04 # 04 sensor raw value to flash - light
    #ode |= 0x08 # 08 sensor raw value to flash - temperature
    mode = 0xf0 if (not is_writing) else 0xf1
    STE_mode[30:31] = bytes(struct.pack('<h',mode))
    #
    gSTEcfgMode = bytes(STE_mode[0:35])
    #
    p.writeCharacteristic( SCD_STE_CONFIG_HND, gSTEcfgMode )
    time.sleep(.3)
    ret_val = p.readCharacteristic( SCD_STE_CONFIG_HND )
    print ("\tSCD: STE config. get\n[%s](%d)" % (hex_str(ret_val), len(ret_val)))
    return

#############################################
# check wether STE is rolling or not 
#
def SCD_is_STE_rolling( p ):
    global SCD_STE_RESULT_HND
    global gSTEisRolling

    STE_result_0 = p.readCharacteristic( SCD_STE_RESULT_HND )
    time.sleep(.5)
    STE_result_1 = p.readCharacteristic( SCD_STE_RESULT_HND )
    print ("\tSCD: Checking rolling counter [%d] [%d]" % (int(STE_result_0[32]), int(STE_result_1[32])) )
    if STE_result_0[32] != STE_result_1[32] :
        gSTEisRolling = True
    else:
        gSTEisRolling = False    
    return gSTEisRolling      

#############################################
# toggle STE start or stop 
#
def SCD_toggle_STE_rolling( p, will_start = False, will_notify = False ):
    global SCD_SET_MODE_HND
    global SCD_SET_GEN_CMD_HND
    global SCD_STE_RESULT_HND
    global gSTEisRolling

    if p == None:
        return

    if will_start:
        if not gSTEisRolling:
            if will_notify:
                p.writeCharacteristic( SCD_STE_RESULT_HND+1, struct.pack('<H', 1) )
                time.sleep(0.7)
            p.writeCharacteristic( SCD_SET_MODE_HND, b'\x00' )    
            p.writeCharacteristic( SCD_SET_GEN_CMD_HND, b'\x20' )
            print ("\tSCD: STE is starting")        
            gSTEisRolling = True
    else:
        if gSTEisRolling:
            p.writeCharacteristic( SCD_SET_GEN_CMD_HND, b'\x20' )
            print ("\tSCD: STE is stopping")        
            ret_val = p.readCharacteristic( SCD_SET_GEN_CMD_HND )
            while ( ret_val != b'\x00' ):
                print ("\t\t=> STE has not completed yet, generic command is [%s]" % ret_val.hex())
                time.sleep(0.7)
                ret_val = p.readCharacteristic( SCD_SET_GEN_CMD_HND )
            print ("\tSCD: STE stoped")
            gSTEisRolling = False
        ret_val = p.readCharacteristic( SCD_SET_MODE_HND )
        while ret_val !=  b'\x00':
            print("\tSCD: set STE mode")
            p.writeCharacteristic( SCD_SET_MODE_HND, b'\x00' )
            ret_val = p.readCharacteristic( SCD_SET_MODE_HND )    
    return        

#############################################
# convert hex() string to format like "hh.hh.hh"
#
def hex_str( vBytes ):
    
    vString = ''.join(['.' + ch if i % 2 == 0 and i != 0 else ch for i, ch in enumerate(vBytes.hex())])
    return vString

#############################################
# output STE data to string
#
def SCD_string_STE_data( pResult ):

    # output Accelerrometer X, Y, Z axis arithmetic mean & variation  
    adxl_mean_x = float( int.from_bytes(pResult[ 0: 2], byteorder='little', signed=True) ) / 10.0
    adxl_mean_y = float( int.from_bytes(pResult[ 2: 4], byteorder='little', signed=True) ) / 10.0
    adxl_mean_z = float( int.from_bytes(pResult[ 4: 6], byteorder='little', signed=True) ) / 10.0
    adxl_vari_x = float( int.from_bytes(pResult[ 6:10], byteorder='little', signed=True) ) / 100.0
    adxl_vari_y = float( int.from_bytes(pResult[10:14], byteorder='little', signed=True) ) / 100.0
    adxl_vari_z = float( int.from_bytes(pResult[14:18], byteorder='little', signed=True) ) / 100.0
    # output temperature
    temperature = float( int.from_bytes(pResult[18:20], byteorder='little', signed=True) ) * 0.0078
    # output light
    light = float( int.from_bytes(pResult[20:24], byteorder='little', signed=True) ) / 1000.0
    # output Magnetometer X, Y, Z axis raw data 
    magneto_x = float( int.from_bytes(pResult[24:26], byteorder='little', signed=True) ) / 16.0
    magneto_y = float( int.from_bytes(pResult[26:28], byteorder='little', signed=True) ) / 16.0
    magneto_z = float( int.from_bytes(pResult[28:30], byteorder='little', signed=True) ) / 16.0
    # make string to send
    str = "(%.1f," % adxl_mean_x
    str += "%.2f," % adxl_vari_x
    str += "%.1f," % adxl_mean_y
    str += "%.2f," % adxl_vari_y
    str += "%.1f," % adxl_mean_z
    str += "%.2f," % adxl_vari_z
    str += "%.2f," % temperature
    str += "%.3f," % light
    str += "%.1f," % magneto_x
    str += "%.1f," % magneto_y
    str += "%.1f)" % magneto_z   
    return str

#############################################    
# print STE result
#
def SCD_print_STE_result():
    global gSTEcfgMode
    global gSTEnotiCnt
    global gSTEstartTime
    global gSTElastTime

    # output time stamp
    tm = float( (struct.unpack('<l', gSTEcfgMode[0:4]))[0] )   
    print ( "\tSCD: STE config. time   : %s(%.3f)" \
            % (datetime.datetime.fromtimestamp(tm).strftime('%Y-%m-%d %H:%M:%S'), tm) )
    print ( "\tSCD: Notification Start : %s(%.3f)" \
            % (datetime.datetime.fromtimestamp(gSTEstartTime).strftime('%Y-%m-%d %H:%M:%S'), gSTEstartTime) )
    print ( "\tSCD: Notification End   : %s(%.3f)" \
            % (datetime.datetime.fromtimestamp(gSTElastTime).strftime('%Y-%m-%d %H:%M:%S'), gSTElastTime) )      
    print ( "\tSCD: Notification Count : %d" % gSTEnotiCnt)
    return

#############################################
# Define scan callback
#############################################
class ScanDelegate(DefaultDelegate):
    
    def __init__(self):
        global gScannedCount

        DefaultDelegate.__init__(self)
        gScannedCount = 0
        print("+*** scan handler is configured", end='\n', flush = True)

    def handleDiscovery(self, dev, isNewDev, isNewData):
        global gScannedCount

        if isNewDev:
            gScannedCount += 1
            print ('+*** >' if gScannedCount==1 else '>', end='', flush = True)
        elif isNewData:
            print ('+*** +' if gScannedCount==0 else '+', end='', flush = True)            

#############################################
# Define notification callback
#############################################
class NotifyDelegate(DefaultDelegate):
    
    def __init__(self, params):
        global gSTEnotiCnt

        DefaultDelegate.__init__(self)
        gSTEnotiCnt = 0
        print("+*** device notification handler is configured", end='\n', flush = True)
      
    def handleNotification(self, cHandle, data):
        global SCD_STE_RESULT_HND
        global SCD_BDT_DATA_FLOW_HND
        global gSTEnotiCnt
        global gSTEstartTime
        global gSTElastTime
        global gSTElastData
        global gBDTnotiCnt
        global gBDTstartTime
        global gBDTlastTime
        global gBDTdata
        global gBDTcrc32

        if cHandle == SCD_STE_RESULT_HND:
            # STE notification
            if gSTEnotiCnt == 0:
                gSTElastTime  = gSTEstartTime = time.time()
            else:
                gSTElastTime = time.time()
            gSTEnotiCnt += 1
            gSTElastData = data
            
        elif cHandle == SCD_BDT_DATA_FLOW_HND:
            # BDT notification
            packet_no = int.from_bytes(data[0:4], byteorder='little', signed=False)
            if packet_no == 0:
                gBDTlastTime = gBDTstartTime = time.time()
                # header packet
                gBDTnotiCnt = int.from_bytes(data[4:8], byteorder='little', signed=False)
                gBDTdata[0:16] = data[4:20]
            elif packet_no < gBDTnotiCnt-1:    
                # data packet
                idx = packet_no * 16
                gBDTdata[idx:idx+16] = data[4:20]
            elif packet_no == gBDTnotiCnt-1:
                gBDTlastTime = time.time()
                # footer packet
                gBDTcrc32 = data[4:8]
                idx = packet_no * 16
                gBDTdata[idx:idx+16] = data[4:20]
            else:
                print("+*** BDT Packet No Error !... [%d] should less than [%d]" % (packet_no, gBDTnotiCnt), end='\n', flush = True)            
        else:
            print("+*** %2d-#%3d-[%s]" % (cHandle, gSTEnotiCnt, hex_str(data)), end='\n', flush = True)

#############################################
# Define Scan_and_connect
#
# should implement "BTLEDisconnectError" exception
#
#############################################
def SCD_scan_and_connect( is_first = True ):
    global SCAN_TIME
    global TARGET_MANUFA_UUID
    global TARGET_DEVICE_NAME
    global gTargetDevice
    ##global gSocketClient
    #
    # scanning for a while
    #
    scanner = Scanner().withDelegate(ScanDelegate())
    print ("\tSCD: BLE device scan %sstarted..." % ('re' if not is_first else '') )
    devices = scanner.scan(SCAN_TIME)
    print ("\n\tSCD: BLE device scan completed... [%d] devices are scanned" % gScannedCount)
    #
    # check to match BOSCH SCD device identifiers
    #
    for dev in devices:
        matching_count = 0
        for (adtype, desc, value) in dev.getScanData():
            if adtype == 255 and TARGET_MANUFA_UUID in value:
                matching_count += 1
                print("\t\t=> found target (AD Type=%d) '%s' is '%s'" % (adtype, desc, value))            
            if adtype == 9 and TARGET_DEVICE_NAME in value:
                matching_count += 1
                print("\t\t=> found target (AD Type=%d) '%s' is '%s'" % (adtype, desc, value))            
            if matching_count >= 2:
                print("\t\t=> found BOSCH SCD device!")
                print("\tSCD: device address [%s], type=[%s], RSSI=[%d]dB" % (dev.addr, dev.addrType, dev.rssi))
                gTargetDevice = dev
                break
        if gTargetDevice != None:
            break
    #
    # if none found then exiting    
    #
    if gTargetDevice == None:
        print("\tSCD: no matching device found... Exiting...")
        ##gSocketClient.close()
        sys.exit(1)
    #
    # connect
    #
    print("\tSCD: connecting [%s], type=[%s]" % (gTargetDevice.addr, gTargetDevice.addrType))
    p = None
    retry = 0
    while p == None:
        try:
            p = Peripheral(gTargetDevice.addr, gTargetDevice.addrType)
        except:
            print("\t\t=> BLE device connection error occured... retry after 3 sec...")
            retry += 1
            if retry > 3:
                print("\t\t=> BLE device connection error occured... exiting...")
                ##gSocketClient.close()
                sys.exit(-1)
            time.sleep(3)    
    #
    # should increase MTU
    #           
    p.setMTU(SCD_MAX_MTU)
    return p

#############################################
# clear memory 
#
def SCD_clear_memory( p ):
    global SCD_MAX_FLASH
    global SCD_STE_CONFIG_HND
    global SCD_SET_GEN_CMD_HND

    ret_val = p.readCharacteristic( SCD_STE_CONFIG_HND )
    print ("\tSCD: Flash memory remain is [%s] MAX:0b0000" % ret_val[31:34].hex())
    if (struct.unpack('i', ret_val[31:35]))[0] < SCD_MAX_FLASH:  
        print ("\t\t=> flash memory is not empty...cleanning-up flash memory")
        print ("\tSCD: Erase flash wait for seconds...")
        p.writeCharacteristic( SCD_SET_GEN_CMD_HND, b'\x30' ) # erase sensor data
        p.disconnect()
        time.sleep(10.)
        p = None
    return p    

#############################################
#############################################
#         
# Main starts here
#
if len(sys.argv) > 1:
    print ("+--- take 1'st argument as Host IP address (default: '%s')" % TCP_HOST_NAME)
    TCP_HOST_NAME = sys.argv[1]
if len(sys.argv) > 2:
    print ("+--- take 2'nd argument as port# (default: '%d')" % TCP_PORT)
    TCP_PORT = int(sys.argv[2])

#############################################
#
# scan and connect SCD
#
p = SCD_scan_and_connect(True)
#
# set STE configuration
#
SCD_set_STE_config (p,False)
#
# read Device Info. such as Name, Manufacurer Name, etc.
#
ret_val = p.readCharacteristic( SCD_DEVICE_NAME_HND )
print ("\tSCD: Device Name is [%s]" % ret_val.decode("utf-8"))
#
ret_val = p.readCharacteristic( SCD_SYSTEM_ID_HND )
print ("\tSCD: System ID is [%s][%s]" % (hex_str(ret_val[0:3]), hex_str(ret_val[3:8])))
#
ret_val = p.readCharacteristic( SCD_SERIAL_NUM_HND )
print ("\tSCD: Serial # is [%s]" % ret_val.decode("utf-8"))
#
ret_val = p.readCharacteristic( SCD_FW_REVISION_HND )
print ("\tSCD: Revision is FW [%s]," % ret_val.decode("utf-8"), end = '')
#
ret_val = p.readCharacteristic( SCD_HW_REVISION_HND )
print ("HW [%s]," % ret_val.decode("utf-8"), end = '')
#
ret_val = p.readCharacteristic( SCD_SW_REVISION_HND )
print ("SW [%s]" % ret_val.decode("utf-8"))
#
ret_val = p.readCharacteristic( SCD_MANUFA_NAME_HND )
print ("\tSCD: Manufacturer Name is [%s]" % ret_val.decode("utf-8"))
#
ret_val = p.readCharacteristic( SCD_IF_VERSION_HND )
print ("\tSCD: IF Version is [%s]" % hex_str(ret_val))
#
ret_val = p.readCharacteristic( SCD_TEST_RESULT_HND )
print ("\tSCD: Self Test Result is [%s] c0:OK, otherwise not OK!" % ret_val.hex())
#
ret_val = p.readCharacteristic( SCD_SET_MODE_HND )
print ("\tSCD: Mode is [%s] 00:STE, ff:Mode Selection" % ret_val.hex())
#
# check STE is rolling or not, memory is empty or not; stop rolling & cleanup memory
#
SCD_is_STE_rolling(p)
SCD_toggle_STE_rolling(p, False, False)
if  SCD_clear_memory(p) == None:
    p = SCD_scan_and_connect(False)
#

#############################################
#
# loop if not TCP_DEV_CLOSE_MSG 
#
gIDLElastTime = time.time()
loop = asyncio.get_event_loop()
while gTCPrxMsg != TCP_DEV_CLOSE_MSG:
#
#############################################
    #
    # wait any message from server
    #
    gTCPrxMsg = None
    loop.run_until_complete(tcp_RX_message(TCP_DEV_READY_MSG, loop))
    if gTCPrxMsg != None:
        #
        # get & process server message
        #
        if gTCPrxMsg == TCP_STE_START_MSG:
            # start STE rolling w/o memory writing
            print ("+--- Start STE...")
            p.setDelegate( NotifyDelegate(p) )
            SCD_set_STE_config(p, False)
            SCD_toggle_STE_rolling(p, True, False)
        elif gTCPrxMsg == TCP_STE_REQ_MSG:
            # request STE data
            print ("+--- Request STE data...")
            gSTEisDataSent = False
            # if not enable STE notification
            gSTElastData = p.readCharacteristic(SCD_STE_RESULT_HND)
            tx_data = SCD_string_STE_data(gSTElastData)
            loop.run_until_complete(tcp_TX_data(tx_data, loop))           
        elif gTCPrxMsg == TCP_BDT_START_MSG:
            #################################
            # will be threading
            #################################
            gBDTisRolling = True
            # start STE w/ memory writing
            print ("+--- Recording STE starting...")
            p.setDelegate( NotifyDelegate(p) )
            SCD_set_STE_config(p, True)
            SCD_toggle_STE_rolling(p, True, True)
            # take rolling time ( added more overhead time)
            tm = time.time()
            while time.time() - tm <= STE_RUN_TIME:
                wait_flag = p.waitForNotifications(1.)
            # stop STE
            SCD_toggle_STE_rolling(p, False, False) 
            SCD_print_STE_result()            
            # start BDT
            print ("+--- Bulk Data Transfer after a while")
            time.sleep(0.7)
            p.setDelegate( NotifyDelegate(p) )
            print ("+--- BDT Starting...")
            time.sleep(0.7)
            p.writeCharacteristic( SCD_BDT_DATA_FLOW_HND+1, struct.pack('<H', 1) )
            time.sleep(0.7)
            p.writeCharacteristic( SCD_BDT_CONTROL_HND, b'\x01' )
            ret_val = b'x01'
            while ret_val == b'x01':  
                wait_flag = p.waitForNotifications(5.)
                if wait_flag :
                    continue
                ret_val = p.readCharacteristic( SCD_BDT_STATUS_HND )
            time.sleep(0.7)
            print ("\n+--- Bulk Data Transfer completed...status is [%s], time [%.3f], count [%d]" % \
                    (ret_val.hex(), (gBDTlastTime-gBDTstartTime), gBDTnotiCnt) )
            #################################
            gBDTisRolling = False
            gIDLElastTime = time.time()        
            #################################
            # will be threaded
            #################################
        elif gTCPrxMsg == TCP_STE_STOP_MSG or gTCPrxMsg == TCP_DEV_CLOSE_MSG:
            # stop STE or disconnect
            print ("+--- Stop STE ...")
            SCD_set_STE_config (p, False)
            SCD_toggle_STE_rolling (p, False, False)
            SCD_print_STE_result()
        else:
            print ("+--- invalid [RX] message !")    
        #
        if gTCPrxMsg == TCP_DEV_CLOSE_MSG:
            # disconnect
            print ("+--- Close Device ...")
            break    
    #
    # get notification
    #

    #
    # idling check
    #
    t = time.time()
    if t - gIDLElastTime > gIDLEinterval:
        #
        # doing some to keep BLE connection
        #
        p.readCharacteristic( SCD_STE_RESULT_HND )
        gIDLElastTime = t
        print ("+--- STE result query to keep connection")
#
#############################################

#############################################
#
# clean-up and init sensor device
#
p.writeCharacteristic( SCD_SET_GEN_CMD_HND, b'\x21' ) # reset threshold flag
time.sleep(0.7)
##p.writeCharacteristic( SCD_SET_MODE_HND, b'\xFF' )    # mode selection
##time.sleep(0.7)
if SCD_clear_memory(p) != None:
    p.disconnect()
#
# complete
#
loop.close()
print ("+--- All done !")
#
#############################################
