"""Write one field to the device and confirm it by reading it back."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import async_timeout
from bleak import BleakScanner
from bleak.exc import BleakError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection
from homeassistant.exceptions import HomeAssistantError
from bluetti_bt_lib import BluettiDevice, DeviceWriter, DeviceWriterConfig
from bluetti_bt_lib.fields import DeviceField
from bluetti_bt_lib.registers import ReadableRegisters

from .coordinator import PollingCoordinator
from .utils import mac_loggable

ATTEMPTS = 3
WRITE_TIMEOUT = 30
SETTLE_SECONDS = 2


async def async_write_field(
    coordinator: PollingCoordinator,
    bluetti_device: BluettiDevice,
    address: str,
    use_encryption: bool,
    lock: asyncio.Lock,
    field: DeviceField,
    value: Any,
    expected: Any,
    logger: logging.Logger,
) -> None:
    """Write value to field, read the register back and retry until it holds.

    Raises HomeAssistantError when the device does not report the expected
    value after ATTEMPTS writes, so the failure shows up in the UI.
    """
    if bluetti_device.build_write_command(field.name, value) is None:
        raise HomeAssistantError(f"Refused to write {value!r} to {field.name}")

    for attempt in range(1, ATTEMPTS + 1):
        try:
            # The unit takes one client, so a held read connection blocks this.
            await coordinator.reader.release()

            device = await BleakScanner.find_device_by_address(address, timeout=5)
            if device is None:
                logger.warning("Device %s not found", mac_loggable(address))
                continue

            client = await establish_connection(
                BleakClientWithServiceCache,
                device,
                device.name or "Unknown Device",
                max_attempts=10,
            )
            writer = DeviceWriter(
                client,
                bluetti_device,
                DeviceWriterConfig(use_encryption=use_encryption),
                lock=lock,
            )
            async with async_timeout.timeout(WRITE_TIMEOUT):
                await writer.write(field.name, value)

            # Let the unit apply the value before reading it back
            await asyncio.sleep(SETTLE_SECONDS)

            data = await coordinator.reader.read(
                only_registers=[ReadableRegisters(field.address, field.size)]
            )
            actual = None if data is None else data.get(field.name)
            if actual == expected:
                logger.info("Wrote %s = %s (attempt %d)", field.name, expected, attempt)
                await coordinator.async_request_refresh()
                return

            logger.warning(
                "Read back %s = %s after writing %s (attempt %d)",
                field.name,
                actual,
                expected,
                attempt,
            )
        except (TimeoutError, BleakError) as err:
            logger.warning("Write %s failed (attempt %d): %s", field.name, attempt, err)

    await coordinator.async_request_refresh()
    raise HomeAssistantError(
        f"Could not set {field.name} to {expected} after {ATTEMPTS} attempts"
    )
