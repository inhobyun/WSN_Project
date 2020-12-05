"""
Code to test async I/O client

by Inho Byun, Researcher/KAIST
   inho.byun@gmail.com
                    started 2020-11-05
                    last updated 2020-11-12
"""
import asyncio
import socket
import sys
import time

#############################################
# target definitions to TCP Server
#############################################
#
# target TCP Server identifiers
#
##TCP_HOST_NAME   = '125.131.73.31'
##TCP_HOST_NAME   = '127.0.0.1'
TCP_HOST_NAME   = '10.2.2.3'
TCP_PORT        = 8088
TCP_DEV_READY_MSG   = 'DEV_READY'
TCP_DEV_CLOSE_MSG   = 'DEV_CLOSE'
TCP_STE_START_MSG   = 'STE_START'
TCP_STE_STOP_MSG    = 'STE_STOP'
TCP_STE_REQ_MSG     = 'STE_REQ'
#
# global variables
#
gTCPreader  = None
gTCPwriter  = None
gTCPrxMsg   = None


#############################################
# function to open tcp connection
#############################################
#
async def tcp_open(is_wait, loop):
    global TCP_HOST_NAME
    global TCP_PORT
    global gTCPreader
    global gTCPwriter

    gTCPreader, gTCPwriter = await asyncio.open_connection(TCP_HOST_NAME, TCP_PORT)

#############################################
# function to open tcp connection
#############################################
#
async def tcp_close(is_wait, loop):
    global TCP_HOST_NAME
    global TCP_PORT
    global gTCPreader
    global gTCPwriter

    gTCPwriter.close()

#############################################
# handle to receive command message
#############################################
#
async def tcp_RX_message(tx_msg, loop):
    global TCP_HOST_NAME
    global TCP_PORT
    global gTCPreader
    global gTCPwriter
    global gTCPrxMsg

    print('\n+----\nAIO C-> receive command...')
    gTCPreader, gTCPwriter = await asyncio.open_connection(TCP_HOST_NAME, TCP_PORT)

    if tx_msg != None:
        print('AIO C-> [TX] "%r" wait...' % tx_msg)
        gTCPwriter.write(tx_msg.encode())
        await gTCPwriter.drain()
        print('AIO C-> [TX] "%r" sent' % tx_msg)
    print('AIO C-> [RX] try...')
    rx_data = None
    try:
        rx_data = await asyncio.wait_for ( gTCPreader.read(512), timeout=.5 )
    except asyncio.TimeoutError:
        pass 
    if rx_data != None:
        gTCPrxMsg = rx_data.decode()
        print('AIO C-> [RX] "%r"' % gTCPrxMsg)
    
    gTCPwriter.close()        
    
#############################################
# handle to send data
#############################################
#
async def tcp_TX_data(tx_msg, loop):
    global TCP_HOST_NAME
    global TCP_PORT
    global gTCPreader
    global gTCPwriter
    global gTCPrxMsg

    print('\n+----\nAIO C-> send data...')
    gTCPreader, gTCPwriter = await asyncio.open_connection(TCP_HOST_NAME, TCP_PORT)

    print('AIO C-> [RX] try...')
    rx_msg = None
    try:
        rx_data = await asyncio.wait_for ( gTCPreader.read(512), timeout=.5 )
    except asyncio.TimeoutError:
        pass
    else:
        rx_msg = rx_data.decode()
        print('AIO C-> [RX] "%r"' % rx_msg)

    if gTCPrxMsg == TCP_STE_REQ_MSG and rx_msg == None:
        if tx_msg == None:
            tx_msg = input('AIO C-> input data to server: ')
        print('AIO C-> [tx] "%r" wait...' % tx_msg)
        tx_data = tx_msg.encode()
        gTCPwriter.write(tx_data)
        await gTCPwriter.drain()        
        print('AIO C-> [tx] "%r" sent' % tx_msg)

    gTCPwriter.close()        

#############################################
#############################################
#         
# Main starts here
#
#############################################

loop = asyncio.get_event_loop()
##loop.run_until_complete(tcp_open(True, loop))
while gTCPrxMsg != TCP_DEV_CLOSE_MSG:
    try:
        loop.run_until_complete(tcp_RX_message(TCP_DEV_READY_MSG, loop))
        if gTCPrxMsg == TCP_STE_REQ_MSG:
            loop.run_until_complete(tcp_TX_data('(12345678901234567890123456789012345678901234567890123456789012345678901234567890)', loop))
    except KeyboardInterrupt:
        break
    print( '.', end = '')    
##loop.run_until_complete(tcp_close(True, loop))
loop.close()