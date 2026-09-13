from __future__ import annotations

import sys
from typing import Protocol

# ────────────────────────────────────────────────────────────────| Reporter |──
#
# install()/uninstall() need to emit status lines and ask yes/no questions
# without caring whether that happens via the terminal (console-subsystem
# build) or a Tkinter window (windowed-subsystem build, which has no valid
# stdout/stdin to print()/input() through at all).


class Reporter(Protocol):
    def info(self, text: str) -> None: ...

    def confirm(self, prompt: str, default: bool) -> bool: ...


class ConsoleReporter:
    """Reports via print()/input() - the behavior install()/uninstall() had
    directly before this abstraction existed."""

    def info(self, text: str) -> None:
        print(text)

    def confirm(self, prompt: str, default: bool) -> bool:
        if not sys.stdin.isatty():
            return default

        hint = "Y/n" if default else "y/N"

        try:
            answer = input(f"\n{prompt} [{hint}] ").strip().lower()

        except EOFError:
            return default

        if default:
            return answer not in ("n", "no")

        return answer in ("y", "yes")
