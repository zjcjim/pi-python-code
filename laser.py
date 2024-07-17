import RPi.GPIO as GPIO
import time

laser_pin = 14
GPIO.setmode(GPIO.BCM)
GPIO.setup(laser_pin, GPIO.OUT)

while True:
    try:
        GPIO.output(laser_pin, GPIO.HIGH)
        time.sleep(0.2)
        GPIO.output(laser_pin, GPIO.LOW)
        time.sleep(0.2)
    except KeyboardInterrupt:
        GPIO.output(laser_pin, GPIO.LOW)
        GPIO.cleanup()
        break