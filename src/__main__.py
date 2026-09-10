from __future__ import annotations

import argparse
import shutil
import sys

from src.config import load_config
from src.installer import install, is_installed, uninstall
from src.services.schedule import should_run_today

from . import APP_NAME

# ────────────────────────────────────────────────────────────────────| Main |──


def _pause_if_windows() -> None:
    if sys.platform == "win32":
        from src.platform.windows.console import pause

    else:
        from src.platform.linux.console import pause

    pause()


def _hide_console() -> None:
    if sys.platform == "win32":
        from src.platform.windows.console import hide

    else:
        from src.platform.linux.console import hide

    hide()


def _show_console() -> None:
    if sys.platform == "win32":
        from src.platform.windows.console import show

    else:
        from src.platform.linux.console import show

    show()


def _require_git() -> None:
    """Exit with a friendly message if git isn't on PATH.

    GitPython raises a raw ImportError deep in its own import machinery the
    moment anything imports it without a git executable available - by the
    time that happens it's too late to show anything but a traceback. Catch
    the missing prerequisite before importing anything that pulls GitPython
    in, and report it the way the GUI app would.
    """

    if shutil.which("git"):
        return

    message = (
        f"{APP_NAME} requires Git, but it wasn't found on PATH.\n\n"
        "Install Git from https://git-scm.com/downloads, then run "
        f"{APP_NAME} again."
    )

    try:
        import tkinter
        from tkinter import messagebox

        root = tkinter.Tk()
        root.withdraw()
        messagebox.showerror(APP_NAME, message)
        root.destroy()

    except Exception:
        print(message, file=sys.stderr)

    sys.exit(1)


def main() -> None:
    """Application entry point."""

    if getattr(sys, "frozen", False):
        _hide_console()

    parser = argparse.ArgumentParser(
        prog=APP_NAME,
        description=(
            "Daily git repository audit - reports uncommitted, unpushed, "
            "stashed, or stale work."
        ),
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Run even if the script has already run today.",
    )
    action = parser.add_mutually_exclusive_group()
    action.add_argument(
        "-i",
        "--install",
        action="store_true",
        help="Install (or reinstall) the binary, config, and autostart entry, "
        "then exit.",
    )
    action.add_argument(
        "--uninstall",
        action="store_true",
        help="Remove the binary, autostart entry, and optionally config/state, "
        "then exit.",
    )

    args = parser.parse_args()

    if args.install:
        _show_console()
        install(force=True)
        _pause_if_windows()
        sys.exit(0)

    if args.uninstall:
        _show_console()
        uninstall()
        _pause_if_windows()
        sys.exit(0)

    if getattr(sys, "frozen", False) and not is_installed():
        _show_console()
        print(f"{APP_NAME}: first run detected - installing...")
        print()
        install()
        _pause_if_windows()
        sys.exit(0)

    cfg = load_config()

    if not should_run_today(cfg, force=args.force):
        sys.exit(0)

    _require_git()

    from .ui.gui.app import GitSentinelApp

    app = GitSentinelApp(cfg)
    app.mainloop()


if __name__ == "__main__":
    main()
