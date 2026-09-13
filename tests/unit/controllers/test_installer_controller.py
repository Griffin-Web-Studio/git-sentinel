from __future__ import annotations

import subprocess
import sys
import threading
from collections.abc import Callable
from unittest.mock import patch

import pytest

from src.controllers.events import EventBus
from src.controllers.installer import InstallerController
from src.models import Confirm, InstallOptions, InstallStep, MsgLog

# ────────────────────────────────────────────────────────────────| Fixtures |──


@pytest.fixture
def bus() -> EventBus:
    """Reusable Event Bus fixture.

    Returns:
        EventBus: Application Event Bus.
    """

    return EventBus()


@pytest.fixture
def ctrl(bus: EventBus) -> InstallerController:
    """Reusable installer controller fixture.

    Returns:
        InstallerController: Controller under test.
    """

    return InstallerController(bus)


# ───────────────────────────────────────────────────────────────────| info() |──


class TestInfo:
    """info() emits a MsgLog on installer.log."""

    def test_emits_msg_log(
        self, ctrl: InstallerController, bus: EventBus
    ) -> None:
        """info() emits a MsgLog carrying the text."""

        received: list[MsgLog] = []

        bus.subscribe("installer.log", received.append)
        ctrl.info("hello")

        assert len(received) == 1 and isinstance(received[0], MsgLog)
        assert received[0].text == "hello"


# ─────────────────────────────────────────────────────────────────| confirm() |──


class TestConfirm:
    """confirm() emits a Confirm and blocks until the event is set."""

    def _auto_resolve(self, result: bool) -> Callable[[Confirm], None]:
        def handler(req: Confirm) -> None:
            req.result = result
            req.event.set()

        return handler

    def test_emits_confirm(
        self, ctrl: InstallerController, bus: EventBus
    ) -> None:
        """confirm() emits a Confirm on installer.confirm."""

        received: list[object] = []

        def handler(req: Confirm) -> None:
            received.append(req)
            req.event.set()

        bus.subscribe("installer.confirm", handler)
        ctrl.confirm("Continue?", default=True)

        assert len(received) == 1 and isinstance(received[0], Confirm)

    def test_returns_true_when_confirmed(
        self, ctrl: InstallerController, bus: EventBus
    ) -> None:
        """confirm() returns True when the gate is resolved True."""

        bus.subscribe("installer.confirm", self._auto_resolve(True))

        assert ctrl.confirm("Continue?", default=False) is True

    def test_returns_false_when_declined(
        self, ctrl: InstallerController, bus: EventBus
    ) -> None:
        """confirm() returns False when the gate is resolved False."""

        bus.subscribe("installer.confirm", self._auto_resolve(False))

        assert ctrl.confirm("Continue?", default=True) is False


# ────────────────────────────────────────────────────────────────────| step |──


class TestStep:
    """advance()/back() move between WELCOME and OPTIONS only."""

    def test_starts_at_welcome(self, ctrl: InstallerController) -> None:
        """step starts at WELCOME."""

        assert ctrl.step is InstallStep.WELCOME

    def test_advance_moves_to_options(self, ctrl: InstallerController) -> None:
        """advance() from WELCOME moves to OPTIONS."""

        ctrl.advance()

        assert ctrl.step is InstallStep.OPTIONS

    def test_advance_from_options_is_noop(
        self, ctrl: InstallerController
    ) -> None:
        """advance() from any step other than WELCOME does nothing."""

        ctrl.advance()
        ctrl.advance()

        assert ctrl.step is InstallStep.OPTIONS

    def test_back_moves_to_welcome(self, ctrl: InstallerController) -> None:
        """back() from OPTIONS moves to WELCOME."""

        ctrl.advance()
        ctrl.back()

        assert ctrl.step is InstallStep.WELCOME

    def test_back_from_welcome_is_noop(self, ctrl: InstallerController) -> None:
        """back() from any step other than OPTIONS does nothing."""

        ctrl.back()

        assert ctrl.step is InstallStep.WELCOME


# ─────────────────────────────────────────────────────────────────| options |──


class TestOptions:
    """options exposes and accepts the user's install-time choices."""

    def test_defaults(self, ctrl: InstallerController) -> None:
        """options starts as the InstallOptions defaults."""

        assert ctrl.options == InstallOptions()

    def test_set_desktop_shortcut(self, ctrl: InstallerController) -> None:
        """set_desktop_shortcut() updates options.desktop_shortcut."""

        ctrl.set_desktop_shortcut(False)

        assert ctrl.options.desktop_shortcut is False

    def test_set_run_first_scan(self, ctrl: InstallerController) -> None:
        """set_run_first_scan() updates options.run_first_scan."""

        ctrl.set_run_first_scan(True)

        assert ctrl.options.run_first_scan is True


class TestSupportsDesktopShortcut:
    """supports_desktop_shortcut defaults from sys.platform but is settable."""

    def test_defaults_from_platform(
        self, bus: EventBus, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Defaults to True only when constructed on win32.

        Args:
            bus (EventBus): Fixture bus.
            monkeypatch (pytest.MonkeyPatch): Sets sys.platform to 'win32'.
        """

        monkeypatch.setattr(sys, "platform", "win32")

        assert InstallerController(bus).supports_desktop_shortcut is True

    def test_directly_settable(self, ctrl: InstallerController) -> None:
        """Can be overridden directly, independent of the real platform.

        This is what makes the Windows-only Options-page checkbox testable
        from tests/unit/ui/gui, which never runs on win32 in CI.
        """

        ctrl.supports_desktop_shortcut = True

        assert ctrl.supports_desktop_shortcut is True


# ───────────────────────────────────────────────────────────────────| docs |──


class TestWelcomeText:
    """welcome_text() delegates to services.docs.welcome_text()."""

    def test_delegates(
        self, ctrl: InstallerController, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The controller's welcome_text() returns the docs helper's result."""

        monkeypatch.setattr(
            "src.controllers.installer.welcome_text", lambda: "blurb"
        )

        assert ctrl.welcome_text() == "blurb"


class TestReleaseNotesUrl:
    """release_notes_url() delegates to services.docs.release_notes_url()."""

    def test_delegates_with_app_version(
        self, ctrl: InstallerController, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Called with the running APP_VERSION."""

        calls: list[str] = []

        monkeypatch.setattr(
            "src.controllers.installer.release_notes_url", calls.append
        )
        monkeypatch.setattr("src.APP_VERSION", "9.9.9")

        ctrl.release_notes_url()

        assert calls == ["9.9.9"]


# ─────────────────────────────────────────────────────────────| begin_install |──


class TestBeginInstall:
    """begin_install() runs install() on a background daemon thread."""

    @pytest.fixture
    def spawned(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> list[threading.Thread]:
        """Capture every thread started via src.controllers.installer.

        Args:
            monkeypatch (pytest.MonkeyPatch): Wraps threading.Thread so each
                created instance is recorded before being returned as-is.

        Returns:
            list[threading.Thread]: Threads created, appended as constructed.
        """

        threads: list[threading.Thread] = []
        real_thread = threading.Thread

        def spy_thread(*args: object, **kwargs: object) -> threading.Thread:
            t = real_thread(*args, **kwargs)  # type: ignore[arg-type]
            threads.append(t)
            return t

        monkeypatch.setattr(
            "src.controllers.installer.threading.Thread", spy_thread
        )

        return threads

    def test_sets_step_to_installing_synchronously(
        self, ctrl: InstallerController, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """step becomes INSTALLING immediately, before the thread runs.

        Uses a full mock (not the spawned/spy fixture) so no real thread can
        race ahead to FINISH before the assertion below runs.
        """

        with patch("src.controllers.installer.threading.Thread"):
            ctrl.begin_install(force=True)

        assert ctrl.step is InstallStep.INSTALLING

    def test_spawns_daemon_thread(
        self,
        ctrl: InstallerController,
        spawned: list[threading.Thread],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The worker thread is marked daemon."""

        monkeypatch.setattr("src.installer.install", lambda **kw: None)

        ctrl.begin_install(force=True)

        assert len(spawned) == 1
        assert spawned[0].daemon is True

        spawned[0].join(timeout=2)

    def test_calls_install_with_expected_kwargs(
        self,
        ctrl: InstallerController,
        spawned: list[threading.Thread],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """install() is called with force, reporter=self, and the current
        desktop_shortcut option."""

        calls: list[dict[str, object]] = []

        monkeypatch.setattr(
            "src.installer.install", lambda **kw: calls.append(kw)
        )
        ctrl.set_desktop_shortcut(False)

        ctrl.begin_install(force=True)
        spawned[0].join(timeout=2)

        assert calls == [
            {"force": True, "reporter": ctrl, "create_desktop_shortcut": False}
        ]

    def test_marks_closable_and_finishes_after_install(
        self,
        ctrl: InstallerController,
        spawned: list[threading.Thread],
        bus: EventBus,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """closable flips True, step becomes FINISH, and installer.finish is
        emitted once install() returns."""

        received: list[None] = []

        bus.subscribe("installer.finish", received.append)
        monkeypatch.setattr("src.installer.install", lambda **kw: None)

        ctrl.begin_install(force=False)
        spawned[0].join(timeout=2)

        assert ctrl.closable is True
        assert ctrl.step is InstallStep.FINISH
        assert len(received) == 1


# ───────────────────────────────────────────────────────────| begin_uninstall |──


class TestBeginUninstall:
    """begin_uninstall() runs uninstall() on a background daemon thread."""

    @pytest.fixture
    def spawned(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> list[threading.Thread]:
        """Capture every thread started via src.controllers.installer."""

        threads: list[threading.Thread] = []
        real_thread = threading.Thread

        def spy_thread(*args: object, **kwargs: object) -> threading.Thread:
            t = real_thread(*args, **kwargs)  # type: ignore[arg-type]
            threads.append(t)
            return t

        monkeypatch.setattr(
            "src.controllers.installer.threading.Thread", spy_thread
        )

        return threads

    def test_spawns_daemon_thread(
        self,
        ctrl: InstallerController,
        spawned: list[threading.Thread],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The worker thread is marked daemon."""

        monkeypatch.setattr("src.installer.uninstall", lambda **kw: None)

        ctrl.begin_uninstall()

        assert len(spawned) == 1
        assert spawned[0].daemon is True

        spawned[0].join(timeout=2)

    def test_calls_uninstall_with_reporter(
        self,
        ctrl: InstallerController,
        spawned: list[threading.Thread],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """uninstall() is called with reporter=self."""

        calls: list[dict[str, object]] = []

        monkeypatch.setattr(
            "src.installer.uninstall", lambda **kw: calls.append(kw)
        )

        ctrl.begin_uninstall()
        spawned[0].join(timeout=2)

        assert calls == [{"reporter": ctrl}]

    def test_marks_closable_and_finishes_after_uninstall(
        self,
        ctrl: InstallerController,
        spawned: list[threading.Thread],
        bus: EventBus,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """closable flips True and installer.finish is emitted."""

        received: list[None] = []

        bus.subscribe("installer.finish", received.append)
        monkeypatch.setattr("src.installer.uninstall", lambda **kw: None)

        ctrl.begin_uninstall()
        spawned[0].join(timeout=2)

        assert ctrl.closable is True
        assert len(received) == 1


# ───────────────────────────────────────────────────| relaunch_if_requested |──


class TestRelaunchIfRequested:
    """relaunch_if_requested() detaches a --force relaunch when opted in."""

    def test_noop_when_not_requested(
        self, ctrl: InstallerController, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Popen is never called when run_first_scan is False."""

        called: list[object] = []

        monkeypatch.setattr(
            "src.controllers.installer.subprocess.Popen",
            lambda *a, **kw: called.append((a, kw)),
        )

        ctrl.relaunch_if_requested()

        assert called == []

    def test_launches_binary_with_force(
        self, ctrl: InstallerController, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Popen is called with [BINARY_DST, --force] and detached streams."""

        calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

        monkeypatch.setattr(
            "src.controllers.installer.subprocess.Popen",
            lambda *a, **kw: calls.append((a, kw)),
        )
        monkeypatch.setattr("src.installer.BINARY_DST", "/opt/git-sentinel")

        ctrl.set_run_first_scan(True)
        ctrl.relaunch_if_requested()

        assert len(calls) == 1
        args, kwargs = calls[0]

        assert args[0] == ["/opt/git-sentinel", "--force"]
        assert kwargs["stdin"] is subprocess.DEVNULL
        assert kwargs["stdout"] is subprocess.DEVNULL
        assert kwargs["stderr"] is subprocess.DEVNULL

    def test_no_creationflags_off_windows(
        self, ctrl: InstallerController, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """creationflags stays 0 when not on win32."""

        calls: list[dict[str, object]] = []

        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setattr(
            "src.controllers.installer.subprocess.Popen",
            lambda *a, **kw: calls.append(kw),
        )
        monkeypatch.setattr("src.installer.BINARY_DST", "/opt/git-sentinel")

        ctrl.set_run_first_scan(True)
        ctrl.relaunch_if_requested()

        assert calls[0]["creationflags"] == 0

    def test_does_not_crash_when_simulating_windows(
        self, ctrl: InstallerController, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The win32 branch runs safely even on a non-Windows interpreter,
        where subprocess.CREATE_NO_WINDOW isn't a real attribute at all."""

        calls: list[dict[str, object]] = []

        monkeypatch.setattr(sys, "platform", "win32")
        monkeypatch.setattr(
            "src.controllers.installer.subprocess.Popen",
            lambda *a, **kw: calls.append(kw),
        )
        monkeypatch.setattr("src.installer.BINARY_DST", "/opt/git-sentinel")

        ctrl.set_run_first_scan(True)
        ctrl.relaunch_if_requested()  # must not raise

        assert len(calls) == 1
