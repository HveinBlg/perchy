"""Entry point for the desktop pet.

Run with:  python main.py
"""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from pet_window import PetWindow


def main() -> int:
    app = QApplication(sys.argv)
    # Don't quit when the pet is temporarily hidden (e.g. desktop is focused).
    app.setQuitAtLastWindowClosed(False)

    pet = PetWindow()
    pet.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
