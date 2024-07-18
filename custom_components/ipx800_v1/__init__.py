from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers import device_registry as dr
from .const import DOMAIN, CONF_POLL_INTERVAL, CONF_API_URL, APP_PORT
import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the IPX800 component."""
    _LOGGER.info("Setting up IPX800 component")
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up IPX800 from a config entry."""
    _LOGGER.info(f"Setting up IPX800 entry: {entry.data}")
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Register the device
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        manufacturer="IPX800",
        name=entry.title,
        model="V1",
        sw_version="1.0",
    )

    # Forward the entry setup to the sensor and light platforms
    await hass.config_entries.async_forward_entry_setup(entry, "sensor")
    await hass.config_entries.async_forward_entry_setup(entry, "light")
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload IPX800 config entry."""
    _LOGGER.info(f"Unloading IPX800 entry: {entry.data}")
    await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    await hass.config_entries.async_forward_entry_unload(entry, "light")
    hass.data[DOMAIN].pop(entry.entry_id)
    return True
