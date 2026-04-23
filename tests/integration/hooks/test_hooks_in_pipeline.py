"""Integration tests: guardrail hooks fire and produce HOOK_FIRED audit records.

Uses mock agents so no LLM calls are made.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from pulsecraft.config.loader import reload_config
from pulsecraft.hooks.config import HookRegistration
from pulsecraft.orchestrator.audit import AuditWriter
from pulsecraft.orchestrator.engine import Orchestrator
from pulsecraft.orchestrator.hitl import HITLQueue
from pulsecraft.orchestrator.mock_agents import MockBUAtlas, MockPushPilot, MockSignalScribe
from pulsecraft.orchestrator.states import WorkflowState
from pulsecraft.schemas.audit_record import EventType
from pulsecraft.schemas.change_artifact import ChangeArtifact

CONFIG_DIR = Path(__file__).parent.parent.parent.parent / "config"
FIXTURES_DIR = Path(__file__).parent.parent.parent.parent / "fixtures" / "changes"

_HOOK_REGISTRATIONS = {
    "pre_ingest": HookRegistration(
        name="pre_ingest",
        module="pulsecraft.hooks.pre_ingest",
        entrypoint="run",
        fail="closed",
        enabled=True,
    ),
    "post_agent": HookRegistration(
        name="post_agent",
        module="pulsecraft.hooks.post_agent",
        entrypoint="run",
        fail="closed",
        enabled=True,
    ),
    "pre_deliver": HookRegistration(
        name="pre_deliver",
        module="pulsecraft.hooks.pre_deliver",
        entrypoint="run",
        fail="closed",
        enabled=True,
    ),
    "audit": HookRegistration(
        name="audit",
        module="pulsecraft.hooks.audit_hook",
        entrypoint="run",
        fail="open",
        enabled=True,
    ),
}


@pytest.fixture(autouse=True)
def config_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PULSECRAFT_CONFIG_DIR", str(CONFIG_DIR))
    reload_config()
    yield
    reload_config()


def _load_fixture(filename: str) -> ChangeArtifact:
    path = FIXTURES_DIR / filename
    return ChangeArtifact.model_validate(json.loads(path.read_text(encoding="utf-8")))


def _make_orchestrator(tmp_path: Path) -> tuple[Orchestrator, AuditWriter]:
    audit = AuditWriter(root=tmp_path / "audit")
    hitl = HITLQueue(audit_writer=audit, root=tmp_path / "queue")
    with patch(
        "pulsecraft.orchestrator.engine.load_hook_registrations",
        return_value=_HOOK_REGISTRATIONS,
    ):
        orch = Orchestrator(
            signalscribe=MockSignalScribe(),
            buatlas=MockBUAtlas(),
            pushpilot=MockPushPilot(),
            audit_writer=audit,
            hitl_queue=hitl,
        )
    return orch, audit


def test_hook_fired_records_appear_in_audit_chain(tmp_path: Path) -> None:
    orch, audit = _make_orchestrator(tmp_path)
    artifact = _load_fixture("change_001_clearcut_communicate.json")

    result = orch.run_change(artifact)

    chain = audit.read_chain(artifact.change_id)
    hook_records = [r for r in chain if r.event_type == EventType.HOOK_FIRED]
    assert len(hook_records) >= 2, "Expected at least pre_ingest and post_agent HOOK_FIRED records"


def test_pre_ingest_hook_fired_record(tmp_path: Path) -> None:
    orch, audit = _make_orchestrator(tmp_path)
    artifact = _load_fixture("change_001_clearcut_communicate.json")
    orch.run_change(artifact)

    chain = audit.read_chain(artifact.change_id)
    pre_ingest_records = [
        r for r in chain if r.event_type == EventType.HOOK_FIRED and r.actor.id == "pre_ingest"
    ]
    assert len(pre_ingest_records) == 1
    assert pre_ingest_records[0].outcome in ("success", "failure")


def test_post_agent_hook_fired_records(tmp_path: Path) -> None:
    orch, audit = _make_orchestrator(tmp_path)
    artifact = _load_fixture("change_001_clearcut_communicate.json")
    orch.run_change(artifact)

    chain = audit.read_chain(artifact.change_id)
    post_agent_records = [
        r for r in chain if r.event_type == EventType.HOOK_FIRED and r.actor.id == "post_agent"
    ]
    # At minimum SignalScribe fires post_agent; BUAtlas and PushPilot may also fire
    assert len(post_agent_records) >= 1


def test_no_hooks_when_disabled(tmp_path: Path) -> None:
    audit = AuditWriter(root=tmp_path / "audit")
    hitl = HITLQueue(audit_writer=audit, root=tmp_path / "queue")
    with patch(
        "pulsecraft.orchestrator.engine.load_hook_registrations",
        return_value={},
    ):
        orch = Orchestrator(
            signalscribe=MockSignalScribe(),
            buatlas=MockBUAtlas(),
            pushpilot=MockPushPilot(),
            audit_writer=audit,
            hitl_queue=hitl,
        )
    artifact = _load_fixture("change_001_clearcut_communicate.json")
    orch.run_change(artifact)

    chain = audit.read_chain(artifact.change_id)
    hook_records = [r for r in chain if r.event_type == EventType.HOOK_FIRED]
    assert len(hook_records) == 0


def test_pipeline_reaches_terminal_state_with_hooks(tmp_path: Path) -> None:
    orch, audit = _make_orchestrator(tmp_path)
    artifact = _load_fixture("change_001_clearcut_communicate.json")
    result = orch.run_change(artifact)

    assert result.terminal_state in WorkflowState.__members__.values()
    assert result.terminal_state != WorkflowState.RECEIVED
