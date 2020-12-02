"""
Code to test async I/O server 

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
TCP_HOST_NAME   = socket.gethostname()
##TCP_HOST_NAME   = '10.2.2.3'
##TCP_HOST_NAME   = '127.0.0.1'
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
gTCPtxMsg   = None

#############################################
# handle RX_TX
#############################################
#
async def handle_RX_TX(reader, writer):
    global gTCPrxMsg
    global gTCPtxMsg

    if gTCPtxMsg == TCP_STE_REQ_MSG:
        print('AIO S-> [RX] try...')
        try:
            rx_data = await asyncio.wait_for ( reader.read(512), timeout=10.0 )
        except asyncio.TimeoutError:
            pass
        else:
            gTCPrxMsg = rx_data.decode()
            addr = writer.get_extra_info('peername')
            print('AIO S-> [RX] "%r" from "%r"' % (gTCPrxMsg, addr))
    else:        
        tx_msg = input('AIO S-> input command to client: ')
        print('\n>>>>>')
        if tx_msg != '':
            print('AIO S-> [TX] try')
            tx_data = tx_msg.encode()
            writer.write(tx_data)
            await writer.drain()
            gTCPtxMsg = tx_msg
            print('AIO C-> [TX] "%r" sent' % gTCPtxMsg)

    print('AIO S-> close the client socket')
    print('<<<<<')
    writer.close()

#############################################
#############################################
#         
# Main starts here
#
#############################################

loop = asyncio.get_event_loop()
coro = asyncio.start_server(handle_RX_TX, TCP_HOST_NAME, TCP_PORT, loop=loop)
server = loop.run_until_complete(coro)

# Serve requests until Ctrl+C is pressed
print('AIO S-> Serving on {}'.format(server.sockets[0].getsockname()))
try:
    loop.run_forever()
except KeyboardInterrupt:
    pass

# Close the server
server.close()
loop.run_until_complete(server.wait_closed())
loop.close()