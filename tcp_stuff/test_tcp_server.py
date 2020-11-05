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
TCP_LOCAL_HOST = "127.0.0.1"
#CP_HOST_NAME  = "125.131.73.31"
TCP_HOST_NAME  = socket.gethostname()
TCP_PORT       = 8088
#
# global variables
#
gSoketServer = None

gSoketServer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
if gSoketServer != None:
    print("Tcp Server> socket created")
    try:
        print("Tcp Server> trying to bind %s:%d" % (TCP_HOST_NAME, TCP_PORT) )
        gSoketServer.bind((TCP_HOST_NAME, TCP_PORT))
    except:
        print("TCP Server> binding fail... Exiting...")
        sys.exit(1)
else:
    print("TCP Server> socket creation fail... Exiting...")
    sys.exit(1)
    
print("Tcp Server> socket binded")    
gSoketServer.listen(2)

while True:
    print("Tcp Server> listen & accepting...")
    conn, addr = gSoketServer.accept()
    from_client = ''
    cnt = 0
    while True:
        data = conn.recv(1024)
        print("Tcp Server> data received...")
        if not data:
            break
        cnt += 1
        from_client = data.decode()
        print ("Tcp Server> data: [%s]" % from_client)
        if cnt > 15:
            conn.send("STOP".encode())
            break
    conn.close()
    print ('Tcp Server> client disconnected, count is', cnt)
