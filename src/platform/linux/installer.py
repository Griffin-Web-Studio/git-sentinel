from __future__ import annotations

import shutil
from pathlib import Path

from src import APP_NAME

# ───────────────────────────────────────────────────────────────────| Paths |──

_LOCAL = Path.home() / ".local"
BIN_DIR = _LOCAL / "bin"
BINARY_DST = BIN_DIR / APP_NAME

AUTOSTART_DIR = Path.home() / ".config" / "autostart"
AUTOSTART_FILE = AUTOSTART_DIR / f"{APP_NAME}.desktop"

APPS_DIR = _LOCAL / "share" / "applications"
LAUNCHER_FILE = APPS_DIR / f"{APP_NAME}.desktop"

ICONS_DIR = _LOCAL / "share" / "icons" / "hicolor" / "scalable" / "apps"
ICON_FILE = ICONS_DIR / f"{APP_NAME}.svg"

# ───────────────────────────────────────────────| Install steps (protected) |──


def install_icon(resource: Path) -> str:
    """Create icons dir, and copy the icon inside.

    Args:
        resource (Path): Path to the bundled SVG icon.
    """

    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(resource), str(ICON_FILE))

    return f"Installed icon\t\t→ {ICON_FILE}"


def install_autostart(desktop_content: str) -> str:
    """Create autostart dir, and write the autostart desktop entry.

    Args:
        desktop_content (str): Rendered .desktop file content.
    """

    AUTOSTART_DIR.mkdir(
        parents=True, exist_ok=True
    )  # create autostart dir (if missing)

    AUTOSTART_FILE.write_text(desktop_content)  # write autostart desktop entry

    return f"Registered autostart\t→ {AUTOSTART_FILE}"


def install_launcher(desktop_content: str) -> str:
    """add app launcher entry into launcher

    Args:
        desktop_content (str): Rendered .desktop file content.
    """

    APPS_DIR.mkdir(parents=True, exist_ok=True)  # create apps dir (if missing)

    LAUNCHER_FILE.write_text(desktop_content)  # write launcher desktop entry

    return f"Registered launcher\t→ {LAUNCHER_FILE}"


# ─────────────────────────────────────────────────────────| Uninstall steps |──


def remove_binary() -> str:
    """removes the binary"""

    BINARY_DST.unlink()

    return f"Removed binary\t\t→ {BINARY_DST}"


def remove_icon() -> str:
    """remove icon"""

    if ICON_FILE.exists():
        ICON_FILE.unlink()

        return f"Removed icon\t\t→ {ICON_FILE}"

    return f"Icon not found\t\t→ {ICON_FILE}  (skipping)"


def remove_autostart() -> str:
    """remove autostart entry"""

    if AUTOSTART_FILE.exists():
        AUTOSTART_FILE.unlink()

        return f"Removed autostart\t→ {AUTOSTART_FILE}"

    return f"Autostart not found\t→ {AUTOSTART_FILE}  (skipping)"


def remove_launcher() -> str:
    """remove launcher entry"""

    if LAUNCHER_FILE.exists():
        LAUNCHER_FILE.unlink()

        return f"Removed launcher\t→ {LAUNCHER_FILE}"

    return f"Launcher not found\t→ {LAUNCHER_FILE}  (skipping)"
