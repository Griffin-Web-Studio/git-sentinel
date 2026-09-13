from __future__ import annotations

import subprocess
import sys
import threading
from collections.abc import Callable

from src.controllers.events import EventBus
from src.models import Confirm, InstallOptions, InstallStep, MsgLog
from src.reporter import Reporter
from src.services.docs import release_notes_url, welcome_text

# ────────────────────────────────────────────────────────| InstallerController |──


class InstallerController(Reporter):
    """Drives the install wizard / uninstall window; bridges to the EventBus.

    Structurally implements Reporter (info()/confirm()) exactly like the
    GuiReporter it replaces, so it can be passed straight into
    install()/uninstall() as `reporter=`. Wizard navigation (step, options)
    is plain synchronous state - always mutated from a button click already
    on the main thread, so there is nothing to marshal across threads and
    no need to route it through the bus, mirroring how ScanController.closable
    is already a plain property rather than a bus event.

    No tkinter import anywhere: a future TUI view could drive this same
    controller through the same methods/properties.

    Args:
        bus (EventBus): Shared EventBus that UI adapters subscribe to.
    """

    def __init__(self, bus: EventBus) -> None:
        self._bus = bus
        self._closable = False
        self._step = InstallStep.WELCOME
        self._options = InstallOptions()
        self.supports_desktop_shortcut = sys.platform == "win32"

    # ── Reporter ──────────────────────────────────────────────────────────────

    def info(self, text: str) -> None:
        """Emit a log line on the bus.

        Args:
            text (str): Line to append; a newline is added by the view.
        """

        self._bus.emit("installer.log", MsgLog(text))

    def confirm(self, prompt: str, default: bool) -> bool:
        """Emit a confirm gate and block until the UI resolves it.

        Args:
            prompt (str): Question text shown to the user.
            default (bool): Answer to use if dismissed without choosing.

        Returns:
            bool: The user's answer.
        """

        req = Confirm(prompt, default)

        self._bus.emit("installer.confirm", req)
        req.event.wait()

        return req.result

    # ── Wizard navigation (main-thread only) ────────────────────────────────────

    @property
    def step(self) -> InstallStep:
        """The wizard page currently shown."""

        return self._step

    @property
    def options(self) -> InstallOptions:
        """The user's current install-time option choices."""

        return self._options

    def advance(self) -> None:
        """Move from WELCOME to OPTIONS. No-op from any other step."""

        if self._step is InstallStep.WELCOME:
            self._step = InstallStep.OPTIONS

    def back(self) -> None:
        """Move from OPTIONS back to WELCOME. No-op from any other step."""

        if self._step is InstallStep.OPTIONS:
            self._step = InstallStep.WELCOME

    def set_desktop_shortcut(self, value: bool) -> None:
        """Record the Options page's Desktop shortcut checkbox state.

        Args:
            value (bool): True to create a Desktop shortcut on install.
        """

        self._options.desktop_shortcut = value

    def set_run_first_scan(self, value: bool) -> None:
        """Record the Finish page's Run first scan checkbox state.

        Args:
            value (bool): True to relaunch the binary with --force after
                the wizard closes.
        """

        self._options.run_first_scan = value

    # ── Docs (pure data; safe to call directly from the main thread) ───────────

    def welcome_text(self) -> str:
        """Text shown on the Welcome page."""

        return welcome_text()

    def release_notes_url(self) -> str:
        """URL the Finish page's Release Notes button should open."""

        from src import APP_VERSION

        return release_notes_url(APP_VERSION)

    # ── Lifecycle (background thread) ───────────────────────────────────────────

    def begin_install(self, *, force: bool) -> None:
        """Start install() on a background daemon thread.

        Args:
            force (bool): Passed through to install().
        """

        from src.installer import install

        self._step = InstallStep.INSTALLING

        worker = threading.Thread(
            target=self._run_install, args=(install, force), daemon=True
        )
        worker.start()

    def _run_install(self, install: Callable[..., None], force: bool) -> None:
        install(
            force=force,
            reporter=self,
            create_desktop_shortcut=self._options.desktop_shortcut,
        )
        self._finish()

    def begin_uninstall(self) -> None:
        """Start uninstall() on a background daemon thread."""

        from src.installer import uninstall

        worker = threading.Thread(
            target=self._run_uninstall, args=(uninstall,), daemon=True
        )
        worker.start()

    def _run_uninstall(self, uninstall: Callable[..., None]) -> None:
        uninstall(reporter=self)
        self._finish()

    def _finish(self) -> None:
        self._closable = True
        self._step = InstallStep.FINISH

        self._bus.emit("installer.finish", None)

    @property
    def closable(self) -> bool:
        """True once the background install/uninstall work has finished."""

        return self._closable

    # ── Post-close relaunch ──────────────────────────────────────────────────────

    def relaunch_if_requested(self) -> None:
        """Relaunch the installed binary with --force if the user opted in.

        Spawns a fully detached process so it survives this one exiting.
        Must only be called after the wizard's Tk mainloop() has returned
        (never from inside a widget callback) so the new process can never
        race this one's own window teardown.
        """

        if not self._options.run_first_scan:
            return

        from src.installer import BINARY_DST

        creationflags = 0

        if sys.platform == "win32":  # pragma: no cover - Windows only
            # subprocess.CREATE_NO_WINDOW is only defined as an attribute at
            # all on a genuine Windows interpreter; getattr keeps this branch
            # safe to exercise under a monkeypatched sys.platform in
            # cross-platform unit tests.
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        subprocess.Popen(
            [str(BINARY_DST), "--force"],
            creationflags=creationflags,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
