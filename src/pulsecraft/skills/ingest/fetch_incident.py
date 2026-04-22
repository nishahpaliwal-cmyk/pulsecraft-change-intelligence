"""Ingest adapter for incident source artifacts.

Dev mode (transport=None): reads from fixtures/sources/incidents/<source_ref>.json.
Production mode: caller supplies a transport callable.

Stub payload shape::

    {
        "incident_id": str,
        "title": str,
        "summary": str,
        "severity": str,               # e.g. "P1", "P2"
        "status": str,                 # e.g. "resolved", "active"
        "affected_components": list[str],
        "created_at": str,             # ISO-8601
        "resolved_at": str | None      # ISO-8601, optional
    }
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from pulsecraft.schemas.change_artifact import ChangeArtifact
from pulsecraft.skills.ingest.errors import IngestMalformed, IngestNotFound
from pulsecraft.skills.ingest.normalizer import normalize_to_change_artifact

_FIXTURES_ROOT = (
    Path(__file__).parent.parent.parent.parent.parent / "fixtures" / "sources" / "incidents"
)


def _load_from_fixture(source_ref: str) -> dict[str, Any]:
    fixture_path = _FIXTURES_ROOT / f"{source_ref}.json"
    if not fixture_path.exists():
        raise IngestNotFound(f"Incident fixture not found: {fixture_path}")
    try:
        return cast(dict[str, Any], json.loads(fixture_path.read_text(encoding="utf-8")))
    except json.JSONDecodeError as exc:
        raise IngestMalformed(f"Fixture JSON parse error for {source_ref!r}: {exc}") from exc


def fetch_incident(
    source_ref: str,
    *,
    transport: Callable[[str], dict] | None = None,
) -> ChangeArtifact:
    """Fetch and normalize an incident artifact.

    Parameters
    ----------
    source_ref:
        Incident identifier (e.g. ``"INC-2026-001"``).
    transport:
        Optional callable ``(source_ref) -> dict``.  When ``None``, reads from
        the stub fixture file at
        ``fixtures/sources/incidents/<source_ref>.json``.

    Returns
    -------
    ChangeArtifact

    Raises
    ------
    IngestNotFound
        Fixture file not found (dev mode) or transport signals 404.
    IngestMalformed
        Payload is structurally invalid or missing required fields.
    """
    payload: dict = (
        transport(source_ref) if transport is not None else _load_from_fixture(source_ref)
    )

    try:
        title = payload["title"]
        summary = payload["summary"]
        severity: str = payload.get("severity", "unknown")
        status: str = payload.get("status", "unknown")
        affected_components: list[str] = payload.get("affected_components", [])
        created_at_str: str | None = payload.get("created_at")
    except KeyError as exc:
        raise IngestMalformed(f"Incident payload missing required field: {exc}") from exc

    resolved_at_str: str | None = payload.get("resolved_at")

    # Parse created_at for ingested_at
    ingested_at: datetime | None = None
    if created_at_str:
        try:
            ingested_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
        except ValueError:
            ingested_at = None

    labels = [
        f"severity:{severity}",
        f"status:{status}",
    ] + [f"component:{c}" for c in affected_components]

    # Build raw_text with full context
    raw_text_parts = [summary]
    if affected_components:
        raw_text_parts.append(f"Affected components: {', '.join(affected_components)}")
    raw_text_parts.append(f"Severity: {severity} | Status: {status}")
    if created_at_str:
        raw_text_parts.append(f"Created: {created_at_str}")
    if resolved_at_str:
        raw_text_parts.append(f"Resolved: {resolved_at_str}")
    raw_text = "\n".join(raw_text_parts)

    return normalize_to_change_artifact(
        source_type="incident",
        source_ref=source_ref,
        title=title,
        raw_text=raw_text,
        author=None,
        labels=labels,
        ingested_at=ingested_at or datetime.now(UTC),
    )
