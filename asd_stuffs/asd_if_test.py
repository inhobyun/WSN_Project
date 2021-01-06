"""
client application for edge computing device
coded functions as below
- BLE sensor device; BOSCH SCD 110 scan & connect using bluepy.btle

by Inho Byun, Researcher/KAIST
   inho.byun@gmail.com
                    started 2020-12-30
"""
import asyncio
import datetime
import socket
import struct
import sys
import time
from urllib import request, parse

import ADS1256
import RPi.GPIO as GPIO

#
# constant values
#
TEST_DURATION = 10.0

#
# gloval
#
gData = []


#############################################
# get_g_value 
#
def get_g_value (chNumber):
        v_val = ADC.ADS1256_GetChannalValue(chNumber)*5.0/0x7fffff
        g_val = v_val - 1.5 # ZERO g BIAS typical 1.5, x & y: 1.35~1.65, z: 1.2~1.8
        g_val = g_val * 0.3 # typical 300mV, 270~330mV
        return g_val

#############################################
#############################################
#         
# Main starts here
#
print ("ASD--> ADS1256 Test Program", flush=True)

try:
    ADC = ADS1256.ADS1256()
    ADC.ADS1256_init()
except :
    GPIO.cleanup()
    print ("ASD--> ADS1256 init fail, unknown error !", flush=True)
    sys.exit(-1)

t_0 = t = time.time()
n = 0
while t_1 - t_0 < TEST_DURATION:
        x = get_g_value (3)
        y = get_g_value (4)
        z = get_g_value (5)
        t = time.time()
        n += 1
        gData.append(t)
        gData.append(x)
        gData.append(y)
        gData.append(z)

print ("ASD--> record %d rows, start: %f, end: %f; %f sec" % (n, t_0, t, t-t_0 ), flush=True)

