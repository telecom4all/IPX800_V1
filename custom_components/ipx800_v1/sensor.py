from homeassistant.helpers.entity import Entity
from homeassistant.const import CONF_IP_ADDRESS
from .const import CONF_POLL_INTERVAL, CONF_API_URL
import requests
import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    ip_address = config_entry.data[CONF_IP_ADDRESS]
    poll_interval = config_entry.data[CONF_POLL_INTERVAL]
    api_url = config_entry.data[CONF_API_URL]
    _LOGGER.info(f"Setting up IPX800 sensor with IP: {ip_address}, poll interval: {poll_interval}, and API URL: {api_url}")

    leds = [led for led in ["led0", "led1", "led2", "led3", "led4", "led5", "led6", "led7"] if config_entry.options.get(led)]
    sensors = [IPX800Sensor(ip_address, poll_interval, api_url, led) for led in leds]

    async_add_entities(sensors)

class IPX800Sensor(Entity):
    def __init__(self, ip_address, poll_interval, api_url, led):
        self._ip_address = ip_address
        self._poll_interval = poll_interval
        self._api_url = api_url
        self._state = None
        self._led = led
        _LOGGER.info(f"Initialized IPX800 Sensor with IP: {self._ip_address}, poll interval: {self._poll_interval}, API URL: {self._api_url}, and LED: {self._led}")

    @property
    def name(self):
        return f"IPX800 Sensor {self._led}"

    @property
    def state(self):
        return self._state

    async def async_update(self):
        url = f"{self._api_url}/status"
        _LOGGER.info(f"Updating IPX800 sensor from URL: {url}")
        response = await self.hass.async_add_executor_job(requests.get, url)
        if response.status_code == 200:
            _LOGGER.info("Successfully updated IPX800 sensor")
            self._state = response.json().get(self._led)
        else:
            _LOGGER.error(f"Failed to update IPX800 sensor: {response.status_code}")
            self._state = None
