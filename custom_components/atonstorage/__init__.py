"""AtonStorage integration."""

import logging
from datetime import timedelta

import async_timeout
from collections.abc import Awaitable, Callable
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_SCAN_INTERVAL,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.debounce import Debouncer
from .controller import Controller as AtonStorage
from typing import TypeVar

from .const import (
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.SENSOR,
]
TIMEOUT = 10

T = TypeVar("T")

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the atonStorage component from YAML."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up AtonStorage from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    device = entry.data.get(CONF_DEVICE_ID)

    try:
        opts = {"session": async_get_clientsession(hass)}
        controller = AtonStorage(hass, device, opts)

        scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        coordinator = await _create_update_coordinator(hass, controller, device, timedelta(seconds=scan_interval))

        hass.data[DOMAIN][entry.entry_id] = {
            "coordinator": coordinator,
            "controller": controller,
        }

    except Exception as exc:
        _LOGGER.error("Unable to connect to AtonStorage controller: %s", str(exc))
        raise ConfigEntryNotReady

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)

    return unload_ok

async def _create_update_coordinator(
    hass,
    bridge: AtonStorage,
    serial_number: str,
    update_interval: timedelta,
):

    coordinator = AtonStorageUpdateCoordinator(
        hass,
        _LOGGER,
        bridge=bridge,
        serial_number=serial_number,
        name=f"{serial_number}_data_update_coordinator",
        update_interval=update_interval,
    )

    await coordinator.async_config_entry_first_refresh()

    return coordinator


class AtonStorageUpdateCoordinator(DataUpdateCoordinator):
    """A specialised DataUpdateCoordinator for AtonStorage."""

    def __init__(
        self,
        hass: HomeAssistant,
        logger: logging.Logger,
        bridge: AtonStorage,
        serial_number: str,
        name: str,
        update_interval: timedelta | None = None,
        update_method: Callable[[], Awaitable[T]] | None = None,
        request_refresh_debouncer: Debouncer | None = None,
    ) -> None:
        """Create a AtonStorageUpdateCoordinator."""
        super().__init__(
            hass,
            logger,
            name=name,
            update_interval=update_interval,
            update_method=update_method,
            request_refresh_debouncer=request_refresh_debouncer,
        )
        self.bridge = bridge
        self.serial_number = serial_number
        self.update_interval = update_interval

    async def _async_update_data(self):
        """Fetch data from AtonStorage."""
        _LOGGER.debug("refreshing data")
        async with async_timeout.timeout(self.update_interval.seconds):
            try:
                await self.bridge.refresh()
            except Exception as err:
                raise UpdateFailed(
                    f"Could not update {self.serial_number} values: {err}"
                ) from err
            if not self.bridge.status:
                raise UpdateFailed("Error fetching AtonStorage state")
