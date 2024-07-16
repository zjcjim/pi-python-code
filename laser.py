import RPi.GPIO as GPIO
import time

laser_pin = 14
GPIO.setmode(GPIO.BCM)
GPIO.setup(laser_pin, GPIO.OUT)

for i in range(10):
    GPIO.output(laser_pin, GPIO.HIGH)
    time.sleep(0.5)
    GPIO.output(laser_pin, GPIO.LOW)
    time.sleep(0.5)