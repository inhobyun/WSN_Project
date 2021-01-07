"""
client application for edge computing device
coded functions as below
- Analog sensor device; ADXL335 + Wavwshare AD/DA Board (ADC: ADS1256)
- server connect using asyncio
- getting server message and run routine upon the message
- start or stop sensor running called STE; Short Time Experiment
- getting sensor STE data
- getting sensor memory data using BDT; Block Data Transfer

by Inho Byun, Researcher/KAIST
   inho.byun@gmail.com
                    syarted 2021-01-07;
"""
import asyncio
## from bluepy.btle import Scanner, DefaultDelegate, UUID, Peripheral
import datetime
import socket
import struct
import sys
import time
from urllib import request, parse

import ADS1256
import RPi.GPIO as GPIO

#############################################
# target definitions to interface ASD(Analog Sensor Device)
#############################################
#
STE_RUN_TIME    = 3.0    # STE rolling time in secconds for SENSOR data recording
STE_FREQUENCY   = (400, 800, 1600, 3200, 6400)  # of STE result 400 / 800 / 1600 / 3200 / 6400 Hz
#
WSN_STAMP_TIME      = "server time"
WSN_STAMP_DELAY     = "delay time"
WSN_STAMP_FREQ      = "accelometer ODR" 
#
# global variables
#
gScannedCount = 0     # count of scanned BLE devices
# STE - Short Time Experiment
gSTEcfgMode   = bytes(35)  # Sensor Mode
gSTEnotiCnt   = 0     # count of notifications from connected device
gSTEstartTime = 0.    # notification start timestamp
gSTElastTime  = 0.    # last notification timestamp
gSTElastData  = None  # last notification data
gSTEisRolling = False # flag wether STE is on rolling
# BDT - Block Data Transfer
gBDTnotiCnt   = 0
gBDTstartTime = 0.   
gBDTlastTime  = 0.
gBDTdata      = bytearray(SCD_MAX_FLASH)
gBDTtextBlock = ''
gBDTtextLen   = 0
gBDTtextPos   = 0
gBDTcrc32     = bytearray(4)
gBDTisRolled = False
# IDLE
gIDLElastTime = 0.    # last BLE traffic on connection


#############################################
# target definitions to TCP Server
#############################################
#
# target TCP Server identifiers
#
##TCP_HOST_NAME = "127.0.0.1"       # TEST Host Name
##TCP_HOST_NAME = "10.2.2.3"        # TEST Host Name
##TCP_HOST_NAME = "192.168.0.3"     # TEST Host Name
TCP_HOST_NAME   = "125.131.73.31"   # Default Host Name
TCP_PORT        = 8088              # Default TCP Port Name
##TCP_HTTP_PORT = 5000              # origin flask WEB server port
TCP_HTTP_PORT   = 8081              # WEB server http port
TCP_PACKET_MAX  = 1024              # max TCP packet size
TCP_POLL_TIME   = 300.              # max time interval to poll TCP port
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
# global variables
#
gTCPlastTime = 0.
gTCPreader   = None
gTCPwriter   = None
gTCPrxMsg    = None
gTCPtxMsg    = None
gTCPrxNull   = 0

#############################################
# polling flask server via HTTP
#############################################
#
def http_polling(pol_msg = TCP_DEV_READY_MSG):
    global gTCPreader
    global gTCPwriter
    global TCP_HOST_NAME
    global TCP_PORT
    global TCP_HTTP_PORT
    #
    print('----->\nWSN-C> HTTP polling try => ', end='', flush=True)
    url_str = 'http://%s:%s/get_polling/%s' % (TCP_HOST_NAME, TCP_HTTP_PORT, pol_msg)
    rtn_str = ''
    try: 
        f = request.urlopen(url_str)
        print('sent => ',  end='', flush=True)
        rtn_str = f.read().decode()
        f.close()
    except:
        print('error !\n----->')
        sys.exit(-1)
    else:
        print('"%r" received\n----->' % rtn_str)
    
    return rtn_str

#############################################
# send & receive via http port of flask server
#############################################
#
async def http_TX(tx_msg, loop):
    global gTCPreader
    global gTCPwriter
    #
    print('----->\nAIO-C> connecting http server to write & read ... ', end ='', flush=True)
    try:
        reader, writer = await asyncio.open_connection(TCP_HOST_NAME, TCP_HTTP_PORT)
    except asyncio.TimeoutError:
        print('timeout !\n----->', flush=True)
    except:
        print('error !\n----->', flush=True)
        sys.exit(-1)
    else:    
        print('connected\n----->', flush=True)
        # send 'GET /get_polling/%s HTTP/1.1'
        tx_data = ('GET /get_polling/%s HTTP/1.1' % tx_msg).encode('ascii')
        # send GET
        print('AIO-C> [HTTP TX] try => ', end = '', flush=True) 
        try:        
            writer.write(tx_data)
            await asyncio.wait_for ( writer.drain(), timeout=3.0 )
        except asyncio.TimeoutError:
            print('timeout !', flush=True)
        except:
            print('error !', flush=True)
            sys.exit(-1)
        else:
            print('"%r" sent' % tx_msg, flush=True)
        # connect server
        ## rx_corout = asyncio.wait_for ( reader.read(TCP_PACKET_MAX), timeout=3.0 )
        if tx_msg == TCP_DEV_OPEN_MSG:
            print('AIO-C> connecting to server => ',  end='', flush=True)
            if gTCPwriter != None:
                gTCPwriter.close()
                gTCPwriter = None
            try:    
                gTCPreader, gTCPwriter = await asyncio.open_connection(TCP_HOST_NAME, TCP_PORT)
            except asyncio.TimeoutError:
                print('timeout !', flush=True)
            except:
                print('error !', flush=True)
                sys.exit(-1)
            else:    
                print('connected', flush=True)
        # receive
        '''
        print('AIO-C> [HTTP RX] wait => ', end = '', flush=True)    
        rx_msg = ''
        rx_data = None
        try:
            rx_data = await asyncio.wait_for ( reader.read(TCP_PACKET_MAX), timeout=3.0 )
            ## rx_data = await rx_corout
        except asyncio.TimeoutError:
            print('timeout', flush=True)
        except:
            print('error !', flush=True)
            sys.exit(-1)
        else:
            if rx_data != None:
                rx_msg = rx_data.decode()
            if rx_msg == '':
                print('null received', flush=True)
            else:
                print('"%r" received' % rx_msg, flush=True)
        '''      
        #
        writer.close()        

#############################################
# handle to receive command message
#############################################
#
async def tcp_RX(loop):
    global gTCPlastTime
    global gTCPrxMsg
    global gTCPreader
    global gTCPwriter
    global gTCPrxNull
    #
    if ( gTCPwriter != None ):
    #
        rx_data = None
        print('AIO-C> [RX] wait => ', end = '', flush=True)    
        try:
            rx_data = await asyncio.wait_for ( gTCPreader.read(TCP_PACKET_MAX), timeout=10.0 )
        except asyncio.TimeoutError:
            print('timeout', flush=True)
        except ConnectionResetError:
            print('connection error !', flush=True)
            gTCPwriter = gTCPreader = None
        except:
            print('unknown error !', flush=True)
            sys.exit(-1)
        else:
            if rx_data != None:
                gTCPrxMsg = rx_data.decode()
            else:
                gTCPrxNull += 1
            if gTCPrxMsg == '':
                gTCPrxNull += 1
                print('null received: %d times' % gTCPrxNull, flush=True)
                time.sleep(1.)
            else:
                gTCPrxNull = 0
                print('"%r" received' % gTCPrxMsg, flush=True)
            gTCPlastTime = time.time()     
    
#############################################
# handle to send data
#############################################
#
async def tcp_TX(tx_msg, loop):
    global gTCPlastTime
    global gTCPrxMsg
    global gTCPreader
    global gTCPwriter
    #
    if ( gTCPwriter != None ):
    #
        if tx_msg != None and tx_msg != '':
            print('AIO-C> [TX] try => ', end = '', flush=True)        
            tx_data = tx_msg.encode()
            try:        
                gTCPwriter.write(tx_data)
                await asyncio.wait_for ( gTCPwriter.drain(), timeout=10.0 )
            except asyncio.TimeoutError:
                print('timeout !', flush=True)
            except ConnectionResetError:
                print('connection error !', flush=True)
                gTCPwriter = gTCPreader = None
            except:
                print('unknown error !', flush=True)
                sys.exit(-1)
            else:
                n = len(tx_msg)
                if n < 40:        
                    print('"%r" sent' % tx_msg, flush=True)
                else:
                    txt = tx_msg[0:40]
                    txt.replace('\n','\\n')
                    print('"%r"...; %d bytes sent' % (txt, n), flush=True)
                gTCPlastTime = time.time()        
        else:
            print('AIO-C> [TX] nothing to send !', flush=True)    

#############################################
# functions definition
#############################################

#############################################
# convert hex() string to format like "hh.hh.hh"
#
def hex_str( vBytes ):
    #
    vString = ''.join(['.' + ch if i % 2 == 0 and i != 0 else ch for i, ch in enumerate(vBytes.hex())])
    #
    return vString

   return


#############################################
# Define ASD_connect
#
# should implement "BTLEDisconnectError" exception
#
#############################################
def ASD_connect( is_first = True ):

   return p    


#############################################
# run STE & BLK data transfer
#
def ASD_run_STE_and_BDT():
    global gBDTisRolled
    global gBDTnotiCnt
    global gBDTstartTime
    global gBDTlastTime    
    #
    # rolls STE for certain time period
    #
    # start STE w/ memory writing
    print ("ASD--> Recording STE starting ...", flush=True)
    p.setDelegate( NotifyDelegate(p) )
    SCD_set_STE_config(p, True, True)
    SCD_toggle_STE_rolling(p, True, True)
    # take rolling time
    tm = time.time()
    while time.time() - tm <= STE_RUN_TIME:
        wait_flag = p.waitForNotifications(0.33)
        if wait_flag :
            continue
     # stop STE
    SCD_toggle_STE_rolling(p, False, False) 
    SCD_print_STE_status()
    #
    # start BDT
    #
    print ("ASD--> Bulk Data Transfer after a while ...", flush=True)
    time.sleep(0.7)
    p.setDelegate( NotifyDelegate(p) )
    print ("ASD--> BDT Starting ...", flush=True)
    time.sleep(0.7)
    p.writeCharacteristic( SCD_BDT_DATA_FLOW_HND+1, struct.pack('<H', 1) )
    time.sleep(0.7)
    p.writeCharacteristic( SCD_BDT_CONTROL_HND, b'\x01' )
    ret_val = b'x01'
    while ret_val == b'x01':  
        wait_flag = p.waitForNotifications(8.0)
        if wait_flag :
            continue
        ret_val = p.readCharacteristic( SCD_BDT_STATUS_HND )
    print ("\nASD--> Bulk Data Transfer completed...status is [%s], time [%.3f], count [%d]" % \
            (ret_val.hex(), (gBDTlastTime-gBDTstartTime), gBDTnotiCnt), flush=True )
    #
    if ret_val == b'x02':
        gBDTisRolled = True        
    return


#############################################
# create text memory block from BDT w/o non-data
#
def ASD_BDT_text_block():
    global gBDTnotiCnt
    global gBDTdata
    global gBDTtextBlock
    global gBDTtextLen
    global gBDTtextPos
    
    print ("ASD--> text block creation from BDT ...", flush=True)
    if gBDTtextBlock != '':
        del gBDTtextBlock
        gBDTtextBlock = ''
    #    
    print ("ASD--> text block [%d] bytes recorded !" % gBDTtextLen, flush=True)

#############################################
# create text memory block from BDT w/o non-data
#
def SCD_BDT_get_text(returnMax = TCP_PACKET_MAX):
    global gBDTtextBlock
    global gBDTtextLen
    global gBDTtextPos

    if gBDTtextPos >= gBDTtextLen:
        rtn = 'End of Data\n'
        gBDTtextPos = idx = 0
    else:
        idx = gBDTtextPos + returnMax    
        if idx > gBDTtextLen:
            idx = gBDTtextLen
        while ( gBDTtextBlock[idx-1:idx] != '\n' ) and ( idx > gBDTtextPos ):
            idx -= 1
        if idx > gBDTtextPos:
            rtn = gBDTtextBlock[gBDTtextPos:idx+1]
            gBDTtextPos = idx + 1
        else:
            rtn = ''
            gBDTtextPos += 1
    return rtn    

#############################################
# server message handling
#
def server_msg_handling( p ):
    global gTCPrxMsg
    global gTCPtxMsg
    global gSTElastData
    global gSTElastTime
    global gSTEisRolling
    global gBDTisRolled
    global gIDLElastTime

    # idling check
    t = time.time()
    if t - gIDLElastTime > SCD_IDLE_INTERVAL:
        SCD_run_STE_for_idling(p)
        gIDLElastTime = t
    # message handling
    if gTCPrxMsg == TCP_DEV_READY_MSG or gTCPrxMsg == TCP_DEV_OPEN_MSG:
        # polling messages that server or manually sent
        print ("WSN-C> got polling [%s] ..." % gTCPrxMsg, flush=True)
        # polling reponse here
    elif gTCPrxMsg == TCP_BDT_END_MSG:
        # polling message that server sent, should echo-back
        print ("WSN-C> got polling [%s], echo-back..." % TCP_BDT_END_MSG, flush=True)
        gTCPtxMsg = TCP_BDT_END_MSG
    elif gTCPrxMsg == TCP_STE_START_MSG:
        # start STE rolling w/o memory writing
        print ("WSN-C> start STE rolling...", flush=True)
        p.setDelegate( NotifyDelegate(p) )
        SCD_set_STE_config(p, False)
        SCD_toggle_STE_rolling(p, True, False)
        ## gIDLElastTime = time.time()
    elif gTCPrxMsg == TCP_STE_REQ_MSG:
        # request STE data
        if gSTEisRolling:
            print ("WSN-C> handover STE data ...", flush=True)
            # if not enable STE notification
            gSTElastData = p.readCharacteristic(SCD_STE_RESULT_HND)
            gSTElastTime = time.time()
            gTCPtxMsg = SCD_string_STE_data(gSTElastTime, gSTElastData)
            ## gIDLElastTime = gSTElastTime   
        else:
            print ("WSN-C> invalid message, STE has not been started !", flush=True)    
    elif gTCPrxMsg == TCP_BDT_RUN_MSG:
        # start BDT
        print ("WSN-C> start BDT running ...")
        if not gSTEisRolling:                
            SCD_run_STE_and_BDT(p)
            if SCD_clear_memory(p) == None:
                p = SCD_scan_and_connect(False)
            SCD_BDT_text_block()
            gBDTisRolled = True    
            gIDLElastTime = time.time()
        else:
            print ("WSN-C> invalid message, BDT is not allowed during rolling !", flush=True)     
    elif gTCPrxMsg == TCP_BDT_REQ_MSG:
        # request BDT data
        if gBDTisRolled:
            print ("WSN-C> request BDT data ...", flush=True)
            gTCPtxMsg = SCD_BDT_get_text()
            if gTCPtxMsg.find("End") != -1:
                gBDTisRolled = False
        else:
            print ("WSN-C> invalid message, BDT has not been done !", flush=True)    
    elif gTCPrxMsg == TCP_STE_STOP_MSG or gTCPrxMsg == TCP_DEV_CLOSE_MSG:
        # stop STE or disconnect
        print ("WSN-C> stop STE rolling ...", flush=True)
        SCD_set_STE_config (p, False)
        SCD_toggle_STE_rolling (p, False, False)
        SCD_print_STE_status()
        ## gIDLElastTime = time.time()
    elif gTCPrxMsg == TCP_DEV_CLOSE_MSG:
        # exit from loop
        print ("WSN-C> close device ...", flush=True)
    elif gTCPrxMsg != None:
        # invalid message
        print ('WSN-C> invalid [RX] message: "%r" !' % gTCPrxMsg, flush=True)    
    #
    return
#
#############################################

#############################################
#############################################
#         
# Main starts here
#
if len(sys.argv) > 1:
    print ("WSN-C> take 1'st argument as Host IP address (default: '%s')" % TCP_HOST_NAME, flush=True)
    TCP_HOST_NAME = sys.argv[1]
if len(sys.argv) > 2:
    print ("WSN-C> take 2'nd argument as tcp port# (default: '%d')" % TCP_PORT, flush=True)
    TCP_PORT = int(sys.argv[2])
if len(sys.argv) > 3:
    print ("WSN-C> take 3'rd argument as http port# (default: '%d')" % TCP_HTTP_PORT, flush=True)
    TCP_HTTP_PORT = int(sys.argv[3])

#
# scan and connect SCD
#
p = SCD_scan_and_connect(True)
#
# set STE configuration
#
SCD_set_STE_config(p, False, True)
#
# read Device Info. such as Name, Manufacurer Name, etc.
#
SCD_print_info(p)
#
# check STE is rolling or not, memory is empty or not; stop rolling & cleanup memory
#
SCD_check_STE_rolling(p)
SCD_toggle_STE_rolling(p, False, False)
if  SCD_clear_memory(p) == None:
    p = SCD_scan_and_connect(False)
#
# connect server
#
loop = asyncio.get_event_loop()
loop.run_until_complete( http_TX(TCP_DEV_OPEN_MSG, loop) )
#############################################
#
# loop if not TCP_DEV_CLOSE_MSG 
#
gTCPlastTime = gIDLElastTime = time.time()
while gTCPrxMsg != TCP_DEV_CLOSE_MSG:
    #
    # if too many null messages
    #
    if gTCPrxNull > 3:
            print ("WSN-C> too many null received, exiting !", flush=True)
            break
    #
    # if any messae to send
    #
    if gTCPtxMsg != None:
        loop.run_until_complete( tcp_TX(gTCPtxMsg, loop) )
    #
    # wait any message from server
    #
    gTCPtxMsg = gTCPrxMsg = None
    loop.run_until_complete( tcp_RX(loop) )
    #
    # does message handling
    #
    try:
        server_msg_handling( p )
    except Exception as e:
        print ('WSN-S> error "%r" while message loop ... reconnecting ...' % (e), flush=True)
        p = SCD_scan_and_connect(False)
        if  SCD_clear_memory(p) == None:
            p = SCD_scan_and_connect(False)
    #
    # if last server communication time is longer than poll time, polling via http
    #
    if time.time() - gTCPlastTime > TCP_POLL_TIME:
            http_polling()
            ## loop.run_until_complete( http_TX(TCP_DEV_READY_MSG, loop) )
#
#############################################

#############################################
#
# complete
#
loop.close()
print ("WSN-C> all done ...", flush=True)
#
#############################################
