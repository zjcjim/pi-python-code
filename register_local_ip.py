# register local ip to IP server while booting
import socket
import requests
import sys
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

ip_server_url = 'http://124.71.164.229:5000'

# register pi's ip address
def register_ip(ip_server_url, max_retries=3):
    ip_register_url = ip_server_url + '/register'
    data = {'name': 'pi', 'ip': get_local_ip()}
    headers = {'Content-Type': 'application/json'}

    retries = 0
    while retries < max_retries:
        try:
            response = requests.post(ip_register_url, json=data, headers=headers)
            response.raise_for_status()  # Raises a HTTPError for bad responses
            print(response.json())
            return
        except requests.exceptions.RequestException as e:
            print(f"Attempt {retries + 1} failed: {e}")
            retries += 1
            if retries < max_retries:
                time.sleep(1)  # Wait for 2 seconds before retrying

    print("Failed to register IP after 3 attempts. Exiting program.")
    sys.exit(1)

if __name__ == "__main__":
    register_ip(ip_server_url)