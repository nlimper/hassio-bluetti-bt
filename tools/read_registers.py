"""Read-only register dump for a BLUETTI V2 device over BLE.

Sends only Modbus function 03 (read holding registers). Any other command
is refused before it reaches the device.

Usage:
    python tools/read_registers.py --mac AA:BB:CC:DD:EE:FF
"""

import argparse
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

from bluetti_bt_lib.base_devices import BaseDeviceV2
from bluetti_bt_lib.bluetooth.device_reader import DeviceReader, DeviceReaderConfig
from bluetti_bt_lib.registers import ReadableRegisters

# (start, count) per block, taken from the app's ModbusV2Dispatcher
BLOCKS = [
    (100, 120),  # live data
    (1100, 70),  # inverter base info
    (1200, 60),  # PV
    (1300, 40),  # grid, per phase W/V/A/VA from 1313
    (1400, 70),  # load, per phase W/V/A/VA from 1430
    (1500, 40),  # inverter output, per phase from 1509
    (2000, 100),  # base settings
    (2200, 110),  # advanced settings
    (3500, 10),  # total energy
    (3600, 20),  # energy this year
    (6000, 40),  # battery pack main info
    (12002, 20),  # IoT settings
    (12205, 10),  # IoT display settings
    (14000, 10),  # HMI info
]
CHUNK = 10


class ReadOnlyGuard(DeviceReader):
    """DeviceReader that refuses anything but a read and keeps raw responses."""

    raw: dict[int, str]

    async def _async_send_command(self, registers):
        cmd = bytes(registers)
        if len(cmd) < 2 or cmd[1] != 0x03 or not isinstance(registers, ReadableRegisters):
            raise RuntimeError(f"Refused non-read command: {cmd.hex()}")
        res = await super()._async_send_command(registers)
        self.raw[registers.starting_address] = bytes(res).hex()
        return res


async def main(mac: str, out_dir: Path):
    device = BaseDeviceV2()
    assert device.max_packs == 0, "pack selector would write a register"

    reader = ReadOnlyGuard(
        mac,
        device,
        asyncio.Future,
        DeviceReaderConfig(timeout=600, use_encryption=True),
    )
    reader.raw = {}

    registers = [
        ReadableRegisters(start + i, min(CHUNK, count - i))
        for start, count in BLOCKS
        for i in range(0, count, CHUNK)
    ]
    print(f"Reading {len(registers)} chunks ...")
    result = await reader.read(only_registers=registers, raw=True)
    await reader.release()

    if result is None:
        print("Read failed")
        return

    regs: dict[int, int] = {}
    errors: list[int] = []
    for start, body in result.items():
        full = bytes.fromhex(reader.raw.get(start, ""))
        if len(full) >= 2 and full[1] & 0x80:
            errors.append(start)
            continue
        for i in range(0, len(body) - 1, 2):
            regs[start + i // 2] = int.from_bytes(body[i : i + 2], "big")

    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"dump_{datetime.now():%Y%m%d_%H%M%S}.json"
    out.write_text(
        json.dumps(
            {
                "mac": mac,
                "time": datetime.now().isoformat(),
                "registers": {str(k): v for k, v in sorted(regs.items())},
                "raw": reader.raw,
                "exception_chunks": errors,
            },
            indent=1,
        )
    )
    print(f"{len(regs)} registers read, {len(errors)} chunks refused by device")
    print(f"Saved to {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mac", required=True)
    parser.add_argument("--out", default=str(Path(__file__).parent / "dumps"))
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.WARNING)
    asyncio.run(main(args.mac, Path(args.out)))
