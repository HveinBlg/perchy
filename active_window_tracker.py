"""Tracks the currently focused top-level window on Windows.

Uses ctypes to call Win32 / DWM APIs directly, so pywin32 is not required.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from typing import Optional, Tuple

user32 = ctypes.windll.user32
dwmapi = ctypes.windll.dwmapi

# --- DWM attribute IDs ---
DWMWA_CLOAKED = 14
DWMWA_EXTENDED_FRAME_BOUNDS = 9

# Window class names we always want to ignore (desktop / shell).
SHELL_CLASSES = {
    "Progman",         # desktop
    "WorkerW",         # desktop worker
    "Shell_TrayWnd",   # taskbar
    "Shell_SecondaryTrayWnd",  # taskbar on secondary monitors
    "DV2ControlHost",  # start menu (older)
    "Windows.UI.Core.CoreWindow",  # start menu / notification center on Win10/11
}


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


def _get_class_name(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def _is_cloaked(hwnd: int) -> bool:
    cloaked = ctypes.c_int(0)
    hr = dwmapi.DwmGetWindowAttribute(
        wintypes.HWND(hwnd),
        DWMWA_CLOAKED,
        ctypes.byref(cloaked),
        ctypes.sizeof(cloaked),
    )
    if hr != 0:
        return False
    return bool(cloaked.value)


def _get_extended_bounds(hwnd: int) -> Optional[RECT]:
    rect = RECT()
    hr = dwmapi.DwmGetWindowAttribute(
        wintypes.HWND(hwnd),
        DWMWA_EXTENDED_FRAME_BOUNDS,
        ctypes.byref(rect),
        ctypes.sizeof(rect),
    )
    if hr != 0:
        return None
    return rect


class ActiveWindowTracker:
    """Reads the foreground window's screen rectangle.

    `self_hwnd_getter` returns our own pet window's HWND so we can skip it
    (otherwise focusing the pet would make it try to follow itself).
    """

    def __init__(self, self_hwnd_getter=None):
        self.self_hwnd_getter = self_hwnd_getter

    def get_active_window_rect(self) -> Optional[Tuple[int, int, int, int]]:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None

        my_hwnd = self.self_hwnd_getter() if self.self_hwnd_getter else 0
        if my_hwnd and hwnd == my_hwnd:
            return None

        # Minimized windows have a bogus (-32000, -32000) rect.
        if user32.IsIconic(hwnd):
            return None

        # UWP / suspended apps mark themselves cloaked; DwmGetWindowAttribute
        # still returns a rect but the window isn't actually visible.
        if _is_cloaked(hwnd):
            return None

        # Filter out the desktop and taskbar so the pet doesn't stick to them
        # when the user clicks the desktop.
        cls = _get_class_name(hwnd)
        if cls in SHELL_CLASSES:
            return None

        # DwmGetWindowAttribute(EXTENDED_FRAME_BOUNDS) gives us the "visible"
        # bounds excluding the invisible drop-shadow padding that
        # GetWindowRect includes on Win10+. Much more accurate for placement.
        rect = _get_extended_bounds(hwnd)
        if rect is None:
            rect = RECT()
            if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                return None

        return (rect.left, rect.top, rect.right, rect.bottom)
