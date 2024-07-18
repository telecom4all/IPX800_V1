import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_IP_ADDRESS, CONF_NAME
import homeassistant.helpers.config_validation as cv
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
            return self.async_create_entry(title=user_input["device_name"], data=user_input)

        return self.async_show_form(
            step_id="add_device",
            data_schema=vol.Schema({
                vol.Required("device_name"): str,
                vol.Required("input_button"): vol.In(["btn0", "btn1", "btn2", "btn3"]),
                vol.Optional("led0", description={"suggested_value": False}): bool,
                vol.Optional("led1", description={"suggested_value": False}): bool,
                vol.Optional("led2", description={"suggested_value": False}): bool,
                vol.Optional("led3", description={"suggested_value": False}): bool,
                vol.Optional("led4", description={"suggested_value": False}): bool,
                vol.Optional("led5", description={"suggested_value": False}): bool,
                vol.Optional("led6", description={"suggested_value": False}): bool,
                vol.Optional("led7", description={"suggested_value": False}): bool,
            })
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return IPX800OptionsFlow(config_entry)


class IPX800OptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional("device_name", default=options.get("device_name", "")): str,
                vol.Optional("input_button", default=options.get("input_button", "btn0")): vol.In(["btn0", "btn1", "btn2", "btn3"]),
                vol.Optional("led0", description={"suggested_value": "LED 0"}): bool,
                vol.Optional("led1", description={"suggested_value": "LED 1"}): bool,
                vol.Optional("led2", description={"suggested_value": "LED 2"}): bool,
                vol.Optional("led3", description={"suggested_value": "LED 3"}): bool,
                vol.Optional("led4", description={"suggested_value": "LED 4"}): bool,
                vol.Optional("led5", description={"suggested_value": "LED 5"}): bool,
                vol.Optional("led6", description={"suggested_value": "LED 6"}): bool,
                vol.Optional("led7", description={"suggested_value": "LED 7"}): bool,
            })
        )
