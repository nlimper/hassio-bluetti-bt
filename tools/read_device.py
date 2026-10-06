"""Read-only: poll a device the way the integration does and print parsed values.

Usage:
    python tools/read_device.py --mac AA:BB:CC:DD:EE:FF --name "Elite 200 V2<serial>"
"""

import argparse
import asyncio

from bluetti_bt_lib import build_device, get_unit, FieldName
from bluetti_bt_lib.bluetooth.device_reader import DeviceReaderConfig

from read_registers import ReadOnlyGuard


async def main(mac: str, name: str):
    device = build_device(name)
    if device is None:
        print("Unknown device name")
        return
    reader = ReadOnlyGuard(
        mac, device, asyncio.Future, DeviceReaderConfig(timeout=120, use_encryption=True)
    )
    reader.raw = {}
    data = await reader.read()
    await reader.release()
    if not data:
        print("Read failed")
        return
    for field in device.fields:
        value = data.get(field.name, "-")
        unit = get_unit(FieldName(field.name)) or ""
        print(f"{field.address:5d} {field.name:32s} {value} {unit}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--mac", required=True)
    p.add_argument("--name", required=True)
    a = p.parse_args()
    asyncio.run(main(a.mac, a.name))
