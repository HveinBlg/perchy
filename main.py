"""Entry point for the desktop pet.

Run from source:            python main.py
Windows frozen bundle:      double-click perchy.exe
macOS frozen bundle:        double-click Perchy.app
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication


def _app_dir() -> Path:
    """Directory that contains this app's config + assets, whether we're
    running from source or from a PyInstaller bundle.

    - Source mode:                        next to main.py
    - Frozen mode (Windows onedir):       next to perchy.exe
    - Frozen mode (macOS .app bundle):    next to Perchy.app (i.e. the
                                          directory the user extracted
                                          the zip into), so users can
                                          drop their own PNGs into
                                          ``assets/pets/`` right beside
                                          the .app.
    """
    if getattr(sys, "frozen", False):
        exe_path = Path(sys.executable).resolve()
        # On macOS a frozen bundle lives at
        #   .../Perchy.app/Contents/MacOS/Perchy
        # We want to expose assets next to Perchy.app, so climb three
        # levels up to escape the bundle.
        if sys.platform == "darwin":
            parts = exe_path.parts
            if len(parts) >= 4 and parts[-3:] == ("Contents", "MacOS", exe_path.name):
                return Path(*parts[:-3]).parent
        return exe_path.parent
    return Path(__file__).resolve().parent


def _configure_macos_dock_visibility() -> None:
    """Make Perchy a background 'accessory' app on macOS.

    Prevents a Python / Perchy icon from appearing in the Dock or in
    Cmd+Tab, which is what you'd expect from a floating pet. Safe to
    call before QApplication is constructed.
    """
    if sys.platform != "darwin":
        return
    try:
        from AppKit import NSApplication  # type: ignore[import-not-found]

        NSApp = NSApplication.sharedApplication()
        # NSApplicationActivationPolicyAccessory = 1
        # (no Dock icon, no menu bar, but can still show windows)
        NSApp.setActivationPolicy_(1)
    except Exception:
        # pyobjc missing / accessibility policies unavailable -- fine,
        # the app will just have an ordinary Dock icon.
        pass


def main() -> int:
    # chdir so config.py's relative paths ("assets/pets") resolve the same
    # regardless of how we were launched (terminal cwd, Explorer double
    # click, Startup shortcut, macOS Dock, etc).
    os.chdir(_app_dir())

    _configure_macos_dock_visibility()

    # Import AFTER chdir so ImageManager picks up the right folder on
    # first scan.
    from pet_window import PetWindow  # noqa: WPS433 (local import intentional)

    app = QApplication(sys.argv)
    # Don't quit when the pet is temporarily hidden (e.g. desktop is focused).
    app.setQuitOnLastWindowClosed(False)

    pet = PetWindow()
    pet.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
