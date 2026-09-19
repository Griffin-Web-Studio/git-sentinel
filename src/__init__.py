from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# ────────────────────────────────────────────────────────────────────| Meta |──

APP_VERSION = "0.2.1"
APP_NAME = "git-sentinel"
GITLAB_URL = "https://gitlab.com/griffin-web-studio/garage/git-sentinel"

# ──────────────────────────────────────────────────────────| Platform paths |──

TMP_DIR = Path(tempfile.gettempdir())
HOME_DIR = Path.home()

if sys.platform == "win32":  # pragma: no cover - Windows only
    from src.platform.windows.paths import conf_dir, ssh_sock_dir, state_dir

else:
    from src.platform.linux.paths import conf_dir, ssh_sock_dir, state_dir

CONF_DIR = conf_dir(HOME_DIR, APP_NAME)
STATE_DIR = state_dir(HOME_DIR, APP_NAME)
SSH_SOCK_DIR = ssh_sock_dir(TMP_DIR, APP_NAME)

CONF_FILE = CONF_DIR / "settings.ini"
LOCK_FILE = STATE_DIR / "last-run-date"

# ────────────────────────────────────────────────────────────| Packaging |──


def is_frozen() -> bool:
    """True when running as a packaged binary (PyInstaller or Nuitka).

    PyInstaller sets sys.frozen; Nuitka never does, and instead injects a
    __compiled__ global into every module it compiles. This module is
    always part of a Nuitka-compiled program, so checking its own globals
    here reflects the whole build.

    Returns:
        bool: True when packaged, False in a source checkout.
    """

    return getattr(sys, "frozen", False) or "__compiled__" in globals()


def frozen_data_dir() -> Path | None:
    """Directory holding this build's bundled data/ subfolder, if any.

    Resolves PyInstaller's sys._MEIPASS extraction directory, or - for
    Nuitka - the directory of sys.executable. Nuitka's __compiled__.
    containing_dir is a compile-time constant (wherever `nuitka` happened to
    be invoked from) and is useless at runtime on another machine, so it is
    not used here. sys.executable is what's actually usable: on a standalone
    build it's the bundled interpreter shipped next to the data/ folder, and
    on a onefile build it's the per-run extraction directory the payload
    (data files included) was unpacked into - confirmed against a real
    Nuitka onefile build, since this is the opposite of how PyInstaller
    treats sys.executable/sys.argv[0] (see _current_binary() in installer.py).

    Returns:
        Path | None: The bundle's root directory, or None in a source
            checkout.
    """

    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)

    if "__compiled__" in globals():
        return Path(sys.executable).resolve().parent

    return None
