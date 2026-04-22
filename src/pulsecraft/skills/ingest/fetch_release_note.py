"""Ingest adapter for release note source artifacts.

Dev mode (transport=None): reads from fixtures/sources/release_notes/<source_ref>.json.
Production mode: caller supplies a transport callable.

Stub payload shape::

    {
        "release_id": str,
        "title": str,
        "body": str,
        "author_name": str,
        "published_at": str,          # ISO-8601
        "tags": list[str],
        "rollout": {                   # optional
            "start_date": str,
            "ramp": str,
            "target_population": str
        }
    }
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from pulsecraft.schemas.change_artifact import Author, ChangeArtifact, RolloutHints
from pulsecraft.skills.ingest.errors import IngestMalformed, IngestNotFound
from pulsecraft.skills.ingest.normalizer import normalize_to_change_artifact

# Path to stub fixture directory (repo root / fixtures / sources / release_notes)
_FIXTURES_ROOT = (
    Path(__file__).parent.parent.parent.parent.parent / "fixtures" / "sources" / "release_notes"
)


def _load_from_fixture(source_ref: str) -> dict[str, Any]:
    """Read the stub JSON file for *source_ref*."""
    fixture_path = _FIXTURES_ROOT / f"{source_ref}.json"
    if not fixture_path.exists():
        raise IngestNotFound(f"Release note fixture not found: {fixture_path}")
    try:
        return cast(dict[str, Any], json.loads(fixture_path.read_text(encoding="utf-8")))
    except json.JSONDecodeError as exc:
        raise IngestMalformed(f"Fixture JSON parse error for {source_ref!r}: {exc}") from exc


def fetch_release_note(
    source_ref: str,
    *,
    transport: Callable[[str], dict] | None = None,
) -> ChangeArtifact:
    """Fetch and normalize a release note artifact.

    Parameters
    ----------
    source_ref:
        Release note identifier (e.g. ``"RN-2026-042"``).
    transport:
        Optional callable ``(source_ref) -> dict``.  When ``None``, the adapter
        reads from the stub fixture file at
        ``fixtures/sources/release_notes/<source_ref>.json``.  The callable may
        raise :exc:`IngestNotFound`, :exc:`IngestUnauthorized`, or
        :exc:`IngestMalformed` directly.

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
        body = payload["body"]
        author_name = payload.get("author_name", "<unknown-author>")
        tags: list[str] = payload.get("tags", [])
    except KeyError as exc:
        raise IngestMalformed(f"Release note payload missing required field: {exc}") from exc

    # Parse rollout hints if present
    rollout_raw = payload.get("rollout")
    rollout_hints: RolloutHints | None = None
    if rollout_raw:
        rollout_hints = RolloutHints(
            start_date=rollout_raw.get("start_date"),
            ramp=rollout_raw.get("ramp"),
            target_population=rollout_raw.get("target_population"),
        )

    # Parse published_at for ingested_at
    published_at_str: str | None = payload.get("published_at")
    ingested_at: datetime | None = None
    if published_at_str:
        try:
            ingested_at = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
        except ValueError:
            ingested_at = None

    author = Author(name=author_name, role=None)

    return normalize_to_change_artifact(
        source_type="release_note",
        source_ref=source_ref,
        title=title,
        raw_text=body,
        author=author,
        labels=tags,
        rollout_hints=rollout_hints,
        ingested_at=ingested_at or datetime.now(UTC),
    )
