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
TCP_HOST_NAME   = '125.131.73.31'
TCP_PORT        = 8088
TCP_DEV_READY_MSG   = 'DEV_READY'
TCP_DEV_CLOSE_MSG   = 'DEV_CLOSE'
TCP_STE_START_MSG   = 'STE_START'
TCP_STE_STOP_MSG    = 'STE_STOP'
TCP_STE_REQ_MSG     = 'STE_REQ'
#
# global variables
#
gTCPrxMsg   = None

#############################################
# handle to receive command message
#############################################
#
async def tcp_RX_command(tx_msg, loop):
    global gTCPrxMsg

    reader, writer = await asyncio.open_connection(TCP_HOST_NAME, TCP_PORT)

    print('\nAIO C-> receive command...')
    if tx_msg != ''
        print('AIO C-> [TX] "%r"' % tx_msg)
        writer.write(tx_msg.encode())

    print('AIO C-> [RX] wait...')
    gTCPrxMsg = None
    try:
        rx_data = await asyncio.wait_for ( reader.read(512), timeout=1.0 )
    except asyncio.TimeoutError:
        pass
    else:
        gTCPrxMsg = rx_data.decode()
        print('AIO C-> [RX] "%r"' % gTCPrxMsg)

    print('AIO C-> close the socket')
    writer.close()

#############################################
# handle to send data
#############################################
#
async def tcp_TX_data(tx_msg, loop):
    global gTCPrxMsg

    reader, writer = await asyncio.open_connection(TCP_HOST_NAME, TCP_PORT)

    print('\nAIO C-> send data...')
    print('AIO C-> [RX] wait...')
    gTCPrxMsg = None
    try:
        rx_data = await asyncio.wait_for ( reader.read(512), timeout=1.0 )
    except asyncio.TimeoutError:
        pass
    else:
        gTCPrxMsg = rx_data.decode()
        print('AIO C-> [RX] "%r"' % gTCPrxMsg)

    if gTCPrxMsg == '' or gTCPrxMsg == TCP_STE_REQ_MSG:
        if tx_msg == '':
            tx_msg = input('AIO C-> input data to server: ')
        print('AIO C-> [tx] "%r"' % tx_msg)
        tx_data = tx_msg.encode()
        writer.write(tx_data)
        await writer.drain()        
        print('AIO C-> [tx] sent')

    print('AIO C-> close the socket')
    writer.close()

#############################################
#############################################
#         
# Main starts here
#
#############################################

loop = asyncio.get_event_loop()

while gTCPrxMsg != TCP_DEV_CLOSE_MSG:
    try:
        loop.run_until_complete(tcp_RX_command(TCP_DEV_READY_MSG, loop))
        loop.run_until_complete(tcp_TX_data('(client data)', loop))
    except KeyboardInterrupt:
        break    

loop.close()