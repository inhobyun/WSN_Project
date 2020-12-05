"""
Sensor data monitoring and analysis application based on flask WEB application framework

by Inho Byun, Researcher/KAIST
   inho.byun@gmail.com
                    started 2020-10-01
                    last updated 2020-12-03
"""
import datetime
from flask import Flask, redirect, request
from jinja2 import Environment, PackageLoader, Markup, select_autoescape
import json
import math
import socket
import sys
import time

#############################################
# target definitions to TCP Server
#############################################
#
# target TCP Server identifiers
#
##TCP_HOST_NAME = "127.0.0.1"       # TEST Host Name
##TCP_HOST_NAME = "10.2.2.3"        # TEST Host Name
##TCP_HOST_NAME = "192.168.0.3"     # TEST Host Name
##TCP_HOST_NAME = "125.131.73.31"   # Default Host Name
TCP_HOST_NAME = socket.gethostname()
TCP_PORT      = 8088              # Default TCP Port Name
#
TCP_DEV_READY_MSG = 'DEV_READY'     # server message to check client ready
TCP_DEV_CLOSE_MSG = 'DEV_CLOSE'     # server message to disconnect client
TCP_STE_START_MSG = 'STE_START'     # server message to start STE for monitoring
TCP_STE_STOP_MSG  = 'STE_STOP'      # server message to stop STE
TCP_STE_REQ_MSG   = 'STE_REQ'       # server message to request a STE result data 
TCP_BDT_RUN_MSG   = 'BDT_RUN'       # server message to run BDT advanced STE /w memory write
TCP_BDT_REQ_MSG   = 'BDT_REQ'       # server message to request BDT data
TCP_BDT_END_MSG   = 'BDT_END'       # client message to inform BDT data transfer completed
#
# global variables
#
gSocketServer   = None
gSocketConn     = None
gSocketAddr     = None
#
gIsMonStarted   = False

#############################################
#############################################
#         
# socket stuffs
#
#############################################
# create, bind and listen socket
#
def open_socket(clientNum = 1):
    global TCP_HOST_NAME
    global TCP_PORT
    global gSocketServer
    #
    if len(sys.argv) > 1:
        print ("TCP-S> take argument as port# (default: %d)" % TCP_PORT)
        TCP_PORT = int(sys.argv[1])
    gSocketServer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if gSocketServer != None:
        print("TCP-S> socket created")
        print("TCP-S> trying to bind %s:%d" % (TCP_HOST_NAME, TCP_PORT) )
        try:
            gSocketServer.bind((TCP_HOST_NAME, TCP_PORT))
        except:
            print("TCP-S> binding fail... Exiting...")
            return False
    else:
        print("TCP-S> socket creation fail... Exiting...")
        return False
    print("TCP-S> binded...")    
    gSocketServer.listen(clientNum)
    print("TCP-S> listening...") 
    #
    return True 

##############################################
# accept socket
#
def accept_socket(blockingTimer = 60):
    global gSocketServer
    global gSocketConn
    global gSocketAddr
    #
    if gSocketConn == None:
        print ("\nTCP-S> accepting to read ... ", end = '')
        try:
            gSocketServer.setblocking(blockingTimer)
            gSocketConn, gSocketAddr = gSocketServer.accept()
        except:
            print ("error !")
            gSocketConn = gSocketAddr = None
            return False         
        print ("accepted port# [", gSocketAddr, "]")
    return True    

##############################################
# read from socket
#
def read_from_socket(blockingTimer = 8):
    global gSocketServer
    global gSocketConn
    #
    print ("\nTCP-S> read ... ", end = '')
    rx_msg = ''
    try:
        gSocketServer.setblocking(blockingTimer)
        data = gSocketConn.recv(1024)
    except TimeoutError:
        print ("timeout !")
    except:
        print ("error !")
    else:
        rx_msg = data.decode()
        print ("received [%s]" % rx_msg)
    #    
    return rx_msg   

#############################################
# write to socket
#
def write_to_socket(tx_msg):
    global gSocketServer
    global gSocketConn
    #
    print ("\nTCP-S> write ... ", end = '')
    try:
        gSocketConn.send(tx_msg.encode())
    except:
        print ("error !" )
    else:
        print ("[%s] sent" % tx_msg)
    #    
    return
#
#############################################
#############################################
#         
# flask stuffs
#
#############################################
#
app = Flask(__name__, static_url_path='/static')
env = Environment(
    loader=PackageLoader(__name__, 'templates'),
    autoescape=select_autoescape(['html', 'xml'])
)

#############################################
# base UI
#
@app.route('/')
def root():
    template = env.get_template('main.html')
    return template.render()

#############################################
# sensor monitoring UI
#
@app.route('/m_monitor')
def monitor():
    template = env.get_template('m_monitor.html')
    return template.render()

#############################################
# graphics UI
#
@app.route('/m_dashboard')
def dashboard():
    template = env.get_template('m_dashboard.html')
    return template.render()

#############################################
# about UI - page #1
#
@app.route('/m_intro_1')
def intro_1():
    template = env.get_template('m_intro_1.html')
    return template.render()

#############################################
# about UI - page #2
#
@app.route('/m_intro_2')
def intro_2():
    template = env.get_template('m_intro_2.html')
    return template.render()

#############################################
# Ooops UI
#
@app.route('/m_Ooops')
def Ooops():
    template = env.get_template('m_Ooops.html')
    return template.render()

#############################################
# monitoring UI - start
#
@app.route('/post_monStart', methods=['POST'])
def post_monStart():
    data = json.loads(request.data)
    value = data['value']
    #
    global gIsMonStarted
    
    # send STE start & request
    accept_socket()
    if not gIsMonStarted: 
        time.sleep(0.2)
        write_to_socket(TCP_STE_START_MSG)
        from_client = None
        gIsMonStarted = True
    else:    
        time.sleep(0.2)
        write_to_socket(TCP_STE_REQ_MSG)
        time.sleep(0.2)
        from_client = read_from_socket()

    # get the data to post
    if from_client != None:
        from_client = from_client.replace(')','')
        from_client = from_client.replace('(','')
        vals = from_client.split(',')  
        rows = {'row_00' : vals[ 0],
                'row_01' : vals[ 1],
                'row_02' : vals[ 2],
                'row_03' : vals[ 3],
                'row_04' : vals[ 4],
                'row_05' : vals[ 5],
                'row_06' : vals[ 6],
                'row_07' : vals[ 7],
                'row_08' : vals[ 8],
                'row_09' : vals[ 9],
                'row_10' : vals[10],
                'row_11' : vals[11]
               }
    else:                          
        rows = {'row_00' : '?',
                'row_01' : '?',
                'row_02' : '?',
                'row_03' : '?',
                'row_04' : '?',
                'row_05' : '?',
                'row_06' : '?',
                'row_07' : '?',
                'row_08' : '?',
                'row_09' : '?',
                'row_10' : '?',
                'row_11' : '?'
               }               

    return json.dumps(rows)

#############################################
# monitoring UI - stop
#
@app.route('/post_monStop', methods=['POST'])
def post_monStop():
    data = json.loads(request.data)
    value = data['value']
    #
    global gIsMonStarted

    # send STE request & stop
    accept_socket()
    if gIsMonStarted:
        time.sleep(0.2)
        write_to_socket(TCP_STE_STOP_MSG)
        gIsMonStarted = False
        tm = time.time()
        tm_stamp = ( "%s [%.3f]" % (datetime.datetime.fromtimestamp(tm).strftime('%Y-%m-%d %H:%M:%S'), tm) )
        rows = {'row_00' : tm_stamp,
                'row_01' : '-',
                'row_02' : '-',
                'row_03' : '-',
                'row_04' : '-',
                'row_05' : '-',
                'row_06' : '-',
                'row_07' : '-',
                'row_08' : '-',
                'row_09' : '-',
                'row_10' : '-',
                'row_11' : '-'
               }               

    return json.dumps(rows)

#############################################
# graphics UI - drawing
#
@app.route('/post_graph', methods=['POST'])
def post_graph():
    data = json.loads(request.data)
    value = data['value']

    # Prepare data to send in here.
    x = []
    y = []
    for i in range(100):
        # Sine value for example.
        curr_x = float(i / 10)
        x.append(curr_x)
        y.append(math.sin(curr_x) * value)
    
    return json.dumps({ 'x': x, 'y': y })

#############################################
#############################################
#         
# Main starts here
#
#############################################
#
if __name__ == '__main__':
    if open_socket():
        app.run(host='0.0.0.0')
#
#############################################        