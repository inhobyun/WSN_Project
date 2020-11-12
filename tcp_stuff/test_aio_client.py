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

#############################################
# handle RX_TX
#############################################
#
async def tcp_TX_client(tx_msg, loop):
    reader, writer = await asyncio.open_connection(TCP_HOST_NAME, TCP_PORT,
                                                   loop=loop)

    print('AIO C-> [TX] "%r"' % tx_msg)
    writer.write(tx_msg.encode())

    rx_data = await reader.read(512)
    print('AIO C-> [RX] "%r"' % rx_data.decode())

    print('AIO C-> close the socket')
    writer.close()

#############################################
#############################################
#         
# Main starts here
#
#############################################

loop = asyncio.get_event_loop()
loop.run_until_complete(tcp_TX_client(TCP_DEV_READY_MSG, loop))
loop.close()