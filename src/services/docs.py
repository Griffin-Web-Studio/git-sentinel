from __future__ import annotations

import re
from pathlib import Path

from src import frozen_data_dir

# ─────────────────────────────────────────────────────────────────| Resources |──
#
# README.md/CHANGELOG.md live at the project root, unlike the src/data/
# resources installer.py's _resource() resolves - a separate resolver is
# needed since the two live in different places in the dev tree, even though
# both end up under the same bundled data/ directory once frozen.


def _doc_resource(name: str) -> Path:
    """Locate a bundled root-level doc file at runtime.

    Args:
        name (str): File name (e.g. "README.md").

    Returns:
        Path: Absolute path to the requested file.
    """

    data_dir = frozen_data_dir()

    if data_dir is not None:
        return data_dir / "data" / name

    return Path(__file__).resolve().parents[2] / name


# ───────────────────────────────────────────────────────────────| Welcome text |──

_HEADING_RE = re.compile(r"^## ", re.MULTILINE)
_IMG_LINE_RE = re.compile(r"^\s*<img\b.*$", re.IGNORECASE)
_BADGE_LINE_RE = re.compile(r"^\[!\[.*$")
_ADMONITION_TOKEN_RE = re.compile(
    r"^\[!(?:NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*"
)


def welcome_blurb(readme_text: str) -> str:
    """Derive a short wizard-welcome blurb from README.md's content.

    Keeps only the title and intro paragraph - everything before the first
    "## " heading - so the Welcome page reads like a wizard blurb rather
    than the full technical reference further down (config tables, code
    fences, etc.) that a plain tk.Text can't render sensibly. Strips the
    leading HTML <img> line, Markdown badge links, and ">[!NOTE]"-style
    admonition markers (kept as plain sentences) along the way.

    Args:
        readme_text (str): Full contents of README.md.

    Returns:
        str: Sanitised intro text, ready for display in a read-only Text
            widget.
    """

    match = _HEADING_RE.search(readme_text)
    head = readme_text[: match.start()] if match else readme_text

    lines: list[str] = []

    for line in head.splitlines():
        if _IMG_LINE_RE.match(line) or _BADGE_LINE_RE.match(line):
            continue

        if line.startswith(">"):
            line = _ADMONITION_TOKEN_RE.sub("", line[1:].strip())

        lines.append(line)

    text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines))

    return text.strip()


def welcome_text() -> str:
    """Return the wizard Welcome page's text, reading README.md if bundled.

    Fails soft: if README.md wasn't bundled (or can't be read), returns a
    short fallback sentence instead of raising, so a future bundling
    regression degrades gracefully rather than crashing the installer.

    Returns:
        str: Sanitised welcome text, or a fallback sentence.
    """

    try:
        raw = _doc_resource("README.md").read_text(encoding="utf-8")

    except OSError:
        return "See README.md for details."

    return welcome_blurb(raw)


# ─────────────────────────────────────────────────────────| Release notes URL |──


def _gitlab_anchor_slug(heading_text: str) -> str:
    """Best-effort reproduction of GitLab's Markdown heading-anchor slug.

    GitLab lower-cases the heading, strips characters that aren't
    alphanumeric/space/hyphen, then collapses whitespace runs to a single
    hyphen. If GitLab ever changes this algorithm the resulting link simply
    lands at the top of the file instead of the exact section - not a
    broken link, just a missed scroll.

    Args:
        heading_text (str): Heading text, without the leading "#"/"##".

    Returns:
        str: URL fragment (without the leading "#").
    """

    text = heading_text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)

    return re.sub(r"\s+", "-", text).strip("-")


def _changelog_base_url(repo_url: str) -> str:
    return f"{repo_url}/-/blob/main/CHANGELOG.md"


def gitlab_release_notes_url(
    changelog_text: str, version: str, repo_url: str
) -> str:
    """Build a GitLab URL to the current version's CHANGELOG.md section.

    Args:
        changelog_text (str): Full contents of CHANGELOG.md.
        version (str): APP_VERSION to look up (e.g. "0.2.1").
        repo_url (str): Base GitLab repository URL (no trailing slash).

    Returns:
        str: URL anchored to the version's heading, or a plain link to the
            file if that heading can't be found.
    """

    base = _changelog_base_url(repo_url)
    pattern = re.compile(
        rf"^## v{re.escape(version)} \([^)]*\)\s*$", re.MULTILINE
    )
    match = pattern.search(changelog_text)

    if not match:
        return base

    heading = match.group(0).removeprefix("##").strip()

    return f"{base}#{_gitlab_anchor_slug(heading)}"


def release_notes_url(version: str) -> str:
    """Return the Release Notes URL for *version*, reading CHANGELOG.md if
    bundled.

    Fails soft: if CHANGELOG.md wasn't bundled (or can't be read), falls
    back to a plain (non-anchored) link to the file on GitLab.

    Args:
        version (str): APP_VERSION to look up.

    Returns:
        str: URL to open in the user's browser.
    """

    from src import GITLAB_URL

    try:
        raw = _doc_resource("CHANGELOG.md").read_text(encoding="utf-8")

    except OSError:
        return _changelog_base_url(GITLAB_URL)

    return gitlab_release_notes_url(raw, version, GITLAB_URL)
