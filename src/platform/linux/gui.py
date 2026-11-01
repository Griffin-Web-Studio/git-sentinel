from __future__ import annotations

import os
import subprocess
from pathlib import Path

# ─────────────────────────────────────────────────────────────────| Helpers |──


def open_file(path: Path) -> None:  # pragma: no cover - no custom logic
    """Open *path* with the default MIME application.

    Args:
        path (Path): file (like report) path
    """

    subprocess.Popen(["xdg-open", str(path)])


def configure_webengine() -> None:
    """Disable QtWebEngine's GPU path when running under Wayland.

    On some Wayland setups (seen with the proprietary NVIDIA driver) the GPU
    path fails to initialise and the window opens briefly, then vanishes
    while the process lingers. Software rendering is ample for this UI, so
    GPU rendering is turned off there. X11 sessions, and any explicit
    QT_QPA_PLATFORM choice other than Wayland, are left untouched.

    Must run before QtWebEngine initialises, i.e. before webview.start().
    """

    platform = os.environ.get("QT_QPA_PLATFORM", "")
    on_wayland = bool(os.environ.get("WAYLAND_DISPLAY")) and (
        not platform or platform.startswith("wayland")
    )
    flags = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "")

    if on_wayland and "--disable-gpu" not in flags.split():
        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
            f"{flags} --disable-gpu".strip()
        )
