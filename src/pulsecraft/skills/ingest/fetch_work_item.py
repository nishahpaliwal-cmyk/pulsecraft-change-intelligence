"""Ingest adapter for work item source artifacts (Jira and ADO).

Dev mode (transport=None): reads from fixtures/sources/work_items/<source_ref>.json.
Production mode: caller supplies a transport callable.

Stub payload shape::

    {
        "key": str,                        # e.g. "JIRA-ALPHA-1234" or "ADO-5678"
        "fields": {
            "summary": str,
            "description": str,
            "status": str,
            "priority": str,
            "assignee": str,
            "labels": list[str],
            "linked_items": list[{"type": str, "ref": str}]
        }
    }

The ``source_type`` parameter controls whether the artifact is tagged as
``"jira_work_item"`` or ``"ado_work_item"``.  The adapter auto-detects from
the key prefix when ``source_type`` is not explicitly supplied.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from pulsecraft.schemas.change_artifact import (
    Author,
    ChangeArtifact,
    RelatedRef,
    RelationKind,
    SourceType,
)
from pulsecraft.skills.ingest.errors import IngestMalformed, IngestNotFound
from pulsecraft.skills.ingest.normalizer import normalize_to_change_artifact

_FIXTURES_ROOT = (
    Path(__file__).parent.parent.parent.parent.parent / "fixtures" / "sources" / "work_items"
)

_ADO_PREFIX = "ADO-"
_JIRA_PREFIX = "JIRA-"


def _detect_source_type(source_ref: str) -> str:
    """Infer source_type from key prefix when not explicitly provided."""
    if source_ref.upper().startswith(_ADO_PREFIX):
        return SourceType.ADO_WORK_ITEM.value
    return SourceType.JIRA_WORK_ITEM.value


def _load_from_fixture(source_ref: str) -> dict[str, Any]:
    fixture_path = _FIXTURES_ROOT / f"{source_ref}.json"
    if not fixture_path.exists():
        raise IngestNotFound(f"Work item fixture not found: {fixture_path}")
    try:
        return cast(dict[str, Any], json.loads(fixture_path.read_text(encoding="utf-8")))
    except json.JSONDecodeError as exc:
        raise IngestMalformed(f"Fixture JSON parse error for {source_ref!r}: {exc}") from exc


def fetch_work_item(
    source_ref: str,
    *,
    source_type: str = "jira_work_item",
    transport: Callable[[str], dict] | None = None,
) -> ChangeArtifact:
    """Fetch and normalize a Jira or ADO work item artifact.

    Parameters
    ----------
    source_ref:
        Work item identifier (e.g. ``"JIRA-ALPHA-1234"`` or ``"ADO-5678"``).
    source_type:
        ``"jira_work_item"`` or ``"ado_work_item"``.  Defaults to
        ``"jira_work_item"``; auto-detected from key prefix when the source_ref
        begins with ``"ADO-"``.
    transport:
        Optional callable ``(source_ref) -> dict``.  When ``None``, reads from
        the stub fixture file.

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
    # Auto-detect source_type from prefix if not explicitly overridden
    resolved_source_type = (
        _detect_source_type(source_ref)
        if source_type == "jira_work_item" and source_ref.upper().startswith(_ADO_PREFIX)
        else source_type
    )

    payload: dict = (
        transport(source_ref) if transport is not None else _load_from_fixture(source_ref)
    )

    try:
        fields: dict = payload["fields"]
        summary: str = fields["summary"]
        description: str = fields.get("description", "")
        assignee_name: str = fields.get("assignee", "<unknown-author>")
        labels: list[str] = fields.get("labels", [])
        linked_items: list[dict] = fields.get("linked_items", [])
    except KeyError as exc:
        raise IngestMalformed(f"Work item payload missing required field: {exc}") from exc

    # Build related refs from linked_items
    related_refs: list[RelatedRef] = []
    for item in linked_items:
        item_ref = item.get("ref", "")
        if item_ref:
            item_type = _detect_source_type(item_ref)
            related_refs.append(
                RelatedRef(
                    type=SourceType(item_type),
                    ref=item_ref,
                    relation=RelationKind.REFERENCES,
                )
            )

    author = Author(name=assignee_name, role=None)

    # Combine summary + description as raw_text
    raw_text = f"{summary}\n\n{description}".strip()

    return normalize_to_change_artifact(
        source_type=resolved_source_type,
        source_ref=source_ref,
        title=summary,
        raw_text=raw_text,
        author=author,
        labels=labels,
        related_refs=related_refs,
        ingested_at=datetime.now(UTC),
    )
