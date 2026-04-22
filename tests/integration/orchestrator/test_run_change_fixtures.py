"""Integration tests: every fixture through the orchestrator with scripted mocks.

Each test loads a real fixture, constructs scripted mock agents, runs the orchestrator,
and asserts the expected terminal state and audit record count.
"""

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from pulsecraft.orchestrator.audit import AuditWriter
from pulsecraft.orchestrator.engine import Orchestrator
from pulsecraft.orchestrator.hitl import HITLQueue, HITLReason
from pulsecraft.orchestrator.mock_agents import MockBUAtlas, MockPushPilot, MockSignalScribe
from pulsecraft.orchestrator.states import WorkflowState
from pulsecraft.schemas.change_artifact import ChangeArtifact
from pulsecraft.schemas.change_brief import (
    ChangeBrief,
    ChangeType,
    ProducedBy,
    Timeline,
    TimelineStatus,
)
from pulsecraft.schemas.decision import Decision, DecisionAgent, DecisionVerb
from pulsecraft.schemas.delivery_plan import DeliveryDecision
from pulsecraft.schemas.personalized_brief import (
    MessageQuality,
    MessageVariants,
    PersonalizedBrief,
    Priority,
    Relevance,
)
from pulsecraft.schemas.personalized_brief import (
    ProducedBy as PBProducedBy,
)
from pulsecraft.schemas.push_pilot_output import PushPilotOutput

FIXTURES_DIR = Path(__file__).parent.parent.parent.parent / "fixtures" / "changes"


def _load_fixture(filename: str) -> ChangeArtifact:
    path = FIXTURES_DIR / filename
    return ChangeArtifact.model_validate(json.loads(path.read_text(encoding="utf-8")))


def _make_orchestrator(
    tmp_path: Path,
    signalscribe: MockSignalScribe | None = None,
    buatlas: MockBUAtlas | None = None,
    pushpilot: MockPushPilot | None = None,
) -> tuple[Orchestrator, AuditWriter]:
    audit = AuditWriter(root=tmp_path / "audit")
    hitl = HITLQueue(audit_writer=audit, root=tmp_path / "queue")
    orch = Orchestrator(
        signalscribe=signalscribe or MockSignalScribe(),
        buatlas=buatlas or MockBUAtlas(),
        pushpilot=pushpilot or MockPushPilot(),
        audit_writer=audit,
        hitl_queue=hitl,
    )
    return orch, audit


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _ss_agent() -> DecisionAgent:
    return DecisionAgent(name="signalscribe", version="mock-1.0")


def _ba_agent() -> DecisionAgent:
    return DecisionAgent(name="buatlas", version="mock-1.0")


def _pp_agent() -> DecisionAgent:
    return DecisionAgent(name="pushpilot", version="mock-1.0")


def _communicate_ripe_ready_brief(change_id: str) -> ChangeBrief:
    now = _now()
    agent = _ss_agent()
    return ChangeBrief(
        brief_id=str(uuid.uuid4()),
        change_id=change_id,
        produced_at=now,
        produced_by=ProducedBy(version="mock-1.0"),
        summary="Test: communicate ripe ready",
        before="old state",
        after="new state",
        change_type=ChangeType.BEHAVIOR_CHANGE,
        impact_areas=["specialty_pharmacy", "hcp_portal_ordering"],
        affected_segments=["hcp_users"],
        timeline=Timeline(status=TimelineStatus.RIPE),
        required_actions=[],
        risks=[],
        mitigations=[],
        faq=[],
        sources=[],
        confidence_score=0.90,
        decisions=[
            Decision(
                gate=1,
                verb=DecisionVerb.COMMUNICATE,
                reason="test",
                confidence=0.90,
                decided_at=now,
                agent=agent,
            ),
            Decision(
                gate=2,
                verb=DecisionVerb.RIPE,
                reason="test",
                confidence=0.90,
                decided_at=now,
                agent=agent,
            ),
            Decision(
                gate=3,
                verb=DecisionVerb.READY,
                reason="test",
                confidence=0.90,
                decided_at=now,
                agent=agent,
            ),
        ],
    )


def _archive_brief(change_id: str) -> ChangeBrief:
    now = _now()
    agent = _ss_agent()
    return ChangeBrief(
        brief_id=str(uuid.uuid4()),
        change_id=change_id,
        produced_at=now,
        produced_by=ProducedBy(version="mock-1.0"),
        summary="Pure internal refactor — no user impact.",
        before="old internals",
        after="new internals, same behavior",
        change_type=ChangeType.BUGFIX,
        impact_areas=[],
        affected_segments=[],
        timeline=Timeline(status=TimelineStatus.RIPE),
        required_actions=[],
        risks=[],
        mitigations=[],
        faq=[],
        sources=[],
        confidence_score=0.92,
        decisions=[
            Decision(
                gate=1,
                verb=DecisionVerb.ARCHIVE,
                reason="Pure internal refactor, no user impact.",
                confidence=0.92,
                decided_at=now,
                agent=agent,
            ),
        ],
    )


def _escalate_brief(change_id: str) -> ChangeBrief:
    now = _now()
    agent = _ss_agent()
    return ChangeBrief(
        brief_id=str(uuid.uuid4()),
        change_id=change_id,
        produced_at=now,
        produced_by=ProducedBy(version="mock-1.0"),
        summary="Ambiguous artifact — insufficient detail to classify.",
        before="unknown",
        after="unknown",
        change_type=ChangeType.BEHAVIOR_CHANGE,
        impact_areas=[],
        affected_segments=[],
        timeline=Timeline(status=TimelineStatus.RIPE),
        required_actions=[],
        risks=[],
        mitigations=[],
        faq=[],
        sources=[],
        confidence_score=0.45,
        escalation_reason="Artifact says 'various improvements' without specifics.",
        decisions=[
            Decision(
                gate=1,
                verb=DecisionVerb.ESCALATE,
                reason="Ambiguous scope — cannot classify without more detail.",
                confidence=0.45,
                decided_at=now,
                agent=agent,
            ),
        ],
    )


def _hold_until_brief(change_id: str) -> ChangeBrief:
    now = _now()
    agent = _ss_agent()
    return ChangeBrief(
        brief_id=str(uuid.uuid4()),
        change_id=change_id,
        produced_at=now,
        produced_by=ProducedBy(version="mock-1.0"),
        summary="Feature flag at 2% internal — not ripe yet.",
        before="flag disabled",
        after="flag at 2% internal",
        change_type=ChangeType.CONFIGURATION_CHANGE,
        impact_areas=["hcp_portal_ordering"],
        affected_segments=["hcp_users"],
        timeline=Timeline(
            status=TimelineStatus.HELD_UNTIL,
            reevaluate_at="2026-06-01",
            reevaluate_trigger="GA ramp announcement",
        ),
        required_actions=[],
        risks=[],
        mitigations=[],
        faq=[],
        sources=[],
        confidence_score=0.88,
        decisions=[
            Decision(
                gate=1,
                verb=DecisionVerb.COMMUNICATE,
                reason="Visible flag rollout started.",
                confidence=0.88,
                decided_at=now,
                agent=agent,
            ),
            Decision(
                gate=2,
                verb=DecisionVerb.HOLD_UNTIL,
                reason="2% internal only, GA far out.",
                confidence=0.88,
                decided_at=now,
                agent=agent,
                payload={"date": "2026-06-01", "trigger": "GA ramp announcement"},
            ),
        ],
    )


def _need_clarification_brief(change_id: str) -> ChangeBrief:
    now = _now()
    agent = _ss_agent()
    return ChangeBrief(
        brief_id=str(uuid.uuid4()),
        change_id=change_id,
        produced_at=now,
        produced_by=ProducedBy(version="mock-1.0"),
        summary="Order submission improvement — unclear scope.",
        before="prior order process",
        after="improved order process",
        change_type=ChangeType.BEHAVIOR_CHANGE,
        impact_areas=["specialty_pharmacy"],
        affected_segments=[],
        timeline=Timeline(status=TimelineStatus.RIPE),
        required_actions=[],
        risks=[],
        mitigations=[],
        faq=[],
        sources=[],
        confidence_score=0.65,
        open_questions=[
            "Does 'Q3 Processing Improvements' apply to US or all regions?",
            "Is this change already live or still rolling out?",
        ],
        decisions=[
            Decision(
                gate=1,
                verb=DecisionVerb.COMMUNICATE,
                reason="Workflow change detected.",
                confidence=0.82,
                decided_at=now,
                agent=agent,
            ),
            Decision(
                gate=2,
                verb=DecisionVerb.RIPE,
                reason="Change described as complete.",
                confidence=0.80,
                decided_at=now,
                agent=agent,
            ),
            Decision(
                gate=3,
                verb=DecisionVerb.NEED_CLARIFICATION,
                reason="Scope is unclear — US or global?",
                confidence=0.65,
                decided_at=now,
                agent=agent,
                payload={"questions": ["US or global?", "Live or rolling out?"]},
            ),
        ],
    )


def _mlr_sensitive_personalized_brief(
    change_id: str,
    brief_id: str,
    bu_id: str = "bu_alpha",
) -> PersonalizedBrief:
    """Returns a brief with MLR-sensitive scientific terms in the message."""
    now = _now()
    agent = _ba_agent()
    return PersonalizedBrief(
        personalized_brief_id=str(uuid.uuid4()),
        change_id=change_id,
        brief_id=brief_id,
        bu_id=bu_id,
        produced_at=now,
        produced_by=PBProducedBy(version="mock-1.0", invocation_id=str(uuid.uuid4())),
        relevance=Relevance.AFFECTED,
        priority=Priority.P1,
        why_relevant="BU uses HCP educational modules.",
        recommended_actions=[],
        assumptions=[],
        message_variants=MessageVariants(
            push_short="HCP module updated — see new clinical data on safety profile.",
            teams_medium="The HCP educational module has been updated with new clinical outcomes data.",
            email_long="New content presents efficacy and adverse event data for updated indications.",
        ),
        message_quality=MessageQuality.WORTH_SENDING,
        confidence_score=0.80,
        decisions=[
            Decision(
                gate=4,
                verb=DecisionVerb.AFFECTED,
                reason="BU uses HCP modules.",
                confidence=0.80,
                decided_at=now,
                agent=agent,
            ),
            Decision(
                gate=5,
                verb=DecisionVerb.WORTH_SENDING,
                reason="Message is clear.",
                confidence=0.80,
                decided_at=now,
                agent=agent,
            ),
        ],
    )


def _digest_output(brief_id: str | None = None) -> PushPilotOutput:
    now = _now()
    return PushPilotOutput(
        decision=DeliveryDecision.DIGEST,
        reason="P2 awareness item — digest format is appropriate.",
        confidence_score=0.90,
        gate_decision=Decision(
            gate=6,
            verb=DecisionVerb.DIGEST,
            reason="P2 digest",
            confidence=0.90,
            decided_at=now,
            agent=_pp_agent(),
        ),
    )


class TestFixture001ClearcutCommunicate:
    """Fixture 001: clear-cut communicate → DELIVERED."""

    def test_terminal_state_is_delivered(self, tmp_path: Path) -> None:
        artifact = _load_fixture("change_001_clearcut_communicate.json")
        orch, audit = _make_orchestrator(tmp_path)
        result = orch.run_change(artifact)
        assert result.terminal_state == WorkflowState.DELIVERED

    def test_audit_records_written(self, tmp_path: Path) -> None:
        artifact = _load_fixture("change_001_clearcut_communicate.json")
        orch, audit = _make_orchestrator(tmp_path)
        result = orch.run_change(artifact)
        assert result.audit_record_count >= 5

    def test_hitl_not_queued(self, tmp_path: Path) -> None:
        artifact = _load_fixture("change_001_clearcut_communicate.json")
        orch, audit = _make_orchestrator(tmp_path)
        result = orch.run_change(artifact)
        assert not result.hitl_queued

    def test_personalized_briefs_populated(self, tmp_path: Path) -> None:
        artifact = _load_fixture("change_001_clearcut_communicate.json")
        orch, audit = _make_orchestrator(tmp_path)
        result = orch.run_change(artifact)
        assert len(result.personalized_briefs) > 0


class TestFixture002PureInternalRefactor:
    """Fixture 002: pure internal refactor → ARCHIVED."""

    def test_terminal_state_is_archived(self, tmp_path: Path) -> None:
        artifact = _load_fixture("change_002_pure_internal_refactor.json")
        orch, audit = _make_orchestrator(
            tmp_path,
            signalscribe=MockSignalScribe(
                script={artifact.change_id: _archive_brief(artifact.change_id)}
            ),
        )
        result = orch.run_change(artifact)
        assert result.terminal_state == WorkflowState.ARCHIVED

    def test_no_personalized_briefs(self, tmp_path: Path) -> None:
        artifact = _load_fixture("change_002_pure_internal_refactor.json")
        orch, _ = _make_orchestrator(
            tmp_path,
            signalscribe=MockSignalScribe(
                script={artifact.change_id: _archive_brief(artifact.change_id)}
            ),
        )
        result = orch.run_change(artifact)
        assert result.personalized_briefs == {}

    def test_hitl_not_queued(self, tmp_path: Path) -> None:
        artifact = _load_fixture("change_002_pure_internal_refactor.json")
        orch, _ = _make_orchestrator(
            tmp_path,
            signalscribe=MockSignalScribe(
                script={artifact.change_id: _archive_brief(artifact.change_id)}
            ),
        )
        result = orch.run_change(artifact)
        assert not result.hitl_queued


class TestFixture003AmbiguousEscalate:
    """Fixture 003: ambiguous scope → SignalScribe ESCALATE → AWAITING_HITL."""

    def test_terminal_state_is_awaiting_hitl(self, tmp_path: Path) -> None:
        artifact = _load_fixture("change_003_ambiguous_escalate.json")
        orch, _ = _make_orchestrator(
            tmp_path,
            signalscribe=MockSignalScribe(
                script={artifact.change_id: _escalate_brief(artifact.change_id)}
            ),
        )
        result = orch.run_change(artifact)
        assert result.terminal_state == WorkflowState.AWAITING_HITL

    def test_hitl_queued_with_agent_escalate_reason(self, tmp_path: Path) -> None:
        artifact = _load_fixture("change_003_ambiguous_escalate.json")
        orch, _ = _make_orchestrator(
            tmp_path,
            signalscribe=MockSignalScribe(
                script={artifact.change_id: _escalate_brief(artifact.change_id)}
            ),
        )
        result = orch.run_change(artifact)
        assert result.hitl_queued
        assert result.hitl_reason == HITLReason.AGENT_ESCALATE


class TestFixture004EarlyFlagHoldUntil:
    """Fixture 004: gate-2 HOLD_UNTIL → HELD."""

    def test_terminal_state_is_held(self, tmp_path: Path) -> None:
        artifact = _load_fixture("change_004_early_flag_hold_until.json")
        orch, _ = _make_orchestrator(
            tmp_path,
            signalscribe=MockSignalScribe(
                script={artifact.change_id: _hold_until_brief(artifact.change_id)}
            ),
        )
        result = orch.run_change(artifact)
        assert result.terminal_state == WorkflowState.HELD

    def test_hitl_not_queued_for_hold(self, tmp_path: Path) -> None:
        artifact = _load_fixture("change_004_early_flag_hold_until.json")
        orch, _ = _make_orchestrator(
            tmp_path,
            signalscribe=MockSignalScribe(
                script={artifact.change_id: _hold_until_brief(artifact.change_id)}
            ),
        )
        result = orch.run_change(artifact)
        assert not result.hitl_queued


class TestFixture005MuddledNeedClarification:
    """Fixture 005: gate-3 NEED_CLARIFICATION → AWAITING_HITL."""

    def test_terminal_state_is_awaiting_hitl(self, tmp_path: Path) -> None:
        artifact = _load_fixture("change_005_muddled_need_clarification.json")
        orch, _ = _make_orchestrator(
            tmp_path,
            signalscribe=MockSignalScribe(
                script={artifact.change_id: _need_clarification_brief(artifact.change_id)}
            ),
        )
        result = orch.run_change(artifact)
        assert result.terminal_state == WorkflowState.AWAITING_HITL

    def test_hitl_reason_is_need_clarification(self, tmp_path: Path) -> None:
        artifact = _load_fixture("change_005_muddled_need_clarification.json")
        orch, _ = _make_orchestrator(
            tmp_path,
            signalscribe=MockSignalScribe(
                script={artifact.change_id: _need_clarification_brief(artifact.change_id)}
            ),
        )
        result = orch.run_change(artifact)
        assert result.hitl_reason == HITLReason.NEED_CLARIFICATION


class TestFixture006MultiBUMixed:
    """Fixture 006: mixed BU results — bu_alpha AFFECTED, others NOT_AFFECTED → DELIVERED."""

    def test_terminal_state_is_delivered_with_one_affected_bu(self, tmp_path: Path) -> None:
        artifact = _load_fixture("change_006_multi_bu_affected_vs_adjacent.json")
        # Default SignalScribe uses impact_areas=["specialty_pharmacy", "hcp_portal_ordering"]
        # bu_alpha owns both → AFFECTED; others will be NOT_AFFECTED by default
        orch, _ = _make_orchestrator(tmp_path)
        result = orch.run_change(artifact)
        assert result.terminal_state == WorkflowState.DELIVERED

    def test_multiple_bus_evaluated(self, tmp_path: Path) -> None:
        artifact = _load_fixture("change_006_multi_bu_affected_vs_adjacent.json")
        orch, _ = _make_orchestrator(tmp_path)
        result = orch.run_change(artifact)
        assert len(result.personalized_briefs) > 0


class TestFixture007MLRSensitive:
    """Fixture 007: MLR-sensitive terms in draft → AWAITING_HITL."""

    def test_terminal_state_is_awaiting_hitl(self, tmp_path: Path) -> None:
        artifact = _load_fixture("change_007_mlr_sensitive.json")
        change_brief = _communicate_ripe_ready_brief(artifact.change_id)

        mlr_pb = _mlr_sensitive_personalized_brief(artifact.change_id, change_brief.brief_id)
        mlr_script = {(artifact.change_id, mlr_pb.bu_id): mlr_pb}

        orch, _ = _make_orchestrator(
            tmp_path,
            signalscribe=MockSignalScribe(script={artifact.change_id: change_brief}),
            buatlas=MockBUAtlas(script=mlr_script),
        )
        result = orch.run_change(artifact)
        assert result.terminal_state == WorkflowState.AWAITING_HITL

    def test_hitl_reason_is_mlr_sensitive(self, tmp_path: Path) -> None:
        artifact = _load_fixture("change_007_mlr_sensitive.json")
        change_brief = _communicate_ripe_ready_brief(artifact.change_id)
        mlr_pb = _mlr_sensitive_personalized_brief(artifact.change_id, change_brief.brief_id)
        mlr_script = {(artifact.change_id, mlr_pb.bu_id): mlr_pb}

        orch, _ = _make_orchestrator(
            tmp_path,
            signalscribe=MockSignalScribe(script={artifact.change_id: change_brief}),
            buatlas=MockBUAtlas(script=mlr_script),
        )
        result = orch.run_change(artifact)
        assert result.hitl_reason == HITLReason.MLR_SENSITIVE


class TestFixture008PostHocAlreadyShipped:
    """Fixture 008: post-hoc shipped → PushPilot DIGEST → DIGESTED."""

    def test_terminal_state_is_digested(self, tmp_path: Path) -> None:
        artifact = _load_fixture("change_008_post_hoc_already_shipped.json")
        change_brief = _communicate_ripe_ready_brief(artifact.change_id)

        # Script BUAtlas for bu_alpha → AFFECTED+WORTH_SENDING
        now = _now()
        agent = _ba_agent()
        pb_id = str(uuid.uuid4())
        pb = PersonalizedBrief(
            personalized_brief_id=pb_id,
            change_id=artifact.change_id,
            brief_id=change_brief.brief_id,
            bu_id="bu_alpha",
            produced_at=now,
            produced_by=PBProducedBy(version="mock-1.0", invocation_id=str(uuid.uuid4())),
            relevance=Relevance.AFFECTED,
            priority=Priority.P2,
            why_relevant="Post-hoc notification for awareness.",
            recommended_actions=[],
            assumptions=[],
            message_variants=MessageVariants(push_short="notification wording standardized"),
            message_quality=MessageQuality.WORTH_SENDING,
            confidence_score=0.85,
            decisions=[
                Decision(
                    gate=4,
                    verb=DecisionVerb.AFFECTED,
                    reason="test",
                    confidence=0.85,
                    decided_at=now,
                    agent=agent,
                ),
                Decision(
                    gate=5,
                    verb=DecisionVerb.WORTH_SENDING,
                    reason="test",
                    confidence=0.85,
                    decided_at=now,
                    agent=agent,
                ),
            ],
        )

        orch, _ = _make_orchestrator(
            tmp_path,
            signalscribe=MockSignalScribe(script={artifact.change_id: change_brief}),
            buatlas=MockBUAtlas(script={(artifact.change_id, "bu_alpha"): pb}),
            pushpilot=MockPushPilot(script={pb_id: _digest_output()}),
        )
        result = orch.run_change(artifact)
        assert result.terminal_state == WorkflowState.DIGESTED
