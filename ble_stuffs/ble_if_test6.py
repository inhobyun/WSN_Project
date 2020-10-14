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
import struct
import sys
import time
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
"""
SCD_DEVICE_NAME_UUID = UUID("00002a00-0000-1000-8000-00805f9b34fb") # handle:  3, read
SCD_MANUFA_NAME_UUID = UUID("00002a29-0000-1000-8000-00805f9b34fb") # handle: 21, read
SCD_SET_MODE_UUID    = UUID("02a65821-0003-1000-2000-b05cb05cb05c") # handle: 28, read / write
SCD_SET_GEN_CMD_UUID = UUID("02a65821-0004-1000-2000-b05cb05cb05c") # handle: 30, read / write
SCD_STE_SERVICE_UUID = UUID("02a65821-1000-1000-2000-b05cb05cb05c") 
SCD_STE_CONFIG_UUID  = UUID("02a65821-1001-1000-2000-b05cb05cb05c") # handle: 35, read / write
SCD_STE_RESULT_UUID  = UUID("02a65821-1002-1000-2000-b05cb05cb05c") # handle: 37, read / notify
"""
SCD_DEVICE_NAME_HND  = 3
SCD_MANUFA_NAME_HND  = 21
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
scanned_count   = 0
target_device   = None
target_STE_mode = bytearray(35)
#
# STE configuration
#
target_STE_mode[ 0: 4] = b'\x00\x00\x00\x00'  # [ 0~ 3] Unix time
target_STE_mode[ 4: 6] = b'\xFC\x00'          # [    4] sensor En/Disable
                                              # [    5] output data rate
target_STE_mode[ 6: 8] = b'\xE4\x07'          # [ 6~ 7] accelerometer threshold
target_STE_mode[12:16] = b'\x00\x00\x00\x00'  # [12~15] light sensor threshold low
target_STE_mode[16:20] = b'\xE8\xE4\xF5\x05'  # [16~19] light sensor threshold high
target_STE_mode[20:22] = b'\x80\x57'          # [20~21] magnetometer threshold
target_STE_mode[26:28] = b'\x80\xF3'          # [26~27] temperature threshold low
target_STE_mode[28:30] = b'\x00\x2D'          # [28~29] temperature threshold high
target_STE_mode[30:32] = b'\xF0\x00'          # [   30] sensor raw value to flash
target_STE_mode = bytes( target_STE_mode[0:35] )

                  
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
            print ('^', end='', flush = True) #print("Received new data from [%s]" % dev.addr)

#############################################
# Define notification callback
#############################################
class NotifyDelegate(DefaultDelegate):
    def __init__(self, params):
        DefaultDelegate.__init__(self)
      
    def handleNotification(self, cHandle, data):
         print("Handle:", cHandle, ", Notification: [", data, "]", end='\n', flush = True)

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
print ("Blooth BLE Device scan started..." )
devices = scanner.scan(8.0) # scanning for 8 sec
print ("\nBlooth BLE Device scan completed... [%d] devices are scanned\n" % scanned_count)

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
p = Peripheral(target_device.addr, target_device.addrType)
p.setMTU(65)
p.setDelegate( NotifyDelegate(p) )
#
# read Device Name, Manufacurer Name
#
ret_val = p.readCharacteristic( SCD_DEVICE_NAME_HND )
print("\tDevice Name is [" + ret_val.decode("utf-8") + "]")
ret_val = p.readCharacteristic( SCD_MANUFA_NAME_HND )
print("\tManufacturer Name is [" + ret_val.decode("utf-8") + "]")
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
p.writeCharacteristic( SCD_STE_CONFIG_HND, target_STE_mode )
ret_val = p.readCharacteristic( SCD_STE_CONFIG_HND )
hex_string = ''.join(['.' + ch if i % 2 == 0 else ch for i, ch in enumerate(ret_val.hex())])
print("\tSTE configuration is\n[" + hex_string + "] size=", len(ret_val))
ret_val = p.readCharacteristic( SCD_SET_GEN_CMD_HND )
print("\tGeneric Command is [" + ret_val.hex() + "]")
#
# start STE and stop after a while
#
print("+--- STE Starting...")
p.writeCharacteristic( SCD_SET_GEN_CMD_HND, b'\x20' )
time.sleep(3) # wait 3 seconds for rolling
p.writeCharacteristic( SCD_SET_GEN_CMD_HND, b'\x20' )
print("+--- STE STOP...")
p.writeCharacteristic( SCD_SET_GEN_CMD_HND, b'\x00' )          
#
# output STE result
#
ret_val = p.readCharacteristic( SCD_STE_RESULT_HND )
hex_string = ''.join(['.' + ch if i % 2 == 0 else ch for i, ch in enumerate(ret_val.hex())])
print("\tSTE result return is\n[" + hex_string + "] size=", len(ret_val))
#
# output temperature
#
hex_string = ''.join(['.' + ch if i % 2 == 0 else ch for i, ch in enumerate(ret_val[18:20].hex())])
print ("+--- Temperature raw data is [" + hex_string + "]", end = '' )
temperature = float( int( ret_val[18] ) + 256 * int( ret_val[19] ) ) \
              * 0.0078
print ("\t=> [%.2f] C" % (temperature) )
#
# output light
#    
hex_string = ''.join(['.' + ch if i % 2 == 0 else ch for i, ch in enumerate(ret_val[20:24].hex())])
print ("+--- Light raw data is [" + hex_string + "]", end = '')
light = float( int( ret_val[20] ) + 256 * int( ret_val[21] ) ) \
        + float(2**16) * float( int( ret_val[22] ) + 256 * int( ret_val[23] ) )
print ("\t=> [%.3f] lux" % (light/1000) )
#
# output tolling count
#    
print ("+--- Rolling Counter:", int(ret_val[32]) )
#
# clean-up and init sensor device
#

#
# disconnect
#
p.disconnect()


