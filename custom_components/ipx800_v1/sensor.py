from homeassistant.helpers.entity import Entity
from homeassistant.const import CONF_IP_ADDRESS

async def async_setup_entry(hass, config_entry, async_add_entities):
    ip_address = config_entry.data[CONF_IP_ADDRESS]
    async_add_entities([IPX800Sensor(ip_address)])

class IPX800Sensor(Entity):
    def __init__(self, ip_address):
        self._ip_address = ip_address
        self._state = None

    @property
    def name(self):
        return f"IPX800 Sensor {self._ip_address}"

    @property
    def state(self):
        return self._state

    async def async_update(self):
        url = f"http://{self._ip_address}/status.xml"
        response = await self.hass.async_add_executor_job(requests.get, url)
        if response.status_code == 200:
            self._state = response.text
        else:
            self._state = None
