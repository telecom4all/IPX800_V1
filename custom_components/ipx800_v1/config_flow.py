import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
import sqlite3
import os
import uuid
import json
import websockets
from .const import DOMAIN, IP_ADDRESS, POLL_INTERVAL, WEBSOCKET_URL, WS_PORT

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
            websocket_url = f"ws://localhost:{WS_PORT}"

            # Création de la base de données SQLite
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
                    ip_address TEXT
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
                    "unique_id": unique_id,
                    "websocket_url": websocket_url,
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
            new_device = {
                "device_name": user_input["device_name"],
                "input_button": user_input["input_button"],
                "select_leds": user_input["select_leds"]
            }
            devices.append(new_device)
            cursor.execute('''
                INSERT INTO devices (device_name, input_button, select_leds, unique_id, variable_etat_name, ip_address)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                user_input["device_name"],
                user_input["input_button"],
                ",".join(user_input["select_leds"]),
                self.config_entry.data["unique_id"],
                f'etat_{user_input["device_name"].lower().replace(" ", "_")}',
                self.config_entry.data["ip_address"]
            ))
            conn.commit()
            conn.close()
            
            self.hass.config_entries.async_update_entry(self.config_entry, data={**self.config_entry.data, "devices": devices})

            # Ajouter les entités pour le nouveau sous-appareil
            await add_new_entities(self.hass, self.config_entry, [new_device])
            
            async with websockets.connect(f'ws://localhost:{WS_PORT}') as websocket:
                await websocket.send(json.dumps({
                    "action": "add_device",
                    "device_name": user_input["device_name"],
                    "input_button": user_input["input_button"],
                    "select_leds": user_input["select_leds"],
                    "unique_id": self.config_entry.data["unique_id"],
                    "variable_etat_name": f'etat_{user_input["device_name"].lower().replace(" ", "_")}',
                    "ip_address": self.config_entry.data["ip_address"]
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

async def add_new_entities(hass, config_entry, devices):
    for device in devices:
        await hass.config_entries.async_forward_entry_setup(config_entry, "light")
        await hass.config_entries.async_forward_entry_setup(config_entry, "sensor")

