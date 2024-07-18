import logging
from homeassistant.components.light import LightEntity
from .const import DOMAIN, CONF_IP_ADDRESS, CONF_API_URL
import requests

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    if "device_name" not in config_entry.options:
        return

    ip_address = config_entry.data[CONF_IP_ADDRESS]
    api_url = config_entry.data[CONF_API_URL]
    device_name = config_entry.options.get("device_name")
    output_leds = [led for led in ["led0", "led1", "led2", "led3", "led4", "led5", "led6", "led7"] if config_entry.options.get(led)]

    lights = [IPX800Light(ip_address, api_url, led, device_name) for led in output_leds]
    async_add_entities(lights, update_before_add=True)

class IPX800Light(LightEntity):
    def __init__(self, ip_address, api_url, led, device_name):
        self._ip_address = ip_address
        self._api_url = api_url
        self._led = led
        self._device_name = device_name
        self._is_on = False

    @property
    def name(self):
        return f"{self._device_name} Light {self._led}"

    @property
    def is_on(self):
        return self._is_on

    def turn_on(self, **kwargs):
        self._set_led_state(1)

    def turn_off(self, **kwargs):
        self._set_led_state(0)

    def _set_led_state(self, state):
        url = f"{self._api_url}/set_led"
        response = requests.post(url, json={'led': self._led, 'state': state})
        if response.status_code == 200:
            self._is_on = state == 1
        else:
            _LOGGER.error(f"Failed to set LED {self._led}: {response.status_code}")

    def update(self):
        url = f"{self._api_url}/status"
        response = requests.get(url)
        if response.status_code == 200:
            status = response.json()
            self._is_on = status['leds'].get(self._led) == 1
        else:
            _LOGGER.error(f"Failed to update light state: {response.status_code}")
