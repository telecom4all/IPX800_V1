import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.light import LightEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN
import aiohttp

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    _LOGGER.debug("Setting up IPX800 entities")
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = []

    devices = config_entry.options.get("devices", [])
    _LOGGER.debug(f"Devices in config entry options: {devices}")
    if not devices:
        _LOGGER.warning("No devices found in config entry options.")

    _LOGGER.debug(f"Devices found in config entry: {devices}")
    for device in devices:
        device_name = device["device_name"]
        input_button = device["input_button"]
        select_leds = device["select_leds"]
        _LOGGER.debug(f"Adding device: {device_name}, input_button: {input_button}, select_leds: {select_leds}")

        entities.append(IPX800Sensor(coordinator, config_entry, device_name, input_button, select_leds))
        entities.append(IPX800Light(coordinator, config_entry, device_name, input_button, select_leds))

    _LOGGER.debug(f"Entities to add: {entities}")
    async_add_entities(entities)

class IPX800Entity(CoordinatorEntity):
    def __init__(self, coordinator, config_entry, device_name, input_button, select_leds):
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._name = device_name
        self._input_button = input_button
        self._select_leds = select_leds
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=device_name,
            manufacturer="GCE Electronics",
            model="IPX800_V1",
        )
        _LOGGER.debug(f"Initialized IPX800 entity: {self._attr_name}")

    async def async_added_to_hass(self):
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        # Restore previous state
        state = self.hass.states.get(self.entity_id)
        if state:
            self._is_on = state.state == "on"
            self._input_button = state.attributes.get("input_button", self._input_button)
            self._select_leds = state.attributes.get("select_leds", self._select_leds)
        _LOGGER.debug(f"Restored state for {self._name}: {self._is_on}, {self._input_button}, {self._select_leds}")

    @property
    def name(self):
        return self._name

    @property
    def extra_state_attributes(self):
        return {
            "input_button": self._input_button,
            "select_leds": self._select_leds,
        }

class IPX800Sensor(IPX800Entity, SensorEntity):
    @property
    def state(self):
        if self.coordinator.data:
            return all(self.coordinator.data["leds"].get(led, False) for led in self._select_leds)
        _LOGGER.warning("Coordinator data is empty or None")
        return False

    async def async_update(self):
        _LOGGER.debug(f"Updating sensor: {self._name}")
        await self.coordinator.async_request_refresh()

class IPX800Light(IPX800Entity, LightEntity):
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
