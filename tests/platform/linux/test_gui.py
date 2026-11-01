from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.platform.linux.gui import configure_webengine, open_file

# ─────────────────────────────────────────────────────────────| open_file |──


class TestOpenFile:
    """Tests open_file dispatches to xdg-open."""

    def test_invokes_xdg_open_with_path(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """open_file spawns xdg-open with the given path as its sole argument.

        Args:
            monkeypatch (pytest.MonkeyPatch): Replaces subprocess.Popen with a
                recording stub so no real process is spawned.
            tmp_path (Path): Stand-in report file path.
        """

        popen = MagicMock()
        monkeypatch.setattr("src.platform.linux.gui.subprocess.Popen", popen)

        report = tmp_path / "report.log"
        open_file(report)

        popen.assert_called_once_with(["xdg-open", str(report)])


# ───────────────────────────────────────────────────────| configure_webengine |──


class TestConfigureWebengine:
    """Tests configure_webengine disables the GPU only under Wayland."""

    FLAGS = "QTWEBENGINE_CHROMIUM_FLAGS"

    @pytest.fixture(autouse=True)
    def _clean_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Start every test without any Qt/Wayland variables set."""
        for var in ("QT_QPA_PLATFORM", "WAYLAND_DISPLAY", self.FLAGS):
            monkeypatch.delenv(var, raising=False)

    def test_wayland_session_disables_gpu(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A Wayland session gets --disable-gpu.

        Args:
            monkeypatch (pytest.MonkeyPatch): Sets the session variables.
        """
        monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
        configure_webengine()

        assert os.environ[self.FLAGS] == "--disable-gpu"

    def test_existing_flags_are_preserved(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The flag is appended to flags the user already set.

        Args:
            monkeypatch (pytest.MonkeyPatch): Sets the session variables.
        """
        monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
        monkeypatch.setenv(self.FLAGS, "--v=1")
        configure_webengine()

        assert os.environ[self.FLAGS] == "--v=1 --disable-gpu"

    def test_flag_not_duplicated(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Calling twice, or with the flag already set, adds it only once.

        Args:
            monkeypatch (pytest.MonkeyPatch): Sets the session variables.
        """
        monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
        configure_webengine()
        configure_webengine()

        assert os.environ[self.FLAGS] == "--disable-gpu"

    def test_x11_session_untouched(self) -> None:
        """Without a Wayland display nothing is changed."""
        configure_webengine()

        assert self.FLAGS not in os.environ

    def test_explicit_xcb_platform_untouched(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Forcing xcb inside a Wayland session keeps GPU rendering.

        Args:
            monkeypatch (pytest.MonkeyPatch): Sets the session variables.
        """
        monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
        monkeypatch.setenv("QT_QPA_PLATFORM", "xcb")
        configure_webengine()

        assert self.FLAGS not in os.environ
