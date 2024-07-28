import logging
import voluptuous as vol
import json
import uuid
import asyncio
import websockets
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class IPX800ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            device_name = user_input["device_name"]
            ip_address = user_input["ip_address"]
            poll_interval = user_input["poll_interval"]
            unique_id = str(uuid.uuid4())

            async with websockets.connect('ws://localhost:6789') as websocket:
                await websocket.send(json.dumps({
                    "action": "init_device",
                    "device_name": device_name,
                    "ip_address": ip_address,
                    "poll_interval": poll_interval,
                    "unique_id": unique_id
                }))

            return self.async_create_entry(
                title=device_name,
                data={
                    "device_name": device_name,
                    "ip_address": ip_address,
                    "poll_interval": poll_interval,
                    "unique_id": unique_id
                }
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("device_name"): str,
                vol.Required("ip_address"): str,
                vol.Required("poll_interval", default=10): int,
            })
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return IPX800OptionsFlowHandler(config_entry)

class IPX800OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        return await self.async_step_add_device()

    async def async_step_add_device(self, user_input=None):
        if user_input is not None:
            device_name = user_input["device_name"]
            input_button = user_input["input_button"]
            select_leds = user_input["select_leds"]
            unique_id = self.config_entry.data["unique_id"]
            variable_etat_name = f'etat_{device_name.lower().replace(" ", "_")}'

            async with websockets.connect('ws://localhost:6789') as websocket:
                await websocket.send(json.dumps({
                    "action": "add_device",
                    "device_name": device_name,
                    "input_button": input_button,
                    "select_leds": select_leds,
                    "unique_id": unique_id,
                    "variable_etat_name": variable_etat_name
                }))

            return self.async_create_entry(title="", data={})
        
        return self.async_show_form(
            step_id="add_device",
            data_schema=vol.Schema({
                vol.Required("device_name"): str,
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
