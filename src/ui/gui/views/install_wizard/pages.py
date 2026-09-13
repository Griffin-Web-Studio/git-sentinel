from __future__ import annotations

import tkinter as tk

from src.controllers.installer import InstallerController
from ..wizard_chrome import BODY_FONT, build_header

# ─────────────────────────────────────────────────────────────────| Welcome |──


class WelcomePage(tk.Frame):
    """Wizard page one: introduces the app via a trimmed README blurb.

    Args:
        master: Container frame owned by InstallWizard.
        controller: Supplies the sanitised welcome text to display.
    """

    def __init__(
        self, master: tk.Misc, controller: InstallerController
    ) -> None:
        super().__init__(master)

        build_header(
            self,
            "Welcome",
            "This wizard will install the app on your computer.",
        )

        body = tk.Frame(self)
        body.pack(fill="both", expand=True, padx=10, pady=10)

        y_scroll = tk.Scrollbar(body, orient="vertical")
        y_scroll.pack(side="right", fill="y")

        text = tk.Text(
            body,
            yscrollcommand=y_scroll.set,
            font=BODY_FONT,
            wrap="word",
            borderwidth=0,
            highlightthickness=0,
        )
        text.pack(fill="both", expand=True)
        y_scroll.config(command=text.yview)

        text.insert("end", controller.welcome_text())
        text.config(state="disabled")


# ─────────────────────────────────────────────────────────────────| Options |──


class OptionsPage(tk.Frame):
    """Wizard page two: install-time options (Desktop shortcut, etc.).

    Autostart is always shown as informational text on both platforms - it
    is never a user-controlled toggle. The Desktop shortcut checkbox is
    Windows-only; Linux shows an explanatory placeholder instead, but the
    page itself is always shown on both platforms so the wizard's step
    count/state machine stays identical across them.

    Args:
        master: Container frame owned by InstallWizard.
        controller: Read/written for the current option choices.
    """

    def __init__(
        self, master: tk.Misc, controller: InstallerController
    ) -> None:
        super().__init__(master)

        self._controller = controller

        build_header(
            self,
            "Install Options",
            "Review the options below, then click Install.",
        )

        body = tk.Frame(self)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        tk.Label(
            body,
            text="✔ Run automatically at login (always enabled)",
            anchor="w",
            font=BODY_FONT,
        ).pack(fill="x", pady=(0, 8))

        if controller.supports_desktop_shortcut:
            self._shortcut_var = tk.BooleanVar(
                value=controller.options.desktop_shortcut
            )
            tk.Checkbutton(
                body,
                text="Create a Desktop shortcut",
                variable=self._shortcut_var,
                anchor="w",
                font=BODY_FONT,
                command=self._on_toggle_shortcut,
            ).pack(fill="x", anchor="w")

        else:
            tk.Label(
                body,
                text="No additional install options for Linux.",
                anchor="w",
                font=BODY_FONT,
                fg="gray40",
            ).pack(fill="x", anchor="w")

    def _on_toggle_shortcut(self) -> None:
        self._controller.set_desktop_shortcut(self._shortcut_var.get())


# ────────────────────────────────────────────────────────────────| Progress |──


class ProgressPage(tk.Frame):
    """Wizard page three: install progress log.

    Layout mirrors today's InstallerWindow log pane verbatim.

    Args:
        master: Container frame owned by InstallWizard.
    """

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)

        build_header(
            self, "Installing...", "Please wait while setup completes."
        )

        body = tk.Frame(self)
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

    def append_log(self, text: str) -> None:
        """Append *text* as a new line in the log pane.

        Args:
            text: Line to append; a newline is added automatically. Empty
                text is ignored.
        """

        if not text:
            return

        self._log_text.config(state="normal")
        self._log_text.insert("end", text + "\n")
        self._log_text.see("end")
        self._log_text.config(state="disabled")


# ──────────────────────────────────────────────────────────────────| Finish |──


class FinishPage(tk.Frame):
    """Wizard page four: run-first-scan checkbox + release notes button.

    Args:
        master: Container frame owned by InstallWizard.
        controller: Supplies the initial checkbox state.
    """

    def __init__(
        self, master: tk.Misc, controller: InstallerController
    ) -> None:
        super().__init__(master)

        build_header(
            self, "Setup Complete", "Setup has finished installing the app."
        )

        body = tk.Frame(self)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        self._run_var = tk.BooleanVar(value=controller.options.run_first_scan)
        tk.Checkbutton(
            body,
            text="Run first scan now",
            variable=self._run_var,
            anchor="w",
            font=BODY_FONT,
        ).pack(fill="x", anchor="w")

    @property
    def run_first_scan(self) -> bool:
        """Current state of the Run first scan checkbox."""

        return self._run_var.get()
