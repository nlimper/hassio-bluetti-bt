"""Write test on a harmless register: display timeout (2067).

Only register 2067 can be written, only with the values 4 (5 min) and 5 (never).
Steps: read, write the current value back, read, write 4, read, restore 5, read.
Aborts if the starting value is not 5.

Usage:
    python tools/write_test_display.py --mac AA:BB:CC:DD:EE:FF
"""

import argparse
import asyncio

from bleak import BleakClient, BleakScanner
from bluetti_bt_lib.base_devices import BaseDeviceV2
from bluetti_bt_lib.bluetooth.device_reader import DeviceReaderConfig
from bluetti_bt_lib.bluetooth.device_writer import DeviceWriter, DeviceWriterConfig
from bluetti_bt_lib.enums import DisplayMode
from bluetti_bt_lib.fields import FieldName, SelectField
from bluetti_bt_lib.registers import ReadableRegisters

from read_registers import ReadOnlyGuard

ADDRESS = 2067
ALLOWED = {DisplayMode.MIN5, DisplayMode.NEVER}


class DisplayOnly(BaseDeviceV2):
    def __init__(self):
        super().__init__([SelectField(FieldName.CTRL_DISPLAY_TIMEOUT, ADDRESS, DisplayMode)])

    def build_write_command(self, name, value):
        if DisplayMode[value] not in ALLOWED:
            raise RuntimeError(f"Refused value {value}")
        cmd = super().build_write_command(name, value)
        if cmd is None or cmd.address != ADDRESS:
            raise RuntimeError(f"Refused write {cmd}")
        return cmd


async def read_value(mac: str) -> int | None:
    reader = ReadOnlyGuard(
        mac, BaseDeviceV2(), asyncio.Future,
        DeviceReaderConfig(timeout=60, use_encryption=True),
    )
    reader.raw = {}
    res = await reader.read(only_registers=[ReadableRegisters(ADDRESS, 1)], raw=True)
    await reader.release()
    if not res or len(res.get(ADDRESS, b"")) != 2:
        return None
    return int.from_bytes(res[ADDRESS], "big")


async def write_value(mac: str, mode: DisplayMode):
    ble = await BleakScanner.find_device_by_address(mac, timeout=10)
    if ble is None:
        raise RuntimeError("Device not found")
    writer = DeviceWriter(
        BleakClient(ble), DisplayOnly(), DeviceWriterConfig(timeout=30, use_encryption=True)
    )
    await writer.write(FieldName.CTRL_DISPLAY_TIMEOUT.value, mode.name)


async def main(mac: str):
    start = await read_value(mac)
    print(f"start: {start}")
    if start != DisplayMode.NEVER.value:
        print("Starting value is not 5, aborting without writing")
        return
    try:
        for mode in (DisplayMode.NEVER, DisplayMode.MIN5):
            await write_value(mac, mode)
            await asyncio.sleep(2)
            print(f"wrote {mode.value}, read back: {await read_value(mac)}")
    finally:
        await write_value(mac, DisplayMode.NEVER)
        await asyncio.sleep(2)
        print(f"restored 5, read back: {await read_value(mac)}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--mac", required=True)
    asyncio.run(main(p.parse_args().mac))
