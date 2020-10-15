"""
Code to test communication with blutooth ble device

This code does discover BOSCH SCD Sensor device via blutooth ble communication, and read sensor data
followings are the steps in this code;
- discovery
- connect
- set mode
- set STE configuration
- start STE
- stop STE
- get STE result

by Inho Byun
started 2020-10-12
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
#
# service UUID -- not using in this code
#
SCD_DEVICE_NAME_HND  = 3
SCD_MANUFA_NAME_HND  = 21
SCD_TEST_RESULT_HND  = 26
SCD_SET_MODE_HND     = 28
SCD_SET_GEN_CMD_HND  = 30
SCD_STE_CONFIG_HND   = 35
SCD_STE_RESULT_HND   = 37
#
# MTU
#
SCD_MAX_MTU = 65
#
# global variables
#
SCAN_TIME       = 8.
scanned_count   = 0
target_device   = None
target_STE_mode = bytes(35) 
MAX_STE_ROLL_TIME   = 10. # seconds
#
# STE configuration
#
STE_mode = bytearray(35)
STE_mode[ 0: 4]  = b'\x00\x00\x00\x00'  # [ 0~ 3] Unix time
#
STE_bits_pattern = 240                  # [    4] F0 sensor En/Disable - reserved
STE_bits_pattern+= 1                    # [    4] 01 sensor En/Disable - accelerometer
STE_bits_pattern+= 2                    # [    4] 02 sensor En/Disable - magnetometer
STE_bits_pattern+= 4                    # [    4] 04 sensor En/Disable - light
STE_bits_pattern+= 8                    # [    4] 08 sensor En/Disable - temperature
STE_mode[ 4: 5] = struct.pack('<h',STE_bits_pattern)

#
#TE_bits_pattern = 0                    # [    5] ?0 data rate - accelerometer ODR 400Hz
#TE_bits_pattern = 1                    # [    5] ?1 data rate - accelerometer ODR 800Hz
#TE_bits_pattern = 2                    # [    5] ?2 data rate - accelerometer ODR 1600Hz
#TE_bits_pattern = 3                    # [    5] ?3 data rate - accelerometer ODR 3200Hz
STE_bits_pattern = 4                    # [    5] ?4 data rate - accelerometer ODR 6400Hz
#TE_bits_pattern+= 0                    # [    5] 0? data rate - light sensor ODR 100ms(10Hz)
#TE_bits_pattern+= 16                   # [    5] 1? data rate - light sensor ODR 800ms(1.25Hz)
STE_bits_pattern+= 192                  # [    5] C0 reserved
STE_mode[ 5: 6] = struct.pack('<h',STE_bits_pattern)
#
STE_mode[ 6: 8]  = b'\xE4\x07'          # [ 6~ 7] accelerometer threshold
STE_mode[12:16]  = b'\x00\x00\x00\x00'  # [12~15] light sensor threshold low
STE_mode[16:20]  = b'\xE8\xE4\xF5\x05'  # [16~19] light sensor threshold high
STE_mode[20:22]  = b'\x80\x57'          # [20~21] magnetometer threshold
STE_mode[26:28]  = b'\x80\xF3'          # [26~27] temperature threshold low
STE_mode[28:30]  = b'\x00\x2D'          # [28~29] temperature threshold high
#
STE_bits_pattern = 240                  # [   30] F0 sensor raw value to flash
#TE_bits_pattern+= 1                    # [   30] 01 sensor raw value to flash - accelerometer
#TE_bits_pattern+= 2                    # [   30] 02 sensor raw value to flash - magnetometer
#TE_bits_pattern+= 4                    # [   30] 04 sensor raw value to flash - light
#TE_bits_pattern+= 8                    # [   30] 08 sensor raw value to flash - temperature
STE_mode[30:31] = struct.pack('<h',STE_bits_pattern)
#
target_STE_mode = bytes( STE_mode[0:35] )
                  
#############################################
# Define scan callback
#############################################
class ScanDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleDiscovery(self, dev, isNewDev, isNewData):
        global scanned_count
        if isNewDev:
            scanned_count += 1
            print ('>', end='', flush = True) #print("Discovered device [%s]" % dev.addr)
        elif isNewData:
            print ('-', end='', flush = True) #print("Received new data from [%s]" % dev.addr)

#############################################
# Define notification callback
#############################################
class NotifyDelegate(DefaultDelegate):
    def __init__(self, params):
        DefaultDelegate.__init__(self)
      
    def handleNotification(self, cHandle, data):
         print("Handle:", cHandle, ", Notification: [", data, "]", end='\n', flush = True)

#############################################
# Define functions
#############################################
#
# convert hex() string to "XX.XX"
#
def hex_str( vBytes ):    
    vString = ''.join(['.' + ch if i % 2 == 0 and i != 0 else ch for i, ch in enumerate(vBytes.hex())])
    return vString
#
# output STE result
#
def output_STE_result( result ):
    global target_STE_mode

    print ( "\tSTE configuration time stamp: ", end = '')
    t = ''.join(map(str, struct.unpack('f', target_STE_mode[0:4])))   
    print ( datetime.datetime.fromtimestamp \
            ( int( (t.split('.'))[0] ) \
            ).strftime('%Y-%m-%d %H:%M:%S') \
          )
                   
    print ("\tSTE result is\n[%s]\n\tsize is [%d]" % (hex_str(result), len(result)))
# output Accelerrometer X, Y, Z axis arithmetic mean & variation  
    accel_mean_x = float( int.from_bytes(result[0:2], byteorder='little', signed=True) ) \
                  / 10.0
    accel_vari_x = float( int.from_bytes(result[6:10], byteorder='little', signed=True) ) \
                   / 100.0
    print ("+--- Accel mean X raw data is [%4s]\t=> [%.1f] g, variation [%.2f] g^2" \
           % (hex_str(result[0:2]), accel_mean_x, accel_vari_x) )
    accel_mean_y = float( int.from_bytes(result[2:4], byteorder='little', signed=True) ) \
                  / 10.0
    accel_vari_y = float( int.from_bytes(result[10:14], byteorder='little', signed=True) ) \
                   / 100.0
    print ("+--- Accel mean Y raw data is [%4s]\t=> [%.1f] g, variation [%.2f] g^2" \
           % (hex_str(result[2:4]), accel_mean_y, accel_vari_y) )
    accel_mean_z = float( int.from_bytes(result[4:6], byteorder='little', signed=True) ) \
                  / 10.0
    accel_vari_z = float( int.from_bytes(result[14:18], byteorder='little', signed=True) ) \
                   / 100.0
    print ("+--- Accel mean Z raw data is [%4s]\t=> [%.1f] g, variation [%.2f] g^2" \
           % (hex_str(result[4:6]), accel_mean_z, accel_vari_z) )
# output temperature
    temperature = float( int.from_bytes(result[18:20], byteorder='little', signed=True) ) \
                  * 0.0078
    print ("+--- Temperature raw data is [%4s]\t=> [%.2f] C" \
           % (hex_str(result[18:20]), temperature) )
# output light
    light = float( int.from_bytes(result[20:24], byteorder='little', signed=True) )
    print ("+--- Light raw data is [%s]\t=> [%.3f] lux" \
           % (hex_str(result[20:24]), light/1000.) )
# output Magnetometer X, Y, Z axis raw data 
    magneto_x = float( int.from_bytes(result[24:26], byteorder='little', signed=True) ) \
                  / 16.0
    print ("+--- Magneto X raw data is [%s]\t=> [%.1f] uT" \
           % (hex_str(result[24:26]), magneto_x) )
    magneto_y = float( int.from_bytes(result[26:28], byteorder='little', signed=True) ) \
                  / 16.0
    print ("+--- Magneto Y raw data is [%s]\t=> [%.1f] uT" \
           % (hex_str(result[26:28]), magneto_y) )
    magneto_z = float( int.from_bytes(result[28:30], byteorder='little', signed=True) ) \
                  / 16.0
    print ("+--- Magneto Z raw data is [%s]\t=> [%.1f] uT" \
           % (hex_str(result[28:30]), magneto_z) )
    return

#############################################
#############################################
#         
# Main starts here
#
#############################################
#############################################

#
# Scanning for a while
#
scanner = Scanner().withDelegate(ScanDelegate())
print ("BLE Device scan started..." )
devices = scanner.scan(SCAN_TIME)
print ("\nBLE Device scan completed... [%d] devices are scanned" % scanned_count)

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
            target_device = dev
            break
    if target_device != None:
        break
#
# if none found then exiting    
#
if target_device == None:
    print("No matching device found... Exiting...")
    sys.exit(1)

#
# connect
#
print("+--- Connecting [" + target_device.addr + "] type=[" + target_device.addrType + "] ...")
p = None
retry = 0
while p == None:
    try:
        p = Peripheral(target_device.addr, target_device.addrType)
    except:
        print("BLE Device connection error occured... Retry after 3 sec...")
        retry += 1
        time.sleep(3)
        if retry > 3:
            print("BLE Device connection error occured... Exiting...")
            sys.exit(-1)
          
p.setMTU(SCD_MAX_MTU)
p.setDelegate( NotifyDelegate(p) )

#
# read Device Name, Manufacurer Name
#
ret_val = p.readCharacteristic( SCD_DEVICE_NAME_HND )
print("\tDevice Name is [" + ret_val.decode("utf-8") + "]")
ret_val = p.readCharacteristic( SCD_MANUFA_NAME_HND )
print("\tManufacturer Name is [" + ret_val.decode("utf-8") + "]")
ret_val = p.readCharacteristic( SCD_TEST_RESULT_HND )
print("\tSelf Test Result is [" + ret_val.hex() + "]")

#############################################
#
# check Mode to set STE Mode
#
ret_val = p.readCharacteristic( SCD_SET_MODE_HND )
print("\tMode is [" + ret_val.hex() + "]")
if ret_val !=  b'\x00': # if not STE mode
    print("+--- Set STE mode")
    p.writeCharacteristic( SCD_SET_MODE_HND, b'\x00' )
    ret_val = p.readCharacteristic( SCD_SET_MODE_HND )
    print("\tMode is [" + ret_val.hex() + "]")

#
# set STE Configuration
#
time_bytes = bytearray(4)
time_bytes = struct.pack('<f', time.time())
target_STE_mode = bytes( time_bytes[0:4] ) + target_STE_mode[4:35]
p.writeCharacteristic( SCD_STE_CONFIG_HND, target_STE_mode )
ret_val = p.readCharacteristic( SCD_STE_CONFIG_HND )
hex_string = hex_str( ret_val )
print("\tSTE configuration is\n[%s]\n\tsize is [%d]" % (hex_string, len(ret_val)))
ret_val = p.readCharacteristic( SCD_TEST_RESULT_HND )
print("\tSelf Test Result is [" + ret_val.hex() + "]")


#
# start STE and stop after a while
#
print("+--- STE Starting...")
p.writeCharacteristic( SCD_SET_GEN_CMD_HND, b'\x20' )
time_start = time.time()
time_stop = time_start
ret_val = p.readCharacteristic( SCD_STE_RESULT_HND )
print("\tSTE runinug, rolling count is ", end='', flush = True)
while (time_stop - time_start) < MAX_STE_ROLL_TIME:
    print("[%2d] " % int(ret_val[32]), end='', flush = True)
    time_stop = time.time()
    if int(ret_val[32]) > 1:
        STE_result_0 = ret_val
        print( "." )
        break
    time.sleep(.05)
    ret_val = p.readCharacteristic( SCD_STE_RESULT_HND )
p.writeCharacteristic( SCD_SET_GEN_CMD_HND, b'\x20' )
ret_val = p.readCharacteristic( SCD_SET_GEN_CMD_HND )
while ( ret_val != b'\x00' ):
    print("\tSTE has not completed yet, generic command is [" + ret_val.hex() + "]")
    time.sleep(.05)
    ret_val = p.readCharacteristic( SCD_SET_GEN_CMD_HND )
STE_result_1 = p.readCharacteristic( SCD_STE_RESULT_HND )
#
# output tolling time & count
#    
print ("+--- STE Stopped... rolling Time [%.3f], Counter [%d]" % (time_stop-time_start, int(STE_result_0[32])))
output_STE_result(STE_result_1)

#############################################
#
# clean-up and init sensor device
#
p.writeCharacteristic( SCD_SET_GEN_CMD_HND, b'\x21' ) # reset threshold flag
p.writeCharacteristic( SCD_SET_MODE_HND, b'\xFF' )    # mode selection
p.writeCharacteristic( SCD_SET_GEN_CMD_HND, b'\x30' ) # erase sensor data
#
# disconnect
#
p.disconnect()


