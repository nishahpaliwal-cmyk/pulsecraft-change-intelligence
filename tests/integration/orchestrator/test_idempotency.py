"""Tests for orchestrator idempotency — running the same fixture twice should produce
the same terminal state and the same number of audit records."""

import json
from pathlib import Path

from pulsecraft.orchestrator.audit import AuditWriter
from pulsecraft.orchestrator.engine import Orchestrator
from pulsecraft.orchestrator.hitl import HITLQueue
from pulsecraft.orchestrator.mock_agents import MockBUAtlas, MockPushPilot, MockSignalScribe
from pulsecraft.schemas.change_artifact import ChangeArtifact

FIXTURES_DIR = Path(__file__).parent.parent.parent.parent / "fixtures" / "changes"


def _load(filename: str) -> ChangeArtifact:
    return ChangeArtifact.model_validate(
        json.loads((FIXTURES_DIR / filename).read_text(encoding="utf-8"))
    )


def _run(artifact: ChangeArtifact, tmp_path: Path) -> tuple[str, int]:
    audit = AuditWriter(root=tmp_path / "audit")
    hitl = HITLQueue(audit_writer=audit, root=tmp_path / "queue")
    orch = Orchestrator(
        signalscribe=MockSignalScribe(),
        buatlas=MockBUAtlas(),
        pushpilot=MockPushPilot(),
        audit_writer=audit,
        hitl_queue=hitl,
    )
    result = orch.run_change(artifact)
    return str(result.terminal_state), result.audit_record_count


class TestIdempotency:
    def test_same_fixture_same_terminal_state(self, tmp_path: Path) -> None:
        artifact = _load("change_001_clearcut_communicate.json")
        state1, _ = _run(artifact, tmp_path / "run1")
        state2, _ = _run(artifact, tmp_path / "run2")
        assert state1 == state2

    def test_same_fixture_same_audit_record_count(self, tmp_path: Path) -> None:
        artifact = _load("change_001_clearcut_communicate.json")
        _, count1 = _run(artifact, tmp_path / "run1")
        _, count2 = _run(artifact, tmp_path / "run2")
        assert count1 == count2

    def test_different_changes_independent(self, tmp_path: Path) -> None:
        a1 = _load("change_001_clearcut_communicate.json")
        a2 = _load("change_002_pure_internal_refactor.json")

        audit = AuditWriter(root=tmp_path / "audit")
        hitl = HITLQueue(audit_writer=audit, root=tmp_path / "queue")
        orch = Orchestrator(
            signalscribe=MockSignalScribe(),
            buatlas=MockBUAtlas(),
            pushpilot=MockPushPilot(),
            audit_writer=audit,
            hitl_queue=hitl,
        )

        orch.run_change(a1)
        orch.run_change(a2)

        # Each change has its own audit chain
        chain1 = audit.read_chain(a1.change_id)
        chain2 = audit.read_chain(a2.change_id)
        assert all(r.change_id == a1.change_id for r in chain1)
        assert all(r.change_id == a2.change_id for r in chain2)
