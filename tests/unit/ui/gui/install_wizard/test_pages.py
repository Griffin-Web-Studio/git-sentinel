from __future__ import annotations

import tkinter as tk

import pytest

from src.controllers.events import EventBus
from src.controllers.installer import InstallerController
from src.ui.gui.views.install_wizard.pages import (
    FinishPage,
    OptionsPage,
    ProgressPage,
    WelcomePage,
)

# ────────────────────────────────────────────────────────────────| Fixtures |──


@pytest.fixture
def controller(monkeypatch: pytest.MonkeyPatch) -> InstallerController:
    """A real InstallerController with welcome_text() stubbed out, so page
    tests never touch the filesystem/bundled README.md.

    Returns:
        InstallerController: Controller under test.
    """

    ctrl = InstallerController(EventBus())

    monkeypatch.setattr(
        "src.controllers.installer.welcome_text", lambda: "hello world"
    )

    return ctrl


def _find(widget: tk.Misc, kind: type) -> tk.Widget | None:
    for child in widget.winfo_children():
        if isinstance(child, kind):
            return child

        found = _find(child, kind)

        if found is not None:
            return found

    return None


# ─────────────────────────────────────────────────────────────────| Welcome |──


class TestWelcomePage:
    def test_shows_controller_welcome_text_read_only(
        self, tk_root: tk.Tk, controller: InstallerController
    ) -> None:
        page = WelcomePage(tk_root, controller)

        text_widget = _find(page, tk.Text)

        assert text_widget is not None
        assert str(text_widget["state"]) == "disabled"
        assert "hello world" in text_widget.get("1.0", "end")


# ─────────────────────────────────────────────────────────────────| Options |──


class TestOptionsPage:
    def test_windows_shows_desktop_shortcut_checkbox(
        self, tk_root: tk.Tk, controller: InstallerController
    ) -> None:
        controller.supports_desktop_shortcut = True

        page = OptionsPage(tk_root, controller)

        assert _find(page, tk.Checkbutton) is not None

    def test_linux_shows_placeholder_instead(
        self, tk_root: tk.Tk, controller: InstallerController
    ) -> None:
        controller.supports_desktop_shortcut = False

        page = OptionsPage(tk_root, controller)

        assert _find(page, tk.Checkbutton) is None

    def test_toggling_checkbox_updates_controller(
        self, tk_root: tk.Tk, controller: InstallerController
    ) -> None:
        controller.supports_desktop_shortcut = True
        controller.set_desktop_shortcut(True)

        page = OptionsPage(tk_root, controller)
        page._shortcut_var.set(False)
        page._on_toggle_shortcut()

        assert controller.options.desktop_shortcut is False


# ────────────────────────────────────────────────────────────────| Progress |──


class TestProgressPage:
    def test_append_log_inserts_text(self, tk_root: tk.Tk) -> None:
        page = ProgressPage(tk_root)

        page.append_log("hello")

        assert "hello" in page._log_text.get("1.0", "end")

    def test_append_log_ignores_empty_text(self, tk_root: tk.Tk) -> None:
        page = ProgressPage(tk_root)

        page.append_log("")

        assert page._log_text.get("1.0", "end").strip() == ""


# ─────────────────────────────────────────────────────────────────| Finish |──


class TestFinishPage:
    def test_defaults_from_controller_options(
        self, tk_root: tk.Tk, controller: InstallerController
    ) -> None:
        page = FinishPage(tk_root, controller)

        assert page.run_first_scan is False

    def test_reflects_existing_controller_choice(
        self, tk_root: tk.Tk, controller: InstallerController
    ) -> None:
        controller.set_run_first_scan(True)

        page = FinishPage(tk_root, controller)

        assert page.run_first_scan is True

    def test_checkbox_toggle_reflected_in_property(
        self, tk_root: tk.Tk, controller: InstallerController
    ) -> None:
        page = FinishPage(tk_root, controller)

        page._run_var.set(True)

        assert page.run_first_scan is True
