"""AtonStorage integration."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import timedelta
from typing import TypeVar

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_MONITORED_VARIABLES,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import AVAILABLE_SENSORS, DEFAULT_SCAN_INTERVAL, DOMAIN
from .controller import Controller as AtonStorage
from .controller import InvalidUsernameOrPasswordError

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
]

# One refresh performs three cloud calls of REQUEST_TIMEOUT each, so the update
# needs room to finish. Tying this to the scan interval, as it used to be, made
# every slow response abort the update.
UPDATE_TIMEOUT = 90

T = TypeVar("T")


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the atonStorage component from YAML."""
    return True


def _entry_value(entry: ConfigEntry, key: str, default):
    """Read a setting, options first, falling back to the initial setup data."""
    return entry.options.get(key, entry.data.get(key, default))


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up AtonStorage from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    user = entry.data.get(CONF_USERNAME)
    password = entry.data.get(CONF_PASSWORD)
    serial_number = entry.data.get(CONF_DEVICE_ID)
    scan_interval = _entry_value(entry, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    sensors_selected = _entry_value(
        entry, CONF_MONITORED_VARIABLES, AVAILABLE_SENSORS
    )

    controller = AtonStorage(
        hass, user, password, serial_number, {"interval": scan_interval}
    )

    try:
        coordinator = await _create_update_coordinator(
            hass, controller, serial_number, timedelta(seconds=scan_interval)
        )
    except Exception:
        # async_config_entry_first_refresh already raises ConfigEntryNotReady or
        # ConfigEntryAuthFailed as appropriate; just do not leak the http client.
        await controller.async_close()
        raise

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "controller": controller,
        "username": user,
        "sensors_selected": sensors_selected,
    }

    # Without this, a new scan interval or sensor selection only took effect
    # after a full Home Assistant restart.
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )
    if unload_ok:
        data = hass.data[DOMAIN].pop(config_entry.entry_id)
        await data["controller"].async_close()

    return unload_ok


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry so changed options are picked up."""
    await hass.config_entries.async_reload(entry.entry_id)


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

    async def _async_update_data(self):
        """Fetch data from AtonStorage."""
        _LOGGER.debug("refreshing data")
        try:
            async with asyncio.timeout(UPDATE_TIMEOUT):
                await self.bridge.refresh()
        except InvalidUsernameOrPasswordError as err:
            # Triggers the reauth flow instead of retrying forever with a
            # password the portal has already rejected.
            raise ConfigEntryAuthFailed(
                "AtonStorage rejected the stored credentials"
            ) from err
        except TimeoutError as err:
            raise UpdateFailed(
                f"Timeout fetching {self.serial_number} values"
            ) from err
        except Exception as err:
            raise UpdateFailed(
                f"Could not update {self.serial_number} values: {err}"
            ) from err

        if not self.bridge.status:
            raise UpdateFailed("Error fetching AtonStorage state")
