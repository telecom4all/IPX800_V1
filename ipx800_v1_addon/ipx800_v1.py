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
import sqlite3

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

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

def get_ipx800_status(ip_address):
    url = f"http://{ip_address}/status.xml"
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

def set_ipx800_led(ip_address, led, state_value):
    led_index = int(led.replace("led", "")) + 1
    url = f"http://{ip_address}/preset.htm?led{led_index}={state_value}"
    try:
        logging.info(f"[INFO] Sending request to IPX800 to set {led} to {state_value}: {url}")
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        logging.info(f"[INFO] Successfully set {led} to {state_value}")
        return response.status_code
    except requests.RequestException as e:
        logging.error(f"[ERROR] Failed to set LED {led} to {state_value}: {e}")
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

def poll_ipx800(ip_address, poll_interval):
    logging.info(f"[INFO] Starting IPX800 poller for {ip_address} with interval: {poll_interval} seconds")
    while True:
        status = get_ipx800_status(ip_address)
        if status:
            parse_ipx800_status(status)
            logging.info("[INFO] IPX800 status updated")
            notify_home_assistant(state)
            asyncio.run(notify_clients(state))
        time.sleep(poll_interval)

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
    ip_address = request.args.get('ip_address')
    logging.info(f"[INFO] /status endpoint called for IP: {ip_address}")
    xml_status = get_ipx800_status(ip_address)
    if xml_status:
        logging.info(f"[INFO] XML status received: {xml_status}")
        parse_ipx800_status(xml_status)
        return jsonify(state)
    else:
        logging.error("[ERROR] Failed to retrieve status from IPX800")
        return jsonify({"error": "Failed to get status from IPX800"}), 500

@app.route('/set_led', methods=['POST'])
def set_led():
    data = request.json
    ip_address = data.get('ip_address')
    led = data.get('led')
    state_value = data.get('state')
    if ip_address and led and state_value is not None:
        result = set_ipx800_led(ip_address, led, state_value)
        if result == 200:
            state['leds'][led] = int(state_value)
            notify_home_assistant(state)
            asyncio.run(notify_clients(state))
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Failed to set LED"}), 500
    else:
        return jsonify({"error": "Invalid request"}), 400

@app.route('/toggle_button', methods=['POST'])
def toggle_button():
    data = request.json
    ip_address = data.get('ip_address')
    button = data.get('button')
    if ip_address and button:
        new_state = 'up' if state['buttons'][button] == 'dn' else 'dn'
        state['buttons'][button] = new_state
        for led in state['leds']:
            state['leds'][led] = not state['leds'][led]
        notify_home_assistant(state)
        asyncio.run(notify_clients(state))
        return jsonify({"success": True, "new_state": new_state})
    else:
        return jsonify({"error": "Invalid request"}), 400

if __name__ == "__main__":
    # Démarrer le serveur WebSocket dans un thread distinct
    websocket_thread = Thread(target=lambda: asyncio.run(start_websocket_server()))
    websocket_thread.start()

    # Démarrer les boucles de sondage pour chaque IPX800 configuré
    db_files = [f for f in os.listdir("/config") if f.startswith("ipx800_") and f.endswith(".db")]
    for db_file in db_files:
        db_path = os.path.join("/config", db_file)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT ip_address, poll_interval FROM infos")
        result = cursor.fetchone()
        conn.close()

        if result:
            ip_address, poll_interval = result
            poll_thread = Thread(target=poll_ipx800, args=(ip_address, poll_interval))
            poll_thread.start()

    app.run(host="0.0.0.0", port=5213)
