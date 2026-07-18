"""Tracks the currently focused top-level window on macOS.

Uses AppKit for the frontmost application and the Accessibility API
(AXUIElement) for the window's on-screen rectangle.

*** Permissions ***

The Accessibility API refuses to expose window information unless the
running process has been granted "Accessibility" permission in
    System Settings  →  Privacy & Security  →  Accessibility
So the very first time Perchy runs, the user will see nothing until
they add and tick the app there. We call AXIsProcessTrusted() at
construction time and log a friendly hint if the permission is missing.

*** Current limitations ***

- ``is_maximized`` is always False; macOS has no direct "maximised"
  concept (green button either "zooms" to fill available space or
  enters a per-Space fullscreen), so we don't yet flip into
  firecracker mode here.
- ``restore_window`` is a no-op for the same reason.
"""

from __future__ import annotations

import sys
from typing import Optional

from ._base import WindowState

# Import lazily inside the class so this module is importable on any
# platform (the ImportError only fires when a macOS user actually tries
# to construct the tracker without pyobjc installed).
_AppKit = None
_AX = None


def _ensure_imports() -> None:
    global _AppKit, _AX
    if _AppKit is not None and _AX is not None:
        return

    try:
        import AppKit as AppKit_mod
    except ImportError as exc:
        raise ImportError(
            "Perchy on macOS needs pyobjc-framework-Cocoa. Install it with:\n"
            "    pip install pyobjc-framework-Cocoa pyobjc-framework-Quartz"
        ) from exc

    # AX symbols live in HIServices, exposed by pyobjc through multiple
    # umbrella modules depending on version. Try the most common ones.
    ax_mod = None
    for name in ("ApplicationServices", "HIServices", "Quartz", "Cocoa"):
        try:
            ax_mod = __import__(name)
            # Sanity: must expose AXUIElementCreateApplication
            if hasattr(ax_mod, "AXUIElementCreateApplication"):
                break
        except ImportError:
            continue

    if ax_mod is None or not hasattr(ax_mod, "AXUIElementCreateApplication"):
        raise ImportError(
            "Could not find AXUIElement APIs. Install:\n"
            "    pip install pyobjc-framework-Cocoa pyobjc-framework-Quartz"
        )

    _AppKit = AppKit_mod
    _AX = ax_mod


# Bundle IDs of processes that own the desktop / dock / notification center.
# When one of these is the frontmost app we hide the pet entirely.
_SHELL_BUNDLE_IDS = {
    "com.apple.dock",
    "com.apple.WindowManager",
    "com.apple.controlcenter",
    "com.apple.systemuiserver",
    "com.apple.notificationcenterui",
}


class ActiveWindowTracker:
    def __init__(self, self_hwnd_getter=None):
        self.self_hwnd_getter = self_hwnd_getter  # unused on macOS
        _ensure_imports()

        # Warn once at startup if Accessibility is not granted.
        try:
            if not _AX.AXIsProcessTrusted():
                sys.stderr.write(
                    "[perchy] Accessibility permission not granted. Add this "
                    "app in System Settings → Privacy & Security → "
                    "Accessibility, then relaunch Perchy.\n"
                )
        except Exception:
            pass

    # ------------------------------------------------------------------
    def get_active_window_state(self) -> Optional[WindowState]:
        ws = _AppKit.NSWorkspace.sharedWorkspace()
        front_app = ws.frontmostApplication()
        if front_app is None:
            return None

        # Skip the Finder desktop / dock / other shell processes so the
        # cat auto-hides when the user clicks the desktop.
        bundle_id = front_app.bundleIdentifier()
        if bundle_id in _SHELL_BUNDLE_IDS:
            return None

        pid = int(front_app.processIdentifier())

        # AXUIElement for the whole app...
        app_el = _AX.AXUIElementCreateApplication(pid)
        if app_el is None:
            return None

        # ...then its focused window (fall back to main window).
        focused = self._copy_attr(app_el, "AXFocusedWindow")
        if focused is None:
            focused = self._copy_attr(app_el, "AXMainWindow")
        if focused is None:
            return None

        # If the window is hidden / minimised, bail.
        minimized = self._copy_attr(focused, "AXMinimized")
        if bool(minimized):
            return None

        pos_ax = self._copy_attr(focused, "AXPosition")
        size_ax = self._copy_attr(focused, "AXSize")
        if pos_ax is None or size_ax is None:
            return None

        pt = self._unpack_ax_value(pos_ax, "point")
        sz = self._unpack_ax_value(size_ax, "size")
        if pt is None or sz is None:
            return None

        # AX position/size use screen coordinates in points, top-left
        # origin (same as Qt), so we can pass them straight through.
        left = int(round(pt[0]))
        top = int(round(pt[1]))
        right = int(round(pt[0] + sz[0]))
        bottom = int(round(pt[1] + sz[1]))

        # Zero-size windows are usually artefacts (splash screens closing,
        # transient palettes) -- ignore them.
        if right - left <= 0 or bottom - top <= 0:
            return None

        return WindowState(
            hwnd=pid,          # not really an hwnd; kept for API symmetry
            left=left,
            top=top,
            right=right,
            bottom=bottom,
            is_maximized=False,  # MVP: no maximise detection on macOS yet
        )

    def restore_window(self, hwnd) -> None:
        # No-op on macOS for now. Once maximise-detection lands, we'll
        # perform an AXPress on the zoom (green) button of the target
        # window, or set AXFullScreen=False for a fullscreen app.
        pass

    # ------------------------------------------------------------------
    # Helpers around pyobjc's slightly-awkward AX bridging.
    # ------------------------------------------------------------------
    def _copy_attr(self, element, attribute_name: str):
        """AXUIElementCopyAttributeValue wrapper that returns just the
        value (or None on error / missing)."""
        try:
            err, val = _AX.AXUIElementCopyAttributeValue(
                element, attribute_name, None
            )
        except Exception:
            return None
        if err != 0:
            return None
        return val

    def _unpack_ax_value(self, ax_value, kind: str):
        """Extract a CGPoint / CGSize from an AXValue.

        Returns a (float, float) tuple: (x, y) for a point,
        (width, height) for a size.
        """
        # Point/Size come back as AXValueRef; pyobjc offers a couple of
        # ways to get the underlying struct. We try the direct-attribute
        # path first (recent pyobjc gives you an NSPoint/NSSize object)
        # and fall back to AXValueGetValue.
        try:
            if kind == "point":
                if hasattr(ax_value, "x") and hasattr(ax_value, "y"):
                    return (float(ax_value.x), float(ax_value.y))
            elif kind == "size":
                if hasattr(ax_value, "width") and hasattr(ax_value, "height"):
                    return (float(ax_value.width), float(ax_value.height))
        except Exception:
            pass

        try:
            type_id = (
                _AX.kAXValueCGPointType if kind == "point"
                else _AX.kAXValueCGSizeType
            )
            success, unpacked = _AX.AXValueGetValue(ax_value, type_id, None)
            if not success or unpacked is None:
                return None
            if kind == "point":
                return (float(unpacked.x), float(unpacked.y))
            return (float(unpacked.width), float(unpacked.height))
        except Exception:
            return None
