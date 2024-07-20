import logging
from homeassistant.components.light import LightEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN
import aiohttp

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    _LOGGER.debug("Setting up IPX800 light entities")
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = []

    devices = config_entry.options.get("devices", [])
    if not devices:
        _LOGGER.warning("No devices found in config entry options.")

    _LOGGER.debug(f"Devices found in config entry: {devices}")
    for device in devices:
        device_name = device["device_name"]
        input_button = device["input_button"]
        select_leds = device["select_leds"]
        _LOGGER.debug(f"Adding device: {device_name}, input_button: {input_button}, select_leds: {select_leds}")

        entities.append(IPX800Light(coordinator, config_entry, device_name, input_button, select_leds))

    _LOGGER.debug(f"Entities to add: {entities}")
    async_add_entities(entities)

class IPX800Light(CoordinatorEntity, LightEntity):
    def __init__(self, coordinator, config_entry, device_name, input_button, select_leds):
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._name = device_name
        self._input_button = input_button
        self._select_leds = select_leds
        self._is_on = False
        self._attr_name = f"{device_name} Light"
        self._attr_unique_id = f"{config_entry.entry_id}_{device_name}_light"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=device_name,
            manufacturer="GCE Electronics",
            model="IPX800_V1",
        )
        _LOGGER.debug(f"Initialized IPX800Light entity: {self._attr_name}")

    @property
    def name(self):
        return self._name

    @property
    def is_on(self):
        if self.coordinator.data:
            return all(self.coordinator.data["leds"].get(led, False) for led in self._select_leds)
        _LOGGER.warning("Coordinator data is empty or None")
        return False

    async def async_turn_on(self, **kwargs):
        await self._set_led_state(True)
        self._is_on = True
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        await self._set_led_state(False)
        self._is_on = False
        await self.coordinator.async_request_refresh()

    async def _set_led_state(self, state):
        url = f"{self.config_entry.data['api_url']}/set_led"
        async with aiohttp.ClientSession() as session:
            for led in self._select_leds:
                payload = {'led': led, 'state': '1' if state else '0'}
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        _LOGGER.debug(f"Set {led} to {state}")
                    else:
                        _LOGGER.error(f"Failed to set {led} to {state}")

    @property
    def supported_color_modes(self):
        return []  # Assurez-vous de définir les modes de couleur supportés si nécessaire
