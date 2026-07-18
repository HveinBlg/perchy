# Perchy — Desktop Pet (Windows)

A tiny cartoon character that sits on top of your **currently active window**
and follows it as you move it around. Every few minutes it changes into a
different image picked from `assets/pets/`.

Inspired by the "little guy sitting on your window" screenshots you see on 小红书.

## For end users (just want to run it)

Grab the latest Windows zip from the
[Releases page](https://github.com/HveinBlg/perchy/releases), extract it,
and double-click `perchy.exe`. No Python or git required. See
`使用说明.txt` inside the zip for a full Chinese quickstart.

Everything below is for **developers** who want to hack on the source or
build their own zip.

## What it does

- Tracks the **currently focused** top-level window (via Win32 `GetForegroundWindow`).
- Draws a **transparent, always-on-top, frameless** window with your pet image.
- Positions the pet centered on the window's top edge, with its "butt" resting
  on the title bar.
- **Click-through**: the pet doesn't block clicks on the title bar / close button.
- **No focus stealing**: uses `WS_EX_NOACTIVATE`.
- **No taskbar entry / no Alt-Tab entry**: uses `WS_EX_TOOLWINDOW`.
- Skips the desktop, taskbar, and minimized/cloaked windows.
- **Auto-rotates** the pet image every N minutes (configurable).
- **Hot-reloads** the images folder every 10s, so you can drop new PNGs
  in while it's running.

## Requirements

- Windows 10 or 11
- **Python 3.9 or newer** (recommended: 3.11 or 3.12)
  - Python 3.7 / 3.8 will NOT work — PyQt6 has no wheels for them and
    building from source usually fails on Windows.
  - Download from https://www.python.org/downloads/windows/ and be sure
    to tick "Add Python to PATH" during install.

## Install

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Add pet images

Drop any number of PNG / GIF / JPG / WEBP files into `assets/pets/`.
Transparent-background PNGs look best. The pet will randomly cycle through
every image in that folder.

## Run

Three ways, pick whichever suits you:

### 1. Foreground (dev mode)

Good for tweaking `config.py` and seeing output/errors.

```powershell
python main.py
```

Closing the terminal (or Ctrl+C) will kill the pet.

### 2. Background (recommended for daily use)

```powershell
start pythonw main.py
```

`pythonw` is Python's windowless launcher. `start` detaches it from the
terminal so you can close the console and the pet keeps running. Stop it
via Task Manager (find `pythonw.exe`) or by running `stop.bat`.

### 3. Double-click `run.bat`

Just double-click `run.bat` in the project folder. Same effect as
option 2, no terminal required.

### Auto-start at Windows login

Press `Win+R`, type `shell:startup`, hit Enter. That opens your Startup
folder. Right-click `run.bat` in the project folder → **Create shortcut**,
then move the shortcut into that Startup folder. From next login onward,
the pet appears automatically. Delete the shortcut to disable.

Focus any window and you should see the pet perched on its top edge.
Move / resize the window and the pet follows.

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

## Exit

- **If launched via `python main.py`**: `Ctrl+C` in the terminal.
- **If launched via `pythonw` / `run.bat`**: double-click `stop.bat`, or
  open Task Manager, find `pythonw.exe`, end task.

A tray-icon quit menu is on the todo list.

## Building a release yourself

Two options:

### Option A: local build (fastest)

```powershell
build.bat
```

Produces `dist\perchy\` containing `perchy.exe`, `assets/pets/`,
`使用说明.txt`, and `stop.bat`. Zip it up and send:

```powershell
Compress-Archive -Path dist\perchy -DestinationPath perchy-windows-x64.zip -Force
```

### Option B: let GitHub Actions build it

Push a tag matching `v*` and CI will build a Windows zip and attach it
to a new GitHub Release automatically:

```powershell
git tag v1.0.0
git push --tags
```

Watch the run under the repo's **Actions** tab, then grab the zip from
**Releases** when it turns green.

## Known limits

- Exclusive-fullscreen apps (some games) draw over the pet.
- Only the currently focused window has a pet; unfocused windows don't.
- Windows only — the tracker uses Win32 / DWM directly.
- The bundled `.exe` isn't code-signed, so Windows SmartScreen will show
  "Windows protected your PC" on first launch. Click **More info →
  Run anyway**. If you have a code-signing certificate you can sign
  `dist\perchy\perchy.exe` in a post-build step.
