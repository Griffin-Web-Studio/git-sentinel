from __future__ import annotations

from tkinter import messagebox
import tkinter as tk

from src import APP_NAME
from src.controllers.events import EventBus
from src.controllers.installer import InstallerController
from src.models import Confirm, MsgLog
from ..threadsafe import thread_safe
from .wizard_chrome import build_button_row, build_header

# ─────────────────────────────────────────────────────────| InstallerWindow |──


class InstallerWindow(tk.Tk):
    """Root window driving uninstall() for the windowed build.

    Must be its own tk.Tk root: it runs before any GitSentinelApp exists,
    since it *is* the --uninstall UI for the GUI-only binary, which never
    has a console to fall back on. Unlike install (see InstallWizard) this
    stays a single window - just a confirmation screen shown first (so an
    accidental --uninstall can't destructively proceed unattended), then
    the same log-pane + background-thread flow as before. Restyled via
    wizard_chrome so both windows present one consistent look.
    """

    def __init__(self) -> None:
        super().__init__()

        self._started = False
        self._done = False

        self.title(f"{APP_NAME} Setup")
        self.minsize(520, 360)
        self.protocol("WM_DELETE_WINDOW", self._guard_close)

        self._bus = EventBus()
        self.controller = InstallerController(self._bus)

        self._page_container = tk.Frame(self)
        self._page_container.pack(fill="both", expand=True)

        self._button_row = build_button_row(self)

        self._subscribe()
        self._render_confirm()

    # ── Bus subscriptions ─────────────────────────────────────────────────────

    def _subscribe(self) -> None:
        self._bus.subscribe("installer.log", thread_safe(self, self._on_log))
        self._bus.subscribe(
            "installer.confirm", thread_safe(self, self._on_confirm)
        )
        self._bus.subscribe(
            "installer.finish", thread_safe(self, self._on_finish)
        )

    # ── Screens ──────────────────────────────────────────────────────────────

    def _clear(self) -> None:
        for w in self._page_container.winfo_children():
            w.destroy()

        for w in self._button_row.winfo_children():
            w.destroy()

    def _render_confirm(self) -> None:
        self._clear()

        build_header(
            self._page_container,
            "Uninstall",
            f"Remove {APP_NAME} from this computer.",
        )

        body = tk.Frame(self._page_container)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        tk.Label(
            body,
            text=(
                f"Are you sure you want to uninstall {APP_NAME}?\n"
                "This cannot be undone."
            ),
            anchor="w",
            justify="left",
            font=("sans-serif", 10),
        ).pack(fill="x")

        tk.Button(
            self._button_row, text="Cancel", width=12, command=self.destroy
        ).pack(side="right", padx=4)
        tk.Button(
            self._button_row,
            text="Uninstall",
            width=12,
            command=self._on_confirm_uninstall,
        ).pack(side="right")

    def _render_progress(self) -> None:
        self._clear()

        build_header(
            self._page_container,
            "Uninstalling...",
            "Please wait while setup completes.",
        )

        body = tk.Frame(self._page_container)
        body.pack(fill="both", expand=True, padx=10, pady=10)

        y_scroll = tk.Scrollbar(body, orient="vertical")
        y_scroll.pack(side="right", fill="y")

        self._log_text = tk.Text(
            body,
            yscrollcommand=y_scroll.set,
            font=("monospace", 9),
            state="disabled",
            wrap="word",
        )
        self._log_text.pack(fill="both", expand=True)

        y_scroll.config(command=self._log_text.yview)

        self._close_btn = tk.Button(
            self._button_row,
            text="Please wait...",
            state="disabled",
            command=self.destroy,
        )
        self._close_btn.pack(side="right")

    # ── Handlers ─────────────────────────────────────────────────────────────

    def _on_confirm_uninstall(self) -> None:
        self._started = True

        self._render_progress()
        self.controller.begin_uninstall()

    def _on_log(self, msg: MsgLog) -> None:
        if not msg.text:
            return

        self._log_text.config(state="normal")
        self._log_text.insert("end", msg.text + "\n")
        self._log_text.see("end")
        self._log_text.config(state="disabled")

    def _on_confirm(self, req: Confirm) -> None:
        req.result = messagebox.askyesno(
            APP_NAME,
            req.prompt.strip(),
            default="yes" if req.default else "no",
        )
        req.event.set()

    def _on_finish(self, _: None) -> None:
        self._done = True

        self._close_btn.config(text="Close", state="normal")

    # ── Close guard ───────────────────────────────────────────────────────────

    def _guard_close(self) -> None:
        if not self._started or self._done:
            self.destroy()
