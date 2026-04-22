"""HITL queue — file-based pending/approved/rejected/held queue.

Every operation writes to the audit log. The queue is intentionally file-based
in v1: operators can run ``ls queue/hitl/pending/`` to see what's waiting.
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

import structlog

from pulsecraft.orchestrator.audit import AuditWriter
from pulsecraft.schemas.audit_record import (
    Actor,
    ActorType,
    AuditOutcome,
    AuditRecord,
    EventType,
)

logger = structlog.get_logger(__name__)


class HITLReason(StrEnum):
    """Reason why a change event was routed to the HITL queue."""

    AGENT_ESCALATE = "agent_escalate"
    NEED_CLARIFICATION = "need_clarification"
    UNRESOLVABLE = "unresolvable"
    CONFIDENCE_BELOW_THRESHOLD = "confidence_below_threshold"
    PRIORITY_P0 = "priority_p0"
    DRAFT_HAS_COMMITMENT = "draft_has_commitment"
    RESTRICTED_TERM_DETECTED = "restricted_term_detected"
    MLR_SENSITIVE = "mlr_sensitive"
    SECOND_WEAK_FROM_GATE_5 = "second_weak_from_gate_5"
    DEDUPE_OR_RATE_LIMIT_CONFLICT = "dedupe_or_rate_limit_conflict"


class HITLStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EDITED = "edited"
    ANSWERED = "answered"


class HITLItem:
    """One HITL queue item, loaded from JSON."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.change_id: str = data["change_id"]
        self.reason: str = data["reason"]
        self.status: str = data["status"]
        self.enqueued_at: str = data["enqueued_at"]
        self.payload: dict[str, Any] = data.get("payload", {})
        self.reviewer: str | None = data.get("reviewer")
        self.reviewer_notes: str | None = data.get("reviewer_notes")
        self._raw = data

    def to_dict(self) -> dict[str, Any]:
        return self._raw.copy()


class HITLQueue:
    """File-based HITL queue.

    Queue directories:
      <root>/pending/   — awaiting human review
      <root>/approved/  — approved by reviewer
      <root>/rejected/  — rejected by reviewer
      <root>/archived/  — resolved items kept for audit

    Inject a custom ``root`` in tests to avoid touching the real queue/ directory.
    """

    def __init__(
        self,
        audit_writer: AuditWriter,
        root: Path | str | None = None,
    ) -> None:
        if root is None:
            root = Path(os.environ.get("PULSECRAFT_QUEUE_DIR", "queue/hitl"))
        self._root = Path(root)
        self._audit = audit_writer
        for subdir in ("pending", "approved", "rejected", "archived"):
            (self._root / subdir).mkdir(parents=True, exist_ok=True)

    # ── internal helpers ──────────────────────────────────────────────────

    def _path(self, status: str, change_id: str) -> Path:
        return self._root / status / f"{change_id}.json"

    def _read(self, status: str, change_id: str) -> dict[str, Any] | None:
        p = self._path(status, change_id)
        if not p.exists():
            return None
        with p.open(encoding="utf-8") as fh:
            return json.load(fh)  # type: ignore[no-any-return]

    def _write(self, status: str, data: dict[str, Any]) -> None:
        p = self._path(status, data["change_id"])
        p.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _move(self, from_status: str, to_status: str, change_id: str) -> dict[str, Any]:
        src = self._path(from_status, change_id)
        dst = self._path(to_status, change_id)
        if not src.exists():
            raise KeyError(f"HITL item not found: change_id={change_id!r} status={from_status!r}")
        data: dict[str, Any] = json.loads(src.read_text(encoding="utf-8"))
        dst.write_text(json.dumps(data, indent=2), encoding="utf-8")
        src.unlink()
        return data

    def _audit_hitl(
        self,
        change_id: str,
        action: str,
        output_summary: str,
        reviewer: str | None = None,
    ) -> None:
        actor_id = reviewer if reviewer else "hitl_queue"
        actor_type = ActorType.HUMAN if reviewer else ActorType.ORCHESTRATOR
        record = AuditRecord(
            audit_id=str(uuid.uuid4()),
            timestamp=datetime.now(tz=UTC),
            event_type=EventType.HITL_ACTION,
            change_id=change_id,
            actor=Actor(type=actor_type, id=actor_id, version=None),
            action=action,
            input_hash=hashlib.sha256(change_id.encode()).hexdigest(),
            output_summary=output_summary[:500],
            outcome=AuditOutcome.SUCCESS,
        )
        self._audit.log_event(record)

    # ── public API ────────────────────────────────────────────────────────

    def enqueue(
        self,
        change_id: str,
        reason: HITLReason,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """Add change_id to the pending queue with the given reason."""
        data: dict[str, Any] = {
            "change_id": change_id,
            "reason": str(reason),
            "status": HITLStatus.PENDING,
            "enqueued_at": datetime.now(tz=UTC).isoformat(),
            "payload": payload or {},
            "reviewer": None,
            "reviewer_notes": None,
        }
        self._write("pending", data)
        self._audit_hitl(
            change_id,
            action="enqueued",
            output_summary=f"Enqueued for HITL review: reason={reason}",
        )
        logger.info("hitl_enqueued", change_id=change_id, reason=str(reason))

    def list_pending(self) -> list[HITLItem]:
        """Return all items currently in the pending queue."""
        pending_dir = self._root / "pending"
        items = []
        for p in sorted(pending_dir.glob("*.json")):
            with p.open(encoding="utf-8") as fh:
                items.append(HITLItem(json.load(fh)))
        return items

    def approve(self, change_id: str, reviewer: str, notes: str | None = None) -> None:
        """Move change_id from pending to approved."""
        data = self._move("pending", "approved", change_id)
        data["status"] = HITLStatus.APPROVED
        data["reviewer"] = reviewer
        data["reviewer_notes"] = notes
        data["resolved_at"] = datetime.now(tz=UTC).isoformat()
        self._write("approved", data)
        self._audit_hitl(
            change_id,
            action="approved",
            output_summary=f"Approved by {reviewer}. Notes: {notes or 'none'}",
            reviewer=reviewer,
        )

    def reject(self, change_id: str, reviewer: str, reason: str) -> None:
        """Move change_id from pending to rejected."""
        data = self._move("pending", "rejected", change_id)
        data["status"] = HITLStatus.REJECTED
        data["reviewer"] = reviewer
        data["reviewer_notes"] = reason
        data["resolved_at"] = datetime.now(tz=UTC).isoformat()
        self._write("rejected", data)
        self._audit_hitl(
            change_id,
            action="rejected",
            output_summary=f"Rejected by {reviewer}. Reason: {reason}",
            reviewer=reviewer,
        )

    def edit(
        self,
        change_id: str,
        field_path: str,
        new_value: Any,
        reviewer: str,
    ) -> None:
        """Record an edit to a drafted message field. Writes audit; no re-run in v1."""
        data = self._read("pending", change_id)
        if data is None:
            raise KeyError(f"HITL item not found in pending: change_id={change_id!r}")
        edits: list[dict[str, Any]] = data.setdefault("edits", [])
        edits.append(
            {
                "field_path": field_path,
                "new_value": new_value,
                "edited_by": reviewer,
                "edited_at": datetime.now(tz=UTC).isoformat(),
            }
        )
        data["status"] = HITLStatus.EDITED
        self._write("pending", data)
        self._audit_hitl(
            change_id,
            action="edited",
            output_summary=f"Field '{field_path}' edited by {reviewer}.",
            reviewer=reviewer,
        )

    def answer_clarification(
        self,
        change_id: str,
        answers: dict[str, str],
        reviewer: str,
    ) -> None:
        """Record answers to SignalScribe's gate-3 clarification questions."""
        data = self._read("pending", change_id)
        if data is None:
            raise KeyError(f"HITL item not found in pending: change_id={change_id!r}")
        data["clarification_answers"] = answers
        data["answered_by"] = reviewer
        data["answered_at"] = datetime.now(tz=UTC).isoformat()
        data["status"] = HITLStatus.ANSWERED
        self._write("pending", data)
        self._audit_hitl(
            change_id,
            action="clarification_answered",
            output_summary=f"Clarification answered by {reviewer}: {len(answers)} answer(s).",
            reviewer=reviewer,
        )

    def is_pending(self, change_id: str) -> bool:
        """Return True if change_id is in the pending queue."""
        return self._path("pending", change_id).exists()
