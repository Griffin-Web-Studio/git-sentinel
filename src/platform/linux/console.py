from __future__ import annotations  # pragma: no cover - there's nothing to test

# ─────────────────────────────────────────────────────────────────| Console |──


def pause() -> None:  # pragma: no cover - there's nothing to test
    """No-op on Linux; a terminal window doesn't close on process exit."""


def hide() -> None:  # pragma: no cover - there's nothing to test
    """No-op on Linux; there's no console-subsystem window to hide."""


def show() -> None:  # pragma: no cover - there's nothing to test
    """No-op on Linux; there's no console-subsystem window to show."""
