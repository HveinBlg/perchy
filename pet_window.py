"""Transparent, always-on-top pet window that hitchhikes on the active window."""

from __future__ import annotations

import ctypes
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QPixmap, QGuiApplication
from PyQt6.QtWidgets import QLabel, QWidget

import config
from active_window_tracker import ActiveWindowTracker
from image_manager import ImageManager

# --- Win32 extended-window-style bits we set after the window is shown ---
GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000  # clicks/focus never activate our window
WS_EX_TOOLWINDOW = 0x00000080  # hide from Alt-Tab and taskbar
WS_EX_TRANSPARENT = 0x00000020  # mouse events pass through (belt & braces)


class PetWindow(QWidget):
    def __init__(self):
        super().__init__()

        self._pet_size = tuple(config.PET_SIZE)
        self._overlap = int(config.OVERLAP)
        self._anchor = float(config.HORIZONTAL_ANCHOR)

        # --- Window flags: frameless, always on top, no taskbar entry ---
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        if config.CLICK_THROUGH:
            # Qt-level click-through. We additionally OR WS_EX_TRANSPARENT
            # below because some drivers ignore the Qt flag alone.
            flags |= Qt.WindowType.WindowTransparentForInput
        self.setWindowFlags(flags)

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.resize(*self._pet_size)

        # --- The pet sprite itself ---
        # The label + widget are resized on every image change to match the
        # scaled pixmap's real dimensions (see _on_image_changed). Starting
        # them at 1x1 avoids a one-frame flash of a giant transparent box
        # before the first pixmap arrives.
        self._label = QLabel(self)
        self._label.setStyleSheet("background: transparent;")

        # --- Image rotation ---
        self._images = ImageManager(
            assets_dir=config.ASSETS_DIR,
            rotate_seconds=config.ROTATE_SECONDS,
            rescan_seconds=config.RESCAN_SECONDS,
            parent=self,
        )
        self._images.image_changed.connect(self._on_image_changed)
        # Paint whatever's available right now (or nothing).
        self._on_image_changed(self._images.current_pixmap())

        # --- Active-window follower ---
        self._tracker = ActiveWindowTracker(self_hwnd_getter=lambda: int(self.winId()))
        self._track_timer = QTimer(self)
        self._track_timer.setInterval(int(config.TRACK_INTERVAL_MS))
        self._track_timer.timeout.connect(self._on_tick)
        self._track_timer.start()

        self._ex_style_applied = False

    # ------------------------------------------------------------------
    # Qt event overrides
    # ------------------------------------------------------------------
    def showEvent(self, event):
        super().showEvent(event)
        # Extended styles can only be applied once the HWND actually exists.
        if not self._ex_style_applied:
            self._apply_win32_ex_style()
            self._ex_style_applied = True

    # ------------------------------------------------------------------
    # Win32 tweaks
    # ------------------------------------------------------------------
    def _apply_win32_ex_style(self) -> None:
        """Force NOACTIVATE + TOOLWINDOW (+ TRANSPARENT) on our HWND.

        Without NOACTIVATE, clicking near the pet would steal focus from the
        window we're supposed to be sitting on top of. TOOLWINDOW keeps us
        out of Alt-Tab.
        """
        try:
            hwnd = int(self.winId())
            user32 = ctypes.windll.user32
            cur = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            new = cur | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
            if config.CLICK_THROUGH:
                new |= WS_EX_TRANSPARENT
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new)
        except Exception:
            # Non-Windows or restricted environment; fall back to Qt-only flags.
            pass

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------
    def _on_image_changed(self, pixmap: Optional[QPixmap]) -> None:
        if pixmap is None or pixmap.isNull():
            # Empty folder => hide the pet entirely so nothing is drawn.
            self._label.clear()
            self.hide()
            return

        scaled = pixmap.scaled(
            QSize(*self._pet_size),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._label.setPixmap(scaled)

        # Resize both the label and the pet window to the pixmap's ACTUAL
        # scaled size (which fits within self._pet_size but may be smaller
        # in one dimension). This is what lets the pet dock cleanly to the
        # top of a maximised window: with a fixed 180x180 widget, a
        # short/wide sprite would leave 60-80px of invisible transparent
        # space above its head, and when the widget got clamped to y=0
        # (screen top) all that padding pushed the visible cat far down
        # into the app's toolbar.
        new_size = scaled.size()
        self._label.setFixedSize(new_size)
        self.resize(new_size)

    def _on_tick(self) -> None:
        # If we don't have an image yet, don't bother positioning.
        if self._images.current_pixmap() is None:
            if self.isVisible():
                self.hide()
            return

        rect = self._tracker.get_active_window_rect()
        if rect is None:
            if self.isVisible():
                self.hide()
            return

        left, top, right, _bottom = rect
        win_w = right - left
        # Use the widget's current dimensions (which follow the loaded
        # sprite's real size), not the max PET_SIZE box, so positioning is
        # tight against the actual cat rather than an invisible bounding
        # rectangle.
        pet_w = self.width()
        pet_h = self.height()

        # Horizontal anchor along the window's top edge.
        x = left + int(win_w * self._anchor) - pet_w // 2
        # Vertical: pet's bottom overlaps the title bar by `overlap` pixels.
        y = top - pet_h + self._overlap

        # Keep the pet on-screen if the window is docked to the top.
        screen = QGuiApplication.screenAt(self.pos())
        if screen is None:
            screen = QGuiApplication.primaryScreen()
        if screen is not None:
            geo = screen.geometry()
            if y < geo.top():
                y = geo.top()

        self.move(x, y)
        if not self.isVisible():
            self.show()
