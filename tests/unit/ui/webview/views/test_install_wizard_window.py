from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from src.models import Confirm, InstallStep, MsgLog
from src.ui.webview.views import install_wizard_window as wizard_module
from src.ui.webview.views.install_wizard_window import (
    InstallWizardApi,
    create_install_wizard,
)
from tests.unit.ui.webview.conftest import FakeWindow

# ────────────────────────────────────────────────────────────────| Fixtures |──


@pytest.fixture(autouse=True)
def no_real_install(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent begin_install()/begin_uninstall() from spawning a real
    background thread for every test in this module.

    Args:
        monkeypatch (pytest.MonkeyPatch): Replaces threading.Thread with a
            double whose start() is a no-op.
    """

    monkeypatch.setattr(
        "src.controllers.installer.threading.Thread", MagicMock()
    )


@pytest.fixture(autouse=True)
def stub_welcome_text(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent welcome_text() from touching the filesystem/bundled README.

    Args:
        monkeypatch (pytest.MonkeyPatch): Stubs the module-level function
            InstallerController.welcome_text() calls.
    """

    monkeypatch.setattr(
        "src.controllers.installer.welcome_text", lambda: "hello world"
    )


@pytest.fixture
def api(fake_window: FakeWindow) -> InstallWizardApi:
    """An InstallWizardApi bound to a FakeWindow, ready for use.

    Args:
        fake_window (FakeWindow): The window double to bind.

    Returns:
        InstallWizardApi: A bound Api instance, force=True (matches how
            __main__.py drives an explicit --install).
    """

    instance = InstallWizardApi(force=True)
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


class TestBindWindow:
    """bind_window() renders the Welcome step via the loaded event."""

    def test_loaded_event_renders_welcome(
        self, api: InstallWizardApi, fake_window: FakeWindow
    ) -> None:
        fake_window.events.loaded.fire()

        payload = _last_payload(fake_window)

        assert payload["step"] == "welcome"
        assert payload["welcome_text"] == "hello world"


# ─────────────────────────────────────────────────────────────| create_install_wizard |──


class TestCreateInstallWizard:
    """create_install_wizard() builds and binds the window via webview."""

    def test_passes_title_url_and_js_api(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake = FakeWindow()
        calls: list[dict] = []

        def fake_create_window(title: str, **kwargs: object) -> FakeWindow:
            calls.append({"title": title, **kwargs})
            return fake

        monkeypatch.setattr(
            wizard_module.webview, "create_window", fake_create_window
        )

        result = create_install_wizard(force=True)

        assert isinstance(result, InstallWizardApi)
        assert len(calls) == 1
        assert calls[0]["title"].endswith("Setup")
        assert calls[0]["js_api"] is result
        assert calls[0]["url"].endswith("/install_wizard/index.html")

    def test_raises_if_create_window_returns_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            wizard_module.webview, "create_window", lambda *a, **k: None
        )

        with pytest.raises(AssertionError):
            create_install_wizard()


# ─────────────────────────────────────────────────────────────────| Navigation |──


class TestNavigation:
    """advance()/back()/begin_install() move the wizard through its steps."""

    def test_advance_moves_to_options(
        self, api: InstallWizardApi, fake_window: FakeWindow
    ) -> None:
        api.advance()

        assert api.controller.step is InstallStep.OPTIONS

        payload = _last_payload(fake_window)
        assert payload["step"] == "options"

    def test_options_render_includes_desktop_shortcut_support(
        self, api: InstallWizardApi, fake_window: FakeWindow
    ) -> None:
        api.controller.supports_desktop_shortcut = True
        api.controller.set_desktop_shortcut(True)

        api.advance()

        payload = _last_payload(fake_window)
        assert payload["supports_desktop_shortcut"] is True
        assert payload["desktop_shortcut"] is True

    def test_back_returns_to_welcome(self, api: InstallWizardApi) -> None:
        api.advance()
        api.back()

        assert api.controller.step is InstallStep.WELCOME

    def test_begin_install_calls_controller_with_force(
        self, api: InstallWizardApi, fake_window: FakeWindow
    ) -> None:
        api.advance()
        api.begin_install()

        assert api.controller.step is InstallStep.INSTALLING

        payload = _last_payload(fake_window)
        assert payload["step"] == "installing"


# ─────────────────────────────────────────────────────────────────────| Finish |──


class TestFinish:
    """Finish-step rendering and its JS-callable Api."""

    def test_installer_finish_event_renders_finish_step(
        self, api: InstallWizardApi, fake_window: FakeWindow
    ) -> None:
        api.controller._step = InstallStep.FINISH  # type: ignore[attr-defined]

        api._bus.emit("installer.finish", None)

        payload = _last_payload(fake_window)
        assert payload["step"] == "finish"
        assert payload["run_first_scan"] is False

    def test_set_run_first_scan_updates_controller(
        self, api: InstallWizardApi
    ) -> None:
        api.set_run_first_scan(True)

        assert api.controller.options.run_first_scan is True

    def test_open_release_notes_opens_browser(
        self, api: InstallWizardApi, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "src.controllers.installer.release_notes_url",
            lambda version: "https://example.com/x",
        )

        calls: list[str] = []
        monkeypatch.setattr(
            "src.ui.webview.views.install_wizard_window.webbrowser.open",
            lambda url: calls.append(url),
        )

        api.open_release_notes()

        assert calls == ["https://example.com/x"]


# ─────────────────────────────────────────────────────────────────────| Log |──


class TestLog:
    """installer.log events forward to the page regardless of step."""

    def test_forwards_log_text(
        self, api: InstallWizardApi, fake_window: FakeWindow
    ) -> None:
        api._bus.emit("installer.log", MsgLog("hello"))

        payload = _last_payload(fake_window)
        assert payload["text"] == "hello"


# ─────────────────────────────────────────────────────────────────| Confirm |──


class TestConfirm:
    """Confirm gates push to the page and resolve_confirm() unblocks them."""

    def test_on_confirm_pushes_and_stores_pending(
        self, api: InstallWizardApi, fake_window: FakeWindow
    ) -> None:
        req = Confirm(prompt="Continue?", default=True)

        api._on_confirm(req)

        assert api._pending_confirm is req

        payload = _last_payload(fake_window)
        assert payload["prompt"] == "Continue?"
        assert "event" not in payload

    def test_resolve_confirm_sets_result_and_event(
        self, api: InstallWizardApi
    ) -> None:
        req = Confirm(prompt="Continue?", default=True)
        api._pending_confirm = req

        api.resolve_confirm(True)

        assert req.result is True
        assert req.event.is_set()
        assert api._pending_confirm is None


# ────────────────────────────────────────────────────────────| Close guard |──


class TestOnClosing:
    """_on_closing() vetoes only while installing and not yet closable."""

    def test_allows_close_before_installing(
        self, api: InstallWizardApi
    ) -> None:
        assert api._on_closing() is None

    def test_vetoes_while_installing_and_not_closable(
        self, api: InstallWizardApi
    ) -> None:
        api.advance()
        api.begin_install()

        assert api.controller.step is InstallStep.INSTALLING
        assert api._on_closing() is False

    def test_allows_once_closable(self, api: InstallWizardApi) -> None:
        api.advance()
        api.begin_install()
        api.controller._closable = True  # type: ignore[attr-defined]

        assert api._on_closing() is None


# ─────────────────────────────────────────────────────────────────────| close |──


class TestClose:
    def test_destroys_the_window(
        self, api: InstallWizardApi, fake_window: FakeWindow
    ) -> None:
        api.close()

        assert fake_window.destroyed is True
