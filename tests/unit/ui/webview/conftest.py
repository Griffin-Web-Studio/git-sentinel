from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

# ───────────────────────────────────────────────────────────────| FakeWindow |──


class FakeEvent:
    """Stands in for pywebview's webview.event.Event.

    Mirrors the real class's __iadd__/call semantics closely enough for
    tests: a handler returning False vetoes (matches Event.set() returning
    True - i.e. "cancel" - when any handler returns False).
    """

    def __init__(self) -> None:
        self.handlers: list[Callable[..., Any]] = []

    def __iadd__(self, handler: Callable[..., Any]) -> FakeEvent:
        self.handlers.append(handler)
        return self

    def fire(self, *args: Any, **kwargs: Any) -> bool:
        """Call every registered handler; returns True if any vetoed (
        returned False), mirroring Event.set()'s return value."""

        results = [h(*args, **kwargs) for h in self.handlers]

        return False in results


class FakeEvents:
    def __init__(self) -> None:
        self.loaded = FakeEvent()
        self.closing = FakeEvent()


class FakeWindow:
    """Stands in for webview.Window: records evaluate_js() calls instead of
    driving a real native window - there's no headless-but-real option for
    WebView2 in CI, so Api classes are tested against this double instead.
    """

    def __init__(self) -> None:
        self.events = FakeEvents()
        self.evaluate_js_calls: list[str] = []
        self.destroyed = False

    def evaluate_js(self, script: str) -> None:
        self.evaluate_js_calls.append(script)

    def destroy(self) -> None:
        self.destroyed = True


@pytest.fixture
def fake_window() -> FakeWindow:
    """A FakeWindow double, fresh for each test."""

    return FakeWindow()
