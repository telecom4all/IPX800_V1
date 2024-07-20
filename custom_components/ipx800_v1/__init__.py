import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers import device_registry as dr, entity_registry as er
from .const import IP_ADDRESS, DOMAIN, POLL_INTERVAL, API_URL, APP_PORT
from datetime import timedelta, datetime
import aiohttp

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    """Configurer l'intégration via le fichier configuration.yaml (non utilisé ici)"""
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

    # Restore devices from config entry options
    devices = entry.options.get("devices", [])
    for device in devices:
        _LOGGER.debug(f"Restored device: {device}")

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

    async def _async_update_data(self):
        now = datetime.now()
        if self._last_update is not None:
            elapsed = now - self._last_update
            _LOGGER.info(f"Data updated. {elapsed.total_seconds() / 60:.2f} minutes elapsed since last update.")
        self._last_update = now

        _LOGGER.info("Fetching new data from IPX800 Docker")

        # Fetch data from IPX800 Docker
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
