#!/usr/bin/env bash
# git-sentinel build.sh - builds the Nuitka binary into dist/git-sentinel
# Run from the project root directory.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v uv &>/dev/null; then
  echo "ERROR: uv is not installed." >&2
  echo "       Install it from: https://docs.astral.sh/uv/getting-started/installation/" >&2
  echo "       or reopen this project in devcontainer where it will be" >&2
  echo "       installed automatically, along with other dependencies." >&2
  exit 1
fi

if [ ! -f "$SCRIPT_DIR/pyproject.toml" ]; then
  echo "ERROR: pyproject.toml not found in $SCRIPT_DIR" >&2
  exit 1
fi

echo "Syncing build dependencies..."
(cd "$SCRIPT_DIR" && uv sync --group dev)

mkdir -p "$SCRIPT_DIR/dist"

DATA_ARGS=(
  --include-data-files="$SCRIPT_DIR/src/data/git-sentinel.desktop=data/git-sentinel.desktop"
  --include-data-files="$SCRIPT_DIR/src/data/git-sentinel.svg=data/git-sentinel.svg"
  --include-data-files="$SCRIPT_DIR/README.md=data/README.md"
  --include-data-files="$SCRIPT_DIR/CHANGELOG.md=data/CHANGELOG.md"
)

echo "Building console binary (this may take a few minutes)..."
(cd "$SCRIPT_DIR" && uv run python -m nuitka \
  --onefile \
  --output-filename=git-sentinel \
  --output-dir=build \
  --enable-plugin=tk-inter \
  --include-package=src.config.migrations \
  --assume-yes-for-downloads \
  "${DATA_ARGS[@]}" \
  git-sentinel)

cp "$SCRIPT_DIR/build/git-sentinel" "$SCRIPT_DIR/dist/git-sentinel"

if [ ! -f "$SCRIPT_DIR/dist/git-sentinel" ]; then
  echo "ERROR: build failed - dist/git-sentinel not found" >&2
  exit 1
fi

echo "Building windowed binary (this may take a few minutes)..."
(cd "$SCRIPT_DIR" && uv run python -m nuitka \
  --onefile \
  --output-filename=git-sentinel-gui \
  --output-dir=build \
  --enable-plugin=tk-inter \
  --include-package=src.config.migrations \
  --assume-yes-for-downloads \
  "${DATA_ARGS[@]}" \
  git-sentinel-gui)

cp "$SCRIPT_DIR/build/git-sentinel-gui" "$SCRIPT_DIR/dist/git-sentinel-gui"

if [ ! -f "$SCRIPT_DIR/dist/git-sentinel-gui" ]; then
  echo "ERROR: build failed - dist/git-sentinel-gui not found" >&2
  exit 1
fi

echo "Build complete → $SCRIPT_DIR/dist/git-sentinel, $SCRIPT_DIR/dist/git-sentinel-gui"
