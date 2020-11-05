import socket
import sys

#############################################
# target definitions to TCP Server
#############################################
#
# target TCP Server identifiers
#
#CP_ADDRESS = "125.131.73.31"
TCP_ADDRESS = "127.0.0.1"
TCP_PORT    = 8088
#
# global variables
#
gSoketServer = None

gSoketServer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
if gSoketServer != None:
    print("Tcp Server> Socket created")
    try:
        gSoketServer.bind((socket.gethostname(), TCP_PORT))
    except:
        print("TCP Server> binding fail... Exiting...")
        sys.exit(1)
else:
    print("TCP Server> Socket creation fail... Exiting...")
    sys.exit(1)
    
print("Tcp Server> Socket binded")    
gSoketServer.listen(1)

cnt = 0
while True:
    print("Tcp Server> listen & accepting...")
    conn, addr = gSoketServer.accept()
    print("Tcp Server> connected address:", str(addr))
    from_client = ''
    while True:
        data = conn.recv(4096)
        print("Tcp Server> data received...")
        if not data:
            break
        cnt += 1
        from_client += data
        print ("Tcp Server> data:", from_client)
        if cnt > 10:
            conn.send("STOP")
    conn.close()
    print ('Tcp Server> client disconnected')
