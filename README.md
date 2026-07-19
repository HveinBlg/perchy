<h1 align="center">Perchy</h1>

<p align="center">
  <b>A desktop pet that follows your active window.</b><br>
  <i>Switch Chrome, cat follows. Switch VS Code, cat's there. Switch Slack, cat's still with you.</i>
</p>

<p align="center">
  <a href="https://github.com/HveinBlg/perchy/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License MIT"></a>
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS-lightgrey" alt="Platform">
  <a href="https://github.com/HveinBlg/perchy/releases/latest"><img src="https://img.shields.io/github/v/release/HveinBlg/perchy" alt="Latest release"></a>
  <a href="https://github.com/HveinBlg/perchy/stargazers"><img src="https://img.shields.io/github/stars/HveinBlg/perchy?style=social" alt="Stars"></a>
</p>

<p align="center">
  <a href="https://github.com/HveinBlg/perchy/releases/latest">Download</a>
  &nbsp;·&nbsp;
  <a href="#support-the-project">Support</a>
</p>

<p align="center">
  <!-- Demo GIF: record your screen switching between 3-4 apps and drop it here. -->
  <!-- Save as demo.gif at the repo root and reference it with <img src="demo.gif" width="600"/> -->
  <i>[Demo GIF — replace with a 5-10s screen recording of the cat following windows]</i>
</p>

---

## What makes it special

- **Follows the active window.** The cat sits on whatever app you're
  using right now, not on a fixed screen position.
- **Click-through.** Clicks pass through to the buttons underneath,
  so the title bar still works normally.
- **No taskbar or Dock icon, no focus stealing, no Alt-Tab entry.**
  The pet stays out of the way.
- **DIY-friendly, free forever.** Drop any transparent PNG into
  `assets/pets/` and it becomes your pet.
- **`.perchy-pack` support.** One-file installs for character packs
  (any zip with a `pack.json` and an `images/` folder works).
- **Cross-platform.** Windows 10/11, macOS 11+, and a special legacy
  build for macOS 10.15 Catalina.
- **Firecracker easter egg on Windows.** Maximise a window and the
  cat turns into a swinging string of firecrackers. Click them to
  restore the window and bring the cat back.

Perchy is inspired by the "little guy sitting on your window"
screenshots on 小红书, turned into something that actually runs.

---

## Download

| Your OS | File | Notes |
|---|---|---|
| Windows 10 / 11 | [`perchy-vX.Y.Z-windows-x64.zip`](https://github.com/HveinBlg/perchy/releases/latest) | Extract, run `perchy.exe`. |
| macOS 11+ (Big Sur through Sequoia) | [`Perchy-vX.Y.Z-macos.dmg`](https://github.com/HveinBlg/perchy/releases/latest) | Mount, drag `Perchy.app` and `assets/` to `/Applications`. |
| macOS 10.15 Catalina | [`Perchy-vX.Y.Z-macos-legacy.dmg`](https://github.com/HveinBlg/perchy/releases/latest) | PyQt5-based build for older Macs. |

**macOS reminder:** first launch needs Accessibility permission
(System Settings → Privacy & Security → Accessibility → add Perchy).

---

## Support the project

Perchy is MIT-licensed and free forever. If it made your day less
grumpy, consider any of these:

- **Star this repo** — signals to me and others that it's worth
  maintaining.
- **[Report bugs or request features](https://github.com/HveinBlg/perchy/issues).**
  Real-world signal beats guesswork.
- **Contribute pet art** — open a PR adding your PNGs to
  `assets/pets/community/`.
- **Buy a character pack** *(coming soon)* — official packs will
  live on the [Releases page](https://github.com/HveinBlg/perchy/releases). Buying them literally pays
  for the next round of art commissions.
- **Tip me** *(TBD)* — 爱发电 / Ko-fi links coming when the project
  gets its first 100 stars.

---

## For developers

Perchy is 100% MIT — fork it, ship your own, or contribute back.

### Running from source

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS:    source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Python 3.9 or newer required. 3.11 or 3.12 recommended.

### Convenience launchers (Windows)

- `run.bat` — start Perchy in the background (no terminal).
- `stop.bat` — kill every Perchy process (handles both source-mode
  `python.exe` and the packaged `perchy.exe`).

### What lives where

```
main.py                     entry point; chdir + macOS Dock hiding
pet_window.py               transparent overlay, image rotation, positioning
image_manager.py            scans assets/pets/, rotates every N minutes,
                            loads .perchy-pack archives
qt_compat.py                PyQt6-first / PyQt5-fallback shim; lets one
                            source tree build against either Qt version
active_window_tracker/      platform-dispatching active-window tracker
    __init__.py             chooses _windows or _macos at import time
    _base.py                WindowState NamedTuple
    _windows.py             Win32 + DWM via ctypes
    _macos.py               AppKit + AXUIElement via pyobjc
config.py                   user-tunable settings
run.bat, stop.bat           Windows launchers
build.bat / build_macos.sh  local packaging scripts
.github/workflows/          three-platform CI (Windows + macOS +
                            macOS legacy)
```

### Tuning

Edit `config.py`:

| Setting              | What it does                                                 |
| -------------------- | ------------------------------------------------------------ |
| `PET_SIZE`           | Pet max width and height in pixels (image scales to fit).     |
| `OVERLAP`            | Float in (0,1] = fraction of sprite height dipped into title bar (0.5 = bisected). Int ≥ 2 = fixed pixel offset. |
| `CLAMP_TO_SCREEN`    | If True, keep pet fully on-screen for maximised windows.      |
| `ROTATE_SECONDS`     | How often the pet image swaps (default 180s = 3 min).         |
| `RESCAN_SECONDS`     | How often we pick up newly added images (default 10s).        |
| `TRACK_INTERVAL_MS`  | Follow polling interval; lower = smoother, higher = lighter.  |
| `HORIZONTAL_ANCHOR`  | 0.0 = left edge, 0.5 = center, 1.0 = right edge.              |
| `CLICK_THROUGH`      | Whether clicks pass through the pet.                          |

### macOS compatibility matrix

| Your macOS       | Which dmg                       | Notes                          |
| ---------------- | ------------------------------- | ------------------------------ |
| 15 Sequoia       | `-macos.dmg`                    | PyQt6, native performance.     |
| 14 Sonoma        | `-macos.dmg`                    | PyQt6.                         |
| 13 Ventura       | `-macos.dmg`                    | PyQt6.                         |
| 12 Monterey      | `-macos.dmg`                    | PyQt6.                         |
| 11 Big Sur       | `-macos.dmg`                    | PyQt6, minimum for modern build. |
| **10.15 Catalina** | **`-macos-legacy.dmg`**       | **PyQt5, Python 3.9.**         |
| 10.14 or older   | not supported                   | Apple dropped signing / Python. |

### Building a release yourself

**Option A: local build**

- Windows: `build.bat` — produces `dist\perchy\perchy.exe` and friends.
- macOS: `./build_macos.sh v1.2.3` — produces `dist/Perchy.app` and a `.dmg`.

**Option B: tag and push, let GitHub Actions do it**

```bash
git tag v1.4.0
git push --tags
```

CI builds Windows, macOS modern, and macOS legacy in parallel and
attaches all three artifacts to the release page automatically.

---

## License

**Engine code:** [MIT](LICENSE). Free to fork, modify, and redistribute.

**Character art (`.perchy-pack` files):** each pack carries its own
license text embedded inside. Buying a pack does not automatically
grant redistribution rights — see the pack's own `LICENSE.txt`.

**Bundled sample cats** (the nine English Shorthair PNGs in
`assets/pets/`): AI-generated, provided for personal use with the
engine.

---

## Contributing

Contributions welcome, especially:

- **Pet art** — drop your PNGs into a subfolder under `assets/pets/`
  (say `assets/pets/community-shibas/`) and open a PR.
- **Bug reports** with screenshots and `python main.py` output.
- **Linux support** — the tracker is a platform-dispatching package;
  add `active_window_tracker/_linux.py` and it slots in.
- **Docs** — especially English translations of the Chinese guides.

---

## Known limits

- **Exclusive-fullscreen apps** (some games) draw over the pet. This
  is an OS limitation. Use borderless-windowed mode instead.
- **Unsigned binaries** — Windows SmartScreen and macOS Gatekeeper
  will complain on first launch. On Windows: click *More info →
  Run anyway*. On macOS: right-click the app → *Open* → click
  *Open* on the confirmation dialog (one-time bypass). Signing
  costs $99-$500 per year and we won't invest until the project
  has real traction.
- **macOS 10.15 legacy** carries all the modern build's features
  except that Apple removed some APIs; we haven't hit any yet but
  file an issue if you do.
- **`is_maximized` is always False on macOS** — macOS doesn't have
  Windows' clean "maximised" state, so the firecracker restore hint
  is Windows-only for now.
- **No single-instance lock** — running Perchy twice gets you two
  cats. On the todo list.
