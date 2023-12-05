"""AtonStorage integration."""
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .controller import Controller as AtonStorage

_LOGGER = logging.getLogger(__name__)


@dataclass
class AtonStorageBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Class to describe a AtonStorage sensor entity."""

    value_calc_function: Callable[[AtonStorage], Any] = None


INVERTER_BINARY_SENSOR_DESCRIPTIONS = (
    AtonStorageBinarySensorEntityDescription(
        key="grid_to_house",
        translation_key="grid_to_house",
        name="Grid to House",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_calc_function=lambda controller: controller.grid_to_house
    ),
    AtonStorageBinarySensorEntityDescription(
        key="solar_to_battery",
        translation_key="solar_to_battery",
        name="Solar to Battery",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_calc_function=lambda controller: controller.solar_to_battery
    ),
    AtonStorageBinarySensorEntityDescription(
        key="solar_to_grid",
        translation_key="solar_to_grid",
        name="Solar to Grid",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_calc_function=lambda controller: controller.solar_to_grid
    ),
    AtonStorageBinarySensorEntityDescription(
        key="battery_to_house",
        translation_key="battery_to_house",
        name="Battery to House",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_calc_function=lambda controller: controller.battery_to_house
    ),
    AtonStorageBinarySensorEntityDescription(
        key="solar_to_house",
        translation_key="solar_to_house",
        name="Solar to House",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_calc_function=lambda controller: controller.solar_to_house
    ),
    AtonStorageBinarySensorEntityDescription(
        key="grid_to_battery",
        translation_key="grid_to_battery",
        name="Grid to Battery",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_calc_function=lambda controller: controller.grid_to_battery
    ),
    AtonStorageBinarySensorEntityDescription(
        key="battery_to_grid",
        translation_key="battery_to_grid",
        name="Batter to Grid",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_calc_function=lambda controller: controller.battery_to_grid
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the AtonStorage sensors."""
    _LOGGER.debug("Set up the AtonStorage binary sensors")
    entities = _create_entities(hass, entry)
    async_add_entities(entities, True)


def _create_entities(hass: HomeAssistant, entry: dict):
    entities = []

    controller = hass.data[DOMAIN][entry.entry_id]["controller"]
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    username = hass.data[DOMAIN][entry.entry_id]["username"]
    sensors_selected = hass.data[DOMAIN][entry.entry_id]["sensors_selected"]

    if "BINARY SENSORS" in sensors_selected:
        for entity_description in INVERTER_BINARY_SENSOR_DESCRIPTIONS:
            entities.append(
                AtonStorageBinarySensorEntity(
                    entry=entry,
                    controller=controller,
                    coordinator=coordinator,
                    description=entity_description,
                    username=username,
                )
            )

    return entities


class AtonStorageBinarySensorEntity(CoordinatorEntity, BinarySensorEntity):
    """AtonStorage Sensor which receives its data via an DataUpdateCoordinator."""

    entity_description: AtonStorageBinarySensorEntityDescription
    # _attr_has_entity_name = True

    def __init__(
        self,
        entry: ConfigEntry,
        controller: AtonStorage,
        coordinator,
        description: AtonStorageBinarySensorEntityDescription,
        username,
        # device_info,
    ):
        """Batched AtonStorage Sensor Entity constructor."""
        super().__init__(coordinator)

        self.controller = controller
        self.entity_description = description

        # self._entry = entry
        # self._name = self.entity_description.name
        # self._attr_name = f"{controller.serial_number}_{self.entity_description.name}"
        # self._attr_translation_key = self.entity_description.key
        self._attr_name = f"{username} {self.entity_description.name}"
        self._attr_unique_id = f"{controller.serial_number}_{self.entity_description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "AtonStorage " + username)},
            name=username,
            manufacturer="AtonStorage",
        )

        self._register_key = self.entity_description.key
        if "#" in self._register_key:
            self._register_key = self._register_key[0 : self._register_key.find("#")]

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""

        return self.entity_description.value_calc_function(self.controller)