"""
Sensor data monitoring and analysis application based on flask WEB application framework

usage: python wsn_server_SCD.py [port#]

by Inho Byun, Researcher/KAIST
   inho.byun@gmail.com
                    started 2020-10-01
                    updated 2020-12-09; monitoring, graph drawing working
                    updated 2020-12-10; acquisition
                    updated 2020-12-20; mobile UI, multi-monitoring protection, polling
                    updated 2020-12-22; data log file name
                    updated 2020-12-28; DEV_OPEN
                    updated 2020-12-31; argv Bug fix
                    updated 2021-01-06; graph drawing updated
                    updated 2021-08-03; updated port #
"""
import datetime
from flask import Flask, redirect, request
from jinja2 import Environment, PackageLoader, Markup, select_autoescape
import json
import numpy as np
from markupsafe import escape
import math
## import matplotlib.pyplot as plotter
import os, fnmatch
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
TCP_HOST_NAME   = socket.gethostname()
TCP_PORT        = 8082              # Default TCP Port Name
TCP_HTTP_PORT   = 5000              # Default WEB server port
TCP_PACKET_MAX  = 4096              # max TCP packet size
TCP_POLL_TIME   = 300.              # max time interval to poll TCP port
TCP_ERR_CNT_MAX = 8                 # max unknown error count before reconnection
#
TCP_DEV_READY_MSG = 'DEV_READY'     # server message to check client ready
TCP_DEV_OPEN_MSG  = 'DEV_OPEN'      # server message to connect client
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
ACCEPT_WAIT_TIME  = 9               # time period to wait client connection
#
MAX_X_LIMIT       = 9600            # X-Axis point limit 
#
WSN_LOG_FILE_PATH   = "./static/log"
WSN_LOG_FILE_NAME   = "WSN_log.csv"
WSN_LOG_FILE_PREFIX = "WSN_log"
WSN_LOG_FILE_SUFFIX = ".csv"
WSN_STAMP_TIME      = "server time"
WSN_STAMP_DELAY     = "delay time"
WSN_STAMP_FREQ      = "accelometer ODR"
#
# global variables
#
gSocketServer   = None
gSocketConn     = None
gSocketAddr     = None
gTCPerrCnt      = 0
gTCPlastTime    = 0.
#
gBDTtextList    = []
#
gSTElockFlag    = False 
gBDTlockFlag    = False

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
    global gTCPerrCnt
    global gTCPlastTime

    #
    if len(sys.argv) > 1:
        print ("TCP-S> take argument as port# (default: %d)" % TCP_PORT, flush=True)
        TCP_PORT = int(sys.argv[1])
    gSocketServer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #
    if gSocketServer != None:
        print ("TCP-S> socket created", flush=True)
        print ("TCP-S> trying to bind %s:%d" % (TCP_HOST_NAME, TCP_PORT), flush=True )
        try:
            gSocketServer.bind((TCP_HOST_NAME, TCP_PORT))
        except:
            print ("TCP-S> binding fail... Exiting...", flush=True)
            return False
    else:
        print ("TCP-S> socket creation fail... Exiting...", flush=True)
        return False
    print ("TCP-S> binded...", flush=True)    
    gSocketServer.listen(clientNum)
    print ("TCP-S> listening...", flush=True) 
    gTCPerrCnt = 0
    gTCPlastTime = time.time()
    #
    return True 
#############################################
# refresh socket
#
def refresh_socket(clientNum = 1):
    global gSocketServer
    global gSocketConn
    global gSocketAddr
    global gTCPerrCnt
    global gTCPlastTime
    #
    if gSocketConn != None:
        print ("TCP-S> close accepted connection", flush=True)
        gSocketConn.close()
        gSocketConn = gSocketAddr = None
        gTCPlastTime = gTCPerrCnt = 0
    #
    if gSocketServer != None:
        gSocketServer.listen(clientNum)
        print ("TCP-S> listening...", flush=True) 
        gTCPerrCnt = 0
        gTCPlastTime = time.time()
    else:
        print ("TCP-S> socket is null ... Exiting...", flush=True)
        return False
    #
    return True    

#############################################
# close socket
#
def close_socket():
    global gSocketServer
    global gSocketConn
    global gSocketAddr
    global gTCPerrCnt
    global gTCPlastTime
    #
    if gSocketConn != None:
        print ("TCP-S> close accepted connection", flush=True)
        gSocketConn.close()
        gSocketConn = gSocketAddr = None
        gTCPlastTime = gTCPerrCnt = 0
    #
    if gSocketServer != None:
        print ("TCP-S> close socket", flush=True)
        gSocketServer.close()
        gSocketServer = None
    #
    return    

##############################################
# check TCP error
#
def check_tcp_error():
    global gTCPerrCnt
    #
    if gTCPerrCnt > TCP_ERR_CNT_MAX:
        refresh_socket()
        return True

    return False

##############################################
# accept socket
#
def accept_socket(blockingTimer = 8):
    global gSocketServer
    global gSocketConn
    global gSocketAddr
    global gTCPerrCnt
    global gTCPlastTime
    #
    check_tcp_error()
    if gSocketConn == None:
        print ("----->\nTCP-S> wait client; accepting => ", end = '', flush=True)
        try:
            gSocketServer.setblocking(blockingTimer)
            gSocketConn, gSocketAddr = gSocketServer.accept()
        except:
            print ("error !\n----->", flush=True)
            gSocketConn = gSocketAddr = None
            return False         
        print ("accepted port# [", gSocketAddr, "]\n----->", flush=True)
        gTCPlastTime = time.time()
    return True    

##############################################
# read from socket
#
def read_from_socket(blockingTimer = 8):
    global gSocketServer
    global gSocketConn
    global gTCPerrCnt
    global gTCPlastTime
    #
    accept_socket(3)
    print ("TCP-S> [RX] wait => ", end = '', flush=True)
    rx_msg = ''
    gSocketServer.setblocking(blockingTimer)
    try:
        data = gSocketConn.recv(TCP_PACKET_MAX)
    except TimeoutError:
        print ("timeout !", flush=True)
    except Exception as e:
        gTCPerrCnt += 1
        print ('error "%r"!' % (e), flush=True)
    else: 
        rx_msg = data.decode()
        n = len(rx_msg)
        if n < 40:
            print ('received "%r"' % rx_msg, flush=True)
        else:
            txt = rx_msg[0:40]
            txt.replace('\n','\\n')
            print ('received "%r"...; %d bytes' % (txt ,n), flush=True)
        gTCPlastTime = time.time()        
    #    
    return rx_msg   

#############################################
# write to socket
#
def write_to_socket(tx_msg):
    global gSocketServer
    global gSocketConn
    global gTCPerrCnt
    global gTCPlastTime
    #
    accept_socket(3)
    print ("TCP-S> [TX] try => ", end = '', flush=True)
    try:
        gSocketConn.send(tx_msg.encode())
    except Exception as e:
        gTCPerrCnt += 1
        print ('error "%r"!' % (e), flush=True)
    else:
        print ('"%r" sent to WSN client' % tx_msg, flush=True)
        gTCPlastTime = time.time()
    #    
    return
#
#############################################

#############################################
#         
# misc. stuffs
#
#############################################
# time stamp retuen
#
def time_stamp():
    tm = time.time()
    return ( "%s (%.3f)" % (datetime.datetime.fromtimestamp(tm).strftime('%Y-%m-%d %H:%M:%S'), tm) )

#############################################
# get stamp string from header lines
#
def stamp_heder(header, target):
    rtn_stamp = 'unknown'
    if header.find(target) != -1:
        idx = header.find(':')
        if idx >= len(target): 
            rtn_stamp = header[idx+1:].strip() 
    return rtn_stamp

#############################################
#############################################
#         
# flask stuffs
# - main menu
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
# base MOBILE UI
#
@app.route('/m')
def mroot():
    template = env.get_template('mmain.html')
    return template.render()    

#############################################
# Ooops UI
#
@app.route('/m_Ooops')
def Ooops():
    template = env.get_template('m_Ooops.html')
    return template.render()

#############################################
# sensor monitoring MOBILE UI
#
@app.route('/m_mobile')
def mobile():
    template = env.get_template('m_mobile.html')
    return template.render()

#############################################
# sensor monitoring UI
#
@app.route('/m_monitor')
def monitor():
    template = env.get_template('m_monitor.html')
    return template.render()

#############################################
# acquisition UI
#
@app.route('/m_acquisition')
def acquisition():
    template = env.get_template('m_acquisition.html')
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
# about UI - MOBILE
#
@app.route('/m_intro_0')
def intro_0():
    template = env.get_template('m_intro_0.html')
    return template.render()

#############################################
#         
# sub-menu button stuffs
#

#############################################
# monitoring UI - start
#
@app.route('/post_monStart', methods=['POST'])
def post_monStart():
    data = json.loads(request.data)
    value = data['value']
    #
    global gSTElockFlag
    global gBDTlockFlag

    # check client socket connect
    if (gSocketConn == None):
        rows = {'row' : [time_stamp(),'*','*','*','*','*','*','*','*','*','*','*'],
                'status' : ['[sensor device]', '[is disconnected]'],
                'timer' : 'off'
               }
        return json.dumps(rows)   

    # check STE, BDT lock flag
    if (value==0 and  gSTElockFlag) or gBDTlockFlag:
        rows = {'row' : [time_stamp(),'*','*','*','*','*','*','*','*','*','*','*'],
                'status' : ['[locked]', '[by other user]'],
                'timer' : 'off'
               }
        write_to_socket(TCP_STE_STOP_MSG)
        gSTElockFlag = False                     
        return json.dumps(rows)   

    # send STE start & request
    print('WSN-S> monitoring count "%r"' % value, flush=True)
    if value==0: 
        write_to_socket(TCP_STE_START_MSG)
        from_client = None
    elif value<11:    
        gSTElockFlag = True
        write_to_socket(TCP_STE_REQ_MSG)
        from_client = read_from_socket(blockingTimer = 20)
    else:
        post_monStop()
        return    
    # get the data to post
    if from_client != None and from_client != '':
        from_client = from_client.replace(')','')
        from_client = from_client.replace('(','')
        vals = from_client.split(',')     
        try:
            # get the status
            val_x = float(vals[2])
            val_y = float(vals[4])
            val_z = float(vals[6])
        except Exception as e:
            print('WSN-S> error during monitoring, "%r"' % (e), flush=True)
            status = ['UNKNOWN', 'UNKNOWN']
        else:    
            # ===========================================
            # analyz more to display status afterward....
            # ===========================================
            if max(val_x, val_y, val_z) >= 0.7 or (val_x > 0.2 and val_y > 0.2  and val_z > 0.2):        
                status = ['VIBRATION', 'ABNORMAL']
            elif max(val_x, val_y, val_z) >= 0.2:
                status = ['VIBRATION', 'NORMAL']
            elif val_x == 0.0 and val_y == 0.0  and val_z == 0.0: 
                status = ['STOP', 'NORMAL']
            else:    
                status = ['STOP', 'UNKNOWN']
            # ===========================================
        rows = {'row' : vals, 'status' : status, 'timer' : 'on' }
    else:                          
        rows = {'row' : [time_stamp(),'?','?','?','?','?','?','?','?','?','?','?'],
                'status' : ['-?-', '-?-'],
                'timer' : 'on'
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
    global gSTElockFlag

    # send STE stop
    write_to_socket(TCP_STE_STOP_MSG)
    gSTElockFlag = False

    rows = {'row' : [time_stamp(),'*','*','*','*','*','*','*','*','*','*','*'],
            'status' : ['---', '---'],
            'timer' : 'off'
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
    global gSTElockFlag
    global gBDTlockFlag
    global gBDTtextList

    # check client socket connect
    if (gSocketConn == None):
        msgs = {'msg_00' : "sensor device is disconnected",
                'msg_01' : 'N'
           }
        return json.dumps(msgs)

    # check BDT lock flag
    if gBDTlockFlag or gSTElockFlag:
        msgs = {'msg_00' : "somebody is running BDT or STE",
                'msg_01' : 'N'
           }
        return json.dumps(msgs)

    # send BDT run
    write_to_socket(TCP_BDT_RUN_MSG)
    time.sleep(3.0)
    # wait till echo-back
    write_to_socket(TCP_BDT_END_MSG)
    from_client = ''
    while from_client != TCP_BDT_END_MSG:
        from_client = read_from_socket(blockingTimer = 8)
    #
    msgs = {'msg_00' : time_stamp(),
            'msg_01' : 'Y'
           }

    # release BDT lock flag
    gBDTlockFlag = False    
    
    return json.dumps(msgs)

#############################################
# analysis UI - BDTtoServer
#
@app.route('/post_BDTtoServer', methods=['POST'])
def post_BDTtoServer():
    #data = json.loads(request.data)
    #value = data['value']
    #
    global gSTElockFlag
    global gBDTlockFlag
    global gBDTtextList

    # check BDT lock flag
    if gBDTlockFlag or gSTElockFlag:
        msgs = {'msg_00' : "somebody is running BDT or STE",
                'msg_01' : 'N'
           }
        return json.dumps(msgs)
    else:    
        gBDTlockFlag = True    

    # init data buffer
    gBDTtextList = []
    while True:
        # send BDT request
        ##accept_socket()
        time.sleep(0.1)
        write_to_socket(TCP_BDT_REQ_MSG)
        time.sleep(0.1)
        # get data from client
        from_client = ''
        while from_client == '':
            from_client = read_from_socket(blockingTimer = 8)
        if from_client.find('End of Data') == -1:
            gBDTtextList.append(from_client)
        else:
            gBDTtextList.append(from_client)
            break
    #
    msgs = {'msg_00' : time_stamp(),
            'msg_01' : 'Y'
           }

    # release BDT lock flag
    gBDTlockFlag = False    
    
    return json.dumps(msgs)

#############################################
# analysis UI - BDTtoFile
#
@app.route('/post_BDTtoFile', methods=['POST'])
def post_BDTtoFile():
    data = json.loads(request.data)
    value = data['value']
    #
    global gSTElockFlag
    global gBDTlockFlag
    global gBDTtextList

    # check BDT lock flag
    if gBDTlockFlag or gSTElockFlag:
        msgs = {'msg_00' : "somebody is running BDT or STE",
                'msg_01' : 'N'
           }
        return json.dumps(msgs)
    else:    
        gBDTlockFlag = True    

    # write to file
    idx = 0
    n = len(gBDTtextList)
    fmark = value.strip().replace(' ', '_')
    fname  = WSN_LOG_FILE_PATH
    fname += '/' + WSN_LOG_FILE_PREFIX
    fname += '_' + datetime.datetime.fromtimestamp(time.time()).strftime('%Y%m%d%H%M%S')
    if fmark != '':
        fname += '_' + fmark
    fname += WSN_LOG_FILE_SUFFIX
    f = open(fname, "w")
    for idx in range(n):
        f.write(gBDTtextList[idx])
    f.close()
    #
    msgs = {'msg_00' : time_stamp() + ' "' + fname + '" was created',
            'msg_01' : 'Y'
           }

    # release BDT lock flag
    gBDTlockFlag = False    

    return json.dumps(msgs)    

#############################################
# graphics - time series UI - drawing
#
@app.route('/post_graphTime', methods=['POST'])
def post_graphTime():
    data = json.loads(request.data)
    value = data['value']
    fname = data['fname']
    if fname == '':
        fname = WSN_LOG_FILE_NAME
    else:
        fname = WSN_LOG_FILE_PATH + '/' + fname    
    # read sensor data from file    
    f = open(fname, "r")
    print("WSN-S> open sensor data log file: %s" % fname, flush=True)
    # check 4 header lines
    row = f.readline()
    time_stamp = stamp_heder(row,WSN_STAMP_TIME)
    row = f.readline()
    time_stamp += '+' + stamp_heder(row,WSN_STAMP_DELAY)
    row = f.readline()
    freq_stamp = stamp_heder(row,WSN_STAMP_FREQ)
    freq_str = ''.join([c for c in freq_stamp if c in '0123456789.'])
    row = f.readline()
    # init    
    x = []
    y = []
    x_base = n_base = n = 0
    # read x, y, z accelometer values
    while n < MAX_X_LIMIT:
        try:
            row = f.readline()
        except Exception as e:
            print('WSN-S> error line at [%d], "%r"' % (n, e), flush=True)
            break
        if not row:
            break
        if row.find('End') != -1:
            print("WSN-S> end-of-data at [%d]" % n, flush=True)
            break        
        if len(row) < 7:
            print("WSN-S> incomplete line at [%d]" % n, flush=True)
        else: 
            try:
                col = row.split(',')
                if col[1] == '':
                    x_val = x_base + (n - n_base) / float(freq_str)
                else:
                    x_val = float(col[1])
                    if n==0:
                        x_offset = x_val
                    x_val -= x_offset
                    x_base = x_val
                    n_base = int(col[0])
                # ===========================================
                # here, handle more options afterward 
                # - option: sum, x, y, z
                # - ...
                # ===========================================
                if value == 'X only':
                    y_val = abs(float(col[2]))
                elif value == 'Y only':
                    y_val = abs(float(col[3]))
                elif value == 'Z only':
                    y_val = abs(float(col[4]))
                else:
                    y_val = abs(float(col[2])) + abs(float(col[3])) + abs(float(col[4]))              
                # ===========================================
                x.append(x_val)
                y.append(y_val)
            except Exception as e:
                print('WSN-S> error line at [%d], "%r"' % (n, e), flush=True)
            n += 1        
    # fill zero    
    ##while n < 9600:
    ##  n += 1
    ##  x_val = float(n) / 3200.0
    ##  y_val = 0.
    ##  x.append(x_val)
    ##  y.append(y_val)
    #
    print("WSN-S> read [%d] lines of data" % n, flush=True)    
    f.close()

    return json.dumps({ 'x': x, 'y': y, 't': time_stamp, 'f': freq_stamp, 'm': value })

#############################################
# graphics - frequency UI - drawing
#
@app.route('/post_graphFreq', methods=['POST'])
def post_graphFreq():
    data = json.loads(request.data)
    fname = data['fname']
    if fname == '':
        fname = WSN_LOG_FILE_NAME
    else:
        fname = WSN_LOG_FILE_PATH + '/' + fname    
    # read sensor data from file    
    f = open(fname, "r")
    print("WSN-S> open sensor data log file: %s" % fname, flush=True)
    # check 4 header lines
    row = f.readline()
    time_stamp = stamp_heder(row,WSN_STAMP_TIME)
    row = f.readline()
    time_stamp += '+' + stamp_heder(row,WSN_STAMP_DELAY)
    row = f.readline()
    freq_stamp = stamp_heder(row,WSN_STAMP_FREQ)
    freq_str = ''.join([c for c in freq_stamp if c in '0123456789.'])
    row = f.readline()
    # init       
    y = []
    n = 0
    # read x, y, z accelerometer values
    while n < MAX_X_LIMIT:
        try:
            row = f.readline()
        except Exception as e:
            print('WSN-S> error line at [%d], "%r"' % (n, e), flush=True)
            break
        if not row:
            break
        if row.find('End') != -1:
            print("WSN-S> end-of-data at [%d]" % n, flush=True)
            break        
        if len(row) < 7:
            print("WSN-S> incomplete line at [%d]" % n, flush=True)
        else: 
            try:
                col = row.split(',')
                # ===========================================
                # here, handle more options afterward 
                # - option: sum(abs(x), abx(y), abx(z))
                # - ...
                # ===========================================
                y_val = abs(float(col[2])) + abs(float(col[3])) + abs(float(col[4]))
                # ===========================================
                y.append(y_val)
            except Exception as e:
                print('WSN-S> error line at [%d], "%r"' % (n, e), flush=True)
            n += 1        
    print("WSN-S> read [%d] lines of data" % n, flush=True)    
    f.close()          
    # prepare fourier Transform
    print("WSN-S> prepare FFT", flush=True)
    sampling_frequency = float(freq_str)
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
    print("WSN-S> done FFT", flush=True)
    # convert to list
    x = []
    y = []
    idx = 1
    n = int(tp_count/2)
    while idx < n:
        try:   
            x_val = float(frequencies[idx])
            y_val = abs(float(fourier_transform[idx]))
        except Exception as e:
            print('WSN-S> error point at [%d], "%r"' % (idx, e), flush=True)
            x_val = y_val = 0.
        x.append(x_val)
        y.append(y_val)
        idx += 1
    
    return json.dumps({ 'x': x, 'y': y, 't': time_stamp, 'f': freq_stamp, 'm': 'Fourier Transform' })

#############################################
#         
# misc stuffs
#

#############################################
#
# DEVICE READY polling
@app.route('/get_polling/<message>', methods=['GET'])
def get_polling(message):
    global gSocketConn
    global gSocketAddr

    msg = escape(message)
    ret_msg = '' 
    print('WSN-S> "%r" reeived from WSN client' % msg, flush=True)
    if msg == TCP_DEV_READY_MSG or msg == TCP_STE_STOP_MSG or msg == TCP_DEV_CLOSE_MSG:
        if gSocketConn != None:
            write_to_socket(msg)
            ret_msg = 'replied: ' + msg + ' at ' + time_stamp() + ' to WSN client'
            if msg == TCP_DEV_CLOSE_MSG:
                gSocketConn.close()
                gSocketConn = gSocketAddr = None
        else:
            ret_msg = 'could not reply: ' + msg + ' at ' + time_stamp() + ' to WSN client'    
    elif msg == TCP_DEV_OPEN_MSG:
        if gSocketConn == None:
            accept_socket(ACCEPT_WAIT_TIME)
    #        
    return ret_msg

#############################################
#
# log file listing
@app.route('/post_logList', methods=['POST'])
def post_logList():
    #data = json.loads(request.data)
    #value = data['value']
    #
    rows = []
    listOfFiles = os.listdir(WSN_LOG_FILE_PATH + '/')
    pattern = "*" + WSN_LOG_FILE_SUFFIX
    for entry in listOfFiles:
        if fnmatch.fnmatch(entry, pattern):
                rows.append(entry)
    print('WSN-S> "%d" log files listed ' % len(rows), flush=True)                       

    return json.dumps({'rows' : rows})

#############################################
#############################################
#         
# Main starts here
#
#############################################
#
if __name__ == '__main__':
    print("WSN-S> starting !", flush=True)
    try:
        if open_socket():
            #
            # flask web server running
            #
            app.run(host='0.0.0.0', port=5000)
            #
    ## except KeyboardInterrupt: # does not work, seems caught by flask
    except:     
        print("WSN-S> error during running, close client...", flush=True)
        write_to_socket(TCP_DEV_CLOSE_MSG)
    close_socket()
    print("WSN-S> all done !", flush=True)
#
#############################################        