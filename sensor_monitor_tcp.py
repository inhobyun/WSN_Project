"""
Sensor data monitoring and analysis application based on flask WEB application framework

by Inho Byun, Researcher/KAIST
   inho.byun@gmail.com
                    started 2020-10-01
                    last updated 2020-11-09
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

#############################################
#############################################
#         
# flask stuffs
#
#############################################

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

    # global definitions
    global gSocketServer
    global TCP_DEV_READY_MSG
    global TCP_DEV_CLOSE_MSG
    global TCP_STE_START_MSG
    global TCP_STE_STOP_MSG

    # Prepare data to post
    rows = {'row_01' : 'TBD',
            'row_02' : 'TBD',
            'row_03' : 'TBD',
            'row_04' : 'TBD',
            'row_05' : 'TBD',
            'row_06' : 'TBD',
            'row_07' : 'TBD',
            'row_08' : 'TBD',
            'row_09' : 'TBD',
            'row_10' : 'TBD',
            'row_11' : 'TBD'
           }

    # send STE start
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
            elif from_client[0] == '(':
                break
    except KeyboardInterrupt:
        print ('TCP S-> keybord interrupted... Send "%s" to client...' % TCP_STE_STOP_MSG)
        conn.send(TCP_STE_STOP_MSG.encode())
        time.sleep(5.)
        print ('TCP S-> Send "%s" to client and Exiting...' % TCP_DEV_CLOSE_MSG)
        conn.send(TCP_DEV_CLOSE_MSG.encode())
        conn.close()
        return json.dumps(rows)
    except:
        print ('TCP S-> unknown exception... Exiting...')
        return json.dumps(rows)

    # get the data to post
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
    conn.close()
    print ('TCP S-> client disconnected, count is', cnt)
    
    return json.dumps(rows)

@app.route('/post_monStop', methods=['POST'])
def post_monStop():
    data = json.loads(request.data)
    value = data['value']

    # global definitions
    global gSocketServer
    global TCP_DEV_READY_MSG
    global TCP_DEV_CLOSE_MSG
    global TCP_STE_START_MSG
    global TCP_STE_STOP_MSG

    # Prepare data to post
    rows = {'row_01' : '--.-',
            'row_02' : '--.--',
            'row_03' : '--.-',
            'row_04' : '--.--',
            'row_05' : '--.-',
            'row_06' : '--.--',
            'row_07' : '--.--',
            'row_08' : '---.---',
            'row_09' : '---.-',
            'row_10' : '---.-',
            'row_11' : '---.-'
           }

    # send STE stop
    try:
        print("TCP S-> listen & accepting...")
        conn, addr = gSocketServer.accept()
        conn.send(TCP_STE_STOP_MSG.encode())
        from_client = ''
        cnt = 0
        while True:
            data = conn.recv(1024)
            if not data:
                break
            cnt += 1
            from_client = data.decode()
            print ("TCP S-> received [%s]" % (from_client))
    except KeyboardInterrupt:
        print ('TCP S-> keybord interrupted... Send "%s" to client...' % TCP_STE_STOP_MSG)
        conn.send(TCP_STE_STOP_MSG.encode())
        time.sleep(5.)
        print ('TCP S-> Send "%s" to client and Exiting...' % TCP_DEV_CLOSE_MSG)
        conn.send(TCP_DEV_CLOSE_MSG.encode())
        conn.close()
        return json.dumps(rows)
    except:
        print ('TCP S-> unknown exception... Exiting...')
        return json.dumps(rows)

    # get the data to post   
    rows = {'row_01' : '$$.$',
            'row_02' : '00.00',
            'row_03' : '00.0',
            'row_04' : '00.00',
            'row_05' : '00.0',
            'row_06' : '00.00',
            'row_07' : '00.00',
            'row_08' : '000.000',
            'row_09' : '000.0',
            'row_10' : '000.0',
            'row_11' : '$$$.$'
           }               
    conn.close()
    print ('TCP S-> client disconnected, count is', cnt)

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

if __name__ == '__main__':
    app.run(host='0.0.0.0')