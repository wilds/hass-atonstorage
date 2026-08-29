"""Config flow for AtonStorage integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_MONITORED_VARIABLES,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
)
from homeassistant.helpers import selector
from homeassistant.util import slugify

from .const import AVAILABLE_SENSORS, DEFAULT_NAME, DEFAULT_SCAN_INTERVAL, DOMAIN
from .controller import AtonStorageConnectionError
from .controller import Controller as AtonStorage
from .controller import (
    InvalidUsernameOrPasswordError,
    SerialNumberRequiredError,
    UsernameAndPasswordRequiredError,
)

_LOGGER = logging.getLogger(__name__)

# The value is forwarded to set_request.php as the plant's monitoring interval,
# so it has to stay an int and within something the portal accepts.
SCAN_INTERVAL_VALIDATOR = vol.All(vol.Coerce(int), vol.Range(min=10, max=3600))

SENSOR_SELECTOR = selector.SelectSelector(
    selector.SelectSelectorConfig(
        options=AVAILABLE_SENSORS,
        multiple=True,
        mode=selector.SelectSelectorMode.LIST,
    ),
)

DEVICE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_DEVICE_ID): str,
        vol.Optional(
            CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
        ): SCAN_INTERVAL_VALIDATOR,
        vol.Required(CONF_MONITORED_VARIABLES, default=AVAILABLE_SENSORS): (
            SENSOR_SELECTOR
        ),
    }
)

REAUTH_SCHEMA = vol.Schema({vol.Required(CONF_PASSWORD): str})


class FlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for AtonStorage."""

    VERSION = 1

    _reauth_entry: ConfigEntry | None = None

    async def _async_validate(
        self, data: dict[str, Any]
    ) -> tuple[dict[str, str], str | None]:
        """Try the credentials, returning form errors and the plant serial."""
        controller = None
        try:
            controller = AtonStorage(
                self.hass,
                data.get(CONF_USERNAME),
                data.get(CONF_PASSWORD),
                data.get(CONF_DEVICE_ID),
                {"interval": data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)},
            )
            await controller.refresh()
            return {}, controller.serial_number
        except InvalidUsernameOrPasswordError:
            return {"base": "invalid_auth"}, None
        except AtonStorageConnectionError:
            return {"base": "cannot_connect"}, None
        except UsernameAndPasswordRequiredError:
            return {
                CONF_USERNAME: "username_required",
                CONF_PASSWORD: "password_required",
            }, None
        except SerialNumberRequiredError:
            return {CONF_DEVICE_ID: "serial_number_required"}, None
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            return {"base": "unknown"}, None
        finally:
            if controller is not None:
                await controller.async_close()

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            errors, serial_number = await self._async_validate(user_input)

            if not errors:
                # Outside the validation helper on purpose: the AbortFlow raised
                # here must not be swallowed by its broad except.
                await self.async_set_unique_id(slugify(serial_number))
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"{DEFAULT_NAME} {user_input.get(CONF_USERNAME)}",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user", data_schema=DEVICE_SCHEMA, errors=errors
        )

    async def async_step_reauth(self, entry_data):
        """Handle credentials the portal no longer accepts."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        """Ask for a new password and validate it before storing it."""
        errors: dict[str, str] = {}
        entry = self._reauth_entry

        if user_input is not None:
            new_data = {**entry.data, **user_input}
            errors, _ = await self._async_validate(new_data)

            if not errors:
                self.hass.config_entries.async_update_entry(entry, data=new_data)
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=REAUTH_SCHEMA,
            description_placeholders={"username": entry.data.get(CONF_USERNAME)},
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry):
        return OptionsFlowHandler()


class OptionsFlowHandler(OptionsFlow):
    """Handle the scan interval and the sensor selection after setup."""

    @property
    def config_entry(self):
        return self.hass.config_entries.async_get_entry(self.handler)

    async def async_step_init(self, user_input=None):
        """Manage the options."""

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        entry = self.config_entry
        # Options win, but the values chosen during setup live in entry.data.
        interval = entry.options.get(
            CONF_SCAN_INTERVAL,
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        selected = entry.options.get(
            CONF_MONITORED_VARIABLES,
            entry.data.get(CONF_MONITORED_VARIABLES, AVAILABLE_SENSORS),
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL, default=interval
                    ): SCAN_INTERVAL_VALIDATOR,
                    vol.Required(
                        CONF_MONITORED_VARIABLES, default=selected
                    ): SENSOR_SELECTOR,
                }
            ),
        )
