from __future__ import annotations

import shutil
import sys
from pathlib import Path

from . import APP_NAME, CONF_DIR, STATE_DIR, frozen_data_dir
from src.config.template import render_config, wrap_comment
from src.reporter import ConsoleReporter, Reporter
from .models import ConfigEntry, ConfigSection

if sys.platform == "win32":  # pragma: no cover - Windows only
    from src.platform.windows.installer import (
        BIN_DIR as BIN_DIR,
        BINARY_DST as BINARY_DST,
    )

else:
    from src.platform.linux.installer import (
        BIN_DIR as BIN_DIR,
        BINARY_DST as BINARY_DST,
    )

# ───────────────────────────────────────────────────────────────| Resources |──


def _resource(name: str) -> Path:
    """Locate a bundled data file at runtime.

    Resolves to the PyInstaller/Nuitka bundle's data/ subfolder when frozen,
    or src/data/ in the source tree during development.

    Args:
        name (str): File name relative to the data directory.

    Returns:
        Path: Absolute path to the requested data file.
    """

    data_dir = frozen_data_dir()

    if data_dir is not None:
        return data_dir / "data" / name

    return Path(__file__).parent / "data" / name


def _current_binary() -> Path:
    """get's either normalised binary location or (in development) script entry
    point

    PyInstaller sets sys.frozen and points sys.executable at the launched
    binary. Nuitka never sets sys.frozen, and in onefile mode sys.executable
    points at its extracted temp interpreter rather than the binary the user
    ran - so it falls into the sys.argv[0] branch below, which is correct
    for Nuitka and for a dev-mode script alike.

    Returns:
        Path: location of binary/script
    """

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve()

    return Path(sys.argv[0]).resolve()


def _render_desktop(exec_cmd: str, extra: str) -> str:
    """Fill the single .desktop template for either deployment target."""

    return (
        _resource(f"{APP_NAME}.desktop")
        .read_text()
        .replace("{exec}", exec_cmd)
        .replace("{extra}", extra)
    )


def _render_example_config() -> str:
    """Generate the settings.example.ini content for the current platform."""

    win = sys.platform == "win32"
    sep = "; " + "─" * 78

    config_path = (
        r"%APPDATA%\git-sentinel\settings.ini"
        if win
        else "~/.config/git-sentinel/settings.ini"
    )

    header = "\n".join(
        [
            "; git-sentinel - settings.example.ini",
            sep,
            wrap_comment(
                f"Copy this file to {config_path} and edit as needed."
                " The executable does this automatically on first start."
            ),
            ";",
            wrap_comment(
                "All path values are relative to your home directory unless"
                " absolute."
            ),
            sep,
        ]
    )

    return render_config(
        header=header,
        sections=[
            ConfigSection(
                "paths",
                [
                    ConfigEntry(
                        "git_root",
                        "git",
                        "Git root directory scanned recursively for git"
                        " repositories.",
                    ),
                    ConfigEntry(
                        "export_path",
                        "git/reports",
                        "Directory where reports are written. Accepts any path:"
                        " a Desktop folder, a shared network path, a CI"
                        " artefact directory, etc.\n By default git-sentinel "
                        "will store the file inside the git/reports dir.",
                        enabled=True,
                    ),
                ],
            ),
            ConfigSection(
                "reports",
                [
                    ConfigEntry(
                        "retention_days",
                        "14",
                        "Number of days to keep report files locally."
                        " Reports older than this are removed.",
                    ),
                    ConfigEntry(
                        "report_extension",
                        "log",
                        'File extension written on report files. "log" is'
                        " conventional and opens well in most text editors.",
                    ),
                ],
            ),
            ConfigSection(
                "staleness",
                [
                    ConfigEntry(
                        "stale_threshold_days",
                        "90",
                        "A repository is flagged as stale when its most recent"
                        " commit across all local branches is older than this"
                        " many days.",
                    ),
                ],
            ),
            ConfigSection(
                "schedule",
                [
                    ConfigEntry(
                        "once_per_day",
                        "true",
                        "When true, the script runs at most once per calendar"
                        " day. Subsequent logins on the same day exit silently."
                        " Run with --force to bypass.",
                    ),
                ],
            ),
            ConfigSection(
                "ssh",
                [
                    ConfigEntry(
                        "use_control_master",
                        "false" if win else "true",
                        (
                            "SSH ControlMaster multiplexing is not supported on"
                            " Windows. This setting has no effect and is always"
                            " treated as false."
                            if win
                            else "Use SSH ControlMaster multiplexing so that"
                            " each SSH host requires only one FIDO key"
                            " authentication per scan session. After you"
                            " approve a host in the GUI and enter your PINe"
                            " once, all further git ls-remote calls to that"
                            " host will reuse the established control socket"
                            " automatically. It is RECOMMENDED to keep this on."
                            " From experience, more than 2 requests in a short"
                            " time will inevitably get annoying and will be"
                            " habitually approved without checking. If you are"
                            " working in a high security environment, set this"
                            " to false.\n"
                            "Set to false to disable. Note: with ControlMaster"
                            " disabled, every SSH remote check may prompt for"
                            " your authentication or FIDO key separately."
                        ),
                    ),
                    ConfigEntry(
                        "control_persist_seconds",
                        "300",
                        (
                            "How long (in seconds) to keep a control socket"
                            " alive (Linux only)."
                            if win
                            else "How long (in seconds) to keep a control"
                            " socket alive after the last connection to that"
                            " host finishes. The socket is also explicitly"
                            " closed at the end of the scan regardless of this"
                            " value."
                        ),
                    ),
                ],
            ),
            ConfigSection(
                "meta",
                [
                    ConfigEntry(
                        "version",
                        "1",
                        "DO NOT REMOVE!\nUsed to determine the migration"
                        " version of this config file",
                    ),
                ],
            ),
        ],
    )


# ───────────────────────────────────────────────────────────────────| State |──


def is_installed() -> bool:
    """True when the running binary is already the installed copy."""

    try:
        return _current_binary().samefile(BINARY_DST)

    except OSError:
        return False


# ───────────────────────────────────────────────| Install steps (protected) |──


def _install_binary() -> str:
    """Copies the app binary into a destination location"""

    src = _current_binary()

    BIN_DIR.mkdir(parents=True, exist_ok=True)

    try:
        shutil.copy2(str(src), str(BINARY_DST))

    except shutil.SameFileError, PermissionError:
        pass

    BINARY_DST.chmod(0o755)

    return f"Installed binary\t→ {BINARY_DST}"


def _install_config() -> str:
    """Create config dir, write the platform-specific example, and seed the live
    settings.ini from it on first install.
    """

    example_dst = CONF_DIR / "settings.example.ini"
    config = CONF_DIR / "settings.ini"
    content = _render_example_config()

    CONF_DIR.mkdir(parents=True, exist_ok=True)
    example_dst.write_text(content, encoding="utf-8")
    lines = [f"Installed example\t→ {example_dst}"]

    if not config.exists():
        config.write_text(content, encoding="utf-8")
        lines.append(f"Created config\t\t→ {config}  (edit to customise)")

    else:
        lines.append(f"Existing config\t\t→ {config}  (left unchanged)")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────| Uninstall steps |──


def _remove_binary() -> str:
    """removes the binary"""

    if not BINARY_DST.exists():
        return f"Binary not found\t→ {BINARY_DST}  (skipping)"

    if sys.platform == "win32":  # pragma: no cover - Windows only
        from src.platform.windows.installer import remove_binary

    else:
        from src.platform.linux.installer import remove_binary

    return remove_binary()


def _remove_config() -> str:
    """removes the config dir"""

    if CONF_DIR.exists():
        shutil.rmtree(CONF_DIR)

        return f"Removed config\t\t→ {CONF_DIR}"

    return f"Config not found\t→ {CONF_DIR}  (skipping)"


def _remove_state() -> str:
    """remove state dir"""

    if STATE_DIR.exists():
        shutil.rmtree(STATE_DIR)

        return f"Removed state\t\t→ {STATE_DIR}"

    return f"State not found\t\t→ {STATE_DIR}  (skipping)"


# ─────────────────────────────────────────────────────────────| Public API  |──


def install(
    *,
    force: bool = False,
    reporter: Reporter | None = None,
    create_desktop_shortcut: bool | None = None,
) -> None:
    """Public API to initialise application installation

    Args:
        force (bool, optional): force install flag. Defaults to False.
        reporter (Reporter, optional): where status/prompts go. Defaults to
            a console-based reporter.
        create_desktop_shortcut (bool, optional): Windows-only. When None
            (default), prompts via reporter.confirm() exactly as before -
            this is what the console binary always gets. When explicitly
            True/False (the windowed wizard's Options-page checkbox), that
            decision is used directly and reporter.confirm() is not called.
    """

    reporter = reporter or ConsoleReporter()

    if sys.platform not in ("linux", "win32"):
        print(
            f"ERROR: {APP_NAME} supports Linux and Windows only.",
            file=sys.stderr,
        )

        sys.exit(1)

    reporter.info(f"NOTICE: {sys.platform} detected, installing {APP_NAME}...")

    reporter.info(_install_binary())
    reporter.info(_install_config())

    if sys.platform == "linux":
        from src.platform.linux.installer import (
            install_autostart,
            install_icon,
            install_launcher,
        )

        reporter.info(install_icon(_resource(f"{APP_NAME}.svg")))
        reporter.info(
            install_autostart(
                _render_desktop(
                    str(BINARY_DST), "X-GNOME-Autostart-enabled=true"
                )
            )
        )
        reporter.info(
            install_launcher(
                _render_desktop(f"{BINARY_DST} --force", "Categories=Utility;")
            )
        )

    elif sys.platform == "win32":  # pragma: no cover - Windows only
        from src.platform.windows.installer import (
            install_autostart_windows,
            install_desktop_shortcut,
            install_programs_entry,
            install_start_menu,
            install_start_menu_uninstall,
        )

        reporter.info(install_autostart_windows())
        reporter.info(install_start_menu())
        reporter.info(install_start_menu_uninstall())
        reporter.info(install_programs_entry())

        if create_desktop_shortcut is None:
            create_desktop_shortcut = reporter.confirm(
                "Create a Desktop shortcut?", default=True
            )

        if create_desktop_shortcut:
            reporter.info(install_desktop_shortcut())

    reporter.info("")
    reporter.info(
        f"{APP_NAME} installed - will open automatically on next login."
    )

    if not force:
        reporter.info(f"To run immediately:\t{BINARY_DST} --force")
        reporter.info(f"To configure:\t\t{CONF_DIR / 'settings.ini'}")


def uninstall(*, reporter: Reporter | None = None) -> None:
    """Public API to initialise application uninstallation

    Args:
        reporter (Reporter, optional): where status/prompts go. Defaults to
            a console-based reporter.
    """

    reporter = reporter or ConsoleReporter()

    if sys.platform == "linux":
        from src.platform.linux.installer import (
            remove_autostart,
            remove_icon,
            remove_launcher,
        )

        reporter.info(remove_autostart())
        reporter.info(remove_launcher())
        reporter.info(remove_icon())

    elif sys.platform == "win32":  # pragma: no cover - Windows only
        from src.platform.windows.installer import (
            remove_autostart_windows,
            remove_desktop_shortcut,
            remove_programs_entry,
            remove_start_menu,
            remove_start_menu_uninstall,
        )

        reporter.info(remove_autostart_windows())
        reporter.info(remove_programs_entry())
        reporter.info(remove_start_menu_uninstall())
        reporter.info(remove_start_menu())
        reporter.info(remove_desktop_shortcut())

    purge = reporter.confirm("Remove config and state data?", default=False)

    if purge:
        reporter.info(_remove_config())
        reporter.info(_remove_state())

    else:
        reporter.info("")
        reporter.info("Config and run-state left intact:")
        reporter.info(f"  {CONF_DIR}")
        reporter.info(f"  {STATE_DIR}")

    reporter.info(_remove_binary())

    reporter.info("")
    reporter.info("Uninstallation complete.")
