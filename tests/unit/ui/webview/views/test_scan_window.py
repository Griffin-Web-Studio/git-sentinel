from __future__ import annotations

import configparser
import json
from pathlib import Path

import pytest

from src import APP_NAME, APP_VERSION
from src.config.migrate import MigrationStep
from src.models import GateHTTP, GateSSH, MsgFinish
from src.ui.webview.views import scan_window as scan_window_module
from src.ui.webview.views.scan_window import ScanWindowApi, create_scan_window
from tests.unit.ui.webview.conftest import FakeWindow

# ────────────────────────────────────────────────────────────────| Fixtures |──


@pytest.fixture(autouse=True)
def no_real_scan(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent start_scan from spawning a real background scan worker.

    Args:
        monkeypatch (pytest.MonkeyPatch): Replaces ScanController.start_scan
            with a spy for every test in this module.
    """

    monkeypatch.setattr(
        "src.controllers.scan.ScanController.start_scan", lambda self, cfg: None
    )


@pytest.fixture
def api(fake_window: FakeWindow) -> ScanWindowApi:
    """A ScanWindowApi bound to a FakeWindow, ready for use.

    Args:
        fake_window (FakeWindow): The window double to bind.

    Returns:
        ScanWindowApi: A bound Api instance.
    """

    instance = ScanWindowApi(configparser.ConfigParser())
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


def _ssh_req() -> GateSSH:
    return GateSSH(url="git@github.com:user/repo.git", repo="~/projects/repo")


def _http_req() -> GateHTTP:
    return GateHTTP(
        url="https://example.com/repo.git", repo="~/projects/repo", error="boom"
    )


# ─────────────────────────────────────────────────────────| create_scan_window |──


class TestCreateScanWindow:
    """create_scan_window() builds and binds the window via webview."""

    def test_passes_title_url_and_js_api(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Args:
        monkeypatch (pytest.MonkeyPatch): Replaces webview.create_window with
            a spy returning a FakeWindow.
        """

        fake = FakeWindow()
        calls: list[dict] = []

        def fake_create_window(title: str, **kwargs: object) -> FakeWindow:
            calls.append({"title": title, **kwargs})
            return fake

        monkeypatch.setattr(
            scan_window_module.webview, "create_window", fake_create_window
        )

        result = create_scan_window(configparser.ConfigParser())

        assert result is fake
        assert len(calls) == 1
        assert APP_NAME in calls[0]["title"]
        assert APP_VERSION in calls[0]["title"]
        assert isinstance(calls[0]["js_api"], ScanWindowApi)
        assert calls[0]["url"].endswith("/scan/index.html")

    def test_raises_if_create_window_returns_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            scan_window_module.webview,
            "create_window",
            lambda *a, **k: None,
        )

        with pytest.raises(AssertionError):
            create_scan_window(configparser.ConfigParser())


# ─────────────────────────────────────────────────────────────────| _on_loaded |──


class TestOnLoaded:
    """_on_loaded() dispatches to the migration dialog or starts the scan."""

    def test_starts_scan_when_no_pending_migrations(
        self, api: ScanWindowApi, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "src.ui.webview.views.scan_window.make_adapter", lambda: object()
        )
        monkeypatch.setattr(
            "src.ui.webview.views.scan_window.chain.pending",
            lambda adapter: [],
        )

        calls: list[object] = []
        monkeypatch.setattr(
            "src.controllers.scan.ScanController.start_scan",
            lambda self, cfg: calls.append(cfg),
        )

        api._on_loaded()

        assert len(calls) == 1

    def test_pushes_migration_pending_when_steps_exist(
        self,
        api: ScanWindowApi,
        fake_window: FakeWindow,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        step = MigrationStep(
            from_version=0,
            to_version=1,
            description="test",
            fn=lambda cfg: None,
        )
        monkeypatch.setattr(
            "src.ui.webview.views.scan_window.make_adapter", lambda: object()
        )
        monkeypatch.setattr(
            "src.ui.webview.views.scan_window.chain.pending",
            lambda adapter: [step],
        )

        calls: list[object] = []
        monkeypatch.setattr(
            "src.controllers.scan.ScanController.start_scan",
            lambda self, cfg: calls.append(cfg),
        )

        api._on_loaded()

        assert calls == []
        assert "migration.pending" in fake_window.evaluate_js_calls[-1]

        payload = _last_payload(fake_window)
        assert payload["steps"] == [
            {"from_version": 0, "to_version": 1, "description": "test"}
        ]


# ────────────────────────────────────────────────────────────────| _on_closing |──


class TestOnClosing:
    """_on_closing() vetoes the window-manager close while not closable."""

    def test_vetoes_while_not_closable(self, api: ScanWindowApi) -> None:
        assert api._on_closing() is False

    def test_allows_once_closable(self, api: ScanWindowApi) -> None:
        api._controller.finish(0, None)

        assert api._on_closing() is None


# ─────────────────────────────────────────────────────────────────| _on_finish |──


class TestOnFinish:
    """_on_finish() pushes the finish state, with a home-relative location."""

    def test_clean_run_has_no_location_or_report(
        self, api: ScanWindowApi, fake_window: FakeWindow
    ) -> None:
        api._on_finish(MsgFinish(issue_count=0, report_path=None))

        payload = _last_payload(fake_window)

        assert payload == {
            "issue_count": 0,
            "report_path": None,
            "location": "",
        }

    def test_report_under_home_is_tilde_shortened(
        self, api: ScanWindowApi, fake_window: FakeWindow
    ) -> None:
        report = Path.home() / "git" / "reports" / "report.log"
        api._on_finish(MsgFinish(issue_count=2, report_path=report))

        payload = _last_payload(fake_window)

        assert payload["issue_count"] == 2
        assert payload["report_path"] == str(report)
        assert payload["location"] == " ~/git/reports"

    def test_report_outside_home_uses_absolute_path(
        self, api: ScanWindowApi, fake_window: FakeWindow
    ) -> None:
        report = (
            Path(Path.home().anchor)
            / "mnt"
            / "shared"
            / "reports"
            / "report.log"
        )
        api._on_finish(MsgFinish(issue_count=1, report_path=report))

        payload = _last_payload(fake_window)

        assert payload["location"] == f" {report.parent}"


# ───────────────────────────────────────────────────────────────────| _on_gate |──


class TestOnGate:
    """_on_gate() stashes the live gate and pushes its serialised form."""

    def test_ssh_gate_dispatches_with_kind(
        self, api: ScanWindowApi, fake_window: FakeWindow
    ) -> None:
        req = _ssh_req()
        api._on_gate(req)

        assert api._pending_gate is req

        payload = _last_payload(fake_window)
        assert payload["kind"] == "ssh"
        assert payload["url"] == req.url
        assert payload["repo"] == req.repo
        assert "event" not in payload

    def test_http_gate_dispatches_with_kind(
        self, api: ScanWindowApi, fake_window: FakeWindow
    ) -> None:
        req = _http_req()
        api._on_gate(req)

        payload = _last_payload(fake_window)
        assert payload["kind"] == "http"
        assert payload["error"] == "boom"


# ─────────────────────────────────────────────────────| apply/dismiss migration |──


class TestApplyMigrations:
    """apply_migrations() runs the chain and reports success/failure to JS."""

    def test_success_reloads_config_and_starts_scan(
        self, api: ScanWindowApi, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "src.ui.webview.views.scan_window.apply_migrations",
            lambda: None,
        )

        new_cfg = configparser.ConfigParser()
        new_cfg["marker"] = {"reloaded": "yes"}
        monkeypatch.setattr(
            "src.ui.webview.views.scan_window.load_config", lambda: new_cfg
        )

        scan_calls: list[object] = []
        monkeypatch.setattr(
            "src.controllers.scan.ScanController.start_scan",
            lambda self, cfg: scan_calls.append(cfg),
        )

        result = api.apply_migrations()

        assert result == {"ok": True}
        assert api._cfg is new_cfg
        assert scan_calls == [new_cfg]

    def test_failure_does_not_start_scan(
        self, api: ScanWindowApi, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "src.ui.webview.views.scan_window.apply_migrations",
            lambda: OSError("disk full"),
        )

        scan_calls: list[object] = []
        monkeypatch.setattr(
            "src.controllers.scan.ScanController.start_scan",
            lambda self, cfg: scan_calls.append(cfg),
        )

        result = api.apply_migrations()

        assert result["ok"] is False
        assert "disk full" in result["error"]
        assert scan_calls == []


class TestDismissMigration:
    def test_starts_scan_with_existing_config(
        self, api: ScanWindowApi, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        scan_calls: list[object] = []
        monkeypatch.setattr(
            "src.controllers.scan.ScanController.start_scan",
            lambda self, cfg: scan_calls.append(cfg),
        )

        api.dismiss_migration()

        assert scan_calls == [api._cfg]


# ───────────────────────────────────────────────────────| resolve_ssh / http |──


class TestResolveSsh:
    def test_resolves_pending_gate_and_clears_it(
        self, api: ScanWindowApi
    ) -> None:
        req = _ssh_req()
        api._pending_gate = req

        api.resolve_ssh(True)

        assert req.approved is True
        assert req.event.is_set()
        assert api._pending_gate is None


class TestResolveHttp:
    def test_resolves_pending_gate_and_clears_it(
        self, api: ScanWindowApi
    ) -> None:
        req = _http_req()
        api._pending_gate = req

        api.resolve_http(False)

        assert req.retry is False
        assert req.event.is_set()
        assert api._pending_gate is None


# ─────────────────────────────────────────────────────────────| open_report |──


class TestOpenReport:
    def test_delegates_to_linux_open_file(
        self, api: ScanWindowApi, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("sys.platform", "linux")

        calls: list[Path] = []
        monkeypatch.setattr(
            "src.platform.linux.gui.open_file", lambda path: calls.append(path)
        )

        api.open_report("/tmp/report.log")

        assert calls == [Path("/tmp/report.log")]


# ─────────────────────────────────────────────────────────────────────| close |──


class TestClose:
    def test_destroys_the_window(
        self, api: ScanWindowApi, fake_window: FakeWindow
    ) -> None:
        api.close()

        assert fake_window.destroyed is True
