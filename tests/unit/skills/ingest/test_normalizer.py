"""Unit tests for pulsecraft.skills.ingest.normalizer."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from pulsecraft.schemas.change_artifact import ChangeArtifact
from pulsecraft.skills.ingest.errors import IngestMalformed
from pulsecraft.skills.ingest.normalizer import normalize_to_change_artifact


class TestHappyPath:
    def test_returns_change_artifact(self) -> None:
        artifact = normalize_to_change_artifact(
            source_type="release_note",
            source_ref="RN-TEST-001",
            title="Test Release Note",
            raw_text="This is the body of the release note.",
        )
        assert isinstance(artifact, ChangeArtifact)

    def test_schema_version_is_1_0(self) -> None:
        artifact = normalize_to_change_artifact(
            source_type="release_note",
            source_ref="RN-TEST-001",
            title="Test",
            raw_text="body",
        )
        assert artifact.schema_version == "1.0"

    def test_source_type_set(self) -> None:
        artifact = normalize_to_change_artifact(
            source_type="incident",
            source_ref="INC-TEST-001",
            title="Test Incident",
            raw_text="Something broke.",
        )
        assert artifact.source_type.value == "incident"

    def test_source_ref_set(self) -> None:
        artifact = normalize_to_change_artifact(
            source_type="doc",
            source_ref="DOC-99",
            title="Test Doc",
            raw_text="content",
        )
        assert artifact.source_ref == "DOC-99"

    def test_title_set(self) -> None:
        artifact = normalize_to_change_artifact(
            source_type="doc",
            source_ref="DOC-99",
            title="My Title",
            raw_text="content",
        )
        assert artifact.title == "My Title"


class TestDefaultFields:
    def test_change_id_generated_when_not_provided(self) -> None:
        artifact = normalize_to_change_artifact(
            source_type="release_note",
            source_ref="RN-TEST-001",
            title="Test",
            raw_text="body",
        )
        # Must be a valid UUID
        parsed = uuid.UUID(artifact.change_id)
        assert str(parsed) == artifact.change_id

    def test_change_id_used_when_provided(self) -> None:
        fixed_id = "aaaaaaaa-bbbb-4ccc-dddd-eeeeeeeeeeee"
        artifact = normalize_to_change_artifact(
            source_type="release_note",
            source_ref="RN-TEST-001",
            title="Test",
            raw_text="body",
            change_id=fixed_id,
        )
        assert artifact.change_id == fixed_id

    def test_ingested_at_generated_when_not_provided(self) -> None:
        before = datetime.now(UTC)
        artifact = normalize_to_change_artifact(
            source_type="release_note",
            source_ref="RN-TEST-001",
            title="Test",
            raw_text="body",
        )
        after = datetime.now(UTC)
        assert before <= artifact.ingested_at <= after

    def test_ingested_at_used_when_provided(self) -> None:
        ts = datetime(2026, 4, 15, 9, 0, 0, tzinfo=UTC)
        artifact = normalize_to_change_artifact(
            source_type="release_note",
            source_ref="RN-TEST-001",
            title="Test",
            raw_text="body",
            ingested_at=ts,
        )
        assert artifact.ingested_at == ts

    def test_related_refs_defaults_to_empty_list(self) -> None:
        artifact = normalize_to_change_artifact(
            source_type="release_note",
            source_ref="RN-TEST-001",
            title="Test",
            raw_text="body",
        )
        assert artifact.related_refs == []

    def test_labels_defaults_to_empty_list(self) -> None:
        artifact = normalize_to_change_artifact(
            source_type="release_note",
            source_ref="RN-TEST-001",
            title="Test",
            raw_text="body",
        )
        assert artifact.labels == []

    def test_author_defaults_to_none(self) -> None:
        artifact = normalize_to_change_artifact(
            source_type="release_note",
            source_ref="RN-TEST-001",
            title="Test",
            raw_text="body",
        )
        assert artifact.author is None


class TestRedactionApplied:
    def test_email_in_raw_text_is_redacted(self) -> None:
        artifact = normalize_to_change_artifact(
            source_type="release_note",
            source_ref="RN-TEST-001",
            title="Test",
            raw_text="Contact admin@example.com for details.",
        )
        assert "@" not in artifact.raw_text
        assert "[REDACTED]" in artifact.raw_text

    def test_ssn_in_raw_text_is_redacted(self) -> None:
        artifact = normalize_to_change_artifact(
            source_type="incident",
            source_ref="INC-TEST-001",
            title="Test",
            raw_text="Patient SSN: 123-45-6789 found in logs.",
        )
        assert "123-45-6789" not in artifact.raw_text
        assert "[REDACTED]" in artifact.raw_text

    def test_clean_raw_text_unchanged(self) -> None:
        clean = "Order API now supports batch mode for high-volume workflows."
        artifact = normalize_to_change_artifact(
            source_type="release_note",
            source_ref="RN-TEST-001",
            title="Test",
            raw_text=clean,
        )
        assert artifact.raw_text == clean


class TestIngestMalformed:
    def test_invalid_source_type_raises(self) -> None:
        with pytest.raises(IngestMalformed, match="Unknown source_type"):
            normalize_to_change_artifact(
                source_type="unknown_type",
                source_ref="X-001",
                title="Test",
                raw_text="body",
            )

    def test_all_valid_source_types_accepted(self) -> None:
        for st in (
            "release_note",
            "jira_work_item",
            "ado_work_item",
            "doc",
            "feature_flag",
            "incident",
        ):
            artifact = normalize_to_change_artifact(
                source_type=st,
                source_ref="REF-001",
                title="Test",
                raw_text="body",
            )
            assert artifact.source_type.value == st
