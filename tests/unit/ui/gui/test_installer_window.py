from __future__ import annotations

import tkinter as tk
from collections.abc import Generator
from unittest.mock import patch

import pytest

from src import APP_NAME
from src.models import Confirm, MsgLog
from src.ui.gui.views.installer_window import InstallerWindow

# ────────────────────────────────────────────────────────────────| Fixtures |──


@pytest.fixture
def window() -> Generator[InstallerWindow]:
    """Construct a withdrawn InstallerWindow with no real background thread.

    threading.Thread is patched so clicking Uninstall in a test can never
    spawn a real thread that would call the real uninstall().

    Yields:
        InstallerWindow: A freshly constructed, withdrawn window instance.
    """

    with patch("src.controllers.installer.threading.Thread"):
        instance = InstallerWindow()
        instance.withdraw()

        yield instance

        try:
            instance.destroy()

        except tk.TclError:
            pass  # already destroyed by the test itself


def _button_texts(row: tk.Frame) -> list[str]:
    return [
        str(child["text"])
        for child in row.winfo_children()
        if isinstance(child, tk.Button)
    ]


# ────────────────────────────────────────────────────────────────────| Init |──


class TestInit:
    def test_title_contains_app_name(self, window: InstallerWindow) -> None:
        assert APP_NAME in window.title()

    def test_starts_on_confirm_screen(self, window: InstallerWindow) -> None:
        texts = _button_texts(window._button_row)

        assert "Uninstall" in texts
        assert "Cancel" in texts

    def test_not_started_before_any_click(
        self, window: InstallerWindow
    ) -> None:
        assert window._started is False


# ───────────────────────────────────────────────────────────| Confirm screen |──


class TestConfirmScreen:
    def test_cancel_invoke_destroys_the_window(
        self, window: InstallerWindow
    ) -> None:
        cancel_btn = next(
            child
            for child in window._button_row.winfo_children()
            if isinstance(child, tk.Button) and str(child["text"]) == "Cancel"
        )

        cancel_btn.invoke()

        with pytest.raises(tk.TclError):
            window.winfo_exists()  # destroyed Tk roots raise, unlike widgets

    def test_uninstall_starts_background_work_and_shows_progress(
        self, window: InstallerWindow
    ) -> None:
        with patch.object(
            window.controller,
            "begin_uninstall",
            wraps=window.controller.begin_uninstall,
        ) as mock_begin:
            window._on_confirm_uninstall()

        mock_begin.assert_called_once()
        assert window._started is True
        assert hasattr(window, "_log_text")


# ─────────────────────────────────────────────────────────| Event handlers |──


class TestOnLog:
    def test_appends_text_to_log_pane(self, window: InstallerWindow) -> None:
        window._on_confirm_uninstall()

        window._on_log(MsgLog("Removed binary -> /usr/local/bin/app"))

        content = window._log_text.get("1.0", "end")

        assert "Removed binary -> /usr/local/bin/app" in content

    def test_ignores_empty_text(self, window: InstallerWindow) -> None:
        window._on_confirm_uninstall()

        window._on_log(MsgLog(""))

        assert window._log_text.get("1.0", "end").strip() == ""


class TestOnConfirm:
    def test_resolves_the_gate_and_unblocks_the_waiter(
        self, window: InstallerWindow
    ) -> None:
        req = Confirm(prompt="Remove config and state data?", default=False)

        with patch(
            "src.ui.gui.views.installer_window.messagebox.askyesno",
            return_value=True,
        ) as mock_ask:
            window._on_confirm(req)

        mock_ask.assert_called_once()
        assert req.result is True
        assert req.event.is_set()

    def test_passes_default_through(self, window: InstallerWindow) -> None:
        req = Confirm(prompt="Remove config and state data?", default=False)

        with patch(
            "src.ui.gui.views.installer_window.messagebox.askyesno",
            return_value=False,
        ) as mock_ask:
            window._on_confirm(req)

        assert mock_ask.call_args.kwargs["default"] == "no"


class TestOnFinish:
    def test_enables_close_button(self, window: InstallerWindow) -> None:
        window._on_confirm_uninstall()

        window._on_finish(None)

        assert str(window._close_btn["state"]) == "normal"

    def test_marks_done_so_close_is_allowed(
        self, window: InstallerWindow
    ) -> None:
        window._on_confirm_uninstall()

        assert window._done is False

        window._on_finish(None)

        assert window._done is True


# ────────────────────────────────────────────────────────────| Close guard |──


class TestCloseGuard:
    def test_allowed_before_starting(self, window: InstallerWindow) -> None:
        with patch.object(window, "destroy") as mock_destroy:
            window._guard_close()

        mock_destroy.assert_called_once()

    def test_blocked_while_in_progress_and_not_done(
        self, window: InstallerWindow
    ) -> None:
        window._on_confirm_uninstall()

        with patch.object(window, "destroy") as mock_destroy:
            window._guard_close()

        mock_destroy.assert_not_called()

    def test_allowed_once_done(self, window: InstallerWindow) -> None:
        window._on_confirm_uninstall()
        window._on_finish(None)

        with patch.object(window, "destroy") as mock_destroy:
            window._guard_close()

        mock_destroy.assert_called_once()
