"""
Code to receive sensor data via BLE and send it to server thru TCP socket
Target Sensor Device: blutooth ble device; BOSCH SCD 110

This code does discover BOSCH SCD Sensor device via blutooth ble communication and read sensor data
followings are the brief steps included in this code;
- discovery
- connect
- set STE configuration
- start STE(Short Time Experiment)
- write STE notification to TCP socket
- until stop received
- disconnect

by Inho Byun, Researcher/KAIST
   inho.byun@gmail.com
                    started 2020-11-05
                    last updated 2020-11-07
"""
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
SCD_MAX_NOTIFY  = SCD_MAX_FLASH>>4  # int(SCD_MAX_FLASH / 16)

#
# Some constant parameters
#
SCAN_TIME        = 8.    # scanning duration for BLE devices 
STE_RUN_TIME     = 0.    # STE rolling time in secconds (if 0, end-less rolling)
STE_FREQUENCY    = (400, 800, 1600, 3200, 6400)  # of STE result 400 / 800 / 1600 / 3200 / 6400 Hz
MAX_STE_RUN_TIME = 30.   # max STE rolling time in seconds
#
# global variables
#
gTargetDevice    = None  # target device object 
gScannedCount    = 0     # count of scanned BLE devices
# STE - Short Time Experiment
gSTEMode    = bytes(35)  # Sensor Mode
gSTECount        = 0     # count of notifications from connected device
gSTEStartTime    = 0.    # notification start timestamp
gSTEStopTime     = 0.    # notification stop timestamp
gSTELastTime     = 0.    # last notification timestamp
gSTEData    = bytearray(33)

#############################################
# target definitions to TCP Server
#############################################
#
# target TCP Server identifiers
#
# TCP_HOST_NAME   = "127.0.0.1"       # TEST Host Name
# TCP_HOST_NAME   = "10.2.2.3"        # TEST Host Name
TCP_HOST_NAME   = "192.168.0.3"     # TEST Host Name
# TCP_HOST_NAME   = "125.131.73.31"   # Default Host Name
TCP_PORT        = 8088              # Default TCP Port Name
TCP_TX_INTERVAL     = 1.            # time interval to send notification to host      
TCP_DEV_READY_MSG   = 'DEV_READY'
TCP_DEV_CLOSE_MSG   = 'DEV_CLOSE'
TCP_STE_START_MSG   = 'STE_START'
TCP_STE_STOP_MSG    = 'STE_STOP'
#
# global variables
#
gSocketClient = None
gSocketError  = False

#############################################
# STE(Short Time Experiment) mode configuration (35 bytes) 
#############################################
#
STE_mode = bytearray(35)
STE_mode[ 0: 4]  = b'\x00\x00\x00\x00'  # [ 0~ 3] Unix time
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
mode  = 0xf0 # F0 sensor raw value to flash
#ode |= 0x01 # 01 sensor raw value to flash - accelerometer
#ode |= 0x02 # 02 sensor raw value to flash - magnetometer
#ode |= 0x04 # 04 sensor raw value to flash - light
#ode |= 0x08 # 08 sensor raw value to flash - temperature
STE_mode[30:31] = bytes(struct.pack('<h',mode))
#
gSTEMode = bytes(STE_mode[0:35])
                  
#############################################
# functions definition
#############################################
# convert hex() string to format like "hh.hh.hh"
#
def hex_str( vBytes ):
    
    vString = ''.join(['.' + ch if i % 2 == 0 and i != 0 else ch for i, ch in enumerate(vBytes.hex())])
    return vString

#############################################
# output STE data
#
def string_STE_data( pResult ):

    # output Accelerrometer X, Y, Z axis arithmetic mean & variation  
    adxl_mean_x = float( int.from_bytes(pResult[0:2], byteorder='little', signed=True) ) \
                  / 10.0
    adxl_vari_x = float( int.from_bytes(pResult[6:10], byteorder='little', signed=True) ) \
                  / 100.0
    adxl_mean_y = float( int.from_bytes(pResult[2:4], byteorder='little', signed=True) ) \
                  / 10.0
    adxl_vari_y = float( int.from_bytes(pResult[10:14], byteorder='little', signed=True) ) \
                  / 100.0
    adxl_mean_z = float( int.from_bytes(pResult[4:6], byteorder='little', signed=True) ) \
                  / 10.0
    adxl_vari_z = float( int.from_bytes(pResult[14:18], byteorder='little', signed=True) ) \
                  / 100.0
    # output temperature
    temperature = float( int.from_bytes(pResult[18:20], byteorder='little', signed=True) ) \
                  * 0.0078
    # output light
    light = float( int.from_bytes(pResult[20:24], byteorder='little', signed=True) ) \
            / 1000.0
    # output Magnetometer X, Y, Z axis raw data 
    magneto_x = float( int.from_bytes(pResult[24:26], byteorder='little', signed=True) ) \
                / 16.0
    magneto_y = float( int.from_bytes(pResult[26:28], byteorder='little', signed=True) ) \
                / 16.0
    magneto_z = float( int.from_bytes(pResult[28:30], byteorder='little', signed=True) ) \
                / 16.0
    # make string to send
    str  = '('
    str += "%.1f" % adxl_mean_x + ','
    str += "%.2f" % adxl_vari_x + ','
    str += "%.1f" % adxl_mean_y + ','
    str += "%.2f" % adxl_vari_y + ','
    str += "%.1f" % adxl_mean_z + ','
    str += "%.2f" % adxl_vari_z + ','
    str += "%.2f" % temperature + ','
    str += "%.3f" % light + ','
    str += "%.1f" % magneto_x + ','
    str += "%.1f" % magneto_y + ','
    str += "%.1f" % magneto_z
    str += ')'     
    return str

#############################################    
# print STE result
#
def print_STE_result():
    global gSTEMode
    global gSTECount
    global gSTEStartTime
    global gSTEStopTime

    # output time stamp
    tm = float( (struct.unpack('<l', gSTEMode[0:4]))[0] )   
    print ( "\tSTE config. time   : %s(%.3f)" \
            % (datetime.datetime.fromtimestamp(tm).strftime('%Y-%m-%d %H:%M:%S'), tm) )
    print ( "\tNotification Start : %s(%.3f)" \
            % (datetime.datetime.fromtimestamp(gSTEStartTime).strftime('%Y-%m-%d %H:%M:%S'), gSTEStartTime) )
    print ( "\tNotification End   : %s(%.3f)" \
            % (datetime.datetime.fromtimestamp(gSTEStopTime).strftime('%Y-%m-%d %H:%M:%S'), gSTEStopTime) )      
    print ( "\tNotification Count : %d" % gSTECount)
    return

#############################################
# Define scan callback
#############################################
class ScanDelegate(DefaultDelegate):
    
    def __init__(self):
        global gScannedCount

        DefaultDelegate.__init__(self)
        gScannedCount = 0
        print("**** scan handler is configured", end='\n', flush = True)

    def handleDiscovery(self, dev, isNewDev, isNewData):
        global gScannedCount

        if isNewDev:
            gScannedCount += 1
            print ('**** >' if gScannedCount==1 else '>', end='', flush = True)
        elif isNewData:
            print ('**** +' if gScannedCount==0 else '+', end='', flush = True)            

#############################################
# Define notification callback
#############################################
class NotifyDelegate(DefaultDelegate):
    
    def __init__(self, params):
        global gSTECount

        DefaultDelegate.__init__(self)
        gSTECount = 0
        print("**** device notification handler is configured", end='\n', flush = True)
      
    def handleNotification(self, cHandle, data):
        global SCD_STE_RESULT_HND
        global TCP_TX_INTERVAL
        global gSTECount
        global gSTEStartTime
        global gSTEStopTime
        global gSTELastTime
        global gSocketClient
        global gSocketError

        if cHandle == SCD_STE_RESULT_HND:
        # STE notification
            if gSTECount == 0:
                gSTEStopTime = gSTELastTime  = gSTEStartTime = time.time()
            else:
                gSTEStopTime = time.time()
            gSTECount += 1
            if gSTEStopTime-gSTELastTime > TCP_TX_INTERVAL:
                try:
                    gSocketClient.send(string_STE_data(data).encode())
                except:
                    gSocketError = -2
                else:    
                    gSTELastTime = gSTEStopTime
        else:
            print("**** %2d-#%3d-[%s]" % (cHandle, gSTECount, hex_str(data)), end='\n', flush = True)

#############################################
# Define Scan_and_connect
#############################################
def scan_and_connect( is_first = True ):
    global SCAN_TIME
    global TARGET_MANUFA_UUID
    global TARGET_DEVICE_NAME
    global gTargetDevice
    global gSocketClient
    #
    # scanning for a while
    #
    scanner = Scanner().withDelegate(ScanDelegate())
    if is_first:
        print ("+--- BLE device scan started..." )
    else:
        print ("+--- BLE device scan restarted..." )    
    devices = scanner.scan(SCAN_TIME)
    print ("\n+--- BLE device scan completed... [%d] devices are scanned" % gScannedCount)
    #
    # check to match BOSCH SCD device identifiers
    #
    for dev in devices:
        matching_count = 0
        for (adtype, desc, value) in dev.getScanData():
            if adtype == 255 and TARGET_MANUFA_UUID in value:
                matching_count += 1
                print("\tfound target (AD Type=%d) '%s' is '%s'" % (adtype, desc, value))            
            if adtype == 9 and TARGET_DEVICE_NAME in value:
                matching_count += 1
                print("\tfound target (AD Type=%d) '%s' is '%s'" % (adtype, desc, value))            
            if matching_count >= 2:
                print("\tfound BOSCH SCD device!")
                print("+--- device address [%s], type=[%s], RSSI=[%d]dB" % (dev.addr, dev.addrType, dev.rssi))
                gTargetDevice = dev
                break
        if gTargetDevice != None:
            break
    #
    # if none found then exiting    
    #
    if gTargetDevice == None:
        print("\tno matching device found... Exiting...")
        gSocketClient.close()
        sys.exit(1)
    #
    # connect
    #
    print("+--- connecting [%s], type=[%s]" % (gTargetDevice.addr, gTargetDevice.addrType))
    p = None
    retry = 0
    while p == None:
        try:
            p = Peripheral(gTargetDevice.addr, gTargetDevice.addrType)
        except:
            print("\tBLE device connection error occured... retry after 3 sec...")
            retry += 1
            if retry > 3:
                print("\tBLE device connection error occured... exiting...")
                gSocketClient.close()
                sys.exit(-1)
            time.sleep(3)    
    #
    # should increase MTU
    #           
    p.setMTU(SCD_MAX_MTU)
    return p

#############################################
#############################################
#         
# Main starts here
#
#############################################

if len(sys.argv) > 1:
    print ("TCP S-> take 1'st argument as Host IP address (default: '%s')" % TCP_HOST_NAME)
    TCP_HOST_NAME = sys.argv[1]
if len(sys.argv) > 2:
    print ("TCP S-> take 2'nd argument as port# (default: '%d')" % TCP_PORT)
    TCP_PORT = int(sys.argv[2])

#############################################
#
# connect server socket
#
gSocketClient = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

if gSocketClient != None:
    try:
        print("TCP C-> trying to connect %s:%d" % (TCP_HOST_NAME, TCP_PORT) )
        gSocketClient.connect((TCP_HOST_NAME, TCP_PORT))
    except:
        print("TCP C-> socket connection fail... Exiting...")
        sys.exit(1)    
else:
    print("TCP C-> socket creation fail... Exiting...")
    sys.exit(1)
gSocketClient.setblocking(0)

#############################################
#
# scan and connect SCD
#
p = scan_and_connect()
#
# read Device Name, Manufacurer Name, etc.
#
ret_val = p.readCharacteristic( SCD_DEVICE_NAME_HND )
print ("\tDevice Name is [%s]" % ret_val.decode("utf-8"))
#
ret_val = p.readCharacteristic( SCD_SYSTEM_ID_HND )
print ("\tSystem ID is [%s][%s]" % (hex_str(ret_val[0:3]), hex_str(ret_val[3:8])))
#
ret_val = p.readCharacteristic( SCD_SERIAL_NUM_HND )
print ("\tSerial # is [%s]" % ret_val.decode("utf-8"))
#
ret_val = p.readCharacteristic( SCD_FW_REVISION_HND )
print ("\tRevision is FW [%s]," % ret_val.decode("utf-8"), end = '')
#
ret_val = p.readCharacteristic( SCD_HW_REVISION_HND )
print ("HW [%s]," % ret_val.decode("utf-8"), end = '')
#
ret_val = p.readCharacteristic( SCD_SW_REVISION_HND )
print ("SW [%s]" % ret_val.decode("utf-8"))
#
ret_val = p.readCharacteristic( SCD_MANUFA_NAME_HND )
print ("\tManufacturer Name is [%s]" % ret_val.decode("utf-8"))
#
ret_val = p.readCharacteristic( SCD_IF_VERSION_HND )
print ("\tIF Version is [%s]" % hex_str(ret_val))
#
ret_val = p.readCharacteristic( SCD_TEST_RESULT_HND )
print ("\tSelf Test Result is [%s] c0:OK, otherwise not OK!" % ret_val.hex())
#
ret_val = p.readCharacteristic( SCD_SET_MODE_HND )
print ("\tMode is [%s] 00:STE, ff:Mode Selection" % ret_val.hex())
#
#
STE_result_0 = p.readCharacteristic( SCD_STE_RESULT_HND )
time.sleep(1.)
STE_result_1 = p.readCharacteristic( SCD_STE_RESULT_HND )
print ("\tChecking rolling counter [%d] [%d]" % (int(STE_result_0[32]), int(STE_result_1[32])) )
if STE_result_0[32] != STE_result_1[32] :
    print ("\t\t=> rolling...set STE stop")
    p.writeCharacteristic( SCD_SET_MODE_HND, b'\x00' )
    p.writeCharacteristic( SCD_SET_GEN_CMD_HND, b'\x20' )
#
ret_val = p.readCharacteristic( SCD_STE_CONFIG_HND )
print ("\tFlash memory remain is [%s] MAX:0b0000" % ret_val[31:34].hex())
if (struct.unpack('i', ret_val[31:35]))[0] < SCD_MAX_FLASH:  
    print ("\t\t=> flash memory is not empty...cleanning-up flash and re-try")
    print ("+--- Erase flash wait for seconds...")
    p.writeCharacteristic( SCD_SET_GEN_CMD_HND, b'\x30' ) # erase sensor data
    p.disconnect()
    time.sleep(10.)
    p = scan_and_connect(False)    
#
#############################################
#
# check Mode to set STE Mode
#
ret_val = p.readCharacteristic( SCD_SET_MODE_HND )
if ret_val !=  b'\x00':
    print("+--- set STE mode")
    p.writeCharacteristic( SCD_SET_MODE_HND, b'\x00' )
    ret_val = p.readCharacteristic( SCD_SET_MODE_HND )
#############################################
#
# set STE Configuration
#
time_bytes = struct.pack('<l', int(time.time()))
gSTEMode = bytes( time_bytes[0:4] ) + gSTEMode[4:35]
p.writeCharacteristic( SCD_STE_CONFIG_HND, gSTEMode )
time.sleep(1.)
ret_val = p.readCharacteristic( SCD_STE_CONFIG_HND )
print ("\tSTE config. get\n[%s](%d)" % (hex_str(ret_val), len(ret_val)))
#
#############################################

#############################################
#
# send 1'st message
#
try:
    gSocketClient.send(TCP_DEV_READY_MSG.encode())
    print("TCP C-> [send] '%s'..." % TCP_DEV_READY_MSG)
except:
    gSocketError = True
    print("TCP C-> [send] error !!!")

#############################################
#
# loop if not socket error and not dev_close 
#
while not gSocketError:
#
#############################################
#
# wait start message
#
    while True:
        try:
            rx_msg = gSocketClient.recv(1024).decode()
        except BlockingIOError:
            continue
        print ( "TCP C-> [recv] '%s'" % rx_msg)
        break    
    
    if rx_msg == TCP_DEV_CLOSE_MSG:
        break

    if rx_msg == TCP_STE_START_MSG:
#
# start STE
#
        print ("+--- STE starting...")
        p.setDelegate( NotifyDelegate(p) )
        p.writeCharacteristic( SCD_STE_RESULT_HND+1, struct.pack('<H', 1))
        time.sleep(0.7)
        p.writeCharacteristic( SCD_SET_GEN_CMD_HND, b'\x20' )
        time_start = time.time()
        while True:
            wait_flag = p.waitForNotifications(1.)
            time_stop = time.time()
            if STE_RUN_TIME > 0 and (time_stop-time_start) > STE_RUN_TIME:
                print ( "\n\t[done] STE time exceeded", end = '\n', flush = True )
                break
            if gSocketError == -2:
                print ( "\n\t[done] sending error thru socket, reset error", end = '\n', flush = True )
                gSocketError = False
                break          
            try:
                rx_msg = gSocketClient.recv(1024).decode()
            except BlockingIOError:
                continue
            else:
                print ( "\nTCP C-> [recv] '%s'" % rx_msg)
                if rx_msg == TCP_STE_STOP_MSG or rx_msg == TCP_DEV_CLOSE_MSG:
                    break
#
# stop STE
#
    if rx_msg == TCP_STE_STOP_MSG or rx_msg == TCP_DEV_CLOSE_MSG:
        p.writeCharacteristic( SCD_SET_GEN_CMD_HND, b'\x20' )        
        print ("\tSTE is stopping")        
        ret_val = p.readCharacteristic( SCD_SET_GEN_CMD_HND )
        while ( ret_val != b'\x00' ):
            print ("\tSTE has not completed yet, generic command is [%s]" % ret_val.hex())
            time.sleep(0.7)
            ret_val = p.readCharacteristic( SCD_SET_GEN_CMD_HND )
        print ("\n+--- STE stoped")
        print_STE_result()
    if rx_msg == TCP_DEV_CLOSE_MSG:
        break    
#
#############################################

#############################################

#
# clean-up and init sensor device
#
p.writeCharacteristic( SCD_SET_GEN_CMD_HND, b'\x21' ) # reset threshold flag
time.sleep(0.7)
# p.writeCharacteristic( SCD_SET_MODE_HND, b'\xFF' )    # mode selection
# time.sleep(0.7)
p.writeCharacteristic( SCD_SET_GEN_CMD_HND, b'\x30' ) # erase sensor data
print ("+--- erase flash memory wait for 10 seconds...wait...")
time.sleep(10.)
#
# disconnect
#
p.disconnect()
gSocketClient.close()
#
#############################################
#    
print ("+--- All done !")
#
#############################################
