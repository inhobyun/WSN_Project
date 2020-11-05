import socket
import sys

#############################################
# target definitions to TCP Server
#############################################
#
# target TCP Server identifiers
#
#CP_ADDRESS = "125.131.73.31" #
TCP_ADDRESS = "0.0.0.0"
TCP_PORT    = 8088         #
#
# global variables
#
gSoketServer = None

gSoketServer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
if gSoketServer != None:
    try:
        gSoketServer.bind((TCP_ADDRESS, TCP_PORT))
    except:
        print("Socket binding fail... Exiting...")
        sys.exit(1)
else:
    print("Socket creation fail... Exiting...")
    sys.exit(1)            

gSoketServer.listen(30)

cnt = 0
while True:
    conn, addr = gSoketServer.accept()
    from_client = ''
    while True:
        data = conn.recv(4096)
        if not data:
            break
        cnt += 1
        from_client += data
        print (from_client)
        if cnt > 10:
            conn.send("STOP")
    conn.close()
    print ('client disconnected')