"""Normalizer — converts raw source payloads to ChangeArtifact instances.

All ingest adapters funnel through ``normalize_to_change_artifact``.  This
function applies redaction, sets defaults for generated fields (change_id,
ingested_at), and validates the result against the ChangeArtifact model.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pulsecraft.schemas.change_artifact import (
    Author,
    ChangeArtifact,
    RelatedRef,
    RolloutHints,
    SourceType,
)
from pulsecraft.skills.ingest.errors import IngestMalformed
from pulsecraft.skills.ingest.redaction import redact

_VALID_SOURCE_TYPES = {st.value for st in SourceType}


def normalize_to_change_artifact(
    *,
    source_type: str,
    source_ref: str,
    title: str,
    raw_text: str,
    author: Author | None = None,
    related_refs: list[RelatedRef] | None = None,
    links: list[str] | None = None,
    labels: list[str] | None = None,
    rollout_hints: RolloutHints | None = None,
    ingested_at: datetime | None = None,
    change_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> ChangeArtifact:
    """Build and validate a ``ChangeArtifact`` from normalized field values.

    Parameters
    ----------
    source_type:
        Must be one of the ``SourceType`` enum values (e.g. ``"release_note"``).
    source_ref:
        Opaque source-system identifier (e.g. ``"RN-2026-042"``).
    title:
        Display title; max 500 characters.
    raw_text:
        Full text of the artifact.  Always run through ``redact()`` before
        storage — callers need not pre-redact.
    author:
        Optional ``Author`` instance.
    related_refs:
        Optional list of ``RelatedRef`` instances.
    links:
        Optional list of internal URI strings.
    labels:
        Optional list of string tags.
    rollout_hints:
        Optional ``RolloutHints`` instance.
    ingested_at:
        UTC-aware datetime.  Defaults to ``datetime.now(timezone.utc)``.
    change_id:
        UUID v4 string.  Generated via ``uuid.uuid4()`` if not provided.
    extra:
        Unused; reserved for forward compatibility.

    Returns
    -------
    ChangeArtifact
        Validated instance.

    Raises
    ------
    IngestMalformed
        If ``source_type`` is not a recognised ``SourceType`` value, or if
        Pydantic validation fails for any other reason.
    """
    if source_type not in _VALID_SOURCE_TYPES:
        raise IngestMalformed(
            f"Unknown source_type {source_type!r}. Valid values: {sorted(_VALID_SOURCE_TYPES)}"
        )

    resolved_change_id = change_id if change_id is not None else str(uuid.uuid4())
    resolved_ingested_at = ingested_at if ingested_at is not None else datetime.now(UTC)

    try:
        return ChangeArtifact.model_validate(
            {
                "schema_version": "1.0",
                "change_id": resolved_change_id,
                "source_type": source_type,
                "source_ref": source_ref,
                "ingested_at": resolved_ingested_at,
                "title": title,
                "raw_text": redact(raw_text),
                "author": author.model_dump() if author is not None else None,
                "related_refs": [r.model_dump() for r in (related_refs or [])],
                "links": links or [],
                "labels": labels or [],
                "rollout_hints": rollout_hints.model_dump() if rollout_hints is not None else None,
            }
        )
    except Exception as exc:
        raise IngestMalformed(f"ChangeArtifact validation failed: {exc}") from exc
