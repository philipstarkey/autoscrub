#!/usr/bin/python

import monarchcommand as mnc
import RPi.GPIO as gpio
import time

# IP address of the Monarch
target_ip = '130.194.171.212'

# Username and password (default is admin/admin)
usr = 'admin'
pwd = 'admin'

# Parameters
max_fails = 3
connection_fails = 0
recording = False

# Create MonarchHD instance
monarch = mnc.MonarchHD(target_ip, username=usr, password=pwd)

# Setup GPIO
gpio.setwarnings(False)  # Ignore GPIO warnings
gpio.setmode(gpio.BOARD) # Use board pin numbering
leds = {'blue': 36, 'green': 38, 'red': 40}
for i in leds.values():
    gpio.setup(i, gpio.OUT)
    gpio.output(i, False)

# Display blinking pattern at startup
for j in range(3):
    for i in leds.values():
        gpio.output(i, True)
        time.sleep(0.2)
        gpio.output(i, False)

def led_on(colour):
    for c, i in leds.items():
        if c == colour:
            gpio.output(i, True)
        else:
            gpio.output(i, False)


def update_status():
    global connection_fails; global recording
    if connection_fails >= max_fails:
        led_on('blue')
        print('Connection failure')
    try:
        status = monarch.GetStatus()
        print(status.text)
        if status.text.startswith('RECORD:ON'):
            led_on('red')
            recording = True
        elif status.text.startswith('RECORD:READY'):
            led_on('green')
            recording = False
        elif status.text.startswith('SUCCESS'):
            if recording:
                led_on('green')
                recording = False
            else:
                led_on('red')
                recording = True
        elif status.text.startswith('RECORD:DISABLED'):
            led_on('blue')
            recording = False
        else:
            # Undefined status
            led_on('blue')
            recording = False
        connection_fails = 0
    except mnc.requests.ConnectionError:
        print('Connection failed. Tying again shortly...')
        # led_on('blue')
        connection_fails += 1
    except Exception as e:
        print(e)
        led_on(None)

if True: #__name__ == '__main__':
    print('Starting...')
    while True:
        try:
           update_status()
           time.sleep(4)
        except KeyboardInterrupt:
           print('Quitting...')
           led_on(None)
           break
        except Exception as e:
           print('Unhandled exception... quitting.')
           led_on(None)
           break
