#!/usr/bin/env python3
"""Package a folder of pet sprites into a distributable ``.perchy-pack``.

Usage examples:

    # Basic: package everything in ./shibas/ into shiba-pack.perchy-pack
    python create_pack.py \
        --name "柴犬合集" \
        --author "You" \
        --images ./shibas/ \
        --output shiba-pack

    # Full metadata + preview + license
    python create_pack.py \
        --name "Shiba Collection" \
        --author "Kvin Blg" \
        --version 1.0.0 \
        --description "12 poses of happy shibas" \
        --license "Commercial. Purchase grants personal-use rights only." \
        --preview ./shibas/cover.png \
        --images ./shibas/ \
        --output shiba-v1.0.0

The output file is a zip archive with the ``.perchy-pack`` extension.
Drop it into a user's ``assets/pets/`` folder and Perchy picks it up
on the next 10-second scan without a restart.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import List

SUPPORTED_EXTS = {".png", ".gif", ".jpg", ".jpeg", ".webp", ".bmp"}


def _slug(text: str) -> str:
    """Turn an arbitrary string into a URL-safe slug for the pack ID.

    Preserves ASCII letters and digits; everything else becomes an
    underscore. Non-ASCII (e.g. Chinese) input falls back to a
    generic ``pack`` slug so the ID stays predictable.
    """
    ascii_only = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return ascii_only if ascii_only else "pack"


def _collect_images(images_dir: Path) -> List[Path]:
    """Return sorted image files in ``images_dir`` (non-recursive)."""
    if not images_dir.is_dir():
        raise FileNotFoundError(f"images folder does not exist: {images_dir}")
    files = sorted(
        p
        for p in images_dir.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS
    )
    if not files:
        raise ValueError(f"no supported image files in {images_dir}")
    return files


def build(
    name: str,
    author: str,
    version: str,
    description: str,
    license_text: str,
    images_dir: Path,
    preview: Path | None,
    output: Path,
) -> Path:
    """Assemble the .perchy-pack archive. Returns the final output path."""
    image_files = _collect_images(images_dir)

    manifest = {
        "id": f"{_slug(author)}.{_slug(name)}",
        "name": name,
        "author": author,
        "version": version,
        "description": description,
        "license": license_text,
        "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "engine_min_version": "1.3.0",
        "image_count": len(image_files),
        "images": [f"images/{p.name}" for p in image_files],
    }

    # Force the extension so downstream tooling picks it up
    if output.suffix != ".perchy-pack":
        output = output.with_suffix(".perchy-pack")
    output.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # 1) manifest -- always the first entry so tools that only
        #    read one file get the fastest possible metadata read
        zf.writestr(
            "pack.json",
            json.dumps(manifest, ensure_ascii=False, indent=2),
        )

        # 2) sprites
        for img in image_files:
            zf.write(img, f"images/{img.name}")

        # 3) preview thumbnail (optional)
        if preview is not None:
            if not preview.exists():
                raise FileNotFoundError(f"preview image not found: {preview}")
            zf.write(preview, "preview.png")

        # 4) license text (human-readable copy of what's in manifest)
        zf.writestr("LICENSE.txt", license_text.strip() + "\n")

        # 5) short README for anyone poking at the zip directly
        zf.writestr(
            "README.txt",
            (
                f"Perchy character pack: {name}\n"
                f"Author: {author}\n"
                f"Version: {version}\n"
                f"Created: {manifest['created']}\n"
                f"Contains: {len(image_files)} images\n\n"
                "How to install:\n"
                "  Drop this .perchy-pack file into Perchy's "
                "assets/pets/ folder.\n"
                "  Perchy scans that folder every 10 seconds; the new "
                "characters will\n  join the rotation without a restart.\n\n"
                "Engine: https://github.com/HveinBlg/perchy\n"
            ),
        )

    return output


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="create_pack",
        description=(
            "Package a folder of pet sprite PNGs into a distributable "
            ".perchy-pack file for use with the Perchy desktop pet engine."
        ),
    )
    p.add_argument("--name", required=True, help="Human-readable pack name")
    p.add_argument("--author", required=True, help="Author display name")
    p.add_argument("--version", default="1.0.0", help="Semantic version")
    p.add_argument(
        "--description",
        default="",
        help="One-line description shown in future pack pickers",
    )
    p.add_argument(
        "--license",
        default=(
            "Proprietary. Personal use only. No redistribution without "
            "the author's written permission."
        ),
        help="License text embedded in the pack",
    )
    p.add_argument(
        "--images",
        type=Path,
        required=True,
        help="Folder containing pet sprite images (non-recursive)",
    )
    p.add_argument(
        "--preview",
        type=Path,
        default=None,
        help="Optional preview thumbnail (PNG recommended)",
    )
    p.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output path (.perchy-pack extension appended if missing)",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    try:
        output = build(
            name=args.name,
            author=args.author,
            version=args.version,
            description=args.description,
            license_text=args.license,
            images_dir=args.images,
            preview=args.preview,
            output=args.output,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"Created {output}")
    print(f"  Name        : {args.name}")
    print(f"  Author      : {args.author}")
    print(f"  Version     : {args.version}")
    print(f"  Size        : {output.stat().st_size / 1024:.1f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
