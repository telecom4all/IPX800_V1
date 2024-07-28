import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    await coordinator.async_config_entry_first_refresh()

    entities = [IPX800V1Sensor(coordinator, config_entry)]
    async_add_entities(entities)

class IPX800V1Sensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, config_entry):
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._attr_name = f"IPX800 V1 Sensor"
        self._attr_unique_id = f"{config_entry.entry_id}_sensor"

    @property
    def state(self):
        # Return the state based on the data fetched by the coordinator
        return self.coordinator.data.get("state", "unknown")

    async def async_update(self):
        # Called to update the state of the sensor
        await self.coordinator.async_request_refresh()
