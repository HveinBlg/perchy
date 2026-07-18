"""Transparent, always-on-top pet window that hitchhikes on the active window.

Two visual modes, chosen every tick based on the active window's state:

- Cat mode      : the currently-selected sprite floats over the window's top
                  edge (bisected by default). Click-through is ON so the
                  cat never steals focus from the app underneath.
- Button mode   : the active window is maximised, so the cat would deep-dive
                  into the app's content. Instead we hide the sprite and
                  show a small gently-bouncing "查看猫咪状态" pill in a
                  blank spot on the title bar; clicking it restores the
                  window, which puts us back in cat mode automatically.
"""

from __future__ import annotations

import ctypes
import math
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

# --- Bounce animation parameters ---
BOUNCE_RANGE_PX = 6           # vertical travel of the bounce (px)
BOUNCE_FRAME_MS = 30          # ~33 fps
BOUNCE_PHASE_STEP = 0.18      # radians per frame => ~1s per full cycle

# --- Where in the maximised window's title bar we place the button ---
# 0.5 puts it dead center, which is the blank strip between the app's
# left-side title text and the right-side min/max/close buttons in most
# Windows apps.
BUTTON_HORIZONTAL_ANCHOR = 0.5

# --- How far below the window's top edge the widget sits (px) ---
BUTTON_TOP_INSET_PX = 4

BUTTON_STYLE = """
    QPushButton {
        background-color: rgba(255, 255, 255, 235);
        border: 1px solid rgba(150, 150, 150, 200);
        border-radius: 11px;
        padding: 3px 14px;
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

        # --- Mutable runtime state (declared UP FRONT so that anything
        # invoked from later in __init__ -- e.g. the initial
        # _on_image_changed() call from ImageManager setup -- doesn't
        # AttributeError trying to read them). ---
        self._ex_style_applied = False
        self._in_button_mode = False
        self._tracked_hwnd: Optional[int] = None

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

        # --- The "restore this window" button (only in button mode) ---
        self._button = QPushButton("查看猫咪状态", self)
        self._button.setStyleSheet(BUTTON_STYLE)
        self._button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._button.clicked.connect(self._on_restore_clicked)
        self._button.hide()
        self._button.adjustSize()

        # --- Bounce animation state (drives the pill up + down in button mode) ---
        self._bounce_timer = QTimer(self)
        self._bounce_timer.setInterval(BOUNCE_FRAME_MS)
        self._bounce_timer.timeout.connect(self._on_bounce_frame)
        self._bounce_phase = 0.0
        # Base y of the button inside the (slightly-taller) widget. The
        # button oscillates around this baseline; the widget itself
        # holds a fixed screen position so the app title bar underneath
        # doesn't jitter.
        self._button_base_y = 0

        # --- Image rotation ---
        self._images = ImageManager(
            assets_dir=config.ASSETS_DIR,
            rotate_seconds=config.ROTATE_SECONDS,
            rescan_seconds=config.RESCAN_SECONDS,
            parent=self,
        )
        self._images.image_changed.connect(self._on_image_changed)
        self._on_image_changed(self._images.current_pixmap())

        # --- Active-window follower ---
        self._tracker = ActiveWindowTracker(self_hwnd_getter=lambda: int(self.winId()))
        self._track_timer = QTimer(self)
        self._track_timer.setInterval(int(config.TRACK_INTERVAL_MS))
        self._track_timer.timeout.connect(self._on_tick)
        self._track_timer.start()

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
        """Runtime toggle of WS_EX_TRANSPARENT (click-through)."""
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
        val = self._overlap
        if isinstance(val, float) and 0.0 < val <= 1.0:
            return int(round(pet_h * val))
        try:
            return int(val)
        except (TypeError, ValueError):
            return pet_h // 2

    def _rescale_cat_to_widget(self) -> None:
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
        if not self._in_button_mode:
            self.resize(scaled.size())

    def _on_restore_clicked(self) -> None:
        hwnd = self._tracked_hwnd
        if hwnd:
            self._tracker.restore_window(hwnd)

    def _on_bounce_frame(self) -> None:
        """Move the button up/down by a fraction of BOUNCE_RANGE_PX.

        Uses a cosine so y_offset smoothly cycles 0 -> BOUNCE_RANGE_PX
        -> 0 -> BOUNCE_RANGE_PX -> ... The button rests at
        _button_base_y (bottom of its travel) and rises up from there.
        """
        self._bounce_phase += BOUNCE_PHASE_STEP
        if self._bounce_phase > 2 * math.pi:
            self._bounce_phase -= 2 * math.pi
        # cos maps to (1, -1); ((cos+1)/2) maps to (1, 0); *range gives
        # (RANGE, 0). We subtract from base_y so the button *rises* from
        # rest (smaller y == higher on screen).
        rise = int(((math.cos(self._bounce_phase) + 1.0) * 0.5) * BOUNCE_RANGE_PX)
        self._button.move(0, self._button_base_y - rise + BOUNCE_RANGE_PX)

    # ------------------------------------------------------------------
    # Mode switches
    # ------------------------------------------------------------------
    def _enter_button_mode(self, state: WindowState) -> None:
        # Remember which window to restore when the button is clicked;
        # refresh every tick in case the user switches between two
        # maximised windows.
        self._tracked_hwnd = state.hwnd

        if not self._in_button_mode:
            # One-time setup on transition INTO button mode
            self._label.hide()
            self._button.show()
            self._set_click_through(False)  # let the button receive clicks
            self._in_button_mode = True

            btn_size = self._button.sizeHint()
            self._button.resize(btn_size)
            # Widget is slightly taller than the button to give room for
            # the vertical bounce. Baseline y is BOUNCE_RANGE_PX
            # (bottom of the widget); the bounce animates up from there.
            self._button_base_y = 0
            self._button.move(0, BOUNCE_RANGE_PX)  # start at rest
            self.resize(btn_size.width(), btn_size.height() + BOUNCE_RANGE_PX)

            # Kick off the bounce
            self._bounce_phase = 0.0
            self._bounce_timer.start()

        # Reposition every tick (window may briefly change bounds during
        # a monitor switch, animations, etc).
        win_w = state.right - state.left
        x = state.left + int(win_w * BUTTON_HORIZONTAL_ANCHOR) - self.width() // 2
        y = state.top + BUTTON_TOP_INSET_PX
        self.move(x, y)

        if not self.isVisible():
            self.show()

    def _enter_cat_mode(self, state: WindowState) -> None:
        if self._in_button_mode:
            # One-time teardown on transition OUT of button mode
            self._bounce_timer.stop()
            self._button.hide()
            self._label.show()
            if config.CLICK_THROUGH:
                self._set_click_through(True)
            self._in_button_mode = False
            self._rescale_cat_to_widget()

        pet_w = self.width()
        pet_h = self.height()

        x = state.left + int((state.right - state.left) * self._anchor) - pet_w // 2
        overlap_px = self._resolve_overlap_px(pet_h)
        y = state.top - pet_h + overlap_px

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
