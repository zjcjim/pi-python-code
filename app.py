from flask import Flask, request, jsonify
from flask_cors import CORS
import serial
import requests
import socket
import time
import math
import numpy as np
import os

    
last_error_x= 0
last_error_y = 0
previous_x = 0
previous_y = 0
pid_x = 0
pid_y = 0

error_x = 0
error_y = 0

motor_speeds = [0, 0, 0, 0]
servo_angle = [0.0, 0.0]

previous_angle_x = 90
previous_angle_y = 90

# initialize the motor speeds and servo angles
# send_to_arduino(motor_speeds, servo_angle)

last_error_x= 0
last_error_y = 0

PID_count = 0

target_lost_counter = 0
target_found_counter = 0

def motor_speed_smoothing(target_motor_speeds, smoothing_factor):
    global motor_speeds
    print("Processing speed smoothing...")
    print("Current motor speeds: ", motor_speeds)
    print("Target motor speeds: ", target_motor_speeds)
    diff = [x - y for x, y in zip(target_motor_speeds, motor_speeds)]
    smoothed_diff = [1 / ((diff[i] / smoothing_factor) ** 2 + 1) * diff[i] for i in range(4)]
    motor_speeds = [int(x + y) for x, y in zip(motor_speeds, smoothed_diff)]
    print("Smoothed motor speeds: ", motor_speeds)

def getCPUtemperature():
    cmd = os.popen('vcgencmd measure_temp').readline()
    CPU_TEMP = cmd.replace("temp=","Temp:").replace("'C\n","C")
    temp = float(cmd.replace("temp=","").replace("'C\n",""))
    print(CPU_TEMP)
    return temp

def PID_Servo_Control(x, y):
    global error_x, error_y, last_error_x, last_error_y, previous_x, previous_y,pid_x,pid_y
    # 下面开始pid算法：
    # pid总公式：PID = Uk + KP*【E(k)-E(k-1)】 + KI*E(k) + KD*【E(k)-2E(k-1)+E(k-2)】 
    # 这里只用到了p，所以公式为：P = Uk + KP*【E(k)-E(k-1)】
    # uk:原值   E(k):当前误差   KP:比例系数   KI:积分系数   KD:微分系数
    
    # 使用PID（可以发现舵机云台运动比较稳定）
    
    # 1 获取误差(x和y方向)（分别计算距离x、y轴中点的误差）
    error_x = x - pid_x     # width:320
    error_y = y - pid_y # height:240
    
    previous_x = x
    previous_y = y
    # 2 PID控制参数
    pwm_x = error_x * 0.8 #+ (error_x - last_error_x)*0.5
    pwm_y = error_y * 0.8 #+ (error_y - last_error_y)*0.5
    # 这里pwm（p分量） = 当前误差*3 + 上次的误差增量*1

    # 3 保存本次误差，以便下一次运算
    last_error_x = error_x
    last_error_y = error_y
    
    pid_x += pwm_x
    pid_y += pwm_y
    # p(pid的p) = 原值 + p分量
    return int(pid_x), int(pid_y)

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception as e:
        print(f"An error occurred: {e}")
        ip = "Unable to get IP"
    finally:
        s.close()
    return ip

def motor_control(previous_angle_x, is_target_lost=False):
    global motor_speeds
    motor_speed_initial = 100
    speed_diff = abs(previous_angle_x - 90)
    regulared = previous_angle_x / 90 - 1

    if is_target_lost:
        motor_speeds = [0, 0, 0, 0]
    else:
        if abs(previous_angle_x - 90) > 60:
            motor_speeds = [0, 0, 0, 0]
                 
        elif 10 <= abs(previous_angle_x - 90) <= 60:
            if previous_angle_x > 90:
                # turn left
                # add a coefficent
                motor_speed_smoothing([30, speed_diff * 1.2 + 150, speed_diff * 1.2 + 150, 30], 120)
                print("Turning left")
            else:
                # turn right
                motor_speed_smoothing([speed_diff + 150, 40, 40, speed_diff + 150], 80)
                print("Turning right")
        else:
            # go straight
            motor_speed_smoothing([100, 100, 100, 100], 60)

def capture_image(server_url):
    response = requests.get(f"{server_url}/capture")
    if response.status_code == 200:
        print("Image URL:", response.text)
    else:
        print("Failed to capture image")
    return response.text

start_time = time.time()
end_time = time.time()

def send_to_arduino(motor_speeds, servo_angle):
    global start_time, end_time
    start_time = time.time()
    gap_time = start_time - end_time

    # magic number 0.05
    if gap_time < 0.05:
        time.sleep(0.05 - gap_time)

    data = str(int(motor_speeds[0])) + " " + str(int(motor_speeds[1])) + " " + str(int(motor_speeds[2])) + " " + str(int(motor_speeds[3])) + " " + str(int(servo_angle[0])) + " " + str(int(servo_angle[1])) + "\n"
    ser.write(data.encode("utf-8"))
    print("Data send to Arduino: " + str(data))
    feedback = ser.readline()
    print("Feedback from Arduino: " + str(feedback.decode("utf-8").replace('\n','')))
    end_time = time.time()
    print(f"Time taken to send data on serial: {end_time - start_time} seconds")

server_url = "http://127.0.0.1:9000"

ip_server_url = 'http://124.71.164.229:5000'

# register pi's ip address
ip_register_url = ip_server_url + '/register'
data = {'name': 'pi', 'ip': get_local_ip()}
headers = {'Content-Type': 'application/json'}

response = requests.post(ip_register_url, json=data, headers=headers)
print(response.json())

# get backend's ip address
ip_fetch_url = ip_server_url + '/get_ips'

while True:
    try:
        response = requests.get(ip_fetch_url)
        data = response.json()
        if response.status_code == 200:
            data = response.json()
            backend_ip = data.get("backend")
            if backend_ip:
                print(f"IP address of backend: {backend_ip}")
                break
            else:
                print("Device 'backend' not found")
        else:
            print(f"Failed to fetch IPs, status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Error occurred: {e}")

    time.sleep(1)

backend_url = 'http://' + str(backend_ip) + ':5000/receive_url'

ser = serial.Serial('/dev/ttyACM0', 9600)

app = Flask(__name__)
CORS(app)

@app.route('/key', methods=['POST'])
def key_event():
    global motor_speeds
    data = request.get_json()
    key_pressed = data.get('key')
    print(f'Key pressed: {key_pressed}')

    if(key_pressed=='w'):
        print('motor forward')
        motor_speeds = [100, 100, 100, 100]
    elif(key_pressed=='s'):
        print('motor backward')
        motor_speeds = [-100, -100, -100, -100]
    elif(key_pressed=='a'):
        print('motor turn left')
        motor_speeds = [-100, 100, 100, -100]
    elif(key_pressed=='d'):
        print('motor turn right')
        motor_speeds = [100, -100, -100, 100]
    elif(key_pressed=='q'):
        print('motor stop')
        motor_speeds = [0, 0, 0, 0]
    elif(key_pressed=='p'):
        print('taking a photo')
        image_url = capture_image(server_url)
        data = {'url': image_url}

        response = requests.post(backend_url, json=data)
        print(response.status_code)
        print(response.text)
        return jsonify({'Image_URL': image_url, 'response_text': response.text})

    return jsonify({'message': 'Key received'})

@app.route('/position', methods=['POST'])
def position_event():
    global motor_speeds, servo_angle, target_lost_counter, target_found_counter
    data = request.get_json()
    current_time = time.time()
    global previous_angle_x, previous_angle_y, PID_count

    print(f'Position received at {current_time}')

    print("data: " + str(data))
    
    position_x = data.get('position_x')
    position_y = data.get('position_y')
    target_lost = data.get('target_lost')

    position_x = float(position_x)
    position_y = float(position_y)
    is_target_lost = (target_lost.lower() == 'true')

    if position_x is not None and position_y is not None:

        motor_control(previous_angle_x, is_target_lost)

        x_length_to_arc = -math.atan2(position_x, 2.58) * 180 / math.pi
        y_length_to_arc = math.atan2(position_y, 6.26) * 180 / math.pi

        print("target angle x: " + str(x_length_to_arc + previous_angle_x))
        print("previous angle x: " + str(previous_angle_x))

        print("target angle y: " + str(y_length_to_arc + previous_angle_y))
        print("previous angle y: " + str(previous_angle_y))

        if PID_count < 20:
            servo_angle[0] = int(x_length_to_arc * 0.5 + previous_angle_x)
            servo_angle[1] = int(y_length_to_arc * 0.2 + previous_angle_y)
            PID_Servo_Control(float(x_length_to_arc + previous_angle_x), float(y_length_to_arc + previous_angle_y))
            PID_count += 1
        else:
            servo_angle[0], servo_angle[1] = PID_Servo_Control(float(x_length_to_arc + previous_angle_x), float(y_length_to_arc + previous_angle_y))
        
        # reset servo
        if servo_angle[0] >= 150:
            servo_angle[0] = 150
        if servo_angle[0] <= 30:
            servo_angle[0] = 30

        if servo_angle[1] > 180:
            servo_angle[1] = 180
        if servo_angle[1] < 0:
            servo_angle[1] = 0

        previous_angle_x = servo_angle[0]
        previous_angle_y = servo_angle[1]

        relative_angle_x = abs(servo_angle[0] - 90)
        slow_side_coefficient = 1 - relative_angle_x / 90 if relative_angle_x < 22.5 else 0.75
        fast_side_coefficient = 1 + relative_angle_x / 90 if relative_angle_x < 22.5 else 1.25

        # override motor_control when target is found again
        if target_lost_counter < 10 and is_target_lost == False:
            print("smoothing motor speed start")
            if servo_angle[0] < 90:
                # turn right
                motor_speed_smoothing([2 * target_lost_counter + 30 * fast_side_coefficient, 
                                       1 * target_lost_counter + 10 * slow_side_coefficient, 
                                       1 * target_lost_counter + 10 * slow_side_coefficient, 
                                       2 * target_lost_counter + 30 * fast_side_coefficient], 
                                       30)
            else:
                # turn left
                motor_speed_smoothing([1 * target_lost_counter + 10 * slow_side_coefficient, 
                                       2 * target_lost_counter + 30 * fast_side_coefficient, 
                                       2 * target_lost_counter + 30 * fast_side_coefficient, 
                                       1 * target_lost_counter + 10 * slow_side_coefficient], 
                                       50)
            target_lost_counter += 1
            target_found_counter = 0
        elif target_found_counter < 6 and is_target_lost == True:
            target_found_counter += 1
            target_lost_counter = 0

        send_to_arduino(motor_speeds, servo_angle)

        current_time = time.time()
        print(f'send to arduino at {current_time}')
        print("position_x: " + str(position_x))
        print("position_y: " + str(position_y))
        getCPUtemperature()

        return jsonify({'message': 'Position received'})
    else:
        return jsonify({'error': 'Position not provided'}), 400

@app.before_request
def before_request():
    print("Request received at "+ str(time.time()))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
