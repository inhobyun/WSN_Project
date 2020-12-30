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


print ("\332J") # clear screen
print ("\33[H") # cursor to upper, left corner
print ("ASD--> ADS1256 Test Program", end='', flush=True)

try:
    ADC = ADS1256.ADS1256()
    ADC.ADS1256_init()
except :
    GPIO.cleanup()
    print ("\33[3,1H")
    print ("ASD--> ADS1256 init fail, unknown error !", end='', flush=True)
    exit()

cnt = 0
t0 = t1 = time.time()
while ( t1 - t0 < 1.0 ):
        ADC_Value = ADC.ADS1256_GetAll()
        t1 = time.time()
        print ("\33[2,1H")
        print ("ASD--> #1 [%lf]"%(ADC_Value[1]*5.0/0x7fffff), end='', flush=True)
        cnt += 1

print ("\33[3,1H")
print ("ASD--> count [%d]", end='', flush=True)

GPIO.cleanup()

print ("\33[5,1H")
print ("ASD--> completed", flush=True)