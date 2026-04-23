"""Shared types for PulseCraft guardrail hooks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class HookContext:
    """Envelope passed to every hook entrypoint."""

    stage: str
    change_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class HookResult:
    outcome: Literal["pass", "fail", "skip"]
    reason: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    audit_payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def passed(cls, reason: str = "", **details: Any) -> HookResult:
        return cls(outcome="pass", reason=reason, details=dict(details))

    @classmethod
    def failed(cls, reason: str, **details: Any) -> HookResult:
        return cls(outcome="fail", reason=reason, details=dict(details))

    @classmethod
    def skipped(cls, reason: str = "") -> HookResult:
        return cls(outcome="skip", reason=reason)
