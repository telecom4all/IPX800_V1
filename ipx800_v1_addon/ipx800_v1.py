import time
import requests
import json
import os

IPX800_IP = os.getenv("IPX800_IP", "192.168.1.121")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 10))

def get_ipx800_status():
    url = f"http://{IPX800_IP}/status.xml"
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        print(f"Failed to get status from IPX800: {response.status_code}")
        return None

def set_ipx800_led(led, state):
    url = f"http://{IPX800_IP}/preset.htm?led{led}={state}"
    response = requests.get(url)
    if response.status_code == 200:
        print(f"Successfully set LED{led} to {state}")
    else:
        print(f"Failed to set LED{led}: {response.status_code}")

def main():
    while True:
        status = get_ipx800_status()
        if status:
            print(status)
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()