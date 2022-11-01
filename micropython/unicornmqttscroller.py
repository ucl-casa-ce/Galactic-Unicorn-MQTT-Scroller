# Asynchronous mqtt client with clean session (C) Copyright Peter Hinch 2017-2019.
# Released under the MIT licence.

# Public brokers https://github.com/mqtt/mqtt.github.io/wiki/public_brokers

# The use of clean_session means that after a connection failure subscriptions
# must be renewed (MQTT spec 3.1.2.4). This is done by the connect handler.
# Note that publications issued during the outage will be missed. If this is
# an issue see unclean.py.

# red LED: ON == WiFi fail
# blue LED heartbeat: demonstrates scheduler is running.



#Import libraries - config.py sets up wifi and mqtt
import time
from galactic import GalacticUnicorn
from picographics import PicoGraphics, DISPLAY_GALACTIC_UNICORN as DISPLAY


from mqtt_as import MQTTClient, config
from config import wifi_led, blue_led  # Local definitions
import uasyncio as asyncio
import machine
from machine import Pin, PWM
from time import sleep


# constants for controlling scrolling text
PADDING = 2
MESSAGE_COLOUR = (255, 255, 255)
OUTLINE_COLOUR = (0, 0, 0)
MESSAGE = ""
#BACKGROUND_COLOUR = (10, 0, 96)
BACKGROUND_COLOUR = (255, 255, 0)
HOLD_TIME = 2.0
STEP_TIME = 0.065 #Edit to slow down/speed up text

# create galactic object and graphics surface for drawing
gu = GalacticUnicorn()
graphics = PicoGraphics(DISPLAY)

width = GalacticUnicorn.WIDTH
height = GalacticUnicorn.HEIGHT

# state constants
STATE_PRE_SCROLL = 0
STATE_SCROLLING = 1
STATE_POST_SCROLL = 2

shift = 0
state = STATE_PRE_SCROLL

# set the font
graphics.set_font("bitmap8")

# calculate the message width so scrolling can happen
msg_width = graphics.measure_text(MESSAGE, 1)

last_time = time.ticks_ms()


# MQTT Message Subscription and Display

def sub_cb(topic, msg, retained):
    print(f'Topic: "{topic.decode()}" Message: "{msg.decode()}" Retained: {retained}')
    
        
    # state constants
    brightness = 0.1
    gu.set_brightness(brightness)
    STATE_PRE_SCROLL = 0
    STATE_SCROLLING = 1
    STATE_POST_SCROLL = 2

    shift = 0
    state = STATE_PRE_SCROLL
    def outline_text(text, x, y):
        graphics.set_pen(graphics.create_pen(int(OUTLINE_COLOUR[0]), int(OUTLINE_COLOUR[1]), int(OUTLINE_COLOUR[2])))
        graphics.text(text, x - 1, y - 1, -1, 1)
        graphics.text(text, x, y - 1, -1, 1)
        graphics.text(text, x + 1, y - 1, -1, 1)
        graphics.text(text, x - 1, y, -1, 1)
        graphics.text(text, x + 1, y, -1, 1)
        graphics.text(text, x - 1, y + 1, -1, 1)
        graphics.text(text, x, y + 1, -1, 1)
        graphics.text(text, x + 1, y + 1, -1, 1)

        graphics.set_pen(graphics.create_pen(int(MESSAGE_COLOUR[0]), int(MESSAGE_COLOUR[1]), int(MESSAGE_COLOUR[2])))
        graphics.text(text, x, y, -1, 1)
    
    DATA = (msg.decode('utf-8'))
    MESSAGE = str("                " + DATA + "             ")
    
# calculate the message width so scrolling can happen
    msg_width = graphics.measure_text(MESSAGE, 1)

    last_time = time.ticks_ms()
       

    print (MESSAGE)
    
    while True:
        time_ms = time.ticks_ms()

        if gu.is_pressed(GalacticUnicorn.SWITCH_BRIGHTNESS_UP):
            gu.adjust_brightness(+0.01)

        if gu.is_pressed(GalacticUnicorn.SWITCH_BRIGHTNESS_DOWN):
            gu.adjust_brightness(-0.01)

        if state == STATE_PRE_SCROLL and time_ms - last_time > HOLD_TIME * 1000:
            if msg_width + PADDING * 2 >= width:
                state = STATE_SCROLLING
            last_time = time_ms

        if state == STATE_SCROLLING and time_ms - last_time > STEP_TIME * 1000:
            shift += 1
            if shift >= (msg_width + PADDING * 2) - width - 1:
                state = STATE_POST_SCROLL
                brightness = 0
                gu.set_brightness(brightness)
                gu.update(graphics)
                break
            last_time = time_ms
           

        if state == STATE_POST_SCROLL and time_ms - last_time > HOLD_TIME * 1000:
            state = STATE_PRE_SCROLL
            shift = 0
            last_time = time_ms
            

        graphics.set_pen(graphics.create_pen(int(BACKGROUND_COLOUR[0]), int(BACKGROUND_COLOUR[1]), int(BACKGROUND_COLOUR[2])))
        graphics.clear()

        outline_text(MESSAGE, x=PADDING - shift, y=2)

        # update the display
        gu.update(graphics)

        # pause for a moment (important or the USB serial device will fail)
        time.sleep(0.001)
    
    
    
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
    
# MQTT Subscirbe Topic   
    await client.subscribe('personal/ucfnaps/led/#', 1)

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