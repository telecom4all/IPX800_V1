import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
import sqlite3
import os

from .const import DOMAIN, IP_ADDRESS, POLL_INTERVAL

_LOGGER = logging.getLogger(__name__)

@config_entries.HANDLERS.register(DOMAIN)
class IPX800ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        self.device_name = None
        self.ip_address = None
        self.poll_interval = None

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            self.device_name = user_input["device_name"]
            self.ip_address = user_input["ip_address"]
            self.poll_interval = user_input["poll_interval"]
            return await self.async_step_device()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("device_name"): str,
                vol.Required("ip_address"): str,
                vol.Required("poll_interval", default=10): int,
            })
        )

    async def async_step_device(self, user_input=None):
        if user_input is not None:
            db_path = f"/config/ipx800_{self.ip_address}.db"
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS infos (
                    device_name TEXT,
                    ip_address TEXT,
                    poll_interval INTEGER,
                    unique_id TEXT
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS devices (
                    device_name TEXT,
                    input_button TEXT,
                    select_leds TEXT,
                    unique_id TEXT,
                    variable_etat_name TEXT
                )
            ''')
            cursor.execute('''
                INSERT INTO infos (device_name, ip_address, poll_interval, unique_id)
                VALUES (?, ?, ?, ?)
            ''', (self.device_name, self.ip_address, self.poll_interval, self.unique_id))
            conn.commit()

            devices = [{
                "device_name": user_input["device_name"],
                "input_button": user_input["input_button"],
                "select_leds": user_input["select_leds"]
            }]

            cursor.execute('''
                INSERT INTO devices (device_name, input_button, select_leds, unique_id, variable_etat_name)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_input["device_name"], user_input["input_button"], ",".join(user_input["select_leds"]), self.unique_id, f'etat_{user_input["device_name"].lower().replace(" ", "_")}'))
            conn.commit()
            conn.close()

            portapp = self.hass.data["ipx800_v1"].get("portapp", 5213)  # Fetching the portapp from addon configuration
            api_url = f"http://localhost:{portapp}"

            return self.async_create_entry(
                title=self.device_name,
                data={
                    "device_name": self.device_name,
                    "ip_address": self.ip_address,
                    "poll_interval": self.poll_interval,
                    "api_url": api_url,
                    "unique_id": self.unique_id,
                    "devices": devices
                }
            )

        return self.async_show_form(
            step_id="device",
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

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return IPX800OptionsFlowHandler(config_entry)

class IPX800OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        return self.async_show_form(step_id="init", data_schema=vol.Schema({}), errors={})
