import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.components.http import HomeAssistantView
from datetime import timedelta, datetime
import aiohttp
import asyncio
import websockets

from .const import DOMAIN, POLL_INTERVAL, API_URL

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    """Configurer l'intégration via le fichier configuration.yaml (non utilisé ici)"""
    hass.http.register_view(IPX800View)
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    if entry.entry_id in hass.data[DOMAIN]:
        return False  # Entry déjà configurée

    poll_interval = int(entry.data.get("poll_interval", POLL_INTERVAL))
    coordinator = IPX800Coordinator(hass, entry, update_interval=poll_interval)
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
    def __init__(self, hass, config_entry, update_interval):
        super().__init__(
            hass,
            _LOGGER,
            name="IPX800",
            update_interval=timedelta(seconds=update_interval),
        )
        self.config_entry = config_entry
        self._last_update = None
        self.api_url = config_entry.data[API_URL]
        _LOGGER.info(f"Coordinator initialized with update interval: {update_interval} seconds")
        asyncio.create_task(self._listen_to_websocket())

    async def _async_update_data(self):
        now = datetime.now()
        if self._last_update is not None:
            elapsed = now - self._last_update
            _LOGGER.info(f"Data updated. {elapsed.total_seconds() / 60:.2f} minutes elapsed since last update.")
        self._last_update = now

        _LOGGER.info("Fetching new data from IPX800 Docker")

        data = await self.fetch_data_from_docker()

        if data:
            _LOGGER.info("New data fetched successfully")
            _LOGGER.debug(f"Data received: {data}")
        else:
            _LOGGER.error("No data received from IPX800 Docker")

        return data

    async def fetch_data_from_docker(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.api_url}/status") as response:
                if response.status != 200:
                    raise UpdateFailed(f"Failed to fetch data from Docker API: {response.status}")
                data = await response.json()
                return data

    async def _listen_to_websocket(self):
        async with websockets.connect('ws://localhost:6789') as websocket:
            while True:
                message = await websocket.recv()
                data = json.loads(message)
                self.async_set_updated_data(data)

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
