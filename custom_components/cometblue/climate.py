"""Comet Blue climate integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    PRESET_AWAY,
    PRESET_COMFORT,
    PRESET_ECO,
    PRESET_NONE,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, PRECISION_HALVES, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import CometBlueBluetoothEntity, CometBlueDataUpdateCoordinator

LOGGER = logging.getLogger(__name__)

MIN_TEMP = 8
MAX_TEMP = 28


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the client entities."""

    coordinator: CometBlueDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([CometBlueClimateEntity(coordinator)])


class CometBlueClimateEntity(CometBlueBluetoothEntity, ClimateEntity):
    """A Comet Blue Climate climate entity."""

    _attr_min_temp = MIN_TEMP
    _attr_max_temp = MAX_TEMP
    _attr_target_temperature_step = PRECISION_HALVES
    _attr_name = None

    def __init__(self, coordinator: CometBlueDataUpdateCoordinator) -> None:
        """Initialize CometBlueClimateEntity."""

        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}-climate"
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_hvac_modes = [HVACMode.AUTO]
        self._attr_hvac_mode = HVACMode.AUTO
        self._attr_supported_features: ClimateEntityFeature = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
            | ClimateEntityFeature.PRESET_MODE
        )
        self._attr_preset_modes = [
            PRESET_NONE,
            PRESET_ECO,
            PRESET_AWAY,
            PRESET_COMFORT,
        ]

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self.coordinator.data["currentTemp"]

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature currently set to be reached."""
        return self.coordinator.data["manualTemp"]

    @property
    def target_temperature_high(self) -> float | None:
        """Return the upper bound target temperature."""
        return self.coordinator.data["targetTempHigh"]

    @property
    def target_temperature_low(self) -> float | None:
        """Return the lower bound target temperature."""
        return self.coordinator.data["targetTempLow"]

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode, e.g., home, away, temp.

        Requires ClimateEntityFeature.PRESET_MODE.
        """
        if self.target_temperature == self.target_temperature_low:
            return PRESET_ECO
        if self.target_temperature == self.target_temperature_high:
            return PRESET_COMFORT
        # AWAY MODE NOT SUPPORTED YET
        return PRESET_NONE

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperatures."""

        await self.coordinator.send_command(
            "set_temperature_async",
            {
                "values": {
                    # manual temperature always needs to be set, otherwise TRV will turn OFF
                    "manualTemp": kwargs.get(ATTR_TEMPERATURE)
                    or self.target_temperature,
                    "targetTempLow": kwargs.get(ATTR_TARGET_TEMP_LOW),
                    "targetTempHigh": kwargs.get(ATTR_TARGET_TEMP_HIGH),
                }
            },
            self.entity_id,
        )
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new target preset mode."""

        if self.preset_modes and preset_mode not in self.preset_modes:
            raise ValueError(f"Unsupported preset_mode '{preset_mode}'")
        if preset_mode in [PRESET_NONE, PRESET_AWAY]:
            raise ValueError(f"Setting preset '{preset_mode}' is not supported.")
        if preset_mode == PRESET_ECO:
            await self.async_set_temperature(temperature=self.target_temperature_low)
        elif preset_mode == PRESET_COMFORT:
            await self.async_set_temperature(temperature=self.target_temperature_high)
