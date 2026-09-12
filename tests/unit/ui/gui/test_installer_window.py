from __future__ import annotations

import tkinter as tk
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from src.models import Confirm, MsgLog
from src.ui.gui.views.installer_window import GuiReporter, InstallerWindow

# ────────────────────────────────────────────────────────────────| Fixtures |──


@pytest.fixture
def window() -> Generator[InstallerWindow]:
    """Construct a withdrawn InstallerWindow with no real background thread.

    threading.Thread is patched so __init__'s deferred self.after(0,
    self._begin) - which never actually fires without a running mainloop,
    same as GitSentinelApp in test_app.py - can never spawn a real thread
    that would call the real install()/uninstall() even if a test happens
    to trigger it.

    Yields:
        InstallerWindow: A freshly constructed, withdrawn window instance.
    """

    with patch("src.ui.gui.views.installer_window.threading.Thread"):
        instance = InstallerWindow("install", force=True)
        instance.withdraw()

        yield instance

        try:
            instance.destroy()

        except tk.TclError:
            pass  # already destroyed by the test itself


# ────────────────────────────────────────────────────────────────────| Init |──


class TestInit:
    def test_title_contains_app_name(self, window: InstallerWindow) -> None:
        from src import APP_NAME

        assert APP_NAME in window.title()

    def test_begin_spawns_a_background_thread(
        self, window: InstallerWindow
    ) -> None:
        with patch(
            "src.ui.gui.views.installer_window.threading.Thread"
        ) as mock_thread:
            window._begin()

            mock_thread.assert_called_once_with(
                target=window._run, daemon=True
            )
            mock_thread.return_value.start.assert_called_once_with()


# ─────────────────────────────────────────────────────────────────────| _run |──


class TestRun:
    def test_install_mode_calls_install_with_force(
        self, window: InstallerWindow
    ) -> None:
        with patch("src.installer.install") as mock_install:
            window._run()

            mock_install.assert_called_once_with(
                force=True, reporter=window._reporter
            )

    def test_uninstall_mode_calls_uninstall(self) -> None:
        with (
            patch("src.ui.gui.views.installer_window.threading.Thread"),
            patch("src.installer.uninstall") as mock_uninstall,
        ):
            win = InstallerWindow("uninstall")
            win.withdraw()

            try:
                win._run()

                mock_uninstall.assert_called_once_with(reporter=win._reporter)

            finally:
                win.destroy()


# ─────────────────────────────────────────────────────────| Event handlers |──


class TestOnLog:
    def test_appends_text_to_log_pane(self, window: InstallerWindow) -> None:
        window._on_log(MsgLog("Installed binary -> C:\\bin\\app.exe"))

        content = window._log_text.get("1.0", "end")

        assert "Installed binary -> C:\\bin\\app.exe" in content

    def test_ignores_empty_text(self, window: InstallerWindow) -> None:
        window._on_log(MsgLog(""))

        assert window._log_text.get("1.0", "end").strip() == ""


class TestOnConfirm:
    def test_resolves_the_gate_and_unblocks_the_waiter(
        self, window: InstallerWindow
    ) -> None:
        req = Confirm(prompt="Create a shortcut?", default=True)

        with patch(
            "src.ui.gui.views.installer_window.messagebox.askyesno",
            return_value=True,
        ) as mock_ask:
            window._on_confirm(req)

        mock_ask.assert_called_once()
        assert req.result is True
        assert req.event.is_set()

    def test_passes_default_through(self, window: InstallerWindow) -> None:
        req = Confirm(prompt="Remove data?", default=False)

        with patch(
            "src.ui.gui.views.installer_window.messagebox.askyesno",
            return_value=False,
        ) as mock_ask:
            window._on_confirm(req)

        assert mock_ask.call_args.kwargs["default"] == "no"


class TestOnFinish:
    def test_enables_close_button(self, window: InstallerWindow) -> None:
        window._on_finish(None)

        assert str(window._close_btn["state"]) == "normal"

    def test_marks_done_so_close_is_allowed(
        self, window: InstallerWindow
    ) -> None:
        assert window._done is False

        window._on_finish(None)

        assert window._done is True


# ───────────────────────────────────────────────────────────────| GuiReporter |──


class TestGuiReporter:
    def test_info_emits_installer_log(self) -> None:
        bus = MagicMock()
        GuiReporter(bus).info("hello")

        event, msg = bus.emit.call_args[0]

        assert event == "installer.log"
        assert msg.text == "hello"

    def test_confirm_blocks_until_resolved_and_returns_result(self) -> None:
        bus = MagicMock()

        def _resolve(event: str, req: Confirm) -> None:
            req.result = True
            req.event.set()

        bus.emit.side_effect = _resolve

        assert GuiReporter(bus).confirm("Continue?", default=True) is True
