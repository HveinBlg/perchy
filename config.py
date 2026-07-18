"""User-tunable settings for the desktop pet."""

# Pet display size in pixels (width, height). The image will be scaled to
# fit inside this box while keeping its aspect ratio.
PET_SIZE = (180, 180)

# How much of the pet dips INTO the window (i.e. below the window's top
# edge). Accepts two formats:
#
#   * float in (0.0, 1.0]  = fraction of the pet's own height. This is
#                            the recommended mode because the split
#                            stays consistent no matter which sprite is
#                            showing (tall waving cat vs. squat sleeping
#                            cat both bisect the title bar the same way).
#       0.5 -> half above the title bar, half below (the "sitting on
#              the edge" look).
#       0.33 -> one-third of the pet inside, two-thirds hanging above.
#       1.0 -> pet sits fully inside the title bar.
#
#   * int >= 2  = absolute pixel offset (the pet's bottom overlaps the
#                 title bar by exactly that many px). Provided for
#                 backward compat / power users who want a fixed dip
#                 regardless of sprite size.
OVERLAP = 0.5

# When the pet's ideal position would push its top edge above the top of
# the screen (typical for maximised windows whose title bar is already
# at y=0), what should we do?
#   True  = clamp so the pet stays fully visible on-screen even if that
#           breaks the OVERLAP rule for that particular frame.
#   False = obey OVERLAP strictly; the pet's upper half may extend above
#           the screen (invisible) when the active window is docked to
#           the top of the display.
CLAMP_TO_SCREEN = True

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
# 0.85 sits the pet in the right corner: out of the way of the app icon /
# title text on the left, but not covering the min/max/close buttons on
# the far right. Change to 0.15 for a left-corner perch instead.
HORIZONTAL_ANCHOR = 0.85
