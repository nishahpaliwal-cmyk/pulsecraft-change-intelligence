"""Unit tests for the policy skill — confidence checks, restricted terms, HITL triggers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pulsecraft.orchestrator.hitl import HITLReason
from pulsecraft.schemas.decision import Decision, DecisionAgent, DecisionVerb
from pulsecraft.schemas.personalized_brief import (
    MessageQuality,
    PersonalizedBrief,
    Priority,
    Relevance,
)
from pulsecraft.schemas.personalized_brief import (
    ProducedBy as BUProducedBy,
)
from pulsecraft.schemas.policy import (
    BUAtlasThresholds,
    ConfidenceThresholds,
    GlobalRateLimits,
    PerBURateLimits,
    PerRecipientRateLimits,
    Policy,
    PushPilotThresholds,
    QuietHoursDefault,
    RateLimits,
    RestrictedTerms,
    SignalScribeThresholds,
)
from pulsecraft.skills.policy import (
    check_confidence_threshold,
    check_restricted_terms,
    evaluate_hitl_triggers,
)


def _make_decision(gate: int, verb: DecisionVerb, confidence: float) -> Decision:
    return Decision(
        gate=gate,
        verb=verb,
        reason="test reason",
        confidence=confidence,
        decided_at=datetime.now(UTC),
        agent=DecisionAgent(
            name="signalscribe" if gate <= 3 else ("buatlas" if gate <= 5 else "pushpilot"),
            version="1.0",
        ),
    )


def _make_policy(
    gate_1_communicate: float = 0.7,
    gate_1_archive: float = 0.6,
    gate_2_ripe: float = 0.7,
    gate_3_ready: float = 0.75,
    gate_4_any: float = 0.6,
    gate_4_affected: float = 0.7,
    gate_5_worth_sending: float = 0.65,
    gate_6_any: float = 0.6,
    hitl_triggers: list[str] | None = None,
    commitments: list[str] | None = None,
    scientific: list[str] | None = None,
    sensitive: list[str] | None = None,
) -> Policy:
    return Policy(
        confidence_thresholds=ConfidenceThresholds(
            signalscribe=SignalScribeThresholds(
                gate_1_communicate=gate_1_communicate,
                gate_1_archive=gate_1_archive,
                gate_2_ripe=gate_2_ripe,
                gate_3_ready=gate_3_ready,
            ),
            buatlas=BUAtlasThresholds(
                gate_4_affected=gate_4_affected,
                gate_4_any=gate_4_any,
                gate_5_worth_sending=gate_5_worth_sending,
            ),
            pushpilot=PushPilotThresholds(gate_6_any=gate_6_any),
        ),
        hitl_triggers=hitl_triggers or [],
        restricted_terms=RestrictedTerms(
            commitments_and_dates=commitments or [],
            scientific_communication=scientific or [],
            sensitive_data_markers=sensitive or [],
        ),
        rate_limits=RateLimits(
            per_recipient=PerRecipientRateLimits(max_per_day=5, max_per_week=20),
            per_bu=PerBURateLimits(max_per_day=10),
            **{"global": GlobalRateLimits(max_per_hour=100)},
        ),
        quiet_hours_default=QuietHoursDefault(timezone="UTC", start="20:00", end="08:00"),
        mlr_review_required_when=[],
    )


def _make_personalized_brief(
    bu_id: str = "bu_alpha",
    relevance: Relevance = Relevance.AFFECTED,
    priority: Priority | None = Priority.P1,
    message_quality: MessageQuality | None = MessageQuality.WORTH_SENDING,
    decisions: list[Decision] | None = None,
    regeneration_attempts: int = 0,
    push_short: str | None = "Test message",
    teams_medium: str | None = None,
) -> PersonalizedBrief:
    from pulsecraft.schemas.personalized_brief import MessageVariants

    return PersonalizedBrief(
        personalized_brief_id=str(uuid.uuid4()),
        change_id=str(uuid.uuid4()),
        brief_id=str(uuid.uuid4()),
        bu_id=bu_id,
        produced_at=datetime.now(UTC),
        produced_by=BUProducedBy(invocation_id=str(uuid.uuid4()), version="1.0"),
        relevance=relevance,
        priority=priority,
        why_relevant="relevant" if relevance != Relevance.NOT_AFFECTED else "",
        recommended_actions=[],
        assumptions=[],
        message_variants=MessageVariants(push_short=push_short, teams_medium=teams_medium)
        if push_short or teams_medium
        else None,
        message_quality=message_quality,
        confidence_score=0.8,
        decisions=decisions or [],
        regeneration_attempts=regeneration_attempts,
    )


class TestCheckConfidenceThreshold:
    def test_gate1_communicate_above_threshold_passes(self) -> None:
        policy = _make_policy(gate_1_communicate=0.7)
        d = _make_decision(1, DecisionVerb.COMMUNICATE, 0.8)
        assert check_confidence_threshold(d, policy) is True

    def test_gate1_communicate_below_threshold_fails(self) -> None:
        policy = _make_policy(gate_1_communicate=0.7)
        d = _make_decision(1, DecisionVerb.COMMUNICATE, 0.6)
        assert check_confidence_threshold(d, policy) is False

    def test_gate1_archive_uses_archive_threshold(self) -> None:
        policy = _make_policy(gate_1_archive=0.6)
        d = _make_decision(1, DecisionVerb.ARCHIVE, 0.65)
        assert check_confidence_threshold(d, policy) is True

    def test_gate2_below_threshold_fails(self) -> None:
        policy = _make_policy(gate_2_ripe=0.7)
        d = _make_decision(2, DecisionVerb.RIPE, 0.5)
        assert check_confidence_threshold(d, policy) is False

    def test_gate3_exactly_at_threshold_passes(self) -> None:
        policy = _make_policy(gate_3_ready=0.75)
        d = _make_decision(3, DecisionVerb.READY, 0.75)
        assert check_confidence_threshold(d, policy) is True

    def test_gate4_below_threshold_fails(self) -> None:
        policy = _make_policy(gate_4_any=0.6)
        d = _make_decision(4, DecisionVerb.AFFECTED, 0.55)
        assert check_confidence_threshold(d, policy) is False

    def test_gate5_above_threshold_passes(self) -> None:
        policy = _make_policy(gate_5_worth_sending=0.65)
        d = _make_decision(5, DecisionVerb.WORTH_SENDING, 0.70)
        assert check_confidence_threshold(d, policy) is True

    def test_gate6_below_threshold_fails(self) -> None:
        policy = _make_policy(gate_6_any=0.6)
        d = _make_decision(6, DecisionVerb.SEND_NOW, 0.55)
        assert check_confidence_threshold(d, policy) is False


class TestCheckRestrictedTerms:
    def test_no_text_returns_empty(self) -> None:
        policy = _make_policy(sensitive=["confidential"])
        assert check_restricted_terms("", policy) == []

    def test_sensitive_data_marker_detected(self) -> None:
        policy = _make_policy(sensitive=["patient id"])
        hits = check_restricted_terms("the patient id is 12345", policy)
        assert len(hits) == 1
        assert hits[0].category == "sensitive_data_markers"
        assert hits[0].term == "patient id"

    def test_commitment_detected(self) -> None:
        policy = _make_policy(commitments=["will be available by"])
        hits = check_restricted_terms("the feature will be available by Q3", policy)
        assert len(hits) == 1
        assert hits[0].category == "commitments_and_dates"

    def test_scientific_term_detected(self) -> None:
        policy = _make_policy(scientific=["clinical efficacy"])
        hits = check_restricted_terms("data shows clinical efficacy in trials", policy)
        assert len(hits) == 1
        assert hits[0].category == "scientific_communication"

    def test_case_insensitive_matching(self) -> None:
        policy = _make_policy(sensitive=["CONFIDENTIAL"])
        hits = check_restricted_terms("this is confidential data", policy)
        assert len(hits) == 1

    def test_no_match_returns_empty(self) -> None:
        policy = _make_policy(sensitive=["patient id"], commitments=["will ship"])
        hits = check_restricted_terms("completely clean text here", policy)
        assert hits == []

    def test_position_is_recorded(self) -> None:
        policy = _make_policy(sensitive=["secret"])
        hits = check_restricted_terms("contains secret here", policy)
        assert hits[0].position == "contains secret here".lower().find("secret")


class TestEvaluateHITLTriggers:
    def test_no_triggers_returns_empty_list(self) -> None:
        policy = _make_policy()
        brief = _make_personalized_brief()
        result = evaluate_hitl_triggers({"bu_alpha": brief}, policy)
        assert result == []

    def test_not_affected_bus_skipped(self) -> None:
        policy = _make_policy(hitl_triggers=["priority_p0"])
        brief = _make_personalized_brief(relevance=Relevance.NOT_AFFECTED, priority=Priority.P0)
        result = evaluate_hitl_triggers({"bu_alpha": brief}, policy)
        assert result == []

    def test_priority_p0_triggers_hitl(self) -> None:
        policy = _make_policy(hitl_triggers=["priority_p0"])
        brief = _make_personalized_brief(priority=Priority.P0)
        result = evaluate_hitl_triggers({"bu_alpha": brief}, policy)
        assert len(result) == 1
        assert result[0].reason == HITLReason.PRIORITY_P0

    def test_second_weak_triggers_hitl(self) -> None:
        policy = _make_policy(hitl_triggers=["second_weak_from_gate_5"])
        brief = _make_personalized_brief(
            message_quality=MessageQuality.WEAK,
            regeneration_attempts=1,
        )
        result = evaluate_hitl_triggers({"bu_alpha": brief}, policy)
        assert len(result) == 1
        assert result[0].reason == HITLReason.SECOND_WEAK_FROM_GATE_5

    def test_first_weak_does_not_trigger(self) -> None:
        policy = _make_policy(hitl_triggers=["second_weak_from_gate_5"])
        brief = _make_personalized_brief(
            message_quality=MessageQuality.WEAK,
            regeneration_attempts=0,
        )
        result = evaluate_hitl_triggers({"bu_alpha": brief}, policy)
        assert result == []

    def test_confidence_below_threshold_triggers(self) -> None:
        policy = _make_policy(gate_4_any=0.9, hitl_triggers=["confidence_below_threshold"])
        d = _make_decision(4, DecisionVerb.AFFECTED, 0.5)
        brief = _make_personalized_brief(decisions=[d])
        result = evaluate_hitl_triggers({"bu_alpha": brief}, policy)
        assert len(result) == 1
        assert result[0].reason == HITLReason.CONFIDENCE_BELOW_THRESHOLD

    def test_agent_escalate_triggers(self) -> None:
        policy = _make_policy(hitl_triggers=["any_agent_escalate"])
        d = _make_decision(4, DecisionVerb.ESCALATE, 0.5)
        brief = _make_personalized_brief(decisions=[d])
        result = evaluate_hitl_triggers({"bu_alpha": brief}, policy)
        assert len(result) == 1
        assert result[0].reason == HITLReason.AGENT_ESCALATE

    def test_mlr_sensitive_triggers(self) -> None:
        policy = _make_policy(scientific=["efficacy data"])
        brief = _make_personalized_brief(push_short="shows efficacy data in trials")
        result = evaluate_hitl_triggers({"bu_alpha": brief}, policy)
        assert len(result) == 1
        assert result[0].reason == HITLReason.MLR_SENSITIVE

    def test_commitment_triggers_draft_has_commitment(self) -> None:
        policy = _make_policy(commitments=["available by q2"])
        brief = _make_personalized_brief(push_short="feature available by q2")
        result = evaluate_hitl_triggers({"bu_alpha": brief}, policy)
        assert len(result) == 1
        assert result[0].reason == HITLReason.DRAFT_HAS_COMMITMENT

    def test_sensitive_data_triggers_restricted_term(self) -> None:
        policy = _make_policy(sensitive=["ssn"])
        brief = _make_personalized_brief(push_short="patient ssn required")
        result = evaluate_hitl_triggers({"bu_alpha": brief}, policy)
        assert len(result) == 1
        assert result[0].reason == HITLReason.RESTRICTED_TERM_DETECTED

    def test_early_exit_returns_first_trigger_only(self) -> None:
        policy = _make_policy(
            hitl_triggers=["priority_p0"],
            scientific=["efficacy data"],
        )
        brief_p0 = _make_personalized_brief(
            "bu_alpha", priority=Priority.P0, push_short="efficacy data test"
        )
        result = evaluate_hitl_triggers({"bu_alpha": brief_p0}, policy)
        assert len(result) == 1
        assert result[0].reason == HITLReason.PRIORITY_P0

    def test_bu_id_recorded_in_trigger(self) -> None:
        policy = _make_policy(hitl_triggers=["priority_p0"])
        brief = _make_personalized_brief("bu_delta", priority=Priority.P0)
        result = evaluate_hitl_triggers({"bu_delta": brief}, policy)
        assert result[0].bu_id == "bu_delta"
