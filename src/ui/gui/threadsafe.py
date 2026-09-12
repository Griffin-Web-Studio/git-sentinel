from __future__ import annotations

from collections.abc import Callable
from typing import Any
import tkinter as tk

# ──────────────────────────────────────────────────────────────| thread_safe |──


def thread_safe(
    widget: tk.Misc, fn: Callable[[Any], None]
) -> Callable[[Any], None]:
    """Wrap *fn* so it always runs on *widget*'s Tk main thread.

    EventBus handlers run in the emitting thread; anything that touches Tk
    widgets must be marshalled back via widget.after(0, ...) instead.

    Args:
        widget (tk.Misc): Any widget belonging to the target Tk main loop.
        fn (Callable[[Any], None]): Handler to run on the main thread.
    """

    def wrapper(data: Any) -> None:
        widget.after(0, lambda: fn(data))

    return wrapper
