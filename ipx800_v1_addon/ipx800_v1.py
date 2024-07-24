import time
import requests
import os
import asyncio
import websockets
from flask import Flask, jsonify, request
from flask_cors import CORS
import logging
import xml.etree.ElementTree as ET

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

IPX800_IP = os.getenv("IPX800_IP", "192.168.1.121")
SUPERVISOR_TOKEN = os.getenv("SUPERVISOR_TOKEN")
HEADERS = {
    "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
    "Content-Type": "application/json"
}

state = {
    'leds': {
        'led0': 0,
        'led1': 0,
        'led2': 0,
        'led3': 0,
        'led4': 0,
        'led5': 0,
        'led6': 0,
        'led7': 0,
    },
    'buttons': {
        'btn0': 'up',
        'btn1': 'up',
        'btn2': 'dn',
        'btn3': 'dn',
    }
}

websocket_connections = {}

async def ipx800_websocket(ip):
    uri = f"ws://{ip}/ws"
    logging.info(f"Trying to connect to WebSocket: {uri}")
    if ip in websocket_connections:
        logging.info(f"WebSocket connection for IP {ip} already exists. Using the existing connection.")
        return websocket_connections[ip]

    async with websockets.connect(uri) as websocket:
        websocket_connections[ip] = websocket
        try:
            while True:
                message = await websocket.recv()
                logging.info(f"Received WebSocket message: {message}")
                parse_ipx800_status(message)
                notify_home_assistant(state)
        except websockets.ConnectionClosed:
            logging.error(f"WebSocket connection to {ip} closed")
            del websocket_connections[ip]

def parse_ipx800_status(message):
    try:
        root = ET.fromstring(message)
        for led in state['leds'].keys():
            state['leds'][led] = int(root.find(led).text)
        for button in state['buttons'].keys():
            state['buttons'][button] = root.find(button).text
        logging.info(f"Updated state from IPX800: {state}")
    except ET.ParseError as e:
        logging.error(f"Failed to parse WebSocket message: {e}")

def set_ipx800_led(led, state):
    url = f"http://{IPX800_IP}/preset.htm?{led}={state}"
    try:
        logging.info(f"Sending request to IPX800 to set {led} to {state}: {url}")
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        logging.info(f"Successfully set {led} to {state}")
        return response.status_code
    except requests.RequestException as e:
        logging.error(f"Failed to set LED {led} to {state}: {e}")
        return None

def notify_home_assistant(data):
    url = "http://supervisor/core/api/states/sensor.ipx800_v1"
    try:
        logging.info(f"Sending notification to Home Assistant: {url}")
        response = requests.post(url, json=data, headers=HEADERS)
        response.raise_for_status()
        logging.info("Successfully notified Home Assistant")
        return response.status_code
    except requests.RequestException as e:
        logging.error(f"Failed to notify Home Assistant: {e}")
        return None

@app.route('/status', methods=['GET'])
def status():
    return jsonify(state)

@app.route('/set_led', methods=['POST'])
def set_led():
    data = request.json
    led = data.get('led')
    state_value = data.get('state')
    if led and state_value is not None:
        result = set_ipx800_led(led, state_value)
        if result == 200:
            state['leds'][led] = int(state_value)
            notify_home_assistant(state)
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Failed to set LED"}), 500
    else:
        return jsonify({"error": "Invalid request"}), 400

@app.route('/toggle_button', methods=['POST'])
def toggle_button():
    data = request.json
    button = data.get('button')
    if button:
        new_state = 'up' if state['buttons'][button] == 'dn' else 'dn'
        state['buttons'][button] = new_state

        for led in state['leds']:
            state['leds'][led] = not state['leds'][led]
        notify_home_assistant(state)

        return jsonify({"success": True, "new_state": new_state})
    else:
        return jsonify({"error": "Invalid request"}), 400

def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(ipx800_websocket(IPX800_IP))

if __name__ == "__main__":
    main()
