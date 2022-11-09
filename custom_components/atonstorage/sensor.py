"""AtonStorage integration."""
import logging
from datetime import datetime

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
    POWER_WATT,
    TEMP_CELSIUS,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify
from homeassistant.util.dt import as_local

from .const import DOMAIN
from .controller import Controller as AtonStorage

_LOGGER = logging.getLogger(__name__)


INVERTER_SENSOR_DESCRIPTIONS = (
    SensorEntityDescription(
        key="data",
        name="Date",
        icon="mdi:calendar-range",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key="pSolare",
        name="Instant solar power",
        icon="mdi:solar-power-variant",
        native_unit_of_measurement=POWER_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="pUtenze",
        name="Instant user power",
        icon="mdi:home-lightning-bolt-outline",
        native_unit_of_measurement=POWER_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="pBatteria",
        name="Instant battery power",
        icon="mdi:home-battery",
        native_unit_of_measurement=POWER_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="pReteIn",
        name="Power grid input",
        icon="mdi:transmission-tower-import",
        native_unit_of_measurement=POWER_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="pReteOut",
        name="Power grid output",
        icon="mdi:transmission-tower-export",
        native_unit_of_measurement=POWER_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="pRete",
        name="Power grid",
        icon="mdi:transmission-tower",
        native_unit_of_measurement=POWER_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="soc",
        name="State of battery",
        icon="mdi:battery-heart-variant",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="string1V",
        name="String1 Voltage",
        icon="mdi:solar-panel-large",
        native_unit_of_measurement=ELECTRIC_POTENTIAL_VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="string1I",
        name="String1 Current",
        icon="mdi:solar-panel-large",
        native_unit_of_measurement=ELECTRIC_CURRENT_AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="string2V",
        name="String2 Voltage",
        icon="mdi:solar-panel-large",
        native_unit_of_measurement=ELECTRIC_POTENTIAL_VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="string2I",
        name="String2 Current",
        icon="mdi:solar-panel-large",
        native_unit_of_measurement=ELECTRIC_CURRENT_AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="utenzeV",
        name="Utilities Voltage",
        icon="mdi:flash-triangle-outline",
        native_unit_of_measurement=ELECTRIC_POTENTIAL_VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="utenzeI",
        name="Utilities Current",
        icon="mdi:current-dc",
        native_unit_of_measurement=ELECTRIC_CURRENT_AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="ahCaricati",
        name="Current charged",
        icon="mdi:battery-plus-variant",
        native_unit_of_measurement="AH",
        # device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="ahScaricati",
        name="Current discharged",
        icon="mdi:battery-minus-variant",
        native_unit_of_measurement="AH",
        # device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="pMaxVenduta",
        name="Max power sold",
        icon="mdi:transmission-tower-export",
        native_unit_of_measurement=POWER_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="pMaxPannelli",
        name="Panels max power",
        icon="mdi:solar-panel",
        native_unit_of_measurement=POWER_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="pMaxBatteria",
        name="Battery max pawer",
        icon="mdi:battery-charging-100",
        native_unit_of_measurement=POWER_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="pMaxComprata",
        name="Max power bought",
        icon="mdi:transmission-tower-import",
        native_unit_of_measurement=POWER_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="eVenduta",
        name="Energy sold",
        icon="mdi:solar-power",
        # native_unit_of_measurement=POWER_WATT,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="ePannelli",
        name="daily Solar energy",
        icon="mdi:solar-power-variant-outline",
        # native_unit_of_measurement=POWER_WATT,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="eBatteria",
        name="Battery energy",
        icon="mdi:battery-charging-high",
        # native_unit_of_measurement=POWER_WATT,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="eComprata",
        name="daily Energy bought",
        icon="mdi:transmission-tower-import",
        # native_unit_of_measurement=POWER_WATT,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="gridV",
        name="Grid Voltage",
        icon="mdi:power-plug-outline",
        native_unit_of_measurement=ELECTRIC_POTENTIAL_VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="gridHz",
        name="Grid Frequency",
        icon="mdi:sine-wave",
        native_unit_of_measurement=FREQUENCY_HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="pGrid",
        name="Instant Grid power",
        icon="mdi:transmission-tower",
        native_unit_of_measurement=POWER_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="temperatura",
        name="Inverter Temperature",
        icon="mdi:thermometer-low",
        native_unit_of_measurement=TEMP_CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="temperatura2",
        name="Temperature 2",
        icon="mdi:thermometer-low",
        native_unit_of_measurement=TEMP_CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="numBatterie",
        name="Batteries number",
        icon="mdi:battery",
        # device_class=SensorDeviceClass.NONE,
        # state_class=SensorStateClass.MEASUREMENT,
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
        entities.append(
            AtonStorageSensorEntity(
                entry, name, controller, coordinator, entity_description
            )
        )

    return entities


class AtonStorageSensorEntity(CoordinatorEntity, SensorEntity):
    """AtonStorage Sensor which receives its data via an DataUpdateCoordinator."""

    entity_description: SensorEntityDescription

    def __init__(
        self,
        entry: ConfigEntry,
        name: str,
        controller: AtonStorage,
        coordinator,
        description: SensorEntityDescription,
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
        value = self.controller.getRawData(self._register_key)
        # if self.entity_description.value_conversion_function:
        #    value = self.entity_description.value_conversion_function(value)
        if (
            "data" in self._register_key.lower()
            or "timestamp" in self._register_key.lower()
        ):  # TODO: implement value_conversion_function
            value = as_local(datetime.strptime(value, "%d/%m/%Y %H:%M:%S"))

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
