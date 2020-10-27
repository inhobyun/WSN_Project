"""
Code to test communication with blutooth ble device

This code does discover BOSCH SCD Sensor device via blutooth ble communication, read sensor data
followings are the steps included this code;
- discovery
- connect
- set STE configuration
- start STE(Short Time Experiment)
- stop STE
- start BDT(Block Data Transfer)
- stop BDT
- disconnect
- write BDT data to file

by Inho Byun, Researcher/KAIST
   inho.byun@gmail.com
                    started 2020-10-12
                    last updated 2020-10-26
"""
import sys
import time
import datetime
import struct
from bluepy.btle import Scanner, DefaultDelegate, UUID, Peripheral

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
STE_RUN_TIME     = 3.    # STE rolling time in secconds
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
gSTELastTime     = 0.    # notification last timestamp
gSTEData    = bytearray(33*512)

# BDT - Block Data Transfer
gBDTCount        = 0
gBDTStartTime    = 0.   
gBDTLastTime     = 0.
gBDTData   = bytearray(SCD_MAX_FLASH)
gBDTCRC32  = bytearray(4)

#############################################
# STE(Short Time Experiment) mode configuration (35 bytes) 
#############################################
#
STE_mode = bytearray(35)
STE_mode[ 0: 4]  = b'\x00\x00\x00\x00'  # [ 0~ 3] Unix time
#
mode  = 0xf0
mode |= 0x01 # 01 sensor En/Disable - accelerometer
#ode |= 0x02 # 02 sensor En/Disable - magnetometer
#ode |= 0x04 # 04 sensor En/Disable - light
#ode |= 0x08 # 08 sensor En/Disable - temperature
STE_mode[ 4: 5] = bytes(struct.pack('<h',mode))
#
mode  = 0x00 # ?0 data rate - accelerometer ODR 400Hz
#ode  = 0x01 # ?1 data rate - accelerometer ODR 800Hz
#ode  = 0x02 # ?2 data rate - accelerometer ODR 1600Hz
mode  = 0x03 # ?3 data rate - accelerometer ODR 3200Hz
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
mode |= 0x01 # 01 sensor raw value to flash - accelerometer
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
def print_STE_data( pResult ):

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
    # print    
    print ("A: X[%4.1f][%4.2f] Y[%4.1f][%4.2f] Z[%4.1f][%4.2f]g" %\
           ( adxl_mean_x, adxl_vari_x, adxl_mean_y, adxl_vari_y, adxl_mean_z, adxl_vari_z ), \
           end = '' \
          )
    print (" - T: [%4.2f]C" % temperature, end = '' )
    print (" - L: [%7.3f]lux" % light, end = '' )
    print (" - M: X[%5.1f] Y[%5.1f] Z[%5.1f]uT" % (magneto_x, magneto_y, magneto_z), end = '\n', flush = True )
    return

#############################################    
# print STE result
#
def print_STE_result( pResult ):
    global gSTEMode
    global gSTEStartTime
    global gSTELastTime

    # output time stamp
    tm = float( (struct.unpack('<l', gSTEMode[0:4]))[0] )   
    print ( "\tSTE config. time   : %s(%.3f)" \
            % (datetime.datetime.fromtimestamp(tm).strftime('%Y-%m-%d %H:%M:%S'), tm) )
    print ( "\tNotification Start : %s(%.3f)" \
            % (datetime.datetime.fromtimestamp(gSTEStartTime).strftime('%Y-%m-%d %H:%M:%S'), gSTEStartTime) )
    print ( "\tNotification End   : %s(%.3f)" \
            % (datetime.datetime.fromtimestamp(gSTELastTime).strftime('%Y-%m-%d %H:%M:%S'), gSTELastTime) )      
    print ("\t", end = '', flush = True )
    print_STE_data (pResult)
    return

#############################################
# print STE notify data
#
def print_STE_notify_data( pResult ):
    global gSTECount

    print("**** #%3d - " % gSTECount, end = '', flush = True)
    print_STE_data (pResult)
    return
  
#############################################
# Define scan callback
#############################################
class ScanDelegate(DefaultDelegate):
    
    def __init__(self):
        global gScannedCount

        DefaultDelegate.__init__(self)
        gScannedCount = 0
        print("**** Scanner Handler is configured", end='\n', flush = True)

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

        DefaultDelegate.__init__(self)
        print("**** Device Notification Handler is configured", end='\n', flush = True)
      
    def handleNotification(self, cHandle, data):
        global gSTECount
        global gSTEStartTime
        global gSTELastTime
        global gSTEStartData
        global gSTELastData
        global gBDTCount
        global gBDTStartTime
        global gBDTLastTime
        global gBDTData
        global gBDTCRC32

        if cHandle == SCD_STE_RESULT_HND:
        # STE notification
            if gSTECount == 0:
                gSTELastTime  = gSTEStartTime = time.time()
                gSTEStartData = data
            else:
                gSTELastTime = time.time()
                gSTELastData = data
            idx = int(data[32]) * 33
            gSTEData[idx:idx+33] = data[0:33]
            gSTECount += 1
        elif cHandle == SCD_BDT_DATA_FLOW_HND:
        # BDT notification
            #print("**** %2d-#%3d-[%s][%s]" % (cHandle, gSTECount, hex_str(data[0:4]),hex_str(data[4:20])), end='\n', flush = True)
            packet_no = int.from_bytes(data[0:4], byteorder='little', signed=False)
            if packet_no == 0:
                gBDTLastTime = gBDTStartTime = time.time()
                # header packet
                gBDTCount = int.from_bytes(data[4:8], byteorder='little', signed=False)
                gBDTData[0:16] = data[4:20]
            elif packet_no < gBDTCount-1:    
                # data packet
                idx = packet_no * 16
                gBDTData[idx:idx+16] = data[4:20]
            elif packet_no == gBDTCount-1:
                gBDTLastTime = time.time()
                # footer packet
                gBDTCRC32 = data[4:8]
                idx = packet_no * 16
                gBDTData[idx:idx+16] = data[4:20]
            else:
                print("**** BDT Packet No Error !... [%d] should less than [%d]" % (packet_no, gBDTCount), end='\n', flush = True)
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
    #
    # scanning for a while
    #
    scanner = Scanner().withDelegate(ScanDelegate())
    if is_first:
        print ("+--- BLE Device scan started..." )
    else:
        print ("+--- BLE Device scan restarted..." )    
    devices = scanner.scan(SCAN_TIME)
    print ("\n+--- BLE Device scan completed... [%d] devices are scanned" % gScannedCount)
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
                print("+--- Device address [%s], type=[%s], RSSI=[%d]dB" % (dev.addr, dev.addrType, dev.rssi))
                print("\tfound BOSCH SCD device!")
                gTargetDevice = dev
                break
        if gTargetDevice != None:
            break
    #
    # if none found then exiting    
    #
    if gTargetDevice == None:
        print("No matching device found... Exiting...")
        sys.exit(1)
    #
    # connect
    #
    print("+--- Connecting [%s], type=[%s]" % (gTargetDevice.addr, gTargetDevice.addrType))
    p = None
    retry = 0
    while p == None:
        try:
            p = Peripheral(gTargetDevice.addr, gTargetDevice.addrType)
        except:
            print("BLE Device connection error occured... Retry after 3 sec...")
            retry += 1
            if retry > 3:
                print("BLE Device connection error occured... Exiting...")
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
    print("+--- Set STE mode")
    p.writeCharacteristic( SCD_SET_MODE_HND, b'\x00' )
    ret_val = p.readCharacteristic( SCD_SET_MODE_HND )
#############################################
#
# set STE Configuration
#
time_bytes = struct.pack('<l', int(time.time()))
gSTEMode = bytes( time_bytes[0:4] ) + gSTEMode[4:35]
##print ("\tSTE config. set\n[%s](%d)" % (hex_str(gSTEMode), len(gSTEMode)))
p.writeCharacteristic( SCD_STE_CONFIG_HND, gSTEMode )
time.sleep(1.)
ret_val = p.readCharacteristic( SCD_STE_CONFIG_HND )
print ("\tSTE config. get\n[%s](%d)" % (hex_str(ret_val), len(ret_val)))
#############################################
#
# start STE
#
print ("+--- STE Starting...")
p.setDelegate( NotifyDelegate(p) )
p.writeCharacteristic( SCD_STE_RESULT_HND+1, struct.pack('<H', 1))
time.sleep(0.7)
p.writeCharacteristic( SCD_SET_GEN_CMD_HND, b'\x20' )
time_start = time.time()
while True:
    wait_flag = p.waitForNotifications(1.)
    time_stop = time.time()
    if (time_stop-time_start) > STE_RUN_TIME:
        print ( "\n\t[done] STE time exceeded", end = '\n', flush = True )
        p.writeCharacteristic( SCD_SET_GEN_CMD_HND, b'\x20' )
        print ("\tSTE is stopping")
        break
#############################################
#
# stop STE
#
ret_val = p.readCharacteristic( SCD_SET_GEN_CMD_HND )
while ( ret_val != b'\x00' ):
    print ("\tSTE has not completed yet, generic command is [%s]" % ret_val.hex())
    time.sleep(0.7)
    ret_val = p.readCharacteristic( SCD_SET_GEN_CMD_HND )
print ("\n+--- STE Stoped...rolling time [%.3f], count [%d]" % ( (gSTELastTime-gSTEStartTime), gSTECount))
print_STE_result(gSTELastData)
#
#############################################

#############################################
#
# bulk data transfer 
#
#############################################
print ("+--- Bulk Data Transfer after a while")
time.sleep(3.0)
p.setDelegate( NotifyDelegate(p) )
print ("+--- BDT Starting...")
time.sleep(0.7)
p.writeCharacteristic( SCD_BDT_DATA_FLOW_HND+1, struct.pack('<H', 1) )
time.sleep(0.7)
p.writeCharacteristic( SCD_BDT_CONTROL_HND, b'\x01' )
ret_val = b'x01'
while ret_val == b'x01':  
    wait_flag = p.waitForNotifications(15.)
    if wait_flag :
        continue
    ret_val = p.readCharacteristic( SCD_BDT_STATUS_HND )
time.sleep(0.7)
print ("\n+--- Bulk Data Transfer completed...status is [%s], time [%.3f], count [%d]" % \
       (ret_val.hex(), (gBDTLastTime-gBDTStartTime), gBDTCount) )
#############################################
#
# clean-up and init sensor device
#
p.writeCharacteristic( SCD_SET_GEN_CMD_HND, b'\x21' ) # reset threshold flag
time.sleep(0.7)
##p.writeCharacteristic( SCD_SET_MODE_HND, b'\xFF' )    # mode selection
##time.sleep(0.7)
p.writeCharacteristic( SCD_SET_GEN_CMD_HND, b'\x30' ) # erase sensor data
print ("+--- Erase flash wait for seconds...wait...")
time.sleep(10.)
#
# disconnect
#
p.disconnect()
#
#############################################

#############################################
#
# write flash dump time series data file
#
'''
print ("+--- Save packet to binary file...")
file_path  = "SCD_log_"
file_path += datetime.datetime.fromtimestamp(gSTEStartTime).strftime('%Y-%m-%d_%H-%M-%S')
file_path += ".bin"
try:
    f = open(file_path, "xb")
except:
    print ("\tfile error!")   
if f != None:
    for i in range(0, gBDTCount):
        f.write ( gBDTData[i*16:i*16+16] )
    f.close()
#
############################################
#
print ("+--- Save packet to decimal text file...")
file_path  = "SCD_Dec_log_"
file_path += datetime.datetime.fromtimestamp(gSTEStartTime).strftime('%Y-%m-%d_%H-%M-%S')
file_path += ".csv"
try:
    f = open(file_path, "x")
except:
    print ("\tfile error!")   
if f != None:
    f.write ("accelometer ODR: %d Hz\n" % STE_FREQUENCY[ int(gSTEMode[5]) & 0xf ])
    f.write ("total # of rows: %d\n" % (gBDTCount-1))            
    f.write (" Row #,     01,     02,     03,     04,     05,     06,     07,     08\n")
    for i in range(0, gBDTCount):
        f.write ( "%6d" % i )
        for j in range(i*16, i*16+16, 2):
            f.write ( ", %6d" % int.from_bytes(gBDTData[j:j+2], byteorder='little', signed=True))
        f.write ( "\n" )    
    f.write ("End of Data")    
    f.close()
#
############################################
'''
#
print ("+--- Save packet to hexa text file (w/ non-data)...")
file_path  = "SCD_Hex_log_"
file_path += datetime.datetime.fromtimestamp(gSTEStartTime).strftime('%Y-%m-%d_%H-%M-%S')
file_path += ".csv"
try:
    f = open(file_path, "x")
except:
    print ("\tfile error!")   
if f != None:
    f.write ("accelometer ODR: %d Hz\n" % STE_FREQUENCY[ int(gSTEMode[5]) & 0xf ])
    f.write ("total # of rows: %d\n" % (gBDTCount-1))            
    f.write (" Row #, 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12, 13, 14, 15, 16\n")
    for i in range(0, gBDTCount):
        text_line = ''.join([', ' + ch if j % 2 == 0 and j != 0 else ch for j, ch in enumerate(gBDTData[i*16:i*16+16].hex())])
        f.write ( "  %04x, %s\n" % ( i, text_line ))
    f.write ("End of Data")    
    f.close()
#
#########################################
#
print ("+--- Save data to decimal text file (w/o non-data)...")
file_path  = "SCD_log_"
file_path += datetime.datetime.fromtimestamp(gSTEStartTime).strftime('%Y-%m-%d_%H-%M-%S')
file_path += ".csv"
try:
    f = open(file_path, "x")
except:
    print ("\tfile error!")
if f != None:
    # find EOD(End-of-Data: 0xaaaa, 0xaaaa)
    is_aa = 0
    for EOD_pos in range((gBDTCount+1)*16, (gBDTCount-3)*16, -1):
        if gBDTData[EOD_pos] != 0xaa:
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
    time_unix  = int.from_bytes(gBDTData[idx+ 5:idx+ 9], byteorder='little', signed=True)
    time_delay = int.from_bytes(gBDTData[idx+ 9:idx+13], byteorder='little', signed=True)
    ODR_adxl   = gBDTData[idx+13]
    idx += 17 # skip start maker & container
    f.write ("server time    : %s(%d)\n" %  ( (datetime.datetime.fromtimestamp(float(time_unix)).strftime('%Y-%m-%d %H:%M:%S'), time_unix) ))
    f.write ("delay time     : %.3f\n" % ( float(time_delay)/1000. ))
    f.write ("accelometer ODR: %d Hz\n" % STE_FREQUENCY[ ODR_adxl ]) 
    f.write (" Row #, Time-Stamp, X-AXIS, Y-AXIS, Z-AXIS\n")
    line = 1
    while (idx < EOD_pos):
        sensor_type =  gBDTData[idx  ] & 0x0f
        time_stamp  = (gBDTData[idx  ] & 0xf0) >> 4
        time_stamp +=  gBDTData[idx+1] << 4
        time_stamp +=  gBDTData[idx+2] << 12
        time_stamp += (gBDTData[idx+3] & 0x0f) << 28
        data_len  = (gBDTData[idx+3] & 0xf0) >> 4
        data_len +=  gBDTData[idx+4] << 4
        idx += 5
        for n in range(data_len):
            if idx >= EOD_pos:
                break
            if (n == 0):
                f.write ( "%6d, %10.3f" % (line,(float(time_stamp)/1000.)))                          
            elif (n % 3) == 0:
                line += 1
                f.write ( "\n%6d,           " % line )
            f.write ( ", %6d" % (int.from_bytes(gBDTData[idx:idx+2], byteorder='little', signed=True)) )
            idx += 2
        f.write ( "\n" )     
    f.write ("End of Data")    
    f.close()
#    
print ("+--- data recorded...all done !")
#
#
#############################################
