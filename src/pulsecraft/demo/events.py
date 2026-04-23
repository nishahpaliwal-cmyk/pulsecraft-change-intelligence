"""Demo event contract — typed Pydantic models for SSE events."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any, Literal


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _new_id() -> str:
    return f"ev_{uuid.uuid4().hex[:12]}"


# ── base ──────────────────────────────────────────────────────────────────────

class Event:
    """Base for all SSE events. Not a Pydantic model — kept lightweight."""

    def __init__(self, run_id: str, event_type: str, payload: dict[str, Any]) -> None:
        self.event_id = _new_id()
        self.run_id = run_id
        self.timestamp = _now_iso()
        self.type = event_type
        self.payload = payload

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "type": self.type,
            "payload": self.payload,
        }

    def is_terminal(self) -> bool:
        return self.type == "terminal_state"


def make_event(run_id: str, raw: dict[str, Any]) -> Event:
    """Construct an Event from a raw on_event callback payload."""
    event_type = raw.pop("type", "unknown")
    return Event(run_id=run_id, event_type=event_type, payload=raw)


def serialize_to_sse(event: Event) -> str:
    """Produce the SSE wire format: ``data: {json}\\n\\n``."""
    return f"data: {json.dumps(event.to_dict(), ensure_ascii=False)}\n\n"


TERMINAL_EVENT_TYPE: Literal["terminal_state"] = "terminal_state"
