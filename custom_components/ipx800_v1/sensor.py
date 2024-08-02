import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
import sqlite3
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

def clean_entity_name(name):
    return name.lower().replace(' ', '_').replace('é', 'e').replace('è', 'e').replace('ê', 'e').replace('à', 'a').replace('ç', 'c')

async def async_setup_entry(hass, config_entry, async_add_entities):
    _LOGGER.debug("Setting up IPX800 sensor entities")
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = []
    _LOGGER.debug(f"config_entry: {config_entry}")
    devices = config_entry.data.get("devices", [])
    _LOGGER.debug(f"Devices in config entry data: {devices}")
    if not devices:
        _LOGGER.warning("No devices found in config entry data.")

    entity_registry = async_get_entity_registry(hass)

    for device in devices:
        device_name = device["device_name"]
        select_leds = device["select_leds"]
        unique_id = f"{config_entry.entry_id}_{clean_entity_name(device_name)}_light_sensor"

        if unique_id in entity_registry.entities:
            _LOGGER.warning(f"Entity with unique_id {unique_id} already exists. Skipping.")
            continue

        _LOGGER.debug(f"Adding sensor entity: {device_name} Light Sensor")
        entities.append(IPX800LightSensor(coordinator, config_entry, device_name, select_leds, unique_id))

    _LOGGER.debug(f"Sensor entities to add: {entities}")
    async_add_entities(entities)

class IPX800Base(CoordinatorEntity):
    def __init__(self, coordinator, config_entry, device_name, select_leds):
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._name = device_name
        self._select_leds = select_leds
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_name)},
            name=device_name,
            manufacturer="GCE Electronics",
            model="IPX800_V1",
            via_device=(DOMAIN, config_entry.entry_id)
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
    def __init__(self, coordinator, config_entry, device_name, select_leds, unique_id):
        super().__init__(coordinator, config_entry, device_name, select_leds)
        self._is_on = False
        self._attr_name = f"{device_name} Light Sensor"
        self._attr_unique_id = unique_id
        self._variable_etat_name = f"etat_{clean_entity_name(device_name)}"

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
        # Ici, nous devons lire l'état de `state` à partir de la base de données
        db_path = f"/config/ipx800_{self.coordinator.config_entry.data['ip_address']}.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT state FROM devices WHERE device_name = ?", (self._name,))
        variable_state = cursor.fetchone()[0]
        conn.close()
        return "on" if variable_state == 'on' else "off"
