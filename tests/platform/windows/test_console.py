from __future__ import annotations

from unittest.mock import patch

from src.platform.windows import console

# ──────────────────────────────────────────────────────────────────────| pause |──


class TestPause:
    def test_prompts_before_returning(self) -> None:
        with patch(
            "src.platform.windows.console.input", return_value=""
        ) as mock_input:
            console.pause()

            mock_input.assert_called_once_with("\nPress Enter to close...")
