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
TEST_DURATION = 1.0

print ("ASD--> ADS1256 Test Program", flush=True)

try:
    ADC = ADS1256.ADS1256()
    ADC.ADS1256_init()
except :
    GPIO.cleanup()
    print ("ASD--> ADS1256 init fail, unknown error !", flush=True)
    exit()

cnt = 0
t0 = t1 = time.time()
while ( t1 - t0 < TEST_DURATION ):
        t1 = time.time()
        print ('ASD--> at %f\x0d'%(t1), flush=True)
        print ("\33[2A", flush=True)
        cnt += 1
        
print ('\nASD--> count [%d] time period: %f, %f'%(cnt, (t1-t0), (t1-t0)/cnt), flush=True)


cnt = 0
t0 = t1 = time.time()
while ( t1 - t0 < TEST_DURATION ):
        val_x = ADC.ADS1256_GetChannalValue(0)
        t1 = time.time()
        print ('ASD--> [%lf] at %f\x0d'%(val_x*5.0/0x7fffff, t1), flush=True)
        print ("\33[2A", flush=True)
        cnt += 1
        
print ('\nASD--> count [%d] time period: %f, %f'%(cnt, (t1-t0), (t1-t0)/cnt), flush=True)

cnt = 0
t0 = t1 = time.time()
while ( t1 - t0 < TEST_DURATION ):
        val_x = ADC.ADS1256_GetChannalValue(0)
        val_y = ADC.ADS1256_GetChannalValue(1)
        val_z = ADC.ADS1256_GetChannalValue(2)
        t1 = time.time()
        print ('ASD--> [%lf][%lf][%lf] at %f\x0d'%(val_x*5.0/0x7fffff, val_y*5.0/0x7fffff, val_z*5.0/0x7fffff, t1), flush=True)
        print ("\33[2A", flush=True)
        cnt += 1
        
print ('\nASD--> count [%d] time period: %f, %f'%(cnt, (t1-t0), (t1-t0)/cnt), flush=True)

GPIO.cleanup()

print ("ASD--> completed", flush=True)
