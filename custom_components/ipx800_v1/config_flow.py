import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class IPX800ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self.config_data = {}

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            self.config_data.update(user_input)
            return self.async_create_entry(title=self.config_data["name"], data=self.config_data)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("name"): str,
                vol.Required("ip_address"): str,
                vol.Required("poll_interval", default=10): int,
                vol.Required("api_url", default="http://localhost:5213"): str,
            })
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return IPX800OptionsFlow(config_entry)

class IPX800OptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry
        self.options = dict(config_entry.options)

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            self.options.update(user_input)
            return await self.async_step_select_buttons()

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required("device_name", description="Nom du sous-appareil"): str,
            })
        )

    async def async_step_select_buttons(self, user_input=None):
        if user_input is not None:
            self.options.update(user_input)
            return await self.async_step_select_leds()

        return self.async_show_form(
            step_id="select_buttons",
            data_schema=vol.Schema({
                vol.Required("input_button", description="Sélectionner un bouton"): vol.In(["btn0", "btn1", "btn2", "btn3"]),
            })
        )

    async def async_step_select_leds(self, user_input=None):
        if user_input is not None:
            self.options.update(user_input)
            return self.async_create_entry(title=self.options["device_name"], data=self.options)

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
