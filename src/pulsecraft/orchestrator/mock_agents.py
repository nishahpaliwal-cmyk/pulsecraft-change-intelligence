"""Mock agents for testing — satisfy the Agent Protocols with scripted, deterministic responses.

These are testing-only. They make no LLM calls, no network calls, and do not read config.
agent_name uses the "_mock" suffix so audit logs clearly distinguish mock from real runs.
Decision.agent.name uses the canonical agent name (no "_mock") to satisfy schema validation.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pulsecraft.schemas.bu_profile import BUProfile
from pulsecraft.schemas.change_artifact import ChangeArtifact, SourceType
from pulsecraft.schemas.change_brief import (
    ChangeBrief,
    ChangeType,
    SourceCitation,
    Timeline,
    TimelineStatus,
)
from pulsecraft.schemas.change_brief import (
    ProducedBy as ChangeBriefProducedBy,
)
from pulsecraft.schemas.decision import Decision, DecisionAgent, DecisionVerb
from pulsecraft.schemas.delivery_plan import DeliveryDecision
from pulsecraft.schemas.past_engagement import PastEngagement
from pulsecraft.schemas.personalized_brief import (
    MessageQuality,
    MessageVariants,
    PersonalizedBrief,
    Priority,
    RecommendedAction,
    Relevance,
)
from pulsecraft.schemas.personalized_brief import (
    ProducedBy as PersonalizedBriefProducedBy,
)
from pulsecraft.schemas.push_pilot_output import PushPilotOutput


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _uuid() -> str:
    return str(uuid.uuid4())


def _decision_agent(name: str) -> DecisionAgent:
    return DecisionAgent(name=name, version="mock-1.0")


# ── Default scripted responses ────────────────────────────────────────────────


def _default_change_brief(artifact: ChangeArtifact, agent_version: str = "mock-1.0") -> ChangeBrief:
    """Default ChangeBrief: COMMUNICATE + RIPE + READY at confidence 0.85."""
    now = _now()
    agent = _decision_agent("signalscribe")
    return ChangeBrief(
        brief_id=_uuid(),
        change_id=artifact.change_id,
        produced_at=now,
        produced_by=ChangeBriefProducedBy(version=agent_version),
        summary="Mock summary: a change was detected and interpreted.",
        before="prior state unknown",
        after="new state as described in the artifact",
        change_type=ChangeType.BEHAVIOR_CHANGE,
        impact_areas=["specialty_pharmacy", "hcp_portal_ordering"],
        affected_segments=["hcp_portal_users"],
        timeline=Timeline(status=TimelineStatus.RIPE),
        required_actions=["review the change and prepare team communications"],
        risks=[],
        mitigations=[],
        faq=[],
        sources=[
            SourceCitation(
                type=SourceType.RELEASE_NOTE,
                ref=artifact.source_ref,
                quote="change detected by mock",
            )
        ],
        confidence_score=0.85,
        decisions=[
            Decision(
                gate=1,
                verb=DecisionVerb.COMMUNICATE,
                reason="Mock: visible behavior change detected.",
                confidence=0.85,
                decided_at=now,
                agent=agent,
            ),
            Decision(
                gate=2,
                verb=DecisionVerb.RIPE,
                reason="Mock: rollout is imminent.",
                confidence=0.85,
                decided_at=now,
                agent=agent,
            ),
            Decision(
                gate=3,
                verb=DecisionVerb.READY,
                reason="Mock: interpretation is clear enough to hand off.",
                confidence=0.85,
                decided_at=now,
                agent=agent,
            ),
        ],
    )


def _default_personalized_brief(
    change_brief: ChangeBrief,
    bu_profile: BUProfile,
    agent_version: str = "mock-1.0",
) -> PersonalizedBrief:
    """Default PersonalizedBrief: AFFECTED + WORTH_SENDING if overlap, NOT_AFFECTED otherwise."""
    overlap = set(bu_profile.owned_product_areas) & set(change_brief.impact_areas)
    now = _now()
    agent = _decision_agent("buatlas")
    invocation_id = _uuid()

    if not overlap:
        return PersonalizedBrief(
            personalized_brief_id=_uuid(),
            change_id=change_brief.change_id,
            brief_id=change_brief.brief_id,
            bu_id=bu_profile.bu_id,
            produced_at=now,
            produced_by=PersonalizedBriefProducedBy(
                version=agent_version, invocation_id=invocation_id
            ),
            relevance=Relevance.NOT_AFFECTED,
            priority=None,
            why_relevant="",
            recommended_actions=[],
            assumptions=[],
            message_variants=None,
            message_quality=None,
            confidence_score=0.90,
            decisions=[
                Decision(
                    gate=4,
                    verb=DecisionVerb.NOT_AFFECTED,
                    reason="Mock: no overlap between BU product areas and change impact areas.",
                    confidence=0.90,
                    decided_at=now,
                    agent=agent,
                )
            ],
        )

    return PersonalizedBrief(
        personalized_brief_id=_uuid(),
        change_id=change_brief.change_id,
        brief_id=change_brief.brief_id,
        bu_id=bu_profile.bu_id,
        produced_at=now,
        produced_by=PersonalizedBriefProducedBy(version=agent_version, invocation_id=invocation_id),
        relevance=Relevance.AFFECTED,
        priority=Priority.P1,
        why_relevant=f"Mock: BU owns {', '.join(sorted(overlap))} which overlaps with change impact.",
        recommended_actions=[
            RecommendedAction(
                owner="BU head",
                action="Review change and prepare team briefing.",
                by_when=None,
            )
        ],
        assumptions=["mock assumption: standard rollout applies to this BU"],
        message_variants=MessageVariants(
            push_short="Mock: a relevant change has been detected.",
            teams_medium="Mock notification: a change affecting your BU has been processed.",
            email_long="Mock email: Please review the following change which affects your BU.",
        ),
        message_quality=MessageQuality.WORTH_SENDING,
        confidence_score=0.85,
        decisions=[
            Decision(
                gate=4,
                verb=DecisionVerb.AFFECTED,
                reason=f"Mock: overlap on {sorted(overlap)}.",
                confidence=0.85,
                decided_at=now,
                agent=agent,
            ),
            Decision(
                gate=5,
                verb=DecisionVerb.WORTH_SENDING,
                reason="Mock: message is specific enough to be actionable.",
                confidence=0.85,
                decided_at=now,
                agent=agent,
            ),
        ],
    )


def _default_pushpilot_output(
    personalized_brief: PersonalizedBrief,
    bu_profile: BUProfile,
    agent_version: str = "mock-1.0",
) -> PushPilotOutput:
    """Default PushPilotOutput: SEND_NOW on the first approved channel."""
    now = _now()
    channel = bu_profile.preferences.channels[0] if bu_profile.preferences.channels else None
    from pulsecraft.schemas.delivery_plan import Channel as DeliveryChannel

    # Map BUProfile channel to DeliveryPlan channel enum
    channel_map = {
        "teams": DeliveryChannel.TEAMS,
        "email": DeliveryChannel.EMAIL,
        "push": DeliveryChannel.PUSH,
        "portal_digest": DeliveryChannel.PORTAL_DIGEST,
        "servicenow": DeliveryChannel.SERVICENOW,
    }
    delivery_channel = channel_map.get(str(channel).lower()) if channel else None

    return PushPilotOutput(
        decision=DeliveryDecision.SEND_NOW,
        channel=delivery_channel,
        scheduled_time=None,
        reason="Mock: recipient is within working hours and no rate-limit pressure.",
        confidence_score=0.90,
        gate_decision=Decision(
            gate=6,
            verb=DecisionVerb.SEND_NOW,
            reason="Mock: recipient is within working hours and no rate-limit pressure.",
            confidence=0.90,
            decided_at=now,
            agent=_decision_agent("pushpilot"),
        ),
    )


# ── Mock agent classes ────────────────────────────────────────────────────────


class MockSignalScribe:
    """Scripted mock for SignalScribe.

    ``script``: maps change_id → ChangeBrief. If no script entry, returns the default
    COMMUNICATE+RIPE+READY brief.
    """

    agent_name: str = "signalscribe_mock"
    version: str = "mock-1.0"

    def __init__(self, script: dict[str, ChangeBrief] | None = None) -> None:
        self._script: dict[str, ChangeBrief] = script or {}

    def invoke(self, artifact: ChangeArtifact) -> ChangeBrief:
        if artifact.change_id in self._script:
            return self._script[artifact.change_id]
        return _default_change_brief(artifact, agent_version=self.version)


class MockBUAtlas:
    """Scripted mock for BUAtlas.

    ``script``: maps (change_id, bu_id) → PersonalizedBrief. If no script entry,
    returns AFFECTED+WORTH_SENDING when product areas overlap, NOT_AFFECTED otherwise.
    """

    agent_name: str = "buatlas_mock"
    version: str = "mock-1.0"

    def __init__(self, script: dict[tuple[str, str], PersonalizedBrief] | None = None) -> None:
        self._script: dict[tuple[str, str], PersonalizedBrief] = script or {}

    def invoke(
        self,
        change_brief: ChangeBrief,
        bu_profile: BUProfile,
        past_engagement: PastEngagement | None = None,
    ) -> PersonalizedBrief:
        key = (change_brief.change_id, bu_profile.bu_id)
        if key in self._script:
            return self._script[key]
        return _default_personalized_brief(change_brief, bu_profile, agent_version=self.version)


class MockPushPilot:
    """Scripted mock for PushPilot.

    ``script``: maps personalized_brief_id → PushPilotOutput. If no entry, returns
    SEND_NOW on the BU's first approved channel.
    """

    agent_name: str = "pushpilot_mock"
    version: str = "mock-1.0"

    def __init__(self, script: dict[str, PushPilotOutput] | None = None) -> None:
        self._script: dict[str, PushPilotOutput] = script or {}

    def invoke(
        self,
        personalized_brief: PersonalizedBrief,
        bu_profile: BUProfile,
    ) -> PushPilotOutput:
        if personalized_brief.personalized_brief_id in self._script:
            return self._script[personalized_brief.personalized_brief_id]
        return _default_pushpilot_output(personalized_brief, bu_profile, agent_version=self.version)
