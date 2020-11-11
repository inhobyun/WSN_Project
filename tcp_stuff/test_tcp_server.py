"""
Code to test socket

by Inho Byun, Researcher/KAIST
   inho.byun@gmail.com
                    started 2020-11-05
                    last updated 2020-11-11
"""
import socket
import sys
import time

#############################################
# target definitions to TCP Server
#############################################
#
# target TCP Server identifiers
#
TCP_HOST_NAME   = socket.gethostname()
TCP_PORT        = 8088
TCP_DEV_READY_MSG   = 'DEV_READY'
TCP_DEV_CLOSE_MSG   = 'DEV_CLOSE'
TCP_STE_START_MSG   = 'STE_START'
TCP_STE_STOP_MSG    = 'STE_STOP'
TCP_STE_REQ_MSG     = 'STE_REQ'
#
# global variables
#
gSocketServer = None

#############################################
#############################################
#         
# Main starts here
#
#############################################

gSocketServer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
if gSocketServer != None:
    print("TCP S-> socket created")
    if len(sys.argv) > 1:
        print ("TCP S-> take argument as port# (default: 8088)")
        TCP_PORT = int(sys.argv[1])
    try:
        print("TCP S-> trying to bind %s:%d" % (TCP_HOST_NAME, TCP_PORT) )
        gSocketServer.bind((TCP_HOST_NAME, TCP_PORT))
    except:
        print("TCP S-> binding fail... Exiting...")
        sys.exit(1)
else:
    print("TCP S-> socket creation fail... Exiting...")
    sys.exit(1)
    
print("TCP S-> socket binded")    
gSocketServer.listen(1)
print("TCP S-> listen & accepting...")
conn, addr = gSocketServer.accept()
from_client = ''

#
# RX 1'st data 
#
data = conn.recv(1024)
if data:
    from_client = data.decode()
    print ("TCP S-> [RX]] '%s'" % (from_client))
#
# Key input and TX
#
while True:
    try:
        msg = input("TCP S-> input: ")
    except KeyboardInterrupt:
        print ('TCP S-> keybord interrupted... Send "%s" to client...' % TCP_STE_CLOSE_MSG)
        conn.send(TCP_STE_CLOSE_MSG.encode())
        break

    try:
       conn.send(msg.encode())
    except:   
        print("TCP S-> [TX] fail... Exiting...")

    if msg == TCP_STE_START_MSG:
        for _ in range(10):
            time.sleep(1.)
            try:
                conn.send(TCP_STE_REQ_MSG.encode())
                print ("TCP S-> [TX]] '%s'" % (TCP_STE_REQ_MSG))
            except:   
                print("TCP S-> [TX] fail... Exiting...")
            data = conn.recv(1024)
            if data:
                from_client = data.decode()
                print ("TCP S-> [RX]] '%s'" % (from_client))
#
# All done !
#

time.sleep(3.)
conn.close()
gSocketServer.close()        