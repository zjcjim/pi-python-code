from flask import Flask, request, jsonify
from flask_cors import CORS
import serial
import requests
import socket
import time

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


def capture_image(server_url):
    response = requests.get(f"{server_url}/capture")
    if response.status_code == 200:
        print("Image URL:", response.text)
    else:
        print("Failed to capture image")
    return response.text

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

    time.sleep(2)  # 等待2秒后重试

backend_url = 'http://' + str(backend_ip) + ':5000/receive_url'

ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)

app = Flask(__name__)
CORS(app)

@app.route('/key', methods=['POST'])
def key_event():
    data = request.get_json()
    key_pressed = data.get('key')
    print(f'Key pressed: {key_pressed}')
    if(key_pressed=='w'):
        print('motor forward')
    elif(key_pressed=='s'):
        print('motor backward')
    elif(key_pressed=='a'):
        print('motor turn left')
    elif(key_pressed=='d'):
        print('motor turn right')
    elif(key_pressed=='q'):
        print('motor stop')
    elif(key_pressed=='p'):
        print('taking a photo')
        image_url = capture_image(server_url)
        data = {'url': image_url}

        response = requests.post(backend_url, json=data)
        print(response.status_code)
        print(response.text)
        return jsonify({'Image_URL': image_url, 'response_text': response.text})


    ser.write(key_pressed.encode('utf-8'))

    return jsonify({'message': 'Key received'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
