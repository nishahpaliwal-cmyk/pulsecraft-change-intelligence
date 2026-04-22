"""Integration tests — CLI ingest command and run-change command.

These tests call ``pulsecraft`` via subprocess to verify end-to-end behavior
without mocking any internal modules.  Each ingest test:

1. Calls ``pulsecraft ingest <source_type> <source_ref> --output-dir <tmp>``.
2. Reads the generated JSON file.
3. Validates it with ``ChangeArtifact.model_validate()``.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from pulsecraft.schemas.change_artifact import ChangeArtifact

# Path to the pulsecraft CLI entry point inside the venv
_PULSECRAFT = str(Path(sys.executable).parent / "pulsecraft")

# Fixtures root (repo root)
_REPO_ROOT = Path(__file__).parent.parent.parent.parent


def _run_ingest(
    source_type: str,
    source_ref: str,
    tmp_path: Path,
) -> tuple[subprocess.CompletedProcess, Path]:
    """Run ``pulsecraft ingest`` and return (result, output_dir)."""
    result = subprocess.run(
        [_PULSECRAFT, "ingest", source_type, source_ref, "--output-dir", str(tmp_path)],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
    )
    return result, tmp_path


def _find_artifact_file(output_dir: Path) -> Path:
    """Return the first .json file in output_dir, asserting exactly one exists."""
    files = list(output_dir.glob("*.json"))
    assert len(files) == 1, f"Expected 1 artifact JSON, found {len(files)}: {files}"
    return files[0]


class TestIngestReleaseNote:
    def test_release_note_produces_artifact(self, tmp_path: Path) -> None:
        result, out_dir = _run_ingest("release_note", "RN-2026-042", tmp_path)
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        artifact_file = _find_artifact_file(out_dir)
        raw = json.loads(artifact_file.read_text())
        artifact = ChangeArtifact.model_validate(raw)
        assert artifact.source_type.value == "release_note"
        assert artifact.source_ref == "RN-2026-042"


class TestIngestJiraWorkItem:
    def test_jira_work_item_produces_artifact(self, tmp_path: Path) -> None:
        result, out_dir = _run_ingest("jira_work_item", "JIRA-ALPHA-1234", tmp_path)
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        artifact_file = _find_artifact_file(out_dir)
        raw = json.loads(artifact_file.read_text())
        artifact = ChangeArtifact.model_validate(raw)
        assert artifact.source_type.value == "jira_work_item"
        assert artifact.source_ref == "JIRA-ALPHA-1234"


class TestIngestADOWorkItem:
    def test_ado_work_item_produces_artifact(self, tmp_path: Path) -> None:
        result, out_dir = _run_ingest("ado_work_item", "ADO-5678", tmp_path)
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        artifact_file = _find_artifact_file(out_dir)
        raw = json.loads(artifact_file.read_text())
        artifact = ChangeArtifact.model_validate(raw)
        assert artifact.source_type.value == "ado_work_item"
        assert artifact.source_ref == "ADO-5678"


class TestIngestDoc:
    def test_doc_produces_artifact(self, tmp_path: Path) -> None:
        result, out_dir = _run_ingest("doc", "DOC-42", tmp_path)
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        artifact_file = _find_artifact_file(out_dir)
        raw = json.loads(artifact_file.read_text())
        artifact = ChangeArtifact.model_validate(raw)
        assert artifact.source_type.value == "doc"
        assert artifact.source_ref == "DOC-42"


class TestIngestFeatureFlag:
    def test_feature_flag_produces_artifact(self, tmp_path: Path) -> None:
        result, out_dir = _run_ingest("feature_flag", "FLAG-99", tmp_path)
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        artifact_file = _find_artifact_file(out_dir)
        raw = json.loads(artifact_file.read_text())
        artifact = ChangeArtifact.model_validate(raw)
        assert artifact.source_type.value == "feature_flag"
        assert artifact.source_ref == "FLAG-99"


class TestIngestIncident:
    def test_incident_produces_artifact(self, tmp_path: Path) -> None:
        result, out_dir = _run_ingest("incident", "INC-2026-001", tmp_path)
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        artifact_file = _find_artifact_file(out_dir)
        raw = json.loads(artifact_file.read_text())
        artifact = ChangeArtifact.model_validate(raw)
        assert artifact.source_type.value == "incident"
        assert artifact.source_ref == "INC-2026-001"


class TestRunChangeStillWorks:
    def test_run_change_with_existing_fixture(self, tmp_path: Path) -> None:
        """Verify the run-change command still works after CLI restructure."""
        fixture = _REPO_ROOT / "fixtures" / "changes" / "change_001_clearcut_communicate.json"
        result = subprocess.run(
            [
                _PULSECRAFT,
                "run-change",
                str(fixture),
                "--audit-dir",
                str(tmp_path / "audit"),
                "--queue-dir",
                str(tmp_path / "queue"),
            ],
            capture_output=True,
            text=True,
            cwd=str(_REPO_ROOT),
        )
        assert result.returncode == 0, (
            f"run-change failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )


class TestIngestArtifactSchema:
    def test_generated_artifact_roundtrips_cleanly(self, tmp_path: Path) -> None:
        """Generated JSON must round-trip through ChangeArtifact without errors."""
        result, out_dir = _run_ingest("release_note", "RN-2026-099", tmp_path)
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        artifact_file = _find_artifact_file(out_dir)
        raw = json.loads(artifact_file.read_text())
        # model_validate should not raise
        artifact = ChangeArtifact.model_validate(raw)
        # Re-serialise and re-parse once more (full round-trip)
        round_tripped = ChangeArtifact.model_validate(json.loads(artifact.model_dump_json()))
        assert round_tripped.change_id == artifact.change_id
        assert round_tripped.source_ref == artifact.source_ref
