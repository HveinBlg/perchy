"""Shared types for the platform-specific window trackers."""

from __future__ import annotations

from typing import NamedTuple


class WindowState(NamedTuple):
    """Everything the pet needs to know about the active window in one tick.

    - ``hwnd`` is an opaque platform-specific window handle used only for
      the restore-window action. On Windows it's a real HWND (int); on
      macOS we currently don't implement restore, so it can be 0.
    - ``left/top/right/bottom`` are the window's screen rectangle in
      the native coordinate system (top-left origin, DIP-pixels).
    - ``is_maximized`` is True when the window is in a "fills the
      screen" state that we should replace with the firecracker hint.
      On macOS this is currently always False (no maximise equivalent).
    """

    hwnd: int
    left: int
    top: int
    right: int
    bottom: int
    is_maximized: bool
