from __future__ import annotations

from pathlib import Path

import pytest

import src.services.docs as docs_module
from src.services.docs import (
    _doc_resource,
    _gitlab_anchor_slug,
    gitlab_release_notes_url,
    release_notes_url,
    welcome_blurb,
    welcome_text,
)

REPO_URL = "https://gitlab.com/griffin-web-studio/garage/git-sentinel"

# ───────────────────────────────────────────────────────────────| _doc_resource |──


class TestDocResource:
    """_doc_resource resolves bundled root-level docs in dev and frozen
    modes."""

    def test_dev_mode_path_is_project_root(self) -> None:
        """In dev mode the path sits at the project root, not src/data/."""

        result = _doc_resource("README.md")

        assert result.name == "README.md"
        assert result == Path(__file__).resolve().parents[3] / "README.md"

    def test_frozen_mode_uses_bundled_data_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When packaged (PyInstaller or Nuitka), returns bundle/data/<name>.

        Args:
            tmp_path (Path): Used as the fake bundle root directory.
            monkeypatch (pytest.MonkeyPatch): Stubs frozen_data_dir() to
                simulate either tool having bundled the app.
        """

        monkeypatch.setattr(docs_module, "frozen_data_dir", lambda: tmp_path)
        result = _doc_resource("README.md")

        assert result == tmp_path / "data" / "README.md"


# ─────────────────────────────────────────────────────────────────| welcome_blurb |──

_README_FIXTURE = """\
<img align="right" width="200" src="src/data/git-sentinel.svg" alt="Icon">

> [!NOTE]
> GitHub users - see [GitLab](https://gitlab.com/example/example).

[![pipeline status](https://example.com/badge.svg)](https://example.com/pipe)
[![coverage](https://example.com/cov.svg)](https://example.com/cov)

# App Title (v1.0.0)

Intro paragraph line one.
Intro paragraph line two.

## Requirements

- some requirement that must never appear in the blurb
"""


class TestWelcomeBlurb:
    """welcome_blurb() truncates and sanitises README.md content."""

    def test_strips_html_img_line(self) -> None:
        """The leading <img> HTML tag is removed."""

        assert "<img" not in welcome_blurb(_README_FIXTURE)

    def test_strips_badge_lines(self) -> None:
        """Markdown badge image-links are removed."""

        result = welcome_blurb(_README_FIXTURE)

        assert "[![" not in result
        assert "badge.svg" not in result

    def test_admonition_becomes_plain_sentence(self) -> None:
        """The '> [!NOTE]' blockquote is rewritten as a plain sentence."""

        result = welcome_blurb(_README_FIXTURE)

        assert "[!NOTE]" not in result
        assert ">" not in result
        assert "GitHub users - see [GitLab]" in result

    def test_truncates_before_first_h2_heading(self) -> None:
        """Content from the first '## ' heading onward is excluded."""

        result = welcome_blurb(_README_FIXTURE)

        assert "Requirements" not in result
        assert "some requirement" not in result

    def test_keeps_title_and_intro(self) -> None:
        """The H1 title and intro paragraph survive."""

        result = welcome_blurb(_README_FIXTURE)

        assert "# App Title (v1.0.0)" in result
        assert "Intro paragraph line one." in result
        assert "Intro paragraph line two." in result

    def test_no_readme_heading_returns_whole_text_sanitised(self) -> None:
        """A README with no '## ' heading at all is used in full."""

        text = "# Just a title\n\nJust a paragraph.\n"

        assert welcome_blurb(text).strip() == text.strip()


class TestWelcomeText:
    """welcome_text() reads README.md via _doc_resource and sanitises it."""

    def test_returns_sanitised_content(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The bundled file's content is passed through welcome_blurb()."""

        readme = tmp_path / "README.md"
        readme.write_text(_README_FIXTURE, encoding="utf-8")
        monkeypatch.setattr(
            "src.services.docs._doc_resource", lambda name: readme
        )

        result = welcome_text()

        assert "App Title" in result
        assert "Requirements" not in result

    def test_fails_soft_when_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A missing README.md returns a fallback sentence, not an error."""

        monkeypatch.setattr(
            "src.services.docs._doc_resource",
            lambda name: tmp_path / "missing.md",
        )

        assert welcome_text() == "See README.md for details."


# ──────────────────────────────────────────────────────────────| anchor slug |──


class TestGitlabAnchorSlug:
    """_gitlab_anchor_slug reproduces GitLab's heading-anchor rule."""

    def test_lowercases_and_strips_punctuation(self) -> None:
        """Periods and parentheses are dropped; spaces become hyphens."""

        assert _gitlab_anchor_slug("v0.2.1 (2026-06-30)") == "v021-2026-06-30"

    def test_collapses_whitespace(self) -> None:
        """Multiple spaces collapse into a single hyphen."""

        assert _gitlab_anchor_slug("Bug   Fixes") == "bug-fixes"


# ─────────────────────────────────────────────────────| gitlab_release_notes_url |──

_CHANGELOG_FIXTURE = """\
## v0.2.1 (2026-06-30)

### Bug Fixes

- fixed something

## v0.2.0 (2026-06-25)

### Features

- added something
"""


class TestGitlabReleaseNotesUrl:
    """gitlab_release_notes_url() builds an anchored link to CHANGELOG.md."""

    def test_anchored_link_for_known_version(self) -> None:
        """A version with a matching heading gets an anchored URL."""

        url = gitlab_release_notes_url(_CHANGELOG_FIXTURE, "0.2.1", REPO_URL)

        assert url == (f"{REPO_URL}/-/blob/main/CHANGELOG.md#v021-2026-06-30")

    def test_different_version_gets_different_anchor(self) -> None:
        """A different, also-present version resolves its own anchor."""

        url = gitlab_release_notes_url(_CHANGELOG_FIXTURE, "0.2.0", REPO_URL)

        assert url.endswith("#v020-2026-06-25")

    def test_falls_back_to_plain_link_when_version_not_found(self) -> None:
        """An unrecognised version falls back to a non-anchored file link."""

        url = gitlab_release_notes_url(_CHANGELOG_FIXTURE, "9.9.9", REPO_URL)

        assert url == f"{REPO_URL}/-/blob/main/CHANGELOG.md"


class TestReleaseNotesUrl:
    """release_notes_url() reads CHANGELOG.md via _doc_resource."""

    def test_returns_anchored_url(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The bundled file's content is used to build the anchored URL."""

        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(_CHANGELOG_FIXTURE, encoding="utf-8")
        monkeypatch.setattr(
            "src.services.docs._doc_resource", lambda name: changelog
        )
        monkeypatch.setattr("src.GITLAB_URL", REPO_URL)

        assert release_notes_url("0.2.1").endswith("#v021-2026-06-30")

    def test_fails_soft_when_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A missing CHANGELOG.md falls back to a plain file link."""

        monkeypatch.setattr(
            "src.services.docs._doc_resource",
            lambda name: tmp_path / "missing.md",
        )
        monkeypatch.setattr("src.GITLAB_URL", REPO_URL)

        assert release_notes_url("0.2.1") == (
            f"{REPO_URL}/-/blob/main/CHANGELOG.md"
        )
