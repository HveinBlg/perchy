# Perchy — Desktop Pet (Windows + macOS)

A tiny cartoon character that sits on top of your **currently active window**
and follows it as you move it around. Every few minutes it changes into a
different image picked from `assets/pets/`.

Inspired by the "little guy sitting on your window" screenshots you see on 小红书.

## For end users (just want to run it)

**👉 Full walkthrough in Chinese: [docs/使用指南.md](docs/使用指南.md)**
(covers install, customisation, troubleshooting FAQ, and why you'd
want to run it in the first place).

Short version — grab the latest for your OS from the
[Releases page](https://github.com/HveinBlg/perchy/releases):

- **Windows**: download `perchy-vX.Y.Z-windows-x64.zip`, extract, double-click
  `perchy.exe`. Full quickstart in `使用说明.txt` inside the zip.
- **macOS (Big Sur 11 or newer)**: download
  `Perchy-vX.Y.Z-macos.dmg`. Built against PyQt6 + Python 3.12.
- **macOS (Catalina 10.15)**: download
  `Perchy-vX.Y.Z-macos-legacy.dmg`. Built against PyQt5 + Python 3.9
  with `LSMinimumSystemVersion=10.15`. Same features and UX as the
  modern build.

Either dmg: double-click to mount, drag `Perchy.app` **and** the
`assets` folder into the same location (e.g. `/Applications`), then
double-click `Perchy.app`. First launch needs Accessibility
permission — see `使用说明_macOS.txt` inside the disk image.

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

No Python or git required.

Everything below is for **developers** who want to hack on the source or
build their own zip.

## What it does

- Tracks the **currently focused** top-level window
  - Windows: Win32 `GetForegroundWindow` + DWM extended-frame-bounds
  - macOS: `NSWorkspace.frontmostApplication` + Accessibility API
    (`AXFocusedWindow`, `AXPosition`, `AXSize`)
- Draws a **transparent, always-on-top, frameless** window with your pet image.
- Positions the pet on the window's top edge, right-anchored by default,
  bisected by the title bar so half sits above and half inside.
- **Click-through**: the pet doesn't block clicks on the title bar / close button.
- **No focus stealing**: uses `WS_EX_NOACTIVATE` (Windows) /
  `WA_ShowWithoutActivating` (both).
- **No taskbar / Dock entry**: `WS_EX_TOOLWINDOW` on Windows,
  `LSUIElement=YES` + `NSApplicationActivationPolicyAccessory` on macOS.
- Skips the desktop, taskbar, and minimised/cloaked windows.
- **Auto-rotates** the pet image every N minutes (configurable).
- **Hot-reloads** the images folder every 10s, so you can drop new PNGs
  in while it's running.
- **Firecracker restore hint on maximised windows** — Windows only for now.
  On macOS the pet just stays in "cat mode" whether or not the window is
  zoomed.

## Requirements

- **Windows 10 or 11** (any recent hardware), OR
- **macOS 12+** (Apple Silicon or Intel; grants Accessibility permission)
- **Python 3.9 or newer** (recommended: 3.11 or 3.12)
  - Python 3.7 / 3.8 will NOT work — PyQt6 has no wheels for them and
    building from source usually fails on Windows.

## Install (from source)

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS:    source .venv/bin/activate
pip install -r requirements.txt
```

The `requirements.txt` conditionally installs pyobjc on macOS.

## Add pet images

Drop any number of PNG / GIF / JPG / WEBP files into `assets/pets/`.
Transparent-background PNGs look best. The pet will randomly cycle through
every image in that folder.

## Run

### Windows

**Foreground (dev mode)** — good for tweaking `config.py`, terminal shows errors:
```powershell
python main.py
```

**Background** — no terminal needed:
```powershell
start pythonw main.py
```
or just double-click `run.bat`. Stop with `stop.bat` or Task Manager
(→ `pythonw.exe`).

**Auto-start at login**: `Win+R` → `shell:startup` → drop a shortcut to
`run.bat` in that folder.

### macOS

**First-time**: run once and grant Accessibility permission:
```bash
python main.py
```
System Settings → Privacy & Security → Accessibility → add Perchy /
your terminal / your Python interpreter. **Without this, no windows are
tracked and you'll never see the cat.**

**Background** — the frozen `.app` hides itself from the Dock automatically.
When running from source you can either just leave `python main.py`
running in a terminal, or wrap it in a launchd `.plist` for auto-start.

**Auto-start at login**: System Settings → General → Login Items → `+`,
select `Perchy.app`.

**Quit**: Activity Monitor → search "Perchy" → force quit. (A menu-bar
quit item is on the todo list.)

## Tuning

Edit `config.py`:

| Setting              | What it does                                                 |
| -------------------- | ------------------------------------------------------------ |
| `PET_SIZE`           | Pet max width & height in pixels (image is scaled to fit).    |
| `OVERLAP`            | How much of the pet dips inside the window. Float in (0,1] = fraction of the sprite's height (0.5 = bisected by title bar). Int ≥ 2 = fixed pixel offset. |
| `CLAMP_TO_SCREEN`    | If True, keep pet fully on-screen for maximised windows.      |
| `ROTATE_SECONDS`     | How often the pet image swaps (default 180s = 3 min).         |
| `RESCAN_SECONDS`     | How often we pick up newly added images (default 10s).        |
| `TRACK_INTERVAL_MS`  | Follow polling interval; lower = smoother, higher = lighter.  |
| `HORIZONTAL_ANCHOR`  | 0.0 = left edge, 0.5 = center, 1.0 = right edge.              |
| `CLICK_THROUGH`      | Whether clicks pass through the pet.                          |

## Building a release yourself

### Option A: local build

**Windows**:
```powershell
build.bat
```
Produces `dist\perchy\` containing `perchy.exe`, `assets/pets/`,
`使用说明.txt`, and `stop.bat`. Zip it up:
```powershell
Compress-Archive -Path dist\perchy -DestinationPath perchy-windows-x64.zip -Force
```

**macOS**:
```bash
./build_macos.sh v1.2.2
```
Produces both `dist/Perchy.app` (raw bundle) and
`dist/Perchy-v1.2.2-macos.dmg` (compressed disk image ready to
share — double-click to mount, drag app to Applications). The version
string is only used for the DMG filename + Info.plist; pass whatever
tag you're building for.

### Option B: let GitHub Actions build both

Push a tag matching `v*` and CI will build a Windows zip AND a macOS zip
and attach both to a new GitHub Release automatically:
```bash
git tag v1.2.0
git push --tags
```
Watch progress under **Actions**, then grab the zips from **Releases**.

## Architecture

```
main.py                  entry point; chdir to app dir + macOS Dock hiding
pet_window.py            transparent overlay, image rotation, positioning
image_manager.py         scans assets/pets, rotates every N minutes
qt_compat.py             PyQt6-first / PyQt5-fallback shim so the same
                         source builds against either. Aliases PyQt5's
                         flat enums to PyQt6-style scoped ones so the
                         downstream code stays PyQt6-style.
active_window_tracker/   platform-dispatching active-window tracker
    __init__.py          picks _windows or _macos at import time
    _base.py             WindowState named tuple
    _windows.py          Win32 + DWM via ctypes
    _macos.py            AppKit + AXUIElement via pyobjc
config.py                user-tunable settings
run.bat, stop.bat        Windows convenience launchers
build.bat                Windows local build script
build_macos.sh           macOS local build script
```

### Modern vs legacy macOS builds

Everything except the Qt version is identical between the two macOS
builds. The `qt_compat.py` shim lets the same `pet_window.py` etc.
work against either PyQt5 or PyQt6:

- Modern build (`-macos.dmg`) installs PyQt6 into its bundled Python
  and never touches the PyQt5 branch of `qt_compat`.
- Legacy build (`-macos-legacy.dmg`) installs PyQt5 into its bundled
  Python 3.9 with `MACOSX_DEPLOYMENT_TARGET=10.15`, and
  `qt_compat` monkey-patches PyQt5's flat enums to look like PyQt6's
  scoped ones before any other module imports Qt symbols.

## Retrospective

The full one-day journey — 21 concrete pitfalls we hit, their root
causes, fixes, and lessons — is captured in Chinese here:

**[docs/项目复盘.md](docs/项目复盘.md)**

Categories:

- Environment & toolchain (Python 3.7 vs PyQt6, sandbox network limits)
- Image processing (premultiplied alpha, background detection)
- UI positioning (invisible padding, bisect logic, maximised-window sink)
- Code bugs (init order, Qt method typos)
- Git & branches (revert-then-merge conflicts, wrong-branch commits)
- Packaging & distribution (stop.bat vs perchy.exe, SmartScreen, dmg vs zip)
- macOS legacy support (PyQt5 fallback, LSMinimumSystemVersion)

## Known limits

- Exclusive-fullscreen apps (some games) draw over the pet.
- Only the currently focused window has a pet; unfocused windows don't.
- The bundled `.exe` / `.app` aren't code-signed:
  - **Windows** SmartScreen: click *More info → Run anyway*.
  - **macOS** Gatekeeper: right-click → *Open* on first launch.
- **macOS-specific**:
  - Requires **Accessibility permission** (System Settings → Privacy &
    Security → Accessibility) — this is a per-app permission and
    macOS doesn't offer any way to skip it.
  - `is_maximized` is always False on macOS today, so the firecracker
    restore hint doesn't show. macOS doesn't have Windows' clean
    "maximised" state; a proper detection needs to compare window
    bounds to the target screen's visible frame, and a proper
    "restore" needs to press the zoom (green) button via AXPress.
    Both are planned.
