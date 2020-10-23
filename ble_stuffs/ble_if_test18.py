"""
Code to test communication with blutooth ble device

This code does discover BOSCH SCD Sensor device via blutooth ble communication, read sensor data
followings are the steps included this code;
- discovery
- connect
- set mode
- set STE configuration
- start STE(Short Time Experiment)
- stop STE
- get flash memory dump
- write dump to a file
- disconnect

by Inho Byun, Researcher/KAIST
   inho.byun@gmail.com
                    started 2020-10-12
                    last updated 2020-10-23
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
SCD_DEVICE_NAME_HND     = 3     # R,  uuid: 00002a00-0000-1000-8000-00805f9b34fb
SCD_SYSTEM_ID_HND       = 11    # R,  uuid: 00002a23-0000-1000-8000-00805f9b34fb
SCD_SERIAL_NUM_HND      = 13    # R,  uuid: 00002a25-0000-1000-8000-00805f9b34fb
SCD_FW_REVISION_HND     = 15    # R,  uuid: 00002a26-0000-1000-8000-00805f9b34fb
SCD_HW_REVISION_HND     = 17    # R,  uuid: 00002a27-0000-1000-8000-00805f9b34fb
SCD_SW_REVISION_HND     = 19    # R,  uuid: 00002a28-0000-1000-8000-00805f9b34fb
SCD_MANUFA_NAME_HND     = 21    # R,  uuid: 00002a29-0000-1000-8000-00805f9b34fb
SCD_IF_VERSION_HND      = 24    # R,  uuid: 02a65821-0001-1000-2000-b05cb05cb05c
SCD_TEST_RESULT_HND     = 26    # R,  uuid: 02a65821-0002-1000-2000-b05cb05cb05c
SCD_SET_MODE_HND        = 28    # RW, uuid: 02a65821-0003-1000-2000-b05cb05cb05c
SCD_SET_GEN_CMD_HND     = 30    # RW, uuid: 02a65821-0004-1000-2000-b05cb05cb05c
SCD_STE_CONFIG_HND      = 35    # RW, uuid: 02a65821-1001-1000-2000-b05cb05cb05c
SCD_STE_RESULT_HND      = 37    # RN, uuid: 02a65821-1002-1000-2000-b05cb05cb05c
SCD_BDT_CONTROL_HND     = 41    # W,  uuid: 02a65821-3001-1000-2000-b05cb05cb05c
SCD_BDT_STATUS_HND      = 43    # R,  uuid: 02a65821-3002-1000-2000-b05cb05cb05c
SCD_BDT_DATA_FLOW_HND   = 45    # RN, uuid: 02a65821-3003-1000-2000-b05cb05cb05c
#
# MAX constant of BOSCH SCD
#
SCD_MAX_MTU     = 65                # MAX SCD Comm. Packet size
SCD_MAX_FLASH   = 0x0b0000          # 720896, 11*16**4)
SCD_MAX_NOTIFY  = SCD_MAX_FLASH>>4  # int(SCD_MAX_FLASH / 16)

#
# Some constant parameters
#
SCAN_TIME           = 8.    # scanning duration for BLE devices 
STE_RUN_TIME        = 1.    # STE rolling time in secconds
STE_RUN_COUNT       = ( 23, 47, 94, 188, 376 )  # of STE result 400 / 800 / 1600 / 3200 / 6400 Hz
MAX_STE_RUN_TIME    = 30.   # max STE rolling time in seconds
#
# global variables
#
gTargetDevice       = None  # target device object 
gScannedCount       = 0     # count of scanned BLE devices
gTargetAddr         = ""    # address of target device
gTargetAddrType     = ""    # address type of target device
gNotifyCount        = 0     # count of notifications from connected device
gNotifyStartTime    = 0.    # notification start timestamp
gNotifyLastTime     = 0.    # notification last timestamp
gNotifyLastData     = bytes(33)     # STE vResult data
gTargetSTEmode      = bytes(35)     # Sensor Mode
#
# SCD flash memeory block
# MAX: 0x0b0000 bytes = 45056 x 16 bytes packet
#
gSCDflashCount      = 0
gSCDflashPacket     = bytearray(SCD_MAX_FLASH)

#############################################
# STE(Short Time Experiment) mode configuration (35 bytes) 
#############################################
#
STE_mode = bytearray(35)
STE_mode[ 0: 4]  = b'\x00\x00\x00\x00'  # [ 0~ 3] Unix time
#
mode  = 0xf1 # 01 sensor En/Disable - accelerometer
#ode |= 0x02 # 02 sensor En/Disable - magnetometer
#ode |= 0x04 # 04 sensor En/Disable - light
#ode |= 0x08 # 08 sensor En/Disable - temperature
STE_mode[ 4: 5] = bytes(struct.pack('<h',mode))
#
#ode  = 0x00 # ?0 data rate - accelerometer ODR 400Hz
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
gTargetSTEmode = bytes(STE_mode[0:35])
                  
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
def print_STE_data( vResult ):

# output Accelerrometer X, Y, Z axis arithmetic mean & variation  
    accel_mean_x = float( int.from_bytes(vResult[0:2], byteorder='little', signed=True) ) \
                  / 10.0
    accel_vari_x = float( int.from_bytes(vResult[6:10], byteorder='little', signed=True) ) \
                   / 100.0
    accel_mean_y = float( int.from_bytes(vResult[2:4], byteorder='little', signed=True) ) \
                  / 10.0
    accel_vari_y = float( int.from_bytes(vResult[10:14], byteorder='little', signed=True) ) \
                   / 100.0
    accel_mean_z = float( int.from_bytes(vResult[4:6], byteorder='little', signed=True) ) \
                  / 10.0
    accel_vari_z = float( int.from_bytes(vResult[14:18], byteorder='little', signed=True) ) \
                   / 100.0
# output temperature
    temperature = float( int.from_bytes(vResult[18:20], byteorder='little', signed=True) ) \
                  * 0.0078
# output light
    light = float( int.from_bytes(vResult[20:24], byteorder='little', signed=True) )
# output Magnetometer X, Y, Z axis raw data 
    magneto_x = float( int.from_bytes(vResult[24:26], byteorder='little', signed=True) ) \
                  / 16.0
    magneto_y = float( int.from_bytes(vResult[26:28], byteorder='little', signed=True) ) \
                  / 16.0
    magneto_z = float( int.from_bytes(vResult[28:30], byteorder='little', signed=True) ) \
                  / 16.0
# print    
    print ("A: X[%4.1f][%4.2f] Y[%4.1f][%4.2f] Z[%4.1f][%4.2f] g" %\
           ( accel_mean_x, accel_vari_x, accel_mean_y, accel_vari_y, accel_mean_z, accel_vari_z
           ), \
           end = '' \
          )
    print (" - T: [%4.2f]C" % temperature, end = '' )
    print (" - L: [%7.3f] lux" % (light/1000.), end = '' )
    print (" - M: X[%5.1f] Y[%5.1f] Z[%5.1f] uT" % (magneto_x, magneto_y, magneto_z), end = '\n', flush = True )
    return

#############################################    
# print STE result
#
def print_STE_result( vResult ):
    global gTargetSTEmode
    global gNotifyStartTime
    global gNotifyLastTime

# output time stamp
    tm = float( (struct.unpack('<l', gTargetSTEmode[0:4]))[0] )   
    print ( "\tSTE config. time   : %s(%.3f)" \
            % (datetime.datetime.fromtimestamp(tm).strftime('%Y-%m-%d %H:%M:%S'), tm) )
    print ( "\tNotification Start : %s(%.3f)" \
            % (datetime.datetime.fromtimestamp(gNotifyStartTime).strftime('%Y-%m-%d %H:%M:%S'), gNotifyStartTime) )
    print ( "\tNotification End   : %s(%.3f)" \
            % (datetime.datetime.fromtimestamp(gNotifyLastTime).strftime('%Y-%m-%d %H:%M:%S'), gNotifyLastTime) )      
    print ("\t")
    print_STE_data (vResult)
    return

#############################################
# print STE notify data
#
def print_STE_notify_data( vResult ):
    global gNotifyCount

    print("**** #%3d -" % gNotifyCount, end = '', flush = True)
    print_STE_data (vResult)
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
        global gNotifyCount
        global gNotifyStartTime
        global gNotifyLastTime
        global gNotifyLastData

        DefaultDelegate.__init__(self)
        gNotifyCount = 0
        gNotifyLastTime = gNotifyStartTime = time.time()
        print("**** Device Notification Handler is configured", end='\n', flush = True)
      
    def handleNotification(self, cHandle, data):
        global gNotifyCount
        global gNotifyStartTime
        global gNotifyLastTime
        global gNotifyLastData
        global gSCDflashCount
        global gSCDflashPacket

        if gNotifyCount < 1:
            gNotifyLastTime = gNotifyStartTime = time.time()
        else:
            gNotifyLastTime = time.time()
        gNotifyLastData = data    
        gNotifyCount += 1
        if cHandle == SCD_STE_RESULT_HND:
            print_STE_notify_data ( data )
        elif cHandle == SCD_BDT_DATA_FLOW_HND:
            #print("**** >" if gNotifyCount==1 else ">", end='', flush=True)
            #gSCDflashCount = gNotifyCount
            #idx = gSCDflashCount*16
            #gSCDflashPacket[idx:idx+16] = data[4:20]
            print("**** %2d-#%3d-[%s][%s]" % (cHandle, gNotifyCount, hex_str(data[0:4]),hex_str(data[4:20])), end='\n', flush = True)
        else:
            print("**** %2d-#%3d-[%s]" % (cHandle, gNotifyCount, hex_str(data)), end='\n', flush = True)

#############################################
#############################################
#         
# Main starts here
#
#############################################
#############################################
#
# scanning for a while
#
scanner = Scanner().withDelegate(ScanDelegate())
print ("+--- BLE Device scan started..." )
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
gTargetAddr = gTargetDevice.addr
gTargetAddrType = gTargetDevice.addrType
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
#
# read Device Name, Manufacurer Name
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
print ("\tFW Revision is [%s]" % ret_val.decode("utf-8"))
#
ret_val = p.readCharacteristic( SCD_HW_REVISION_HND )
print ("\tHW Revision is [%s]" % ret_val.decode("utf-8"))
#
ret_val = p.readCharacteristic( SCD_SW_REVISION_HND )
print ("\tSW Revision is [%s]" % ret_val.decode("utf-8"))
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
ret_val = p.readCharacteristic( SCD_STE_CONFIG_HND )
print ("\tFlash memory remain is [%s] MAX:0b0000" % ret_val[31:34].hex())
'''
if (struct.unpack('i', ret_val[31:35]))[0] < SCD_MAX_FLASH:
    print ("\t\t=> flash memory is not empty...cleanning-up flash and re-connect device")
    p.writeCharacteristic( SCD_SET_GEN_CMD_HND, b'\x30' ) # erase sensor data
    print ("+--- Erase flash wait for seconds...")
    time.sleep(0.7)
    p.disconnect()
    time.sleep(10.)
    p = Peripheral(gTargetAddr, gTargetAddrType)
'''    
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
gTargetSTEmode = bytes( time_bytes[0:4] ) + gTargetSTEmode[4:35]
print ("\tSTE config. was\n[%s](%d)" % (hex_str(gTargetSTEmode), len(gTargetSTEmode)))
p.writeCharacteristic( SCD_STE_CONFIG_HND, gTargetSTEmode )
time.sleep(1.)
ret_val = p.readCharacteristic( SCD_STE_CONFIG_HND )
print ("\tSTE config. is \n[%s](%d)" % (hex_str(ret_val), len(ret_val)))
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
    wait_flag = p.waitForNotifications(3.)
    time_stop = time.time()
    if (time_stop-time_start) > STE_RUN_TIME:
        print ( "\n\t[done] STE time exceeded", end = '\n', flush = True )
        p.writeCharacteristic( SCD_SET_GEN_CMD_HND, b'\x20' )
        print ("\n+--- STE Stopped")
        break
    if wait_flag:
        ##print ( "\t~", end = '\n', flush = True )
        continue
#############################################
#
# stop STE
#
while True:
    wait_flag = p.waitForNotifications(1.)
    time_stop = time.time()
    if (time_stop-time_start) > MAX_STE_RUN_TIME:
        break
    if gNotifyCount > ( STE_RUN_COUNT[ (gTargetSTEmode[5]&0x0f) ] * STE_RUN_TIME ):
        break
ret_val = p.readCharacteristic( SCD_SET_GEN_CMD_HND )
while ( ret_val != b'\x00' ):
    ##print ("\tSTE has not completed yet, generic command is [%s]" % ret_val.hex())
    time.sleep(0.7)
    ret_val = p.readCharacteristic( SCD_SET_GEN_CMD_HND )
print ("\n+--- STE Notification Completed")

#############################################
#
# output rolling time & count
#    
ret_val = p.readCharacteristic( SCD_STE_CONFIG_HND )
print ("+--- Last notification data is as below...rolling Time [%.3f], Count [%d]"\
	% ( (gNotifyLastTime-gNotifyStartTime), gNotifyCount))
print ("\t     [%s]" % hex_str(gNotifyLastData))
print_STE_result(gNotifyLastData)
#############################################
#
# bulk data transfer 
#
#############################################
print ("+--- Bulk Data Transfer after a while")
time.sleep(3.0)
p.setDelegate( NotifyDelegate(p) )
print ("\tStarting...")
time.sleep(0.7)
p.writeCharacteristic( SCD_BDT_DATA_FLOW_HND+1, struct.pack('<H', 1) )
time.sleep(0.7)
p.writeCharacteristic( SCD_BDT_CONTROL_HND, b'\x01' )
while True:  
    wait_flag = p.waitForNotifications(3.)
    ret_val = p.readCharacteristic( SCD_BDT_STATUS_HND )
    if ret_val != b'x01':
        break
time.sleep(5.0)
p.waitForNotifications(5.)
print ("\n+--- Bulk Data Transfer completed...status is [%s] packet count: [%d]" \
       % (ret_val.hex(), gNotifyCount), end = '\n', flush = True)

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
"""
#############################################
#
# write flash dump time series data file
#
print ("+--- Save flash dump data to file...")
file_path  = "SCD_flash_dump_"
file_path += datetime.datetime.fromtimestamp(gNotifyStartTime).strftime('%Y-%m-%d_%H:%M:%S')
file_path += ".csv"
n = 1
try:
    f = open(file_path, "x")
except:
    print ("\tfile error!")
if f != None:
    for i in range(0, gSCDflashCount+16, 16):
        for j in range(0, 16, 2):
            idx = i*16 + j
            val_b = gSCDflashPacket[idx: idx+2]
            val_i = int.from_bytes(val_b, byteorder='little', signed=True)
            val_f = float ( val_i ) / 10.
            f.write ( "%5.1f" % val_f )
            f.write ( "," if n%3 != 0 else "\r\n" )
            n += 1
    f.write ("total %d line recorded" % n)            
    f.close()
print ("+--- all done !")
#
#############################################
"""
