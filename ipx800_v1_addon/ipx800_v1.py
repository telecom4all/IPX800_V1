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
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Failed to get status from IPX800: {e}")
        return None

def set_ipx800_led(led, state):
    url = f"http://{IPX800_IP}/preset.htm?{led}={state}"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.status_code
    except requests.RequestException as e:
        print(f"Failed to set LED {led} to {state}: {e}")
        return None

@app.route('/status', methods=['GET'])
def status():
    status = get_ipx800_status()
    if status:
        # Parse the XML and update the state dictionary
        # This is just an example, you need to parse the XML properly
        print(status)
        return jsonify(state)
    else:
        return jsonify({"error": "Failed to get status from IPX800"}), 500

@app.route('/set_led', methods=['POST'])
def set_led():
    data = request.json
    led = data.get('led')
    state_value = data.get('state')
    if led and state_value is not None:
        result = set_ipx800_led(led, state_value)
        if result == 200:
            state['leds'][led] = int(state_value)  # Convertir en entier ou booléen selon votre préférence
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

        # Invert the state of the LEDs associated with this button
        for led in state['leds']:
            state['leds'][led] = not state['leds'][led]

        return jsonify({"success": True, "new_state": new_state})
    else:
        return jsonify({"error": "Invalid request"}), 400

def main():
    while True:
        status = get_ipx800_status()
        if status:
            # Parse the XML and update the state dictionary
            print(status)
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
