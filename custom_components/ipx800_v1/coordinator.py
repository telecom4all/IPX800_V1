"""Data coordinator for IPX800 V1 Integration v2.0."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Set
from xml.etree import ElementTree as ET

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    COORDINATOR_UPDATE_INTERVAL,
    DEFAULT_CONNECTION_TIMEOUT,
    DEFAULT_RETRY_ATTEMPTS,
    DOMAIN,
    MAX_BUTTONS,
    MAX_LEDS,
    PRESET_ENDPOINT,
    STATE_OFF,
    STATE_ON,
    STATE_UNKNOWN,
    STATE_VERIFICATION_DELAY,
    STATUS_ENDPOINT,
    WEBSOCKET_RECONNECT_DELAY,
    WS_CMD_SET_LED,
)

_LOGGER = logging.getLogger(__name__)


class IPX800StateManager:
    """Centralized state manager for IPX800 device."""
    
    def __init__(self):
        """Initialize state manager."""
        self._leds: Dict[int, str] = {}
        self._buttons: Dict[int, str] = {}
        self._last_updated: Optional[datetime] = None
        self._lock = asyncio.Lock()
        self._command_count = 0
        self._error_count = 0
        
    async def update_led_state(self, led_num: int, state: str, source: str = "unknown") -> None:
        """Update LED state thread-safely."""
        async with self._lock:
            old_state = self._leds.get(led_num, STATE_UNKNOWN)
            self._leds[led_num] = state
            self._last_updated = dt_util.utcnow()
            _LOGGER.debug(
                "LED%d state updated: %s -> %s (source: %s)", 
                led_num, old_state, state, source
            )
    
    async def update_button_state(self, btn_num: int, state: str) -> None:
        """Update button state thread-safely."""
        async with self._lock:
            old_state = self._buttons.get(btn_num, STATE_UNKNOWN)
            self._buttons[btn_num] = state
            self._last_updated = dt_util.utcnow()
            if old_state != state:
                _LOGGER.info("Button%d state changed: %s -> %s", btn_num, old_state, state)
    
    async def get_led_state(self, led_num: int) -> str:
        """Get LED state thread-safely."""
        async with self._lock:
            return self._leds.get(led_num, STATE_UNKNOWN)
    
    async def get_button_state(self, btn_num: int) -> str:
        """Get button state thread-safely."""
        async with self._lock:
            return self._buttons.get(btn_num, STATE_UNKNOWN)
    
    async def get_all_states(self) -> Dict[str, Any]:
        """Get all states as dict."""
        async with self._lock:
            return {
                "leds": self._leds.copy(),
                "buttons": self._buttons.copy(),
                "last_updated": self._last_updated,
                "command_count": self._command_count,
                "error_count": self._error_count,
            }
    
    async def increment_command_count(self) -> None:
        """Increment command counter."""
        async with self._lock:
            self._command_count += 1
    
    async def increment_error_count(self) -> None:
        """Increment error counter."""
        async with self._lock:
            self._error_count += 1


class IPX800Coordinator(DataUpdateCoordinator):
    """IPX800 data coordinator with robust state management."""
    
    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int = 80,
        websocket_port: int = 9870,
        device_name: str = "IPX800",
        polling_interval: float = COORDINATOR_UPDATE_INTERVAL,
        connection_timeout: float = DEFAULT_CONNECTION_TIMEOUT,
        retry_attempts: int = DEFAULT_RETRY_ATTEMPTS,
        force_state_refresh: bool = True,
    ) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{device_name}",
            update_interval=timedelta(seconds=polling_interval),
        )
        
        self.host = host
        self.port = port
        self.websocket_port = websocket_port
        self.device_name = device_name
        self.connection_timeout = connection_timeout
        self.retry_attempts = retry_attempts
        self.force_state_refresh = force_state_refresh
        
        # State management
        self.state_manager = IPX800StateManager()
        self._connection_status = "disconnected"
        self._command_lock = asyncio.Lock()
        
        # URLs
        self.base_url = f"http://{host}:{port}"
        self.status_url = f"{self.base_url}{STATUS_ENDPOINT}"
        self.preset_url = f"{self.base_url}{PRESET_ENDPOINT}"
        
    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from IPX800."""
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.connection_timeout)
            ) as session:
                async with session.get(self.status_url) as response:
                    if response.status != 200:
                        raise UpdateFailed(f"HTTP {response.status}")
                    
                    xml_data = await response.text()
                    await self._parse_status_xml(xml_data)
                    
                    return await self.state_manager.get_all_states()
                    
        except asyncio.TimeoutError:
            await self.state_manager.increment_error_count()
            raise UpdateFailed("Timeout connecting to IPX800")
        except Exception as err:
            await self.state_manager.increment_error_count()
            _LOGGER.error("Error updating data: %s", err)
            raise UpdateFailed(f"Error communicating with IPX800: {err}")
    
    async def _parse_status_xml(self, xml_data: str) -> None:
        """Parse XML status response and update states."""
        try:
            root = ET.fromstring(xml_data)
            
            # Update LED states
            for led_num in range(MAX_LEDS):
                led_element = root.find(f"led{led_num}")
                if led_element is not None:
                    state = STATE_ON if led_element.text == "1" else STATE_OFF
                    await self.state_manager.update_led_state(led_num, state, "http_poll")
            
            # Update button states
            for btn_num in range(MAX_BUTTONS):
                btn_element = root.find(f"btn{btn_num}")
                if btn_element is not None:
                    state = STATE_ON if btn_element.text == "1" else STATE_OFF
                    await self.state_manager.update_button_state(btn_num, state)
                    
        except ET.ParseError as err:
            _LOGGER.error("Error parsing XML response: %s", err)
            await self.state_manager.increment_error_count()
    
    async def async_set_led_state(self, led_num: int, state: bool) -> bool:
        """Set LED state with robust synchronization."""
        if not 0 <= led_num < MAX_LEDS:
            _LOGGER.error("Invalid LED number: %d", led_num)
            return False
        
        async with self._command_lock:
            try:
                # Send command via HTTP
                success = await self._send_led_http_command(led_num, state)
                
                if success:
                    await self.state_manager.increment_command_count()
                    
                    # Update local state immediately
                    new_state = STATE_ON if state else STATE_OFF
                    await self.state_manager.update_led_state(led_num, new_state, "command")
                    
                    # Force verification after delay
                    if self.force_state_refresh:
                        await asyncio.sleep(STATE_VERIFICATION_DELAY)
                        await self._verify_led_state(led_num, state)
                
                return success
                
            except Exception as err:
                _LOGGER.error("Error setting LED%d state: %s", led_num, err)
                await self.state_manager.increment_error_count()
                return False
    
    async def _send_led_http_command(self, led_num: int, state: bool) -> bool:
        """Send LED command via HTTP."""
        try:
            action = "SetLED" if state else "ClearLED"
            url = f"{self.preset_url}?{action}={led_num}"
            
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.connection_timeout)
            ) as session:
                async with session.get(url) as response:
                    success = response.status == 200
                    _LOGGER.debug("HTTP command sent: LED%d = %s (status: %d)", 
                                led_num, state, response.status)
                    return success
                    
        except Exception as err:
            _LOGGER.error("HTTP command failed: %s", err)
            return False
    
    async def _verify_led_state(self, led_num: int, expected_state: bool) -> None:
        """Verify LED state after command."""
        try:
            # Force a data refresh
            await self.async_request_refresh()
            
            # Check if state matches expected
            actual_state = await self.state_manager.get_led_state(led_num)
            expected_state_str = STATE_ON if expected_state else STATE_OFF
            
            if actual_state != expected_state_str:
                _LOGGER.warning(
                    "LED%d state mismatch! Expected: %s, Actual: %s", 
                    led_num, expected_state_str, actual_state
                )
                await self.state_manager.increment_error_count()
            else:
                _LOGGER.debug("LED%d state verified: %s", led_num, actual_state)
                
        except Exception as err:
            _LOGGER.error("Error verifying LED%d state: %s", led_num, err)
    
    async def async_setup(self) -> None:
        """Set up coordinator."""
        _LOGGER.info("Setting up IPX800 coordinator for %s", self.device_name)
        
        # Initial data fetch
        await self.async_config_entry_first_refresh()
        
        _LOGGER.info("IPX800 coordinator setup complete")
    
    async def async_shutdown(self) -> None:
        """Shutdown coordinator."""
        _LOGGER.info("Shutting down IPX800 coordinator")
        _LOGGER.info("IPX800 coordinator shutdown complete")
    
    @property
    def connection_status(self) -> str:
        """Return connection status."""
        return "connected" if self.last_update_success else "disconnected"
    
    async def get_diagnostics(self) -> Dict[str, Any]:
        """Get diagnostic information."""
        states = await self.state_manager.get_all_states()
        return {
            "device_name": self.device_name,
            "host": self.host,
            "connection_status": self.connection_status,
            **states,
        }