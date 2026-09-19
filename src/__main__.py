from __future__ import annotations

import argparse
import configparser
import shutil
import sys
from typing import Literal

from src.config import load_config
from src.installer import install, is_installed, uninstall
from src.services.schedule import should_run_today

from . import APP_NAME, is_frozen

# ────────────────────────────────────────────────────────────────────| Main |──


def _pause_if_windows() -> None:
    if sys.platform == "win32":
        from src.platform.windows.console import pause

    else:
        from src.platform.linux.console import pause

    pause()


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


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser shared by both entry points."""

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

    return parser


def _run_scan_gui(cfg: configparser.ConfigParser) -> None:
    """Launch the Tkinter scan GUI. Identical for both binaries."""

    from .ui.gui.app import GitSentinelApp

    app = GitSentinelApp(cfg)
    app.mainloop()


def _run_gui_installer(
    mode: Literal["install", "uninstall"], *, force: bool = False
) -> None:
    """Run install()/uninstall() behind the windowed build's wizard/window.

    install runs through the multi-page InstallWizard; uninstall keeps the
    single-window InstallerWindow. The wizard's "Run first scan" relaunch is
    fired only after mainloop() returns, i.e. once Tk has fully unwound the
    closing window, so it can never race this process's own teardown.
    """

    if mode == "install":
        from .ui.gui.views.install_wizard.shell import InstallWizard

        wizard = InstallWizard(force=force)
        wizard.mainloop()
        wizard.controller.relaunch_if_requested()

    else:
        from .ui.gui.views.installer_window import InstallerWindow

        InstallerWindow().mainloop()


def main() -> None:
    """Console-subsystem entry point.

    install()/uninstall()/first-run use the terminal (this binary's console
    is never hidden - it is the intended UI for these flows).
    """

    args = _build_parser().parse_args()

    if args.install:
        install(force=True)
        _pause_if_windows()
        sys.exit(0)

    if args.uninstall:
        uninstall()
        _pause_if_windows()
        sys.exit(0)

    if is_frozen() and not is_installed():
        print(f"{APP_NAME}: first run detected - installing...")
        print()
        install()
        _pause_if_windows()
        sys.exit(0)

    cfg = load_config()

    if not should_run_today(cfg, force=args.force):
        sys.exit(0)

    _require_git()
    _run_scan_gui(cfg)


def main_gui() -> None:
    """Windowed-subsystem entry point.

    install()/uninstall()/first-run open InstallerWindow instead of using
    the terminal - this binary never allocates a console at all.
    """

    args = _build_parser().parse_args()

    if args.install:
        _run_gui_installer("install", force=True)
        sys.exit(0)

    if args.uninstall:
        _run_gui_installer("uninstall")
        sys.exit(0)

    if is_frozen() and not is_installed():
        _run_gui_installer("install")
        sys.exit(0)

    cfg = load_config()

    if not should_run_today(cfg, force=args.force):
        sys.exit(0)

    _require_git()
    _run_scan_gui(cfg)


if __name__ == "__main__":
    main()
