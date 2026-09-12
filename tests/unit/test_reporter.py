from __future__ import annotations

import builtins

import pytest

from src.reporter import ConsoleReporter

# ─────────────────────────────────────────────────────────────| ConsoleReporter|──


class TestInfo:
    def test_prints_the_text(self, capsys: pytest.CaptureFixture[str]) -> None:
        ConsoleReporter().info("hello")

        assert capsys.readouterr().out == "hello\n"


class TestConfirm:
    def test_returns_default_when_not_a_tty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)

        assert ConsoleReporter().confirm("? ", default=True) is True
        assert ConsoleReporter().confirm("? ", default=False) is False

    def test_returns_default_on_eof(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("sys.stdin.isatty", lambda: True)

        def _raise_eof(prompt: str = "") -> str:
            raise EOFError

        monkeypatch.setattr(builtins, "input", _raise_eof)

        assert ConsoleReporter().confirm("? ", default=True) is True
        assert ConsoleReporter().confirm("? ", default=False) is False

    @pytest.mark.parametrize(
        "answer,expected",
        [("y", True), ("yes", True), ("", True), ("n", False), ("no", False)],
    )
    def test_default_true_accepts_anything_but_no(
        self,
        monkeypatch: pytest.MonkeyPatch,
        answer: str,
        expected: bool,
    ) -> None:
        monkeypatch.setattr("sys.stdin.isatty", lambda: True)
        monkeypatch.setattr(builtins, "input", lambda prompt="": answer)

        assert ConsoleReporter().confirm("? ", default=True) is expected

    @pytest.mark.parametrize(
        "answer,expected",
        [("y", True), ("yes", True), ("", False), ("n", False), ("anything", False)],
    )
    def test_default_false_requires_explicit_yes(
        self,
        monkeypatch: pytest.MonkeyPatch,
        answer: str,
        expected: bool,
    ) -> None:
        monkeypatch.setattr("sys.stdin.isatty", lambda: True)
        monkeypatch.setattr(builtins, "input", lambda prompt="": answer)

        assert ConsoleReporter().confirm("? ", default=False) is expected
