#!/bin/bash
set -euo pipefail

# pywebview's Qt/QtWebEngine backend (PySide6, pulled in via uv/pyproject.toml)
# needs these X11 client libraries at runtime - confirmed via `ldd` against a
# real build; none of this is pulled in by the PySide6 wheels themselves.
sudo apt-get update -qq
sudo apt-get install -y -qq \
  libxkbfile1 \
  libxcb-cursor0 \
  libxcb-icccm4 \
  libxcb-image0 \
  libxcb-keysyms1 \
  libxcb-render-util0 \
  libxcb-shape0 \
  libxcb-util1

# run setup script
./scripts/setup.sh
