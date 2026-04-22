"""Unit tests for pulsecraft.skills.ingest.fetch_doc."""

from __future__ import annotations

import pytest

from pulsecraft.schemas.change_artifact import ChangeArtifact
from pulsecraft.skills.ingest.errors import IngestMalformed, IngestNotFound
from pulsecraft.skills.ingest.fetch_doc import fetch_doc


class TestHappyPath:
    def test_returns_change_artifact(self) -> None:
        artifact = fetch_doc("DOC-42")
        assert isinstance(artifact, ChangeArtifact)

    def test_source_type_is_doc(self) -> None:
        artifact = fetch_doc("DOC-42")
        assert artifact.source_type.value == "doc"

    def test_source_ref_preserved(self) -> None:
        artifact = fetch_doc("DOC-42")
        assert artifact.source_ref == "DOC-42"

    def test_title_non_empty(self) -> None:
        artifact = fetch_doc("DOC-42")
        assert artifact.title.strip()

    def test_raw_text_is_markdown_content(self) -> None:
        artifact = fetch_doc("DOC-42")
        # The markdown content starts with a heading
        assert "#" in artifact.raw_text

    def test_folder_path_in_labels(self) -> None:
        artifact = fetch_doc("DOC-42")
        assert any("folder:" in label for label in artifact.labels)

    def test_author_populated(self) -> None:
        artifact = fetch_doc("DOC-42")
        assert artifact.author is not None


class TestIngestNotFound:
    def test_unknown_ref_raises(self) -> None:
        with pytest.raises(IngestNotFound):
            fetch_doc("DOC-99999")


class TestIngestMalformed:
    def test_missing_title_raises(self) -> None:
        def bad_transport(ref: str) -> dict:
            return {
                "doc_id": "DOC-TEST",
                "markdown_content": "Some content",
                "author": "<author>",
                "last_modified": "2026-04-10T11:00:00Z",
            }

        with pytest.raises(IngestMalformed):
            fetch_doc("DOC-TEST", transport=bad_transport)

    def test_missing_markdown_content_raises(self) -> None:
        def bad_transport(ref: str) -> dict:
            return {
                "doc_id": "DOC-TEST",
                "title": "A Title",
                "author": "<author>",
                "last_modified": "2026-04-10T11:00:00Z",
            }

        with pytest.raises(IngestMalformed):
            fetch_doc("DOC-TEST", transport=bad_transport)

    def test_transport_override_works(self) -> None:
        def custom_transport(ref: str) -> dict:
            return {
                "doc_id": "DOC-CUSTOM",
                "title": "Custom Doc",
                "markdown_content": "# Custom\n\nContent here.",
                "author": "<custom-author>",
                "last_modified": "2026-01-01T00:00:00Z",
                "folder_path": "/custom/path",
            }

        artifact = fetch_doc("DOC-CUSTOM", transport=custom_transport)
        assert artifact.title == "Custom Doc"
        assert artifact.source_ref == "DOC-CUSTOM"
