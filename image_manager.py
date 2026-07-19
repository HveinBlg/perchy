"""Loads pet images from a folder and rotates them on a timer.

Two ingestion sources, checked on every scan:

- Loose files in the assets/pets/ folder itself (``*.png``, ``*.gif``, ...)
- ``.perchy-pack`` archives dropped into the same folder. Each pack is a
  zip file with:

      pack.json         (manifest: name, author, version, image list)
      preview.png       (optional pack thumbnail)
      LICENSE.txt       (optional embedded license)
      images/           (folder containing the actual pet sprites)

  Packs are extracted on demand to a platform-appropriate cache
  directory (Application Support / AppData Local / ~/.cache) and their
  images join the rotation pool alongside loose files.

Both sources are rescanned every ``rescan_seconds``, so buying a new
pack and dropping the .perchy-pack file next to Perchy is enough --
no restart, no menu, the new characters just start showing up.
"""

from __future__ import annotations

import json
import platform
import random
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Dict, List, Optional

from qt_compat import QObject, QTimer, pyqtSignal, QPixmap

SUPPORTED_EXTS = {".png", ".gif", ".jpg", ".jpeg", ".webp", ".bmp"}
PACK_EXT = ".perchy-pack"


# ---------------------------------------------------------------------------
# Pack file handling
# ---------------------------------------------------------------------------
def _cache_root() -> Path:
    """Where extracted pack contents live.

    Follows each OS's usual per-user cache location so we don't pollute
    the user's home dir or the app folder itself. Packs live here until
    the pack file's mtime changes (indicating a re-purchase / update)
    or the user manually clears the cache.
    """
    system = platform.system()
    if system == "Windows":
        base = Path.home() / "AppData" / "Local"
    elif system == "Darwin":
        base = Path.home() / "Library" / "Caches"
    else:
        base = Path.home() / ".cache"
    cache = base / "Perchy" / "PackCache"
    cache.mkdir(parents=True, exist_ok=True)
    return cache


def _extract_pack(pack_path: Path) -> Optional[Path]:
    """Extract ``pack_path`` to a versioned cache dir. Returns the extract
    dir, or None if the pack is malformed.

    The cache key encodes the pack's mtime, so re-releasing a pack with
    the same filename triggers a fresh extraction on the next scan
    rather than serving stale contents.
    """
    try:
        mtime_ns = pack_path.stat().st_mtime_ns
    except OSError:
        return None

    cache_key = f"{pack_path.stem}_{mtime_ns}"
    extract_dir = _cache_root() / cache_key

    if extract_dir.exists():
        return extract_dir

    # New / updated pack -- clean up stale versions of this same pack
    # (same stem, different mtime) so the cache doesn't grow forever.
    for old in _cache_root().glob(f"{pack_path.stem}_*"):
        if old != extract_dir:
            shutil.rmtree(old, ignore_errors=True)

    extract_dir.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(pack_path, "r") as zf:
            # Guard against zip-slip: refuse absolute paths / .. traversal
            for name in zf.namelist():
                target = (extract_dir / name).resolve()
                if not str(target).startswith(str(extract_dir.resolve())):
                    raise ValueError(f"Unsafe path in pack: {name}")
            zf.extractall(extract_dir)
    except (zipfile.BadZipFile, ValueError, OSError):
        # Malformed pack -- remove the empty cache dir and pretend we
        # never saw it, so a bad pack doesn't kill image loading.
        shutil.rmtree(extract_dir, ignore_errors=True)
        return None

    return extract_dir


def _read_manifest(extract_dir: Path) -> Dict:
    """Return the ``pack.json`` contents as a dict, or {} if absent/bad."""
    manifest_path = extract_dir / "pack.json"
    if not manifest_path.exists():
        return {}
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _pack_images(extract_dir: Path) -> List[Path]:
    """List image files in the ``images/`` subdirectory of an extracted pack."""
    images_dir = extract_dir / "images"
    if not images_dir.is_dir():
        return []
    return sorted(
        p
        for p in images_dir.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS
    )


# ---------------------------------------------------------------------------
# Main image manager
# ---------------------------------------------------------------------------
class ImageManager(QObject):
    """Merges loose PNGs and installed packs into one rotation pool."""

    # Emits the newly-picked QPixmap, or None when the pool is empty.
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
        # Cache of pack manifests, keyed by pack file path. Populated by
        # _refresh_list(); currently unused by the UI but exposed via
        # installed_packs() for future 'pack picker' features.
        self._pack_manifests: Dict[Path, Dict] = {}

        self._refresh_list()
        self._pick_next(emit=True)

        self.rotate_timer = QTimer(self)
        self.rotate_timer.setInterval(max(1, rotate_seconds) * 1000)
        self.rotate_timer.timeout.connect(lambda: self._pick_next(emit=True))
        self.rotate_timer.start()

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
        """Skip to the next image immediately (test / hotkey helper)."""
        self._pick_next(emit=True)

    def installed_packs(self) -> List[Dict]:
        """Return a list of manifest dicts for every loaded pack.

        Useful for future UI: a menu that lists 'installed content'.
        """
        return list(self._pack_manifests.values())

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _refresh_list(self) -> None:
        """Rebuild the image pool from loose files + .perchy-pack archives."""
        files: List[Path] = []
        self._pack_manifests = {}

        try:
            entries = list(self.assets_dir.iterdir())
        except FileNotFoundError:
            self._images = []
            return

        # 1) loose image files
        for p in entries:
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS:
                files.append(p)

        # 2) packs
        for p in entries:
            if p.is_file() and p.suffix.lower() == PACK_EXT:
                extract_dir = _extract_pack(p)
                if extract_dir is None:
                    _log(f"skipped malformed pack: {p.name}")
                    continue
                manifest = _read_manifest(extract_dir)
                if manifest:
                    self._pack_manifests[p] = manifest
                files.extend(_pack_images(extract_dir))

        self._images = sorted(set(files))

    def _on_rescan(self) -> None:
        had_none = not self._images
        self._refresh_list()
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
            pool = [p for p in self._images if p != self._current]
            candidate = random.choice(pool) if pool else self._images[0]

        self._current = candidate
        if emit:
            pix = QPixmap(str(candidate))
            self.image_changed.emit(pix if not pix.isNull() else None)


def _log(msg: str) -> None:
    """Diagnostic message when a pack is bad. Written to stderr so it
    surfaces in `python main.py` sessions but is invisible when the app
    is launched via run.bat / pythonw (which is what we want)."""
    try:
        sys.stderr.write(f"[perchy] {msg}\n")
    except Exception:
        pass
