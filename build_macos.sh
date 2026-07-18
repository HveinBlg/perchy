#!/usr/bin/env bash
# Build a self-contained macOS .app that users can just download and
# double-click, no Python required. Uses PyInstaller.
#
# Usage:  ./build_macos.sh
# Output: dist/Perchy.app  (+ assets, 使用说明.txt copied alongside)
# Zip:    (cd dist && zip -r ../perchy-macos.zip Perchy.app 使用说明.txt assets)
set -euo pipefail

cd "$(dirname "$0")"

echo "=== Perchy build (macOS) ==="

# ---- venv ----
if [ ! -x ".venv/bin/python" ]; then
    echo "Creating .venv with default python3..."
    python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

# ---- deps ----
python -m pip install --upgrade pip >/dev/null
pip install -q -r requirements.txt pyinstaller

# ---- clean ----
rm -rf build dist

# ---- build ----
# --windowed      = no terminal window (macOS: creates .app bundle)
# --osx-bundle-id = reverse-DNS identifier for the app
# --noupx         = don't compress binaries (helps startup + avoids AV)
pyinstaller --clean --noconfirm \
    --name Perchy \
    --windowed \
    --noupx \
    --osx-bundle-identifier com.hveinblg.perchy \
    main.py

# ---- Info.plist tweaks: hide the app from Dock + Cmd-Tab ----
# LSUIElement=YES turns the app into a background "accessory" so it
# doesn't get a Dock icon. We ALSO set the activation policy at runtime
# (see main.py), but Info.plist is more reliable at launch time.
INFO_PLIST="dist/Perchy.app/Contents/Info.plist"
if [ -f "$INFO_PLIST" ]; then
    /usr/libexec/PlistBuddy -c "Delete :LSUIElement" "$INFO_PLIST" 2>/dev/null || true
    /usr/libexec/PlistBuddy -c "Add :LSUIElement bool true" "$INFO_PLIST"
fi

# ---- copy user-facing files ALONGSIDE the .app so users can edit them ----
# (Files inside the .app bundle are treated as read-only by macOS; put
# the assets folder + docs at the same level as the .app instead.)
cp -R assets dist/
[ -f "使用说明.txt" ]     && cp "使用说明.txt"     dist/
[ -f "使用说明_macOS.txt" ] && cp "使用说明_macOS.txt" dist/

# ---- optional: also wrap it as a .dmg (macOS-native distribution format) ----
# Users prefer .dmg on macOS: double-click mounts it, drag Perchy.app
# to /Applications, done. Uses hdiutil which is built into every macOS.
VERSION="${1:-dev-$(date -u +%Y%m%d-%H%M%S)}"

rm -rf dist/dmg-staging
mkdir -p dist/dmg-staging
cp -R dist/Perchy.app dist/dmg-staging/
cp -R dist/assets     dist/dmg-staging/
[ -f "dist/使用说明.txt" ]       && cp "dist/使用说明.txt"       dist/dmg-staging/ || true
[ -f "dist/使用说明_macOS.txt" ] && cp "dist/使用说明_macOS.txt" dist/dmg-staging/ || true
ln -s /Applications dist/dmg-staging/Applications

hdiutil create \
    -volname "Perchy $VERSION" \
    -srcfolder dist/dmg-staging \
    -ov \
    -format UDZO \
    "dist/Perchy-v${VERSION}-macos.dmg"

echo ""
echo "=== Build complete ==="
echo "Output:"
echo "  dist/Perchy.app                    (the app bundle)"
echo "  dist/Perchy-v${VERSION}-macos.dmg  (ready to share)"
