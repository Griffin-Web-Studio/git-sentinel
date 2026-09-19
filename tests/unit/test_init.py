from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import src

# ───────────────────────────────────────────────────────────────| is_frozen |──


class TestIsFrozen:
    """Tests is_frozen() detects either packaging tool, and neither in dev
    mode."""

    def test_dev_mode_is_not_frozen(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Neither sys.frozen nor __compiled__ set: not frozen.

        Args:
            monkeypatch (pytest.MonkeyPatch): Ensures neither marker is set.
        """

        if hasattr(sys, "frozen"):
            monkeypatch.delattr(sys, "frozen")

        monkeypatch.delitem(src.__dict__, "__compiled__", raising=False)

        assert src.is_frozen() is False

    def test_pyinstaller_sets_frozen(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """sys.frozen (PyInstaller) is detected as frozen.

        Args:
            monkeypatch (pytest.MonkeyPatch): Sets sys.frozen.
        """

        monkeypatch.setattr(sys, "frozen", True, raising=False)

        assert src.is_frozen() is True

    def test_nuitka_compiled_marker_is_frozen(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A __compiled__ global (Nuitka) is detected as frozen.

        Args:
            monkeypatch (pytest.MonkeyPatch): Injects __compiled__ into this
                module's globals, mirroring what Nuitka does at compile time.
        """

        if hasattr(sys, "frozen"):
            monkeypatch.delattr(sys, "frozen")

        monkeypatch.setitem(src.__dict__, "__compiled__", SimpleNamespace())

        assert src.is_frozen() is True


# ───────────────────────────────────────────────────────| frozen_data_dir |──


class TestFrozenDataDir:
    """Tests frozen_data_dir() resolves either packaging tool's bundle root,
    or None in dev mode."""

    def test_dev_mode_returns_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Neither _MEIPASS nor __compiled__ set: returns None.

        Args:
            monkeypatch (pytest.MonkeyPatch): Ensures neither marker is set.
        """

        if hasattr(sys, "_MEIPASS"):
            monkeypatch.delattr(sys, "_MEIPASS")

        monkeypatch.delitem(src.__dict__, "__compiled__", raising=False)

        assert src.frozen_data_dir() is None

    def test_pyinstaller_uses_meipass(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """sys._MEIPASS (PyInstaller) is returned as the bundle root.

        Args:
            tmp_path (Path): Used as the fake _MEIPASS extraction directory.
            monkeypatch (pytest.MonkeyPatch): Injects _MEIPASS onto sys.
        """

        monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

        assert src.frozen_data_dir() == tmp_path

    def test_nuitka_uses_sys_executable_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Nuitka (marked by __compiled__): returns dirname(sys.executable).

        Nuitka never sets sys._MEIPASS. Unlike PyInstaller, its onefile mode
        points sys.executable at the extraction directory's bundled
        interpreter rather than the launched binary - which is exactly the
        directory bundled data files land in, on both standalone and
        onefile Nuitka builds.

        Args:
            tmp_path (Path): Used as the fake extraction/dist directory.
            monkeypatch (pytest.MonkeyPatch): Injects __compiled__ and
                points sys.executable at a fake interpreter inside tmp_path.
        """

        if hasattr(sys, "_MEIPASS"):
            monkeypatch.delattr(sys, "_MEIPASS")

        monkeypatch.setitem(src.__dict__, "__compiled__", SimpleNamespace())
        monkeypatch.setattr(sys, "executable", str(tmp_path / "python"))

        assert src.frozen_data_dir() == tmp_path
