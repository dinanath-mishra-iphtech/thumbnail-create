#!/bin/bash
# ─────────────────────────────────────────────
#  run-thumbnail.command
#  Double-click this file on Mac to run the
#  thumbnail tool on the input/ folder.
# ─────────────────────────────────────────────

# Move to the folder where this script lives
cd "$(dirname "$0")"

echo "========================================"
echo "  🖼️  WebP Thumbnail Creator"
echo "========================================"
echo ""
echo "📥 Input folder  : $(pwd)/input"
echo "📤 Output folder : $(pwd)/output"
echo ""

# Run the thumbnail tool (default mode: input/ → output/)
python3 thumbnail.py

echo ""
echo "========================================"
echo "  ✅ Done! Check the output/ folder."
echo "========================================"
echo ""
echo "Press any key to close this window..."
read -n 1
