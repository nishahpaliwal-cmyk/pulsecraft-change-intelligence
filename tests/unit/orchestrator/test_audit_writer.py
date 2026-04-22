"""Tests for AuditWriter — append-only JSONL audit log."""

import uuid
from datetime import UTC, datetime
from pathlib import Path

from pulsecraft.orchestrator.audit import AuditWriter
from pulsecraft.schemas.audit_record import (
    Actor,
    ActorType,
    AuditError,
    AuditOutcome,
    AuditRecord,
    EventType,
)


def _record(
    change_id: str,
    event_type: EventType = EventType.STATE_TRANSITION,
    outcome: AuditOutcome = AuditOutcome.SUCCESS,
    output_summary: str = "test record",
) -> AuditRecord:
    return AuditRecord(
        audit_id=str(uuid.uuid4()),
        timestamp=datetime.now(tz=UTC),
        event_type=event_type,
        change_id=change_id,
        actor=Actor(type=ActorType.ORCHESTRATOR, id="orchestrator", version="1.0"),
        action="test_action",
        input_hash="a" * 64,
        output_summary=output_summary,
        outcome=outcome,
    )


class TestAuditWriterBasic:
    def test_log_and_read_back_single_record(self, tmp_path: Path) -> None:
        writer = AuditWriter(root=tmp_path)
        change_id = str(uuid.uuid4())
        rec = _record(change_id)
        writer.log_event(rec)

        chain = writer.read_chain(change_id)
        assert len(chain) == 1
        assert chain[0].audit_id == rec.audit_id
        assert chain[0].change_id == change_id

    def test_multiple_records_same_change(self, tmp_path: Path) -> None:
        writer = AuditWriter(root=tmp_path)
        change_id = str(uuid.uuid4())
        recs = [_record(change_id, output_summary=f"event {i}") for i in range(5)]
        for r in recs:
            writer.log_event(r)

        chain = writer.read_chain(change_id)
        assert len(chain) == 5

    def test_records_sorted_by_timestamp(self, tmp_path: Path) -> None:
        writer = AuditWriter(root=tmp_path)
        change_id = str(uuid.uuid4())
        for _ in range(3):
            writer.log_event(_record(change_id))

        chain = writer.read_chain(change_id)
        timestamps = [r.timestamp for r in chain]
        assert timestamps == sorted(timestamps)

    def test_different_changes_isolated(self, tmp_path: Path) -> None:
        writer = AuditWriter(root=tmp_path)
        cid_a = str(uuid.uuid4())
        cid_b = str(uuid.uuid4())
        writer.log_event(_record(cid_a))
        writer.log_event(_record(cid_b))
        writer.log_event(_record(cid_a))

        assert len(writer.read_chain(cid_a)) == 2
        assert len(writer.read_chain(cid_b)) == 1

    def test_read_empty_returns_empty_list(self, tmp_path: Path) -> None:
        writer = AuditWriter(root=tmp_path)
        chain = writer.read_chain("nonexistent-change-id")
        assert chain == []

    def test_record_count_tracks_writes(self, tmp_path: Path) -> None:
        writer = AuditWriter(root=tmp_path)
        change_id = str(uuid.uuid4())
        assert writer.record_count(change_id) == 0
        writer.log_event(_record(change_id))
        writer.log_event(_record(change_id))
        assert writer.record_count(change_id) == 2


class TestAuditWriterFileFormat:
    def test_jsonl_file_created_in_date_subdir(self, tmp_path: Path) -> None:
        writer = AuditWriter(root=tmp_path)
        change_id = str(uuid.uuid4())
        writer.log_event(_record(change_id))

        date_dirs = list(tmp_path.iterdir())
        assert len(date_dirs) == 1
        jsonl_file = date_dirs[0] / f"{change_id}.jsonl"
        assert jsonl_file.exists()

    def test_jsonl_file_has_one_line_per_record(self, tmp_path: Path) -> None:
        writer = AuditWriter(root=tmp_path)
        change_id = str(uuid.uuid4())
        for _ in range(3):
            writer.log_event(_record(change_id))

        date_dirs = list(tmp_path.iterdir())
        jsonl_file = date_dirs[0] / f"{change_id}.jsonl"
        lines = [ln for ln in jsonl_file.read_text().splitlines() if ln.strip()]
        assert len(lines) == 3

    def test_round_trip_preserves_all_fields(self, tmp_path: Path) -> None:
        writer = AuditWriter(root=tmp_path)
        change_id = str(uuid.uuid4())
        rec = AuditRecord(
            audit_id=str(uuid.uuid4()),
            timestamp=datetime(2026, 4, 22, 12, 0, 0, tzinfo=UTC),
            event_type=EventType.ERROR,
            change_id=change_id,
            actor=Actor(type=ActorType.AGENT, id="signalscribe_mock", version="mock-1.0"),
            action="invoked",
            input_hash="b" * 64,
            output_summary="error during invocation",
            outcome=AuditOutcome.FAILURE,
            error=AuditError(code="TEST_ERROR", message="test error message"),
        )
        writer.log_event(rec)
        chain = writer.read_chain(change_id)
        assert len(chain) == 1
        recovered = chain[0]
        assert recovered.audit_id == rec.audit_id
        assert recovered.event_type == EventType.ERROR
        assert recovered.error is not None
        assert recovered.error.code == "TEST_ERROR"


class TestAuditWriterSummary:
    def test_summary_contains_change_id(self, tmp_path: Path) -> None:
        writer = AuditWriter(root=tmp_path)
        change_id = str(uuid.uuid4())
        writer.log_event(_record(change_id))
        summary = writer.summary(change_id)
        assert change_id in summary

    def test_summary_no_records_returns_message(self, tmp_path: Path) -> None:
        writer = AuditWriter(root=tmp_path)
        summary = writer.summary("phantom-change-id")
        assert "No audit records" in summary
