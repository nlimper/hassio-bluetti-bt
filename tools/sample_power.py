"""Read-only: sample the power registers a few times, next to an optional HA sensor.

Usage:
    python tools/sample_power.py --mac AA:BB:CC:DD:EE:FF [--samples 8] [--ha-sensor sensor.x]
HA access uses HA_URL and HA_TOKEN from the environment.
"""

import argparse
import asyncio
import json
import os
import urllib.request

from bluetti_bt_lib.base_devices import BaseDeviceV2
from bluetti_bt_lib.bluetooth.device_reader import DeviceReaderConfig
from bluetti_bt_lib.registers import ReadableRegisters

from read_registers import ReadOnlyGuard

READS = [(140, 8), (1312, 5), (1429, 5), (1508, 5)]


def ha_state(entity: str) -> str:
    url, token = os.environ.get("HA_URL"), os.environ.get("HA_TOKEN")
    if not (url and token and entity):
        return "-"
    req = urllib.request.Request(
        f"{url}/api/states/{entity}", headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.load(resp)["state"]


def s16(v: int) -> int:
    return v - 65536 if v >= 32768 else v


async def main(mac: str, samples: int, interval: float, ha_sensor: str):
    reader = ReadOnlyGuard(
        mac,
        BaseDeviceV2(),
        asyncio.Future,
        DeviceReaderConfig(timeout=120, use_encryption=True, keep_alive_seconds=60),
    )
    reader.raw = {}
    regs_to_read = [ReadableRegisters(a, n) for a, n in READS]
    print("AC-uit: 142(app) 1430(W) V*A | AC-in: 146(app) 1313(W) V*A | omvormer 1510 | HA")
    for _ in range(samples):
        res = await reader.read(only_registers=regs_to_read, raw=True)
        if not res:
            print("read failed")
        else:
            r = {}
            for start, body in res.items():
                for i in range(0, len(body) - 1, 2):
                    r[start + i // 2] = int.from_bytes(body[i : i + 2], "big")
            va_out = r[1431] / 10 * r[1432] / 10
            va_in = r[1314] / 10 * abs(s16(r[1315])) / 10
            print(
                f"AC-uit: {r[142]:4d} {r[1430]:4d} {va_out:6.0f} | "
                f"AC-in: {r[146]:4d} {s16(r[1313]):4d} {va_in:6.0f} | "
                f"{r[1510]:4d} | {ha_state(ha_sensor)}"
            )
        await asyncio.sleep(interval)
    await reader.release()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--mac", required=True)
    p.add_argument("--samples", type=int, default=8)
    p.add_argument("--interval", type=float, default=5)
    p.add_argument("--ha-sensor", default="")
    a = p.parse_args()
    asyncio.run(main(a.mac, a.samples, a.interval, a.ha_sensor))
