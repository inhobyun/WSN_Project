"""
Code to test socket

by Inho Byun, Researcher/KAIST
   inho.byun@gmail.com
                    started 2020-11-05
                    last updated 2020-11-05
"""
import socket
import sys

#############################################
# target definitions to TCP Server
#############################################
#
# target TCP Server identifiers
#
#CP_HOST_NAME = "127.0.0.1"       # Local Host IP address  
#CP_HOST_NAME = "125.131.73.31"   # Test Server IP address  
TCP_HOST_NAME = socket.gethostname()
TCP_PORT      = 8088
#
# global variables
#
gSocketServer = None

gSocketServer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
if gSocketServer != None:
    print("TCP S-----> socket created")
    if len(sys.argv) > 1:
        print ("TCP S-----> take argument as port# (default: 8088)")
        TCP_PORT = int(sys.argv[1])
    try:
        print("TCP S-----> trying to bind %s:%d" % (TCP_HOST_NAME, TCP_PORT) )
        gSocketServer.bind((TCP_HOST_NAME, TCP_PORT))
    except:
        print("TCP S-----> binding fail... Exiting...")
        sys.exit(1)
else:
    print("TCP S-----> socket creation fail... Exiting...")
    sys.exit(1)
    
print("TCP S-----> socket binded")    
gSocketServer.listen(1)

while True:
    try:
        print("TCP S-----> listen & accepting...")
        conn, addr = gSocketServer.accept()
        from_client = ''
        cnt = 0
        while True:
            data = conn.recv(1024)
            if not data:
                break
            cnt += 1
            from_client = data.decode()
            print ("TCP S-----> [%s]" % (from_client))
        conn.close()
        print ('TCP S-----> client disconnected, count is', cnt)
    except KeyboardInterrupt:
        print ('TCP S-----> keybord interrupted... Send "STOP" to client and Exiting...')
        conn.send("STOP".encode())
        conn.close()
        break
    except:
        print ('TCP S-----> unknown exception... Exiting...')
        break
gSocketServer.close()        