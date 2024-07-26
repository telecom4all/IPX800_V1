import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
import sqlite3
import os
import uuid

from .const import DOMAIN, IP_ADDRESS, POLL_INTERVAL

# Configuration du logger pour cette intégration
_LOGGER = logging.getLogger(__name__)

# Définition du flux de configuration pour l'intégration IPX800
@config_entries.HANDLERS.register(DOMAIN)
class IPX800ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1  # Version du flux de configuration
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL  # Classe de connexion pour cette intégration

    async def async_step_user(self, user_input=None):
        """Première étape du flux de configuration où l'utilisateur entre les détails de l'appareil principal."""
        if user_input is not None:
            # Extraction des informations fournies par l'utilisateur
            device_name = user_input["device_name"]
            ip_address = user_input["ip_address"]
            poll_interval = user_input["poll_interval"]
            unique_id = str(uuid.uuid4())  # Génération d'un identifiant unique pour l'appareil

            # Utilisation directe du port 5213 pour l'application
            portapp = 5213

            _LOGGER.debug(f"Creating database for IPX800 at /config/ipx800_{ip_address}.db")
            # Création de la base de données SQLite pour stocker les informations de l'appareil
            db_path = f"/config/ipx800_{ip_address}.db"
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            # Création de la table 'infos' si elle n'existe pas déjà
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS infos (
                    device_name TEXT,
                    ip_address TEXT,
                    poll_interval INTEGER,
                    unique_id TEXT
                )
            ''')
            # Insertion des informations de l'appareil dans la table 'infos'
            cursor.execute('''
                INSERT INTO infos (device_name, ip_address, poll_interval, unique_id)
                VALUES (?, ?, ?, ?)
            ''', (device_name, ip_address, poll_interval, unique_id))
            conn.commit()  # Validation des changements
            conn.close()  # Fermeture de la connexion à la base de données

            _LOGGER.debug(f"Database created and data inserted for IPX800 at /config/ipx800_{ip_address}.db")

            # Création d'une entrée de configuration pour l'appareil principal
            return self.async_create_entry(
                title=device_name,
                data={
                    "device_name": device_name,
                    "ip_address": ip_address,
                    "poll_interval": poll_interval,
                    "portapp": portapp,
                    "unique_id": unique_id,
                    "devices": []
                }
            )

        # Affichage du formulaire pour que l'utilisateur entre les détails de l'appareil principal
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
        """Définir la méthode pour obtenir le flux d'options pour cette entrée de configuration."""
        return IPX800OptionsFlowHandler(config_entry)

# Gestionnaire pour le flux d'options de l'intégration IPX800
class IPX800OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Étape initiale du flux d'options."""
        return await self.async_step_add_device()

    async def async_step_add_device(self, user_input=None):
        """Étape où l'utilisateur ajoute un appareil secondaire."""
        if user_input is not None:
            _LOGGER.debug(f"Adding device to IPX800 at /config/ipx800_{self.config_entry.data['ip_address']}.db")
            # Connexion à la base de données SQLite de l'appareil principal
            conn = sqlite3.connect(f"/config/ipx800_{self.config_entry.data['ip_address']}.db")
            cursor = conn.cursor()

            # Récupération de la liste des appareils secondaires de l'entrée de configuration
            devices = self.config_entry.data.get("devices", [])
            devices.append({
                "device_name": user_input["device_name"],
                "input_button": user_input["input_button"],
                "select_leds": user_input["select_leds"]
            })

            # Création de la table 'devices' si elle n'existe pas déjà
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS devices (
                    device_name TEXT,
                    input_button TEXT,
                    select_leds TEXT,
                    unique_id TEXT,
                    variable_etat_name TEXT
                )
            ''')
            # Insertion des informations du nouvel appareil secondaire dans la table 'devices'
            cursor.execute('''
                INSERT INTO devices (device_name, input_button, select_leds, unique_id, variable_etat_name)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_input["device_name"], user_input["input_button"], ",".join(user_input["select_leds"]), self.config_entry.data["unique_id"], f'etat_{user_input["device_name"].lower().replace(" ", "_")}))
            conn.commit()  # Validation des changements
            conn.close()  # Fermeture de la connexion à la base de données

            _LOGGER.debug(f"Device added to database and Home Assistant entry updated for IPX800 at /config/ipx800_{self.config_entry.data['ip_address']}.db")

            # Mise à jour de l'entrée de configuration avec la nouvelle liste des appareils secondaires
            self.hass.config_entries.async_update_entry(self.config_entry, data={**self.config_entry.data, "devices": devices})

            # Création d'une entrée de configuration vide pour finaliser l'ajout de l'appareil secondaire
            return self.async_create_entry(title="", data={})

        # Affichage du formulaire pour que l'utilisateur entre les détails du nouvel appareil secondaire
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
