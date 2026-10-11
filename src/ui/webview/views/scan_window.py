from __future__ import annotations

import configparser
import sys
from pathlib import Path
from typing import Any

import webview

from src import APP_NAME, APP_VERSION, CONF_FILE
from src.config import load_config
from src.config.migrations import apply_migrations, chain, make_adapter
from src.controllers.events import EventBus
from src.controllers.scan import ScanController
from src.models import GateHTTP, GateSSH, MsgFinish
from src.ui.webview.assets import page_url
from src.ui.webview.bridge import dispatch, to_jsonable

_WIDTH = 760
_HEIGHT = 560
_MIN_SIZE = (680, 480)

# ─────────────────────────────────────────────────────────────────| Api |──


class ScanWindowApi:
    """Drives the scan window's page; mirrors GitSentinelApp's role.

    Exposed to the page as `pywebview.api`. Owns the EventBus +
    ScanController exactly as GitSentinelApp did; EventBus messages are
    pushed into the page via bridge.dispatch() instead of threadsafe.py's
    after(0, ...) marshalling - pywebview's evaluate_js() is itself safe to
    call directly from the emitting worker thread.

    Args:
        cfg (configparser.ConfigParser): Loaded application config parser.
    """

    def __init__(self, cfg: configparser.ConfigParser) -> None:
        self._cfg = cfg
        self._bus = EventBus()
        self._controller = ScanController(self._bus)
        self._pending_gate: GateSSH | GateHTTP | None = None
        self._window: webview.Window

    # ── Wiring (main thread, before webview.start()) ────────────────────────

    def bind_window(self, window: webview.Window) -> None:
        """Attach the created window and wire bus/event subscriptions.

        Must be called once, after create_window() and before
        webview.start().

        Args:
            window (webview.Window): This Api's window.
        """

        self._window = window

        self._bus.subscribe("scan.log", lambda m: self._push("scan.log", m))
        self._bus.subscribe(
            "scan.status", lambda m: self._push("scan.status", m)
        )
        self._bus.subscribe(
            "scan.progress", lambda m: self._push("scan.progress", m)
        )
        self._bus.subscribe("scan.finish", self._on_finish)
        self._bus.subscribe("scan.gate", self._on_gate)

        window.events.loaded += self._on_loaded
        window.events.closing += self._on_closing

    def _push(self, event: str, data: Any) -> None:
        dispatch(self._window, event, data)

    # ── Startup sequencing ───────────────────────────────────────────────────

    def _on_loaded(self) -> None:
        """Apply pending migrations (if any), then start the scan.

        Migrations are resolved first; the scan only starts once the page
        has dismissed the migration dialog (apply_migrations()/
        dismiss_migration() below) so the two cannot race.
        """

        pending = chain.pending(make_adapter())

        if not pending:
            self._controller.start_scan(self._cfg)
            return

        self._push(
            "migration.pending",
            {
                "steps": [
                    {
                        "from_version": step.from_version,
                        "to_version": step.to_version,
                        "description": step.description,
                    }
                    for step in pending
                ],
                "conf_file": str(CONF_FILE),
            },
        )

    def _on_closing(self) -> bool | None:
        """Veto the window-manager close while the scan is still running."""

        if not self._controller.closable:
            return False

        return None

    # ── Bus handlers needing more than a blind forward ──────────────────────

    def _on_finish(self, msg: MsgFinish) -> None:
        """Update the page to reflect scan completion.

        Args:
            msg (MsgFinish): The finish message from the worker.
        """

        location = ""

        if msg.report_path:
            try:
                location = (
                    " ~/"
                    + msg.report_path.parent.relative_to(Path.home()).as_posix()
                )

            except ValueError:
                location = f" {msg.report_path.parent}"

        self._push(
            "scan.finish",
            {
                "issue_count": msg.issue_count,
                "report_path": (
                    str(msg.report_path) if msg.report_path else None
                ),
                "location": location,
            },
        )

    def _on_gate(self, req: GateSSH | GateHTTP) -> None:
        """Stash the live gate and push its serialised form to the page.

        Args:
            req (GateSSH | GateHTTP): The gate placed on the bus by the
                worker thread.
        """

        self._pending_gate = req
        kind = "ssh" if isinstance(req, GateSSH) else "http"

        self._push("scan.gate", {"kind": kind, **to_jsonable(req)})

    # ── JS-callable Api (main thread) ────────────────────────────────────────

    def apply_migrations(self) -> dict[str, Any]:
        """Apply pending migrations; called from the migration dialog's
        Update button.

        Returns:
            dict: {"ok": True} on success, {"ok": False, "error": str} on
                failure.
        """

        error = apply_migrations()

        if error:
            return {"ok": False, "error": str(error)}

        self._cfg = load_config()
        self._controller.start_scan(self._cfg)

        return {"ok": True}

    def dismiss_migration(self) -> None:
        """Dismiss the migration dialog without applying; starts the scan
        against the config as-is."""

        self._controller.start_scan(self._cfg)

    def resolve_ssh(self, approved: bool) -> None:
        """Resolve a pending SSH gate; called from the Approve/Skip buttons.

        Args:
            approved (bool): True if the user approved the connection.
        """

        assert isinstance(self._pending_gate, GateSSH)

        self._pending_gate.approved = approved
        self._pending_gate.event.set()
        self._pending_gate = None

    def resolve_http(self, retry: bool) -> None:
        """Resolve a pending HTTP gate; called from the Retry/Skip buttons.

        Args:
            retry (bool): True if the user requested a retry.
        """

        assert isinstance(self._pending_gate, GateHTTP)

        self._pending_gate.retry = retry
        self._pending_gate.event.set()
        self._pending_gate = None

    def open_report(self, path: str) -> None:
        """Open *path* with the OS default application.

        Args:
            path (str): Report file path, as sent back by the page.
        """

        if sys.platform == "win32":
            from src.platform.windows.gui import open_file

        else:
            from src.platform.linux.gui import open_file

        open_file(Path(path))

    def close(self) -> None:
        """Close the window; called from the Close/Acknowledge button."""

        self._window.destroy()


# ────────────────────────────────────────────────────────────| Entry point |──


def create_scan_window(cfg: configparser.ConfigParser) -> webview.Window:
    """Create (but do not start) the scan window.

    Args:
        cfg (configparser.ConfigParser): Loaded application config parser.

    Returns:
        webview.Window: The created window. Caller must still call
            webview.start().
    """

    api = ScanWindowApi(cfg)
    window = webview.create_window(
        f"{APP_NAME}  v{APP_VERSION}",
        url=page_url("scan"),
        js_api=api,
        width=_WIDTH,
        height=_HEIGHT,
        min_size=_MIN_SIZE,
    )

    assert window is not None  # None only when webview.start() already ran

    api.bind_window(window)

    return window
