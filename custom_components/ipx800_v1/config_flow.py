import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
import aiohttp
from .const import IP_ADDRESS, DOMAIN, POLL_INTERVAL, API_URL, APP_PORT

_LOGGER = logging.getLogger(__name__)

@config_entries.HANDLERS.register(DOMAIN)
class IPX800ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            _LOGGER.debug(f"User input received: {user_input}")
            devices = [{
                "device_name": user_input["device_name"],
                "input_button": user_input["input_button"],
                "select_leds": user_input["select_leds"]
            }]
            # Send configuration to Docker
            await self.send_configuration_to_docker(user_input)
            
            return self.async_create_entry(title=user_input["device_name"], data={
                "device_name": user_input["device_name"],
                "ip_address": user_input["ip_address"],
                "poll_interval": user_input["poll_interval"],
                "api_url": user_input["api_url"],
                "devices": devices
            })

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("device_name"): str,
                vol.Required("ip_address"): str,
                vol.Required("poll_interval", default=10): int,
                vol.Required("api_url", default="http://localhost:5213"): str,
                vol.Required("input_button"): vol.In(["btn0", "btn1", "btn2", "btn3"]),
                vol.Required("select_leds"): cv.multi_select({
                    "led0": "LED 0",
                    "led1": "LED 1",
                    "led2": "LED 2",
                    "led3": "LED 3",
                    "led4": "LED 4",
                    "led5": "LED 5",
                    "led6": "LED 6",
                    "led7": "LED 7",
                }),
            })
        )

    async def send_configuration_to_docker(self, user_input):
        api_url = user_input.get("api_url", "http://localhost:5213")
        config_data = {
            "button": user_input["input_button"],
            "leds": user_input["select_leds"]
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{api_url}/configure_leds", json=config_data) as response:
                if response.status == 200:
                    _LOGGER.debug("Configuration sent to Docker successfully")
                else:
                    _LOGGER.error(f"Failed to send configuration to Docker: {response.status}")

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return IPX800OptionsFlowHandler(config_entry)

class IPX800OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        return self.async_show_form(step_id="init", data_schema=vol.Schema({}), errors={})
