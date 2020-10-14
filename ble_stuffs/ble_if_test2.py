from bluetooth.ble import DiscoveryService

target_name = "SCD-7260040000241DA"
target_address = None # 18:04:ED:5A:85:6A

print ("start to discovering...")
service = DiscoveryService()
devices = service.discover(2)
print ("discovering done...")
print ("Devices are: ", devices)

for address, name in devices.items():
    if target_name == name:
        target_address = address
        break

if target_address is not None:
    print ("found target bluetooth device with address ", target_address)
else:
    print ("could not find target bluetooth device nearby")
