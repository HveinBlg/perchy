"""Transparent, always-on-top pet window that hitchhikes on the active window.

Two visual modes, chosen every tick based on the active window's state:

- Cat mode      : the currently-selected sprite floats over the window's top
                  edge (bisected by default). Click-through is ON so the
                  cat never steals focus from the app underneath.
- Button mode   : the active window is maximised, so the cat would deep-dive
                  into the app's content. Instead we hide the sprite and
                  show a tiny string of hanging firecrackers just to the
                  left of the minimize (—) button; clicking them restores
                  the window, which puts us back in cat mode automatically.
"""

from __future__ import annotations

import ctypes
import math
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, QSize, pyqtSignal
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QGuiApplication,
    QPainter,
    QPen,
    QPixmap,
)
from PyQt6.QtWidgets import QLabel, QWidget

import config
from active_window_tracker import ActiveWindowTracker, WindowState
from image_manager import ImageManager

# --- Win32 extended-window-style bits we set / toggle after showing ---
GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000  # clicks/focus never activate our window
WS_EX_TOOLWINDOW = 0x00000080  # hide from Alt-Tab and taskbar
WS_EX_TRANSPARENT = 0x00000020  # mouse events pass through us

# --- Swing animation parameters (firecrackers gently sway) ---
SWING_ANGLE_DEG = 9.0        # max rotation each side of centre (degrees)
SWING_FRAME_MS = 30          # ~33 fps
SWING_PHASE_STEP = 0.09      # radians per frame => ~2.4s per full sway cycle

# --- Where in the maximised window we place the firecrackers ---
# Widget's RIGHT edge is placed this many pixels left of the window's
# right edge. The stock Windows minimise / maximise / close cluster is
# ~138px wide; leaving ~15px extra keeps the firecrackers snug against
# them without ever overlapping.
BUTTON_RIGHT_INSET_PX = 150

# Vertical inset from the window's top edge (firecracker fuse sits here).
BUTTON_TOP_INSET_PX = 2


class FirecrackerWidget(QWidget):
    """A tiny string of three hanging firecrackers, drawn with QPainter.

    - Emits :attr:`clicked` on left mouse press.
    - Rotation about the top-centre pivot: set via
      :meth:`set_swing_angle` from an animation timer.
    """

    clicked = pyqtSignal()

    # Widget geometry -- wide enough to contain the string of firecrackers
    # even at maximum swing without visual clipping.
    W_PX = 34
    H_PX = 52

    # Firecracker body -- 3 red cylinders separated by gold bands.
    _BODY_W = 12
    _BODY_H = 10
    _BAND_H = 2
    _NUM_BODIES = 3
    _FUSE_TOP_Y = 3       # where the spark starts (below widget's top)
    _CLUSTER_TOP_Y = 8    # where the first firecracker starts

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(self.W_PX, self.H_PX)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("点这里，把窗口还原，猫咪出来 🐱")
        self._swing_angle = 0.0

    def set_swing_angle(self, degrees: float) -> None:
        self._swing_angle = degrees
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:  # noqa: D401 (Qt override)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Pivot at top-centre so the whole string swings like a pendulum.
        painter.translate(self.width() / 2, 0)
        painter.rotate(self._swing_angle)

        # --- Fuse (short line) + spark (small gold dot) at the very top ---
        painter.setPen(QPen(QColor(160, 130, 70), 1.4))
        painter.drawLine(0, self._FUSE_TOP_Y + 1, 0, self._CLUSTER_TOP_Y)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(255, 200, 60)))
        painter.drawEllipse(-2, self._FUSE_TOP_Y - 2, 4, 4)

        # --- The stacked red firecrackers, separated by gold bands ---
        body_color = QColor(210, 40, 40)
        body_highlight = QColor(255, 90, 90)
        band_color = QColor(240, 200, 60)
        x_left = -self._BODY_W // 2

        y = self._CLUSTER_TOP_Y
        for _ in range(self._NUM_BODIES):
            # Body: red rounded rect
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(body_color))
            painter.drawRoundedRect(x_left, y, self._BODY_W, self._BODY_H, 2, 2)
            # Subtle highlight strip on the left for a bit of shading
            painter.setBrush(QBrush(body_highlight))
            painter.drawRect(x_left + 1, y + 1, 2, self._BODY_H - 2)
            # Gold band under this body
            painter.setBrush(QBrush(band_color))
            painter.drawRect(x_left, y + self._BODY_H, self._BODY_W, self._BAND_H)
            y += self._BODY_H + self._BAND_H

        # --- Tassel dangling at the very bottom of the string ---
        painter.setBrush(QBrush(QColor(210, 40, 40)))
        painter.drawEllipse(-3, y, 6, 4)


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
        # WS_EX_TRANSPARENT so we can toggle it off when the firecracker
        # needs to receive clicks.
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

        # --- The hanging firecracker string (shown only in button mode) ---
        self._firecracker = FirecrackerWidget(self)
        self._firecracker.clicked.connect(self._on_restore_clicked)
        self._firecracker.hide()

        # --- Swing animation state (drives the firecracker sway) ---
        self._swing_timer = QTimer(self)
        self._swing_timer.setInterval(SWING_FRAME_MS)
        self._swing_timer.timeout.connect(self._on_swing_frame)
        self._swing_phase = 0.0

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

    def _on_swing_frame(self) -> None:
        """Drive the firecracker's swing angle with a smooth sine wave.

        Using sin() (not cos()) means the string starts vertical and
        swings out to each side symmetrically, rather than starting
        pinned to one side.
        """
        self._swing_phase += SWING_PHASE_STEP
        if self._swing_phase > 2 * math.pi:
            self._swing_phase -= 2 * math.pi
        angle = SWING_ANGLE_DEG * math.sin(self._swing_phase)
        self._firecracker.set_swing_angle(angle)

    # ------------------------------------------------------------------
    # Mode switches
    # ------------------------------------------------------------------
    def _enter_button_mode(self, state: WindowState) -> None:
        # Remember which window to restore when the firecrackers are clicked;
        # refreshed every tick in case the user switches between two
        # maximised windows without going through a non-maximised state.
        self._tracked_hwnd = state.hwnd

        if not self._in_button_mode:
            # One-time setup on transition INTO button mode
            self._label.hide()
            self._firecracker.show()
            self._set_click_through(False)  # so the firecracker gets clicks
            self._in_button_mode = True

            fc_w = self._firecracker.width()
            fc_h = self._firecracker.height()
            self._firecracker.move(0, 0)
            self.resize(fc_w, fc_h)

            # Kick off the swing
            self._swing_phase = 0.0
            self._swing_timer.start()

        # Reposition every tick so the string stays glued to the
        # left of the minimize (—) button as the window moves between
        # monitors, resolutions, etc.
        widget_w = self.width()
        x = state.right - BUTTON_RIGHT_INSET_PX - widget_w
        # Guard against pathological cases (widget wider than window).
        if x < state.left:
            x = state.left
        y = state.top + BUTTON_TOP_INSET_PX
        self.move(x, y)

        if not self.isVisible():
            self.show()

    def _enter_cat_mode(self, state: WindowState) -> None:
        if self._in_button_mode:
            # One-time teardown on transition OUT of button mode
            self._swing_timer.stop()
            self._firecracker.hide()
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
