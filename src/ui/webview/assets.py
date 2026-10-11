from __future__ import annotations

from pathlib import Path

from src import frozen_data_dir

WEB_ROOT = Path(__file__).parent / "web"

# ───────────────────────────────────────────────────────────────| Resources |──


def web_root() -> Path:
    """Directory containing the pywebview page assets (HTML/CSS/JS).

    Resolves to the PyInstaller/Nuitka bundle's web/ subfolder when frozen
    (via frozen_data_dir(), the same mechanism src/installer.py uses for
    src/data/), or this package's own web/ directory during development.

    Returns:
        Path: Directory containing one subfolder per page (scan/,
            install_wizard/, uninstall/) plus shared/.
    """

    data_dir = frozen_data_dir()

    if data_dir is not None:
        return data_dir / "web"

    return WEB_ROOT


def page_url(name: str) -> str:
    """file:// URL for a page's index.html, suitable for create_window(url=).

    Args:
        name (str): Page subdirectory name (e.g. "scan").

    Returns:
        str: Absolute file:// URL.
    """

    return (web_root() / name / "index.html").resolve().as_uri()
