#!/bin/bash
set -euo pipefail

# pywebview's Qt/QtWebEngine backend (PySide6, pulled in via uv/pyproject.toml)
# needs these X11 client libraries at runtime - confirmed via `ldd` against a
# real build; none of this is pulled in by the PySide6 wheels themselves.
# patchelf and ccache are Nuitka's Linux build prerequisites (same as CI).
sudo apt-get update -qq
sudo apt-get install -y -qq \
  ripgrep \
  libxkbfile1 \
  libxcb-cursor0 \
  libxcb-icccm4 \
  libxcb-image0 \
  libxcb-keysyms1 \
  libxcb-render-util0 \
  libxcb-shape0 \
  libxcb-util1 \
  libxcb-xkb1 \
  libxkbcommon-x11-0 \
  libasound2t64 \
  libdbus-1-3 \
  libegl1 \
  libgbm1 \
  libgl1 \
  libxcb-dri3-0 \
  libxcomposite1 \
  libxdamage1 \
  libxfixes3 \
  libxkbcommon0 \
  libxrandr2 \
  libxtst6 \
  libwayland-cursor0 \
  libwayland-egl1 \
  patchelf \
  ccache

# run setup script
./scripts/setup.sh
