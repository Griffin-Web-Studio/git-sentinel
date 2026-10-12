from __future__ import annotations

from typing import Any

import webview

from src import APP_NAME
from src.controllers.events import EventBus
from src.controllers.installer import InstallerController
from src.models import Confirm
from src.ui.webview.assets import page_url
from src.ui.webview.bridge import dispatch, to_jsonable

_WIDTH = 560
_HEIGHT = 420
_MIN_SIZE = (520, 360)

# ─────────────────────────────────────────────────────────────────| Api |──


class UninstallWindowApi:
    """Drives the uninstall window's page: a confirm screen, then progress.

    Exposed to the page as `pywebview.api`. Owns an EventBus +
    InstallerController. Unlike the install wizard, there are only two
    screens (confirm, progress) which don't map onto InstallStep, so this
    tracks its own started/done flags instead.
    """

    def __init__(self) -> None:
        self._bus = EventBus()
        self.controller = InstallerController(self._bus)
        self._started = False
        self._done = False
        self._pending_confirm: Confirm | None = None
        self._window: webview.Window

    # ── Wiring (main thread, before webview.start()) ────────────────────────

    def bind_window(self, window: webview.Window) -> None:
        """Attach the created window and wire bus/event subscriptions.

        Args:
            window (webview.Window): This Api's window.
        """

        self._window = window

        self._bus.subscribe(
            "installer.log", lambda m: self._push("installer.log", m)
        )
        self._bus.subscribe("installer.confirm", self._on_confirm)
        self._bus.subscribe("installer.finish", lambda _: self._on_finish())

        window.events.closing += self._on_closing

    def _push(self, event: str, data: Any) -> None:
        dispatch(self._window, event, data)

    def _on_confirm(self, req: Confirm) -> None:
        self._pending_confirm = req
        self._push("installer.confirm", to_jsonable(req))

    def _on_finish(self) -> None:
        self._done = True
        self._push("uninstall.finish", None)

    def _on_closing(self) -> bool | None:
        """Veto the window-manager close only while uninstalling and not yet
        done; the confirm screen can always be closed directly."""

        if self._started and not self._done:
            return False

        return None

    # ── JS-callable Api (main thread) ────────────────────────────────────────

    def begin_uninstall(self) -> None:
        """Start the uninstall; called from the confirm screen's Uninstall
        button."""

        self._started = True
        self.controller.begin_uninstall()
        self._push("uninstall.started", None)

    def resolve_confirm(self, result: bool) -> None:
        """Resolve a pending confirm gate; called from the Yes/No buttons.

        Args:
            result (bool): The user's answer.
        """

        assert self._pending_confirm is not None

        self._pending_confirm.result = result
        self._pending_confirm.event.set()
        self._pending_confirm = None

    def close(self) -> None:
        """Close the window; called from Cancel/Close."""

        self._window.destroy()


# ────────────────────────────────────────────────────────────| Entry point |──


def create_uninstall_window() -> UninstallWindowApi:
    """Create (but do not start) the uninstall window.

    Returns:
        UninstallWindowApi: The bound Api. Caller must still call
            webview.start().
    """

    api = UninstallWindowApi()
    window = webview.create_window(
        f"{APP_NAME} Setup",
        url=page_url("uninstall"),
        js_api=api,
        width=_WIDTH,
        height=_HEIGHT,
        min_size=_MIN_SIZE,
    )

    assert window is not None  # None only when webview.start() already ran

    api.bind_window(window)

    return api
