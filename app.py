import threading
from flask import Flask, request, jsonify
from flask_cors import CORS
import serial
import requests
import socket
import time

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

def send_to_arduino(motor_speeds, servo_angle):
    start_time = time.time()
    check_sum = motor_speeds[0] + motor_speeds[1] + motor_speeds[2] + motor_speeds[3] + servo_angle[0] + servo_angle[1]
    data = str(motor_speeds[0]) + " " + str(motor_speeds[1]) + " " + str(motor_speeds[2]) + " " + str(motor_speeds[3]) + " " + str(servo_angle[0]) + " " + str(servo_angle[1]) + " " + str(check_sum)
    ser.write(data.encode("utf-8"))
    print("Data send to Arduino: " + str(data))
    feedback = ser.readline()
    print("Feedback from Arduino: " + str(feedback.decode("utf-8").replace('\n','')))
    end_time = time.time()
    print(f"Time taken to send data on serial: {end_time - start_time} seconds")

def periodic_send():
    global motor_speeds, servo_angle
    while True:
        send_to_arduino(motor_speeds, servo_angle)
        time.sleep(0.05)  # 每隔0.05秒发送一次

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

motor_speeds = [0, 0, 0, 0]
servo_angle = [0.0, 0.0]

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
    global motor_speeds, servo_angle
    data = request.get_json()
    current_time = time.time()
    print(f'Position received at {current_time}')
    position_x = data.get('position_x')
    position_y = data.get('position_y')
    position_x = float(position_x)
    position_y = float(position_y)

    if position_x is not None and position_y is not None:
        motor_control(position_x)
        reduced_coefficient = 0.1
        servo_angle[0] = int(90 * (reduced_coefficient * (-position_x) + 1))
        servo_angle[1] = int(90 * (reduced_coefficient * (-position_y) + 1))

        print("motor speeds: " + str(motor_speeds))

        current_time = time.time()
        print(f'send to arduino at {current_time}')
        print("position_x: " + str(position_x))
        print("position_y: " + str(position_y))
        return jsonify({'message': 'Position received'})
    else:
        return jsonify({'error': 'Position not provided'}), 400

@app.before_request
def before_request():
    print("Request received at "+ str(time.time()))

if __name__ == '__main__':
    # 启动定时发送数据的线程
    app.run(debug=True, host='0.0.0.0', threaded=True)
    threading.Thread(target=periodic_send, daemon=True).start()
