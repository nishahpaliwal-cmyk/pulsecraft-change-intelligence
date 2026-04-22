"""Unit tests for the dedupe skill — key determinism and duplicate detection."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from pulsecraft.schemas.audit_record import Actor, ActorType, AuditOutcome, AuditRecord, EventType
from pulsecraft.skills.dedupe import compute_dedupe_key, has_recent_duplicate


def _make_delivery_record(input_hash: str, timestamp: datetime) -> AuditRecord:
    return AuditRecord(
        audit_id=str(uuid.uuid4()),
        timestamp=timestamp,
        event_type=EventType.DELIVERY_ATTEMPT,
        change_id=str(uuid.uuid4()),
        actor=Actor(type=ActorType.ORCHESTRATOR, id="orchestrator", version="1.0"),
        action="deliver",
        input_hash=input_hash,
        output_summary="bu_id=bu_alpha decision=send_now channel=teams: delivered",
        outcome=AuditOutcome.SUCCESS,
    )


class _MockReader:
    def __init__(self, records: list[AuditRecord]) -> None:
        self._records = records

    def read_chain(self, change_id: str) -> list[AuditRecord]:
        return []

    def read_recent_events(self, event_type: EventType, window_hours: int) -> list[AuditRecord]:
        return [r for r in self._records if r.event_type == event_type]


class TestComputeDedupeKey:
    def test_same_inputs_produce_same_key(self) -> None:
        key1 = compute_dedupe_key("change-1", "bu_alpha", "recipient-1", "variant-1")
        key2 = compute_dedupe_key("change-1", "bu_alpha", "recipient-1", "variant-1")
        assert key1 == key2

    def test_different_change_id_produces_different_key(self) -> None:
        key1 = compute_dedupe_key("change-1", "bu_alpha", "recipient-1", "variant-1")
        key2 = compute_dedupe_key("change-2", "bu_alpha", "recipient-1", "variant-1")
        assert key1 != key2

    def test_different_bu_id_produces_different_key(self) -> None:
        key1 = compute_dedupe_key("change-1", "bu_alpha", "recipient-1", "variant-1")
        key2 = compute_dedupe_key("change-1", "bu_beta", "recipient-1", "variant-1")
        assert key1 != key2

    def test_different_recipient_produces_different_key(self) -> None:
        key1 = compute_dedupe_key("change-1", "bu_alpha", "recipient-1", "variant-1")
        key2 = compute_dedupe_key("change-1", "bu_alpha", "recipient-2", "variant-1")
        assert key1 != key2

    def test_different_variant_produces_different_key(self) -> None:
        key1 = compute_dedupe_key("change-1", "bu_alpha", "recipient-1", "variant-1")
        key2 = compute_dedupe_key("change-1", "bu_alpha", "recipient-1", "variant-2")
        assert key1 != key2

    def test_key_is_hex_string(self) -> None:
        key = compute_dedupe_key("change-1", "bu_alpha", "recipient-1", "variant-1")
        assert isinstance(key, str)
        assert all(c in "0123456789abcdef" for c in key)
        assert len(key) == 64  # SHA-256 hex


class TestHasRecentDuplicate:
    def test_no_records_returns_false(self) -> None:
        reader = _MockReader([])
        key = compute_dedupe_key("c1", "bu_alpha", "r1", "v1")
        assert has_recent_duplicate(key, reader, window_hours=24) is False

    def test_recent_matching_record_returns_true(self) -> None:
        key = compute_dedupe_key("c1", "bu_alpha", "r1", "v1")
        now = datetime.now(UTC)
        record = _make_delivery_record(input_hash=key, timestamp=now - timedelta(hours=1))
        reader = _MockReader([record])
        assert has_recent_duplicate(key, reader, window_hours=24) is True

    def test_non_matching_record_returns_false(self) -> None:
        key = compute_dedupe_key("c1", "bu_alpha", "r1", "v1")
        other_key = compute_dedupe_key("c2", "bu_beta", "r2", "v2")
        now = datetime.now(UTC)
        record = _make_delivery_record(input_hash=other_key, timestamp=now - timedelta(hours=1))
        reader = _MockReader([record])
        assert has_recent_duplicate(key, reader, window_hours=24) is False

    def test_non_delivery_events_ignored(self) -> None:
        key = compute_dedupe_key("c1", "bu_alpha", "r1", "v1")
        now = datetime.now(UTC)
        # Create a STATE_TRANSITION record with matching hash — should be ignored
        record = AuditRecord(
            audit_id=str(uuid.uuid4()),
            timestamp=now - timedelta(hours=1),
            event_type=EventType.STATE_TRANSITION,
            change_id=str(uuid.uuid4()),
            actor=Actor(type=ActorType.ORCHESTRATOR, id="orchestrator", version="1.0"),
            action="transition",
            input_hash=key,
            output_summary="RECEIVED → INTERPRETED",
            outcome=AuditOutcome.SUCCESS,
        )
        reader = _MockReader([record])
        assert has_recent_duplicate(key, reader, window_hours=24) is False
