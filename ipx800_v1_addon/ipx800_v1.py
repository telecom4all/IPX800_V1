import time
import requests
import os
from flask import Flask, jsonify, request
from flask_cors import CORS
import logging
import xml.etree.ElementTree as ET
from threading import Thread
import asyncio
import websockets
import json

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

IPX800_IP = os.getenv("IPX800_IP", "192.168.1.121")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 10))
SUPERVISOR_TOKEN = os.getenv("SUPERVISOR_TOKEN")
HEADERS = {
    "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
    "Content-Type": "application/json"
}

state = {
    'leds': {f'led{i}': 0 for i in range(8)},
    'buttons': {f'btn{i}': 'up' for i in range(4)}
}

clients = set()

def get_ipx800_status():
    url = f"http://{IPX800_IP}/status.xml"
    try:
        logging.info(f"[INFO] Sending request to IPX800 for status: {url}")
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        logging.info("[INFO] Received status from IPX800")
        return response.text
    except requests.RequestException as e:
        logging.error(f"[ERROR] Failed to get status from IPX800: {e}")
        return None

def parse_ipx800_status(xml_data):
    try:
        root = ET.fromstring(xml_data)
        for led in state['leds'].keys():
            state['leds'][led] = int(root.find(led).text)
        for button in state['buttons'].keys():
            state['buttons'][button] = root.find(button).text
        logging.info(f"[INFO] Updated state from IPX800: {state}")
    except ET.ParseError as e:
        logging.error(f"[ERROR] Failed to parse XML: {e}")

def set_ipx800_led(led, state):
    led_index = int(led.replace("led", "")) + 1
    url = f"http://{IPX800_IP}/preset.htm?led{led_index}={state}"
    try:
        logging.info(f"[INFO] Sending request to IPX800 to set {led} to {state}: {url}")
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        logging.info(f"[INFO] Successfully set {led} to {state}")
        return response.status_code
    except requests.RequestException as e:
        logging.error(f"[ERROR] Failed to set LED {led} to {state}: {e}")
        return None

def notify_home_assistant(data):
    url = "http://supervisor/core/api/states/sensor.ipx800_v1"
    try:
        logging.info(f"[INFO] Sending notification to Home Assistant: {url}")
        response = requests.post(url, json=data, headers=HEADERS)
        response.raise_for_status()
        logging.info("[INFO] Successfully notified Home Assistant")
        return response.status_code
    except requests.RequestException as e:
        logging.error(f"[ERROR] Failed to notify Home Assistant: {e}")
        return None

def main():
    logging.info(f"[INFO] Starting IPX800 poller with interval: {POLL_INTERVAL} seconds")
    while True:
        status = get_ipx800_status()
        if status:
            parse_ipx800_status(status)
            logging.info("[INFO] IPX800 status updated")
            notify_home_assistant(state)
            asyncio.run(notify_clients(state))
        time.sleep(POLL_INTERVAL)

async def notify_clients(state):
    if clients:
        message = json.dumps(state)
        logging.info(f"[INFO] Notifying {len(clients)} clients: {message}")
        await asyncio.wait([client.send(message) for client in clients])

async def websocket_handler(websocket, path):
    clients.add(websocket)
    logging.info(f"[INFO] Client connected: {websocket.remote_address}")
    try:
        async for message in websocket:
            pass
    finally:
        clients.remove(websocket)
        logging.info(f"[INFO] Client disconnected: {websocket.remote_address}")

async def start_websocket_server():
    async with websockets.serve(websocket_handler, "0.0.0.0", 6789):
        logging.info("[INFO] WebSocket server started on port 6789")
        await asyncio.Future()  # Run forever

@app.route('/status', methods=['GET'])
def status():
    logging.info("[INFO] /status endpoint called")
    xml_status = get_ipx800_status()
    if xml_status:
        logging.info(f"[INFO] XML status received: {xml_status}")
        parse_ipx800_status(xml_status)
        return jsonify(state)
    else:
        logging.error("[ERROR] Failed to retrieve status from IPX800")
        return jsonify({"error": "Failed to get status from IPX800"}), 500

@app.route('/set_led', methods=['POST'])
def set_led():
    logging.info("[INFO] /set_led endpoint called")
    data = request.json
    logging.info(f"[INFO] Data received: {data}")
    led = data.get('led')
    state_value = data.get('state')
    if led and state_value is not None:
        result = set_ipx800_led(led, state_value)
        if result == 200:
            state['leds'][led] = int(state_value)
            logging.info(f"[INFO] Updated state: {state}")
            notify_home_assistant(state)
            asyncio.run(notify_clients(state))
            return jsonify({"success": True})
        else:
            logging.error("[ERROR] Failed to set LED on IPX800")
            return jsonify({"error": "Failed to set LED"}), 500
    else:
        logging.error("[ERROR] Invalid request data")
        return jsonify({"error": "Invalid request"}), 400

@app.route('/toggle_button', methods=['POST'])
def toggle_button():
    logging.info("[INFO] /toggle_button endpoint called")
    data = request.json
    logging.info(f"[INFO] Data received: {data}")
    button = data.get('button')
    if button:
        new_state = 'up' if state['buttons'][button] == 'dn' else 'dn'
        state['buttons'][button] = new_state
        logging.info(f"[INFO] Button {button} new state: {new_state}")
        for led in state['leds']:
            state['leds'][led] = not state['leds'][led]
        logging.info(f"[INFO] Updated LED states: {state['leds']}")
        notify_home_assistant(state)
        asyncio.run(notify_clients(state))
        return jsonify({"success": True, "new_state": new_state})
    else:
        logging.error("[ERROR] Invalid request data")
        return jsonify({"error": "Invalid request"}), 400

if __name__ == "__main__":
    websocket_thread = Thread(target=lambda: asyncio.run(start_websocket_server()))
    websocket_thread.start()
    main()
