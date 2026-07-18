"""Loads pet images from a folder and rotates them on a timer.

The folder is rescanned periodically so you can drop in new images while
the pet is running and they'll enter the rotation automatically.
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap

SUPPORTED_EXTS = {".png", ".gif", ".jpg", ".jpeg", ".webp", ".bmp"}


class ImageManager(QObject):
    # Emits the newly-picked QPixmap, or None when the folder is empty.
    image_changed = pyqtSignal(object)

    def __init__(
        self,
        assets_dir: str = "assets/pets",
        rotate_seconds: int = 180,
        rescan_seconds: int = 10,
        parent=None,
    ):
        super().__init__(parent)
        self.assets_dir = Path(assets_dir)
        self.assets_dir.mkdir(parents=True, exist_ok=True)

        self._images: List[Path] = []
        self._current: Optional[Path] = None

        self._refresh_list()
        # Emit the initial pick (or None if folder is empty).
        self._pick_next(emit=True)

        # Rotation timer: swaps the image every rotate_seconds.
        self.rotate_timer = QTimer(self)
        self.rotate_timer.setInterval(max(1, rotate_seconds) * 1000)
        self.rotate_timer.timeout.connect(lambda: self._pick_next(emit=True))
        self.rotate_timer.start()

        # Rescan timer: notices when the user drops new images into the folder.
        self.scan_timer = QTimer(self)
        self.scan_timer.setInterval(max(1, rescan_seconds) * 1000)
        self.scan_timer.timeout.connect(self._on_rescan)
        self.scan_timer.start()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def current_pixmap(self) -> Optional[QPixmap]:
        if self._current is None:
            return None
        pix = QPixmap(str(self._current))
        return pix if not pix.isNull() else None

    def force_next(self) -> None:
        """Skip to the next image immediately (useful for testing / hotkey)."""
        self._pick_next(emit=True)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _refresh_list(self) -> None:
        try:
            files = sorted(
                p
                for p in self.assets_dir.iterdir()
                if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS
            )
        except FileNotFoundError:
            files = []
        self._images = files

    def _on_rescan(self) -> None:
        had_none = not self._images
        self._refresh_list()
        # If we previously had nothing to show and images just appeared,
        # push one out right away instead of waiting for the rotate timer.
        if had_none and self._images:
            self._pick_next(emit=True)

    def _pick_next(self, emit: bool = False) -> None:
        if not self._images:
            self._current = None
            if emit:
                self.image_changed.emit(None)
            return

        if len(self._images) == 1:
            candidate = self._images[0]
        else:
            # Never pick the same image twice in a row.
            pool = [p for p in self._images if p != self._current]
            candidate = random.choice(pool) if pool else self._images[0]

        self._current = candidate
        if emit:
            pix = QPixmap(str(candidate))
            self.image_changed.emit(pix if not pix.isNull() else None)
