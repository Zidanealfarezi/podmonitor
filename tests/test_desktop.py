import ctypes
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import tempfile
import time
import unittest

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QLabel, QScrollArea
from airpods import BatteryReading, Observation
from features import FEATURES, LowBatteryAlerts
from main import Window
from windows_media import Input, send_media


class AlertTests(unittest.TestCase):
    def test_low_battery_warns_once_then_rearms_on_recovery(self):
        alerts = LowBatteryAlerts()
        def observation(level):
            return Observation("A", "pods", -30, 100, BatteryReading("Pro", level, 80, 50))
        self.assertTrue(alerts.should_warn(observation(20), 101, 20, True))
        self.assertFalse(alerts.should_warn(observation(10), 101, 20, True))
        self.assertFalse(alerts.should_warn(observation(40), 101, 20, True))
        self.assertTrue(alerts.should_warn(observation(20), 101, 20, True))

    def test_stale_unknown_and_disabled_do_not_notify(self):
        alerts = LowBatteryAlerts()
        unknown = Observation("A", "pods", -30, 100, BatteryReading("Pro", None, None, 0))
        low = Observation("A", "pods", -30, 100, BatteryReading("Pro", 10, None, 0))
        self.assertFalse(alerts.should_warn(unknown, 101, 20, True))
        self.assertFalse(alerts.should_warn(low, 131, 20, True))
        self.assertFalse(alerts.should_warn(low, 101, 20, False))


class WindowsMediaTests(unittest.TestCase):
    def test_native_packets_contain_press_and_release(self):
        seen = []
        def sender(count, events, size):
            seen.append((count, size, events[0].type,
                         events[0].value.ki.wVk, events[1].value.ki.dwFlags))
            return count
        send_media("play_pause", sender=sender)
        expected_size = 40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28
        self.assertEqual(seen, [(2, expected_size, 1, 0xB3, 2)])

    def test_partial_windows_send_is_reported(self):
        with self.assertRaises(RuntimeError):
            send_media("mute", sender=lambda *args: 0)
        with self.assertRaises(ValueError):
            send_media("not_a_media_command", sender=lambda *args: 2)


class DesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])
        cls.application.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        settings = QSettings(self.directory.name + "/settings.ini", QSettings.Format.IniFormat)
        self.window = Window(demo=True, settings=settings)
        self.window.resize(1100, 760)
        self.window.show()
        self.pump(.35)

    def pump(self, seconds):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self.application.processEvents()
            time.sleep(.01)

    def tearDown(self):
        self.window.worker.stop()
        self.window.worker.thread.join(2)
        if self.window.diag_thread:
            self.window.diag_thread.join(2)
        self.window.allow_close = True
        self.window.close()
        self.window.deleteLater()
        self.application.processEvents()
        self.directory.cleanup()

    def test_live_ui_shows_demo_batteries_and_marks_demo(self):
        self.assertEqual([tile.number.text() for tile in self.window.battery_tiles],
                         ["~80%", "~70%", "~60%"])
        self.assertEqual(self.window.detected_badge.text(), "SIMULASI")
        self.assertFalse(self.window.notify.isEnabled())

    def test_all_reference_features_present_and_no_anc_control_enabled(self):
        texts = {item.text() for item in self.window.findChildren(QLabel)}
        for group in FEATURES.values():
            for name, _description in group:
                self.assertIn(name, texts)
        self.assertTrue(all(not item.isEnabled() for item in self.window.mode_buttons))

    def test_navigation_narrow_window_and_scroll_access(self):
        self.window.resize(780, 520)
        for index in range(5):
            self.window.nav_buttons[index].click()
            self.application.processEvents()
            self.assertEqual(self.window.pages.currentIndex(), index)
            self.assertTrue(self.window.nav_buttons[index].isChecked())
            self.assertIsInstance(self.window.pages.widget(index), QScrollArea)
        self.assertLessEqual(self.window.width(), 800)

    def test_stop_clears_display_and_restart_restores_data(self):
        self.window.scan_button.click()
        self.pump(.4)
        self.assertEqual([tile.number.text() for tile in self.window.battery_tiles], ["--"] * 3)
        self.window.scan_button.click()
        self.pump(.4)
        self.assertEqual(self.window.battery_tiles[0].number.text(), "~80%")

    def test_swap_applies_and_is_saved(self):
        self.window.swap.setChecked(True)
        self.window.tick()
        self.assertEqual(self.window.battery_tiles[0].number.text(), "~70%")
        self.assertTrue(self.window.settings.value("swap", False, type=bool))

    def test_diagnostic_button_produces_report_and_resumes_monitor(self):
        self.window.start_diagnostic()
        self.pump(.8)
        self.assertIsNotNone(self.window.latest_report)
        self.assertEqual(self.window.latest_report["mode"], "DEMO")
        self.assertTrue(self.window.save_button.isEnabled())
        self.assertTrue(self.window.copy_button.isEnabled())
        self.assertTrue(self.window.worker.running)


if __name__ == "__main__":
    unittest.main()
