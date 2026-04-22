"""Unit tests for pulsecraft.skills.ingest.fetch_feature_flag."""

from __future__ import annotations

import pytest

from pulsecraft.schemas.change_artifact import ChangeArtifact
from pulsecraft.skills.ingest.errors import IngestMalformed, IngestNotFound
from pulsecraft.skills.ingest.fetch_feature_flag import fetch_feature_flag


class TestHappyPath:
    def test_returns_change_artifact_flag_99(self) -> None:
        artifact = fetch_feature_flag("FLAG-99")
        assert isinstance(artifact, ChangeArtifact)

    def test_source_type_is_feature_flag(self) -> None:
        artifact = fetch_feature_flag("FLAG-99")
        assert artifact.source_type.value == "feature_flag"

    def test_source_ref_preserved(self) -> None:
        artifact = fetch_feature_flag("FLAG-99")
        assert artifact.source_ref == "FLAG-99"

    def test_title_contains_flag_name(self) -> None:
        artifact = fetch_feature_flag("FLAG-99")
        assert "batch_order_submission_v2" in artifact.title

    def test_title_contains_state(self) -> None:
        artifact = fetch_feature_flag("FLAG-99")
        assert "ramping" in artifact.title

    def test_rollout_hints_populated(self) -> None:
        artifact = fetch_feature_flag("FLAG-99")
        assert artifact.rollout_hints is not None
        assert "25%" in (artifact.rollout_hints.ramp or "")

    def test_state_in_labels(self) -> None:
        artifact = fetch_feature_flag("FLAG-99")
        assert "state:ramping" in artifact.labels

    def test_experiment_flag_12(self) -> None:
        artifact = fetch_feature_flag("FLAG-12")
        assert isinstance(artifact, ChangeArtifact)
        assert "state:experiment" in artifact.labels

    def test_raw_text_contains_description(self) -> None:
        artifact = fetch_feature_flag("FLAG-99")
        assert "batch order submission" in artifact.raw_text.lower()


class TestIngestNotFound:
    def test_unknown_ref_raises(self) -> None:
        with pytest.raises(IngestNotFound):
            fetch_feature_flag("FLAG-99999")


class TestIngestMalformed:
    def test_missing_name_raises(self) -> None:
        def bad_transport(ref: str) -> dict:
            return {
                "flag_id": "FLAG-TEST",
                "description": "Some flag",
                "state": "ga",
                "rollout_percentage": 100,
                "target_audiences": [],
            }

        with pytest.raises(IngestMalformed):
            fetch_feature_flag("FLAG-TEST", transport=bad_transport)

    def test_invalid_state_raises(self) -> None:
        def bad_transport(ref: str) -> dict:
            return {
                "flag_id": "FLAG-TEST",
                "name": "test_flag",
                "description": "A test flag.",
                "state": "unknown_state",
                "rollout_percentage": 0,
                "target_audiences": [],
                "owner_team": "team-a",
            }

        with pytest.raises(IngestMalformed, match="not valid"):
            fetch_feature_flag("FLAG-TEST", transport=bad_transport)

    def test_valid_states_all_accepted(self) -> None:
        for state in ("experiment", "ramping", "ga", "sunset"):

            def make_transport(s: str):
                def transport(ref: str) -> dict:
                    return {
                        "flag_id": "FLAG-TEST",
                        "name": f"flag_{s}",
                        "description": "desc",
                        "state": s,
                        "rollout_percentage": 0,
                        "target_audiences": [],
                        "owner_team": "team",
                    }

                return transport

            artifact = fetch_feature_flag("FLAG-TEST", transport=make_transport(state))
            assert isinstance(artifact, ChangeArtifact)
