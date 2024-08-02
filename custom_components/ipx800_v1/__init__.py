import logging
import asyncio
import websockets
import json
import sqlite3
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.components.http import HomeAssistantView
from datetime import timedelta, datetime

from .const import DOMAIN, IP_ADDRESS, POLL_INTERVAL, WEBSOCKET_URL, WS_PORT

_LOGGER = logging.getLogger(__name__)

def clean_entity_name(name):
    return name.lower().replace(' ', '_').replace('é', 'e').replace('è', 'e').replace('ê', 'e').replace('à', 'a').replace('ç', 'c')


async def async_setup(hass: HomeAssistant, config: dict):
    hass.http.register_view(IPX800View)
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    if entry.entry_id in hass.data[DOMAIN]:
        return False

    poll_interval = int(entry.data.get("poll_interval", POLL_INTERVAL))
    websocket_url = entry.data.get("websocket_url", WEBSOCKET_URL)

    coordinator = IPX800V1Coordinator(hass, entry, update_interval=poll_interval, websocket_url=websocket_url)

    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id] = coordinator

    devices = await coordinator.load_devices()
    data = {**entry.data, "devices": devices}
    hass.config_entries.async_update_entry(entry, data=data)

    await remove_existing_entities(hass, entry)
    await setup_devices_and_entities(hass, entry, devices)

    # Start the WebSocket connection
    asyncio.create_task(coordinator.ensure_websocket_connection())

    _LOGGER.debug(f"Setup entry for {entry.entry_id} completed")
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    if entry.entry_id in hass.data[DOMAIN]:
        await hass.config_entries.async_forward_entry_unload(entry, "sensor")
        await hass.config_entries.async_forward_entry_unload(entry, "light")
        hass.data[DOMAIN].pop(entry.entry_id)
    return True

async def setup_devices_and_entities(hass, entry, devices):
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)

    for device in devices:
        device_name = device["device_name"]
        unique_id = device["unique_id"]
        device_id = device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, unique_id)},
            name=device_name,
            manufacturer="GCE Electronics",
            model="IPX800_V1",
            via_device=(DOMAIN, entry.entry_id)
        ).id

        light_entity_id = f"light.{clean_entity_name(device_name)}"
        sensor_entity_id = f"sensor.{clean_entity_name(device_name)}"

        if not entity_registry.async_is_registered(light_entity_id):
            await hass.config_entries.async_forward_entry_setups(entry, ["light"])

        if not entity_registry.async_is_registered(sensor_entity_id):
            await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

async def remove_existing_entities(hass, entry):
    entity_registry = er.async_get(hass)
    entities_to_remove = [
        entity_id for entity_id in entity_registry.entities
        if entity_registry.async_get(entity_id).config_entry_id == entry.entry_id
    ]
    for entity_id in entities_to_remove:
        entity_registry.async_remove(entity_id)

class IPX800V1Coordinator(DataUpdateCoordinator):
    def __init__(self, hass, config_entry, update_interval, websocket_url):
        super().__init__(
            hass,
            _LOGGER,
            name="IPX800",
            update_interval=timedelta(seconds=update_interval),
        )
        self.config_entry = config_entry
        self._last_update = None
        self.websocket_url = websocket_url
        self.websocket = None
        self.message_queue = asyncio.Queue()  # Initialisation de message_queue

    async def ensure_websocket_connection(self):
        while True:
            try:
                await self.start_websocket()
            except Exception as e:
                _LOGGER.error(f"WebSocket connection error: {e}")
                await asyncio.sleep(5)  # wait before retrying

    async def start_websocket(self):
        async with websockets.connect(f'ws://localhost:{WS_PORT}') as websocket:
            self.websocket = websocket
            await websocket.send(json.dumps({
                "action": "init_device",
                "device_name": self.config_entry.data["device_name"],
                "ip_address": self.config_entry.data["ip_address"],
                "poll_interval": self.config_entry.data["poll_interval"],
                "unique_id": self.config_entry.data["unique_id"]
            }))
            asyncio.create_task(self.receive_messages(websocket))
            await self.process_messages()

    async def receive_messages(self, websocket):
        try:
            async for message in websocket:
                await self.message_queue.put(message)
        except websockets.exceptions.ConnectionClosedError as e:
            _LOGGER.error(f"WebSocket connection closed with error: {e}")
        except Exception as e:
            _LOGGER.error(f"Unexpected error in WebSocket connection: {e}")

    async def process_messages(self):
        while True:
            message = await self.message_queue.get()
            await self.handle_websocket_message(message)

    async def handle_websocket_message(self, message):
        data = json.loads(message)
        # Ensure 'leds' key is always present
        if 'leds' not in data:
            data['leds'] = {}
        # Handle the incoming message from the WebSocket
        _LOGGER.info(f"Received message from WebSocket: {data}")
        self.async_set_updated_data(data)

    async def _async_update_data(self):
        now = datetime.now()
        if self._last_update is not None:
            elapsed = now - self._last_update
            _LOGGER.info(f"Data updated. {elapsed.total_seconds() / 60:.2f} minutes elapsed since last update.")
        self._last_update = now
        _LOGGER.info("Fetching new data from IPX800 Docker")
        # demander via le websocket les data pour l'integration
        if self.websocket:
            await self.websocket.send(json.dumps({"action": "get_data"}))
            data = await self.message_queue.get()
            data = json.loads(data)
            # Ensure 'leds' key is always present
            if 'leds' not in data:
                data['leds'] = {}
            return data
        return {}

    async def load_devices(self):
        ip_address = self.config_entry.data["ip_address"]
        db_path = f"/config/ipx800_{ip_address}.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT device_name, input_button, select_leds, unique_id, variable_etat_name FROM devices')
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
        conn.close()
        return devices

class IPX800View(HomeAssistantView):
    url = "/api/ipx800_update"
    name = "api:ipx800_update"
    requires_auth = False

    async def post(self, request):
        hass = request.app["hass"]
        data = await request.json()
        for entry_id, coordinator in hass.data[DOMAIN].items():
            coordinator.async_set_updated_data(data)
        return self.json({"success": True})
