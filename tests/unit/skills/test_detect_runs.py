"""Unit tests for the detect_runs function and run-scoped build_explanation."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from pulsecraft.orchestrator.audit import AuditWriter
from pulsecraft.schemas.audit_record import (
    Actor,
    ActorType,
    AuditDecision,
    AuditOutcome,
    AuditRecord,
    EventType,
)
from pulsecraft.skills.explain_chain import RunNotFound, build_explanation, detect_runs

# ── Helpers ───────────────────────────────────────────────────────────────────


def _ts(offset_seconds: float = 0.0) -> datetime:
    base = datetime(2026, 4, 23, 15, 0, 0, tzinfo=UTC)
    return base + timedelta(seconds=offset_seconds)


def _orchestrator_actor() -> Actor:
    return Actor(type=ActorType.ORCHESTRATOR, id="orchestrator", version="1.0")


def _agent_actor(name: str) -> Actor:
    return Actor(type=ActorType.AGENT, id=name, version="mock-1.0")


def _make_transition(
    change_id: str,
    from_state: str | None,
    to_state: str,
    reason: str = "test",
    timestamp_offset: float = 0.0,
) -> AuditRecord:
    from_str = "None" if from_state is None else from_state
    summary = f"{from_str} → {to_state}: {reason}"
    return AuditRecord(
        audit_id=str(uuid.uuid4()),
        timestamp=_ts(timestamp_offset),
        event_type=EventType.STATE_TRANSITION,
        change_id=change_id,
        actor=_orchestrator_actor(),
        action="transition",
        input_hash=hashlib.sha256(summary.encode()).hexdigest(),
        output_summary=summary,
        outcome=AuditOutcome.SUCCESS,
    )


def _make_agent_record(
    change_id: str,
    agent: str,
    timestamp_offset: float = 0.0,
) -> AuditRecord:
    summary = f"brief_id={uuid.uuid4()} decisions=['COMMUNICATE', 'RIPE', 'READY']"
    return AuditRecord(
        audit_id=str(uuid.uuid4()),
        timestamp=_ts(timestamp_offset),
        event_type=EventType.AGENT_INVOCATION,
        change_id=change_id,
        actor=_agent_actor(agent),
        action="invoked",
        input_hash=hashlib.sha256(summary.encode()).hexdigest(),
        output_summary=summary,
        decision=AuditDecision(gate=1, verb="COMMUNICATE", reason="test"),
        outcome=AuditOutcome.SUCCESS,
    )


def _seed_audit(tmp_path: Path, change_id: str, records: list[AuditRecord]) -> AuditWriter:
    writer = AuditWriter(root=tmp_path / "audit")
    for r in records:
        writer.log_event(r)
    return writer


# ── Tests: detect_runs ────────────────────────────────────────────────────────


class TestDetectRuns:
    def test_empty_records_returns_empty_list(self) -> None:
        assert detect_runs([]) == []

    def test_single_complete_run_one_boundary(self) -> None:
        cid = str(uuid.uuid4())
        records = [
            _make_transition(cid, None, "RECEIVED", timestamp_offset=0),
            _make_transition(cid, "RECEIVED", "INTERPRETED", timestamp_offset=1),
            _make_transition(cid, "INTERPRETED", "DELIVERED", timestamp_offset=5),
        ]
        runs = detect_runs(records)
        assert len(runs) == 1
        rb = runs[0]
        assert rb.run_index == 1
        assert rb.start_idx == 0
        assert rb.terminal_state == "DELIVERED"

    def test_two_sequential_runs_two_boundaries(self) -> None:
        cid = str(uuid.uuid4())
        records = [
            # Run 1
            _make_transition(cid, None, "RECEIVED", timestamp_offset=0),
            _make_transition(cid, "RECEIVED", "INTERPRETED", timestamp_offset=1),
            _make_transition(cid, "INTERPRETED", "DELIVERED", timestamp_offset=5),
            # Run 2
            _make_transition(cid, None, "RECEIVED", timestamp_offset=10),
            _make_transition(cid, "RECEIVED", "INTERPRETED", timestamp_offset=11),
            _make_transition(cid, "INTERPRETED", "FAILED", timestamp_offset=15),
        ]
        runs = detect_runs(records)
        assert len(runs) == 2

        # Run 1
        assert runs[0].run_index == 1
        assert runs[0].start_idx == 0
        assert runs[0].end_idx == 2  # DELIVERED at index 2
        assert runs[0].terminal_state == "DELIVERED"

        # Run 2
        assert runs[1].run_index == 2
        assert runs[1].start_idx == 3
        assert runs[1].end_idx == 5  # FAILED at index 5
        assert runs[1].terminal_state == "FAILED"

    def test_run_without_terminal_state_ends_at_next_received(self) -> None:
        cid = str(uuid.uuid4())
        records = [
            # Run 1: no terminal state reached (e.g., interrupted)
            _make_transition(cid, None, "RECEIVED", timestamp_offset=0),
            _make_transition(cid, "RECEIVED", "INTERPRETED", timestamp_offset=1),
            # Run 2: new run starts here
            _make_transition(cid, None, "RECEIVED", timestamp_offset=10),
            _make_transition(cid, "RECEIVED", "DELIVERED", timestamp_offset=15),
        ]
        runs = detect_runs(records)
        assert len(runs) == 2

        # Run 1 ends just before run 2 starts (index 1 = last record before index 2)
        assert runs[0].end_idx == 1
        assert runs[0].terminal_state is None

        # Run 2 terminates at DELIVERED
        assert runs[1].start_idx == 2
        assert runs[1].terminal_state == "DELIVERED"

    def test_records_with_no_received_treated_as_one_run(self) -> None:
        cid = str(uuid.uuid4())
        # No None → RECEIVED transition, just some records
        records = [
            _make_agent_record(cid, "signalscribe_mock", timestamp_offset=0),
            _make_transition(cid, "RECEIVED", "INTERPRETED", timestamp_offset=1),
        ]
        runs = detect_runs(records)
        # Falls back to single run starting at index 0
        assert len(runs) == 1
        assert runs[0].start_idx == 0
        assert runs[0].end_idx == 1

    def test_awaiting_hitl_is_a_terminal_state(self) -> None:
        cid = str(uuid.uuid4())
        records = [
            _make_transition(cid, None, "RECEIVED", timestamp_offset=0),
            _make_transition(cid, "RECEIVED", "INTERPRETED", timestamp_offset=1),
            _make_transition(cid, "INTERPRETED", "AWAITING_HITL", timestamp_offset=3),
            # Records after terminal should be excluded from this run's end_idx
            _make_agent_record(cid, "signalscribe_mock", timestamp_offset=10),
        ]
        runs = detect_runs(records)
        assert len(runs) == 1
        assert runs[0].terminal_state == "AWAITING_HITL"
        assert runs[0].end_idx == 2  # AWAITING_HITL transition at index 2


# ── Tests: build_explanation with run_selector ─────────────────────────────────


class TestBuildExplanationRunSelector:
    def test_run_selector_negative_one_is_latest(self, tmp_path: Path) -> None:
        cid = str(uuid.uuid4())
        records = [
            # Run 1
            _make_transition(cid, None, "RECEIVED", timestamp_offset=0),
            _make_agent_record(cid, "signalscribe_mock", timestamp_offset=1),
            _make_transition(cid, "RECEIVED", "DELIVERED", timestamp_offset=5),
            # Run 2
            _make_transition(cid, None, "RECEIVED", timestamp_offset=10),
            _make_agent_record(cid, "buatlas_mock", timestamp_offset=11),
            _make_transition(cid, "RECEIVED", "FAILED", timestamp_offset=15),
        ]
        writer = _seed_audit(tmp_path, cid, records)
        exp = build_explanation(cid, writer, run_selector=-1)

        # Should show run 2 (latest)
        assert exp.run_index == 2
        assert exp.run_count == 2
        assert exp.terminal_state == "FAILED"
        # Only the agent from run 2 (buatlas) should appear
        assert len(exp.agent_decisions) == 1
        assert exp.agent_decisions[0].agent == "buatlas"

    def test_run_selector_out_of_range_raises(self, tmp_path: Path) -> None:
        cid = str(uuid.uuid4())
        records = [
            _make_transition(cid, None, "RECEIVED", timestamp_offset=0),
            _make_transition(cid, "RECEIVED", "DELIVERED", timestamp_offset=5),
        ]
        writer = _seed_audit(tmp_path, cid, records)
        with pytest.raises(RunNotFound):
            build_explanation(cid, writer, run_selector=99)

    def test_build_explanation_scopes_to_latest_run_by_default(self, tmp_path: Path) -> None:
        cid = str(uuid.uuid4())
        # Run 1: signalscribe, delivered
        records = [
            _make_transition(cid, None, "RECEIVED", timestamp_offset=0),
            _make_agent_record(cid, "signalscribe_mock", timestamp_offset=1),
            _make_transition(cid, "RECEIVED", "DELIVERED", timestamp_offset=5),
            # Run 2: pushpilot, failed
            _make_transition(cid, None, "RECEIVED", timestamp_offset=100),
            _make_agent_record(cid, "pushpilot_mock", timestamp_offset=101),
            _make_transition(cid, "RECEIVED", "FAILED", timestamp_offset=105),
        ]
        writer = _seed_audit(tmp_path, cid, records)

        # Default (run_selector=-1) → latest run
        exp = build_explanation(cid, writer)
        assert exp.run_count == 2
        assert exp.run_index == 2
        assert exp.terminal_state == "FAILED"
        # Only run-2 agent (pushpilot) included
        agent_names = {d.agent for d in exp.agent_decisions}
        assert "signalscribe" not in agent_names
        assert "pushpilot" in agent_names

    def test_build_explanation_all_returns_full_chain(self, tmp_path: Path) -> None:
        cid = str(uuid.uuid4())
        records = [
            _make_transition(cid, None, "RECEIVED", timestamp_offset=0),
            _make_agent_record(cid, "signalscribe_mock", timestamp_offset=1),
            _make_transition(cid, "RECEIVED", "DELIVERED", timestamp_offset=5),
            _make_transition(cid, None, "RECEIVED", timestamp_offset=100),
            _make_agent_record(cid, "pushpilot_mock", timestamp_offset=101),
            _make_transition(cid, "RECEIVED", "FAILED", timestamp_offset=105),
        ]
        writer = _seed_audit(tmp_path, cid, records)

        exp = build_explanation(cid, writer, run_selector="all")
        # run_index should be None when "all" is used
        assert exp.run_index is None
        assert exp.run_count == 2
        # Both agents from both runs
        agent_names = {d.agent for d in exp.agent_decisions}
        assert "signalscribe" in agent_names
        assert "pushpilot" in agent_names

    def test_build_explanation_select_first_run(self, tmp_path: Path) -> None:
        cid = str(uuid.uuid4())
        records = [
            # Run 1
            _make_transition(cid, None, "RECEIVED", timestamp_offset=0),
            _make_agent_record(cid, "signalscribe_mock", timestamp_offset=1),
            _make_transition(cid, "RECEIVED", "DELIVERED", timestamp_offset=5),
            # Run 2
            _make_transition(cid, None, "RECEIVED", timestamp_offset=100),
            _make_agent_record(cid, "buatlas_mock", timestamp_offset=101),
            _make_transition(cid, "RECEIVED", "FAILED", timestamp_offset=105),
        ]
        writer = _seed_audit(tmp_path, cid, records)

        exp = build_explanation(cid, writer, run_selector=1)
        assert exp.run_index == 1
        assert exp.run_count == 2
        assert exp.terminal_state == "DELIVERED"
        agent_names = {d.agent for d in exp.agent_decisions}
        assert "signalscribe" in agent_names
        assert "buatlas" not in agent_names

    def test_run_count_populated_for_single_run(self, tmp_path: Path) -> None:
        cid = str(uuid.uuid4())
        records = [
            _make_transition(cid, None, "RECEIVED", timestamp_offset=0),
            _make_transition(cid, "RECEIVED", "DELIVERED", timestamp_offset=5),
        ]
        writer = _seed_audit(tmp_path, cid, records)
        exp = build_explanation(cid, writer)
        assert exp.run_count == 1
        assert exp.run_index == 1
