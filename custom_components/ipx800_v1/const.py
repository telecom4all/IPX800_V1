"""Constants for IPX800 V1 Integration v2.0."""
from __future__ import annotations

from typing import Final

# Integration
DOMAIN: Final = "ipx800_v1"
MANUFACTURER: Final = "GCE Electronics"
MODEL: Final = "IPX800 V1"

# Configuration
CONF_HOST: Final = "host"
CONF_PORT: Final = "port"
CONF_WEBSOCKET_PORT: Final = "websocket_port"
CONF_DEVICE_NAME: Final = "device_name"
CONF_POLLING_INTERVAL: Final = "polling_interval"
CONF_CONNECTION_TIMEOUT: Final = "connection_timeout"
CONF_RETRY_ATTEMPTS: Final = "retry_attempts"
CONF_FORCE_STATE_REFRESH: Final = "force_state_refresh"

# Defaults
DEFAULT_PORT: Final = 80
DEFAULT_WEBSOCKET_PORT: Final = 9870
DEFAULT_POLLING_INTERVAL: Final = 1.0
DEFAULT_CONNECTION_TIMEOUT: Final = 5.0
DEFAULT_RETRY_ATTEMPTS: Final = 3
DEFAULT_FORCE_STATE_REFRESH: Final = True

# API Endpoints
STATUS_ENDPOINT: Final = "/status.xml"
PRESET_ENDPOINT: Final = "/preset.htm"

# Entity types
PLATFORM_LIGHT: Final = "light"
PLATFORM_BINARY_SENSOR: Final = "binary_sensor"

# IPX800 Hardware limits
MAX_LEDS: Final = 8  # LED0-LED7
MAX_BUTTONS: Final = 8  # BTN0-BTN7
MAX_RELAYS: Final = 8  # REL0-REL7

# State management
STATE_ON: Final = "1"
STATE_OFF: Final = "0"
STATE_UNKNOWN: Final = "unknown"

# WebSocket commands
WS_CMD_SET_LED: Final = "SET_LED"
WS_CMD_GET_STATUS: Final = "GET_STATUS"
WS_CMD_PING: Final = "PING"

# Error messages
ERROR_CANNOT_CONNECT: Final = "cannot_connect"
ERROR_INVALID_HOST: Final = "invalid_host"
ERROR_TIMEOUT: Final = "timeout"
ERROR_UNKNOWN: Final = "unknown"

# Diagnostic attributes
ATTR_LED_STATE: Final = "led_state"
ATTR_BUTTON_STATE: Final = "button_state"
ATTR_LAST_UPDATED: Final = "last_updated"
ATTR_CONNECTION_STATUS: Final = "connection_status"
ATTR_COMMAND_COUNT: Final = "command_count"
ATTR_ERROR_COUNT: Final = "error_count"

# Internal constants
COORDINATOR_UPDATE_INTERVAL: Final = 1.0
WEBSOCKET_RECONNECT_DELAY: Final = 5.0
STATE_VERIFICATION_DELAY: Final = 0.3
MAX_COMMAND_QUEUE_SIZE: Final = 50
