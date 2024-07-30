import asyncio
import websockets
import sqlite3
import json
import logging
import aiohttp
import xml.etree.ElementTree as ET


logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')
logger = logging.getLogger(__name__)

WS_PORT = 6789
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
    logger.info(f"action:{action}")
    logger.info(f"data:{data}")

    try:
        if action == "init_device":
            await init_device(data)
        elif action == "set_led_state":
            await set_led_state(data)
        elif action == "get_data":
            await get_data(websocket, data)
        else:
            logger.warning(f"Unknown action: {action}")
    except Exception as e:
        logger.error(f"Error handling message: {e}")

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
    cursor.execute('SELECT COUNT(*) FROM infos WHERE device_name = ? AND ip_address = ?', (device_name, ip_address))
    if cursor.fetchone()[0] == 0:
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

async def set_led_state(data):
    state = data["state"]
    select_leds = data["select_leds"]
    # Implémenter la logique pour allumer ou éteindre les LED de l'IPX800
    logger.info(f"Setting LED state to {'on' if state else 'off'} for LEDs: {select_leds}")
    try:
        # Simulate setting LED state here
        # e.g., send command to IPX800 device
        pass
    except Exception as e:
        logger.error(f"Error setting LED state: {e}")


async def get_data(websocket, data):
    ip_address = data.get("ip_address")
    if not ip_address:
        return
    db_path = f"/config/ipx800_{ip_address}.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM devices')
    rows = cursor.fetchall()
    devices = []
    for row in rows:
        devices.append({
            "device_name": row[0],
            "input_button": row[1],
            "select_leds": row[2].split(","),
            "unique_id": row[3],
            "variable_etat_name": row[4]
        })
    await websocket.send(json.dumps({"action": "data", "devices": devices}))
    conn.close()
    
async def poll_ipx800(ip_address, interval):
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'http://{ip_address}/status.xml') as response:
                    response_text = await response.text()
                    await process_status(response_text)
        except Exception as e:
            logger.error(f"Error polling IPX800: {e}")
        await asyncio.sleep(interval)

async def process_status(xml_data):
    root = ET.fromstring(xml_data)
    status = {}
    for child in root:
        status[child.tag] = child.text
    logger.info(f"Status: {status}")
    # Notify all connected clients with the new status
    message = json.dumps({"action": "status_update", "status": status})
    await notify_clients(message)

async def notify_clients(message):
    if clients:
        await asyncio.wait([client.send(message) for client in clients])


async def main():
    async with websockets.serve(register, "0.0.0.0", WS_PORT):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    logger.info(f"Starting WebSocket server on ws://0.0.0.0:{WS_PORT}")
    asyncio.run(main())
