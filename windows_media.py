"""Media commands for the active Windows output/player, not OEM firmware."""
import ctypes
import sys


class MouseInput(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_int32), ("dy", ctypes.c_int32),
                ("mouseData", ctypes.c_uint32), ("dwFlags", ctypes.c_uint32),
                ("time", ctypes.c_uint32), ("dwExtraInfo", ctypes.c_size_t)]


class KeyboardInput(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_uint16), ("wScan", ctypes.c_uint16),
                ("dwFlags", ctypes.c_uint32), ("time", ctypes.c_uint32),
                ("dwExtraInfo", ctypes.c_size_t)]


class HardwareInput(ctypes.Structure):
    _fields_ = [("uMsg", ctypes.c_uint32), ("wParamL", ctypes.c_uint16),
                ("wParamH", ctypes.c_uint16)]


class InputValue(ctypes.Union):
    _fields_ = [("mi", MouseInput), ("ki", KeyboardInput), ("hi", HardwareInput)]


class Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_uint32), ("value", InputValue)]


KEYS = {"play_pause": 0xB3, "mute": 0xAD, "volume_down": 0xAE, "volume_up": 0xAF}


def send_media(action: str, sender=None) -> None:
    if action not in KEYS:
        raise ValueError("Unsupported media command")
    if sender is None:
        if sys.platform != "win32":
            raise RuntimeError("Kontrol media tersedia di Windows.")
        sender = ctypes.WinDLL("user32", use_last_error=True).SendInput
        sender.argtypes = [ctypes.c_uint32, ctypes.POINTER(Input), ctypes.c_int]
        sender.restype = ctypes.c_uint32
    events = (Input * 2)()
    for index, flag in enumerate((0, 2)):
        events[index].type = 1  # INPUT_KEYBOARD
        events[index].value.ki = KeyboardInput(KEYS[action], 0, flag, 0, 0)
    if sender(2, events, ctypes.sizeof(Input)) != 2:
        raise RuntimeError("Windows tidak menerima perintah media.")
