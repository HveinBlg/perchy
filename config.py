"""User-tunable settings for the desktop pet."""

# Pet display size in pixels (width, height). The image will be scaled to
# fit inside this box while keeping its aspect ratio.
PET_SIZE = (180, 180)

# How many pixels of the pet's bottom overlap the window's top edge.
# Larger value => pet sits deeper into the title bar.
OVERLAP = 30

# How often the pet image is randomly swapped out, in seconds.
# Default = 3 minutes.
ROTATE_SECONDS = 180

# How often we rescan `assets/pets/` for newly added images, in seconds.
# Lets you drop new PNGs in without restarting.
RESCAN_SECONDS = 10

# How often we poll the active window's position, in milliseconds.
# 30ms ~= 33 FPS, gives smooth follow while dragging.
TRACK_INTERVAL_MS = 30

# Folder to load pet images from. Relative to the project root.
# Supported: .png .gif .jpg .jpeg .webp (transparent PNG recommended).
ASSETS_DIR = "assets/pets"

# If True, the pet is decoration only: mouse clicks pass through it to the
# window below (so it doesn't block the title bar). Set to False later if
# you want to add click interactions.
CLICK_THROUGH = True

# Horizontal position of the pet along the window's top edge.
# 0.0 = flush left, 0.5 = centered, 1.0 = flush right.
HORIZONTAL_ANCHOR = 0.5
