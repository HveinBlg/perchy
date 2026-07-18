"""Compatibility shim so the app can build against either PyQt6 or PyQt5.

Why: PyQt6 requires macOS 11 (Big Sur) or newer, which locks out
users still on macOS 10.15 (Catalina) -- and their Macs typically
can't be upgraded any further. To ship a "legacy" build for them we
need PyQt5, which supports macOS 10.13+.

How: this module tries PyQt6 first (used by the Windows build and
the modern macOS build). If PyQt6 isn't installed it falls back to
PyQt5 and monkey-patches the small ergonomic differences so the
rest of the codebase can be written in PyQt6 style.

The three differences we bridge:

- Enum scoping:   PyQt6 -> Qt.WindowType.FramelessWindowHint
                  PyQt5 -> Qt.FramelessWindowHint
                  We alias Qt.WindowType (and friends) to Qt itself,
                  so accessing Qt.WindowType.X transparently falls
                  through to Qt.X.

- QPainter.RenderHint scoping (same idea).

- QApplication.exec() vs QApplication.exec_(): PyQt5 >= 5.11 already
  supports the un-suffixed name, so we don't need to patch anything.

Result: downstream code says `from qt_compat import Qt, QWidget, ...`
and enjoys PyQt6-style scoped enums no matter which Qt is actually
installed.
"""

try:
    from PyQt6.QtCore import (
        Qt,
        QTimer,
        QSize,
        QObject,
        pyqtSignal,
    )
    from PyQt6.QtGui import (
        QBrush,
        QColor,
        QGuiApplication,
        QPainter,
        QPen,
        QPixmap,
    )
    from PyQt6.QtWidgets import (
        QApplication,
        QLabel,
        QPushButton,
        QWidget,
    )

    PYQT_VERSION = 6

except ImportError:
    from PyQt5.QtCore import (
        Qt,
        QTimer,
        QSize,
        QObject,
        pyqtSignal,
    )
    from PyQt5.QtGui import (
        QBrush,
        QColor,
        QGuiApplication,
        QPainter,
        QPen,
        QPixmap,
    )
    from PyQt5.QtWidgets import (
        QApplication,
        QLabel,
        QPushButton,
        QWidget,
    )

    PYQT_VERSION = 5

    # ------------------------------------------------------------------
    # Bridge PyQt5's flat enums to PyQt6's scoped-enum syntax so we can
    # write `Qt.WindowType.FramelessWindowHint` everywhere without
    # caring which Qt is loaded.
    # ------------------------------------------------------------------
    for _scope in (
        "WindowType",
        "WidgetAttribute",
        "AspectRatioMode",
        "TransformationMode",
        "AlignmentFlag",
        "CursorShape",
        "MouseButton",
        "PenStyle",
    ):
        try:
            setattr(Qt, _scope, Qt)
        except (TypeError, AttributeError):
            # Some sip-generated wrapper types refuse attribute assignment.
            # Not fatal -- callers can still fall back to Qt.X directly.
            pass

    # QPainter.RenderHint.Antialiasing (PyQt6) -> QPainter.Antialiasing (PyQt5)
    try:
        QPainter.RenderHint = QPainter
    except (TypeError, AttributeError):
        pass


__all__ = [
    "Qt",
    "QTimer",
    "QSize",
    "QObject",
    "pyqtSignal",
    "QBrush",
    "QColor",
    "QGuiApplication",
    "QPainter",
    "QPen",
    "QPixmap",
    "QApplication",
    "QLabel",
    "QPushButton",
    "QWidget",
    "PYQT_VERSION",
]
