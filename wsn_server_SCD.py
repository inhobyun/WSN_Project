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
import numpy as np
import math
##import matplotlib.pyplot as plotter
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
# Some constant parameters
#
ACCEPT_WAIT_TIME  = 11100           # 3 hrs 5 min.; time period to wait client connection
WSN_LOG_FILE_NAME = "SCD_BDT_Data_log.csv" 
#
# global variables
#
gSocketServer   = None
gSocketConn     = None
gSocketAddr     = None
#
gIsMonStarted   = False
gIsAnaStarted   = False
#
gBDTtextData    = None

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
        print ("TCP-S> socket created")
        print ("TCP-S> trying to bind %s:%d" % (TCP_HOST_NAME, TCP_PORT) )
        try:
            gSocketServer.bind((TCP_HOST_NAME, TCP_PORT))
        except:
            print ("TCP-S> binding fail... Exiting...")
            return False
    else:
        print ("TCP-S> socket creation fail... Exiting...")
        return False
    print ("TCP-S> binded...")    
    gSocketServer.listen(clientNum)
    print ("TCP-S> listening...") 
    #
    return True 

#############################################
# close socket
#
def close_socket():
    global gSocketServer
    global gSocketConn
    global gSocketAddr
    #
    if gSocketConn != None:
        print ("TCP-S> close accepted connection")
        gSocketConn.close()
        gSocketConn = gSocketAddr = None
    #
    if gSocketServer != None:
        print ("TCP-S> close socket")
        gSocketServer.close()
        gSocketServer = None
    #
    return    

##############################################
# accept socket
#
def accept_socket(blockingTimer = 60):
    global gSocketServer
    global gSocketConn
    global gSocketAddr
    #
    if gSocketConn == None:
        print ("\nTCP-S> accepting => ", end = '')
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
    print ("\nTCP-S> reading => ", end = '')
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
    print ("\nTCP-S> writing => ", end = '')
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
#############################################
#         
# menu bar button stuffs
#

#############################################
# base UI
#
@app.route('/')
def root():
    template = env.get_template('main.html')
    return template.render()

#############################################
# Ooops UI
#
@app.route('/m_Ooops')
def Ooops():
    template = env.get_template('m_Ooops.html')
    return template.render()

#############################################
# sensor monitoring UI
#
@app.route('/m_monitor')
def monitor():
    template = env.get_template('m_monitor.html')
    return template.render()

#############################################
# analysis UI
#
@app.route('/m_analysis')
def analysis():
    template = env.get_template('m_analysis.html')
    return template.render()

#############################################
# graphics UI
#
@app.route('/m_graph_time')
def graph_time():
    template = env.get_template('m_graph_time.html')
    return template.render()

#############################################
# graphics UI
#
@app.route('/m_graph_freq')
def graph_freq():
    template = env.get_template('m_graph_freq.html')
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
#############################################
#         
# left block button stuffs
#

#############################################
# monitoring UI - start
#
@app.route('/post_monStart', methods=['POST'])
def post_monStart():
    #data = json.loads(request.data)
    #value = data['value']
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
        # get the status
        val_x = float(val[2])
        val_y = float(val[4])
        val_z = float(val[6])
        if max (val_x, val_y, val_z) >= 0.5:        
            status_01 = '[동작]'
            status_02 = '[이상]'
        elif max (val_x, val_y, val_z) >= 0.2:
            status_01 = '[동작]'
            status_02 = '[정상]'
        else:    
            status_01 = '[정지]'
            status_02 = '[-?-]'
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
                'row_11' : vals[11],
                'status_01' : status_01,
                'status_02' : status_02
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
                'row_11' : '?',
                'status_01' : '[-?-]',
                'status_02' : '[-?-]'
               }               

    return json.dumps(rows)

#############################################
# monitoring UI - stop
#
@app.route('/post_monStop', methods=['POST'])
def post_monStop():
    #data = json.loads(request.data)
    #value = data['value']
    #
    global gIsMonStarted

    # send STE stop
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
# analysis UI - STEandBDT
#
@app.route('/post_STEandBDT', methods=['POST'])
def post_STEandBDT():
    #data = json.loads(request.data)
    #value = data['value']
    #
    global gIsAnaStarted
    global gBDTtextData

    # send BDT run
    accept_socket()
    write_to_socket(TCP_BDT_RUN_MSG)
    # wait till completed
    time.sleep(1.0)
    write_to_socket(TCP_DEV_READY_MSG)
    from_client = ''
    while from_client == '':
        from_client = read_from_socket(blockingTimer = 3)
    #
    tm = time.time()
    tm_stamp = ( "%s [%.3f]" % (datetime.datetime.fromtimestamp(tm).strftime('%Y-%m-%d %H:%M:%S'), tm) )
    msgs = {'msg_00' : tm_stamp,
            'msg_01' : ''
           }
    
    return json.dumps(msgs)

#############################################
# analysis UI - BDTtoServer
#
@app.route('/post_BDTtoServer', methods=['POST'])
def post_BDTtoServer():
    #data = json.loads(request.data)
    #value = data['value']
    #
    global gIsAnaStarted
    global gBDTtextData

    # send BDT run
    accept_socket()
    write_to_socket(TCP_BDT_REQ_MSG)
    # wait till completed
    time.sleep(1.0)
    write_to_socket(TCP_DEV_READY_MSG)
    from_client = ''
    while from_client == '':
        from_client = read_from_socket(blockingTimer = 3)
    #
    tm = time.time()
    tm_stamp = ( "%s [%.3f]" % (datetime.datetime.fromtimestamp(tm).strftime('%Y-%m-%d %H:%M:%S'), tm) )
    msgs = {'msg_00' : tm_stamp,
            'msg_01' : ''
           }
    
    return json.dumps(msgs)

#############################################
# analysis UI - BDTtoFile
#
@app.route('/post_BDTtoFile', methods=['POST'])
def post_BDTtoFile():
    #data = json.loads(request.data)
    #value = data['value']
    #
    global gIsAnaStarted
    global gBDTtextData

    # write to file
    #
    # coding here
    #
    tm = time.time()
    tm_stamp = ( "%s [%.3f]" % (datetime.datetime.fromtimestamp(tm).strftime('%Y-%m-%d %H:%M:%S'), tm) )
    msgs = {'msg_00' : tm_stamp,
            'msg_01' : ''
           }
    
    return json.dumps(msgs)    

#############################################
# graphics - time series UI - drawing
#
@app.route('/post_graphTime', methods=['POST'])
def post_graphTime():
    #data = json.loads(request.data)
    #value = data['value']

    # read sensor data from file    
    f = open(WSN_LOG_FILE_NAME, "r")
    print("WSN-S> open sensor data log file: %s" % WSN_LOG_FILE_NAME)
    # skip 4 header line 
    for _ in range(4):
        row = f.readline()
        print("WSN-S> header: %s" % row)
    # init    
    x = []
    y = []
    n = 0
    # read x, y, z accelometer values
    while n < 9600:
        try:
            row = f.readline()
        except:
            break
        if not row:
            break
        if row.find('End') != -1:
            print("WSN-S> end-of-data at [%d]" % n)
            break        
        if len(row) < 7:
            print("WSN-S> incomplete line at [%d]" % n)
        else: 
            try:
                col = row.split(',')
                x_val = float(int(col[0])) / 3200.0
                #
                # here, put more option 
                # - option: sum(abs(x), abx(y), abx(z))
                y_val = abs(int(col[2])) + abs(int(col[3])) + abs(int(col[4]))
                #
                x.append(x_val)
                y.append(y_val)
            except:
                print("WSN-S> error line at [%d]" % n)
            n += 1        
    # fill zero    
    while n < 9600:
        n += 1
        x_val = float(n) / 3200.0
        y_val = 0.
        x.append(x_val)
        y.append(y_val)

    print("WSN-S> read [%d] lines of data" % n)    
    f.close()

    return json.dumps({ 'x': x, 'y': y })

#############################################
# graphics - frequency UI - drawing
#
@app.route('/post_graphFreq', methods=['POST'])
def post_graphFreq():
    #data = json.loads(request.data)
    #value = data['value']

    # read sensor data from file    
    f = open(WSN_LOG_FILE_NAME, "r")
    print("WSN-S> open sensor data log file: %s" % WSN_LOG_FILE_NAME)
    # skip 4 header line 
    for _ in range(4):
        row = f.readline()
        print("WSN-S> header: %s" % row)
    # init       
    y = []
    n = 0
    # read x, y, z accelometer values
    while n < 9600:
        try:
            row = f.readline()
        except:
            break
        if not row:
            break
        if row.find('End') != -1:
            print("WSN-S> end-of-data at [%d]" % n)
            break        
        if len(row) < 7:
            print("WSN-S> incomplete line at [%d]" % n)
        else: 
            try:
                col = row.split(',')
                #
                # here, put more option 
                # - option: sum(abs(x), abx(y), abx(z))
                y_val = abs(int(col[2])) + abs(int(col[3])) + abs(int(col[4]))
                #
                y.append(y_val)
            except:
                print("WSN-S> error line at [%d]" % n)
            n += 1        
    print("WSN-S> read [%d] lines of data" % n)    
    f.close()          
    # prepare fourier Transform
    print("WSN-S> prepare FFT")
    sampling_frequency = 3200
    amplitude = np.ndarray( n )
    # copy amplitude
    idx = 0
    while idx < n:
        amplitude[idx] = y[idx]
        idx += 1
    # run fourier Transform
    fourier_transform = np.fft.fft(amplitude)/len(amplitude)            # Normalize amplitude
    fourier_transform = fourier_transform[range(int(len(amplitude)/2))] # Exclude sampling frequency
    tp_count    = len(amplitude)
    values      = np.arange(int(tp_count/2))
    time_period = tp_count/sampling_frequency
    frequencies = values/time_period
    print("WSN-S> done FFT")
    # convert to list
    x = []
    y = []
    idx = 1
    n = tp_count/2
    while idx < n:   
        x_val = float(frequencies[idx])
        y_val = abs(float(fourier_transform[idx]))
        x.append(x_val)
        y.append(y_val)
        idx += 1
    
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
        ## accept_socket(ACCEPT_WAIT_TIME)
        app.run(host='0.0.0.0')
    close_socket()
    print("WSN-S> all done !")
#
#############################################        