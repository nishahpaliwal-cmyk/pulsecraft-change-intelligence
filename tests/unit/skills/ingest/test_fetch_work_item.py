"""Unit tests for pulsecraft.skills.ingest.fetch_work_item."""

from __future__ import annotations

import pytest

from pulsecraft.schemas.change_artifact import ChangeArtifact
from pulsecraft.skills.ingest.errors import IngestMalformed, IngestNotFound
from pulsecraft.skills.ingest.fetch_work_item import fetch_work_item


_JIRA_PAYLOAD = {
    "key": "JIRA-ALPHA-1234",
    "fields": {
        "summary": "Test Jira story summary",
        "description": "Test description.",
        "status": "In Progress",
        "priority": "High",
        "assignee": "<engineer-test>",
        "labels": ["test-label"],
        "linked_items": [],
    },
}

_ADO_PAYLOAD = {
    "key": "ADO-5678",
    "fields": {
        "summary": "Test ADO work item summary",
        "description": "ADO description.",
        "status": "Ready for Dev",
        "priority": "Medium",
        "assignee": "<engineer-delta>",
        "labels": ["ado-label"],
        "linked_items": [],
    },
}


class TestJiraRef:
    def test_returns_change_artifact(self) -> None:
        artifact = fetch_work_item("JIRA-ALPHA-1234")
        assert isinstance(artifact, ChangeArtifact)

    def test_source_type_jira(self) -> None:
        artifact = fetch_work_item("JIRA-ALPHA-1234")
        assert artifact.source_type.value == "jira_work_item"

    def test_source_ref_preserved(self) -> None:
        artifact = fetch_work_item("JIRA-ALPHA-1234")
        assert artifact.source_ref == "JIRA-ALPHA-1234"

    def test_labels_populated(self) -> None:
        artifact = fetch_work_item("JIRA-ALPHA-1234")
        assert "prior-authorization" in artifact.labels

    def test_title_from_summary(self) -> None:
        def transport(ref: str) -> dict:
            return _JIRA_PAYLOAD

        artifact = fetch_work_item("JIRA-ALPHA-1234", transport=transport)
        assert artifact.title == "Test Jira story summary"


class TestADORef:
    def test_returns_change_artifact(self) -> None:
        artifact = fetch_work_item("ADO-5678")
        assert isinstance(artifact, ChangeArtifact)

    def test_source_type_ado(self) -> None:
        artifact = fetch_work_item("ADO-5678", source_type="ado_work_item")
        assert artifact.source_type.value == "ado_work_item"

    def test_ado_source_type_auto_detected(self) -> None:
        # When source_type="jira_work_item" but ref starts with ADO-, it should auto-detect ADO
        def transport(ref: str) -> dict:
            return _ADO_PAYLOAD

        artifact = fetch_work_item("ADO-5678", transport=transport)
        assert artifact.source_type.value == "ado_work_item"

    def test_linked_items_become_related_refs(self) -> None:
        artifact = fetch_work_item("ADO-5678")
        # ADO-5678 fixture has linked_items: [{"type": "related", "ref": "ADO-5601"}]
        assert len(artifact.related_refs) == 1
        assert artifact.related_refs[0].ref == "ADO-5601"


class TestIngestNotFound:
    def test_unknown_ref_raises(self) -> None:
        with pytest.raises(IngestNotFound):
            fetch_work_item("JIRA-UNKNOWN-9999")


class TestIngestMalformed:
    def test_missing_fields_key_raises(self) -> None:
        def bad_transport(ref: str) -> dict:
            return {"key": "JIRA-TEST"}  # missing "fields"

        with pytest.raises(IngestMalformed):
            fetch_work_item("JIRA-TEST", transport=bad_transport)

    def test_missing_summary_raises(self) -> None:
        def bad_transport(ref: str) -> dict:
            return {
                "key": "JIRA-TEST",
                "fields": {"description": "no summary here", "labels": [], "linked_items": []},
            }

        with pytest.raises(IngestMalformed):
            fetch_work_item("JIRA-TEST", transport=bad_transport)


class TestSourceTypeDiscriminator:
    def test_explicit_jira_source_type(self) -> None:
        def transport(ref: str) -> dict:
            return _JIRA_PAYLOAD

        artifact = fetch_work_item(
            "JIRA-ALPHA-1234", source_type="jira_work_item", transport=transport
        )
        assert artifact.source_type.value == "jira_work_item"

    def test_explicit_ado_source_type(self) -> None:
        def transport(ref: str) -> dict:
            return _ADO_PAYLOAD

        artifact = fetch_work_item("ADO-5678", source_type="ado_work_item", transport=transport)
        assert artifact.source_type.value == "ado_work_item"
