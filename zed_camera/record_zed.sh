#!/bin/bash

# Navigate to the directory containing this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

echo "========================================"
echo "         ZED X MINI Recorder            "
echo "========================================"

uv run video_capture.py "$@"
