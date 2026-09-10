from __future__ import annotations

from src.platform.linux.console import hide, pause, show

# ──────────────────────────────────────────────────────────────────| Console |──
#
# Linux never opens a console-subsystem window for the app, so all of these
# are no-ops. The only thing worth asserting is that calling them doesn't
# raise.


def test_pause_is_a_noop() -> None:
    assert pause() is None


def test_hide_is_a_noop() -> None:
    assert hide() is None


def test_show_is_a_noop() -> None:
    assert show() is None
