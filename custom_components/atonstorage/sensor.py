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
    CONF_NAME,
    ELECTRIC_CURRENT_AMPERE,
    ELECTRIC_POTENTIAL_VOLT,
    FREQUENCY_HERTZ,
    PERCENTAGE,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
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
    AtonStorageSensorEntityDescription(
        key="data",
        name="Date",
        icon="mdi:calendar-range",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_conversion_function=lambda value: as_local(
            datetime.strptime(value, "%d/%m/%Y %H:%M:%S")
        ),
    ),
    AtonStorageSensorEntityDescription(
        key="pSolare",
        name="Instant solar power",
        icon="mdi:solar-power-variant",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AtonStorageSensorEntityDescription(
        key="pUtenze",
        name="Instant user power",
        icon="mdi:home-lightning-bolt-outline",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AtonStorageSensorEntityDescription(
        key="pBatteria",
        name="Instant battery power",
        icon="mdi:home-battery",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AtonStorageSensorEntityDescription(
        key="pReteIn",
        name="Power grid input",
        icon="mdi:transmission-tower-import",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AtonStorageSensorEntityDescription(
        key="pReteOut",
        name="Power grid output",
        icon="mdi:transmission-tower-export",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AtonStorageSensorEntityDescription(
        key="pRete",
        name="Power grid",
        icon="mdi:transmission-tower",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AtonStorageSensorEntityDescription(
        key="soc",
        name="State of battery",
        icon="mdi:battery-heart-variant",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AtonStorageSensorEntityDescription(
        key="string1V",
        name="String1 Voltage",
        icon="mdi:solar-panel-large",
        native_unit_of_measurement=ELECTRIC_POTENTIAL_VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AtonStorageSensorEntityDescription(
        key="string1I",
        name="String1 Current",
        icon="mdi:solar-panel-large",
        native_unit_of_measurement=ELECTRIC_CURRENT_AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AtonStorageSensorEntityDescription(
        key="string2V",
        name="String2 Voltage",
        icon="mdi:solar-panel-large",
        native_unit_of_measurement=ELECTRIC_POTENTIAL_VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AtonStorageSensorEntityDescription(
        key="string2I",
        name="String2 Current",
        icon="mdi:solar-panel-large",
        native_unit_of_measurement=ELECTRIC_CURRENT_AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AtonStorageSensorEntityDescription(
        key="utenzeV",
        name="Utilities Voltage",
        icon="mdi:flash-triangle-outline",
        native_unit_of_measurement=ELECTRIC_POTENTIAL_VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AtonStorageSensorEntityDescription(
        key="utenzeI",
        name="Utilities Current",
        icon="mdi:current-dc",
        native_unit_of_measurement=ELECTRIC_CURRENT_AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AtonStorageSensorEntityDescription(
        key="ahCaricati",
        name="Current charged",
        icon="mdi:battery-plus-variant",
        native_unit_of_measurement="AH",
        # device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    AtonStorageSensorEntityDescription(
        key="ahScaricati",
        name="Current discharged",
        icon="mdi:battery-minus-variant",
        native_unit_of_measurement="AH",
        # device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    AtonStorageSensorEntityDescription(
        key="vb",
        name="Battery Voltage",
        icon="mdi:current-dc",
        native_unit_of_measurement=ELECTRIC_POTENTIAL_VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AtonStorageSensorEntityDescription(
        key="ib",
        name="Battery Current",
        icon="mdi:current-dc",
        native_unit_of_measurement=ELECTRIC_CURRENT_AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AtonStorageSensorEntityDescription(
        key="pMaxVenduta",
        name="Max power sold",
        icon="mdi:transmission-tower-export",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    AtonStorageSensorEntityDescription(
        key="pMaxPannelli",
        name="Panels max power",
        icon="mdi:solar-panel",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    AtonStorageSensorEntityDescription(
        key="pMaxBatteria",
        name="Battery max power",
        icon="mdi:battery-charging-100",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    AtonStorageSensorEntityDescription(
        key="pMaxComprata",
        name="Max power bought",
        icon="mdi:transmission-tower-import",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    AtonStorageSensorEntityDescription(
        key="eVenduta",
        name="Daily energy sold",
        icon="mdi:solar-power",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_conversion_function=lambda value: int(value) / 1000,
        # last_reset=as_local(datetime.combine(date.today(), datetime.min.time())),
    ),
    AtonStorageSensorEntityDescription(
        key="ePannelli",
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
        name="Daily battery energy",
        icon="mdi:battery-charging-high",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_conversion_function=lambda value: int(value) / 1000,
        # last_reset=as_local(datetime.combine(date.today(), datetime.min.time())),
    ),
    AtonStorageSensorEntityDescription(
        key="eComprata",
        name="Daily energy bought",
        icon="mdi:transmission-tower-import",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_conversion_function=lambda value: int(value) / 1000,
        # last_reset=as_local(datetime.combine(date.today(), datetime.min.time())),
    ),
    AtonStorageSensorEntityDescription(
        key="gridV",
        name="Grid Voltage",
        icon="mdi:power-plug-outline",
        native_unit_of_measurement=ELECTRIC_POTENTIAL_VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AtonStorageSensorEntityDescription(
        key="gridHz",
        name="Grid Frequency",
        icon="mdi:sine-wave",
        native_unit_of_measurement=FREQUENCY_HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AtonStorageSensorEntityDescription(
        key="pGrid",
        name="Instant Grid power",
        icon="mdi:transmission-tower",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AtonStorageSensorEntityDescription(
        key="temperatura",
        name="Inverter Temperature",
        icon="mdi:thermometer-low",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AtonStorageSensorEntityDescription(
        key="temperatura2",
        name="Temperature 2",
        icon="mdi:thermometer-low",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AtonStorageSensorEntityDescription(
        key="numBatterie",
        name="Batteries number",
        icon="mdi:battery",
        # device_class=SensorDeviceClass.NONE,
        # state_class=SensorStateClass.MEASUREMENT,
    ),
    # Calculated values
    AtonStorageSensorEntityDescription(
        key="pBatteriaIn",
        name="Instant battery power input",
        icon="mdi:battery-plus-variant",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_calc_function=lambda controller: controller.instantBatteryPower
        if controller.instantBatteryPower > 0
        else 0,
    ),
    AtonStorageSensorEntityDescription(
        key="pBatteriaOut",
        name="Instant battery power output",
        icon="mdi:battery-minus-variant",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_calc_function=lambda controller: abs(controller.instantBatteryPower)
        if controller.instantBatteryPower < 0
        else 0,
    ),
    AtonStorageIntegrationSensorEntityDescription(
        key="eCharged",
        name="Battery charged energy",
        icon="mdi:battery",
        # native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        # device_class=SensorDeviceClass.ENERGY,
        # state_class=SensorStateClass.TOTAL_INCREASING,
        source_sensor="sensor.instant_battery_power_input",
    ),
    AtonStorageIntegrationSensorEntityDescription(
        key="eDischarged",
        name="Battery discharged energy",
        icon="mdi:battery",
        # native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        # device_class=SensorDeviceClass.ENERGY,
        # state_class=SensorStateClass.TOTAL_INCREASING,
        source_sensor="sensor.instant_battery_power_output",
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
    name = entry.data[CONF_NAME]

    for entity_description in INVERTER_SENSOR_DESCRIPTIONS:
        if isinstance(entity_description, AtonStorageSensorEntityDescription):
            entities.append(
                AtonStorageSensorEntity(
                    entry=entry,
                    name=name,
                    controller=controller,
                    coordinator=coordinator,
                    description=entity_description,
                )
            )
        elif isinstance(
            entity_description, AtonStorageIntegrationSensorEntityDescription
        ):
            entities.append(
                AtonStorageIntegrationSensor(
                    integration_method="left",
                    name=entity_description.name,
                    round_digits=2,
                    # source_entity=f"sensor.{controller.serialNumber}_{entity_description.source_sensor}",
                    source_entity=entity_description.source_sensor,
                    unique_id=f"{controller.serialNumber}_{entity_description.key}",
                    unit_prefix="k",
                    unit_time="h",
                    entry=entry,
                    controller=controller,
                )
            )

    return entities


class AtonStorageSensorEntity(CoordinatorEntity, SensorEntity):
    """AtonStorage Sensor which receives its data via an DataUpdateCoordinator."""

    entity_description: AtonStorageSensorEntityDescription

    def __init__(
        self,
        entry: ConfigEntry,
        name: str,
        controller: AtonStorage,
        coordinator,
        description: AtonStorageSensorEntityDescription,
        # device_info,
    ):
        """Batched AtonStorage Sensor Entity constructor."""
        super().__init__(coordinator)

        self.controller = controller
        self.entity_description = description

        # self._attr_device_info = device_info
        self._entry = entry
        self._name = name
        self._attr_unique_id = f"{controller.serialNumber}_{description.key}"

        self._register_key = self.entity_description.key
        if "#" in self._register_key:
            self._register_key = self._register_key[0 : self._register_key.find("#")]

    @property
    def native_value(self):
        """Native sensor value."""

        if self.entity_description.value_calc_function:
            value = self.entity_description.value_calc_function(self.controller)
        else:
            value = self.controller.getRawData(self._register_key)

        if self.entity_description.value_conversion_function:
            value = self.entity_description.value_conversion_function(value)

        return value

    @property
    def device_info(self):
        """Return device information about AtonStorage Controller."""

        # v_model = controller.vbScheda | "Unkown"
        # v_fw = controller.fwScheda | "Unkown"
        # model = f"H.Store - ({ v_model })"
        # firmware = f" ({ v_fw })"

        return {
            "identifiers": {(DOMAIN, slugify(self._entry.unique_id))},
            "name": self._name,
            "manufacturer": "AtonStorage",
            "serial_number": self.controller.serialNumber,
            # "model": model,
            # "sw_version": firmware,
        }


class AtonStorageIntegrationSensor(IntegrationSensor):
    """Representation of an integration sensor."""

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
        self.controller = controller
        self._entry = entry
        self._name = name

    @property
    def device_info(self):
        """Return device information about AtonStorage Controller."""

        # v_model = controller.vbScheda | "Unkown"
        # v_fw = controller.fwScheda | "Unkown"
        # model = f"H.Store - ({ v_model })"
        # firmware = f" ({ v_fw })"

        return {
            "identifiers": {(DOMAIN, slugify(self._entry.unique_id))},
            "name": self._name,
            "manufacturer": "AtonStorage",
            "serial_number": self.controller.serialNumber,
            # "model": model,
            # "sw_version": firmware,
        }
