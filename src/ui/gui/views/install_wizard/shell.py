from __future__ import annotations

import webbrowser
from tkinter import messagebox
import tkinter as tk

from src import APP_NAME
from src.controllers.events import EventBus
from src.controllers.installer import InstallerController
from src.models import Confirm, InstallStep, MsgLog
from ...threadsafe import thread_safe
from ..wizard_chrome import build_button_row
from .pages import FinishPage, OptionsPage, ProgressPage, WelcomePage

# ───────────────────────────────────────────────────────────────| InstallWizard |──


class InstallWizard(tk.Tk):
    """Root window driving the multi-page install wizard.

    Must be its own tk.Tk root: it runs before any GitSentinelApp exists,
    since it *is* the first-run/--install UI for the windowed build. Owns
    its own EventBus + InstallerController, mirroring how GitSentinelApp
    owns ScanController; `controller` is exposed publicly (unlike
    GitSentinelApp's fully-private one) so __main__.py can call
    controller.relaunch_if_requested() once mainloop() returns.

    Args:
        force: Passed through to InstallerController.begin_install() once
            the user clicks Install on the Options page.
    """

    def __init__(self, *, force: bool = False) -> None:
        super().__init__()

        self._force = force
        self._page: tk.Frame | None = None

        self.title(f"{APP_NAME} Setup")
        self.minsize(560, 420)
        self.protocol("WM_DELETE_WINDOW", self._guard_close)

        self._bus = EventBus()
        self.controller = InstallerController(self._bus)

        self._page_container = tk.Frame(self)
        self._page_container.pack(fill="both", expand=True)

        self._button_row = build_button_row(self)

        self._subscribe()
        self._render()

    # ── Bus subscriptions ─────────────────────────────────────────────────────

    def _subscribe(self) -> None:
        self._bus.subscribe("installer.log", thread_safe(self, self._on_log))
        self._bus.subscribe(
            "installer.confirm", thread_safe(self, self._on_confirm)
        )
        self._bus.subscribe(
            "installer.finish", thread_safe(self, self._on_finish)
        )

    # ── Page rendering ────────────────────────────────────────────────────────

    def _clear(self) -> None:
        for w in self._page_container.winfo_children():
            w.destroy()

        for w in self._button_row.winfo_children():
            w.destroy()

    def _render(self) -> None:
        self._clear()

        step = self.controller.step

        if step is InstallStep.WELCOME:
            self._page = WelcomePage(self._page_container, self.controller)
            self._render_welcome_buttons()

        elif step is InstallStep.OPTIONS:
            self._page = OptionsPage(self._page_container, self.controller)
            self._render_options_buttons()

        elif step is InstallStep.INSTALLING:
            self._page = ProgressPage(self._page_container)
            # no navigation buttons until installer.finish fires

        else:
            self._page = FinishPage(self._page_container, self.controller)
            self._render_finish_buttons()

        self._page.pack(fill="both", expand=True)

    def _render_welcome_buttons(self) -> None:
        tk.Button(
            self._button_row, text="Cancel", width=12, command=self.destroy
        ).pack(side="right", padx=4)
        tk.Button(
            self._button_row, text="Next >", width=12, command=self._on_next
        ).pack(side="right")

    def _render_options_buttons(self) -> None:
        tk.Button(
            self._button_row, text="Cancel", width=12, command=self.destroy
        ).pack(side="right", padx=4)
        tk.Button(
            self._button_row,
            text="Install",
            width=12,
            command=self._on_install,
        ).pack(side="right")
        tk.Button(
            self._button_row,
            text="< Previous",
            width=12,
            command=self._on_back,
        ).pack(side="right", padx=4)

    def _render_finish_buttons(self) -> None:
        tk.Button(
            self._button_row,
            text="Finish",
            width=12,
            command=self._on_finish_click,
        ).pack(side="right")
        tk.Button(
            self._button_row,
            text="Release Notes",
            width=14,
            command=self._on_release_notes,
        ).pack(side="left")

    # ── Navigation handlers ───────────────────────────────────────────────────

    def _on_next(self) -> None:
        self.controller.advance()
        self._render()

    def _on_back(self) -> None:
        self.controller.back()
        self._render()

    def _on_install(self) -> None:
        self.controller.begin_install(force=self._force)
        self._render()

    def _on_release_notes(self) -> None:
        webbrowser.open(self.controller.release_notes_url())

    def _on_finish_click(self) -> None:
        assert isinstance(self._page, FinishPage)

        self.controller.set_run_first_scan(self._page.run_first_scan)
        self.destroy()

    # ── Bus event handlers (main thread) ──────────────────────────────────────

    def _on_log(self, msg: MsgLog) -> None:
        if isinstance(self._page, ProgressPage):
            self._page.append_log(msg.text)

    def _on_confirm(self, req: Confirm) -> None:
        req.result = messagebox.askyesno(
            APP_NAME,
            req.prompt.strip(),
            default="yes" if req.default else "no",
        )
        req.event.set()

    def _on_finish(self, _: None) -> None:
        self._render()

    # ── Close guard ───────────────────────────────────────────────────────────

    def _guard_close(self) -> None:
        if (
            self.controller.step is InstallStep.INSTALLING
            and not self.controller.closable
        ):
            return

        self.destroy()
