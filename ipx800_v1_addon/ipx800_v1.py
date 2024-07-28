import asyncio
import websockets
import sqlite3
import json
import logging

from .const import DOMAIN, IP_ADDRESS, POLL_INTERVAL, API_URL, WEBSOCKET_URL, APP_PORT, WS_PORT

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')
logger = logging.getLogger(__name__)


clients = set()

async def register(websocket):
    clients.add(websocket)
    try:
        async for message in websocket:
            await handle_message(websocket, message)
    finally:
        clients.remove(websocket)

async def handle_message(websocket, message):
    data = json.loads(message)
    action = data.get("action")

    if action == "init_device":
        await init_device(data)
    elif action == "update_state":
        await update_device_state(data)
    # Ajouter d'autres actions ici

async def init_device(data):
    device_name = data["device_name"]
    ip_address = data["ip_address"]
    poll_interval = data["poll_interval"]
    unique_id = data["unique_id"]

    db_path = f"/config/ipx800_{ip_address}.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS infos (
            device_name TEXT,
            ip_address TEXT,
            poll_interval INTEGER,
            unique_id TEXT
        )
    ''')
    cursor.execute('''
        INSERT INTO infos (device_name, ip_address, poll_interval, unique_id)
        VALUES (?, ?, ?, ?)
    ''', (device_name, ip_address, poll_interval, unique_id))
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS devices (
            device_name TEXT,
            input_button TEXT,
            select_leds TEXT,
            unique_id TEXT,
            variable_etat_name TEXT
        )
    ''')
    conn.commit()
    conn.close()

    asyncio.create_task(poll_ipx800(ip_address, poll_interval))

async def update_device_state(data):
    # Gérer la mise à jour de l'état des appareils ici
    pass

async def poll_ipx800(ip_address, interval):
    while True:
        # Implémenter la logique pour interroger l'IPX800 et mettre à jour l'état
        await asyncio.sleep(interval)

async def main():
    async with websockets.serve(register, "0.0.0.0", WS_PORT):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    logger.info(f"Starting WebSocket server on ws://0.0.0.0:{WS_PORT}")
    asyncio.run(main())
