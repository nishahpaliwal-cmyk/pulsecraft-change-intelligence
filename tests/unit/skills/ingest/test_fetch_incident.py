"""Unit tests for pulsecraft.skills.ingest.fetch_incident."""

from __future__ import annotations

import pytest

from pulsecraft.schemas.change_artifact import ChangeArtifact
from pulsecraft.skills.ingest.errors import IngestMalformed, IngestNotFound
from pulsecraft.skills.ingest.fetch_incident import fetch_incident


class TestHappyPath:
    def test_returns_change_artifact(self) -> None:
        artifact = fetch_incident("INC-2026-001")
        assert isinstance(artifact, ChangeArtifact)

    def test_source_type_is_incident(self) -> None:
        artifact = fetch_incident("INC-2026-001")
        assert artifact.source_type.value == "incident"

    def test_source_ref_preserved(self) -> None:
        artifact = fetch_incident("INC-2026-001")
        assert artifact.source_ref == "INC-2026-001"

    def test_title_non_empty(self) -> None:
        artifact = fetch_incident("INC-2026-001")
        assert artifact.title.strip()

    def test_severity_in_labels(self) -> None:
        artifact = fetch_incident("INC-2026-001")
        assert "severity:P1" in artifact.labels

    def test_status_in_labels(self) -> None:
        artifact = fetch_incident("INC-2026-001")
        assert "status:resolved" in artifact.labels

    def test_affected_components_in_labels(self) -> None:
        artifact = fetch_incident("INC-2026-001")
        assert "component:order-submission-api" in artifact.labels

    def test_raw_text_contains_summary(self) -> None:
        artifact = fetch_incident("INC-2026-001")
        assert "latency" in artifact.raw_text.lower()

    def test_ingested_at_from_created_at(self) -> None:
        artifact = fetch_incident("INC-2026-001")
        assert artifact.ingested_at.year == 2026
        assert artifact.ingested_at.month == 4
        assert artifact.ingested_at.day == 18


class TestIngestNotFound:
    def test_unknown_ref_raises(self) -> None:
        with pytest.raises(IngestNotFound):
            fetch_incident("INC-9999-999")


class TestIngestMalformed:
    def test_missing_title_raises(self) -> None:
        def bad_transport(ref: str) -> dict:
            return {
                "incident_id": "INC-TEST",
                "summary": "Something went wrong.",
                "severity": "P2",
                "status": "active",
                "affected_components": [],
                "created_at": "2026-04-18T09:00:00Z",
            }

        with pytest.raises(IngestMalformed):
            fetch_incident("INC-TEST", transport=bad_transport)

    def test_missing_summary_raises(self) -> None:
        def bad_transport(ref: str) -> dict:
            return {
                "incident_id": "INC-TEST",
                "title": "Something Broke",
                "severity": "P2",
                "status": "active",
                "affected_components": [],
                "created_at": "2026-04-18T09:00:00Z",
            }

        with pytest.raises(IngestMalformed):
            fetch_incident("INC-TEST", transport=bad_transport)

    def test_transport_override_works(self) -> None:
        def custom_transport(ref: str) -> dict:
            return {
                "incident_id": "INC-CUSTOM",
                "title": "Custom Incident",
                "summary": "Custom incident details.",
                "severity": "P2",
                "status": "active",
                "affected_components": ["service-x"],
                "created_at": "2026-04-01T10:00:00Z",
            }

        artifact = fetch_incident("INC-CUSTOM", transport=custom_transport)
        assert artifact.title == "Custom Incident"
        assert artifact.source_ref == "INC-CUSTOM"
