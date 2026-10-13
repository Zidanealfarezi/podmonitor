"""Screenshot-derived device settings; these have no working OEM transport yet."""
FEATURES = {
    "audio": [
        ("Personalized Volume", "Volume otomatis mengikuti lingkungan."),
        ("Conversation Awareness", "Menurunkan media ketika kamu berbicara."),
        ("Automatic Ear Detection", "Jeda otomatis berdasarkan sensor di earbud."),
        ("Personalized Spatial Audio", "Personalisasi suara spasial dari perangkat Apple."),
        ("Follow iPhone / Head Tracking", "Pelacakan gerakan kepala dan arah sumber suara."),
        ("Microphone", "Pemilihan earbud yang menjadi mikrofon."),
        ("Hearing Assistance / Hearing Test", "Fitur pendengaran yang terlihat pada menu iPhone."),
    ],
    "controls": [
        ("Press and Hold — Left", "Aksi menahan batang earbud kiri: mode audio atau asisten."),
        ("Press and Hold — Right", "Aksi menahan batang earbud kanan: mode audio atau asisten."),
        ("Siri", "Integrasi asisten yang terlihat pada menu iPhone."),
        ("Answer Call", "Jumlah tekanan untuk menjawab panggilan."),
        ("Mute & Unmute", "Jumlah tekanan untuk membisukan mikrofon panggilan."),
        ("End Call", "Jumlah tekanan untuk mengakhiri panggilan."),
        ("Press Speed", "Kecepatan tekan dua atau tiga kali."),
        ("Press and Hold Duration", "Durasi tekanan panjang pada batang."),
        ("Noise Cancellation with One AirPod", "Pengaturan ANC ketika memakai satu earbud."),
        ("Tone Volume", "Volume nada dan efek suara di earphone."),
        ("Volume Swipe", "Gestur geser pada batang dan waktu jeda antar geser."),
    ],
    "battery": [
        ("Optimized Battery Charging", "Pengelolaan pengisian baterai oleh firmware."),
        ("Enable Charging Case Sounds", "Suara bawaan casing pengisian."),
    ],
    "device": [
        ("Show in Find My", "Layanan pencarian perangkat dalam ekosistem Apple."),
        ("Disconnect / Forget This Device", "Gunakan Pengaturan Bluetooth Windows untuk koneksi."),
    ],
}


class LowBatteryAlerts:
    """Warn once per low-battery episode; do not treat unknown data as empty."""
    def __init__(self):
        self.warned: set[str] = set()

    def should_warn(self, observation, now, threshold: int, enabled: bool) -> bool:
        if not enabled or not observation.fresh(now):
            return False
        levels = [value for value in (observation.battery.left, observation.battery.right)
                  if value is not None]
        if not levels:
            return False
        low = min(levels)
        if low >= threshold + 10:
            self.warned.discard(observation.address)
        if low <= threshold and observation.address not in self.warned:
            self.warned.add(observation.address)
            return True
        return False
