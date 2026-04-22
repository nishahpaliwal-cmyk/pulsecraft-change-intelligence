"""Ingest skills — source adapters that produce ChangeArtifact instances.

Public API::

    from pulsecraft.skills.ingest import (
        fetch_release_note,
        fetch_work_item,
        fetch_doc,
        fetch_feature_flag,
        fetch_incident,
        normalize_to_change_artifact,
        redact,
        IngestNotFound,
        IngestUnauthorized,
        IngestMalformed,
    )
"""

from __future__ import annotations

from pulsecraft.skills.ingest.errors import IngestMalformed, IngestNotFound, IngestUnauthorized
from pulsecraft.skills.ingest.fetch_doc import fetch_doc
from pulsecraft.skills.ingest.fetch_feature_flag import fetch_feature_flag
from pulsecraft.skills.ingest.fetch_incident import fetch_incident
from pulsecraft.skills.ingest.fetch_release_note import fetch_release_note
from pulsecraft.skills.ingest.fetch_work_item import fetch_work_item
from pulsecraft.skills.ingest.normalizer import normalize_to_change_artifact
from pulsecraft.skills.ingest.redaction import redact

__all__ = [
    "fetch_release_note",
    "fetch_work_item",
    "fetch_doc",
    "fetch_feature_flag",
    "fetch_incident",
    "normalize_to_change_artifact",
    "redact",
    "IngestNotFound",
    "IngestUnauthorized",
    "IngestMalformed",
]
