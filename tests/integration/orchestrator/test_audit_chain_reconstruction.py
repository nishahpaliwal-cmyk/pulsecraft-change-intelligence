"""Tests for audit chain reconstruction — after running fixture 001, reading the audit
chain reconstructs the full state transitions and decisions in order."""

import json
from pathlib import Path

from pulsecraft.orchestrator.audit import AuditWriter
from pulsecraft.orchestrator.engine import Orchestrator
from pulsecraft.orchestrator.hitl import HITLQueue
from pulsecraft.orchestrator.mock_agents import MockBUAtlas, MockPushPilot, MockSignalScribe
from pulsecraft.schemas.audit_record import AuditOutcome, EventType
from pulsecraft.schemas.change_artifact import ChangeArtifact

FIXTURES_DIR = Path(__file__).parent.parent.parent.parent / "fixtures" / "changes"


class TestAuditChainReconstruction:
    def test_audit_chain_has_expected_event_types(self, tmp_path: Path) -> None:
        artifact = ChangeArtifact.model_validate(
            json.loads((FIXTURES_DIR / "change_001_clearcut_communicate.json").read_text())
        )
        audit = AuditWriter(root=tmp_path / "audit")
        hitl = HITLQueue(audit_writer=audit, root=tmp_path / "queue")
        orch = Orchestrator(
            signalscribe=MockSignalScribe(),
            buatlas=MockBUAtlas(),
            pushpilot=MockPushPilot(),
            audit_writer=audit,
            hitl_queue=hitl,
        )
        orch.run_change(artifact)
        chain = audit.read_chain(artifact.change_id)

        event_types = [r.event_type for r in chain]
        assert EventType.STATE_TRANSITION in event_types
        assert EventType.AGENT_INVOCATION in event_types
        assert EventType.POLICY_CHECK in event_types
        assert EventType.DELIVERY_ATTEMPT in event_types

    def test_audit_chain_first_record_is_received_transition(self, tmp_path: Path) -> None:
        artifact = ChangeArtifact.model_validate(
            json.loads((FIXTURES_DIR / "change_001_clearcut_communicate.json").read_text())
        )
        audit = AuditWriter(root=tmp_path / "audit")
        hitl = HITLQueue(audit_writer=audit, root=tmp_path / "queue")
        orch = Orchestrator(
            signalscribe=MockSignalScribe(),
            buatlas=MockBUAtlas(),
            pushpilot=MockPushPilot(),
            audit_writer=audit,
            hitl_queue=hitl,
        )
        orch.run_change(artifact)
        chain = audit.read_chain(artifact.change_id)
        first = chain[0]
        assert first.event_type == EventType.STATE_TRANSITION
        assert "RECEIVED" in first.output_summary

    def test_audit_chain_has_signalscribe_invocation(self, tmp_path: Path) -> None:
        artifact = ChangeArtifact.model_validate(
            json.loads((FIXTURES_DIR / "change_001_clearcut_communicate.json").read_text())
        )
        audit = AuditWriter(root=tmp_path / "audit")
        hitl = HITLQueue(audit_writer=audit, root=tmp_path / "queue")
        orch = Orchestrator(
            signalscribe=MockSignalScribe(),
            buatlas=MockBUAtlas(),
            pushpilot=MockPushPilot(),
            audit_writer=audit,
            hitl_queue=hitl,
        )
        orch.run_change(artifact)
        chain = audit.read_chain(artifact.change_id)

        ss_records = [r for r in chain if r.actor.id == "signalscribe_mock"]
        assert len(ss_records) >= 1

    def test_all_records_have_correct_change_id(self, tmp_path: Path) -> None:
        artifact = ChangeArtifact.model_validate(
            json.loads((FIXTURES_DIR / "change_001_clearcut_communicate.json").read_text())
        )
        audit = AuditWriter(root=tmp_path / "audit")
        hitl = HITLQueue(audit_writer=audit, root=tmp_path / "queue")
        orch = Orchestrator(
            signalscribe=MockSignalScribe(),
            buatlas=MockBUAtlas(),
            pushpilot=MockPushPilot(),
            audit_writer=audit,
            hitl_queue=hitl,
        )
        orch.run_change(artifact)
        chain = audit.read_chain(artifact.change_id)
        for record in chain:
            assert record.change_id == artifact.change_id

    def test_all_records_have_success_outcome(self, tmp_path: Path) -> None:
        artifact = ChangeArtifact.model_validate(
            json.loads((FIXTURES_DIR / "change_001_clearcut_communicate.json").read_text())
        )
        audit = AuditWriter(root=tmp_path / "audit")
        hitl = HITLQueue(audit_writer=audit, root=tmp_path / "queue")
        orch = Orchestrator(
            signalscribe=MockSignalScribe(),
            buatlas=MockBUAtlas(),
            pushpilot=MockPushPilot(),
            audit_writer=audit,
            hitl_queue=hitl,
        )
        orch.run_change(artifact)
        chain = audit.read_chain(artifact.change_id)
        for record in chain:
            assert record.outcome in (AuditOutcome.SUCCESS, AuditOutcome.ESCALATED)

    def test_audit_summary_is_human_readable(self, tmp_path: Path) -> None:
        artifact = ChangeArtifact.model_validate(
            json.loads((FIXTURES_DIR / "change_001_clearcut_communicate.json").read_text())
        )
        audit = AuditWriter(root=tmp_path / "audit")
        hitl = HITLQueue(audit_writer=audit, root=tmp_path / "queue")
        orch = Orchestrator(
            signalscribe=MockSignalScribe(),
            buatlas=MockBUAtlas(),
            pushpilot=MockPushPilot(),
            audit_writer=audit,
            hitl_queue=hitl,
        )
        orch.run_change(artifact)
        summary = audit.summary(artifact.change_id)
        assert artifact.change_id in summary
        assert len(summary) > 0
