from __future__ import annotations

import ctypes
import os
from typing import Any

# ─────────────────────────────────────────────────────────────────| Console |──
#
# ctypes.windll is only defined in typeshed's win32 stubs, so a static
# `ctypes.windll....` access fails mypy strict when checked under a
# non-Windows --platform (as the Linux CI job does) while a matching
# `# type: ignore` then trips `warn_unused_ignores` on the Windows CI job,
# which resolves the attribute fine. Routing through getattr() sidesteps the
# platform-conditional stub entirely so both jobs type-check cleanly.

_SW_HIDE = 0
_SW_SHOW = 5


def _kernel32() -> Any:
    return getattr(ctypes, "windll").kernel32


def _user32() -> Any:
    return getattr(ctypes, "windll").user32


def _owns_console() -> bool:
    """True when nothing but this app's own process tree is attached.

    PyInstaller's onefile bootloader on Windows always runs the frozen app
    as a child process of the bootloader, and both stay attached to the
    same console for the app's whole lifetime - so even a fresh
    double-click/shortcut launch reports 2 attached processes (bootloader
    parent + this one), never 1. Anything beyond that pair means the
    console is shared with something else, e.g. a terminal the user
    already had open, which this must never hide.
    """

    pids = (ctypes.c_uint * 8)()
    count = int(_kernel32().GetConsoleProcessList(pids, 8))
    attached = {int(pids[i]) for i in range(min(count, 8))}

    return attached <= {os.getpid(), os.getppid()}


def hide() -> None:
    """Hide the console window, but only if this process owns it exclusively.

    Leaves an existing parent terminal (e.g. a user-launched PowerShell or
    cmd session) untouched.
    """

    if not _owns_console():
        return

    hwnd = _kernel32().GetConsoleWindow()

    if hwnd:
        _user32().ShowWindow(hwnd, _SW_HIDE)


def show() -> None:
    """Reveal a console window previously hidden by hide().

    Safe to call even if the window was never hidden.
    """

    hwnd = _kernel32().GetConsoleWindow()

    if hwnd:
        _user32().ShowWindow(hwnd, _SW_SHOW)


def pause() -> None:
    """Keep a double-clicked console window open until the user dismisses it."""

    input("\nPress Enter to close...")
