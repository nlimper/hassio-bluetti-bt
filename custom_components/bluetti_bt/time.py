"""Bluetti BT times: start and end of each time slot."""

from __future__ import annotations
import asyncio
from dataclasses import replace
from datetime import time
import logging
from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from bluetti_bt_lib import build_device, BluettiDevice
from bluetti_bt_lib.fields import TimeSlot, TimeSlotField

from .types import FullDeviceConfig
from . import device_info as dev_info, get_unique_id
from .const import DATA_COORDINATOR, DATA_LOCK, DOMAIN
from .coordinator import PollingCoordinator
from .time_slots import async_write_time_slot, current_slot
from .utils import mac_loggable

START = "start"
END = "end"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Setup time entities."""

    config = FullDeviceConfig.from_dict(entry.data)
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    lock = hass.data[DOMAIN][entry.entry_id][DATA_LOCK]

    logger = logging.getLogger(
        f"{__name__}.{mac_loggable(config.address).replace(':', '_')}"
    )

    if config is None or not isinstance(coordinator, PollingCoordinator):
        logger.error("No coordinator found")
        return None

    device_info = dev_info(entry)
    bluetti_device = build_device(config.name)

    times_to_add = []
    for field in bluetti_device.get_time_slot_fields():
        for part in (START, END):
            times_to_add.append(
                BluettiTimeSlotTime(
                    bluetti_device,
                    config.address,
                    coordinator,
                    device_info,
                    field,
                    part,
                    lock,
                    config.use_encryption,
                    logger=logger,
                )
            )

    async_add_entities(times_to_add)


class BluettiTimeSlotTime(CoordinatorEntity, TimeEntity):
    """Start or end time of a time slot."""

    def __init__(
        self,
        bluetti_device: BluettiDevice,
        address: str,
        coordinator: PollingCoordinator,
        device_info: DeviceInfo,
        field: TimeSlotField,
        part: str,
        lock: asyncio.Lock,
        use_encryption: bool = False,
        logger: logging.Logger = logging.getLogger(),
    ):
        """Init entity."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._logger = logger
        self._bluetti_device = bluetti_device
        self._address = address
        self._use_encryption = use_encryption
        self._field = field
        self._part = part
        self._lock = lock

        self._attr_has_entity_name = True
        self._attr_device_info = device_info
        self._attr_translation_key = f"{field.name}_{part}"
        self._attr_unique_id = get_unique_id(
            f"{device_info.get('name')} {field.name}_{part}"
        )
        self._attr_available = False

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.coordinator.data
        slot = data.get(self._field.name) if isinstance(data, dict) else None
        if not isinstance(slot, TimeSlot):
            self._attr_available = False
            self.async_write_ha_state()
            return

        hhmm = slot.start if self._part == START else slot.end
        hours, minutes = (int(x) for x in hhmm.split(":"))
        self._attr_available = True
        self._attr_native_value = time(hours, minutes)
        self.async_write_ha_state()

    async def async_set_value(self, value: time) -> None:
        """Change the start or end, keep the mode and the other time."""
        slot = current_slot(self.coordinator, self._field)
        hhmm = value.strftime("%H:%M")
        new = replace(slot, start=hhmm) if self._part == START else replace(slot, end=hhmm)
        await async_write_time_slot(
            self.coordinator,
            self._bluetti_device,
            self._address,
            self._use_encryption,
            self._lock,
            self._field,
            new,
            self._logger,
        )
