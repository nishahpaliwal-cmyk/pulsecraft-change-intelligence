"""Dedupe skill — deterministic key computation and duplicate detection."""

from __future__ import annotations

import hashlib
import json

from pulsecraft.orchestrator.audit import AuditReader
from pulsecraft.schemas.audit_record import EventType


def compute_dedupe_key(
    change_id: str,
    bu_id: str,
    recipient_id: str,
    message_variant_id: str,
) -> str:
    """Return a deterministic SHA-256 hex string for the four input identifiers.

    Stable across replays: same inputs always produce the same key.
    """
    data = {
        "change_id": change_id,
        "bu_id": bu_id,
        "recipient_id": recipient_id,
        "message_variant_id": message_variant_id,
    }
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def has_recent_duplicate(
    dedupe_key: str,
    audit_reader: AuditReader,
    window_hours: int,
) -> bool:
    """Return True if a delivery_attempt record with input_hash == dedupe_key exists in window.

    Scans all DELIVERY_ATTEMPT records in the audit log within the last window_hours.
    For a match to occur, the record's input_hash must equal the dedupe_key — this
    requires the delivery record was written using compute_dedupe_key as the input_hash.
    """
    records = audit_reader.read_recent_events(EventType.DELIVERY_ATTEMPT, window_hours)
    return any(r.input_hash == dedupe_key for r in records)
