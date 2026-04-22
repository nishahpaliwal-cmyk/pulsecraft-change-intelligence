"""Ingest adapter for feature flag source artifacts.

Dev mode (transport=None): reads from fixtures/sources/feature_flags/<source_ref>.json.
Production mode: caller supplies a transport callable.

Stub payload shape::

    {
        "flag_id": str,
        "name": str,
        "description": str,
        "state": "experiment" | "ramping" | "ga" | "sunset",
        "rollout_percentage": int,
        "target_audiences": list[str],
        "owner_team": str
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

_FIXTURES_ROOT = (
    Path(__file__).parent.parent.parent.parent.parent / "fixtures" / "sources" / "feature_flags"
)

_VALID_STATES = {"experiment", "ramping", "ga", "sunset"}


def _load_from_fixture(source_ref: str) -> dict[str, Any]:
    fixture_path = _FIXTURES_ROOT / f"{source_ref}.json"
    if not fixture_path.exists():
        raise IngestNotFound(f"Feature flag fixture not found: {fixture_path}")
    try:
        return cast(dict[str, Any], json.loads(fixture_path.read_text(encoding="utf-8")))
    except json.JSONDecodeError as exc:
        raise IngestMalformed(f"Fixture JSON parse error for {source_ref!r}: {exc}") from exc


def fetch_feature_flag(
    source_ref: str,
    *,
    transport: Callable[[str], dict] | None = None,
) -> ChangeArtifact:
    """Fetch and normalize a feature flag artifact.

    Parameters
    ----------
    source_ref:
        Feature flag identifier (e.g. ``"FLAG-99"``).
    transport:
        Optional callable ``(source_ref) -> dict``.  When ``None``, reads from
        the stub fixture file at
        ``fixtures/sources/feature_flags/<source_ref>.json``.

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
        flag_name = payload["name"]
        description = payload["description"]
        state = payload["state"]
        rollout_percentage: int | None = payload.get("rollout_percentage")
        target_audiences: list[str] = payload.get("target_audiences", [])
        owner_team: str = payload.get("owner_team", "<unknown-team>")
    except KeyError as exc:
        raise IngestMalformed(f"Feature flag payload missing required field: {exc}") from exc

    if state not in _VALID_STATES:
        raise IngestMalformed(
            f"Feature flag state {state!r} is not valid. Valid values: {sorted(_VALID_STATES)}"
        )

    title = f"Feature flag: {flag_name} [{state}]"

    ramp_desc: str | None = None
    if rollout_percentage is not None:
        ramp_desc = f"{rollout_percentage}% rollout"

    rollout_hints = RolloutHints(
        ramp=ramp_desc,
        target_population=", ".join(target_audiences) if target_audiences else None,
    )

    labels = [f"state:{state}", f"team:{owner_team}"]

    # Compose raw_text from flag description + metadata
    raw_text_parts = [description]
    if rollout_percentage is not None:
        raw_text_parts.append(f"Rollout: {rollout_percentage}%")
    if target_audiences:
        raw_text_parts.append(f"Target audiences: {', '.join(target_audiences)}")
    raw_text_parts.append(f"Owner team: {owner_team}")
    raw_text = "\n".join(raw_text_parts)

    author = Author(name=owner_team, role="owner_team")

    return normalize_to_change_artifact(
        source_type="feature_flag",
        source_ref=source_ref,
        title=title,
        raw_text=raw_text,
        author=author,
        labels=labels,
        rollout_hints=rollout_hints,
        ingested_at=datetime.now(UTC),
    )
