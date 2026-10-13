"""Bluetooth runs on one asyncio thread; Tk receives bounded messages."""
import asyncio
import queue
import sys
import threading
import time
from dataclasses import dataclass
from typing import Callable

from airpods import APPLE_COMPANY_ID, Observation, decode_airpods, demo_payload


@dataclass(frozen=True)
class Message:
    kind: str
    value: object


class ScanWorker:
    def __init__(self, demo: bool = False, scanner_factory: Callable | None = None):
        self.demo = demo
        self.scanner_factory = scanner_factory
        self.messages: queue.Queue[Message] = queue.Queue(maxsize=128)
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self._last_emit: dict[str, float] = {}

    @property
    def running(self) -> bool:
        return self.thread is not None and self.thread.is_alive()

    def send(self, kind: str, value: object) -> None:
        message = Message(kind, value)
        try:
            self.messages.put_nowait(message)
        except queue.Full:
            try:
                self.messages.get_nowait()
            except queue.Empty:
                pass
            try:
                self.messages.put_nowait(message)
            except queue.Full:
                pass

    def start(self) -> None:
        if self.running:
            return
        self.stop_event.clear()
        self._last_emit.clear()
        self.thread = threading.Thread(target=self._thread_main, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()

    def _thread_main(self) -> None:
        try:
            asyncio.run(self._run())
        except Exception as exc:
            self.send("error", f"{type(exc).__name__}: {exc}")
        finally:
            self.send("stopped", None)

    def _received(self, device, advertisement) -> None:
        payload = advertisement.manufacturer_data.get(APPLE_COMPANY_ID)
        if payload is None:
            return
        reading = decode_airpods(payload)
        if reading is None:
            return
        now = time.monotonic()
        address = str(device.address)
        # Prevent advertising bursts from monopolizing the UI queue.
        if now - self._last_emit.get(address, float("-inf")) < 0.5:
            return
        self._last_emit[address] = now
        if len(self._last_emit) > 128:
            self._last_emit = {key: value for key, value in self._last_emit.items()
                               if now - value < 30}
        self.send("observation", Observation(
            address, advertisement.local_name or device.name or reading.model,
            advertisement.rssi, now, reading))

    async def _run(self) -> None:
        if self.demo:
            self.send("status", "MODE DEMO — data simulasi, Bluetooth tidak dipindai")
            step = 0
            while not self.stop_event.is_set():
                reading = decode_airpods(demo_payload(8 - (step % 4), 7, 6))
                self.send("observation", Observation(
                    "DEMO-DEVICE", "AirPods simulasi", -42, time.monotonic(), reading))
                step += 1
                for _ in range(5):
                    if self.stop_event.is_set():
                        break
                    await asyncio.sleep(0.2)
            return
        factory = self.scanner_factory
        if factory is None:
            if sys.platform != "win32":
                raise RuntimeError("Mode perangkat asli ditujukan untuk Windows. Gunakan --demo.")
            try:
                from bleak import BleakScanner
            except ImportError as exc:
                raise RuntimeError("Instal dependensi: python -m pip install -r requirements.txt") from exc
            factory = BleakScanner
        # A dedicated worker avoids mixing Tk's loop with WinRT's async work.
        async with factory(detection_callback=self._received, scanning_mode="passive"):
            self.send("status", "Memindai AirPods di sekitar... buka casing dekat laptop")
            while not self.stop_event.is_set():
                await asyncio.sleep(0.2)
