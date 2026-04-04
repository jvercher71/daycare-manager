#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# build_mac.sh — Build Daycare Manager v2 as a macOS .app and wrap in a .dmg
#
# Requirements:
#   - Run this script on a Mac
#   - Python venv activated: source venv/bin/activate
#   - create-dmg installed: brew install create-dmg
#
# Usage:
#   cd /path/to/daycare-manager
#   bash installer/build_mac.sh
# ─────────────────────────────────────────────────────────────────────────────
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
DIST_DIR="$ROOT/dist"
APP_NAME="Daycare Manager v2"
APP_BUNDLE="$DIST_DIR/Daycare Manager v2.app"
DMG_PATH="$DIST_DIR/DaycareManagerV2.dmg"

echo "📦 Building Daycare Manager v2 for macOS..."

# Install build deps
pip install pyinstaller rumps pillow -q

# Clean previous build
rm -rf "$ROOT/build" "$DIST_DIR"

# Run PyInstaller
cd "$ROOT"
pyinstaller installer/daycare_manager.spec --noconfirm

echo "✅ .app bundle created at: $APP_BUNDLE"

# ── Create .dmg ───────────────────────────────────────────────────────────────
if command -v create-dmg &>/dev/null; then
    echo "💿 Creating .dmg installer..."
    create-dmg \
        --volname "$APP_NAME" \
        --volicon "installer/icon.icns" \
        --window-pos 200 120 \
        --window-size 600 400 \
        --icon-size 100 \
        --icon "$APP_NAME.app" 150 180 \
        --hide-extension "$APP_NAME.app" \
        --app-drop-link 450 180 \
        --no-internet-enable \
        "$DMG_PATH" \
        "$DIST_DIR/"
    echo "✅ DMG created: $DMG_PATH"
else
    echo "⚠️  create-dmg not found. Install with: brew install create-dmg"
    echo "   The .app bundle is ready at: $APP_BUNDLE"
fi

echo ""
echo "Done! Distribute: $DMG_PATH"
echo "Note: Users may need to right-click → Open on first launch (no code signing)."
