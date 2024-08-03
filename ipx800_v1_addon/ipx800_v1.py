import asyncio
import websockets
import sqlite3
import json
import logging
import aiohttp
import requests
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
        elif action == "add_device":
            await add_device(data)
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
            variable_etat_name TEXT,
            ip_address TEXT,
            state TEXT DEFAULT 'off'
        )
    ''')

    # Ajouter la colonne ip_address si elle n'existe pas
    cursor.execute("PRAGMA table_info(devices)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'ip_address' not in columns:
        cursor.execute('ALTER TABLE devices ADD COLUMN ip_address TEXT')
    if 'state' not in columns:
        cursor.execute("ALTER TABLE devices ADD COLUMN state TEXT DEFAULT 'off'")

    conn.commit()
    conn.close()

    asyncio.create_task(poll_ipx800(ip_address, poll_interval))

async def add_device(data):
    device_name = data["device_name"]
    input_button = data["input_button"]
    select_leds = ",".join(data["select_leds"])
    unique_id = data["unique_id"]
    variable_etat_name = data["variable_etat_name"]
    ip_address = data["ip_address"]

    db_path = f"/config/ipx800_{ip_address}.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT COUNT(*) FROM devices WHERE device_name = ? AND ip_address = ?
    ''', (device_name, ip_address))
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO devices (device_name, input_button, select_leds, unique_id, variable_etat_name, ip_address, state)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (device_name, input_button, select_leds, unique_id, variable_etat_name, ip_address, 'off'))
        conn.commit()
    conn.close()
    logger.info(f"Device {device_name} added with leds {select_leds} and variable {variable_etat_name}.")
    

async def set_led_state(data):
    state = data["state"]
    select_leds = data["leds"]
    ip_address = data["ip_address"]
    variable_etat_name = data["variable_etat_name"]
    device_name = data.get("device_name", None)

    # Implémenter la logique pour allumer ou éteindre les LED de l'IPX800
    logger.info(f"Setting LED state to {'on' if state else 'off'} for LEDs: {select_leds}")
    try:
        async with aiohttp.ClientSession() as session:
            for led in select_leds:
                url = f"http://{ip_address}/preset.htm?{led}={'1' if state else '0'}"
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Error setting LED {led} to state {'1' if state else '0'}: {response.status}")
                    else:
                        logger.info(f"Set LED {led} to state {'1' if state else '0'}")

        if device_name:
            # Mettre à jour l'état dans la base de données
            db_path = f"/config/ipx800_{ip_address}.db"
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(f"UPDATE devices SET state = ? WHERE device_name = ?", ('on' if state else 'off', device_name))
            conn.commit()
            conn.close()
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
            "variable_etat_name": row[4],
            "ip_address": row[5],
            "state": row[6]
        })
    await websocket.send(json.dumps({"action": "data", "devices": devices}))
    conn.close()

async def poll_ipx800(ip_address, interval):
    previous_status = {}
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'http://{ip_address}/status.xml') as response:
                    response_text = await response.text()
                    await process_status(response_text, ip_address, previous_status)
        except Exception as e:
            logger.error(f"Error polling IPX800: {e}")
        await asyncio.sleep(interval)

async def process_status(xml_data, ip_address, previous_status):
    root = ET.fromstring(xml_data)
    status = {child.tag: child.text for child in root}

    logger.info(f"Status: {status}")
    
    # Vérifier les changements d'état des boutons
    for btn in ['btn0', 'btn1', 'btn2', 'btn3']:
        if btn in status and previous_status.get(btn) != status[btn]:
            await handle_button_change(ip_address, btn, status[btn])

    previous_status.update(status)

    # Notify all connected clients with the new status
    message = json.dumps({"action": "status_update", "status": status})
    await notify_clients(message)

async def handle_button_change(ip_address, btn, state):
    logger.info(f"Button {btn} changed state to {state}")
    db_path = f"/config/ipx800_{ip_address}.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT device_name, select_leds, state FROM devices WHERE input_button = ?', (btn,))
    rows = cursor.fetchall()

    for row in rows:
        device_name, select_leds, current_state = row
        new_state = 'off' if current_state == 'on' else 'on'
        leds = select_leds.split(',')
        await set_led_state({
            "state": new_state == 'on',
            "leds": leds,
            "ip_address": ip_address,
            "variable_etat_name": f'etat_{clean_entity_name(device_name)}',
            "device_name": device_name
        })
        
        # Mettre à jour l'état dans la base de données
        cursor.execute(f"UPDATE devices SET state = ? WHERE device_name = ?", (new_state, device_name))
        conn.commit()
        
        # Mettre à jour l'état dans Home Assistant
        await notify_clients(json.dumps({
            "action": "update_entity_state",
            "entity_id": f"light.{clean_entity_name(device_name)}",
            "state": new_state
        }))

    conn.close()

async def notify_clients(message):
    if clients:
        await asyncio.gather(*(client.send(message) for client in clients))

async def main():
    while True:
        try:
            async with websockets.serve(register, "0.0.0.0", WS_PORT):
                logger.info(f"WebSocket server started on ws://0.0.0.0:{WS_PORT}")
                await asyncio.Future()  # run forever
        except Exception as e:
            logger.error(f"WebSocket server error: {e}")
            await asyncio.sleep(5)  # wait before retrying

def clean_entity_name(name):
    return name.lower().replace(' ', '_').replace('é', 'e').replace('è', 'e').replace('ê', 'e').replace('à', 'a').replace('ç', 'c')

if __name__ == "__main__":
    logger.info(f"Starting WebSocket server on ws://0.0.0.0:{WS_PORT}")
    asyncio.run(main())
