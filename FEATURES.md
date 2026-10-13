# Pemetaan fitur dari screenshot perangkat pengguna

Target: Windows 11. Nama Bluetooth di gambar: **airpods zidane**.
About menampilkan Model Name **AirPods Pro**, Model Number **Unknown**,
Serial Number **Unknown**, dan Version **76.1.11**.

Pengguna sudah mengonfirmasi perangkat ini versi OEM. Data screenshot belum
cukup untuk menetapkan chip atau protokol kendalinya.
Versi 76.1.11 tidak tercantum pada daftar firmware AirPods terbaru di halaman
Apple yang diperiksa 13 Oktober 2026. Ini alasan untuk memeriksa hardware,
bukan kesimpulan bahwa perangkat pasti replika.

Kemunculan menu iPhone menunjukkan pilihan yang ditampilkan sistem. Kita
tetap harus memastikan tiap fitur benar-benar tersedia pada perangkat dan
dapat dikendalikan dari Windows sebelum membuat kontrolnya.

| Fitur yang terlihat | Status pada proyek | Kebutuhan untuk pengembangan |
| --- | --- | --- |
| Baterai earbud dan casing | Decoder perkiraan BLE dan UI tersedia; belum diuji pada perangkat ini | Cek format paket dengan `diagnose.py`; bandingkan pembacaan langsung |
| Off / Transparency / Noise Cancellation | Belum diimplementasikan | Identifikasi model/chip, transport kontrol, dan perintah yang benar |
| Adaptive | Belum diimplementasikan | Pastikan mode tersedia dan dapat dikendalikan pada hardware ini |
| Press and Hold Left / Right | Belum diimplementasikan | Uji perintah konfigurasi per perangkat |
| Siri | Belum diimplementasikan | Fitur ekosistem Apple; alternatif Windows harus dirancang tersendiri |
| Answer Call, Mute/Unmute, End Call | Belum diimplementasikan | Bedakan pemetaan tombol firmware dengan integrasi aplikasi panggilan PC |
| Personalized Volume | Belum diimplementasikan | Periksa konfigurasi firmware; kontrol volume Windows bukan fitur yang sama |
| Conversation Awareness | Belum diimplementasikan | Verifikasi dukungan dan perintah pada perangkat |
| Automatic Ear Detection | Belum diimplementasikan | Verifikasi sumber event sensor dan cara menjeda player yang tepat |
| Personalized Spatial Audio | Belum diimplementasikan | Memerlukan jalur audio dan dukungan personalisasi; menu saja tidak cukup |
| Follow iPhone / Head Tracking | Belum diimplementasikan | Periksa data sensor dan dukungan pengolahan audio; tidak dianggap setara di PC |
| Microphone Automatic | Belum diimplementasikan | Bedakan pemilihan mikrofon earbud dengan pemilihan input Windows |
| Optimized Battery Charging | Belum diimplementasikan | Pengaturan firmware/pengelolaan pengisian, bukan sekadar notifikasi |
| Charging Notifications | Peringatan baterai rendah Windows tersedia di v0.2; pemberitahuan pengisian penuh belum tersedia | Menggunakan data BLE yang masih baru; dukungan tray diperlukan |
| Enable Charging Case Sounds | Belum diimplementasikan | Perlu perintah dan dukungan khusus casing/model |
| Show in Find My | Belum diimplementasikan | Terkait layanan Apple; scan BLE lokal bukan pengganti Find My |
| Press Speed / Press and Hold Duration | Belum diimplementasikan | Perlu konfigurasi firmware yang sesuai hardware |
| Noise Cancellation with One AirPod | Belum diimplementasikan | Perlu verifikasi dukungan dan perintah perangkat |
| Tone Volume | Belum diimplementasikan | Volume nada di perangkat berbeda dari volume media Windows |
| Volume Swipe dan waktu jeda | Belum diimplementasikan | Perlu verifikasi konfigurasi kontrol batang |
| Hearing Assistance / Hearing Test | Belum diimplementasikan | Tidak membuat klaim medis atau tes pendengaran dari monitor baterai ini |
| Disconnect / Forget | Tersedia melalui tombol pembuka Pengaturan Windows | Integrasi koneksi/unpair langsung belum diimplementasikan |

## Yang ditambahkan pada v0.2

- UI Qt dengan navigasi lima halaman, kartu baterai, dan konten yang dapat digulir.
- Seluruh kelompok fitur screenshot ditampilkan sebagai referensi. Kontrol
  hardware yang belum diimplementasikan diberi status **Belum aktif**.
- Tombol play/pause, volume naik/turun, serta mute menggunakan perintah media
  Windows. Ini mengendalikan output/player aktif Windows, bukan konfigurasi
  tombol, Tone Volume, atau firmware earphone.
- Notifikasi baterai rendah melalui system tray Windows bila tersedia.
- Nama tampilan dan pertukaran kiri/kanan disimpan sebagai preferensi lokal.
- Pemeriksaan OEM selama 20 detik dapat dimulai dari halaman **Perangkat**,
  kemudian hasilnya disimpan sebagai JSON atau disalin lewat tombol.

## Urutan implementasi yang disarankan

1. Verifikasi format Bluetooth dan identitas teknis perangkat pengguna.
2. Pastikan baterai benar dan data tidak tertukar dengan perangkat di sekitar.
3. Uji notifikasi/tray Windows dan tambahkan pembacaan status koneksi Windows.
4. Tambahkan ANC/Transparency/Off setelah protokol kontrol diketahui.
5. Tambahkan ear detection dan pengaturan tombol setelah diuji pada hardware.

Dokumentasi MagicPods menunjukkan bahwa sebagian earphone replika dengan chip
Airoha tertentu dapat mendukung baterai, ear detection, ANC, dan pengaturan
tombol melalui implementasi per chip. Hal ini tidak membuktikan bahwa perangkat
pada screenshot memakai chip tersebut. Proyek ini belum mengimplementasikan
protokol Airoha maupun driver Apple AAP.

## Pemeriksaan format tanpa mengubah pengaturan perangkat

Setelah dependensi terpasang, buka PowerShell di folder proyek:

```powershell
.\.venv\Scripts\python.exe diagnose.py --seconds 20 --output diagnostic.json
```

Buka casing di dekat laptop selama pemeriksaan. Hasil mencantumkan nama,
kekuatan sinyal, company id, ukuran payload, dan 11 byte awal manufacturer data.
Bagian terenkripsi AirPods tidak diekspor. Hasil dapat memuat alamat BLE dan
nama perangkat sekitar; periksa sebelum membagikannya. Header BLE membantu
menentukan langkah investigasi tetapi tidak memastikan chip/keaslian sendiri.

Jika file `diagnostic.json` sudah ada, pakai nama baru. Mode demo:

```powershell
py -3 diagnose.py --demo
```

## Rujukan

- Identifikasi nomor model Apple: https://support.apple.com/id-id/109525
- Firmware AirPods Apple: https://support.apple.com/id-id/106340
- Dukungan per headphone MagicPods: https://help.magicpods.app/fun-capability/
- Airoha 1571AM: https://help.magicpods.app/headphones/airoha-airpodspro2-1571am/
- Airoha 1562AE: https://help.magicpods.app/headphones/airoha-airpodspro2-1562ae/

Screenshot dipakai sebagai bahan pemetaan, tidak disertakan dalam ZIP kode.
