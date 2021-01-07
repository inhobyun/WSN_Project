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
STE_RUN_TIME = 6.0
#
WSN_LOG_FILE_PATH   = "./static/log"
WSN_LOG_FILE_NAME   = "WSN_Data_log.csv"
WSN_LOG_FILE_PREFIX = "WSN_Data_log"
WSN_LOG_FILE_SUFFIX = ".csv"
WSN_STAMP_TIME      = "server time"
WSN_STAMP_DELAY     = "delay time"
WSN_STAMP_FREQ      = "accelometer ODR"
#
# global variables
#
# BDT - Block Data Transfer
gBDTstartTime = 0.   
gBDTlastTime  = 0.
gBDTdata      = []
gBDTtextBlock = ''
gBDTtextLen   = 0
gBDTtextPos   = 0



#############################################
# get_g_value 
#
def get_g_value (chNumber):
        v_val  = ADC.ADS1256_GetChannalValue(chNumber)*5.0/0x7fffff
        g_val  = v_val - 1.5 # ZERO g BIAS typical 1.5, x & y: 1.35~1.65, z: 1.2~1.8
        g_val *= 0.3 # 1g = typical 300mV, 270~330mV
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

print ("ASD--> recording => ", end='', flush=True)
t_0 = t = time.time()
rows = 0
while t - t_0 < STE_RUN_TIME:
        x = get_g_value (3)
        y = get_g_value (4)
        z = get_g_value (5)
        t = time.time()
        rows += 1
        gBDTdata.append(t)
        gBDTdata.append(x)
        gBDTdata.append(y)
        gBDTdata.append(z)
frequency = float(rows)/(t-t_0)
print (" %d rows, duration: %f, ODR: %f" % (rows, (t-t_0), frequency), flush=True)

print ("ASD--> formatting => ", end='', flush=True)
gBDTtextBlock  = ("server time: %s(%f)\n" %  ( (datetime.datetime.fromtimestamp(t_0).strftime('%Y-%m-%d %H:%M:%S'), t_0) ))
gBDTtextBlock += ("delay time: %.3f\n" % ( 0. ))
gBDTtextBlock += ("accelometer ODR: %.3f Hz\n" % frequency) 
gBDTtextBlock += ("Row #, Time-Stamp, X-AXIS, Y-AXIS, Z-AXIS\n")
for i in range(rows):
        idx = i*4
        gBDTtextBlock += ("%d,%.5f,%.2f,%.2f,%.2f\n" % (i+1, gBDTdata[idx]-t_0, gBDTdata[idx+1], gBDTdata[idx+2], gBDTdata[idx+3]))
gBDTtextBlock += ("End of Data\n")
gBDTtextLen = len(gBDTtextList)
print ("formtted", flush=True)        

print ('ASD--> writing data to log file => ', end='', flush=True)
fmark = "ADXL335"
fname  = WSN_LOG_FILE_PATH
fname += '/' + WSN_LOG_FILE_PREFIX
fname += '_' + datetime.datetime.fromtimestamp(time.time()).strftime('%Y%m%d%H%M%S')
fname += '_' + fmark
fname += WSN_LOG_FILE_SUFFIX
f = open(fname, "w")
for i in range(gBDTtextLen):
        f.write(gBDTtextList[i])
f.close()
print ('"%s" created' % (fname), flush=True)    

print ('ASD--> completed !', flush=True)
