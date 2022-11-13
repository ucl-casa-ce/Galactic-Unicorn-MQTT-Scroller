# clean.py Test of asynchronous mqtt client with clean session.
# (C) Copyright Peter Hinch 2017-2019.
# Released under the MIT licence.

# Public brokers https://github.com/mqtt/mqtt.github.io/wiki/public_brokers

# The use of clean_session means that after a connection failure subscriptions
# must be renewed (MQTT spec 3.1.2.4). This is done by the connect handler.
# Note that publications issued during the outage will be missed. If this is
# an issue see unclean.py.

# red LED: ON == WiFi fail
# blue LED heartbeat: demonstrates scheduler is running.

#Import libraries - config.py sets up wifi and mqtt

from mqtt_as import MQTTClient, config
from config import wifi_led, blue_led  # Local definitions
import uasyncio as asyncio
import machine
from machine import Pin, PWM
import time
from time import sleep
import sys




# Set up Servo and Data Range
servoPin = PWM(Pin(16))
servoPin.freq(50)

servospeed = 0.05 #Speed of the servo movement - 0.05 provides a good smooth speed
servorange = 90
# Calibrate data to degrees - Servo Range / Data Range (in our case Data Range is 60 for 0-60MPH)


# Set up list for data and max/min/average as required


leftMin = 950
leftMax = 1050
rightMin = 0
rightMax = 90
global servodegrees
global mqttdata 

def translate():
    global servodegrees
    #Calculate Range
    leftSpan = leftMax - leftMin
    rightSpan = rightMax - rightMin
    
    #Convert range to float
    valueScaled = float(mqttdata - leftMin) / float(leftSpan)
    #Create Range
    servodegrees = rightMin + (valueScaled * rightSpan)
    print (servodegrees) 

def servo(degrees):
    # limit degrees beteen 0 and 180
    if degrees > 180: degrees=180
    if degrees < 0: degrees=0
    # set max and min duty
    #Reverse order to change direction according to servo
    
    maxDuty=9000
    minDuty=1000
    # new duty is between min and max duty in proportion to its value
    newDuty=minDuty+(maxDuty-minDuty)*(degrees/180)
    # servo PWM value is set
    servoPin.duty_u16(int(newDuty))


# First Sweep Config - Degree Range to be Edited According to Servo and Data Range
# Edit out (sweep) further down once configured

def sweep():
    n= 0
    while n < servorange :
      
        servo(n)
        sleep(servospeed)
        n = n+1
        
    sleep(4)    
    n= servorange
    while n >= 0 :
      
        servo(n)
        sleep(servospeed)
        n = n-1


# Subscription callback
def sub_cb(topic, msg, retained):
    print(f'Topic: "{topic.decode()}" Message: "{msg.decode()}" Retained: {retained}')
    global mqttdata
    global servodegrees
    mqttdata = float(msg)
    print("Pressure =  ", mqttdata)
  #run the data through the translate function to remap range  
    translate()
    servo(servodegrees)
    sleep(servospeed)
  #Sleep  
  #  wlan.disconnect()
  #  wlan.active(False)
  #  wlan.deinit()
    sleep(60)
  #  machine.lightsleep(1000)

     
# Demonstrate scheduler is operational.
async def heartbeat():
    s = True
    while True:
        await asyncio.sleep_ms(500)
        blue_led(s)
        s = not s

async def wifi_han(state):
    wifi_led(not state)
    print('Wifi is ', 'up' if state else 'down')
   # sweep()
    await asyncio.sleep(1)

# If you connect with clean_session True, must re-subscribe (MQTT spec 3.1.2.4)
async def conn_han(client):
    await client.subscribe('personal/ucfnaps/downhamweather/barometer_mbar', 1)

async def main(client):
    try:
        await client.connect()
    except OSError:
        print('Connection failed.')
        machine.reset()
        return
    n = 0
    while True:
        await asyncio.sleep(5)
       # print('publish', n)
        # If WiFi is down the following will pause for the duration.
        #await client.publish('result', '{} {}'.format(n, client.REPUB_COUNT), qos = 1)
        n += 1

# Define configuration
config['subs_cb'] = sub_cb
config['wifi_coro'] = wifi_han
config['connect_coro'] = conn_han
config['clean'] = True

# Set up client
MQTTClient.DEBUG = True  # Optional
client = MQTTClient(config)

asyncio.create_task(heartbeat())


try:
    asyncio.run(main(client))
    

finally:
    client.close()  # Prevent LmacRxBlk:1 errors
    asyncio.new_event_loop()