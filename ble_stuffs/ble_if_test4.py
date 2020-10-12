"""
Code to test communication with blutooth ble device
by Inho Byun
2020-10-12
"""
import struct
from bluepy.btle import Scanner, DefaultDelegate, UUID, Peripheral

#############################################
# target definitions to interface 
#############################################
TARGET_UUID =       "a6022158" # Manufacturer == BOSCH
TARGET_DEVICE_NAME ="SCD-"      # "SCD-123456789012345"
TARGET_MANUFA_NAME ="bosch-"    # "bosch-connectivity.com"

SCD_DEVICE_NAME_UUID = UUID("00002a00-0000-1000-8000-00805f9b34fb") # handle:  3, read
SCD_MANUFA_NAME_UUID = UUID("00002a29-0000-1000-8000-00805f9b34fb") # handle: 21, read
SCD_SET_MODE_UUID =    UUID("02a65821-0003-1000-2000-b05cb05cb05c") # handle: 28, read / write
SCD_STE_SERVICE_UUID = UUID("02a65821-1000-1000-2000-b05cb05cb05c") #
SCD_STE_CONFIG_UUID =  UUID("02a65821-1001-1000-2000-b05cb05cb05c") # handle: 35, read / write
SCD_STE_RESULT_UUID =  UUID("02a65821-1002-1000-2000-b05cb05cb05c") # handle: 37, read / notify

target_dev = None
ste_service = None
r_w_char = None
r_n_char = None
r_n_handle = None
r_n_cccd = None

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
         print("Handle : " + cHandle)
         print("Notification : " + data.decode("utf-8"))

#############################################
# Main starts here
#############################################

#
# Scanning for a while
#
scanner = Scanner().withDelegate(ScanDelegate())
devices = scanner.scan(8.0) # scanning for 8 sec

#
# Check BOSCH SCD device
#
target_found = 0
for dev in devices:
    print("Device %s (%s), RSSI=%d dB" % (dev.addr, dev.addrType, dev.rssi))
    for (adtype, desc, value) in dev.getScanData():
        
        print("  (AD Type=%d) %s = %s" % (adtype, desc, value))

        if adtype == 255 and TARGET_UUID in value:
            target_found += 1
            print("  +--- found", desc) 
        if adtype == 9 and TARGET_DEVICE_NAME in value:
            target_found += 1
            print("  +--- found", desc)
            
        if target_found >= 2:
            print("  +--- found BOSCH SCD BLUTOOTH BLE device!!")
            target_dev = dev
            break
    if target_found >= 2:
        break

""" commented >>>>>>>>>>>>

if target_dev is not None:
    #############################################
    # Connect
    #############################################
    print("Connecting... address:", target_dev.addr, "type:", target_dev.addrType)
    print(" ")
    p = Peripheral(target_dev.addr, target_dev.addrType)

    try:
        # Set notify callback
        p.setDelegate( NotifyDelegate(p) )

        #############################################
        # For debug
        #############################################
        services=p.getServices()
        # displays all services
        for service in services:
            print(service)
            # displays characteristics in this service
            chList = service.getCharacteristics()
            print("-------------------------------------------------------")
            print("Handle   UUID                                Properties")
            print("-------------------------------------------------------")
            for ch in chList:
                print("  0x"+ format(ch.getHandle(),'02X')  +"   "+str(ch.uuid) +" " + ch.propertiesToString())
            print("-------------------------------------------------------")
            print(" ")


        #############################################
        # Set up characteristics
        #############################################
        ste_service = p.getServiceByUUID(STE_SERVICE_UUID)
        ##r_w_char = ste_service.getCharacteristics(STE_R_W_UUID)[0]
        r_n_char = ste_service.getCharacteristics(STE_R_N_UUID)[0]

        r_n_handle = r_n_char.getHandle()
        print ("Char:", r_n_char, "Handle:", r_n_handle)

        
        # Search and get the read-Characteristics "property" 
        # (UUID-0x2902 CCC-Client Characteristic Configuration))
        # which is located in a handle in the range defined by the boundries of the Service
        for desriptor in p.getDescriptors(r_n_handle, 0xFFFF):  # The handle range should be read from the services 
            if (desriptor.uuid == 0x2902):                   #      but is not done due to a Bluez/BluePy bug :(     
                print("Client Characteristic Configuration found at handle 0x"+ format(desriptor.handle, "02X"))
        ##        r_n_cccd = desriptor.handle
        ##        p.writeCharacteristic(r_n_cccd, struct.pack('<bb', 0x01, 0x00))
                
        r_n_char.write()
        p.waitForNotifications(5.0)

        #############################################
        # BLE message loop
        #############################################
        ##while 1:
        ##    if p.waitForNotifications(5.0):
                # handleNotification() was called
        ##        continue
                
        ##    p.writeCharacteristic(hButtonCCC, struct.pack('<bb', 0x01, 0x00))
        ##    write_char.write(str.encode("hello~"))

        
    finally:
        p.disconnect()


else:
    print("No matching device found...")


print("Close app")

<<<<<<<<<< commented """

