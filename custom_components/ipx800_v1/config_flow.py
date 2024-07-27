import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
import sqlite3
import os
import uuid

from .const import DOMAIN, IP_ADDRESS, POLL_INTERVAL, API_URL

_LOGGER = logging.getLogger(__name__)

@config_entries.HANDLERS.register(DOMAIN)
class IPX800ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            device_name = user_input["device_name"]
            ip_address = user_input["ip_address"]
            poll_interval = user_input["poll_interval"]
            unique_id = str(uuid.uuid4())
            portapp = 5213
            api_url = f"http://{ip_address}:{portapp}"

            db_path = f"/config/ipx800_{ip_address}.db"
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
                INSERT INTO infos (device_name, ip_address, poll_interval, unique_id)
                VALUES (?, ?, ?, ?)
            ''', (device_name, ip_address, poll_interval, unique_id))
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS devices (
                    device_name TEXT,
                    input_button TEXT,
                    select_leds TEXT,
                    unique_id TEXT,
                    variable_etat_name TEXT,
                    poll_interval_device INTEGER
                )
            ''')
            conn.commit()
            conn.close()

            return self.async_create_entry(
                title=device_name,
                data={
                    "device_name": device_name,
                    "ip_address": ip_address,
                    "poll_interval": poll_interval,
                    "portapp": portapp,
                    "unique_id": unique_id,
                    "api_url": api_url,
                    "devices": []
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
            conn = sqlite3.connect(f"/config/ipx800_{self.config_entry.data['ip_address']}.db")
            cursor = conn.cursor()

            devices = self.config_entry.data.get("devices", [])
            devices.append({
                "device_name": user_input["device_name"],
                "input_button": user_input["input_button"],
                "select_leds": user_input["select_leds"],
                "poll_interval_device": user_input["poll_interval_device"]
            })

            variable_etat_name = f'etat_{user_input["device_name"].lower().replace(" ", "_")}'

            cursor.execute('''
                INSERT INTO devices (device_name, input_button, select_leds, unique_id, variable_etat_name, poll_interval_device)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_input["device_name"], user_input["input_button"], ",".join(user_input["select_leds"]), self.config_entry.data["unique_id"], variable_etat_name, user_input["poll_interval_device"]))
            conn.commit()
            conn.close()

            self.hass.config_entries.async_update_entry(self.config_entry, data={**self.config_entry.data, "devices": devices})

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
                vol.Required("poll_interval_device", default=10): int,
            })
        )
