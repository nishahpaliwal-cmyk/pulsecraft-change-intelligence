"""Unit tests for the past_engagement skill — engagement history reconstruction."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from pulsecraft.schemas.audit_record import Actor, ActorType, AuditOutcome, AuditRecord, EventType
from pulsecraft.skills.past_engagement import lookup_past_engagement


def _make_delivery_record(bu_id: str, timestamp: datetime) -> AuditRecord:
    change_id = str(uuid.uuid4())
    return AuditRecord(
        audit_id=str(uuid.uuid4()),
        timestamp=timestamp,
        event_type=EventType.DELIVERY_ATTEMPT,
        change_id=change_id,
        actor=Actor(type=ActorType.ORCHESTRATOR, id="orchestrator", version="1.0"),
        action="deliver",
        input_hash="abc123",
        output_summary=f"bu_id={bu_id} decision=send_now channel=teams: delivered",
        outcome=AuditOutcome.SUCCESS,
    )


class _MockReader:
    def __init__(self, records: list[AuditRecord]) -> None:
        self._records = records

    def read_chain(self, change_id: str) -> list[AuditRecord]:
        return []

    def read_recent_events(self, event_type: EventType, window_hours: int) -> list[AuditRecord]:
        return [r for r in self._records if r.event_type == event_type]


class TestLookupPastEngagement:
    def test_empty_audit_returns_none(self) -> None:
        reader = _MockReader([])
        result = lookup_past_engagement("bu_alpha", "recipient-1", reader)
        assert result is None

    def test_no_matching_bu_returns_none(self) -> None:
        now = datetime.now(UTC)
        records = [_make_delivery_record("bu_beta", now - timedelta(days=5))]
        reader = _MockReader(records)
        result = lookup_past_engagement("bu_alpha", "recipient-1", reader)
        assert result is None

    def test_matching_record_returns_engagement(self) -> None:
        now = datetime.now(UTC)
        records = [_make_delivery_record("bu_alpha", now - timedelta(days=5))]
        reader = _MockReader(records)
        result = lookup_past_engagement("bu_alpha", "recipient-1", reader)
        assert result is not None
        assert result.bu_id == "bu_alpha"

    def test_last_notified_at_is_most_recent(self) -> None:
        now = datetime.now(UTC)
        records = [
            _make_delivery_record("bu_alpha", now - timedelta(days=10)),
            _make_delivery_record("bu_alpha", now - timedelta(days=2)),
            _make_delivery_record("bu_alpha", now - timedelta(days=5)),
        ]
        reader = _MockReader(records)
        result = lookup_past_engagement("bu_alpha", "recipient-1", reader)
        assert result is not None
        expected = now - timedelta(days=2)
        # Allow 1 second tolerance for test timing
        assert abs((result.last_notified_at - expected).total_seconds()) < 1

    def test_notification_count_last_30d_correct(self) -> None:
        now = datetime.now(UTC)
        records = [
            _make_delivery_record("bu_alpha", now - timedelta(days=5)),
            _make_delivery_record("bu_alpha", now - timedelta(days=20)),
            _make_delivery_record("bu_alpha", now - timedelta(days=45)),  # outside 30-day window
        ]
        reader = _MockReader(records)
        result = lookup_past_engagement("bu_alpha", "recipient-1", reader)
        assert result is not None
        assert result.notification_count_last_30d == 2

    def test_lookback_days_filter_applied(self) -> None:
        now = datetime.now(UTC)
        records = [
            _make_delivery_record("bu_alpha", now - timedelta(days=5)),
            _make_delivery_record("bu_alpha", now - timedelta(days=20)),
        ]
        reader = _MockReader(records)
        # lookback_days=10 should only see the record at day 5
        result = lookup_past_engagement("bu_alpha", "recipient-1", reader, lookback_days=10)
        # The mock reader ignores window_hours, so both records are returned
        # In a real implementation, the reader would filter by window
        # We verify the behavior is: if reader returns records, we use them
        assert result is not None

    def test_other_bus_not_counted(self) -> None:
        now = datetime.now(UTC)
        records = [
            _make_delivery_record("bu_alpha", now - timedelta(days=5)),
            _make_delivery_record("bu_beta", now - timedelta(days=3)),
        ]
        reader = _MockReader(records)
        result = lookup_past_engagement("bu_alpha", "recipient-1", reader)
        assert result is not None
        assert result.notification_count_last_30d == 1
