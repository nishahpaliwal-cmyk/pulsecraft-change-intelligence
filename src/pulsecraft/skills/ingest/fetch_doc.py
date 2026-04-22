"""Ingest adapter for document source artifacts.

Dev mode (transport=None): reads from fixtures/sources/docs/<source_ref>.json.
Production mode: caller supplies a transport callable.

Stub payload shape::

    {
        "doc_id": str,
        "title": str,
        "markdown_content": str,
        "author": str,
        "last_modified": str,       # ISO-8601
        "folder_path": str
    }
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from pulsecraft.schemas.change_artifact import Author, ChangeArtifact
from pulsecraft.skills.ingest.errors import IngestMalformed, IngestNotFound
from pulsecraft.skills.ingest.normalizer import normalize_to_change_artifact

_FIXTURES_ROOT = Path(__file__).parent.parent.parent.parent.parent / "fixtures" / "sources" / "docs"


def _load_from_fixture(source_ref: str) -> dict[str, Any]:
    fixture_path = _FIXTURES_ROOT / f"{source_ref}.json"
    if not fixture_path.exists():
        raise IngestNotFound(f"Doc fixture not found: {fixture_path}")
    try:
        return cast(dict[str, Any], json.loads(fixture_path.read_text(encoding="utf-8")))
    except json.JSONDecodeError as exc:
        raise IngestMalformed(f"Fixture JSON parse error for {source_ref!r}: {exc}") from exc


def fetch_doc(
    source_ref: str,
    *,
    transport: Callable[[str], dict] | None = None,
) -> ChangeArtifact:
    """Fetch and normalize a document artifact.

    Parameters
    ----------
    source_ref:
        Document identifier (e.g. ``"DOC-42"``).
    transport:
        Optional callable ``(source_ref) -> dict``.  When ``None``, reads from
        the stub fixture file at ``fixtures/sources/docs/<source_ref>.json``.

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
        markdown_content = payload["markdown_content"]
        author_name = payload.get("author", "<unknown-author>")
        folder_path = payload.get("folder_path", "")
    except KeyError as exc:
        raise IngestMalformed(f"Doc payload missing required field: {exc}") from exc

    last_modified_str: str | None = payload.get("last_modified")
    ingested_at: datetime | None = None
    if last_modified_str:
        try:
            ingested_at = datetime.fromisoformat(last_modified_str.replace("Z", "+00:00"))
        except ValueError:
            ingested_at = None

    author = Author(name=author_name, role=None)

    # Include folder path as a label for discoverability
    labels: list[str] = []
    if folder_path:
        labels.append(f"folder:{folder_path}")

    return normalize_to_change_artifact(
        source_type="doc",
        source_ref=source_ref,
        title=title,
        raw_text=markdown_content,
        author=author,
        labels=labels,
        ingested_at=ingested_at or datetime.now(UTC),
    )
