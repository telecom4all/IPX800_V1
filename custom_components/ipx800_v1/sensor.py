import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    _LOGGER.debug("Setting up IPX800 sensor entities")
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = []

    devices = config_entry.data.get("devices", [])
    _LOGGER.debug(f"Devices in config entry data: {devices}")
    if not devices:
        _LOGGER.warning("No devices found in config entry data.")

    for device in devices:
        device_name = device["device_name"]
        select_leds = device["select_leds"]
        _LOGGER.debug(f"Adding sensor entity: {device_name} Light Sensor")

        entities.append(IPX800LightSensor(coordinator, config_entry, device_name, select_leds))

    _LOGGER.debug(f"Sensor entities to add: {entities}")
    async_add_entities(entities)

class IPX800Base(CoordinatorEntity):
    def __init__(self, coordinator, config_entry, device_name, select_leds):
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._name = device_name
        self._select_leds = select_leds
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=device_name,
            manufacturer="GCE Electronics",
            model="IPX800_V1",
        )
        _LOGGER.debug(f"Initialized IPX800 entity: {self._name}")

    @property
    def name(self):
        return self._name

    @property
    def extra_state_attributes(self):
        return {
            "select_leds": self._select_leds,
        }
    
class IPX800LightSensor(IPX800Base, SensorEntity):
    def __init__(self, coordinator, config_entry, device_name, select_leds):
        super().__init__(coordinator, config_entry, device_name, select_leds)
        self._is_on = False
        self._attr_name = f"{device_name} Light Sensor"
        self._attr_unique_id = f"{config_entry.entry_id}_{device_name}_light_sensor"

    async def async_added_to_hass(self):
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        state = self.hass.states.get(self.entity_id)
        if state:
            self._is_on = state.state == "on"
            self._select_leds = state.attributes.get("select_leds", self._select_leds)
        _LOGGER.debug(f"Restored state for {self._name}: {self._is_on}, {self._select_leds}")

    @property
    def state(self):
        if self.coordinator.data:
            return "on" if any(self.coordinator.data["leds"].get(led, False) for led in self._select_leds) else "off"
        _LOGGER.warning("Coordinator data is empty or None")
        return "unknown"
