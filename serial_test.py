import struct
import time
import serial

ser = serial.Serial('/dev/ttyACM0', 9600)

if __name__ == "__main__":
    while True:
        str = input()
        ser.write(str.encode("utf_8"))

        data = ser.readline()
        rtn = data.decode("utf-8").replace('\n','')
        print(rtn)