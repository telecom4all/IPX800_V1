import asyncio
import logging
import websockets
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

clients = set()

state = {
    'leds': {f'led{i}': 0 for i in range(8)},
    'buttons': {f'btn{i}': 'up' for i in range(4)}
}

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
    logging.info("[INFO] Starting WebSocket server on port 6789")
    async with websockets.serve(websocket_handler, "0.0.0.0", 6789):
        logging.info("[INFO] WebSocket server started on port 6789")
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(start_websocket_server())
