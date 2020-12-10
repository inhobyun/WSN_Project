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
                    updated 2020-12-03; working revision
                    updated 2020-12-08; comm protocol, BLE scan updated
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
# MAX constants of BOSCH SCD
#
SCD_MAX_MTU   = 65                # MAX SCD Comm. Packet size
SCD_MAX_FLASH = 0x0b0000          # 11*16**4 = 720896 = 704K

#
# Some constant parameters
#
SCAN_TIME       = 8.     # scanning duration for BLE devices 
RESCAN_INTERVAL = 90.    # 1.5 min.; interval time to rescan BLE after scan failed
RESCAN_PERIOD   = 11100. # 3 hrs 5 min.; time period to rescan BLE to connect 
#
STE_RUN_TIME    = 3.     # STE rolling time in secconds for SENSOR data recording
STE_FREQUENCY   = (400, 800, 1600, 3200, 6400)  # of STE result 400 / 800 / 1600 / 3200 / 6400 Hz 
#
# global variables
#
gTargetDevice = None  # target device object 
gScannedCount = 0     # count of scanned BLE devices
# STE - Short Time Experiment
gSTEcfgMode   = bytes(35)  # Sensor Mode
gSTEnotiCnt   = 0     # count of notifications from connected device
gSTEstartTime = 0.    # notification start timestamp
gSTElastTime  = 0.    # last notification timestamp
gSTElastData  = None    # last notification data
gSTEisRolling = False # flag wether STE is on rolling
# BDT - Block Data Transfer
gBDTnotiCnt   = 0
gBDTstartTime = 0.   
gBDTlastTime  = 0.
gBDTdata      = bytearray(SCD_MAX_FLASH)
gBDTtextBlock = ''
gBDTtextLen   = 0
gBDTtextLen   = 0
gBDTcrc32     = bytearray(4)
gBDTisRolled = False
# IDLE
gIDLElastTime = 0.    # last BLE traffic on connection
gIDLEinterval = 60.   # time interval to make BLE traffic to keep connection


#############################################
# target definitions to TCP Server
#############################################
#
# target TCP Server identifiers
#
##TCP_HOST_NAME = "127.0.0.1"       # TEST Host Name
TCP_HOST_NAME = "10.2.2.3"        # TEST Host Name
##TCP_HOST_NAME = "192.168.0.3"     # TEST Host Name
##TCP_HOST_NAME = "125.131.73.31"   # Default Host Name
TCP_PORT      = 8088              # Default TCP Port Name
#
TCP_DEV_READY_MSG = 'DEV_READY'     # server message to check client ready
TCP_DEV_CLOSE_MSG = 'DEV_CLOSE'     # server message to disconnect client
TCP_STE_START_MSG = 'STE_START'     # server message to start STE for monitoring
TCP_STE_STOP_MSG  = 'STE_STOP'      # server message to stop STE
TCP_STE_REQ_MSG   = 'STE_REQ'       # server message to request a STE result data 
TCP_BDT_RUN_MSG   = 'BDT_RUN'       # server message to run BDT advanced STE /w memory write
TCP_BDT_REQ_MSG   = 'BDT_REQ'       # server message to request BDT data
TCP_BDT_END_MSG   = 'BDT_END'       # client message to inform BDT data transfer completed
#
# global variables
#
gTCPreader = None
gTCPwriter = None
gTCPrxMsg  = None
gTCPtxMsg  = None
gTCPnullRXcnt = 0

#############################################
# handle to receive command message
#############################################
#
async def tcp_RX(loop):
    global gTCPrxMsg
    global gTCPreader
    global gTCPwriter
    global gTCPnullRXcnt
    #
    if gTCPwriter == None:
        print('\n>--->\nAIO-C> connecting server to read ... ', end ='', flush=True)
        gTCPreader, gTCPwriter = await asyncio.open_connection(TCP_HOST_NAME, TCP_PORT)
        print('connected\n<---<\n', flush=True)
    #
    rx_data = None
    print('AIO-C> [RX] wait => ', end = '', flush=True)
    try:
        rx_data = await asyncio.wait_for ( gTCPreader.read(512), timeout=10.0 )
    except asyncio.TimeoutError:
        print('timeout', flush=True)
        pass
    except:
        print('error !', flush=True)
        gTCPwriter = gTCPreader = None
        pass
    else:
        if rx_data != None:
            gTCPrxMsg = rx_data.decode()
        if gTCPrxMsg == '':
            gTCPnullRXcnt += 1
            print('null received: %d times' % gTCPnullRXcnt, flush=True)
        else:
            gTCPnullRXcnt = 0
            print('"%r" received' % gTCPrxMsg, flush=True) 
    
#############################################
# handle to send data
#############################################
#
async def tcp_TX(tx_msg, loop):
    global gTCPrxMsg
    global gTCPreader
    global gTCPwriter
    #
    if gTCPwriter == None:
        print('\n>--->\nAIO-C> connecting server to write ... ', end ='', flush=True)
        gTCPreader, gTCPwriter = await asyncio.open_connection(TCP_HOST_NAME, TCP_PORT)
        print('connected\n<---<\n', flush=True)
    #
    if tx_msg != None and tx_msg != '':
        print('AIO-C> [TX] try => ', end = '', flush=True)
        tx_data = tx_msg.encode()
        try:
            gTCPwriter.write(tx_data)
            await asyncio.wait_for ( gTCPwriter.drain(), timeout=10.0 )        
        except asyncio.TimeoutError:
            print('timeout !', flush=True)
        except:
            print('error !', flush=True)
            gTCPwriter = gTCPreader = None
        else:
            n = len(tx_msg)
            if n < 40:        
                print('"%r" sent' % tx_msg, flush=True)
            else:
                txt = tx_msg[0:40]
                txt.replace('\n','\\n')
                print('"%r"...; %d bytes sent' % (txt, n), flush=True)    
    else:
        print('AIO-C> [TX] nothing to send !', flush=True)    

#############################################
# functions definition
#############################################
# STE(Short Time Experiment) mode configuration (35 bytes) 
#
def SCD_set_STE_config( p, is_writing = False ):
    global gSTEcfgMode
    #
    if p == None:
        return
    #
    STE_mode = bytearray(35)
    #
    time_bytes = struct.pack( '<l', int(time.time()) )
    STE_mode[ 0: 4]  = bytes( time_bytes[0:4] )  # [ 0~ 3] Unix time
    #
    mode  = 0xf0
    mode |= 0x01 # 01 sensor En/Disable - accelerometer
    mode |= 0x02 # 02 sensor En/Disable - magnetometer
    mode |= 0x04 # 04 sensor En/Disable - light
    mode |= 0x08 # 08 sensor En/Disable - temperature
    STE_mode[ 4: 5] = bytes( struct.pack('<h',mode) )
    #
    #ode  = 0x00 # ?0 data rate - accelerometer ODR 400Hz
    #ode  = 0x01 # ?1 data rate - accelerometer ODR 800Hz
    #ode  = 0x02 # ?2 data rate - accelerometer ODR 1600Hz
    mode  = 0x03 # ?3 data rate - accelerometer ODR 3200Hz
    #ode  = 0x04 # ?4 data rate - accelerometer ODR 6400Hz
    #ode |= 0x00 # 0? data rate - light sensor ODR 100ms(10Hz)
    #ode |= 0x10 # 1? data rate - light sensor ODR 800ms(1.25Hz)
    STE_mode[ 5: 6] = bytes( struct.pack('<h',mode) )
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
    STE_mode[30:31] = bytes( struct.pack('<h',mode) )
    #
    gSTEcfgMode = bytes(STE_mode[0:35])
    #
    p.writeCharacteristic( SCD_STE_CONFIG_HND, gSTEcfgMode )
    time.sleep(.3)
    ret_val = p.readCharacteristic( SCD_STE_CONFIG_HND )
    print ("SCD> STE config. get\n[%s](%d)" % (hex_str(ret_val), len(ret_val)), flush=True)
    #
    return

#############################################
# check wether STE is rolling or not 
#
def SCD_check_STE_rolling( p ):
    global gSTEisRolling
    #
    STE_result_0 = p.readCharacteristic( SCD_STE_RESULT_HND )
    time.sleep(.3)
    STE_result_1 = p.readCharacteristic( SCD_STE_RESULT_HND )
    print ("SCD> checking rolling counter [%d] [%d]" % (int(STE_result_0[32]), int(STE_result_1[32])), flush=True)
    if STE_result_0[32] != STE_result_1[32] :
        gSTEisRolling = True
    else:
        gSTEisRolling = False
    #    
    return gSTEisRolling      

#############################################
# toggle STE start or stop 
#
def SCD_toggle_STE_rolling( p, will_start = False, will_notify = False ):
    global gSTEisRolling
    #
    if p == None:
        return
    #
    if will_start:
        if not gSTEisRolling:
            if will_notify:
                p.writeCharacteristic( SCD_STE_RESULT_HND+1, struct.pack('<H', 1) )
                time.sleep(0.7)
            p.writeCharacteristic( SCD_SET_MODE_HND, b'\x00' )    
            p.writeCharacteristic( SCD_SET_GEN_CMD_HND, b'\x20' )
            print ("SCD> STE is starting", flush=True)        
            gSTEisRolling = True
    else:
        if gSTEisRolling:
            p.writeCharacteristic( SCD_SET_GEN_CMD_HND, b'\x20' )
            print ("SCD> STE is stopping", flush=True)        
            ret_val = p.readCharacteristic( SCD_SET_GEN_CMD_HND )
            while ( ret_val != b'\x00' ):
                print ("SCD> => STE has not completed yet, generic command is [%s]" % ret_val.hex(), flush=True)
                time.sleep(0.7)
                ret_val = p.readCharacteristic( SCD_SET_GEN_CMD_HND )
            print ("SCD> STE stoped", flush=True)
            gSTEisRolling = False
        ret_val = p.readCharacteristic( SCD_SET_MODE_HND )
        while ret_val !=  b'\x00':
            print("SCD> set STE mode", flush=True)
            p.writeCharacteristic( SCD_SET_MODE_HND, b'\x00' )
            ret_val = p.readCharacteristic( SCD_SET_MODE_HND )
    #        
    return        

#############################################
# convert hex() string to format like "hh.hh.hh"
#
def hex_str( vBytes ):
    #
    vString = ''.join(['.' + ch if i % 2 == 0 and i != 0 else ch for i, ch in enumerate(vBytes.hex())])
    #
    return vString

#############################################
# output STE data to string
#
def SCD_string_STE_data( pTime, pResult ):
    #
    # output time stamp
    tm_stamp = ( "%s [%.3f]" % (datetime.datetime.fromtimestamp(pTime).strftime('%Y-%m-%d %H:%M:%S'), pTime) )
    # output Accelerrometer X, Y, Z axis arithmetic mean & variation
    adxl_mean_x = float( int.from_bytes(pResult[ 0: 2], byteorder='little', signed=True) ) / 10.0
    adxl_mean_y = float( int.from_bytes(pResult[ 2: 4], byteorder='little', signed=True) ) / 10.0
    adxl_mean_z = float( int.from_bytes(pResult[ 4: 6], byteorder='little', signed=True) ) / 10.0
    adxl_vari_x = float( int.from_bytes(pResult[ 6:10], byteorder='little', signed=True) ) / 100.0
    adxl_vari_y = float( int.from_bytes(pResult[10:14], byteorder='little', signed=True) ) / 100.0
    adxl_vari_z = float( int.from_bytes(pResult[14:18], byteorder='little', signed=True) ) / 100.0
    #
    # output temperature
    temperature = float( int.from_bytes(pResult[18:20], byteorder='little', signed=True) ) * 0.0078
    #
    # output light
    light = float( int.from_bytes(pResult[20:24], byteorder='little', signed=True) ) / 1000.0
    #
    # output Magnetometer X, Y, Z axis raw data 
    magneto_x = float( int.from_bytes(pResult[24:26], byteorder='little', signed=True) ) / 16.0
    magneto_y = float( int.from_bytes(pResult[26:28], byteorder='little', signed=True) ) / 16.0
    magneto_z = float( int.from_bytes(pResult[28:30], byteorder='little', signed=True) ) / 16.0
    #
    # make string to send
    str  = "(" + tm_stamp + ","
    str += "%.1f," % adxl_mean_x
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
    #   
    return str

#############################################    
# print STE result
#
def SCD_print_STE_status():
    global gSTEcfgMode
    global gSTEnotiCnt
    global gSTEstartTime
    global gSTElastTime
    global gSTElastData
    #
    # output time stamp & notification, rolling count
    #
    tm = float( (struct.unpack('<l', gSTEcfgMode[0:4]))[0] )   
    print ( "SCD> STE config. time   : %s(%.3f)" \
            % (datetime.datetime.fromtimestamp(tm).strftime('%Y-%m-%d %H:%M:%S'), tm), flush=True )
    if gSTEnotiCnt > 0:
        print ( "SCD> Notification Start : %s(%.3f)" \
                % (datetime.datetime.fromtimestamp(gSTEstartTime).strftime('%Y-%m-%d %H:%M:%S'), gSTEstartTime), flush=True )
        print ( "SCD> Notification End   : %s(%.3f)" \
                % (datetime.datetime.fromtimestamp(gSTElastTime).strftime('%Y-%m-%d %H:%M:%S'), gSTElastTime), flush=True )
        print ( "SCD> Notification Count : %d" % gSTEnotiCnt, flush=True )
        gSTEnotiCnt = gSTElastTime = gSTEstartTime = 0
    if  gSTElastData != None:
        print ( "SCD> Rolling Count      : %d" % int(gSTElastData[32]), flush=True )
    #
    return

#############################################
# Define scan callback
#############################################
class ScanDelegate(DefaultDelegate):
    
    def __init__(self):
        global gScannedCount
        #
        DefaultDelegate.__init__(self)
        gScannedCount = 0
        print("WSN-C> scan handler is configured", end='\n', flush = True)

    def handleDiscovery(self, dev, isNewDev, isNewData):
        global gScannedCount
        #
        if isNewDev:
            gScannedCount += 1
            print ('WSN-C> >' if gScannedCount==1 else '>', end='', flush = True)
        elif isNewData:
            print ('WSN-C> +' if gScannedCount==0 else '+', end='', flush = True)            

#############################################
# Define notification callback
#############################################
class NotifyDelegate(DefaultDelegate):
    
    def __init__(self, params):
        global gSTEnotiCnt
        #
        DefaultDelegate.__init__(self)
        gSTEnotiCnt = 0
        print("WSN-C> device notification handler is configured", end='\n', flush = True)
      
    def handleNotification(self, cHandle, data):
        global gSTEnotiCnt
        global gSTEstartTime
        global gSTElastTime
        global gSTElastData
        global gBDTnotiCnt
        global gBDTstartTime
        global gBDTlastTime
        global gBDTdata
        global gBDTcrc32
        #
        if cHandle == SCD_STE_RESULT_HND:
            # STE notification
            if gSTEnotiCnt == 0:
                gSTElastTime  = gSTEstartTime = time.time()
            else:
                gSTElastTime = time.time()
            gSTEnotiCnt += 1
            gSTElastData = data
        #    
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
                print("WSN-C> BDT Packet No Error !... [%d] should less than [%d]" % (packet_no, gBDTnotiCnt), end='\n', flush = True)            
        #        
        else:
            print("WSN-C> %2d-#%3d-[%s]" % (cHandle, gSTEnotiCnt, hex_str(data)), end='\n', flush = True)

#############################################
# Define Scan_and_connect
#
# should implement "BTLEDisconnectError" exception
#
#############################################
def SCD_scan_and_connect( is_first = True ):
    global gTargetDevice
    #
    # scanning for a while
    #
    print ("SCD> BLE device scan %sstarted..." % ('re' if not is_first else ''), flush=True)

    tm = tm_s = time.time()
    while tm_s - tm < RESCAN_PERIOD:
        scanner = Scanner().withDelegate(ScanDelegate())
        devices = scanner.scan(SCAN_TIME)
        print ("\nSCD> BLE device scan completed... [%d] devices are scanned" % gScannedCount, flush=True)
        #
        # check to match BOSCH SCD device identifiers
        #
        for dev in devices:
            matching_count = 0
            for (adtype, desc, value) in dev.getScanData():
                if adtype == 255 and TARGET_MANUFA_UUID in value:
                    matching_count += 1
                    print("SCD> => found target (AD Type=%d) '%s' is '%s'" % (adtype, desc, value), flush=True)            
                if adtype == 9 and TARGET_DEVICE_NAME in value:
                    matching_count += 1
                    print("SCD> => found target (AD Type=%d) '%s' is '%s'" % (adtype, desc, value), flush=True)            
                if matching_count >= 2:
                    print("SCD> => found BOSCH SCD device!")
                    print("SCD> device address [%s], type=[%s], RSSI=[%d]dB" % (dev.addr, dev.addrType, dev.rssi), flush=True)
                    gTargetDevice = dev
                    break
            if gTargetDevice != None:
                break
        #
        # if none found then exiting    
        #
        if gTargetDevice == None:
            tm = time.time()
            print("SCD> no matching device found at [%s]... retry after %d sec..." \
                  % (datetime.datetime.fromtimestamp(tm).strftime('%Y-%m-%d %H:%M:%S'), RESCAN_INTERVAL), flush=True )
            if tm_s - tm >= RESCAN_PERIOD:
                print("SCD> no matching device found... exiting...", flush=True)
                sys.exit(-1)
            time.sleep(RESCAN_INTERVAL)
        else:
            break        
    #
    # connect
    #
    print("SCD> connecting [%s], type=[%s]" % (gTargetDevice.addr, gTargetDevice.addrType), flush=True)
    p = None
    retry = 0
    while p == None:
        try:
            p = Peripheral(gTargetDevice.addr, gTargetDevice.addrType)
        except:
            retry += 1
            print("SCD> => BLE device connection error occured [%d] time(s)... retry after 10 sec..." % retry, flush=True)
            if retry > 30:
                print("SCD> => BLE device connection error occured... exiting...", flush=True)
                sys.exit(-1)
            time.sleep(10)    
    #
    # should increase MTU##
    #           
    p.setMTU(SCD_MAX_MTU)
    #
    return p

#############################################
# clear memory 
#
def SCD_clear_memory( p ):
    #
    ret_val = p.readCharacteristic( SCD_STE_CONFIG_HND )
    print ("SCD> Flash memory remain is [%s] MAX:0b0000" % ret_val[31:34].hex(), flush=True)
    if (struct.unpack('i', ret_val[31:35]))[0] < SCD_MAX_FLASH:  
        print ("SCD> => flash memory is not empty ... cleanning-up flash memory", flush=True)
        print ("SCD> Erase flash wait for seconds ... should reconnect device", flush=True)
        p.writeCharacteristic( SCD_SET_GEN_CMD_HND, b'\x30' ) # erase sensor data
        p.disconnect()
        time.sleep(10.)
        p = None
    #    
    return p    

#############################################
# run STE for idling
#
def SCD_run_STE_for_idling( p ): 
    #
    # rolls STE for short time period
    #
    # start STE w/o memory writing
    print ("SCD> STE running for idling ...", flush=True)
    p.setDelegate( NotifyDelegate(p) )
    SCD_set_STE_config(p, False)
    SCD_toggle_STE_rolling(p, True, True)
    # take rolling time ( added more overhead time)
    tm = time.time()
    while time.time() - tm <= 0.3:
        p.waitForNotifications(0.1)
    # stop STE
    SCD_toggle_STE_rolling(p, False, False) 
    SCD_print_STE_status()
    return

#############################################
# run STE & BLK data transfer
#
def SCD_run_STE_and_BDT( p ):
    global gBDTisRolled
    global gBDTnotiCnt
    global gBDTstartTime
    global gBDTlastTime    
    #
    # rolls STE for certain time period
    #
    # start STE w/ memory writing
    print ("SCD> Recording STE starting ...", flush=True)
    p.setDelegate( NotifyDelegate(p) )
    SCD_set_STE_config(p, True)
    SCD_toggle_STE_rolling(p, True, True)
    # take rolling time ( added more overhead time)
    tm = time.time()
    while time.time() - tm <= STE_RUN_TIME:
        wait_flag = p.waitForNotifications(1.)
    # stop STE
    SCD_toggle_STE_rolling(p, False, False) 
    SCD_print_STE_status()
    #
    # start BDT
    #
    print ("SCD> Bulk Data Transfer after a while ...", flush=True)
    time.sleep(0.7)
    p.setDelegate( NotifyDelegate(p) )
    print ("SCD> BDT Starting ...", flush=True)
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
    print ("\nSCD> Bulk Data Transfer completed...status is [%s], time [%.3f], count [%d]" % \
            (ret_val.hex(), (gBDTlastTime-gBDTstartTime), gBDTnotiCnt), flush=True )
    #
    gBDTisRolled = True        
    return

#############################################
# print SCD info
#
def SCD_print_info( p ):

    ret_val = p.readCharacteristic( SCD_DEVICE_NAME_HND )
    print ("SCD> Device Name is [%s]" % ret_val.decode("utf-8"), flush=True)
    #
    ret_val = p.readCharacteristic( SCD_SYSTEM_ID_HND )
    print ("SCD> System ID is [%s][%s]" % (hex_str(ret_val[0:3]), hex_str(ret_val[3:8])), flush=True)
    #
    ret_val = p.readCharacteristic( SCD_SERIAL_NUM_HND )
    print ("SCD> Serial # is [%s]" % ret_val.decode("utf-8"), flush=True)
    #
    ret_val = p.readCharacteristic( SCD_FW_REVISION_HND )
    print ("SCD> Revision is FW [%s]," % ret_val.decode("utf-8"), end = '', flush=True)
    #
    ret_val = p.readCharacteristic( SCD_HW_REVISION_HND )
    print ("HW [%s]," % ret_val.decode("utf-8"), end = '', flush=True)
    #
    ret_val = p.readCharacteristic( SCD_SW_REVISION_HND )
    print ("SW [%s]" % ret_val.decode("utf-8"), flush=True)
    #
    ret_val = p.readCharacteristic( SCD_MANUFA_NAME_HND )
    print ("SCD> Manufacturer Name is [%s]" % ret_val.decode("utf-8"), flush=True)
    #
    ret_val = p.readCharacteristic( SCD_IF_VERSION_HND )
    print ("SCD> IF Version is [%s]" % hex_str(ret_val), flush=True)
    #
    ret_val = p.readCharacteristic( SCD_TEST_RESULT_HND )
    print ("SCD> Self Test Result is [%s] c0:OK, otherwise not OK!" % ret_val.hex(), flush=True)
    #
    ret_val = p.readCharacteristic( SCD_SET_MODE_HND )
    print ("SCD> Mode is [%s] 00:STE, ff:Mode Selection" % ret_val.hex(), flush=True)
    return

#############################################
# create text memory block from BDT w/o non-data
#
def SCD_BDT_text_block():
    global gBDTnotiCnt
    global gBDTdata
    global gBDTtextBlock
    global gBDTtextLen
    global gBDTtextPos

    
    print ("SCD> text block creation from BDT ...", flush=True)
    if gBDTtextBlock != '':
        del gBDTtextBlock
        gBDTtextBlock = ''
    # find EOD(End-of-Data: 0xaaaa, 0xaaaa)
    is_aa = 0
    for EOD_pos in range((gBDTnotiCnt+1)*16, (gBDTnotiCnt-3)*16, -1):
        if gBDTdata[EOD_pos] != 0xaa:
            is_aa = 0
        else:    
            is_aa += 1
            if is_aa == 4:
                break
    EOD_pos -= 2 # Skip CRC32
    # =====================================       
    # sensor data storage structure in BDT packet
    # =====================================
    #  16 bytes : packet header
    # =====================================
    #   4 bytes : start maker 0x55 0x55 0x55 0x55
    #  13 bytes : container
    # >>>>>>>>>>> repeat from
    #   5 bytes : Sensor type(1N) + TimeStamp(6N) + FIFO Len(3N)
    # 888 bytes : raw data
    # <<<<<<<<<<< repeat to
    #   2 bytes : CRC32
    #   4 bytes : end marker 0xaa 0xaa 0xaa 0xaa
    # =====================================
    #  16 bytes : packet footer
    # ====================================== 
    idx  = 16 # skip paket header
    # container information
    time_unix  = int.from_bytes(gBDTdata[idx+ 5:idx+ 9], byteorder='little', signed=True)
    time_delay = int.from_bytes(gBDTdata[idx+ 9:idx+13], byteorder='little', signed=True)
    ODR_adxl   = gBDTdata[idx+13]
    idx += 17 # skip start maker & container
    gBDTtextBlock  = ("server time    : %s(%d)\n" %  ( (datetime.datetime.fromtimestamp(float(time_unix)).strftime('%Y-%m-%d %H:%M:%S'), time_unix) ))
    gBDTtextBlock += ("delay time     : %.3f\n" % ( float(time_delay)/1000. ))
    gBDTtextBlock += ("accelometer ODR: %d Hz\n" % STE_FREQUENCY[ ODR_adxl ]) 
    gBDTtextBlock += (" Row #, Time-Stamp, X-AXIS, Y-AXIS, Z-AXIS\n")
    line = 1
    while (idx < EOD_pos):
        sensor_type =  gBDTdata[idx  ] & 0x0f
        time_stamp  = (gBDTdata[idx  ] & 0xf0) >> 4
        time_stamp +=  gBDTdata[idx+1] << 4
        time_stamp +=  gBDTdata[idx+2] << 12
        time_stamp += (gBDTdata[idx+3] & 0x0f) << 28
        data_len  = (gBDTdata[idx+3] & 0xf0) >> 4
        data_len +=  gBDTdata[idx+4] << 4
        idx += 5
        for n in range(data_len):
            if idx >= EOD_pos:
                break
            if (n == 0):
                ##gBDTtextBlock += ( "%6d, %10.3f" % (line,(float(time_stamp)/1000.)))
                gBDTtextBlock += ( "%d,%.3f" % (line,(float(time_stamp)/1000.)))                          
            elif (n % 3) == 0:
                line += 1
                ##gBDTtextBlock += ( "\n%6d,           " % line )
                gBDTtextBlock += ( "\n%d," % line )
            ##gBDTtextBlock += ( ", %6d" % (int.from_bytes(gBDTdata[idx:idx+2], byteorder='little', signed=True)) )
            gBDTtextBlock += ( ",%d" % (int.from_bytes(gBDTdata[idx:idx+2], byteorder='little', signed=True)) )
            idx += 2
        gBDTtextBlock += ( "\n" )     
    gBDTtextBlock += ("End of Data\n")
    gBDTtextLen = len(gBDTtextBlock)
    gBDTtextPos = 0
    #    
    print ("SCD> text block [%d] bytes recorded !" % gBDTtextLen, flush=True)

#############################################
# create text memory block from BDT w/o non-data
#
def SCD_BDT_get_text1024():
    global gBDTtextBlock
    global gBDTtextLen
    global gBDTtextPos

    if gBDTtextPos >= gBDTtextLen:
        rtn = 'End of Data\n'
        gBDTtextPos = idx = 0
    else:
        idx = gBDTtextPos + 1024    
        if idx > gBDTtextLen:
            idx = gBDTtextLen
        while ( gBDTtextBlock[idx-1:idx] != '\n' ) and ( idx > gBDTtextPos ):
            idx -= 1
        if idx > gBDTtextPos:
            rtn = gBDTtextBlock[gBDTtextPos:idx+1]
            gBDTtextPos = idx + 1
        else:
            rtn = ''
            gBDTtextPos += 1
    return rtn    
#
#############################################

#############################################
#############################################
#         
# Main starts here
#
if len(sys.argv) > 1:
    print ("WSN-C> take 1'st argument as Host IP address (default: '%s')" % TCP_HOST_NAME, flush=True)
    TCP_HOST_NAME = sys.argv[1]
if len(sys.argv) > 2:
    print ("WSN-C> take 2'nd argument as port# (default: '%d')" % TCP_PORT, flush=True)
    TCP_PORT = int(sys.argv[2])
#
# scan and connect SCD
#
p = SCD_scan_and_connect(True)
#
# set STE configuration
#
SCD_set_STE_config(p, False)
#
# read Device Info. such as Name, Manufacurer Name, etc.
#
SCD_print_info(p)
#
# check STE is rolling or not, memory is empty or not; stop rolling & cleanup memory
#
SCD_check_STE_rolling(p)
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
while gTCPrxMsg != TCP_DEV_CLOSE_MSG and gTCPnullRXcnt < 10:
    #
    # wait any message from server
    #
    print ("\nWSN-C> keep running until [%r] message from server ..." % TCP_DEV_CLOSE_MSG, flush=True)
    gTCPtxMsg = gTCPrxMsg = None
    try:
        loop.run_until_complete( tcp_RX(loop) )
    except ConnectionResetError:
        print ("WSN-C> server connection is broken !", flush=True)
        break
    #
    if gTCPrxMsg != None and gTCPrxMsg != '':
        #
        # process server message
        #
        if gTCPrxMsg == TCP_DEV_READY_MSG:
            # start STE rolling w/o memory writing
            print ("WSN-C> response to [%s]..." % TCP_DEV_READY_MSG, flush=True)
            gTCPtxMsg = TCP_DEV_READY_MSG
        elif gTCPrxMsg == TCP_STE_START_MSG:
            # start STE rolling w/o memory writing
            print ("WSN-C> start STE rolling...", flush=True)
            p.setDelegate( NotifyDelegate(p) )
            SCD_set_STE_config(p, False)
            SCD_toggle_STE_rolling(p, True, False)
            gIDLElastTime = time.time()
        elif gTCPrxMsg == TCP_STE_REQ_MSG:
            # request STE data
            if gSTEisRolling:
                print ("WSN-C> getting STE data ...", flush=True)
                # if not enable STE notification
                gSTElastData = p.readCharacteristic(SCD_STE_RESULT_HND)
                gSTElastTime = time.time()
                gTCPtxMsg = SCD_string_STE_data(gSTElastTime, gSTElastData)
                gIDLElastTime = gSTElastTime   
            else:
                print ("WSN-C> invalid message, STE has not been started !", flush=True)    
        elif gTCPrxMsg == TCP_BDT_RUN_MSG:
            # start BDT
            print ("WSN-C> start BDT running ...")
            if not (gSTEisRolling or gBDTisRolled):                
                SCD_run_STE_and_BDT(p)
                if SCD_clear_memory(p) == None:
                    p = SCD_scan_and_connect(False)
                SCD_BDT_text_block()
                gBDTisRolled = True    
                gIDLElastTime = time.time()
            else:
                print ("WSN-C> invalid message, BDT is not allowed during rolling !", flush=True)     
        elif gTCPrxMsg == TCP_BDT_REQ_MSG:
            # request BDT data
            if gBDTisRolled:
                print ("WSN-C> request BDT data ...", flush=True)
                gTCPtxMsg = SCD_BDT_get_text1024()
                if gTCPtxMsg.find("End") != -1:
                    gBDTisRolled = False
            else:
                print ("WSN-C> invalid message, BDT has not been done !", flush=True)    
        elif gTCPrxMsg == TCP_STE_STOP_MSG or gTCPrxMsg == TCP_DEV_CLOSE_MSG:
            # stop STE or disconnect
            print ("WSN-C> stop STE rolling ...", flush=True)
            SCD_set_STE_config (p, False)
            SCD_toggle_STE_rolling (p, False, False)
            SCD_print_STE_status()
            gIDLElastTime = time.time()
        else:
            # invalid message
            print ("WSN-C> invalid [RX] message !", flush=True)    
        if gTCPrxMsg == TCP_DEV_CLOSE_MSG:
            # exit from loop
            print ("WSN-C> close device ...", flush=True)
            break    
    #
    # idling check
    #
    t = time.time()
    if t - gIDLElastTime > gIDLEinterval:
        SCD_run_STE_for_idling(p)
        gIDLElastTime = t
    #
    # if any messae to send
    #
    if gTCPtxMsg != None:
        try:     
            loop.run_until_complete( tcp_TX(gTCPtxMsg, loop) )
        except ConnectionResetError:
            print ("WSN-C> server connection is broken !", flush=True)
            break;        
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
print ("WSN-C> all done ...", flush=True)
#
#############################################
