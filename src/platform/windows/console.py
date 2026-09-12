from __future__ import annotations

# ─────────────────────────────────────────────────────────────────| Console |──
#
# hide()/show() and the console-ownership/ConPTY-owner-polling machinery that
# used to live here are gone: the console-subsystem build now always shows
# its console (that's the point of it), and the windowed-subsystem build
# never allocates one to hide in the first place. See git-sentinel-gui and
# src/ui/gui/views/installer_window.py.


def pause() -> None:
    """Keep a double-clicked console window open until the user dismisses it."""

    input("\nPress Enter to close...")
