"""
Sensor data monitoring and analysis application based on flask WEB application framework

by Inho Byun, Researcher/KAIST
   inho.byun@gmail.com
                    started 2020-10-01
                    last updated 2020-12-03
"""
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
TCP_HOST_NAME = socket.gethostname()
TCP_PORT      = 8088
TCP_DEV_READY_MSG = 'DEV_READY'
TCP_DEV_CLOSE_MSG = 'DEV_CLOSE'
TCP_STE_START_MSG = 'STE_START'
TCP_STE_STOP_MSG  = 'STE_STOP'
TCP_STE_REQ_MSG   = 'STE_REQ'
TCP_BDT_RUN_MSG   = 'BDT_RUN'
TCP_BDT_REQ_MSG   = 'BDT_REQ'
#
# global variables
#
gSocketServer   = None
gSocketConn     = None
gSocketAddr     = 0
#
gIsStarted      = False

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
    global gSocketConn
    global gSocketAddr
    #
    if len(sys.argv) > 1:
        print ("TCP-S> take argument as port# (default: %d)" % TCP_PORT)
        TCP_PORT = int(sys.argv[1])
    gSocketServer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if gSocketServer != None:
        print("TCP-S> socket created")
        try:
            print("TCP-S> trying to bind %s:%d" % (TCP_HOST_NAME, TCP_PORT) )
            gSocketServer.bind((TCP_HOST_NAME, TCP_PORT))
        except:
            print("TCP-S> binding fail... Exiting...")
            sys.exit(1)
    else:
        print("TCP-S> socket creation fail... Exiting...")
        sys.exit(1)
    print("TCP-S> binded...")    
    gSocketServer.listen(clientNum)
    print("TCP-S> listening...") 
    #
    return  

##############################################
# read from socket
#
def read_from_socket(blockingTimer = 60):
    global gSocketServer
    global gSocketConn
    global gSocketAddr
    #
    try:
        print ("\nTCP-S> accepting to read ... ", end = '')
        gSocketServer.setblocking(blockingTimer)
        gSocketConn, gSocketAddr = gSocketServer.accept()
        print ("accepted port# [", gSocketAddr, "]")
        rx_msg = ''
        cnt = 0
        while True:
            data = gSocketConn.recv(1024)
            if not data:
                break
            cnt += 1
            rx_msg += data.decode()
        print ("TCP-S> received [%d]time(s), [%s]" % (cnt, rx_msg))
        gSocketConn.close()
    except:
        rx_msg = None
        print ("TCP-S> accept & read fail !" )
    #    
    return rx_msg   

#############################################
# write to socket
#
def write_to_socket(tx_msg, blockingTimer = 60):
    global gSocketServer
    global gSocketConn
    global gSocketAddr
    #
    try:
        print ("\nTCP-S> accepting to write ... ", end = '')
        gSocketServer.setblocking(blockingTimer)
        gSocketConn, gSocketAddr = gSocketServer.accept()
        print ("accepted port# [", gSocketAddr, "]")
        if tx_msg != '':
            gSocketConn.send(tx_msg.encode())
            print ("TCP-S> sent [%s]" % tx_msg)
        gSocketConn.close()
    except:
        print ("TCP-S> accept & write fail !" )
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

@app.route('/')
def root():
    template = env.get_template('main.html')
    return template.render()

@app.route('/m_monitor')
def monitor():
    template = env.get_template('m_monitor.html')
    return template.render()

@app.route('/m_dashboard')
def dashboard():
    template = env.get_template('m_dashboard.html')
    return template.render()

@app.route('/m_intro_1')
def intro_1():
    template = env.get_template('m_intro_1.html')
    return template.render()

@app.route('/m_intro_2')
def intro_2():
    template = env.get_template('m_intro_2.html')
    return template.render()

@app.route('/m_Ooops')
def Ooops():
    template = env.get_template('m_Ooops.html')
    return template.render()

@app.route('/post_monStart', methods=['POST'])
def post_monStart():
    data = json.loads(request.data)
    value = data['value']
    #
    global gIsStarted
    
    # send STE start & request
    if not gIsStarted: 
        time.sleep(0.2)
        write_to_socket(TCP_STE_START_MSG)
        gIsStarted = True
        from_client = None
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
        rows = {'row_01' : vals[ 0],
                'row_02' : vals[ 1],
                'row_03' : vals[ 2],
                'row_04' : vals[ 3],
                'row_05' : vals[ 4],
                'row_06' : vals[ 5],
                'row_07' : vals[ 6],
                'row_08' : vals[ 7],
                'row_09' : vals[ 8],
                'row_10' : vals[ 9],
                'row_11' : vals[10]
               }
    else:                          
        rows = {'row_01' : '?',
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

@app.route('/post_monStop', methods=['POST'])
def post_monStop():
    data = json.loads(request.data)
    value = data['value']
    #
    global gIsStarted

    # send STE request & stop
    if gIsStarted:
        time.sleep(0.2)
        write_to_socket(TCP_STE_STOP_MSG)
        gIsStarted = False
        rows = {'row_01' : '-',
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
    open_socket()
    app.run(host='0.0.0.0')