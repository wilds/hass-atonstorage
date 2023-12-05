"""AtonStorage integration."""
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.integration.sensor import IntegrationSensor
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ELECTRIC_CURRENT_AMPERE,
    ELECTRIC_POTENTIAL_VOLT,
    FREQUENCY_HERTZ,
    PERCENTAGE,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify
from homeassistant.util.dt import as_local

from .const import DOMAIN
from .controller import Controller as AtonStorage

_LOGGER = logging.getLogger(__name__)


@dataclass
class AtonStorageSensorEntityDescription(SensorEntityDescription):
    """Class to describe a AtonStorage sensor entity."""

    value_conversion_function: Callable[[Any], Any] = lambda val: val
    value_calc_function: Callable[[AtonStorage], Any] = None


@dataclass
class AtonStorageIntegrationSensorEntityDescription(SensorEntityDescription):
    """Class to describe a AtonStorage Integration sensor entity."""

    source_sensor: str = None


INVERTER_SENSOR_DESCRIPTIONS = (
    # LAST UPDATE
    AtonStorageSensorEntityDescription(
        key="data",
        translation_key="data",
        name="Last update",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_conversion_function=lambda value: as_local(
            datetime.strptime(value, "%d/%m/%Y %H:%M:%S")
        ),
    ),
    # BATTERY
    AtonStorageSensorEntityDescription(
        key="soc",
        translation_key="soc",
        name="Battery level",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        # Limit battery_level to a maximum of 100 and convert it to an integer
        value_conversion_function=lambda value: min(100, int(value)),
    ),
    AtonStorageSensorEntityDescription(
        key="vb",
        translation_key="vb",
        name="Battery voltage",
        icon="mdi:current-dc",
        native_unit_of_measurement=ELECTRIC_POTENTIAL_VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AtonStorageSensorEntityDescription(
        key="ib",
        translation_key="ib",
        name="Battery current",
        icon="mdi:current-dc",
        native_unit_of_measurement=ELECTRIC_CURRENT_AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AtonStorageSensorEntityDescription(
        key="ahCaricati",
        translation_key="ahCaricati",
        name="Battery charged current",
        icon="mdi:battery-plus",
        native_unit_of_measurement="AH",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    AtonStorageSensorEntityDescription(
        key="ahScaricati",
        translation_key="ahScaricati",
        name="Battery discharged current",
        icon="mdi:battery-minus",
        native_unit_of_measurement="AH",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    # INSTANT POWER MEASUREMENTS
    AtonStorageSensorEntityDescription(
        key="pSolare",
        translation_key="pSolare",
        name="Instant solar power",
        icon="mdi:solar-power-variant",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AtonStorageSensorEntityDescription(
        key="pUtenze",
        translation_key="pUtenze",
        name="Instant user power",
        icon="mdi:home-lightning-bolt-outline",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AtonStorageSensorEntityDescription(
        key="pBatteria",
        translation_key="pBatteria",
        name="Instant battery power",
        icon="mdi:battery-charging-high",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AtonStorageSensorEntityDescription(
        key="pRete",
        translation_key="pRete",
        name="Instant grid power",
        icon="mdi:transmission-tower",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # STRING1
    AtonStorageSensorEntityDescription(
        key="string1V",
        translation_key="string1V",
        name="String1 voltage",
        icon="mdi:solar-panel-large",
        native_unit_of_measurement=ELECTRIC_POTENTIAL_VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AtonStorageSensorEntityDescription(
        key="string1I",
        translation_key="string1I",
        name="String1 current",
        icon="mdi:solar-panel-large",
        native_unit_of_measurement=ELECTRIC_CURRENT_AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # STRING2
    AtonStorageSensorEntityDescription(
        key="string2V",
        translation_key="string2V",
        name="String2 voltage",
        icon="mdi:solar-panel-large",
        native_unit_of_measurement=ELECTRIC_POTENTIAL_VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AtonStorageSensorEntityDescription(
        key="string2I",
        translation_key="string2I",
        name="String2 current",
        icon="mdi:solar-panel-large",
        native_unit_of_measurement=ELECTRIC_CURRENT_AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # UTILITIES
    AtonStorageSensorEntityDescription(
        key="utenzeV",
        translation_key="utenzeV",
        name="Utilities voltage",
        icon="mdi:current-ac",
        native_unit_of_measurement=ELECTRIC_POTENTIAL_VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AtonStorageSensorEntityDescription(
        key="utenzeI",
        translation_key="utenzeI",
        name="Utilities current",
        icon="mdi:current-ac",
        native_unit_of_measurement=ELECTRIC_CURRENT_AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # GRID
    AtonStorageSensorEntityDescription(
        key="gridV",
        translation_key="gridV",
        name="Grid voltage",
        icon="mdi:current-ac",
        native_unit_of_measurement=ELECTRIC_POTENTIAL_VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AtonStorageSensorEntityDescription(
        key="gridHz",
        translation_key="gridHz",
        name="Grid frequency",
        native_unit_of_measurement=FREQUENCY_HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # TEMPERATURES
    AtonStorageSensorEntityDescription(
        key="temperatura",
        translation_key="temperatura",
        name="Inverter temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AtonStorageSensorEntityDescription(
        key="temperatura2",
        translation_key="temperatura2",
        name="Temperature 2",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # DAILY ENERGY MEASUREMENTS
    AtonStorageSensorEntityDescription(
        key="eVenduta",
        translation_key="eVenduta",
        name="Daily sold energy",
        icon="mdi:transmission-tower-import",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_conversion_function=lambda value: int(value) / 1000,
        # last_reset=as_local(datetime.combine(date.today(), datetime.min.time())),
    ),
    AtonStorageSensorEntityDescription(
        key="eComprata",
        translation_key="eComprata",
        name="Daily bought energy",
        icon="mdi:transmission-tower-export",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_conversion_function=lambda value: int(value) / 1000,
        # last_reset=as_local(datetime.combine(date.today(), datetime.min.time())),
    ),
    AtonStorageSensorEntityDescription(
        key="ePannelli",
        translation_key="ePannelli",
        name="Daily solar energy",
        icon="mdi:solar-power-variant-outline",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_conversion_function=lambda value: int(value) / 1000,
        # last_reset=as_local(datetime.combine(date.today(), datetime.min.time())),
    ),
    AtonStorageSensorEntityDescription(
        key="eBatteria",
        translation_key="eBatteria",
        name="Daily self consumed energy",
        icon="mdi:battery-charging-high",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_conversion_function=lambda value: int(value) / 1000,
        # last_reset=as_local(datetime.combine(date.today(), datetime.min.time())),
    ),
    ### CALCULATED VALUES ###
    # GRID IN-OUT
    AtonStorageSensorEntityDescription(
        key="pRete_In",
        translation_key="pRete_In",
        name="Instant grid power input",
        icon="mdi:transmission-tower-export",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_calc_function=lambda controller: abs(controller.instant_grid_power)
        if controller.instant_grid_power < 0
        else 0,
    ),
    AtonStorageSensorEntityDescription(
        key="pRete_Out",
        translation_key="pRete_Out",
        name="Instant grid power output",
        icon="mdi:transmission-tower-import",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_calc_function=lambda controller: controller.instant_grid_power
        if controller.instant_grid_power > 0
        else 0,
    ),
    # CONSUMED ENERGY
    AtonStorageSensorEntityDescription(
        key="eConsumed",
        translation_key="eConsumed",
        name="Daily consumed energy",
        #icon="mdi:home-battery",
        icon="mdi:home-lightning-bolt",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_calc_function=lambda controller: int(controller.consumed_energy) / 1000,
    ),
    # SELF SUFFICIENCY
    AtonStorageSensorEntityDescription(
        key="self_sufficiency",
        translation_key="self_sufficiency",
        name="Self sufficiency",
        icon="mdi:home-percent-outline",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_calc_function=lambda controller: round(100 - ((int(controller.bought_energy) / int(controller.consumed_energy)) *100), 2),
    ),
    # BATTERY IN-OUT
    AtonStorageSensorEntityDescription(
        key="pBatteriaIn",
        translation_key="pBatteriaIn",
        name="Instant battery power input",
        icon="mdi:battery-plus",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_calc_function=lambda controller: controller.instant_battery_power
        if controller.instant_battery_power > 0
        else 0,
    ),
    AtonStorageSensorEntityDescription(
        key="pBatteriaOut",
        translation_key="pBatteriaOut",
        name="Instant battery power output",
        icon="mdi:battery-minus",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_calc_function=lambda controller: abs(controller.instant_battery_power)
        if controller.instant_battery_power < 0
        else 0,
    ),
    # BATTERY CHARGED-DISCHARGED
    AtonStorageIntegrationSensorEntityDescription(
        key="eCharged",
        translation_key="eCharged",
        name="Battery charged energy",
        icon="mdi:battery-plus",
        #native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        #state_class=SensorStateClass.TOTAL,
        source_sensor="instant_battery_power_input",
    ),
    AtonStorageIntegrationSensorEntityDescription(
        key="eDischarged",
        translation_key="eDischarged",
        name="Battery discharged energy",
        icon="mdi:battery-minus",
        #native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        #state_class=SensorStateClass.TOTAL,
        source_sensor="instant_battery_power_output",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the AtonStorage sensors."""
    _LOGGER.debug("Set up the AtonStorage sensors")
    entities = _create_entities(hass, entry)
    async_add_entities(entities, True)


def _create_entities(hass: HomeAssistant, entry: dict):
    entities = []

    controller = hass.data[DOMAIN][entry.entry_id]["controller"]
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    username = hass.data[DOMAIN][entry.entry_id]["username"]
    sensors_selected = hass.data[DOMAIN][entry.entry_id]["sensors_selected"]

    for entity_description in INVERTER_SENSOR_DESCRIPTIONS:  
        if entity_description.name in sensors_selected:
            if isinstance(entity_description, AtonStorageSensorEntityDescription):
                entities.append(
                    AtonStorageSensorEntity(
                        entry=entry,
                        controller=controller,
                        coordinator=coordinator,
                        description=entity_description,
                        username=username,
                    )
                )
            elif isinstance(entity_description, AtonStorageIntegrationSensorEntityDescription):
                entities.append(
                    AtonStorageIntegrationSensor(
                        integration_method="left",
                        name=f"{username} {entity_description.name}",
                        round_digits=2,
                        source_entity=f"sensor.{slugify(username)}_{entity_description.source_sensor}",
                        unique_id=f"{controller.serial_number}_{entity_description.key}",
                        unit_prefix="k",
                        unit_time="h",
                        entry=entry,
                        controller=controller,
                        description=entity_description,
                        username=username,
                    )
                )

    return entities


class AtonStorageSensorEntity(CoordinatorEntity, SensorEntity):
    """AtonStorage Sensor which receives its data via an DataUpdateCoordinator."""

    entity_description: AtonStorageSensorEntityDescription
    # _attr_has_entity_name = True

    def __init__(
        self,
        entry: ConfigEntry,
        controller: AtonStorage,
        coordinator,
        description: AtonStorageSensorEntityDescription,
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
    def native_value(self):
        """Native sensor value."""

        if self.entity_description.value_calc_function:
            value = self.entity_description.value_calc_function(self.controller)
        else:
            value = self.controller.get_raw_data(self._register_key)

        if self.entity_description.value_conversion_function:
            value = self.entity_description.value_conversion_function(value)

        return value

    @property
    def extra_state_attributes(self):
        if self.entity_description.key == "data":
            attrSensor = {
                "update delay (s)": self.controller.get_raw_data("DiffDate"),
                "serial number": self.controller.get_raw_data("serialNumber"),
                "firmware version": self.controller.get_raw_data("fwScheda"),
                "bios version": self.controller.get_raw_data("relBIOS"),
                "status": self.controller.get_raw_data("status"),
                "status man": self.controller.get_raw_data("statusMan"),
                "run mode": self.controller.get_raw_data("runMode"),
            }
            return attrSensor
        if self.entity_description.key == "soc":
            attrSensor = {
                "raw data": self.controller.get_raw_data("soc"),
                "batteries number": self.controller.get_raw_data("numBatterie"),
            }
            return attrSensor


class AtonStorageIntegrationSensor(IntegrationSensor):
    """Representation of an integration sensor."""

    entity_description: AtonStorageIntegrationSensorEntityDescription

    def __init__(
        self,
        *,
        integration_method: str,
        name: str | None,
        round_digits: int,
        source_entity: str,
        unique_id: str | None,
        unit_prefix: str | None,
        unit_time: str,
        entry: ConfigEntry,
        controller: AtonStorage,
        description: AtonStorageIntegrationSensorEntityDescription,
        username,
    ) -> None:
        """Initialize the integration sensor."""
        super().__init__(
            integration_method=integration_method,
            name=name,
            round_digits=round_digits,
            source_entity=source_entity,
            unique_id=unique_id,
            unit_prefix=unit_prefix,
            unit_time=unit_time,
        )
        
        self.entity_description = description
        self.controller = controller
        self._entry = entry
        self._name = name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "AtonStorage " + username)},
            name=username,
            manufacturer="AtonStorage",
        )

    @property
    def icon(self):
        return self.entity_description.icon
    
    @property
    def device_class(self):
        return self.entity_description.device_class
