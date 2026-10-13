"""Small, independent decoder for the legacy AirPods BLE proximity frame.

Input is Bleak manufacturer_data[0x004C], WITHOUT the company-id bytes.
This is a community-described format, not an Apple-supported API.
"""
from dataclasses import dataclass

APPLE_COMPANY_ID = 0x004C
MODELS = {
    0x0220: "AirPods 1", 0x0F20: "AirPods 2", 0x1320: "AirPods 3",
    0x1920: "AirPods 4", 0x1B20: "AirPods 4 ANC", 0x0E20: "AirPods Pro",
    0x1420: "AirPods Pro 2", 0x2420: "AirPods Pro 2 USB-C",
    0x2720: "AirPods Pro 3",
}


@dataclass(frozen=True)
class BatteryReading:
    model: str
    left: int | None
    right: int | None
    case: int | None


def _percent(nibble: int) -> int | None:
    # 0xF means unavailable; reserved 0xB..0xE are not fabricated as 100%.
    return nibble * 10 if 0 <= nibble <= 10 else None


def decode_airpods(payload: bytes) -> BatteryReading | None:
    """Find a complete type-07, length-25 legacy frame in Apple's TLV data.

    Only recognized in-ear model ids are decoded. Invalid, truncated,
    different-version and unknown-model frames are ignored conservatively.
    """
    offset = 0
    while offset + 2 <= len(payload):
        kind, length = payload[offset:offset + 2]
        end = offset + 2 + length
        if end > len(payload):
            return None
        frame = payload[offset:end]
        if kind == 0x07 and length == 25 and frame[2] == 0x01:
            model = MODELS.get(int.from_bytes(frame[3:5], "big"))
            if model is not None:
                high, low = frame[6] >> 4, frame[6] & 0x0F
                # The primary-pod flag changes the advertised nibble order.
                left, right = (low, high) if frame[5] & 0x20 else (high, low)
                return BatteryReading(model, _percent(left), _percent(right),
                                      _percent(frame[7] & 0x0F))
        offset = end
    return None


@dataclass(frozen=True)
class Observation:
    address: str
    name: str
    rssi: int
    seen_at: float  # time.monotonic(), never wall-clock time
    battery: BatteryReading

    def fresh(self, now: float, ttl: float = 30.0) -> bool:
        return 0 <= now - self.seen_at < ttl


class DeviceStore:
    """UI-owned cache. Do not merge devices just because models match."""
    def __init__(self) -> None:
        self.devices: dict[str, Observation] = {}

    def put(self, observation: Observation) -> None:
        previous = self.devices.get(observation.address)
        if previous is None or observation.seen_at >= previous.seen_at:
            self.devices[observation.address] = observation
        if len(self.devices) > 64:
            oldest = min(self.devices, key=lambda key: self.devices[key].seen_at)
            del self.devices[oldest]


def demo_payload(left: int = 8, right: int = 7, case: int = 6) -> bytes:
    """Synthetic legacy frame; demo never reads real Bluetooth hardware."""
    return bytes([0x07, 25, 1, 0x0E, 0x20, 0, (left << 4) | right, case,
                  0, 0, 0]) + bytes(16)
