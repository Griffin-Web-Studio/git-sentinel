from __future__ import annotations

import tkinter as tk
from collections.abc import Generator
from unittest.mock import patch

import pytest

from src.models import Confirm, InstallStep, MsgLog
from src.ui.gui.views.install_wizard.pages import (
    FinishPage,
    OptionsPage,
    ProgressPage,
    WelcomePage,
)
from src.ui.gui.views.install_wizard.shell import InstallWizard

# ────────────────────────────────────────────────────────────────| Fixtures |──


@pytest.fixture
def wizard() -> Generator[InstallWizard]:
    """Construct a withdrawn InstallWizard with no real background thread.

    threading.Thread is patched so a test that reaches the Install button
    can never spawn a real thread that would call the real install().

    Yields:
        InstallWizard: A freshly constructed, withdrawn wizard instance.
    """

    with patch("src.controllers.installer.threading.Thread"):
        instance = InstallWizard(force=True)
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
    def test_starts_on_welcome_page(self, wizard: InstallWizard) -> None:
        assert isinstance(wizard._page, WelcomePage)

    def test_welcome_page_has_no_previous_button(
        self, wizard: InstallWizard
    ) -> None:
        texts = _button_texts(wizard._button_row)

        assert "< Previous" not in texts
        assert "Next >" in texts


# ─────────────────────────────────────────────────────────────| Navigation |──


class TestNavigation:
    def test_next_moves_to_options(self, wizard: InstallWizard) -> None:
        wizard._on_next()

        assert isinstance(wizard._page, OptionsPage)
        assert wizard.controller.step is InstallStep.OPTIONS

    def test_back_moves_to_welcome(self, wizard: InstallWizard) -> None:
        wizard._on_next()
        wizard._on_back()

        assert isinstance(wizard._page, WelcomePage)

    def test_options_page_has_install_button_not_next(
        self, wizard: InstallWizard
    ) -> None:
        wizard._on_next()

        texts = _button_texts(wizard._button_row)

        assert "Install" in texts
        assert "Next >" not in texts

    def test_install_calls_begin_install_and_shows_progress(
        self, wizard: InstallWizard
    ) -> None:
        wizard._on_next()

        with patch.object(
            wizard.controller,
            "begin_install",
            wraps=wizard.controller.begin_install,
        ) as mock_begin:
            wizard._on_install()

        mock_begin.assert_called_once_with(force=True)
        assert isinstance(wizard._page, ProgressPage)


# ──────────────────────────────────────────────────────────────────| Finish |──


class TestFinish:
    def test_on_finish_event_renders_finish_page(
        self, wizard: InstallWizard
    ) -> None:
        wizard.controller._step = InstallStep.FINISH

        wizard._on_finish(None)

        assert isinstance(wizard._page, FinishPage)

    def test_finish_click_reads_checkbox_into_controller(
        self, wizard: InstallWizard
    ) -> None:
        wizard.controller._step = InstallStep.FINISH
        wizard._render()

        assert isinstance(wizard._page, FinishPage)
        wizard._page._run_var.set(True)

        with patch.object(wizard, "destroy") as mock_destroy:
            wizard._on_finish_click()

        assert wizard.controller.options.run_first_scan is True
        mock_destroy.assert_called_once()

    def test_release_notes_opens_browser_with_controller_url(
        self, wizard: InstallWizard
    ) -> None:
        wizard.controller._step = InstallStep.FINISH
        wizard._render()

        with (
            patch.object(
                wizard.controller,
                "release_notes_url",
                return_value="https://example.com/x",
            ),
            patch(
                "src.ui.gui.views.install_wizard.shell.webbrowser.open"
            ) as mock_open,
        ):
            wizard._on_release_notes()

        mock_open.assert_called_once_with("https://example.com/x")


# ─────────────────────────────────────────────────────────────────────| Log |──


class TestLog:
    def test_appends_to_progress_page_log(self, wizard: InstallWizard) -> None:
        wizard._on_next()
        wizard._on_install()

        assert isinstance(wizard._page, ProgressPage)
        wizard._on_log(MsgLog("hello"))

        content = wizard._page._log_text.get("1.0", "end")

        assert "hello" in content

    def test_ignored_when_not_on_progress_page(
        self, wizard: InstallWizard
    ) -> None:
        wizard._on_log(MsgLog("hello"))  # currently on WelcomePage; no raise


# ─────────────────────────────────────────────────────────────────| Confirm |──


class TestConfirm:
    def test_resolves_the_gate(self, wizard: InstallWizard) -> None:
        req = Confirm(prompt="Continue?", default=True)

        with patch(
            "src.ui.gui.views.install_wizard.shell.messagebox.askyesno",
            return_value=True,
        ):
            wizard._on_confirm(req)

        assert req.result is True
        assert req.event.is_set()


# ────────────────────────────────────────────────────────────| Close guard |──


class TestCloseGuard:
    def test_close_allowed_before_installing(
        self, wizard: InstallWizard
    ) -> None:
        with patch.object(wizard, "destroy") as mock_destroy:
            wizard._guard_close()

        mock_destroy.assert_called_once()

    def test_close_blocked_while_installing_and_not_closable(
        self, wizard: InstallWizard
    ) -> None:
        wizard._on_next()

        with patch.object(wizard.controller, "begin_install"):
            wizard._on_install()

        wizard.controller._step = InstallStep.INSTALLING

        with patch.object(wizard, "destroy") as mock_destroy:
            wizard._guard_close()

        mock_destroy.assert_not_called()

    def test_close_allowed_once_closable(self, wizard: InstallWizard) -> None:
        wizard.controller._step = InstallStep.INSTALLING
        wizard.controller._closable = True

        with patch.object(wizard, "destroy") as mock_destroy:
            wizard._guard_close()

        mock_destroy.assert_called_once()
