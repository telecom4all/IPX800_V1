from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_IP_ADDRESS, CONF_NAME
import voluptuous as vol
from .const import DOMAIN, CONF_POLL_INTERVAL, CONF_API_URL, APP_PORT
import logging

_LOGGER = logging.getLogger(__name__)

@callback
def configured_instances(hass):
    return set(entry.title for entry in hass.config_entries.async_entries(DOMAIN))

class IPX800ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self.config_data = {}

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
                vol.Required(CONF_API_URL, default=f"http://localhost:{APP_PORT}"): str,
            })
        )

    async def async_step_add_device(self, user_input=None):
        _LOGGER.info("Starting IPX800 add device step")
        if user_input is not None:
            _LOGGER.info(f"Received add device input: {user_input}")
            self.config_data.update(user_input)
            return await self.async_step_select_buttons()

        return self.async_show_form(
            step_id="add_device",
            data_schema=vol.Schema({
                vol.Required("device_name", description="Nom du sous-appareil"): str,
            })
        )

    async def async_step_select_buttons(self, user_input=None):
        _LOGGER.info("Starting IPX800 select buttons step")
        if user_input is not None:
            _LOGGER.info(f"Received button selection: {user_input}")
            self.config_data.update(user_input)
            return await self.async_step_select_leds()

        return self.async_show_form(
            step_id="select_buttons",
            data_schema=vol.Schema({
                vol.Required("input_button", description="Sélectionner un bouton"): vol.In(["btn0", "btn1", "btn2", "btn3"]),
            })
        )

    async def async_step_select_leds(self, user_input=None):
        _LOGGER.info("Starting IPX800 select LEDs step")
        if user_input is not None:
            _LOGGER.info(f"Received LED selection: {user_input}")
            self.config_data.update(user_input)
            return self.async_create_entry(title=self.config_data["device_name"], data=self.config_data)

        return self.async_show_form(
            step_id="select_leds",
            data_schema=vol.Schema({
                vol.Optional("led0", description="LED 0"): bool,
                vol.Optional("led1", description="LED 1"): bool,
                vol.Optional("led2", description="LED 2"): bool,
                vol.Optional("led3", description="LED 3"): bool,
                vol.Optional("led4", description="LED 4"): bool,
                vol.Optional("led5", description="LED 5"): bool,
                vol.Optional("led6", description="LED 6"): bool,
                vol.Optional("led7", description="LED 7"): bool,
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
                vol.Optional("device_name", default=options.get("device_name", ""), description="Nom du sous-appareil"): str,
                vol.Optional("input_button", default=options.get("input_button", "btn0"), description="Sélectionner un bouton"): vol.In(["btn0", "btn1", "btn2", "btn3"]),
                vol.Optional("led0", default=options.get("led0", False), description="LED 0"): bool,
                vol.Optional("led1", default=options.get("led1", False), description="LED 1"): bool,
                vol.Optional("led2", default=options.get("led2", False), description="LED 2"): bool,
                vol.Optional("led3", default=options.get("led3", False), description="LED 3"): bool,
                vol.Optional("led4", default=options.get("led4", False), description="LED 4"): bool,
                vol.Optional("led5", default=options.get("led5", False), description="LED 5"): bool,
                vol.Optional("led6", default=options.get("led6", False), description="LED 6"): bool,
                vol.Optional("led7", default=options.get("led7", False), description="LED 7"): bool,
            })
        )
