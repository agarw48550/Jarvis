from __future__ import annotations
from typing import Dict, Any
import tinytuya


class SmartLifeController:
    def __init__(self, devices: Dict[str, Dict[str, str]]):
        # devices: { friendly_name: {id, local_key, ip} }
        self.devices = devices

    def _dev(self, name: str) -> tinytuya.OutletDevice:
        meta = self.devices[name]
        d = tinytuya.OutletDevice(meta["id"], meta["ip"], meta["local_key"])  # type: ignore[arg-type]
        d.set_version(3.3)
        return d

    def turn_on(self, name: str) -> str:
        d = self._dev(name)
        d.turn_on()
        return f"Turned on {name}"

    def turn_off(self, name: str) -> str:
        d = self._dev(name)
        d.turn_off()
        return f"Turned off {name}"

    def set_brightness(self, name: str, percent: int) -> str:
        d = self._dev(name)
        # DP codes vary; common brightness dp is 22 or 3
        # Here we try common dp=22
        d.set_value(22, int(max(0, min(100, percent))))
        return f"Set brightness of {name} to {percent}%"
