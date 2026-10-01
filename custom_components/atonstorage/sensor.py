"""AtonStorage integration."""
import inspect
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util.dt import as_local

from .const import DOMAIN
from .controller import Controller as AtonStorage

_LOGGER = logging.getLogger(__name__)


def _plant_timestamp(value):
    """Parse a dd/mm/YYYY HH:MM:SS stamp, tolerating an empty or bad one."""
    if not value:
        return None
    try:
        return as_local(datetime.strptime(value, "%d/%m/%Y %H:%M:%S"))
    except (TypeError, ValueError):
        return None


@dataclass
class AtonStorageSensorEntityDescription(SensorEntityDescription):
    """Class to describe a AtonStorage sensor entity."""

    value_conversion_function: Callable[[Any], Any] = lambda val: val
    value_calc_function: Callable[[AtonStorage], Any] = None


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
        value_conversion_function=lambda value: min(100, float(value) if value else 0),
    ),
    AtonStorageSensorEntityDescription(
        key="vb",
        translation_key="vb",
        name="Battery voltage",
        icon="mdi:current-dc",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AtonStorageSensorEntityDescription(
        key="ib",
        translation_key="ib",
        name="Battery current",
        icon="mdi:current-dc",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
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
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AtonStorageSensorEntityDescription(
        key="string1I",
        translation_key="string1I",
        name="String1 current",
        icon="mdi:solar-panel-large",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # STRING2
    AtonStorageSensorEntityDescription(
        key="string2V",
        translation_key="string2V",
        name="String2 voltage",
        icon="mdi:solar-panel-large",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AtonStorageSensorEntityDescription(
        key="string2I",
        translation_key="string2I",
        name="String2 current",
        icon="mdi:solar-panel-large",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # UTILITIES
    AtonStorageSensorEntityDescription(
        key="utenzeV",
        translation_key="utenzeV",
        name="Utilities voltage",
        icon="mdi:current-ac",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AtonStorageSensorEntityDescription(
        key="utenzeI",
        translation_key="utenzeI",
        name="Utilities current",
        icon="mdi:current-ac",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # GRID
    AtonStorageSensorEntityDescription(
        key="gridV",
        translation_key="gridV",
        name="Grid voltage",
        icon="mdi:current-ac",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AtonStorageSensorEntityDescription(
        key="gridHz",
        translation_key="gridHz",
        name="Grid frequency",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
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
        key="tot_pReteOut",
        translation_key="tot_pReteOut",
        name="Daily sold energy",
        icon="mdi:transmission-tower-import",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    AtonStorageSensorEntityDescription(
        key="tot_pReteIn",
        translation_key="tot_pReteIn",
        name="Daily bought energy",
        icon="mdi:transmission-tower-export",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING
    ),
    AtonStorageSensorEntityDescription(
        key="ePannelli",
        translation_key="ePannelli",
        name="Daily solar energy",
        icon="mdi:solar-power-variant-outline",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_conversion_function=lambda value: float(value) / 1000,
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
        value_conversion_function=lambda value: float(value) / 1000,
        # last_reset=as_local(datetime.combine(date.today(), datetime.min.time())),
    ),
    # Daily counter, reset to 0 by the plant at midnight. TOTAL_INCREASING lets the
    # statistics engine detect that reset; TOTAL would need a last_reset attribute,
    # which this integration does not publish.
    AtonStorageSensorEntityDescription(
        key="tot_pBatteria",
        translation_key="tot_pBatteria",
        name="Battery charged energy",
        icon="mdi:battery-plus",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    # Daily counter, reset to 0 by the plant at midnight. TOTAL_INCREASING lets the
    # statistics engine detect that reset; TOTAL would need a last_reset attribute,
    # which this integration does not publish.
    AtonStorageSensorEntityDescription(
        key="tot_pBatteriaB",
        translation_key="tot_pBatteriaB",
        name="Battery discharged energy",
        icon="mdi:battery-minus",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    # CALCULATED VALUES #
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
        # icon="mdi:home-battery",
        icon="mdi:home-lightning-bolt",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_calc_function=lambda controller: controller.consumed_energy,
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
        # Float math on purpose: int() used to truncate both terms, which
        # reported a flat 100% for every day under 1 kWh of consumption.
        value_calc_function=lambda controller: (
            100.0
            if controller.consumed_energy <= 0
            else round(
                100 - (controller.bought_energy / controller.consumed_energy * 100),
                2,
            )
        ),
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
    # EV
    AtonStorageSensorEntityDescription(
        key="num_EV",
        translation_key="num_EV",
        name="EV num",
        # icon="mdi:solar-power-variant",
    ),
    AtonStorageSensorEntityDescription(
        key="SoC_EV",
        translation_key="SoC_EV",
        name="EV Battery level",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        # Limit battery_level to a maximum of 100 and convert it to an integer
        value_conversion_function=lambda value: min(100, float(value) if value else 0),
    ),
    # EV charge
    AtonStorageSensorEntityDescription(
        key="setp_EV",
        translation_key="setp_EV",
        name="EV setp",
        icon="mdi:car-electric",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AtonStorageSensorEntityDescription(
        key="potenza_EV",
        translation_key="potenza_EV",
        name="EV Charge",
        icon="mdi:car-electric",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AtonStorageSensorEntityDescription(
        key="kmh",
        translation_key="kmh",
        name="EV kmh",
        icon="mdi:car-electric",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # EV charged
    AtonStorageSensorEntityDescription(
        key="e_ciclo_EV",
        translation_key="e_ciclo_EV",
        name="EV Charged",
        icon="mdi:car-electric",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_conversion_function=lambda value: max(0, float(value)),
    ),
    AtonStorageSensorEntityDescription(
        key="km",
        translation_key="km",
        name="EV km",
        icon="mdi:car-electric",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AtonStorageSensorEntityDescription(
        key="perc_carica",
        translation_key="perc_carica",
        name="EV charged percentage",
        icon="mdi:car-electric",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        # Limit battery_level to a maximum of 100 and convert it to an integer
        value_conversion_function=lambda value: min(100, float(value) if value else 0),
    ),
    # ADDED IN 1.0.12, from fields the payload always carried but nothing read.
    # Three independent state of charge readings the plant reports side by side.
    AtonStorageSensorEntityDescription(
        key="socBms",
        translation_key="socBms",
        name="Battery level BMS",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_conversion_function=lambda value: min(100, float(value) if value else 0),
    ),
    AtonStorageSensorEntityDescription(
        key="socInv",
        translation_key="socInv",
        name="Battery level inverter",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_conversion_function=lambda value: min(100, float(value) if value else 0),
    ),
    AtonStorageSensorEntityDescription(
        key="socAh",
        translation_key="socAh",
        name="Battery level Ah",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_conversion_function=lambda value: min(100, float(value) if value else 0),
    ),
    # ALARMS
    AtonStorageSensorEntityDescription(
        key="active_alarms",
        translation_key="active_alarms",
        name="Active alarms",
        icon="mdi:alert-circle-outline",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_calc_function=lambda controller: controller.active_alarm_count,
    ),
    AtonStorageSensorEntityDescription(
        key="dataAllarme",
        translation_key="dataAllarme",
        name="Last alarm",
        icon="mdi:alert-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_conversion_function=_plant_timestamp,
    ),
    # DIAGNOSTICS
    AtonStorageSensorEntityDescription(
        key="timestampScheda",
        translation_key="timestampScheda",
        name="Board time",
        icon="mdi:clock-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_conversion_function=_plant_timestamp,
    ),
    AtonStorageSensorEntityDescription(
        key="fwSchedaExt",
        translation_key="fwSchedaExt",
        name="Extended firmware",
        icon="mdi:chip",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # No unit: the plant reports 60000 on a 4 kW system, so the scale is not
    # confirmed. Left as a bare number rather than mislabelling it as watts.
    AtonStorageSensorEntityDescription(
        key="exportLimit",
        translation_key="exportLimit",
        name="Export limit",
        icon="mdi:transmission-tower-off",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # PER PHASE POWER, zero on a single phase plant
    AtonStorageSensorEntityDescription(
        key="pL1",
        translation_key="pL1",
        name="Phase 1 power",
        icon="mdi:numeric-1-box-outline",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AtonStorageSensorEntityDescription(
        key="pL2",
        translation_key="pL2",
        name="Phase 2 power",
        icon="mdi:numeric-2-box-outline",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AtonStorageSensorEntityDescription(
        key="pL3",
        translation_key="pL3",
        name="Phase 3 power",
        icon="mdi:numeric-3-box-outline",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AtonStorageSensorEntityDescription(
        key="pReteL1",
        translation_key="pReteL1",
        name="Grid phase 1 power",
        icon="mdi:transmission-tower",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AtonStorageSensorEntityDescription(
        key="pReteL2",
        translation_key="pReteL2",
        name="Grid phase 2 power",
        icon="mdi:transmission-tower",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AtonStorageSensorEntityDescription(
        key="pReteL3",
        translation_key="pReteL3",
        name="Grid phase 3 power",
        icon="mdi:transmission-tower",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
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
            entities.append(
                AtonStorageSensorEntity(
                    entry=entry,
                    controller=controller,
                    coordinator=coordinator,
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
        self._attr_unique_id = (
            f"{controller.serial_number}_{self.entity_description.key}"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "AtonStorage " + username)},
            name=username,
            manufacturer="AtonStorage",
            sw_version=controller.fw_Scheda,
            serial_number=controller.serial_number,
        )

        self._register_key = self.entity_description.key

    @property
    def native_value(self):
        """Native sensor value."""

        if self.entity_description.value_calc_function:
            value = self.entity_description.value_calc_function(self.controller)
        else:
            value = self.controller.get_raw_data(self._register_key)
            # The payload simply lacks this key, e.g. the EV fields on a
            # plant without a wallbox. Report unknown instead of feeding
            # None to strptime() or float().
            if value is None:
                return None

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
        if self.entity_description.key == "active_alarms":
            return {"alarms": self.controller.active_alarms}
        if self.entity_description.key == "soc":
            attrSensor = {
                "raw data": self.controller.get_raw_data("soc"),
                "batteries number": self.controller.get_raw_data("numBatterie"),
            }
            return attrSensor
