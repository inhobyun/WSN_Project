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
TEST_DURATION = 6.0
#
WSN_LOG_FILE_PATH   = "./static/log"
WSN_LOG_FILE_NAME   = "WSN_Data_log.csv"
WSN_LOG_FILE_PREFIX = "WSN_Data_log"
WSN_LOG_FILE_SUFFIX = ".csv"
WSN_STAMP_TIME      = "server time"
WSN_STAMP_DELAY     = "delay time"
WSN_STAMP_FREQ      = "accelometer ODR"

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
val_odr = float(n)/(t-t_0)
print ("ASD--> record: %d rows, ODR: %f" % (n, val_odr ), flush=True)

fmark = "ADXL335"
fname  = WSN_LOG_FILE_PATH
fname += '/' + WSN_LOG_FILE_PREFIX
fname += '_' + datetime.datetime.fromtimestamp(time.time()).strftime('%Y%m%d%H%M%S')
fname += '_' + fmark
fname += WSN_LOG_FILE_SUFFIX

print ('ASD--> writing data to log file "%s"' % (fname), flush=True)

head1 = ("server time    : %s(%f)\n" %  ( (datetime.datetime.fromtimestamp(t_0).strftime('%Y-%m-%d %H:%M:%S'), t_0) ))
head2 = ("delay time     : %.3f\n" % ( 0. ))
head3 = ("accelometer ODR: %.3f Hz\n" % val_odr) 
head4 = (" Row #, Time-Stamp, X-AXIS, Y-AXIS, Z-AXIS\n")

f = open(fname, "w")

f.write(head1)
f.write(head2)
f.write(head3)
f.write(head4)
for i in range(n):
        idx = i*4
        row = ("%d,%.3f,%.2f,%.2f,%.2f\n" % (i+1, gData[idx]-t_0, gData[idx+1], gData[idx+2], gData[idx+3]))
        f.write(row)
f.write("End of Data\n")        
f.close()

print ('ASD--> completed !', flush=True)