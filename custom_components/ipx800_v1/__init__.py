import logging
import asyncio
import websockets
import json
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .const import DOMAIN, IP_ADDRESS, POLL_INTERVAL, API_URL, WEBSOCKET_URL, APP_PORT

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    coordinator = IPX800V1Coordinator(hass, entry)
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    
    # Start the WebSocket connection
    asyncio.create_task(coordinator.start_websocket())

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    hass.data[DOMAIN].pop(entry.entry_id)
    return True

class IPX800V1Coordinator(DataUpdateCoordinator):
    def __init__(self, hass, config_entry):
        super().__init__(hass, _LOGGER, name=DOMAIN)
        self.config_entry = config_entry
        self.websocket = None

    async def start_websocket(self):
        async with websockets.connect('ws://localhost:6789') as websocket:
            self.websocket = websocket
            await websocket.send(json.dumps({
                "action": "init_device",
                "device_name": self.config_entry.data["device_name"],
                "ip_address": self.config_entry.data["ip_address"],
                "poll_interval": self.config_entry.data["poll_interval"],
                "unique_id": self.config_entry.data["unique_id"]
            }))
            async for message in websocket:
                await self.handle_websocket_message(message)

    async def handle_websocket_message(self, message):
        data = json.loads(message)
        # Handle the incoming message from the WebSocket
        _LOGGER.info(f"Received message from WebSocket: {data}")

    async def _async_update_data(self):
        return {}
