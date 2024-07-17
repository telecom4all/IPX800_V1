import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_IP_ADDRESS, CONF_NAME
from .const import DOMAIN, CONF_POLL_INTERVAL, CONF_API_URL
import logging

_LOGGER = logging.getLogger(__name__)

@callback
def configured_instances(hass):
    return set(entry.title for entry in hass.config_entries.async_entries(DOMAIN))

class IPX800ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input=None):
        _LOGGER.info("Starting IPX800 user step")
        if user_input is not None:
            _LOGGER.info(f"Received user input: {user_input}")
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_IP_ADDRESS): str,
                vol.Required(CONF_POLL_INTERVAL, default=10): int,
                vol.Required(CONF_API_URL, default="http://localhost:5000"): str,
            })
        )

    async def async_step_add_device(self, user_input=None):
        _LOGGER.info("Starting IPX800 add device step")
        if user_input is not None:
            _LOGGER.info(f"Received add device input: {user_input}")
            # Handle the input to add a new device
            pass

        return self.async_show_form(
            step_id="add_device",
            data_schema=vol.Schema({
                vol.Required("device_name"): str,
                vol.Required("input_button"): vol.In(["btn0", "btn1", "btn2", "btn3"]),
                vol.Required("output_leds"): vol.All(vol.Coerce(list), [vol.In(["led0", "led1", "led2", "led3", "led4", "led5", "led6", "led7"])]),
            })
        )
 