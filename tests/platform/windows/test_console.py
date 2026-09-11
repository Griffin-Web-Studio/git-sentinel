from __future__ import annotations

import ctypes
import os
from collections.abc import Callable
from unittest.mock import patch

from src.platform.windows import console

# ────────────────────────────────────────────────────────────────| Helpers |──


def _reporting(pids: list[int]) -> Callable[..., int]:
    """Build a GetConsoleProcessList side_effect that fills *buf* with *pids*.

    Mirrors the real Win32 call: writes up to *size* entries into the caller's
    buffer and returns however many processes are attached in total.
    """

    def _side_effect(buf: ctypes.Array[ctypes.c_uint], size: int) -> int:
        for i, pid in enumerate(pids[:size]):
            buf[i] = pid

        return len(pids)

    return _side_effect


# ──────────────────────────────────────────────────────────────| _owns_console|──


class TestOwnsConsole:
    def test_true_when_only_self_and_bootloader_parent_attached(self) -> None:
        with patch("src.platform.windows.console._kernel32") as mock_kernel32:
            mock_kernel32.return_value.GetConsoleProcessList.side_effect = (
                _reporting([os.getpid(), os.getppid()])
            )

            assert console._owns_console() is True

    def test_false_when_console_shared_with_an_unrelated_process(self) -> None:
        with patch("src.platform.windows.console._kernel32") as mock_kernel32:
            mock_kernel32.return_value.GetConsoleProcessList.side_effect = (
                _reporting([os.getpid(), os.getppid(), 999_999])
            )

            assert console._owns_console() is False


# ──────────────────────────────────────────────────────────────────────| hide |──


class TestHide:
    def test_hides_console_it_owns_exclusively(self) -> None:
        with (
            patch(
                "src.platform.windows.console._owns_console", return_value=True
            ),
            patch("src.platform.windows.console._kernel32") as mock_kernel32,
            patch("src.platform.windows.console._user32") as mock_user32,
        ):
            mock_kernel32.return_value.GetConsoleWindow.return_value = 12345

            console.hide()

            mock_user32.return_value.ShowWindow.assert_called_once_with(
                12345, console._SW_HIDE
            )

    def test_leaves_a_shared_console_untouched(self) -> None:
        with (
            patch(
                "src.platform.windows.console._owns_console", return_value=False
            ),
            patch("src.platform.windows.console._user32") as mock_user32,
        ):
            console.hide()

            mock_user32.return_value.ShowWindow.assert_not_called()

    def test_noop_when_there_is_no_console_window(self) -> None:
        with (
            patch(
                "src.platform.windows.console._owns_console", return_value=True
            ),
            patch("src.platform.windows.console._kernel32") as mock_kernel32,
            patch("src.platform.windows.console._user32") as mock_user32,
        ):
            mock_kernel32.return_value.GetConsoleWindow.return_value = 0

            console.hide()

            mock_user32.return_value.ShowWindow.assert_not_called()


# ──────────────────────────────────────────────────────────────────────| show |──


class TestShow:
    def test_shows_the_console_window(self) -> None:
        with (
            patch("src.platform.windows.console._kernel32") as mock_kernel32,
            patch("src.platform.windows.console._user32") as mock_user32,
        ):
            mock_kernel32.return_value.GetConsoleWindow.return_value = 999

            console.show()

            mock_user32.return_value.ShowWindow.assert_called_once_with(
                999, console._SW_SHOW
            )

    def test_noop_when_there_is_no_console_window(self) -> None:
        with (
            patch("src.platform.windows.console._kernel32") as mock_kernel32,
            patch("src.platform.windows.console._user32") as mock_user32,
        ):
            mock_kernel32.return_value.GetConsoleWindow.return_value = 0

            console.show()

            mock_user32.return_value.ShowWindow.assert_not_called()
