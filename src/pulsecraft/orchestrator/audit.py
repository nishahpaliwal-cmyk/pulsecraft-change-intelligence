"""AuditWriter — append-only JSONL audit log per change per day.

Every state transition, agent invocation, HITL action, and policy check produces
one AuditRecord written here. The audit is observability infrastructure — write
failures are logged loudly but never propagate to the orchestrator's control flow.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import structlog

from pulsecraft.schemas.audit_record import AuditRecord

if TYPE_CHECKING:
    pass

logger = structlog.get_logger(__name__)


class AuditWriter:
    """Append-only JSONL writer for AuditRecord instances.

    Files are written to ``<root>/YYYY-MM-DD/<change_id>.jsonl``.
    One file per (change, day). Atomic line-level appends only — no overwrites.

    Inject a custom ``root`` in tests to avoid touching the real audit/ directory.
    """

    def __init__(self, root: Path | str | None = None) -> None:
        if root is None:
            root = Path(os.environ.get("PULSECRAFT_AUDIT_DIR", "audit"))
        self._root = Path(root)
        self._record_counts: dict[str, int] = {}

    def log_event(self, record: AuditRecord) -> None:
        """Append one AuditRecord to the JSONL file for its change_id."""
        try:
            date_str = record.timestamp.strftime("%Y-%m-%d")
            day_dir = self._root / date_str
            day_dir.mkdir(parents=True, exist_ok=True)
            filepath = day_dir / f"{record.change_id}.jsonl"
            line = record.model_dump_json() + "\n"
            with filepath.open("a", encoding="utf-8") as fh:
                fh.write(line)
                fh.flush()
                os.fsync(fh.fileno())
            self._record_counts[record.change_id] = self._record_counts.get(record.change_id, 0) + 1
        except Exception:
            logger.exception(
                "audit_write_failed",
                change_id=record.change_id,
                event_type=record.event_type,
            )

    def read_chain(self, change_id: str) -> list[AuditRecord]:
        """Read all AuditRecords for change_id across all days, ordered by timestamp."""
        records: list[AuditRecord] = []
        if not self._root.exists():
            return records
        for day_dir in sorted(self._root.iterdir()):
            if not day_dir.is_dir():
                continue
            filepath = day_dir / f"{change_id}.jsonl"
            if not filepath.exists():
                continue
            with filepath.open(encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        try:
                            records.append(AuditRecord.model_validate_json(line))
                        except Exception:
                            logger.warning(
                                "audit_corrupt_line",
                                change_id=change_id,
                                file=str(filepath),
                            )
        records.sort(key=lambda r: r.timestamp)
        return records

    def record_count(self, change_id: str) -> int:
        """Return the number of records written this session for change_id."""
        return self._record_counts.get(change_id, 0)

    def summary(self, change_id: str) -> str:
        """Return a human-readable summary of the decision chain for change_id."""
        records = self.read_chain(change_id)
        if not records:
            return f"No audit records found for change_id={change_id}"
        lines = [f"Audit chain for {change_id} ({len(records)} records):"]
        for r in records:
            ts = r.timestamp.strftime("%H:%M:%S")
            decision_str = ""
            if r.decision:
                decision_str = f" [{r.decision.verb}]"
            lines.append(
                f"  {ts} {r.event_type:25s} {r.actor.id:20s}{decision_str} → {r.output_summary[:60]}"
            )
        return "\n".join(lines)


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)
