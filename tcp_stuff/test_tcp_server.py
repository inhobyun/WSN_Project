"""
Code to test socket

by Inho Byun, Researcher/KAIST
   inho.byun@gmail.com
                    started 2020-11-05
                    last updated 2020-11-05
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

while True:
    try:
        print("TCP S-> listen & accepting...")
        conn, addr = gSocketServer.accept()
        from_client = ''
        cnt = 0
        while True:
            data = conn.recv(1024)
            if not data:
                break
            cnt += 1
            from_client = data.decode()
            print ("TCP S-> received [%s]" % (from_client))
            if from_client == TCP_DEV_READY_MSG:
                conn.send(TCP_STE_START_MSG.encode())
        conn.close()
        print ('TCP S-> client disconnected, count is', cnt)
    except KeyboardInterrupt:
        print ('TCP S-> keybord interrupted... Send "%s" to client...' % TCP_STE_STOP_MSG)
        conn.send(TCP_STE_STOP_MSG.encode())
        time.sleep(5.)
        print ('TCP S-> Send "%s" to client and Exiting...' % TCP_DEV_CLOSE_MSG)
        conn.send(TCP_DEV_CLOSE_MSG.encode())
        conn.close()
        break
    except:
        print ('TCP S-> unknown exception... Exiting...')
        break
gSocketServer.close()        