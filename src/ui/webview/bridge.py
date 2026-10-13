from __future__ import annotations

import json
from dataclasses import fields, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import webview

# ─────────────────────────────────────────────────────────────| Serialising |──


def to_jsonable(data: Any) -> Any:
    """Convert an EventBus payload into something json.dumps can handle.

    Strips the `event` field off Gate*/Confirm dataclasses (the page never
    needs the live threading.Event, only the data), maps Enum members to
    their `.value`, and Path to its string form. NamedTuples (MsgLog,
    MsgStatus, ...) are handled via their `_asdict()`.

    Args:
        data (Any): Raw payload emitted on an EventBus.

    Returns:
        Any: A value safe to pass to json.dumps().
    """

    if data is None or isinstance(data, (str, int, float, bool)):
        return data

    if isinstance(data, Enum):
        return data.value

    if isinstance(data, Path):
        return str(data)

    if is_dataclass(data) and not isinstance(data, type):
        return {
            f.name: to_jsonable(getattr(data, f.name))
            for f in fields(data)
            if f.name != "event"
        }

    if hasattr(data, "_asdict"):  # NamedTuple
        return {k: to_jsonable(v) for k, v in data._asdict().items()}

    if isinstance(data, (list, tuple)):
        return [to_jsonable(v) for v in data]

    if isinstance(data, dict):
        return {k: to_jsonable(v) for k, v in data.items()}

    return data


# ─────────────────────────────────────────────────────────────────| Pushing |──


def dispatch(window: webview.Window, event: str, data: Any = None) -> None:
    """Push *event*/*data* into the page's JS bus (see web/shared/bus.js).

    Replaces threadsafe.py's widget.after(0, ...) marshalling - pywebview's
    evaluate_js() is itself safe to call directly from the emitting
    (background worker) thread, so no main-thread hop is needed.

    Args:
        window (webview.Window): The window whose page defines
            window.bus.dispatch(event, data).
        event (str): Event name, forwarded verbatim to JS.
        data (Any): Payload; converted via to_jsonable() first.
    """

    window.evaluate_js(
        f"window.bus.dispatch({json.dumps(event)}, "
        f"{json.dumps(to_jsonable(data))})"
    )
