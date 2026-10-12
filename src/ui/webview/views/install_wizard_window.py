from __future__ import annotations

import webbrowser
from typing import Any

import webview

from src import APP_NAME
from src.controllers.events import EventBus
from src.controllers.installer import InstallerController
from src.models import Confirm, InstallStep
from src.ui.webview.assets import page_url
from src.ui.webview.bridge import dispatch, to_jsonable

_WIDTH = 640
_HEIGHT = 480
_MIN_SIZE = (560, 420)

# ─────────────────────────────────────────────────────────────────| Api |──


class InstallWizardApi:
    """Drives the install wizard's page: Welcome/Options/Installing/Finish.

    Exposed to the page as `pywebview.api`. Owns an EventBus +
    InstallerController. `controller` is exposed publicly (unlike
    ScanWindowApi's fully-private one) so __main__.py can call
    controller.relaunch_if_requested() once webview.start() returns.

    Args:
        force (bool): Passed through to begin_install() once the user
            clicks Install on the Options page.
    """

    def __init__(self, *, force: bool = False) -> None:
        self._force = force
        self._bus = EventBus()
        self.controller = InstallerController(self._bus)
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
        self._bus.subscribe("installer.finish", lambda _: self._render())

        window.events.loaded += self._render
        window.events.closing += self._on_closing

    def _push(self, event: str, data: Any) -> None:
        dispatch(self._window, event, data)

    # ── Page rendering ───────────────────────────────────────────────────────

    def _render(self) -> None:
        """Push the current wizard step and its data to the page.

        Every navigation re-sends the full step state rather than relying
        on the page to track anything itself.
        """

        step = self.controller.step

        if step is InstallStep.WELCOME:
            self._push(
                "wizard.render",
                {
                    "step": step.value,
                    "welcome_text": self.controller.welcome_text(),
                },
            )

        elif step is InstallStep.OPTIONS:
            self._push(
                "wizard.render",
                {
                    "step": step.value,
                    "supports_desktop_shortcut": (
                        self.controller.supports_desktop_shortcut
                    ),
                    "desktop_shortcut": (
                        self.controller.options.desktop_shortcut
                    ),
                },
            )

        elif step is InstallStep.INSTALLING:
            self._push("wizard.render", {"step": step.value})

        else:
            self._push(
                "wizard.render",
                {
                    "step": step.value,
                    "run_first_scan": self.controller.options.run_first_scan,
                },
            )

    def _on_confirm(self, req: Confirm) -> None:
        self._pending_confirm = req
        self._push("installer.confirm", to_jsonable(req))

    def _on_closing(self) -> bool | None:
        """Veto the window-manager close only while installing and not yet
        closable; Welcome/Options/Finish can always be closed directly."""

        if (
            self.controller.step is InstallStep.INSTALLING
            and not self.controller.closable
        ):
            return False

        return None

    # ── JS-callable Api (main thread) ────────────────────────────────────────

    def advance(self) -> None:
        """Move from Welcome to Options; called from the Next button."""

        self.controller.advance()
        self._render()

    def back(self) -> None:
        """Move from Options to Welcome; called from the Previous button."""

        self.controller.back()
        self._render()

    def begin_install(self) -> None:
        """Start the install; called from the Options page's Install
        button."""

        self.controller.begin_install(force=self._force)
        self._render()

    def set_desktop_shortcut(self, value: bool) -> None:
        """Record the Options page's Desktop shortcut checkbox state.

        Args:
            value (bool): True to create a Desktop shortcut on install.
        """

        self.controller.set_desktop_shortcut(value)

    def set_run_first_scan(self, value: bool) -> None:
        """Record the Finish page's Run first scan checkbox state.

        Args:
            value (bool): True to relaunch the binary with --force after
                the wizard closes.
        """

        self.controller.set_run_first_scan(value)

    def resolve_confirm(self, result: bool) -> None:
        """Resolve a pending confirm gate; called from the Yes/No buttons.

        Args:
            result (bool): The user's answer.
        """

        assert self._pending_confirm is not None

        self._pending_confirm.result = result
        self._pending_confirm.event.set()
        self._pending_confirm = None

    def open_release_notes(self) -> None:
        """Open the release notes URL in the default browser."""

        webbrowser.open(self.controller.release_notes_url())

    def close(self) -> None:
        """Close the window; called from Cancel/Finish."""

        self._window.destroy()


# ────────────────────────────────────────────────────────────| Entry point |──


def create_install_wizard(*, force: bool = False) -> InstallWizardApi:
    """Create (but do not start) the install wizard window.

    Args:
        force (bool): Passed through to begin_install().

    Returns:
        InstallWizardApi: The bound Api; `.controller.relaunch_if_requested()`
            must be called once webview.start() returns. Caller must still
            call webview.start().
    """

    api = InstallWizardApi(force=force)
    window = webview.create_window(
        f"{APP_NAME} Setup",
        url=page_url("install_wizard"),
        js_api=api,
        width=_WIDTH,
        height=_HEIGHT,
        min_size=_MIN_SIZE,
    )

    assert window is not None  # None only when webview.start() already ran

    api.bind_window(window)

    return api
