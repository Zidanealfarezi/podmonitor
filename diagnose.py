"""Inspect public BLE headers before choosing a device-specific protocol.

Run on Windows: python diagnose.py --seconds 20 --output diagnostic.json
No GATT writes, pairing, firmware changes, or decryption are performed.
"""
import argparse
import asyncio
import json
from pathlib import Path
import sys

from airpods import APPLE_COMPANY_ID, decode_airpods, demo_payload


def describe_advertisement(device, advertisement) -> dict:
    manufacturers = {}
    for company, payload in advertisement.manufacturer_data.items():
        # Limit to public frame headers. Do not export Apple's encrypted tail.
        manufacturers[f"0x{company:04X}"] = {
            "length": len(payload), "header_hex": payload[:11].hex(),
        }
    apple_payload = advertisement.manufacturer_data.get(APPLE_COMPANY_ID, b"")
    reading = decode_airpods(apple_payload)
    return {
        "address": str(device.address),
        "name": advertisement.local_name or device.name or "Nama tidak tersedia",
        "rssi_dbm": advertisement.rssi,
        "manufacturers": manufacturers,
        "recognized_legacy_model": reading.model if reading is not None else None,
    }


async def collect(seconds: int, demo: bool) -> dict:
    report = {
        "mode": "DEMO" if demo else "LIVE",
        "duration_seconds": seconds,
        "meaning": "Iklan BLE yang terdeteksi; bukan bukti keaslian atau status audio.",
        "devices": [],
    }
    if demo:
        from types import SimpleNamespace
        device = SimpleNamespace(address="DEMO-DEVICE", name="AirPods simulasi")
        advertisement = SimpleNamespace(
            local_name=None, rssi=-42, manufacturer_data={APPLE_COMPANY_ID: demo_payload()})
        report["devices"] = [describe_advertisement(device, advertisement)]
        return report
    if sys.platform != "win32":
        raise RuntimeError("Pemeriksaan perangkat asli ditujukan untuk Windows. Gunakan --demo.")
    from bleak import BleakScanner
    devices: dict[str, dict] = {}

    def received(device, advertisement):
        # Capture candidates even when the existing AirPods decoder rejects them.
        if not advertisement.manufacturer_data:
            return
        record = describe_advertisement(device, advertisement)
        if record["address"] not in devices and len(devices) >= 64:
            return
        previous = devices.get(record["address"])
        if previous:
            record["manufacturers"] = {**previous["manufacturers"], **record["manufacturers"]}
            if record["name"] == "Nama tidak tersedia":
                record["name"] = previous["name"]
        devices[record["address"]] = record

    async with BleakScanner(detection_callback=received, scanning_mode="passive"):
        await asyncio.sleep(seconds)
    report["devices"] = sorted(devices.values(), key=lambda value: value["rssi_dbm"], reverse=True)
    return report


def main():
    parser = argparse.ArgumentParser(description="Pemeriksaan format iklan Bluetooth AirPods")
    parser.add_argument("--seconds", type=int, default=20, help="Durasi scan 1 sampai 120 detik")
    parser.add_argument("--output", type=Path, help="Simpan laporan JSON ke berkas yang kamu pilih")
    parser.add_argument("--demo", action="store_true", help="Hasil simulasi; tanpa Bluetooth")
    args = parser.parse_args()
    if not 1 <= args.seconds <= 120:
        parser.error("--seconds harus antara 1 dan 120")
    if args.output is not None and args.output.exists():
        parser.error("Berkas output sudah ada; pilih nama baru agar tidak menimpa hasil sebelumnya.")
    print("Buka casing dekat laptop. Memeriksa header BLE...", file=sys.stderr)
    try:
        report = asyncio.run(collect(args.seconds, args.demo))
        rendered = json.dumps(report, ensure_ascii=False, indent=2)
        print(rendered)
        if args.output:
            with args.output.open("x", encoding="utf-8") as output:
                output.write(rendered + "\n")
            print(f"Laporan tersimpan: {args.output}", file=sys.stderr)
    except (Exception, KeyboardInterrupt) as exc:
        print(f"Pemeriksaan gagal: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
