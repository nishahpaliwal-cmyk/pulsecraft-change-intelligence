"""Past-engagement skill — reconstruct BU notification history from the audit log."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from pulsecraft.orchestrator.audit import AuditReader
from pulsecraft.schemas.audit_record import EventType
from pulsecraft.schemas.past_engagement import PastEngagement


def lookup_past_engagement(
    bu_id: str,
    recipient_id: str,
    audit_reader: AuditReader,
    *,
    lookback_days: int = 90,
) -> PastEngagement | None:
    """Reconstruct past engagement from DELIVERY_ATTEMPT audit records.

    Filters by bu_id appearing in output_summary (format: 'bu_id=<id> decision=...').
    Returns None if no delivery records exist for this BU in the lookback window.
    recipient_id is accepted for future use (not yet stored in audit records).
    """
    records = audit_reader.read_recent_events(EventType.DELIVERY_ATTEMPT, lookback_days * 24)

    prefix = f"bu_id={bu_id} "
    bu_records = [r for r in records if r.output_summary.startswith(prefix)]

    if not bu_records:
        return None

    now = datetime.now(UTC)
    thirty_days_ago = now - timedelta(days=30)
    count_30d = sum(1 for r in bu_records if r.timestamp >= thirty_days_ago)
    last_notified = max(r.timestamp for r in bu_records)

    return PastEngagement(
        bu_id=bu_id,
        last_notified_at=last_notified,
        notification_count_last_30d=count_30d,
    )
