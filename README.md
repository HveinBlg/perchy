# Desktop Pet (Windows)

A tiny cartoon character that sits on top of your **currently active window**
and follows it as you move it around. Every few minutes it changes into a
different image picked from `assets/pets/`.

Inspired by the "little guy sitting on your window" screenshots you see on 小红书.

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

```powershell
python main.py
```

Focus any window and you should see the pet perched on its top edge.
Move / resize the window and the pet follows.

## Tuning

Edit `config.py`:

| Setting              | What it does                                                 |
| -------------------- | ------------------------------------------------------------ |
| `PET_SIZE`           | Pet width & height in pixels (image is scaled to fit).        |
| `OVERLAP`            | How many pixels the pet's bottom dips into the title bar.     |
| `ROTATE_SECONDS`     | How often the pet image swaps (default 180s = 3 min).         |
| `RESCAN_SECONDS`     | How often we pick up newly added images (default 10s).        |
| `TRACK_INTERVAL_MS`  | Follow polling interval; lower = smoother, higher = lighter.  |
| `HORIZONTAL_ANCHOR`  | 0.0 = left edge, 0.5 = center, 1.0 = right edge.              |
| `CLICK_THROUGH`      | Whether clicks pass through the pet.                          |

## Exit

Kill from the terminal (`Ctrl+C`) or via Task Manager (looks for `python.exe`).
A tray-icon quit menu is on the todo list.

## Known limits

- Exclusive-fullscreen apps (some games) draw over the pet.
- Only the currently focused window has a pet; unfocused windows don't.
- Windows only — the tracker uses Win32 / DWM directly.
