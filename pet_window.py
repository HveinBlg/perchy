"""Transparent, always-on-top pet window that hitchhikes on the active window.

Two visual modes, chosen every tick based on the active window's state:

- Cat mode      : the currently-selected sprite floats over the window's top
                  edge (bisected by default). Click-through is ON so the
                  cat never steals focus from the app underneath.
- Button mode   : the active window is maximised, so the cat would either
                  end up mostly off-screen or would deep-dive into the
                  app's content. Instead we hide the sprite and show a
                  small "查看猫咪状态" button; clicking it restores the
                  window, which puts us back in cat mode automatically.
"""

from __future__ import annotations

import ctypes
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QPixmap, QGuiApplication
from PyQt6.QtWidgets import QLabel, QPushButton, QWidget

import config
from active_window_tracker import ActiveWindowTracker, WindowState
from image_manager import ImageManager

# --- Win32 extended-window-style bits we set / toggle after showing ---
GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000  # clicks/focus never activate our window
WS_EX_TOOLWINDOW = 0x00000080  # hide from Alt-Tab and taskbar
WS_EX_TRANSPARENT = 0x00000020  # mouse events pass through us

BUTTON_STYLE = """
    QPushButton {
        background-color: rgba(255, 255, 255, 235);
        border: 1px solid rgba(160, 160, 160, 200);
        border-radius: 12px;
        padding: 5px 14px;
        font-size: 12px;
        color: #333;
    }
    QPushButton:hover {
        background-color: rgba(255, 255, 255, 255);
        border-color: rgba(80, 80, 80, 220);
        color: #000;
    }
    QPushButton:pressed {
        background-color: rgba(220, 220, 220, 250);
    }
"""


class PetWindow(QWidget):
    def __init__(self):
        super().__init__()

        self._pet_size = tuple(config.PET_SIZE)
        # OVERLAP can be a fraction (float in (0,1]) or a pixel count
        # (int >= 2). Keep it as-is; _resolve_overlap_px() interprets it
        # against whatever the widget's current height is.
        self._overlap = config.OVERLAP
        self._clamp_to_screen = bool(getattr(config, "CLAMP_TO_SCREEN", True))
        self._anchor = float(config.HORIZONTAL_ANCHOR)

        # --- Window flags: frameless, always on top, no taskbar entry.
        # We intentionally do NOT set Qt.WindowTransparentForInput here:
        # click-through is managed purely at the Win32 layer via
        # WS_EX_TRANSPARENT so we can toggle it off when we need the
        # "restore" button to receive clicks.
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setWindowFlags(flags)

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.resize(*self._pet_size)

        # --- The cat sprite ---
        self._label = QLabel(self)
        self._label.setStyleSheet("background: transparent;")

        # --- The "restore this window" button (shown only in button mode) ---
        self._button = QPushButton("查看猫咪状态", self)
        self._button.setStyleSheet(BUTTON_STYLE)
        self._button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._button.clicked.connect(self._on_restore_clicked)
        self._button.hide()
        self._button.adjustSize()

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
        self._in_button_mode = False
        # HWND of the window we're following. Saved in _enter_button_mode so
        # the click handler can restore that specific window even if focus
        # shifts to us for the instant of the click.
        self._tracked_hwnd: Optional[int] = None

    # ------------------------------------------------------------------
    # Qt event overrides
    # ------------------------------------------------------------------
    def showEvent(self, event):
        super().showEvent(event)
        if not self._ex_style_applied:
            self._apply_win32_base_style()
            self._ex_style_applied = True

    # ------------------------------------------------------------------
    # Win32 tweaks
    # ------------------------------------------------------------------
    def _apply_win32_base_style(self) -> None:
        """Apply NOACTIVATE + TOOLWINDOW + (initial) TRANSPARENT to the HWND."""
        try:
            hwnd = int(self.winId())
            user32 = ctypes.windll.user32
            style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            style |= WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
            if config.CLICK_THROUGH:
                style |= WS_EX_TRANSPARENT
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        except Exception:
            pass

    def _set_click_through(self, enabled: bool) -> None:
        """Runtime toggle of WS_EX_TRANSPARENT.

        Cat mode wants clicks to pass through so it never blocks the
        title bar; button mode wants clicks to LAND on us so the button
        actually works.
        """
        try:
            hwnd = int(self.winId())
            user32 = ctypes.windll.user32
            style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            if enabled:
                style |= WS_EX_TRANSPARENT
            else:
                style &= ~WS_EX_TRANSPARENT
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _resolve_overlap_px(self, pet_h: int) -> int:
        """Interpret config.OVERLAP as either a fraction or a pixel count."""
        val = self._overlap
        if isinstance(val, float) and 0.0 < val <= 1.0:
            return int(round(pet_h * val))
        try:
            return int(val)
        except (TypeError, ValueError):
            return pet_h // 2  # fallback: bisect

    def _rescale_cat_to_widget(self) -> None:
        """(Re)apply the current pixmap to the cat label and resize."""
        pix = self._images.current_pixmap()
        if pix is None or pix.isNull():
            return
        scaled = pix.scaled(
            QSize(*self._pet_size),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._label.setPixmap(scaled)
        self._label.setFixedSize(scaled.size())
        self.resize(scaled.size())

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------
    def _on_image_changed(self, pixmap: Optional[QPixmap]) -> None:
        if pixmap is None or pixmap.isNull():
            self._label.clear()
            # We only hide when we're not showing the button either.
            if not self._in_button_mode:
                self.hide()
            return

        scaled = pixmap.scaled(
            QSize(*self._pet_size),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._label.setPixmap(scaled)
        self._label.setFixedSize(scaled.size())
        # In button mode the widget is sized to the button; don't clobber
        # that just because a new cat rotated in behind the scenes.
        if not self._in_button_mode:
            self.resize(scaled.size())

    def _on_restore_clicked(self) -> None:
        """Un-maximize the tracked window (equivalent to clicking Restore Down)."""
        hwnd = self._tracked_hwnd
        if hwnd:
            self._tracker.restore_window(hwnd)

    # ------------------------------------------------------------------
    # Mode switches
    # ------------------------------------------------------------------
    def _enter_button_mode(self, state: WindowState) -> None:
        # Remember which window to restore when the button is clicked.
        self._tracked_hwnd = state.hwnd

        if not self._in_button_mode:
            self._label.hide()
            self._button.show()
            self._set_click_through(False)  # let the button receive clicks
            self._in_button_mode = True

        btn_size = self._button.sizeHint()
        self._button.resize(btn_size)
        self._button.move(0, 0)
        self.resize(btn_size)

        # Anchor the button horizontally the same way the cat is anchored,
        # so it appears where users' eyes are already looking. Vertically,
        # slot it just inside the title bar so it's fully visible on a
        # maximised window (top == 0).
        win_w = state.right - state.left
        x = state.left + int(win_w * self._anchor) - btn_size.width() // 2
        y = state.top + 5
        self.move(x, y)

        if not self.isVisible():
            self.show()

    def _enter_cat_mode(self, state: WindowState) -> None:
        if self._in_button_mode:
            self._button.hide()
            self._label.show()
            if config.CLICK_THROUGH:
                self._set_click_through(True)
            self._in_button_mode = False
            # Widget was button-sized; snap it back to sprite size.
            self._rescale_cat_to_widget()

        pet_w = self.width()
        pet_h = self.height()

        # Horizontal anchor along the window's top edge.
        x = state.left + int((state.right - state.left) * self._anchor) - pet_w // 2

        # Vertical: pet's bottom overlaps the title bar by `overlap_px`
        # pixels. When OVERLAP is a fraction, it scales with the sprite
        # so wide/short and tall/narrow cats all split the title bar
        # the same way.
        overlap_px = self._resolve_overlap_px(pet_h)
        y = state.top - pet_h + overlap_px

        # Optionally keep the pet fully on-screen when the window is
        # docked to the top of the display.
        if self._clamp_to_screen:
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

    # ------------------------------------------------------------------
    # Main tick
    # ------------------------------------------------------------------
    def _on_tick(self) -> None:
        # If there's no image loaded and we're not in button mode, don't
        # bother showing anything. (In button mode we still want the
        # restore button visible even if the images folder is empty.)
        if self._images.current_pixmap() is None and not self._in_button_mode:
            if self.isVisible():
                self.hide()
            return

        state = self._tracker.get_active_window_state()
        if state is None:
            if self.isVisible():
                self.hide()
            return

        if state.is_maximized:
            self._enter_button_mode(state)
        else:
            self._enter_cat_mode(state)
