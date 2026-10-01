"""Regression coverage for AtonStorageIntegrationSensor on HA 2026.8+.

home-assistant/core PR #177596 ("Do not set a device on YAML integration
entities", merged 2026-07-30, shipped in HA 2026.8.0 on 2026-08-05) removed
the ``hass`` parameter from
``homeassistant.components.integration.sensor.IntegrationSensor.__init__``.
Because ``IntegrationSensor`` is treated as internal API by Home Assistant
core, this was not listed on the official breaking-changes page.

``AtonStorageIntegrationSensor`` (custom_components/atonstorage/sensor.py)
already went through this once: HA 2025.8 made ``hass`` a *required*
constructor argument, so the component was updated (see the "Home Assistant
2025.8+: IntegrationSensor requires hass" comments) to always forward
``hass`` positionally to ``IntegrationSensor.__init__``. HA 2026.8 reverses
that -- ``hass`` is removed entirely and every remaining parameter is
keyword-only -- so the same code now raises::

    TypeError: IntegrationSensor.__init__() takes 1 positional argument but
    2 positional arguments (and 8 keyword-only arguments) were given

at entity-creation time (see issue #57, closed by the reporter without a
fix landing).

The first test below constructs ``AtonStorageIntegrationSensor`` for real,
against whatever ``IntegrationSensor`` is actually installed (HA 2026.8.0 in
this environment), using a real ``homeassistant.core.HomeAssistant``
instance with device/entity registries loaded -- not a bare mock -- so it
exercises the exact call path used by ``_create_entities()`` in
``sensor.py``. Run against the unfixed source this test reproduces the
TypeError above; it only passes once the constructor stops forwarding
``hass`` to a parent that no longer accepts it.

The second and third tests pin the cross-version contract with a monkeypatch
stand-in for the parent class's ``__init__``, so the fix is verified against
both the pre-2026.8 (hass required) and 2026.8+ (hass rejected) shapes
regardless of which homeassistant version happens to be installed.
"""

from __future__ import annotations

from typing import Any

import pytest
from homeassistant.components.integration.sensor import IntegrationSensor
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.atonstorage.sensor import AtonStorageIntegrationSensor


class _FakeController:
    """Minimal stand-in for controller.Controller.

    Only the two attributes AtonStorageIntegrationSensor.__init__ actually
    reads (serial_number, fw_Scheda) are provided; everything else about the
    real Controller (HTTP client, polling) is irrelevant to construction.
    """

    serial_number = "SN123456"
    fw_Scheda = "1.2.3"


@pytest.fixture
async def real_hass(tmp_path) -> HomeAssistant:
    """A real HomeAssistant instance with registries loaded, not a mock."""
    hass = HomeAssistant(str(tmp_path))
    hass.data[dr.DATA_REGISTRY] = dr.DeviceRegistry(hass)
    await dr.async_load(hass, load_empty=True)
    await er.async_load(hass, load_empty=True)
    return hass


async def test_integration_sensor_constructs_against_real_ha(real_hass) -> None:
    """Real construction path: real hass + real registries + real IntegrationSensor.

    This is the exact call made by _create_entities() in sensor.py. Against
    unfixed code, this raises TypeError on HA 2026.8+.
    """
    sensor = AtonStorageIntegrationSensor(
        real_hass,
        integration_method="left",
        name="Test User Instant battery power",
        round_digits=2,
        source_entity="sensor.test_user_battery_power",
        unique_id="SN123456_battery_energy",
        unit_prefix="k",
        unit_time="h",
        entry={"dummy": "entry"},
        controller=_FakeController(),
        description=object(),
        username="Test User",
    )

    assert sensor.unique_id == "SN123456_battery_energy"
    assert sensor.name == "Test User Instant battery power"


def test_hass_still_forwarded_when_parent_accepts_it(monkeypatch) -> None:
    """Pre-2026.8 contract: hass must still be forwarded when the installed
    IntegrationSensor.__init__ accepts it (simulated via monkeypatch so this
    doesn't depend on which homeassistant version is actually installed)."""
    received: dict[str, Any] = {}

    def fake_pre_2026_8_init(
        self,
        hass,
        *,
        integration_method,
        name,
        round_digits,
        source_entity,
        unique_id,
        unit_prefix,
        unit_time,
        max_sub_interval,
    ) -> None:
        received["hass"] = hass
        self._attr_unique_id = unique_id
        self._attr_name = name

    monkeypatch.setattr(IntegrationSensor, "__init__", fake_pre_2026_8_init)

    fake_hass = object()
    AtonStorageIntegrationSensor(
        fake_hass,
        integration_method="left",
        name="n",
        round_digits=2,
        source_entity="sensor.x",
        unique_id="u",
        unit_prefix="k",
        unit_time="h",
        entry={"dummy": "entry"},
        controller=_FakeController(),
        description=object(),
        username="Test User",
    )

    assert received["hass"] is fake_hass


def test_hass_omitted_when_parent_rejects_it(monkeypatch) -> None:
    """2026.8+ contract: hass must NOT be forwarded when the installed
    IntegrationSensor.__init__ no longer accepts it (simulated via
    monkeypatch, mirroring the real 2026.8.0 signature)."""
    received: dict[str, Any] = {}

    def fake_2026_8_init(
        self,
        *,
        integration_method,
        name,
        round_digits,
        source_entity,
        unique_id,
        unit_prefix,
        unit_time,
        max_sub_interval,
        device=None,
    ) -> None:
        received["called"] = True
        self._attr_unique_id = unique_id
        self._attr_name = name

    monkeypatch.setattr(IntegrationSensor, "__init__", fake_2026_8_init)

    AtonStorageIntegrationSensor(
        object(),
        integration_method="left",
        name="n",
        round_digits=2,
        source_entity="sensor.x",
        unique_id="u",
        unit_prefix="k",
        unit_time="h",
        entry={"dummy": "entry"},
        controller=_FakeController(),
        description=object(),
        username="Test User",
    )

    assert received.get("called") is True
    assert "hass" not in received
