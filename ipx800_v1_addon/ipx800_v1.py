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

# Initialisation de l'application Flask
app = Flask(__name__)
CORS(app)

# Configuration de la journalisation
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

# Lecture des variables d'environnement
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 10))
SUPERVISOR_TOKEN = os.getenv("SUPERVISOR_TOKEN")
HEADERS = {
    "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
    "Content-Type": "application/json"
}

# État initial
states = {}

# Ensemble des clients WebSocket
clients = set()

# Fonction pour obtenir le statut de l'IPX800
def get_ipx800_status(ip):
    url = f"http://{ip}/status.xml"
    try:
        logging.info(f"[INFO] Sending request to IPX800 for status: {url}")
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        logging.info("[INFO] Received status from IPX800")
        return response.text
    except requests.RequestException as e:
        logging.error(f"[ERROR] Failed to get status from IPX800: {e}")
        return None

# Fonction pour parser le statut de l'IPX800
def parse_ipx800_status(ip, xml_data):
    try:
        root = ET.fromstring(xml_data)
        for led in states[ip]['leds'].keys():
            states[ip]['leds'][led] = int(root.find(led).text)
        for button in states[ip]['buttons'].keys():
            states[ip]['buttons'][button] = root.find(button).text
        logging.info(f"[INFO] Updated state from IPX800 {ip}: {states[ip]}")
    except ET.ParseError as e:
        logging.error(f"[ERROR] Failed to parse XML for IP {ip}: {e}")

# Fonction pour régler l'état d'une LED sur l'IPX800
def set_ipx800_led(ip, led, state):
    led_index = int(led.replace("led", "")) + 1
    url = f"http://{ip}/preset.htm?led{led_index}={state}"
    try:
        logging.info(f"[INFO] Sending request to IPX800 to set {led} to {state}: {url}")
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        logging.info(f"[INFO] Successfully set {led} to {state} on IPX800 {ip}")
        return response.status_code
    except requests.RequestException as e:
        logging.error(f"[ERROR] Failed to set LED {led} to {state} on IPX800 {ip}: {e}")
        return None

# Fonction pour notifier Home Assistant
def notify_home_assistant(ip, data):
    entity_id = f"sensor.ipx800_{ip.replace('.', '_')}"
    url = f"http://supervisor/core/api/states/{entity_id}"
    try:
        logging.info(f"[INFO] Sending notification to Home Assistant: {url}")
        response = requests.post(url, json=data, headers=HEADERS)
        response.raise_for_status()
        logging.info("[INFO] Successfully notified Home Assistant")
        return response.status_code
    except requests.RequestException as e:
        logging.error(f"[ERROR] Failed to notify Home Assistant for IP {ip}: {e}")
        return None

# Fonction principale pour interroger l'IPX800 et mettre à jour l'état
def poll_ipx800(ip):
    logging.info(f"[INFO] Starting IPX800 poller for {ip} with interval: {POLL_INTERVAL} seconds")
    while True:
        status = get_ipx800_status(ip)
        if status:
            parse_ipx800_status(ip, status)
            logging.info(f"[INFO] IPX800 status updated for {ip}")
            notify_home_assistant(ip, states[ip])
            asyncio.run(notify_clients(states[ip]))
        time.sleep(POLL_INTERVAL)

# Fonction asynchrone pour notifier les clients WebSocket
async def notify_clients(state):
    if clients:
        message = json.dumps(state)
        logging.info(f"[INFO] Notifying {len(clients)} clients: {message}")
        await asyncio.wait([client.send(message) for client in clients])

# Gestionnaire WebSocket pour ajouter et retirer des clients
async def websocket_handler(websocket, path):
    clients.add(websocket)
    logging.info(f"[INFO] Client connected: {websocket.remote_address}")
    try:
        async for message in websocket:
            pass
    finally:
        clients.remove(websocket)
        logging.info(f"[INFO] Client disconnected: {websocket.remote_address}")

# Fonction pour démarrer le serveur WebSocket
async def start_websocket_server():
    async with websockets.serve(websocket_handler, "0.0.0.0", 6789):
        logging.info("[INFO] WebSocket server started on port 6789")
        await asyncio.Future()  # Run forever

# Définir les routes Flask
@app.route('/status', methods=['GET'])
def status():
    ip = request.args.get('ip')
    if ip not in states:
        return jsonify({"error": "Invalid IP address"}), 400
    logging.info(f"[INFO] /status endpoint called for {ip}")
    xml_status = get_ipx800_status(ip)
    if xml_status:
        logging.info(f"[INFO] XML status received for {ip}: {xml_status}")
        parse_ipx800_status(ip, xml_status)
        return jsonify(states[ip])
    else:
        logging.error(f"[ERROR] Failed to retrieve status from IPX800 {ip}")
        return jsonify({"error": f"Failed to get status from IPX800 {ip}"}), 500

@app.route('/set_led', methods=['POST'])
def set_led():
    data = request.json
    ip = data.get('ip')
    led = data.get('led')
    state_value = data.get('state')
    if ip not in states or led not in states[ip]['leds']:
        return jsonify({"error": "Invalid IP address or LED"}), 400
    logging.info(f"[INFO] /set_led endpoint called for {ip}")
    if led and state_value is not None:
        result = set_ipx800_led(ip, led, state_value)
        if result == 200:
            states[ip]['leds'][led] = int(state_value)
            logging.info(f"[INFO] Updated state: {states[ip]}")
            notify_home_assistant(ip, states[ip])
            asyncio.run(notify_clients(states[ip]))
            return jsonify({"success": True})
        else:
            logging.error(f"[ERROR] Failed to set LED on IPX800 {ip}")
            return jsonify({"error": f"Failed to set LED on IPX800 {ip}"}), 500
    else:
        logging.error("[ERROR] Invalid request data")
        return jsonify({"error": "Invalid request"}), 400

@app.route('/toggle_button', methods=['POST'])
def toggle_button():
    data = request.json
    ip = data.get('ip')
    button = data.get('button')
    if ip not in states or button not in states[ip]['buttons']:
        return jsonify({"error": "Invalid IP address or button"}), 400
    logging.info(f"[INFO] /toggle_button endpoint called for {ip}")
    if button:
        new_state = 'up' if states[ip]['buttons'][button] == 'dn' else 'dn'
        states[ip]['buttons'][button] = new_state
        logging.info(f"[INFO] Button {button} new state on {ip}: {new_state}")
        for led in states[ip]['leds']:
            states[ip]['leds'][led] = not states[ip]['leds'][led]
        logging.info(f"[INFO] Updated LED states on {ip}: {states[ip]['leds']}")
        notify_home_assistant(ip, states[ip])
        asyncio.run(notify_clients(states[ip]))
        return jsonify({"success": True, "new_state": new_state})
    else:
        logging.error("[ERROR] Invalid request data")
        return jsonify({"error": "Invalid request"}), 400

# Fonction pour démarrer les serveurs WebSocket et Flask
def start_servers():
    websocket_thread = Thread(target=lambda: asyncio.run(start_websocket_server()))
    websocket_thread.start()

if __name__ == "__main__":
    start_servers()

    # Démarrer le poller principal pour chaque IPX800 configuré après un délai initial
    while not os.path.exists("/config/ipx800_devices.json"):
        logging.info("[INFO] Waiting for IPX800 devices to be configured...")
        time.sleep(10)

    with open("/config/ipx800_devices.json", "r") as f:
        IPX800_IPS = json.load(f).get("devices", [])

    for ip in IPX800_IPS:
        if ip:
            states[ip] = {'leds': {f'led{i}': 0 for i in range(8)}, 'buttons': {f'btn{i}': 'up' for i in range(4)}}
            Thread(target=poll_ipx800, args=(ip,)).start()
