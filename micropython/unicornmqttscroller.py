# Asynchronous mqtt client with clean session (C) Copyright Peter Hinch 2017-2019.
# Released under the MIT licence.

# Public brokers https://github.com/mqtt/mqtt.github.io/wiki/public_brokers

# The use of clean_session means that after a connection failure subscriptions
# must be renewed (MQTT spec 3.1.2.4). This is done by the connect handler.
# Note that publications issued during the outage will be missed. If this is
# an issue see unclean.py.

# red LED: ON == WiFi fail
# blue LED heartbeat: demonstrates scheduler is running.


# Import libraries - config.py sets up wifi and mqtt
import time
from galactic import GalacticUnicorn
from picographics import PicoGraphics, DISPLAY_GALACTIC_UNICORN as DISPLAY


from mqtt_as import MQTTClient, config
from config import wifi_led, blue_led  # Local definitions
import uasyncio as asyncio
import machine
from machine import Pin, PWM
from time import sleep
import _thread


# constants for controlling scrolling text
PADDING = 2
MESSAGE_COLOUR = (255, 255, 255)
OUTLINE_COLOUR = (0, 0, 0)
MESSAGE = ""
# BACKGROUND_COLOUR = (10, 0, 96) # Blue
BACKGROUND_COLOUR = (120, 120, 0)  # Yellow
HOLD_TIME = 2.0
STEP_TIME = 0.045  # Edit to slow down/speed up text - lower for faster scrolling

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

cancel_thread = False
thread_running = False


# MQTT Message Subscription and Display


def sub_cb(topic, msg, retained):
    print(f'Topic: "{topic.decode()}" Message: "{msg.decode()}" Retained: {retained}')

    # state constants
    brightness = 0.5
    gu.set_brightness(brightness)
    STATE_PRE_SCROLL = 0
    STATE_SCROLLING = 1
    STATE_POST_SCROLL = 2

    shift = 0
    state = STATE_PRE_SCROLL

    def outline_text(text, x, y):
        graphics.set_pen(
            graphics.create_pen(
                int(OUTLINE_COLOUR[0]), int(OUTLINE_COLOUR[1]), int(OUTLINE_COLOUR[2])
            )
        )
        graphics.text(text, x - 1, y - 1, -1, 1)
        graphics.text(text, x, y - 1, -1, 1)
        graphics.text(text, x + 1, y - 1, -1, 1)
        graphics.text(text, x - 1, y, -1, 1)
        graphics.text(text, x + 1, y, -1, 1)
        graphics.text(text, x - 1, y + 1, -1, 1)
        graphics.text(text, x, y + 1, -1, 1)
        graphics.text(text, x + 1, y + 1, -1, 1)

        graphics.set_pen(
            graphics.create_pen(
                int(MESSAGE_COLOUR[0]), int(MESSAGE_COLOUR[1]), int(MESSAGE_COLOUR[2])
            )
        )
        graphics.text(text, x, y, -1, 1)

    DATA = msg.decode("utf-8")
    MESSAGE = str("                " + DATA + "             ")

    # calculate the message width so scrolling can happen
    msg_width = graphics.measure_text(MESSAGE, 1)

    last_time = time.ticks_ms()

    print(MESSAGE)

    while True:

        if cancel_thread:
            return

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
                state = STATE_PRE_SCROLL
                state = STATE_PRE_SCROLL
                shift = 0
                last_time = time_ms
            last_time = time_ms

        if state == STATE_POST_SCROLL and time_ms - last_time > HOLD_TIME * 1000:
            state = STATE_PRE_SCROLL
            shift = 0
            last_time = time_ms

        graphics.set_pen(
            graphics.create_pen(
                int(BACKGROUND_COLOUR[0]),
                int(BACKGROUND_COLOUR[1]),
                int(BACKGROUND_COLOUR[2]),
            )
        )
        graphics.clear()

        outline_text(MESSAGE, x=PADDING - shift, y=2)

        # update the display
        gu.update(graphics)

        # pause for a moment (important or the USB serial device will fail)
        sleep(0.001)


# Demonstrate scheduler is operational.
async def heartbeat():
    s = True
    while True:
        await asyncio.sleep_ms(500)
        blue_led(s)
        s = not s

async def wifi_up(up):
    await up.wait()
    print("Wifi is up")
    await client.subscribe("personal/ucfnaps/led/#", 1)


async def main(client):
    try:
        asyncio.create_task(wifi_up(client.up))
        await client.connect()
    except OSError:
        print("Connection failed.")
        # machine.reset()
        raise

    task = None
    while True:
        async for msg in client.queue:
            global thread_running
            global cancel_thread
            if not thread_running:
                _thread.start_new_thread(sub_cb, (msg[0], msg[1], msg[2]))
                thread_running = True
            else:
                cancel_thread = True
                sleep(1)
                _thread.start_new_thread(sub_cb, (msg[0], msg[1], msg[2]))
                cancel_thread = False
            await asyncio.sleep(1)


# Define configuration
config["queue_len"] = 10
config["clean"] = True

# Set up client
MQTTClient.DEBUG = True  # Optional
client = MQTTClient(config)

print("Starting")

asyncio.create_task(heartbeat())


try:
    asyncio.run(main(client))
except Exception as e:
    print(e)

finally:
    client.close()  # Prevent LmacRxBlk:1 errors
    asyncio.new_event_loop()
