from flask import Flask, request, jsonify
from flask_cors import CORS
import serial
import requests
import socket
import time
import threading
import math
import numpy as np

class PositionPID(object):
    """位置式PID算法实现"""

    def __init__(self, target, cur_val, max, min, p, i, d) -> None:
        self._max = max  # 最大输出限制，规避过冲
        self._min = min  # 最小输出限制
        self.k_p = p  # 比例系数
        self.k_i = i  # 积分系数
        self.k_d = d  # 微分系数

        self.target = target  # 目标值
        self.cur_val = cur_val  # 算法当前PID位置值，第一次为设定的初始位置
        self._pre_error = 0  # t-1 时刻误差值
        self._integral = 0  # 误差积分值


    def calculate(self):
        """
        计算t时刻PID输出值cur_val
        """
        error = self.target - self.cur_val  # 计算当前误差
        # 比例项
        p_out = self.k_p * error  
        # 积分项
        self._integral += (error)
        i_out = self.k_i * self._integral
        # 微分项
        derivative = (error - self._pre_error)
        d_out = self.k_d * derivative

        # t 时刻pid输出
        output = p_out + i_out + d_out

        # 限制输出值
        if output > self._max:
            output = self._max
        elif output < self._min:
            output = self._min
        
        self._pre_error = error
        self.cur_val = output
        return self.cur_val
    
    def fit_and_plot(self, count = 200):
        """
        使用PID拟合setPoint
        """
        counts = np.arange(count)
        outputs = []

        for i in counts:
            outputs.append(self.calculate())
        return outputs[-1]

def get_local_ip():
    # 创建一个 UDP 套接字
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # 尝试连接到一个外部的IP地址（这里用的是Google的DNS服务器地址）
        # 实际上并不会真的连接，这只是用来获取本机IP地址
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception as e:
        print(f"An error occurred: {e}")
        ip = "Unable to get IP"
    finally:
        s.close()
    return ip

def motor_control(position_x):
    global motor_speeds
    motor_speed_initial = 150
    max_speed_diff = 50
    motor_speeds = [int(motor_speed_initial + position_x * max_speed_diff), int(motor_speed_initial - position_x * max_speed_diff), int(motor_speed_initial - position_x * max_speed_diff), int(motor_speed_initial + position_x * max_speed_diff)]

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
    data = str(motor_speeds[0]) + " " + str(motor_speeds[1]) + " " + str(motor_speeds[2]) + " " + str(motor_speeds[3]) + " " + str(servo_angle[0]) + " " + str(servo_angle[1]) + "\n"
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
            data = response.json()  # 将响应解析为JSON格式
            # 提取设备名称为"pi"的IP地址
            backend_ip = data.get("backend")
            if backend_ip:
                print(f"IP address of backend: {backend_ip}")
                break  # 成功获取IP地址后退出循环
            else:
                print("Device 'backend' not found")
        else:
            print(f"Failed to fetch IPs, status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Error occurred: {e}")

    time.sleep(1)  # 等待1秒后重试

backend_url = 'http://' + str(backend_ip) + ':5000/receive_url'

ser = serial.Serial('/dev/ttyACM0', 9600)

motor_speeds = [0, 0, 0, 0]
servo_angle = [0.0, 0.0]
previous_angle_x = 90

# initialize the motor speeds and servo angles
# send_to_arduino(motor_speeds, servo_angle)

app = Flask(__name__)
CORS(app)

@app.route('/key', methods=['POST'])
def key_event():
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

    send_to_arduino(motor_speeds, servo_angle)
    return jsonify({'message': 'Key received'})

@app.route('/position', methods=['POST'])
def position_event():
    data = request.get_json()
    current_time = time.time()
    global previous_angle_x

    print(f'Position received at {current_time}')

    print("data: " + str(data))
    
    position_x = data.get('position_x')
    position_y = data.get('position_y')

    # a bug here
    position_x = float(position_x)
    position_y = float(position_y)

    if position_x is not None and position_y is not None:

        motor_control(position_x)

        reduced_coefficient_y = 0.3
        x_length_to_arc = -math.atan2(position_x, 2.58) * 180 / math.pi

        print("target angle: " + str(x_length_to_arc + previous_angle_x))
        print("previous angle: " + str(previous_angle_x))

        # servo_angle[0] = int(x_length_to_arc + previous_angle_x)
        x_pid = PositionPID(x_length_to_arc + previous_angle_x, previous_angle_x, 20, 0, 0.6, 0.005, 0.03)
        servo_angle[0] = int(x_pid.fit_and_plot(20))

        print("PID result: " + str(servo_angle[0]))

        servo_angle[1] = int(90 * (reduced_coefficient_y * position_y + 1))

        print("motor speeds: " + str(motor_speeds))
        # previous_angle_x = servo_angle[0] if servo_angle[0] < 150 and servo_angle[0] > 30 else previous_angle_x
        

        if servo_angle[0] > 180:
            servo_angle[0] = 180
        if servo_angle[0] < 0:
            servo_angle[0] = 0
        if servo_angle[1] > 180:
            servo_angle[1] = 180
        if servo_angle[1] < 0:
            servo_angle[1] = 0

        previous_angle_x = servo_angle[0]
        
        send_to_arduino(motor_speeds, servo_angle)
        current_time = time.time()
        print(f'send to arduino at {current_time}')
        print("position_x: " + str(position_x))
        print("position_y: " + str(position_y))



        return jsonify({'message': 'Position received'})
    else:
        return jsonify({'error': 'Position not provided'}), 400
    
# def reset_on_exit(exception = None):
#     print("Resetting motors to initial state")
#     motor_speeds = [0, 0, 0, 0]
#     servo_angle = [90, 90]
#     send_to_arduino(motor_speeds, servo_angle)
#     # ser.close()
#     print("Serial port closed")
#     if exception:
#         print(f"An exception occurred: {exception}")

# @app.teardown_appcontext
# def teardown(exception = None):
#     reset_on_exit(exception)

@app.before_request
def before_request():
    print("Request received at "+ str(time.time()))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
