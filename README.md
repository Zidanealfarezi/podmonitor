# PodMonitor 0.2 — Windows 11 dan earphone OEM

Versi ini mengganti UI awal dengan Qt: tema terang, kartu baterai, lima halaman
pengaturan, dan konten yang dapat digulir pada jendela kecil.

**Kontrol ANC, Adaptive, deteksi telinga, pengaturan tombol, serta pengaturan
firmware OEM belum diimplementasikan.** Menu referensinya tersedia dengan
status **Belum aktif**. Memasukkan nama fitur ke UI tidak berarti fitur itu
sudah bekerja. Protokol kendali perangkat masih perlu diidentifikasi dan diuji.

## Memperbarui dari versi sebelumnya

1. Tutup PodMonitor lama.
2. Ekstrak ZIP terbaru. Salin isi folder `PodMonitor` ke
   `E:\Training\PodMonitor`, lalu ganti berkas kode yang sama.
3. Klik dua kali `run_windows.bat` (mungkin tampil sebagai `run_windows`).
   Skrip memasang dependensi baru PySide6 sebelum membuka aplikasi.
4. Pastikan tulisan **Versi 0.2** tampil di bagian bawah navigasi.

## Fitur yang sudah memiliki implementasi

| Fitur | Cara menggunakan |
| --- | --- |
| Baterai kiri, kanan, casing | Halaman Ringkasan; pilih kandidat earphone |
| Mulai / hentikan scan | Tombol di Ringkasan |
| Pengaturan Bluetooth Windows | Tombol di Ringkasan |
| Play/pause, volume +/-, mute Windows | Halaman Audio dan mode; berlaku untuk output/player aktif |
| Peringatan baterai rendah | Halaman Baterai; aktifkan notifikasi dan pilih ambang |
| Nama tampilan lokal | Halaman Perangkat; tidak mengubah nama Bluetooth earphone |
| Tukar pembacaan kiri/kanan | Halaman Perangkat |
| Pemeriksaan OEM | Halaman Perangkat; simpan JSON atau salin hasil |
| Ikon system tray | Tersedia bila platform menyediakan tray |
| Mode demo | Jalankan `demo_windows.bat`; data simulasi diberi penanda |

Peringatan baterai dikirim satu kali per episode baterai rendah dan akan
dipersiapkan ulang setelah level pulih. Notifikasi tidak dikirim dari data
lama atau dalam mode demo. Aplikasi harus tetap berjalan, termasuk ketika
diminimalkan; tombol tutup mengakhiri aplikasi.

Tombol media Windows bukan pengaturan mikrofon panggilan, gestur batang,
Tone Volume, atau ANC. Respons tergantung player/output yang aktif. Jika
Windows menolak perintah, aplikasi menampilkan pesan galat.

## Pemeriksaan perangkat OEM tanpa perintah terminal

1. Aktifkan Bluetooth, buka casing dengan kedua earbud di dalamnya,
   lalu dekatkan ke laptop.
2. Buka halaman **Perangkat**.
3. Klik **Mulai pemeriksaan** dan tunggu sekitar 20 detik.
4. Klik **Simpan hasil JSON**.
5. Gunakan laporan untuk meneliti format dan protokol yang tersedia.

Scan monitor dihentikan sementara agar dua scanner tidak berjalan bersamaan.
Jika sebelumnya aktif, monitor dilanjutkan setelah pemeriksaan selesai.
Laporan memuat nama, alamat BLE, sinyal, company id, ukuran payload, dan header
manufacturer data. Periksa nama/alamat perangkat sekitar sebelum membagikannya.
Header saja tidak selalu cukup untuk menetapkan jenis chip.

Pemeriksaan tidak menulis konfigurasi earphone, tidak mengubah firmware, dan
tidak mengunggah hasil otomatis. Bagian terenkripsi frame Apple tidak diekspor.

## Memasang dari awal

Gunakan Python 3.11 atau lebih baru dengan Python Launcher. Ekstrak ZIP, aktifkan
Bluetooth, lalu klik `run_windows.bat`. Pemasangan dependensi memerlukan internet.
Prototipe menggunakan Bleak 3.0.2 dan PySide6-Essentials 6.10.2.

Untuk terminal PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Mode demo:

```powershell
.\.venv\Scripts\python.exe main.py --demo
```

Tes:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Pemeriksaan melalui terminal tetap tersedia:

```powershell
.\.venv\Scripts\python.exe diagnose.py --seconds 20 --output diagnostic.json
```

## Batas pembacaan dan dukungan perangkat

Data BLE adalah perkiraan kelipatan 10%, bukan persentase rinci iPhone.
Angka yang tidak tersedia ditampilkan `--`. Setelah 30 detik tanpa paket baru,
angka disembunyikan agar data lama tidak dianggap terbaru.

Nomor model yang disiarkan dipakai untuk memilih decoder. Perangkat OEM dapat
meniru identitas AirPods, sehingga label format tidak membuktikan generasi atau
chip sebenarnya. Terdeteksi di sekitar juga tidak menunjukkan koneksi audio
ke laptop. Alamat BLE dapat berubah dan menghasilkan kandidat baru.

Format legacy yang dikenali mencakup kode model AirPods 1/2/3/4/4 ANC serta
Pro/Pro 2/Pro 3. Ini daftar pengenalan kode, bukan klaim sudah diuji pada setiap
model. AirPods Max dan format lain belum didukung.

Pengguna mengonfirmasi perangkat ini OEM. Screenshot iPhone mencantumkan
`airpods zidane`, Model Name `AirPods Pro`, Version `76.1.11`, nomor model dan
serial `Unknown`. Informasi tersebut ditandai sebagai informasi dari screenshot.
Screenshot aplikasi v0.1 menunjukkan baterai BLE berhasil diterima, tetapi
tidak memverifikasi akurasi persentase atau kemampuan kontrol hardware.

## Isi kode

| Berkas | Fungsi |
| --- | --- |
| `main.py` | UI Qt, navigasi, preferensi, tray, pemeriksaan OEM |
| `airpods.py` | Decoder frame legacy dan cache observasi |
| `scanner.py` | Scanner BLE di thread asinkron terpisah |
| `diagnose.py` | Pemeriksaan dan ekspor header iklan BLE |
| `features.py` | Daftar pengaturan referensi dan aturan peringatan baterai |
| `windows_media.py` | Perintah media Windows melalui SendInput |
| `FEATURES.md` | Pemetaan fitur screenshot dan status implementasi |
| `CHECKS.md` | Hasil pengujian dan batas validasi |

Pengaturan tampilan disimpan lokal memakai QSettings. Tidak ada koneksi ke
layanan eksternal dari aplikasi; installer pip mengunduh dependensi. Proyek
ini ditulis independen, tanpa kode, aset, lisensi, atau instalasi MagicPods.

## Referensi

- Qt Widgets: https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/index.html
- Bleak Scanner: https://bleak.readthedocs.io/en/latest/api/scanner.html
- Bleak Windows: https://bleak.readthedocs.io/en/latest/backends/windows.html
- Windows SendInput: https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendinput
- Pengamatan format BLE: https://github.com/t4t5/podpower
- Pemetaan dukungan per headphone: https://help.magicpods.app/fun-capability/

Format BLE AirPods berasal dari pengamatan komunitas, bukan API resmi Apple.
