import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.components.http import HomeAssistantView
import aiohttp
import asyncio
import websockets

from .const import DOMAIN, API_URL

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    hass.http.register_view(IPX800View)
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    if entry.entry_id in hass.data[DOMAIN]:
        return False  # Entry déjà configurée

    coordinator = IPX800Coordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "light"])

    _LOGGER.debug(f"Setup entry for {entry.entry_id} completed")
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    if entry.entry_id in hass.data[DOMAIN]:
        await hass.config_entries.async_forward_entry_unload(entry, "sensor")
        await hass.config_entries.async_forward_entry_unload(entry, "light")
        
        hass.data[DOMAIN].pop(entry.entry_id)

    return True

class IPX800Coordinator(DataUpdateCoordinator):
    websocket_connections = {}

    def __init__(self, hass, config_entry):
        super().__init__(
            hass,
            _LOGGER,
            name="IPX800",
        )
        self.config_entry = config_entry
        self.api_url = config_entry.data[API_URL]
        self.websocket_url = f"ws://{self.api_url}/ws"
        self.hass.loop.create_task(self._connect_websocket())

    async def _async_update_data(self):
        return {}  # WebSocket handles updates

    async def _connect_websocket(self):
        if self.websocket_url in self.websocket_connections:
            _LOGGER.info(f"WebSocket connection for URL {self.websocket_url} already exists. Using the existing connection.")
            return self.websocket_connections[self.websocket_url]

        try:
            async with websockets.connect(self.websocket_url) as websocket:
                self.websocket_connections[self.websocket_url] = websocket
                _LOGGER.info("WebSocket connection established")
                async for message in websocket:
                    _LOGGER.debug(f"WebSocket message received: {message}")
                    data = await self.hass.async_add_executor_job(parse_ipx800_status, message)
                    self.async_set_updated_data(data)
        except websockets.ConnectionClosed:
            _LOGGER.error("WebSocket connection closed")
        except Exception as e:
            _LOGGER.error(f"WebSocket error: {e}")

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
