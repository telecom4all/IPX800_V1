import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    _LOGGER.debug("Setting up IPX800 sensor entities")
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

        entities.append(IPX800Sensor(coordinator, config_entry, device_name, input_button, select_leds))

    _LOGGER.debug(f"Entities to add: {entities}")
    async_add_entities(entities)

class IPX800Sensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, config_entry, device_name, input_button, select_leds):
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._name = device_name
        self._input_button = input_button
        self._select_leds = select_leds
        self._is_on = False
        self._attr_name = f"{device_name} Sensor"
        self._attr_unique_id = f"{config_entry.entry_id}_{device_name}_sensor"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=device_name,
            manufacturer="GCE Electronics",
            model="IPX800_V1",
        )
        _LOGGER.debug(f"Initialized IPX800Sensor entity: {self._attr_name}")

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        if self.coordinator.data:
            return all(self.coordinator.data["leds"].get(led, False) for led in self._select_leds)
        _LOGGER.warning("Coordinator data is empty or None")
        return False

    @property
    def extra_state_attributes(self):
        return {
            "input_button": self._input_button,
            "select_leds": self._select_leds,
        }

    async def async_update(self):
        _LOGGER.debug(f"Updating sensor: {self._name}")
        await self.coordinator.async_request_refresh()
