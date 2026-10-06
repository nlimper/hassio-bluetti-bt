"""Shared logic for writing time slots (select, time entities and service)."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import replace

from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from bluetti_bt_lib import BluettiDevice
from bluetti_bt_lib.enums import TimeSlotMode
from bluetti_bt_lib.fields import TimeSlot, TimeSlotField

from .coordinator import PollingCoordinator
from .write import async_write_field


def _minutes(hhmm: str) -> int:
    h, m = (int(x) for x in hhmm.split(":"))
    return h * 60 + m


def current_slot(coordinator: PollingCoordinator, field: TimeSlotField) -> TimeSlot:
    """The slot as last read from the device."""
    data = coordinator.data if isinstance(coordinator.data, dict) else {}
    slot = data.get(field.name)
    if not isinstance(slot, TimeSlot):
        raise HomeAssistantError(f"{field.name} has not been read from the device yet")
    return slot


def _check_overlap(
    coordinator: PollingCoordinator,
    bluetti_device: BluettiDevice,
    field: TimeSlotField,
    slot: TimeSlot,
) -> None:
    """Refuse an active slot that overlaps another active slot."""
    if slot.mode == TimeSlotMode.OFF:
        return
    start, end = _minutes(slot.start), _minutes(slot.end)
    data = coordinator.data if isinstance(coordinator.data, dict) else {}
    for other_field in bluetti_device.get_time_slot_fields():
        if other_field.name == field.name:
            continue
        other = data.get(other_field.name)
        if not isinstance(other, TimeSlot) or other.mode == TimeSlotMode.OFF:
            continue
        if start < _minutes(other.end) and _minutes(other.start) < end:
            raise ServiceValidationError(
                f"{slot.start}-{slot.end} overlaps {other_field.name} "
                f"({other.start}-{other.end})"
            )


async def async_write_time_slot(
    coordinator: PollingCoordinator,
    bluetti_device: BluettiDevice,
    address: str,
    use_encryption: bool,
    lock: asyncio.Lock,
    field: TimeSlotField,
    slot: TimeSlot,
    logger: logging.Logger,
) -> None:
    """Validate a slot and write it (mode, start and end in one command)."""
    if not field.allowed_write_type(slot):
        raise ServiceValidationError(
            f"Invalid time slot {slot.mode.name.lower()} {slot.start}-{slot.end}: "
            "an active slot needs a start before its end"
        )
    _check_overlap(coordinator, bluetti_device, field, slot)

    # The device reports a slot with 00:00-00:00 as off
    expected = slot
    if slot.start == slot.end == "00:00":
        expected = replace(slot, mode=TimeSlotMode.OFF)

    await async_write_field(
        coordinator,
        bluetti_device,
        address,
        use_encryption,
        lock,
        field,
        slot,
        expected,
        logger,
    )
