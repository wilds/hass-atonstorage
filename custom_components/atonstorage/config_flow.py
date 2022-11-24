"""Config flow for AtonStorage integration."""
import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import slugify

from .const import DEFAULT_NAME, DEFAULT_SCAN_INTERVAL, DOMAIN
from .controller import AtonStorageConnectionError
from .controller import Controller as AtonStorage
from .controller import SerialNumberRequiredError, UsernameAndPasswordRequiredError

_LOGGER = logging.getLogger(__name__)

DEVICE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_DEVICE_ID): str,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
    }
)


class FlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for AtonStorage."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:

                user = user_input.get(CONF_USERNAME, None)
                password = user_input.get(CONF_PASSWORD, None)
                serial_number = user_input.get(CONF_DEVICE_ID, None)
                name = user_input.get(CONF_NAME, DEFAULT_NAME)
                interval = user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

                opts = {
                    "session": async_get_clientsession(self.hass),
                    "interval": interval,
                }
                controller = AtonStorage(self.hass, user, password, serial_number, opts)
                await controller.refresh()

                await self.async_set_unique_id(slugify(controller.serialNumber))
                # await self.async_set_unique_id(slugify(serial_number))
                # self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=name,
                    data=user_input
                    # data={CONF_DEVICE_ID: serial_number, CONF_NAME: name, CONF_SCAN_INTERVAL: interval},
                )
            except AtonStorageConnectionError:
                errors["base"] = "cannot_connect"
            except UsernameAndPasswordRequiredError:
                errors[CONF_USERNAME] = "username_required"
                errors[CONF_PASSWORD] = "password_required"
            except SerialNumberRequiredError:
                errors[CONF_DEVICE_ID] = "serial_number_required"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=DEVICE_SCHEMA, errors=errors
        )

    # async def async_step_import(self, user_input):
    #    """Handle import."""
    #    return await self.async_step_user(user_input)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry):
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(OptionsFlow):
    def __init__(self, config_entry: ConfigEntry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        # return await self.async_step_user()
        # name = self.config_entry.options.get(CONF_NAME, DEFAULT_NAME)

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # serial_number = self.config_entry.options.get(CONF_DEVICE_ID, None)
        # name = self.config_entry.options.get(CONF_NAME, DEFAULT_NAME)
        interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    # vol.Required(CONF_DEVICE_ID, default=serial_number): str,
                    # vol.Optional(CONF_NAME, default=name): str,
                    vol.Optional(CONF_SCAN_INTERVAL, default=interval): int,
                }
            ),
        )

    # async def async_step_user(self, user_input=None):
    #    """Handle a flow initialized by the user."""
    #    name = self.config_entry.options.get(CONF_NAME, DEFAULT_NAME)

    #    if user_input is not None:
    #        return self.async_create_entry(title=name, data=user_input)

    #    #serial_number = self.config_entry.options.get(CONF_DEVICE_ID, None)
    #    #name = self.config_entry.options.get(CONF_NAME, DEFAULT_NAME)
    #    interval = self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    #    return self.async_show_form(
    #        step_id="user",
    #        data_schema=vol.Schema({
    #            #vol.Required(CONF_DEVICE_ID, default=serial_number): str,
    #            #vol.Optional(CONF_NAME, default=name): str,
    #            vol.Optional(CONF_SCAN_INTERVAL, default=interval): int,
    #        })
    #    )
