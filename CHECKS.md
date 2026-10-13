# Validasi v0.2 — 13 Oktober 2026

- 29 tes otomatis lulus.
- Semua modul lolos pemeriksaan sintaks.
- Lima halaman Qt dirender dan diperiksa visual pada lingkungan Linux offscreen.
- Navigasi dan scroll diuji pada jendela 780 × 520.
- Mode demo menampilkan data bertanda SIMULASI.
- Pemeriksaan OEM lewat tombol menghasilkan laporan demo dan melanjutkan scanner.
- Peringatan baterai diuji terhadap data lama, nilai tidak tersedia, pemulihan,
  pengaturan nonaktif, dan pencegahan notifikasi berulang.
- Struktur paket SendInput dan penanganan kegagalan Windows diuji dengan mock.

Screenshot pengguna menunjukkan versi awal menerima iklan baterai dari
perangkat OEM. Validasi v0.2 masih menggunakan paket sintetis dan mode demo.
Tampilan, notifikasi system tray, serta perintah media belum diuji langsung
di Windows 11 oleh pembuat kode. Driver BLE dan pipeline decoder dipertahankan,
namun kompatibilitas versi baru tetap memerlukan pengujian di laptop pengguna.

Kontrol ANC, Adaptive, ear detection, gestur, konfigurasi tombol, Tone Volume,
suara casing, Spatial Audio, Find My, dan pengaturan firmware belum berfungsi.
Status tersebut ditunjukkan pada UI dan FEATURES.md.

Perintah pengujian:
python -m unittest discover -s tests -v
