"""Tests for mock agents — Protocol compliance and scripted responses."""

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

from pulsecraft.config.loader import get_bu_profile, reload_config
from pulsecraft.orchestrator.agent_protocol import (
    BUAtlasProtocol,
    PushPilotProtocol,
    SignalScribeProtocol,
)
from pulsecraft.orchestrator.mock_agents import (
    MockBUAtlas,
    MockPushPilot,
    MockSignalScribe,
)
from pulsecraft.schemas.change_artifact import ChangeArtifact, SourceType
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

CONFIG_DIR = Path(__file__).parent.parent.parent.parent / "config"


@pytest.fixture(autouse=True)
def config_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PULSECRAFT_CONFIG_DIR", str(CONFIG_DIR))
    reload_config()
    yield
    reload_config()


def _artifact() -> ChangeArtifact:
    return ChangeArtifact(
        change_id=str(uuid.uuid4()),
        source_type=SourceType.RELEASE_NOTE,
        source_ref="TEST-001",
        ingested_at=datetime.now(tz=UTC),
        title="Test change",
        raw_text="A test change artifact.",
    )


def _change_brief(
    change_id: str | None = None, impact_areas: list[str] | None = None
) -> ChangeBrief:
    now = datetime.now(tz=UTC)
    agent = DecisionAgent(name="signalscribe", version="mock-1.0")
    return ChangeBrief(
        brief_id=str(uuid.uuid4()),
        change_id=change_id or str(uuid.uuid4()),
        produced_at=now,
        produced_by=ProducedBy(version="mock-1.0"),
        summary="Test brief",
        before="before",
        after="after",
        change_type=ChangeType.BEHAVIOR_CHANGE,
        impact_areas=impact_areas or ["specialty_pharmacy", "hcp_portal_ordering"],
        affected_segments=[],
        timeline=Timeline(status=TimelineStatus.RIPE),
        required_actions=[],
        risks=[],
        mitigations=[],
        faq=[],
        sources=[],
        confidence_score=0.85,
        decisions=[
            Decision(
                gate=1,
                verb=DecisionVerb.COMMUNICATE,
                reason="test",
                confidence=0.85,
                decided_at=now,
                agent=agent,
            ),
            Decision(
                gate=2,
                verb=DecisionVerb.RIPE,
                reason="test",
                confidence=0.85,
                decided_at=now,
                agent=agent,
            ),
            Decision(
                gate=3,
                verb=DecisionVerb.READY,
                reason="test",
                confidence=0.85,
                decided_at=now,
                agent=agent,
            ),
        ],
    )


class TestProtocolCompliance:
    def test_mock_signalscribe_satisfies_protocol(self) -> None:
        mock = MockSignalScribe()
        assert isinstance(mock, SignalScribeProtocol)

    def test_mock_buatlas_satisfies_protocol(self) -> None:
        mock = MockBUAtlas()
        assert isinstance(mock, BUAtlasProtocol)

    def test_mock_pushpilot_satisfies_protocol(self) -> None:
        mock = MockPushPilot()
        assert isinstance(mock, PushPilotProtocol)


class TestMockSignalScribe:
    def test_default_returns_communicate_ripe_ready(self) -> None:
        artifact = _artifact()
        mock = MockSignalScribe()
        brief = mock.invoke(artifact)
        verbs = {d.gate: d.verb for d in brief.decisions}
        assert verbs[1] == DecisionVerb.COMMUNICATE
        assert verbs[2] == DecisionVerb.RIPE
        assert verbs[3] == DecisionVerb.READY

    def test_scripted_response_overrides_default(self) -> None:
        artifact = _artifact()
        now = datetime.now(tz=UTC)
        agent = DecisionAgent(name="signalscribe", version="mock-1.0")
        scripted_brief = ChangeBrief(
            brief_id=str(uuid.uuid4()),
            change_id=artifact.change_id,
            produced_at=now,
            produced_by=ProducedBy(version="mock-1.0"),
            summary="scripted",
            before="before",
            after="after",
            change_type=ChangeType.BUGFIX,
            impact_areas=[],
            affected_segments=[],
            timeline=Timeline(status=TimelineStatus.RIPE),
            required_actions=[],
            risks=[],
            mitigations=[],
            faq=[],
            sources=[],
            confidence_score=0.5,
            decisions=[
                Decision(
                    gate=1,
                    verb=DecisionVerb.ARCHIVE,
                    reason="scripted",
                    confidence=0.9,
                    decided_at=now,
                    agent=agent,
                )
            ],
        )
        mock = MockSignalScribe(script={artifact.change_id: scripted_brief})
        result = mock.invoke(artifact)
        assert result.decisions[0].verb == DecisionVerb.ARCHIVE

    def test_agent_name_is_mock_variant(self) -> None:
        assert MockSignalScribe().agent_name == "signalscribe_mock"

    def test_version_is_mock(self) -> None:
        assert "mock" in MockSignalScribe().version

    def test_decision_agent_name_satisfies_schema(self) -> None:
        # Decision.agent.name must match ^(signalscribe|buatlas|pushpilot)$
        artifact = _artifact()
        brief = MockSignalScribe().invoke(artifact)
        for d in brief.decisions:
            assert d.agent.name in ("signalscribe", "buatlas", "pushpilot")


class TestMockBUAtlas:
    def test_default_affected_when_overlap(self) -> None:
        brief = _change_brief(impact_areas=["specialty_pharmacy"])
        profile = get_bu_profile("bu_alpha")  # owns specialty_pharmacy
        mock = MockBUAtlas()
        pb = mock.invoke(brief, profile)
        assert pb.relevance == Relevance.AFFECTED
        assert pb.message_quality == MessageQuality.WORTH_SENDING

    def test_default_not_affected_when_no_overlap(self) -> None:
        brief = _change_brief(impact_areas=["some_other_area"])
        profile = get_bu_profile("bu_alpha")
        mock = MockBUAtlas()
        pb = mock.invoke(brief, profile)
        assert pb.relevance == Relevance.NOT_AFFECTED
        assert pb.message_quality is None

    def test_scripted_response_used(self) -> None:
        now = datetime.now(tz=UTC)
        agent = DecisionAgent(name="buatlas", version="mock-1.0")
        brief = _change_brief()
        profile = get_bu_profile("bu_alpha")
        scripted_pb = PersonalizedBrief(
            personalized_brief_id=str(uuid.uuid4()),
            change_id=brief.change_id,
            brief_id=brief.brief_id,
            bu_id="bu_alpha",
            produced_at=now,
            produced_by=PBProducedBy(version="mock-1.0", invocation_id=str(uuid.uuid4())),
            relevance=Relevance.ADJACENT,
            priority=None,
            why_relevant="",
            recommended_actions=[],
            assumptions=[],
            message_quality=None,
            confidence_score=0.7,
            decisions=[
                Decision(
                    gate=4,
                    verb=DecisionVerb.ADJACENT,
                    reason="scripted",
                    confidence=0.7,
                    decided_at=now,
                    agent=agent,
                )
            ],
        )
        mock = MockBUAtlas(script={(brief.change_id, "bu_alpha"): scripted_pb})
        result = mock.invoke(brief, profile)
        assert result.relevance == Relevance.ADJACENT


class TestMockPushPilot:
    def test_default_send_now(self) -> None:
        now = datetime.now(tz=UTC)
        agent = DecisionAgent(name="buatlas", version="mock-1.0")
        brief = _change_brief()
        profile = get_bu_profile("bu_alpha")
        pb = PersonalizedBrief(
            personalized_brief_id=str(uuid.uuid4()),
            change_id=brief.change_id,
            brief_id=brief.brief_id,
            bu_id="bu_alpha",
            produced_at=now,
            produced_by=PBProducedBy(version="mock-1.0", invocation_id=str(uuid.uuid4())),
            relevance=Relevance.AFFECTED,
            priority=Priority.P1,
            why_relevant="test",
            recommended_actions=[],
            assumptions=[],
            message_variants=MessageVariants(push_short="test"),
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
        mock = MockPushPilot()
        output = mock.invoke(pb, profile)
        assert output.decision == DeliveryDecision.SEND_NOW

    def test_scripted_response_used(self) -> None:
        now = datetime.now(tz=UTC)
        agent = DecisionAgent(name="buatlas", version="mock-1.0")
        brief = _change_brief()
        profile = get_bu_profile("bu_alpha")
        pb_id = str(uuid.uuid4())
        pb = PersonalizedBrief(
            personalized_brief_id=pb_id,
            change_id=brief.change_id,
            brief_id=brief.brief_id,
            bu_id="bu_alpha",
            produced_at=now,
            produced_by=PBProducedBy(version="mock-1.0", invocation_id=str(uuid.uuid4())),
            relevance=Relevance.AFFECTED,
            priority=Priority.P2,
            why_relevant="test",
            recommended_actions=[],
            assumptions=[],
            message_variants=MessageVariants(push_short="test"),
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
        scripted = PushPilotOutput(
            decision=DeliveryDecision.DIGEST,
            reason="scripted digest",
            confidence_score=0.9,
            gate_decision=Decision(
                gate=6,
                verb=DecisionVerb.DIGEST,
                reason="scripted",
                confidence=0.9,
                decided_at=now,
                agent=DecisionAgent(name="pushpilot", version="mock-1.0"),
            ),
        )
        mock = MockPushPilot(script={pb_id: scripted})
        result = mock.invoke(pb, profile)
        assert result.decision == DeliveryDecision.DIGEST
