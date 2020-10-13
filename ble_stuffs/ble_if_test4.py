"""
Code to test communication with blutooth ble device
by Inho Byun
2020-10-12
"""
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
# service UUID
#
SCD_DEVICE_NAME_UUID = UUID("00002a00-0000-1000-8000-00805f9b34fb") # handle:  3, read
SCD_DEVICE_NAME_HND  = 3
SCD_MANUFA_NAME_UUID = UUID("00002a29-0000-1000-8000-00805f9b34fb") # handle: 21, read
SCD_MANUFA_NAME_HND  = 21
SCD_SET_MODE_UUID    = UUID("02a65821-0003-1000-2000-b05cb05cb05c") # handle: 28, read / write
SCD_SET_MODE_HND     = 28
SCD_STE_SERVICE_UUID = UUID("02a65821-1000-1000-2000-b05cb05cb05c") #
SCD_STE_CONFIG_UUID  = UUID("02a65821-1001-1000-2000-b05cb05cb05c") # handle: 35, read / write
SCD_STE_CONFIG_HND   = 35
SCD_STE_RESULT_UUID  = UUID("02a65821-1002-1000-2000-b05cb05cb05c") # handle: 37, read / notify
SCD_STE_RESULT_HND   = 37
#
# MTU
#
SCD_MAX_MTU = 65
#
# global variables
#
target_device  = None
target_STE_mode = b'\x00' \
                  

#############################################
# Define scan callback
#############################################
class ScanDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleDiscovery(self, dev, isNewDev, isNewData):
        if isNewDev:
            print("Discovered device [%s]" % dev.addr)
        elif isNewData:
            print("Received new data from [%s]" % dev.addr)

#############################################
# Define notification callback
#############################################
class NotifyDelegate(DefaultDelegate):
    def __init__(self, params):
        DefaultDelegate.__init__(self)
      
    def handleNotification(self, cHandle, data):
         print("Handle :", cHandle, ", Notification :", data)

#############################################
# Main starts here
#############################################

#
# Scanning for a while
#
scanner = Scanner().withDelegate(ScanDelegate())
devices = scanner.scan(8.0) # scanning for 8 sec

#
# check to match BOSCH SCD device identifiers
#
found_count = 0
for dev in devices:
    print("Device %s (%s), RSSI=%d dB" % (dev.addr, dev.addrType, dev.rssi))
    for (adtype, desc, value) in dev.getScanData():
        
        print("  (AD Type=%d) %s = %s" % (adtype, desc, value))

        if adtype == 255 and TARGET_MANUFA_UUID in value:
            found_count += 1
            print("  +--- found", desc) 
        if adtype == 9 and TARGET_DEVICE_NAME in value:
            found_count += 1
            print("  +--- found", desc)
            
        if found_count >= 2:
            print("  +--- found BOSCH SCD BLUTOOTH BLE device!!")
            target_device = dev
            break
    if found_count >= 2:
        break
#
# connect
#
if target_device != None:
    print("Connecting [" + target_device.addr + "] type:" + target_device.addrType)
    print("...")
    p = Peripheral(target_device.addr, target_device.addrType)
    p.setMTU(65)
    p.setDelegate( NotifyDelegate(p) )
#
# read Device Name, Manufacurer Name
#
    ret_val = p.readCharacteristic( SCD_DEVICE_NAME_HND )
    print("Device Name is [" + ret_val.decode("utf-8") + "]")
    ret_val = p.readCharacteristic( SCD_MANUFA_NAME_HND )
    print("Manufacturer Name is [" + ret_val.decode("utf-8") + "]")
#
# check Mode and set STE Mode
#
    ret_val = p.readCharacteristic( SCD_SET_MODE_HND )
    print("Mode is [", ret_val, "]")
    if ret_val !=  b'\x00':
        print("Set STE mode")
        p.writeCharacteristic( SCD_SET_MODE_HND, b'\x00' )
        ret_val = p.readCharacteristic( SCD_SET_MODE_HND )
        print("Mode is [", ret_val, "]")
#
# set STE Configuration
#
    ret_val = p.readCharacteristic( SCD_STE_CONFIG_HND )
    print("STE Configuration is [", ret_val, "]")
#
# disconnect
#
    p.disconnect()
else:
    print("No matching device found...")



