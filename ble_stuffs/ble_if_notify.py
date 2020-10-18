import bluepy.btle
import sys
import time
import struct

service_uuid = "47e5f35b-e4d2-4190-98e5-0ae2794b7766"

notif_handle = 30
request_handle = 26
conn_param_handle = 28

t1 = 0
t2 = 0

class MyDelegate(bluepy.btle.DefaultDelegate):
    def __init__(self):
        bluepy.btle.DefaultDelegate.__init__(self)
        # ... initialise here
        print (">>>>> notification handler invoked")

    def handleNotification(self, cHandle, data):
        global t1, t2
        t1 = time.time() * 1000
        print(">==== Notification Time = %f ms,\tData Length = %d,\tNotification = %s" %
              (t1 - t2, len(data), struct.unpack('<H', data[0:2])[0]))
        t2 = time.time() * 1000


if __name__ == '__main__':

    p = bluepy.btle.Peripheral("18:04:ed:5a:85:6a")
    print("MTU set to %d" % p.setMTU(65).get('mtu')[0])
    p.setDelegate( MyDelegate() )

    svc = p.getServiceByUUID( service_uuid )
    chars = svc.getCharacteristics()

    time.sleep(0.7)

    if sys.argv[2] != '0':
        conn_interval = int(sys.argv[2], 10)
        p.writeCharacteristic(conn_param_handle, struct.pack('<HHHH', conn_interval, conn_interval, 0, 42), withResponse=True)
        print("Connection params set to (%d, %d, 0, 2000)" % (conn_interval, conn_interval))

    time.sleep(0.7)

    notif_count = int(sys.argv[3], 10)
    p.writeCharacteristic(request_handle, struct.pack('<H', notif_count), withResponse=True)
    print("Notifications requested = %d" % notif_count)

    time.sleep(0.7)

    p.writeCharacteristic((notif_handle + 1), struct.pack('<H', 1))
    print("Notification subscribed by writing handle %d" % (notif_handle + 1))
    t2 = time.time() * 1000


    while True:
        if p.waitForNotifications(1.0):
            # handleNotification() was called
            continue

        print "Waiting..."
        # Perhaps do something else here
