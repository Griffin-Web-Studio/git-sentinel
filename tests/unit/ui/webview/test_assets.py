from __future__ import annotations

from pathlib import Path

import pytest

from src.ui.webview.assets import WEB_ROOT, page_url, web_root

# ─────────────────────────────────────────────────────────────────| web_root |──


class TestWebRoot:
    """web_root() resolves the page assets directory in dev and frozen
    modes."""

    def test_dev_mode_returns_package_web_dir(self) -> None:
        """In dev mode the path is this package's own web/ directory."""

        assert web_root() == WEB_ROOT
        assert web_root().name == "web"

    def test_frozen_mode_uses_frozen_data_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When packaged, returns frozen_data_dir()/web.

        Args:
            tmp_path (Path): Used as the fake bundle root directory.
            monkeypatch (pytest.MonkeyPatch): Stubs frozen_data_dir().
        """

        monkeypatch.setattr(
            "src.ui.webview.assets.frozen_data_dir", lambda: tmp_path
        )

        assert web_root() == tmp_path / "web"


# ──────────────────────────────────────────────────────────────────| page_url |──


class TestPageUrl:
    """page_url() builds a file:// URL pywebview's create_window(url=) accepts."""

    def test_returns_file_uri_to_index_html(self) -> None:
        result = page_url("scan")

        assert result.startswith("file://")
        assert result.endswith("/scan/index.html")

    def test_uses_frozen_web_root_when_frozen(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Args:
        tmp_path (Path): Used as the fake bundle root directory.
        monkeypatch (pytest.MonkeyPatch): Stubs frozen_data_dir().
        """

        monkeypatch.setattr(
            "src.ui.webview.assets.frozen_data_dir", lambda: tmp_path
        )

        result = page_url("install_wizard")

        assert (
            result
            == (tmp_path / "web" / "install_wizard" / "index.html")
            .resolve()
            .as_uri()
        )
