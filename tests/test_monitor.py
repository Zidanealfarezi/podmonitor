import asyncio
import queue
import threading
import time
import unittest
from types import SimpleNamespace

from airpods import BatteryReading, DeviceStore, Observation, decode_airpods, demo_payload
from scanner import ScanWorker
from diagnose import collect, describe_advertisement


class ProtocolTests(unittest.TestCase):
    def test_known_frame_and_case_low_nibble(self):
        payload = bytearray(demo_payload())
        payload[7] = 0xB6  # upper nibble is flags, not the case percentage
        self.assertEqual(decode_airpods(bytes(payload)),
                         BatteryReading("AirPods Pro", 80, 70, 60))

    def test_primary_pod_switches_channel_order(self):
        payload = bytearray(demo_payload())
        payload[5] = 0x20
        reading = decode_airpods(bytes(payload))
        self.assertEqual((reading.left, reading.right), (70, 80))

    def test_full_empty_unknown_and_reserved(self):
        self.assertEqual(decode_airpods(demo_payload(10, 0, 15)),
                         BatteryReading("AirPods Pro", 100, 0, None))
        for value in range(11, 16):
            reading = decode_airpods(demo_payload(value, value, value))
            self.assertEqual((reading.left, reading.right, reading.case), (None, None, None))

    def test_every_truncated_prefix_is_rejected(self):
        payload = demo_payload()
        for length in range(len(payload)):
            with self.subTest(length=length):
                self.assertIsNone(decode_airpods(payload[:length]))

    def test_ignores_other_tlv_and_finds_valid_frame(self):
        payload = bytes([0x10, 2, 0, 0]) + demo_payload()
        self.assertEqual(decode_airpods(payload).left, 80)

    def test_does_not_resynchronize_inside_invalid_tlv(self):
        self.assertIsNone(decode_airpods(bytes([0x10, 255]) + demo_payload()))

    def test_unknown_model_and_variant_are_not_guessed(self):
        for index, value in ((0, 0x10), (1, 24), (2, 2), (3, 0xFF)):
            payload = bytearray(demo_payload())
            payload[index] = value
            self.assertIsNone(decode_airpods(bytes(payload)))

    def test_unavailable_case_does_not_reuse_previous_case(self):
        store = DeviceStore()
        store.put(Observation("A", "AirPods", -40, 1, decode_airpods(demo_payload())))
        store.put(Observation("A", "AirPods", -40, 2, decode_airpods(demo_payload(case=15))))
        self.assertIsNone(store.devices["A"].battery.case)

    def test_ttl_boundary_and_clock(self):
        observation = Observation("A", "AirPods", -40, 100, decode_airpods(demo_payload()))
        self.assertTrue(observation.fresh(129.99))
        self.assertFalse(observation.fresh(130))
        self.assertFalse(observation.fresh(99))

    def test_distinct_addresses_and_late_packets(self):
        store = DeviceStore()
        battery = decode_airpods(demo_payload())
        store.put(Observation("A", "same name", -40, 2, battery))
        store.put(Observation("B", "same name", -50, 2, battery))
        store.put(Observation("A", "old packet", -60, 1, battery))
        self.assertEqual(len(store.devices), 2)
        self.assertEqual(store.devices["A"].name, "same name")

    def test_cache_is_bounded(self):
        store = DeviceStore()
        battery = decode_airpods(demo_payload())
        for index in range(100):
            store.put(Observation(str(index), "pods", -40, index, battery))
        self.assertEqual(len(store.devices), 64)
        self.assertNotIn("0", store.devices)


class DiagnosticTests(unittest.TestCase):
    def test_exports_header_without_encrypted_tail(self):
        payload = demo_payload()[:11] + bytes([0xAA]) * 16
        device = SimpleNamespace(address="A", name="pods")
        advertisement = SimpleNamespace(local_name=None, rssi=-45,
                                        manufacturer_data={0x004C: payload})
        record = describe_advertisement(device, advertisement)
        self.assertEqual(record["manufacturers"]["0x004C"]["length"], 27)
        self.assertEqual(len(record["manufacturers"]["0x004C"]["header_hex"]), 22)
        self.assertNotIn("aa", record["manufacturers"]["0x004C"]["header_hex"])

    def test_unknown_packet_retained_for_investigation(self):
        device = SimpleNamespace(address="A", name="unknown pods")
        advertisement = SimpleNamespace(local_name=None, rssi=-45,
                                        manufacturer_data={0x1234: bytes([1, 2, 3])})
        record = describe_advertisement(device, advertisement)
        self.assertIsNone(record["recognized_legacy_model"])
        self.assertEqual(record["manufacturers"]["0x1234"]["header_hex"], "010203")

    def test_demo_diagnostic_is_explicitly_simulated(self):
        report = asyncio.run(collect(20, demo=True))
        self.assertEqual(report["mode"], "DEMO")
        self.assertEqual(report["devices"][0]["address"], "DEMO-DEVICE")


class WorkerTests(unittest.TestCase):
    def test_company_filter_and_valid_callback(self):
        worker = ScanWorker()
        device = SimpleNamespace(address="A", name=None)
        advert = SimpleNamespace(manufacturer_data={1: demo_payload()}, local_name=None, rssi=-45)
        worker._received(device, advert)
        self.assertTrue(worker.messages.empty())
        advert.manufacturer_data = {0x004C: demo_payload()}
        worker._received(device, advert)
        event = worker.messages.get_nowait()
        self.assertEqual(event.kind, "observation")
        self.assertEqual(event.value.battery.left, 80)

    def test_messages_are_bounded_and_keep_latest(self):
        worker = ScanWorker()
        for index in range(1000):
            worker.send("status", index)
        events = []
        while not worker.messages.empty():
            events.append(worker.messages.get_nowait())
        self.assertEqual(len(events), 128)
        self.assertEqual(events[-1].value, 999)

    def test_scanner_context_is_closed_on_stop(self):
        records = []
        worker = ScanWorker()

        class FakeScanner:
            def __init__(self, detection_callback, scanning_mode):
                self.callback = detection_callback
                records.append(scanning_mode)

            async def __aenter__(self):
                records.append("started")
                self.callback(SimpleNamespace(address="A", name="My Pods"),
                              SimpleNamespace(manufacturer_data={0x004C: demo_payload()},
                                              local_name=None, rssi=-45))
                worker.stop()
                return self

            async def __aexit__(self, *args):
                records.append("closed")

        worker.scanner_factory = FakeScanner
        asyncio.run(worker._run())
        self.assertEqual(records, ["passive", "started", "closed"])
        kinds = [worker.messages.get_nowait().kind for _ in range(worker.messages.qsize())]
        self.assertIn("observation", kinds)

    def test_errors_surface_and_worker_finishes(self):
        class BrokenScanner:
            def __init__(self, **kwargs):
                raise RuntimeError("Bluetooth is off")
        worker = ScanWorker(scanner_factory=BrokenScanner)
        worker.start()
        worker.thread.join(2)
        self.assertFalse(worker.running)
        events = [worker.messages.get_nowait() for _ in range(worker.messages.qsize())]
        self.assertEqual([event.kind for event in events], ["error", "stopped"])
        self.assertIn("Bluetooth is off", events[0].value)

    def test_demo_has_data_and_stops_without_bluetooth(self):
        worker = ScanWorker(demo=True)
        worker.start()
        deadline = time.monotonic() + 2
        events = []
        while time.monotonic() < deadline:
            event = worker.messages.get(timeout=2)
            events.append(event)
            if event.kind == "observation":
                break
        worker.stop()
        worker.thread.join(2)
        self.assertFalse(worker.running)
        observation = next(event.value for event in events if event.kind == "observation")
        self.assertEqual(observation.address, "DEMO-DEVICE")
        self.assertEqual(observation.battery.left, 80)


if __name__ == "__main__":
    unittest.main()
