import logging
from homeassistant.helpers.entity import Entity
from homeassistant.const import CONF_IP_ADDRESS
from .const import CONF_POLL_INTERVAL, CONF_API_URL
import requests

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    ip_address = config_entry.data[CONF_IP_ADDRESS]
    poll_interval = config_entry.data[CONF_POLL_INTERVAL]
    api_url = config_entry.data[CONF_API_URL]
    device_name = config_entry.data.get("device_name")
    input_button = config_entry.data.get("input_button")
    leds = [led for led in ["led0", "led1", "led2", "led3", "led4", "led5", "led6", "led7"] if config_entry.data.get(led)]

    sensors = [IPX800Sensor(ip_address, poll_interval, api_url, led, input_button, device_name) for led in leds]

    async_add_entities(sensors)

class IPX800Sensor(Entity):
    def __init__(self, ip_address, poll_interval, api_url, led, input_button, device_name):
        self._ip_address = ip_address
        self._poll_interval = poll_interval
        self._api_url = api_url
        self._state = None
        self._led = led
        self._input_button = input_button
        self._device_name = device_name

    @property
    def name(self):
        return f"{self._device_name} Sensor {self._led}"

    @property
    def state(self):
        return self._state

    async def async_update(self):
        url = f"{self._api_url}/status"
        response = await self.hass.async_add_executor_job(requests.get, url)
        if response.status_code == 200:
            self._state = response.json().get(self._led)
        else:
            self._state = None
