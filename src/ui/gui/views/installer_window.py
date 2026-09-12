from __future__ import annotations

import threading
from tkinter import messagebox
from typing import Literal
import tkinter as tk

from src import APP_NAME
from src.controllers.events import EventBus
from src.models import Confirm, MsgLog
from src.reporter import Reporter
from ..threadsafe import thread_safe

# ─────────────────────────────────────────────────────────────| GuiReporter |──


class GuiReporter:
    """Reporter that feeds an InstallerWindow instead of the terminal.

    Runs on the install()/uninstall() background thread; every call marshals
    onto the Tk main thread via the bus + thread_safe() the window subscribes
    with. confirm() blocks the calling thread on a Confirm gate exactly like
    ScanController.request_ssh()/request_http_retry() block on a Gate.
    """

    def __init__(self, bus: EventBus) -> None:
        self._bus = bus

    def info(self, text: str) -> None:
        self._bus.emit("installer.log", MsgLog(text))

    def confirm(self, prompt: str, default: bool) -> bool:
        req = Confirm(prompt, default)
        self._bus.emit("installer.confirm", req)
        req.event.wait()

        return req.result


# ─────────────────────────────────────────────────────────| InstallerWindow |──


class InstallerWindow(tk.Tk):
    """Root window driving install()/uninstall() for the windowed build.

    Must be its own tk.Tk root: it runs before any GitSentinelApp exists,
    since it *is* the first-run/--install/--uninstall UI for the GUI-only
    binary, which never has a console to fall back on. install()/uninstall()
    run on a background thread (mirroring ScanController.start_scan()) so
    the window stays responsive; kept mode-generic (log pane + confirm gate)
    so a future "check for updates" flow can reuse GuiReporter/Confirm
    without changes here.

    Args:
        mode: Which orchestrator to run.
        force: Passed through to install() when mode is "install".
    """

    def __init__(
        self, mode: Literal["install", "uninstall"], *, force: bool = False
    ) -> None:
        super().__init__()

        self._mode = mode
        self._force = force
        self._done = False

        self.title(f"{APP_NAME} Setup")
        self.minsize(520, 360)
        self.protocol("WM_DELETE_WINDOW", self._guard_close)

        self._bus = EventBus()
        self._reporter = GuiReporter(self._bus)
        self._build_ui()
        self._subscribe()

        self.after(0, self._begin)

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        verb = "Installing" if self._mode == "install" else "Uninstalling"

        header = tk.Frame(self)
        header.pack(fill="x", padx=10, pady=(10, 2))

        self._status_var = tk.StringVar(value=f"{verb} {APP_NAME}...")
        tk.Label(
            header,
            textvariable=self._status_var,
            anchor="w",
            font=("sans-serif", 10, "bold"),
        ).pack(fill="x")

        body = tk.Frame(self)
        body.pack(fill="both", expand=True, padx=10, pady=2)

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

        button_row = tk.Frame(self)
        button_row.pack(fill="x", padx=10, pady=(4, 10))

        self._close_btn = tk.Button(
            button_row,
            text="Please wait...",
            state="disabled",
            command=self.destroy,
        )
        self._close_btn.pack(side="right")

    # ── Bus subscriptions ─────────────────────────────────────────────────────

    def _subscribe(self) -> None:
        self._bus.subscribe("installer.log", thread_safe(self, self._on_log))
        self._bus.subscribe(
            "installer.confirm", thread_safe(self, self._on_confirm)
        )
        self._bus.subscribe(
            "installer.finish", thread_safe(self, self._on_finish)
        )

    # ── Background work ───────────────────────────────────────────────────────

    def _begin(self) -> None:
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        from src.installer import install, uninstall

        if self._mode == "install":
            install(force=self._force, reporter=self._reporter)

        else:
            uninstall(reporter=self._reporter)

        self._bus.emit("installer.finish", None)

    # ── Event handlers (main thread) ──────────────────────────────────────────

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
        verb = "Install" if self._mode == "install" else "Uninstall"
        self._status_var.set(f"{verb} complete.")
        self._close_btn.config(text="Close", state="normal")

    # ── Close guard ───────────────────────────────────────────────────────────

    def _guard_close(self) -> None:
        if self._done:
            self.destroy()
