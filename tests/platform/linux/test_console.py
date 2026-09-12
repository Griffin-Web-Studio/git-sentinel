from __future__ import annotations

from src.platform.linux.console import pause

# ──────────────────────────────────────────────────────────────────| Console |──
#
# Linux never opens a console-subsystem window for the app, so pause() is a
# no-op. The only thing worth asserting is that calling it doesn't raise.


def test_pause_is_a_noop() -> None:
    assert pause() is None
