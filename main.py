"""PodMonitor 0.2: Qt desktop UI with explicit device-feature availability."""
import argparse
import asyncio
from datetime import datetime
import json
import os
from pathlib import Path
import queue
import sys
import threading
import time

from PySide6.QtCore import Qt, QSettings, QTimer, QRectF
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QMainWindow, QMenu, QMessageBox, QPushButton,
    QScrollArea, QSpinBox, QStackedWidget, QSystemTrayIcon, QVBoxLayout, QWidget,
)
from airpods import DeviceStore
from diagnose import collect
from features import FEATURES, LowBatteryAlerts
from scanner import ScanWorker
from windows_media import send_media

VERSION = "0.2"
STYLE = """
QWidget {font-family:'Segoe UI','DejaVu Sans'; font-size:13px; color:#24312d;}
QMainWindow, QWidget#body {background:#f6f8f9;}
QFrame#sidebar {background:#ffffff; border-right:1px solid #e6ebea;}
QLabel {background:transparent;}
QLabel#brand {font-size:22px; font-weight:700; color:#183e32;}
QLabel#h1 {font-size:27px; font-weight:700; color:#20372e;}
QLabel#h2 {font-size:18px; font-weight:600; color:#24372d;}
QLabel#muted {font-size:12px; color:#73817b;}
QLabel#eyebrow {font-size:11px; font-weight:600; color:#6b7c71;}
QLabel#badge {background:#e8f4ed; color:#2b7153; padding:5px 9px; border-radius:9px; font-size:11px;}
QLabel#pending {background:#fff4de; color:#93702d; padding:5px 9px; border-radius:9px; font-size:10px;}
QFrame#card {background:white; border:1px solid #e7ece9; border-radius:17px;}
QFrame#hero {background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #e7f4ec,stop:1 #eff4f7); border-radius:20px;}
QPushButton {background:#ffffff; border:1px solid #dce5df; border-radius:10px; padding:9px 14px; color:#3e5749;}
QPushButton:hover {background:#edf5ef; border-color:#bed3c5;}
QPushButton:pressed {background:#dcebe2;}
QPushButton:disabled {background:#f3f5f4; color:#929d96; border-color:#e9edea;}
QPushButton#primary {background:#2c7555; color:white; border:none; font-weight:600;}
QPushButton#primary:hover {background:#246548;}
QPushButton#nav {text-align:left; border:none; background:transparent; padding:13px 15px; color:#7a8580;}
QPushButton#nav:checked {background:#e9f4ed; color:#236e4a; font-weight:600;}
QLineEdit,QComboBox,QSpinBox {background:white; border:1px solid #dce5df; border-radius:9px; padding:8px; min-height:17px;}
QComboBox::drop-down {border:none; width:24px;}
QScrollArea {background:transparent; border:none;}
QScrollBar:vertical {background:transparent; width:7px; margin:3px;}
QScrollBar::handle:vertical {background:#c9d4cf; border-radius:3px; min-height:35px;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0px;}
QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical {background:transparent;}
QCheckBox {spacing:9px;}
QCheckBox::indicator {width:17px; height:17px; border:1px solid #bdcdc3; border-radius:5px; background:white;}
QCheckBox::indicator:checked {background:#2c7555; border-color:#2c7555;}
QCheckBox::indicator:disabled {background:#e6ebe8; border-color:#d5ddd8;}
"""


def label(text, role=None):
    widget = QLabel(text)
    if role:
        widget.setObjectName(role)
    widget.setWordWrap(True)
    return widget


def card(title=None):
    frame = QFrame()
    frame.setObjectName("card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(20, 18, 20, 18)
    layout.setSpacing(13)
    if title:
        layout.addWidget(label(title, "h2"))
    return frame, layout


def button(text, slot=None, primary=False):
    item = QPushButton(text)
    if primary:
        item.setObjectName("primary")
    if slot:
        item.clicked.connect(slot)
    return item


def pending_rows(layout, features):
    for name, description in features:
        row = QHBoxLayout()
        content = QVBoxLayout()
        content.setSpacing(4)
        content.addWidget(label(name))
        content.addWidget(label(description, "muted"))
        row.addLayout(content, 1)
        badge = label("Belum aktif", "pending")
        badge.setWordWrap(False)
        row.addWidget(badge, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(row)
        if (name, description) != features[-1]:
            line = QFrame()
            line.setFixedHeight(1)
            line.setStyleSheet("background:#eff2f0;")
            layout.addWidget(line)


class PodsDrawing(QWidget):
    """Code-native vector artwork, with no external or generated image asset."""
    def __init__(self):
        super().__init__()
        self.setFixedSize(250, 130)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.translate(23, 0)
        p.scale(.8125, .8125)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#d4e5db"))
        p.drawEllipse(QRectF(14, 128, 228, 18))
        p.setBrush(QColor("#ffffff"))
        p.setPen(QPen(QColor("#d7e1db"), 1.5))
        p.drawRoundedRect(QRectF(92, 49, 146, 86), 28, 28)
        p.setPen(QPen(QColor("#e0e7e3"), 1.2))
        p.drawLine(98, 78, 232, 78)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#4eaf79"))
        p.drawEllipse(QRectF(161, 93, 5, 5))
        for x, y, rotation in ((20, 22, -17), (59, 27, 15)):
            p.save()
            p.translate(x, y)
            p.rotate(rotation)
            p.setPen(QPen(QColor("#ccd9d1"), 1))
            p.setBrush(QColor("#ffffff"))
            p.drawRoundedRect(QRectF(4, 21, 16, 78), 8, 8)
            p.drawEllipse(QRectF(-9, 0, 40, 34))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#354740"))
            p.drawEllipse(QRectF(-5, 8, 12, 15))
            p.restore()


class BatteryTile(QFrame):
    def __init__(self, name):
        super().__init__()
        self.setObjectName("card")
        self.value = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)
        layout.addWidget(label(name, "eyebrow"))
        self.number = label("--")
        self.number.setStyleSheet("font-size:30px; font-weight:600; color:#274a38;")
        layout.addWidget(self.number)
        self.bar = QFrame()
        self.bar.setFixedHeight(5)
        self.bar.setStyleSheet("background:#edf2ef;border-radius:2px;")
        self.fill = QFrame(self.bar)
        self.fill.setStyleSheet("background:#4b9c72;border-radius:2px;")
        self.note = label("Menunggu data", "muted")
        layout.addWidget(self.bar)
        layout.addWidget(self.note)

    def set_level(self, value, fresh):
        self.value = value
        self.number.setText(f"~{value}%" if value is not None else "--")
        self.note.setText("Perkiraan BLE" if value is not None else
                          ("Data tidak tersedia" if fresh else "Menunggu data baru"))
        self.fill.setGeometry(0, 0, int(self.bar.width() * (value or 0) / 100), 5)
        color = "#d29a42" if value is not None and value <= 20 else "#4b9c72"
        self.fill.setStyleSheet(f"background:{color};border-radius:2px;")


class Window(QMainWindow):
    def __init__(self, demo=False, settings=None):
        super().__init__()
        self.demo = demo
        self.settings = settings if settings is not None else QSettings("PodMonitor", "Desktop")
        self.store = DeviceStore()
        self.worker = ScanWorker(demo=demo)
        self.alerts = LowBatteryAlerts()
        self.selected = None
        self.last_error = None
        self.latest_report = None
        self.results = queue.Queue()
        self.diag_pending = False
        self.diag_running = False
        self.diag_thread = None
        self.closing = False
        self.allow_close = False
        self.setWindowTitle(f"PodMonitor {VERSION} | AirPods OEM")
        self.setStyleSheet(STYLE)
        self.setMinimumSize(780, 520)
        screen = QApplication.primaryScreen().availableGeometry()
        self.resize(min(1100, int(screen.width() * .92)),
                    min(760, int(screen.height() * .90)))
        self._layout()
        self._tray()
        self.worker.start()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(200)

    def _layout(self):
        container = QWidget()
        self.setCentralWidget(container)
        base = QHBoxLayout(container)
        base.setContentsMargins(0, 0, 0, 0)
        base.setSpacing(0)
        side = QFrame()
        side.setObjectName("sidebar")
        side.setFixedWidth(205)
        nav = QVBoxLayout(side)
        nav.setContentsMargins(18, 25, 18, 23)
        nav.setSpacing(9)
        nav.addWidget(label("podmonitor", "brand"))
        nav.addWidget(label("AirPods, di desktopmu.", "muted"))
        nav.addSpacing(27)
        self.nav_buttons = []
        for index, text in enumerate(("Ringkasan", "Audio dan mode", "Kontrol earbud",
                                      "Baterai", "Perangkat")):
            item = button(text, lambda checked=False, i=index: self.navigate(i))
            item.setObjectName("nav")
            item.setCheckable(True)
            nav.addWidget(item)
            self.nav_buttons.append(item)
        nav.addStretch()
        nav.addWidget(label("PERANGKAT OEM", "eyebrow"))
        nav.addWidget(label("Baterai tersedia. Kontrol perangkat menunggu pemeriksaan.", "muted"))
        nav.addSpacing(12)
        nav.addWidget(label(f"Versi {VERSION}  /  " + ("SIMULASI" if self.demo else "Windows"), "muted"))
        base.addWidget(side)
        self.pages = QStackedWidget()
        self.pages.setObjectName("body")
        base.addWidget(self.pages, 1)
        self.overview_page()
        self.audio_page()
        self.controls_page()
        self.battery_page()
        self.device_page()
        self.navigate(0)

    def page(self, title, subtitle):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content.setObjectName("body")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 25, 28, 24)
        layout.setSpacing(17)
        layout.addWidget(label(title, "h1"))
        layout.addWidget(label(subtitle, "muted"))
        scroll.setWidget(content)
        self.pages.addWidget(scroll)
        return layout

    def overview_page(self):
        layout = self.page("AirPods-mu, lebih dekat.",
                           "Pantau baterai dan temukan pengaturan perangkat dalam satu tempat.")
        hero = QFrame()
        hero.setObjectName("hero")
        row = QHBoxLayout(hero)
        row.setContentsMargins(25, 18, 20, 18)
        info = QVBoxLayout()
        info.addWidget(label("PERANGKAT PILIHAN", "eyebrow"))
        self.device_name = label("Menunggu AirPods", "h1")
        info.addWidget(self.device_name)
        self.detected_badge = label("Memindai Bluetooth", "badge")
        info.addWidget(self.detected_badge, 0, Qt.AlignmentFlag.AlignLeft)
        self.age_label = label("Buka casing di dekat laptop.", "muted")
        info.addWidget(self.age_label)
        row.addLayout(info, 1)
        row.addWidget(PodsDrawing())
        layout.addWidget(hero)
        batteries = QHBoxLayout()
        batteries.setSpacing(12)
        self.battery_tiles = [BatteryTile(name) for name in ("EARBUD KIRI", "EARBUD KANAN", "CASING")]
        for tile in self.battery_tiles:
            batteries.addWidget(tile, 1)
        layout.addLayout(batteries)
        frame, content = card()
        picker = QHBoxLayout()
        picker_title = label("Perangkat di sekitar", "h2")
        picker_title.setWordWrap(False)
        picker.addWidget(picker_title)
        self.device_picker = QComboBox()
        self.device_picker.setMinimumWidth(200)
        self.device_picker.currentIndexChanged.connect(self.choose)
        picker.addWidget(self.device_picker, 1)
        content.addLayout(picker)
        self.status_label = label("Memulai pemindaian...", "muted")
        content.addWidget(self.status_label)
        actions = QHBoxLayout()
        self.scan_button = button("Hentikan scan", self.toggle_scan)
        actions.addWidget(self.scan_button)
        actions.addWidget(button("Pengaturan Bluetooth", self.open_settings))
        actions.addStretch()
        content.addLayout(actions)
        content.addWidget(label("Data BLE adalah perkiraan kelipatan 10%. Deteksi sekitar tidak menunjukkan koneksi audio.", "muted"))
        layout.addWidget(frame)
        frame, content = card("Langkah berikutnya")
        content.addWidget(label("Kenali perangkat OEM-mu agar kontrol ANC dan tombol dapat dikembangkan sesuai hardware.", "muted"))
        content.addWidget(button("Periksa perangkat OEM", lambda: self.navigate(4), True),
                          0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(frame)
        layout.addStretch()

    def audio_page(self):
        layout = self.page("Audio & mode", "Fitur dari menu iPhone-mu, dengan status dukungan yang jelas.")
        frame, content = card("Listening Mode")
        row = QHBoxLayout()
        self.mode_buttons = []
        for text in ("Off", "Transparency", "Adaptive", "Noise Cancellation"):
            item = button(text)
            item.setEnabled(False)
            item.setToolTip("Belum ada protokol kontrol yang terverifikasi untuk perangkat OEM ini.")
            row.addWidget(item, 1)
            self.mode_buttons.append(item)
        content.addLayout(row)
        content.addWidget(label("Belum aktif. Mode earphone tidak dapat dibaca atau diubah oleh aplikasi ini.", "muted"))
        layout.addWidget(frame)
        frame, content = card("Kontrol media Windows")
        content.addWidget(label("Berlaku untuk player dan output audio aktif di Windows.", "muted"))
        row = QHBoxLayout()
        self.media_buttons = []
        for text, action in (("Putar / jeda", "play_pause"), ("Volume -", "volume_down"),
                             ("Volume +", "volume_up"), ("Mute", "mute")):
            item = button(text, lambda checked=False, key=action: self.media(key))
            item.setEnabled(sys.platform == "win32" and not self.demo)
            row.addWidget(item)
            self.media_buttons.append(item)
        content.addLayout(row)
        layout.addWidget(frame)
        frame, content = card("Pengaturan audio perangkat")
        content.addWidget(label("Pengaturan berikut belum dapat dikirim ke firmware OEM.", "muted"))
        pending_rows(content, FEATURES["audio"])
        layout.addWidget(frame)
        layout.addStretch()

    def controls_page(self):
        layout = self.page("Kontrol & aksesibilitas", "Pengaturan batang dan gestur yang terlihat pada screenshot.")
        frame, content = card("Pengaturan earbud")
        content.addWidget(label("Belum aktif. Pemeriksaan perangkat diperlukan sebelum konfigurasi bisa diterapkan.", "muted"))
        pending_rows(content, FEATURES["controls"])
        layout.addWidget(frame)
        layout.addStretch()

    def battery_page(self):
        layout = self.page("Baterai", "Pembacaan baterai tersedia. Atur pengingat langsung di aplikasi.")
        frame, content = card("Notifikasi baterai rendah")
        self.notify = QCheckBox("Aktifkan notifikasi Windows")
        self.notify.setChecked(self.settings.value("notifications", False, type=bool))
        self.notify.toggled.connect(lambda value: self.settings.setValue("notifications", value))
        content.addWidget(self.notify)
        row = QHBoxLayout()
        row.addWidget(label("Ingatkan ketika baterai earbud mencapai"))
        self.threshold = QSpinBox()
        self.threshold.setRange(10, 50)
        self.threshold.setSingleStep(10)
        self.threshold.setSuffix("%")
        self.threshold.setValue(self.settings.value("threshold", 20, type=int))
        self.threshold.valueChanged.connect(lambda value: self.settings.setValue("threshold", value))
        row.addWidget(self.threshold)
        row.addStretch()
        content.addLayout(row)
        content.addWidget(label("Satu pengingat per episode baterai rendah. Tidak dikirim dalam mode demo.", "muted"))
        layout.addWidget(frame)
        frame, content = card("Pengisian perangkat")
        content.addWidget(label("Pengaturan pengisian dan suara casing belum didukung.", "muted"))
        pending_rows(content, FEATURES["battery"])
        layout.addWidget(frame)
        layout.addStretch()

    def device_page(self):
        layout = self.page("Perangkat", "Pemeriksaan OEM dan pengaturan tampilan aplikasi.")
        frame, content = card("Periksa perangkat OEM")
        content.addWidget(label("Buka casing di dekat laptop. Pemeriksaan membaca iklan Bluetooth selama 20 detik tanpa mengubah earphone.", "muted"))
        self.diag_button = button("Mulai pemeriksaan", self.start_diagnostic, True)
        content.addWidget(self.diag_button, 0, Qt.AlignmentFlag.AlignLeft)
        self.diag_status = label("Belum ada hasil pemeriksaan.", "muted")
        content.addWidget(self.diag_status)
        row = QHBoxLayout()
        self.save_button = button("Simpan hasil JSON", self.save_report)
        self.copy_button = button("Salin hasil", self.copy_report)
        self.save_button.setEnabled(False)
        self.copy_button.setEnabled(False)
        row.addWidget(self.save_button)
        row.addWidget(self.copy_button)
        row.addStretch()
        content.addLayout(row)
        layout.addWidget(frame)
        frame, content = card("Tampilan aplikasi")
        content.addWidget(label("Nama tampilan", "muted"))
        self.alias = QLineEdit(self.settings.value("alias", "", type=str))
        self.alias.setPlaceholderText("Contoh: airpods zidane")
        self.alias.textChanged.connect(lambda text: self.settings.setValue("alias", text))
        content.addWidget(self.alias)
        content.addWidget(label("Nama ini hanya mengubah tampilan di PodMonitor.", "muted"))
        self.swap = QCheckBox("Tukar pembacaan kiri dan kanan")
        self.swap.setChecked(self.settings.value("swap", False, type=bool))
        self.swap.toggled.connect(lambda value: self.settings.setValue("swap", value))
        content.addWidget(self.swap)
        layout.addWidget(frame)
        frame, content = card("Informasi dari screenshot")
        content.addWidget(label("Jenis: OEM   ·   Model yang ditampilkan: AirPods Pro"))
        content.addWidget(label("Versi di screenshot: 76.1.11   ·   Nomor model dan serial: Unknown", "muted"))
        content.addWidget(label("Informasi ini bukan pembacaan live dan belum menentukan jenis chip.", "muted"))
        pending_rows(content, FEATURES["device"])
        layout.addWidget(frame)
        layout.addStretch()

    def _tray(self):
        self.tray_available = QSystemTrayIcon.isSystemTrayAvailable()
        self.tray = None
        self.notify.setEnabled(self.tray_available and not self.demo)
        if self.tray_available:
            pixmap = QPixmap(40, 40)
            pixmap.fill(Qt.GlobalColor.transparent)
            p = QPainter(pixmap)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setBrush(QColor("#2c7555"))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(2, 2, 36, 36), 11, 11)
            p.setPen(QPen(QColor("white"), 3))
            p.drawArc(QRectF(10, 10, 20, 20), 0, 180 * 16)
            p.drawLine(10, 20, 10, 28)
            p.drawLine(30, 20, 30, 28)
            p.end()
            self.tray = QSystemTrayIcon(QIcon(pixmap), self)
            menu = QMenu()
            menu.addAction("Buka PodMonitor", self.show_window)
            menu.addAction("Keluar", self.close)
            self.tray.setContextMenu(menu)
            self.tray.activated.connect(lambda reason: self.show_window()
                                       if reason == QSystemTrayIcon.ActivationReason.DoubleClick else None)
            self.tray.setToolTip("PodMonitor")
            self.tray.show()

    def navigate(self, index):
        self.pages.setCurrentIndex(index)
        for number, item in enumerate(self.nav_buttons):
            item.setChecked(number == index)

    def show_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def choose(self, _index):
        self.selected = self.device_picker.currentData()

    def open_settings(self):
        if sys.platform == "win32":
            os.startfile("ms-settings:bluetooth")
        else:
            QMessageBox.information(self, "Windows", "Pengaturan Bluetooth tersedia di Windows.")

    def media(self, action):
        try:
            send_media(action)
        except Exception as exc:
            QMessageBox.warning(self, "Kontrol media", str(exc))

    def toggle_scan(self):
        if self.worker.running:
            self.worker.stop()
        else:
            self.restart_scan()

    def restart_scan(self):
        self.worker = ScanWorker(demo=self.demo)
        self.store = DeviceStore()
        self.selected = None
        self.device_picker.clear()
        self.last_error = None
        self.worker.start()

    def tick(self):
        if self.closing:
            return
        for _ in range(128):
            try:
                event = self.worker.messages.get_nowait()
            except queue.Empty:
                break
            if event.kind == "observation":
                self.store.put(event.value)
            elif event.kind == "error":
                self.last_error = str(event.value)
                self.status_label.setText("Scan gagal: " + self.last_error)
            elif event.kind == "status":
                self.status_label.setText("Data simulasi · Bluetooth tidak dipindai." if self.demo else str(event.value))
            elif event.kind == "stopped" and not self.diag_pending and not self.diag_running and not self.last_error:
                self.status_label.setText("Pemindaian dihentikan.")
        while not self.results.empty():
            kind, value = self.results.get_nowait()
            self.finish_diagnostic(kind, value)
        now = time.monotonic()
        addresses = list(self.store.devices)
        existing = [self.device_picker.itemData(i) for i in range(self.device_picker.count())]
        if addresses != existing:
            previous = self.selected
            self.device_picker.blockSignals(True)
            self.device_picker.clear()
            for address, observation in self.store.devices.items():
                self.device_picker.addItem(f"{observation.name} · {address[-8:]}", address)
            index = self.device_picker.findData(previous)
            self.device_picker.setCurrentIndex(max(index, 0))
            self.device_picker.blockSignals(False)
            self.selected = self.device_picker.currentData()
        item = self.store.devices.get(self.selected)
        active = self.worker.running and not self.worker.stop_event.is_set()
        fresh = bool(item and item.fresh(now) and active)
        if item:
            name = self.alias.text().strip() or (item.name if item.name != item.battery.model else "AirPods OEM")
            self.device_name.setText("AirPods simulasi" if self.demo else name)
            self.detected_badge.setText("SIMULASI" if self.demo else ("Data baterai diterima" if fresh else "Data belum diperbarui"))
            age = max(0, int(now - item.seen_at))
            self.age_label.setText(f"Format {item.battery.model}  ·  {age} detik lalu")
        else:
            self.device_name.setText("Menunggu AirPods")
            self.detected_badge.setText("Scan gagal" if self.last_error else "Memindai Bluetooth" if active else "Scan dihentikan")
            self.age_label.setText("Buka casing di dekat laptop.")
        levels = [item.battery.left, item.battery.right, item.battery.case] if fresh else [None] * 3
        if self.swap.isChecked():
            levels[0], levels[1] = levels[1], levels[0]
        for tile, value in zip(self.battery_tiles, levels):
            tile.set_level(value, fresh)
        self.scan_button.setEnabled(not self.diag_pending and not self.diag_running
                                    and not (self.worker.running and self.worker.stop_event.is_set()))
        self.scan_button.setText("Hentikan scan" if active else "Mulai scan")
        if self.tray:
            self.tray.setToolTip("PodMonitor | " + " / ".join(f"~{level}%" if level is not None else "--" for level in levels))
            if fresh and not self.demo and self.alerts.should_warn(item, now, self.threshold.value(), self.notify.isChecked()):
                low = min(value for value in (item.battery.left, item.battery.right) if value is not None)
                self.tray.showMessage("Baterai earbud rendah", f"Perkiraan baterai ~{low}%.",
                                      QSystemTrayIcon.MessageIcon.Information, 5000)

    def start_diagnostic(self):
        if self.diag_pending or self.diag_running:
            return
        self.diag_pending = True
        self.latest_report = None
        self.save_button.setEnabled(False)
        self.copy_button.setEnabled(False)
        self.diag_button.setEnabled(False)
        self.diag_status.setText("Menyiapkan pemeriksaan...")
        self._resume = self.worker.running and not self.worker.stop_event.is_set()
        self._diag_deadline = time.monotonic() + 5
        self.worker.stop()
        QTimer.singleShot(100, self._check_after_stop)

    def _check_after_stop(self):
        if self.closing:
            return
        if self.worker.running:
            if time.monotonic() >= self._diag_deadline:
                self.diag_pending = False
                self.diag_button.setEnabled(True)
                self.diag_status.setText("Scanner belum berhenti. Tunggu lalu coba lagi.")
            else:
                QTimer.singleShot(100, self._check_after_stop)
            return
        self.diag_pending = False
        self.diag_running = True
        self._diag_started = time.monotonic()
        self.diag_status.setText("Memeriksa selama 20 detik. Biarkan casing terbuka...")
        self.diag_thread = threading.Thread(target=self._diagnostic_task, daemon=True)
        self.diag_thread.start()

    def _diagnostic_task(self):
        try:
            self.results.put(("done", asyncio.run(collect(20, self.demo))))
        except Exception as exc:
            self.results.put(("error", str(exc)))

    def finish_diagnostic(self, kind, value):
        self.diag_running = False
        self.diag_pending = False
        self.diag_button.setEnabled(True)
        if kind == "done":
            self.latest_report = value
            self.save_button.setEnabled(True)
            self.copy_button.setEnabled(True)
            self.diag_status.setText(f"Pemeriksaan selesai: {len(value['devices'])} kandidat. Simpan hasil JSON untuk analisis.")
        else:
            self.diag_status.setText("Pemeriksaan gagal: " + str(value))
        if self._resume:
            self.restart_scan()

    def save_report(self):
        if self.latest_report is None:
            return
        default = str(Path.home() / ("diagnostic_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".json"))
        filename, _ = QFileDialog.getSaveFileName(self, "Simpan pemeriksaan OEM", default, "JSON (*.json)")
        if not filename:
            return
        try:
            if not filename.lower().endswith(".json"):
                filename += ".json"
            with open(filename, "x", encoding="utf-8") as output:
                json.dump(self.latest_report, output, ensure_ascii=False, indent=2)
            self.diag_status.setText("Hasil tersimpan: " + filename)
        except Exception as exc:
            QMessageBox.warning(self, "Tidak dapat menyimpan", str(exc))

    def copy_report(self):
        if self.latest_report is not None:
            QApplication.clipboard().setText(json.dumps(self.latest_report, ensure_ascii=False, indent=2))
            self.diag_status.setText("Hasil disalin. Laporan memuat nama dan alamat BLE perangkat yang terdeteksi.")

    def closeEvent(self, event):
        if self.allow_close:
            event.accept()
            return
        event.ignore()
        if not self.closing:
            self.closing = True
            self.worker.stop()
            self.timer.stop()
            if self.tray:
                self.tray.hide()
            self._close_deadline = time.monotonic() + 3
            QTimer.singleShot(50, self._finish_close)

    def _finish_close(self):
        if not self.worker.running or time.monotonic() >= self._close_deadline:
            self.allow_close = True
            self.close()
        else:
            QTimer.singleShot(50, self._finish_close)


def main():
    parser = argparse.ArgumentParser(description="PodMonitor 0.2 untuk Windows dan AirPods OEM")
    parser.add_argument("--demo", action="store_true", help="Gunakan data simulasi")
    args = parser.parse_args()
    application = QApplication(sys.argv[:1])
    application.setApplicationName("PodMonitor")
    application.setFont(QFont("Segoe UI", 10))
    window = Window(demo=args.demo)
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
