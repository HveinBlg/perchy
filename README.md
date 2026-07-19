<h1 align="center">🐱 Perchy</h1>

<p align="center">
  <b>A desktop pet that follows your active window.</b><br>
  <i>Switch Chrome → cat follows. Switch VS Code → cat's there. Switch Slack → cat's still with you.</i>
</p>

<p align="center">
  <a href="https://github.com/HveinBlg/perchy/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License MIT"></a>
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS-lightgrey" alt="Platform">
  <a href="https://github.com/HveinBlg/perchy/releases/latest"><img src="https://img.shields.io/github/v/release/HveinBlg/perchy" alt="Latest release"></a>
  <a href="https://github.com/HveinBlg/perchy/stargazers"><img src="https://img.shields.io/github/stars/HveinBlg/perchy?style=social" alt="Stars"></a>
</p>

<p align="center">
  <a href="docs/使用指南.md">📘 中文说明</a>
  ·
  <a href="https://github.com/HveinBlg/perchy/releases/latest">⬇️ Download</a>
  ·
  <a href="docs/项目复盘.md">📝 21 pitfalls we hit</a>
  ·
  <a href="#-support-the-project">💰 Support</a>
</p>

<p align="center">
  <!-- Demo GIF: record your screen switching between 3-4 apps and drop it here. -->
  <!-- Save as docs/demo.gif and reference it with <img src="docs/demo.gif" width="600"/> -->
  <i>[Demo GIF — replace with a 5-10s screen recording of the cat following windows]</i>
</p>

---

## ✨ What makes it special

- 🎯 **Follows the active window** — the cat sits on whatever app you're using RIGHT NOW, not on a fixed screen position
- 🖱️ **Click-through** — clicks pass through the cat to the buttons underneath, so the title bar still works normally
- 👻 **No taskbar / Dock icon**, **no focus stealing**, **no Alt-Tab entry** — the pet stays out of your way
- 🎨 **DIY-friendly, free forever** — drop any transparent PNG into `assets/pets/` and it's your pet
- 📦 **`.perchy-pack` support** — one-file installs for character packs; make your own with `create_pack.py`
- 🌍 **Cross-platform** — Windows 10/11, macOS 11+, and a special legacy build for macOS 10.15 Catalina
- 🧨 **Windows: firecracker easter egg** — maximise a window and the cat turns into a swinging string of firecrackers; click them to restore

Perchy is **inspired by the "little guy sitting on your window" screenshots** on 小红书, turned into something that actually runs.

---

## 📥 Download

The end-user guide with install screenshots + FAQ:
**[docs/使用指南.md](docs/使用指南.md)** (Chinese)

| Your OS | File | Notes |
|---|---|---|
| Windows 10 / 11 | [`perchy-vX.Y.Z-windows-x64.zip`](https://github.com/HveinBlg/perchy/releases/latest) | Extract → `perchy.exe` |
| macOS 11+ (Big Sur → Sequoia) | [`Perchy-vX.Y.Z-macos.dmg`](https://github.com/HveinBlg/perchy/releases/latest) | Mount → drag app + assets to `/Applications` |
| macOS 10.15 Catalina | [`Perchy-vX.Y.Z-macos-legacy.dmg`](https://github.com/HveinBlg/perchy/releases/latest) | PyQt5-based build for older Macs |

**macOS reminder**: first launch needs Accessibility permission (System Settings → Privacy & Security → Accessibility → add Perchy).

---

## 🌟 Star History

<a href="https://star-history.com/#HveinBlg/perchy&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=HveinBlg/perchy&type=Date&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=HveinBlg/perchy&type=Date" />
    <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=HveinBlg/perchy&type=Date" />
  </picture>
</a>

---

## 💰 Support the project

Perchy is **MIT-licensed and free forever**. If it made your day less
grumpy, consider any of these:

- ⭐ **Star this repo** — signals to me + others that it's worth
  maintaining
- 🐛 **[Report bugs / request features](https://github.com/HveinBlg/perchy/issues)** — the more real-world signal, the better
- 🎨 **Contribute pet art** — open a PR adding your PNGs to
  `assets/pets/community/`
- 💰 **Buy a character pack** *(coming soon)* — official packs will
  live in the [Releases page](https://github.com/HveinBlg/perchy/releases). Buying them literally pays for the next
  round of art commissions
- ☕ **Tip me** *(TBD)* — 爱发电 / Ko-fi links coming when the project
  gets its first 100 stars

---

## 🛠️ For developers

Perchy is 100% MIT — fork it, ship your own, or contribute back.

### Running from source

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS:    source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Python 3.9+ required (3.11 / 3.12 recommended).

### Convenience launchers (Windows)

- `run.bat` — start Perchy in the background (no terminal)
- `stop.bat` — kill every Perchy process (handles both source-mode
  `python.exe` and the packaged `perchy.exe`)

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
create_pack.py              CLI: package a folder of PNGs into a
                            .perchy-pack for distribution
run.bat, stop.bat           Windows launchers
build.bat / build_macos.sh  local packaging scripts
.github/workflows/          three-platform CI (Windows + macOS +
                            macOS legacy)
```

### Tuning

Edit `config.py`:

| Setting              | What it does                                                 |
| -------------------- | ------------------------------------------------------------ |
| `PET_SIZE`           | Pet max width & height in pixels (image is scaled to fit).    |
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
| 15 Sequoia       | `-macos.dmg`                    | PyQt6, native performance      |
| 14 Sonoma        | `-macos.dmg`                    | PyQt6                          |
| 13 Ventura       | `-macos.dmg`                    | PyQt6                          |
| 12 Monterey      | `-macos.dmg`                    | PyQt6                          |
| 11 Big Sur       | `-macos.dmg`                    | PyQt6, minimum for modern build|
| **10.15 Catalina** | **`-macos-legacy.dmg`**       | **PyQt5, Python 3.9**          |
| 10.14 or older   | not supported                   | Apple dropped signing / Python |

### Building a release yourself

Option A: local build

- **Windows**: `build.bat` — produces `dist\perchy\perchy.exe` and friends
- **macOS**: `./build_macos.sh v1.2.3` — produces `dist/Perchy.app` + a `.dmg`

Option B: tag & push, let GitHub Actions do it

```bash
git tag v1.4.0
git push --tags
```

The CI builds Windows + macOS (modern) + macOS (legacy) in parallel and attaches all three artifacts to the release page automatically.

---

## 📄 License

**Engine code**: [MIT](LICENSE) — free to fork, modify, and redistribute.

**Character art** (`.perchy-pack` files): each pack carries its own license text embedded inside. Buying a pack does not automatically grant redistribution rights — see the pack's own `LICENSE.txt`.

**Bundled sample cats** (the 9 English Shorthair PNGs in `assets/pets/`): AI-generated, provided for personal use with the engine.

---

## 📚 More docs

- **[使用指南](docs/使用指南.md)** — end-user quickstart with FAQ (Chinese)
- **[项目复盘](docs/项目复盘.md)** — 21 concrete pitfalls we hit in a
  single day, with root causes + fixes + reusable lessons
- **[角色包制作规范](docs/角色包制作规范.md)** — how to author a
  `.perchy-pack` for distribution (image sizes, naming, manifest,
  licensing templates)
- **[商店文案](docs/商店文案.md)** — copy templates for selling packs on
  淘宝 / 爱发电 / Gumroad / Product Hunt

---

## 🐣 Contributing

Contributions welcome, especially:

- **Pet art** — drop your PNGs into a subfolder under `assets/pets/`
  (say `assets/pets/community-shibas/`) and open a PR
- **Bug reports** with screenshots + `python main.py` output
- **Linux support** — the tracker is a platform-dispatching package;
  add an `active_window_tracker/_linux.py` and it'll slot in
- **Docs** — especially English translations of the Chinese guides

---

## 🚧 Known limits

- **Exclusive-fullscreen** apps (some games) draw over the pet — this
  is an OS limitation, use borderless-windowed mode instead.
- **Unsigned binaries** — Windows SmartScreen and macOS Gatekeeper will
  complain on first launch. Bypass instructions in
  [使用指南](docs/使用指南.md). Signing costs $99-$500/year and we
  won't invest until the project has real traction.
- **macOS 10.15 legacy** carries all the modern build's features
  except that Apple removed some APIs; we haven't hit any yet but
  file an issue if you do.
- **`is_maximized` is always False on macOS** — macOS doesn't have
  Windows' clean "maximised" state, so the firecracker restore hint
  is Windows-only for now.
- **No single-instance lock** — running Perchy twice gets you two
  cats. On the todo list.
