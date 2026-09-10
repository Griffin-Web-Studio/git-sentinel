from __future__ import annotations

from unittest.mock import patch

from src.platform.windows import console

# ──────────────────────────────────────────────────────────────| _owns_console|──


class TestOwnsConsole:
    def test_true_when_sole_attached_process(self) -> None:
        with patch("src.platform.windows.console.ctypes") as mock_ctypes:
            mock_ctypes.windll.kernel32.GetConsoleProcessList.return_value = 1

            assert console._owns_console() is True

    def test_false_when_console_shared_with_parent_shell(self) -> None:
        with patch("src.platform.windows.console.ctypes") as mock_ctypes:
            mock_ctypes.windll.kernel32.GetConsoleProcessList.return_value = 2

            assert console._owns_console() is False


# ──────────────────────────────────────────────────────────────────────| hide |──


class TestHide:
    def test_hides_console_it_owns_exclusively(self) -> None:
        with patch("src.platform.windows.console.ctypes") as mock_ctypes:
            mock_ctypes.windll.kernel32.GetConsoleProcessList.return_value = 1
            mock_ctypes.windll.kernel32.GetConsoleWindow.return_value = 12345

            console.hide()

            mock_ctypes.windll.user32.ShowWindow.assert_called_once_with(
                12345, console._SW_HIDE
            )

    def test_leaves_a_shared_parent_console_untouched(self) -> None:
        with patch("src.platform.windows.console.ctypes") as mock_ctypes:
            mock_ctypes.windll.kernel32.GetConsoleProcessList.return_value = 2

            console.hide()

            mock_ctypes.windll.user32.ShowWindow.assert_not_called()

    def test_noop_when_there_is_no_console_window(self) -> None:
        with patch("src.platform.windows.console.ctypes") as mock_ctypes:
            mock_ctypes.windll.kernel32.GetConsoleProcessList.return_value = 1
            mock_ctypes.windll.kernel32.GetConsoleWindow.return_value = 0

            console.hide()

            mock_ctypes.windll.user32.ShowWindow.assert_not_called()


# ──────────────────────────────────────────────────────────────────────| show |──


class TestShow:
    def test_shows_the_console_window(self) -> None:
        with patch("src.platform.windows.console.ctypes") as mock_ctypes:
            mock_ctypes.windll.kernel32.GetConsoleWindow.return_value = 999

            console.show()

            mock_ctypes.windll.user32.ShowWindow.assert_called_once_with(
                999, console._SW_SHOW
            )

    def test_noop_when_there_is_no_console_window(self) -> None:
        with patch("src.platform.windows.console.ctypes") as mock_ctypes:
            mock_ctypes.windll.kernel32.GetConsoleWindow.return_value = 0

            console.show()

            mock_ctypes.windll.user32.ShowWindow.assert_not_called()
