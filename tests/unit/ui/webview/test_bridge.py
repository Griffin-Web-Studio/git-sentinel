from __future__ import annotations

import json
from pathlib import Path

from src.models import Confirm, GateHTTP, GateSSH, MsgFinish, MsgLog
from src.ui.webview.bridge import dispatch, to_jsonable
from tests.unit.ui.webview.conftest import FakeWindow

# ─────────────────────────────────────────────────────────────| to_jsonable |──


class TestToJsonable:
    """to_jsonable() converts EventBus payloads into plain JSON-safe data."""

    def test_passes_through_primitives(self) -> None:
        assert to_jsonable(None) is None
        assert to_jsonable("text") == "text"
        assert to_jsonable(42) == 42
        assert to_jsonable(3.5) == 3.5
        assert to_jsonable(True) is True

    def test_converts_path_to_string(self) -> None:
        path = Path("tmp") / "report.log"

        assert to_jsonable(path) == str(path)

    def test_converts_namedtuple_via_asdict(self) -> None:
        result = to_jsonable(MsgLog("hello", "info"))

        assert result == {"text": "hello", "tag": "info"}

    def test_strips_event_field_from_gate_dataclass(self) -> None:
        req = GateSSH(url="git@example.com:repo.git", repo="~/repo")
        result = to_jsonable(req)

        assert result == {
            "url": "git@example.com:repo.git",
            "repo": "~/repo",
            "approved": False,
        }
        assert "event" not in result

    def test_strips_event_field_from_confirm_dataclass(self) -> None:
        req = Confirm(prompt="Remove config?", default=False)
        result = to_jsonable(req)

        assert result == {
            "prompt": "Remove config?",
            "default": False,
            "result": False,
        }

    def test_converts_http_gate_with_error(self) -> None:
        req = GateHTTP(
            url="https://example.com/repo.git", repo="~/repo", error="boom"
        )
        result = to_jsonable(req)

        assert result == {
            "url": "https://example.com/repo.git",
            "repo": "~/repo",
            "error": "boom",
            "retry": False,
        }

    def test_converts_nested_path_in_namedtuple(self) -> None:
        path = Path("tmp") / "report.log"
        msg = MsgFinish(issue_count=1, report_path=path)
        result = to_jsonable(msg)

        assert result == {"issue_count": 1, "report_path": str(path)}

    def test_converts_none_report_path(self) -> None:
        msg = MsgFinish(issue_count=0, report_path=None)
        result = to_jsonable(msg)

        assert result == {"issue_count": 0, "report_path": None}

    def test_converts_dict_recursively(self) -> None:
        path = Path("x")
        result = to_jsonable({"kind": "ssh", "path": path})

        assert result == {"kind": "ssh", "path": str(path)}

    def test_converts_list_recursively(self) -> None:
        a, b = Path("a"), Path("b")
        result = to_jsonable([a, b])

        assert result == [str(a), str(b)]

    def test_result_is_actually_json_serialisable(self) -> None:
        req = GateSSH(url="git@example.com:repo.git", repo="~/repo")

        json.dumps(to_jsonable(req))  # must not raise


# ─────────────────────────────────────────────────────────────────| dispatch |──


class TestDispatch:
    """dispatch() pushes a JSON-encoded event/data pair via evaluate_js()."""

    def test_calls_evaluate_js_with_bus_dispatch(
        self, fake_window: FakeWindow
    ) -> None:
        dispatch(fake_window, "scan.status", {"text": "scanning"})

        assert len(fake_window.evaluate_js_calls) == 1
        script = fake_window.evaluate_js_calls[0]

        assert script == (
            'window.bus.dispatch("scan.status", {"text": "scanning"})'
        )

    def test_defaults_data_to_none(self, fake_window: FakeWindow) -> None:
        dispatch(fake_window, "installer.finish")

        assert fake_window.evaluate_js_calls == [
            'window.bus.dispatch("installer.finish", null)'
        ]

    def test_serialises_dataclass_payload(
        self, fake_window: FakeWindow
    ) -> None:
        req = GateSSH(url="git@example.com:repo.git", repo="~/repo")
        dispatch(fake_window, "scan.gate", req)

        script = fake_window.evaluate_js_calls[0]
        payload = json.loads(script.split(", ", 1)[1].rstrip(")"))

        assert payload == {
            "url": "git@example.com:repo.git",
            "repo": "~/repo",
            "approved": False,
        }
