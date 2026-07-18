"""Platform-dispatching active window tracker.

Exposes a single ``ActiveWindowTracker`` class + ``WindowState`` named
tuple, with the actual implementation chosen at import time based on
``sys.platform``:

- Windows  -> Win32 + DWM via ctypes
- macOS    -> AppKit + Accessibility API via pyobjc
- other    -> stub that always says "no active window"
"""

from __future__ import annotations

import sys

from ._base import WindowState

if sys.platform.startswith("win"):
    from ._windows import ActiveWindowTracker  # noqa: F401
elif sys.platform == "darwin":
    from ._macos import ActiveWindowTracker  # noqa: F401
else:
    from typing import Optional

    class ActiveWindowTracker:  # type: ignore[no-redef]
        """No-op tracker for platforms we don't support yet (Linux, etc)."""

        def __init__(self, self_hwnd_getter=None):
            sys.stderr.write(
                f"[perchy] Platform '{sys.platform}' isn't supported yet; "
                "the pet will stay hidden.\n"
            )

        def get_active_window_state(self) -> Optional[WindowState]:
            return None

        def restore_window(self, hwnd) -> None:
            pass


__all__ = ["ActiveWindowTracker", "WindowState"]
