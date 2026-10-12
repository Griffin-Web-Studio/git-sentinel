from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from src.models import Confirm, MsgLog
from src.ui.webview.views import uninstall_window as uninstall_module
from src.ui.webview.views.uninstall_window import (
    UninstallWindowApi,
    create_uninstall_window,
)
from tests.unit.ui.webview.conftest import FakeWindow

# ────────────────────────────────────────────────────────────────| Fixtures |──


@pytest.fixture(autouse=True)
def no_real_uninstall(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent begin_uninstall() from spawning a real background thread for
    every test in this module.

    Args:
        monkeypatch (pytest.MonkeyPatch): Replaces threading.Thread with a
            double whose start() is a no-op.
    """

    monkeypatch.setattr(
        "src.controllers.installer.threading.Thread", MagicMock()
    )


@pytest.fixture
def api(fake_window: FakeWindow) -> UninstallWindowApi:
    """A UninstallWindowApi bound to a FakeWindow, ready for use.

    Args:
        fake_window (FakeWindow): The window double to bind.

    Returns:
        UninstallWindowApi: A bound Api instance.
    """

    instance = UninstallWindowApi()
    instance.bind_window(fake_window)  # type: ignore[arg-type]

    return instance


def _last_payload(fake_window: FakeWindow) -> dict:
    """Decode the JSON payload from the most recent evaluate_js() call.

    Args:
        fake_window (FakeWindow): Window whose last dispatch call to decode.

    Returns:
        dict: The decoded payload argument.
    """

    script = fake_window.evaluate_js_calls[-1]
    _, _, rest = script.partition(", ")

    return json.loads(rest.rstrip(")"))


# ─────────────────────────────────────────────────────────────────────| Init |──


class TestInit:
    def test_not_started_before_any_click(
        self, api: UninstallWindowApi
    ) -> None:
        assert api._started is False
        assert api._done is False


# ─────────────────────────────────────────────────────────────| create_uninstall_window |──


class TestCreateUninstallWindow:
    """create_uninstall_window() builds and binds the window via webview."""

    def test_passes_title_url_and_js_api(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake = FakeWindow()
        calls: list[dict] = []

        def fake_create_window(title: str, **kwargs: object) -> FakeWindow:
            calls.append({"title": title, **kwargs})
            return fake

        monkeypatch.setattr(
            uninstall_module.webview, "create_window", fake_create_window
        )

        result = create_uninstall_window()

        assert isinstance(result, UninstallWindowApi)
        assert len(calls) == 1
        assert calls[0]["title"].endswith("Setup")
        assert calls[0]["js_api"] is result
        assert calls[0]["url"].endswith("/uninstall/index.html")

    def test_raises_if_create_window_returns_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            uninstall_module.webview, "create_window", lambda *a, **k: None
        )

        with pytest.raises(AssertionError):
            create_uninstall_window()


# ────────────────────────────────────────────────────────────| begin_uninstall |──


class TestBeginUninstall:
    def test_starts_background_work_and_marks_started(
        self, api: UninstallWindowApi, fake_window: FakeWindow
    ) -> None:
        api.begin_uninstall()

        assert api._started is True
        assert "uninstall.started" in fake_window.evaluate_js_calls[-1]


# ─────────────────────────────────────────────────────────────────────| Log |──


class TestLog:
    def test_forwards_log_text(
        self, api: UninstallWindowApi, fake_window: FakeWindow
    ) -> None:
        api._bus.emit("installer.log", MsgLog("hello"))

        payload = _last_payload(fake_window)
        assert payload["text"] == "hello"


# ─────────────────────────────────────────────────────────────────| Confirm |──


class TestConfirm:
    def test_on_confirm_pushes_and_stores_pending(
        self, api: UninstallWindowApi, fake_window: FakeWindow
    ) -> None:
        req = Confirm(prompt="Remove config and state data?", default=False)

        api._on_confirm(req)

        assert api._pending_confirm is req

        payload = _last_payload(fake_window)
        assert payload["prompt"] == "Remove config and state data?"
        assert "event" not in payload

    def test_resolve_confirm_sets_result_and_event(
        self, api: UninstallWindowApi
    ) -> None:
        req = Confirm(prompt="Remove config and state data?", default=False)
        api._pending_confirm = req

        api.resolve_confirm(True)

        assert req.result is True
        assert req.event.is_set()
        assert api._pending_confirm is None


# ─────────────────────────────────────────────────────────────────| Finish |──


class TestOnFinish:
    def test_marks_done_and_pushes_finish(
        self, api: UninstallWindowApi, fake_window: FakeWindow
    ) -> None:
        api._bus.emit("installer.finish", None)

        assert api._done is True
        assert "uninstall.finish" in fake_window.evaluate_js_calls[-1]


# ────────────────────────────────────────────────────────────| Close guard |──


class TestOnClosing:
    """_on_closing() vetoes only while uninstalling and not yet done."""

    def test_allows_close_before_starting(
        self, api: UninstallWindowApi
    ) -> None:
        assert api._on_closing() is None

    def test_vetoes_while_in_progress_and_not_done(
        self, api: UninstallWindowApi
    ) -> None:
        api.begin_uninstall()

        assert api._on_closing() is False

    def test_allows_once_done(self, api: UninstallWindowApi) -> None:
        api.begin_uninstall()
        api._bus.emit("installer.finish", None)

        assert api._on_closing() is None


# ─────────────────────────────────────────────────────────────────────| close |──


class TestClose:
    def test_destroys_the_window(
        self, api: UninstallWindowApi, fake_window: FakeWindow
    ) -> None:
        api.close()

        assert fake_window.destroyed is True
