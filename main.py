"""Entry point for the desktop pet.

Run from source:   python main.py
Run when frozen:   double-click perchy.exe
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication


def _app_dir() -> Path:
    """Directory that contains this app's config + assets, whether we're
    running from source or from a PyInstaller onedir bundle.

    - Source mode:   next to main.py
    - Frozen mode:   next to perchy.exe (so users can edit assets/pets/
                     and drop their own PNGs alongside the binary)
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def main() -> int:
    # chdir so config.py's relative paths ("assets/pets") resolve the same
    # regardless of how we were launched (terminal cwd, Explorer double
    # click, Startup shortcut, etc).
    os.chdir(_app_dir())

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
