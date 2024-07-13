# data structure: "(int)MA(int)MB(int)MC(int)MD(float)SA(float)SB"

import struct
import time
import serial

ser = serial.Serial('/dev/ttyACM0', 9600)

if __name__ == "__main__":
    while True:
        motor1 = 10
        motor2 = 20
        motor3 = 30
        motor4 = 40

        servo1 = -50
        servo2 = 30

        send = str(motor1) + " " + str(motor2) + " " + str(motor3) + " " + str(motor4) + " " + str(servo1) + " " + str(servo2) + "\n"
        ser.write(send.encode("utf_8"))
        
        data = ser.readline()
        rtn = data.decode("utf-8").replace('\n','')
        print(rtn)
        time.sleep(0.05)
