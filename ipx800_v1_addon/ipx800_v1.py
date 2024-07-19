import time
import requests
import os
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Initialisation des variables avec des valeurs par défaut
IPX800_IP = os.getenv("IPX800_IP", "192.168.1.121")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 10))

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

def get_ipx800_status():
    url = f"http://{IPX800_IP}/status.xml"
    try:
        print(f"[INFO] Sending request to IPX800 for status: {url}")
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        print("[INFO] Received status from IPX800")
        return response.text
    except requests.RequestException as e:
        print(f"[ERROR] Failed to get status from IPX800: {e}")
        return None

def set_ipx800_led(led, state):
    url = f"http://{IPX800_IP}/preset.htm?{led}={state}"
    try:
        print(f"[INFO] Sending request to IPX800 to set {led} to {state}: {url}")
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        print(f"[INFO] Successfully set {led} to {state}")
        return response.status_code
    except requests.RequestException as e:
        print(f"[ERROR] Failed to set LED {led} to {state}: {e}")
        return None

@app.route('/status', methods=['GET'])
def status():
    print("[INFO] /status endpoint called")
    status = get_ipx800_status()
    if status:
        print(f"[INFO] Current state: {state}")
        return jsonify(state)
    else:
        print("[ERROR] Failed to retrieve status from IPX800")
        return jsonify({"error": "Failed to get status from IPX800"}), 500

@app.route('/set_led', methods=['POST'])
def set_led():
    print("[INFO] /set_led endpoint called")
    data = request.json
    print(f"[INFO] Data received: {data}")
    led = data.get('led')
    state_value = data.get('state')
    if led and state_value is not None:
        result = set_ipx800_led(led, state_value)
        if result == 200:
            state['leds'][led] = int(state_value)  # Convertir en entier ou booléen selon votre préférence
            print(f"[INFO] Updated state: {state}")
            return jsonify({"success": True})
        else:
            print("[ERROR] Failed to set LED on IPX800")
            return jsonify({"error": "Failed to set LED"}), 500
    else:
        print("[ERROR] Invalid request data")
        return jsonify({"error": "Invalid request"}), 400

@app.route('/toggle_button', methods=['POST'])
def toggle_button():
    print("[INFO] /toggle_button endpoint called")
    data = request.json
    print(f"[INFO] Data received: {data}")
    button = data.get('button')
    if button:
        new_state = 'up' if state['buttons'][button] == 'dn' else 'dn'
        state['buttons'][button] = new_state
        print(f"[INFO] Button {button} new state: {new_state}")

        # Invert the state of the LEDs associated with this button
        for led in state['leds']:
            state['leds'][led] = not state['leds'][led]
        print(f"[INFO] Updated LED states: {state['leds']}")

        return jsonify({"success": True, "new_state": new_state})
    else:
        print("[ERROR] Invalid request data")
        return jsonify({"error": "Invalid request"}), 400

def main():
    print(f"[INFO] Starting IPX800 poller with interval: {POLL_INTERVAL} seconds")
    while True:
        status = get_ipx800_status()
        if status:
            # Parse the XML and update the state dictionary
            print("[INFO] IPX800 status:")
            print(status)
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
