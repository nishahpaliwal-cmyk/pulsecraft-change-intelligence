"""Unit tests for pulsecraft.skills.ingest.fetch_release_note."""

from __future__ import annotations

import pytest

from pulsecraft.schemas.change_artifact import ChangeArtifact
from pulsecraft.skills.ingest.errors import IngestMalformed, IngestNotFound
from pulsecraft.skills.ingest.fetch_release_note import fetch_release_note


class TestHappyPath:
    def test_returns_change_artifact(self) -> None:
        artifact = fetch_release_note("RN-2026-042")
        assert isinstance(artifact, ChangeArtifact)

    def test_source_type_is_release_note(self) -> None:
        artifact = fetch_release_note("RN-2026-042")
        assert artifact.source_type.value == "release_note"

    def test_source_ref_preserved(self) -> None:
        artifact = fetch_release_note("RN-2026-042")
        assert artifact.source_ref == "RN-2026-042"

    def test_title_non_empty(self) -> None:
        artifact = fetch_release_note("RN-2026-042")
        assert artifact.title.strip()

    def test_raw_text_non_empty(self) -> None:
        artifact = fetch_release_note("RN-2026-042")
        assert artifact.raw_text.strip()

    def test_rollout_hints_populated(self) -> None:
        artifact = fetch_release_note("RN-2026-042")
        assert artifact.rollout_hints is not None
        assert artifact.rollout_hints.start_date == "2026-04-15"

    def test_labels_populated(self) -> None:
        artifact = fetch_release_note("RN-2026-042")
        assert "api-change" in artifact.labels

    def test_author_populated(self) -> None:
        artifact = fetch_release_note("RN-2026-042")
        assert artifact.author is not None
        assert artifact.author.name

    def test_second_fixture_rn_2026_099(self) -> None:
        artifact = fetch_release_note("RN-2026-099")
        assert isinstance(artifact, ChangeArtifact)
        assert "security" in artifact.labels


class TestIngestNotFound:
    def test_unknown_ref_raises(self) -> None:
        with pytest.raises(IngestNotFound):
            fetch_release_note("RN-9999-999")


class TestIngestMalformed:
    def test_missing_title_raises(self) -> None:
        def bad_transport(ref: str) -> dict:
            return {
                "body": "some body",
                "author_name": "<author>",
                "published_at": "2026-04-15T09:00:00Z",
            }

        with pytest.raises(IngestMalformed):
            fetch_release_note("RN-TEST", transport=bad_transport)

    def test_missing_body_raises(self) -> None:
        def bad_transport(ref: str) -> dict:
            return {
                "title": "Some Title",
                "author_name": "<author>",
                "published_at": "2026-04-15T09:00:00Z",
            }

        with pytest.raises(IngestMalformed):
            fetch_release_note("RN-TEST", transport=bad_transport)


class TestTransportOverride:
    def test_transport_used_instead_of_fixture(self) -> None:
        called_with: list[str] = []

        def custom_transport(ref: str) -> dict:
            called_with.append(ref)
            return {
                "release_id": "RN-CUSTOM",
                "title": "Custom Transport Title",
                "body": "Custom body text.",
                "author_name": "<custom-author>",
                "published_at": "2026-01-01T00:00:00Z",
                "tags": ["custom"],
            }

        artifact = fetch_release_note("RN-CUSTOM", transport=custom_transport)
        assert called_with == ["RN-CUSTOM"]
        assert artifact.title == "Custom Transport Title"
        assert artifact.source_ref == "RN-CUSTOM"

    def test_transport_raising_not_found_propagates(self) -> None:
        def failing_transport(ref: str) -> dict:
            raise IngestNotFound(f"Not found: {ref}")

        with pytest.raises(IngestNotFound):
            fetch_release_note("RN-MISSING", transport=failing_transport)
