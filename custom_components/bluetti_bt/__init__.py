"""Bluetti Bluetooth Integration"""

from __future__ import annotations
import asyncio
import re
import logging
from typing import List
from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.exceptions import ConfigEntryNotReady

from .utils import mac_loggable
from .const import (
    DATA_COORDINATOR,
    DATA_LOCK,
    DOMAIN,
    MANUFACTURER,
)
from .types import FullDeviceConfig
from .coordinator import PollingCoordinator

PLATFORMS: List[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.SELECT,
    Platform.NUMBER,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Bluetti Powerstation from a config entry."""

    config = FullDeviceConfig.from_dict(entry.data)

    if config is None:
        logging.getLogger(__name__).error(
            "Failed to parse config entry data for '%s'. "
            "This may happen when upgrading from v0.1.6 to v0.2.x "
            "due to missing 'use_encryption' field.",
            entry.title,
        )
        return False

    logger = logging.getLogger(
        f"{__name__}.{mac_loggable(config.address).replace(':', '_')}"
    )

    logger.debug("Init Bluetti BT Integration")

    if not bluetooth.async_address_present(hass, config.address):
        raise ConfigEntryNotReady("Bluetti device not present")

    # Create data structure
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(entry.entry_id, {})

    # Create lock
    lock = asyncio.Lock()

    # Create coordinator for polling
    logger.debug("Creating coordinator")
    coordinator = PollingCoordinator(
        hass,
        config,
        lock,
    )
    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id].setdefault(DATA_COORDINATOR, coordinator)
    hass.data[DOMAIN][entry.entry_id].setdefault(DATA_LOCK, lock)

    logger.debug("Creating entities")
    # Setup platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    logger.debug("Setup done")

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Apply changed options.

    The coordinator takes its polling interval at construction, so without a
    reload an options change only lands on the next restart.
    """
    await hass.config_entries.async_reload(entry.entry_id)


def device_info(entry: ConfigEntry):
    """Device info."""
    config = FullDeviceConfig.from_dict(entry.data)

    if config is None:
        return None

    return DeviceInfo(
        identifiers={(DOMAIN, config.address)},
        name=entry.title,
        manufacturer=MANUFACTURER,
        model=config.dev_type,
    )


def get_unique_id(name: str, sensor_type: str | None = None):
    """Generate an unique id."""
    res = re.sub("[^A-Za-z0-9]+", "_", name).lower()
    if sensor_type is not None:
        return f"{sensor_type}.{res}"
    return res
