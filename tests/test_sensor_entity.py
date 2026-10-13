"""Unit tests for entity value resolution and controller helpers.

No network access: the Controller is created without ``__init__`` (so no httpx
client is built) and fed with canned payloads.
"""

from __future__ import annotations

from datetime import datetime

from custom_components.atonstorage.controller import Controller
from custom_components.atonstorage.sensor import (
    INVERTER_SENSOR_DESCRIPTIONS,
    AtonStorageSensorEntity,
    _plant_timestamp,
)


def _make_controller(monitor_data, energy_data=None):
    """A Controller without __init__: no hass, no httpx client."""
    controller = Controller.__new__(Controller)
    controller.monitor_data = monitor_data
    controller.energy_data = energy_data
    controller._alarm_descriptions = []
    controller._alarm_descriptions_tried = True
    return controller


def _description(name):
    for description in INVERTER_SENSOR_DESCRIPTIONS:
        if description.name == name:
            return description
    raise KeyError(name)


def _make_entity(description, controller):
    return AtonStorageSensorEntity(
        entry={"entry_id": "test"},
        controller=controller,
        coordinator=object(),
        description=description,
        username="Test User",
    )


def _base_monitor(**overrides):
    data = {
        "serialNumber": "SN123456",
        "fwScheda": "1.2.3",
        "status": "0",
    }
    data.update(overrides)
    return data


def test_missing_payload_key_returns_none():
    """A plant without a wallbox lacks the EV keys: unknown, not a crash."""
    controller = _make_controller(_base_monitor())
    entity = _make_entity(_description("EV num"), controller)
    assert entity.native_value is None


def test_soc_capped_at_100():
    controller = _make_controller(_base_monitor(soc="105.5"))
    entity = _make_entity(_description("Battery level"), controller)
    assert entity.native_value == 100.0

    controller = _make_controller(_base_monitor(soc=""))
    entity = _make_entity(_description("Battery level"), controller)
    assert entity.native_value == 0


def test_grid_power_split():
    controller = _make_controller(_base_monitor(pRete="-500"))
    assert (
        _make_entity(_description("Instant grid power input"), controller).native_value
        == 500
    )
    assert (
        _make_entity(_description("Instant grid power output"), controller).native_value
        == 0
    )

    controller = _make_controller(_base_monitor(pRete="300"))
    assert (
        _make_entity(_description("Instant grid power input"), controller).native_value
        == 0
    )
    assert (
        _make_entity(_description("Instant grid power output"), controller).native_value
        == 300
    )


def test_calc_function_wins_over_raw_key():
    """Daily consumed energy comes from the controller, not the payload."""
    controller = _make_controller(_base_monitor(), energy_data={"tot_pUtenze": "9.99"})
    entity = _make_entity(_description("Daily consumed energy"), controller)
    assert entity.native_value == 9.99


def test_timestamp_conversion():
    controller = _make_controller(_base_monitor(data="13/10/2026 12:00:00"))
    entity = _make_entity(_description("Last update"), controller)
    assert isinstance(entity.native_value, datetime)
    assert (
        entity.native_value.year,
        entity.native_value.month,
        entity.native_value.day,
    ) == (
        2026,
        10,
        13,
    )

    assert _plant_timestamp("") is None
    assert _plant_timestamp("garbage") is None


def test_status_bitfield():
    controller = _make_controller(_base_monitor(status="3"))
    assert controller.grid_to_house is True
    assert controller.solar_to_battery is True
    assert controller.solar_to_grid is False
    assert controller.battery_to_grid is False


def test_active_alarms_mapped_positionally():
    controller = _make_controller(_base_monitor(allarmi=["0", "32", "0"]))
    controller._alarm_descriptions = ["alarm A", "alarm B", "alarm C"]
    assert controller.active_alarms == ["alarm B"]
    assert controller.active_alarm_count == 1


def test_get_raw_data_falls_back_to_energy_payload():
    controller = _make_controller(_base_monitor(), energy_data={"tot_pReteIn": "1.5"})
    assert controller.get_raw_data("tot_pReteIn") == "1.5"
    assert controller.get_raw_data("no_such_key") is None
