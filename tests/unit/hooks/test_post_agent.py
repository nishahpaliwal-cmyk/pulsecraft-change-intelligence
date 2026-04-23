"""Unit tests for post_agent hook."""

from __future__ import annotations

from datetime import UTC, datetime

from pulsecraft.hooks.base import HookContext
from pulsecraft.hooks.post_agent import run
from pulsecraft.schemas.decision import Decision, DecisionAgent, DecisionVerb
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


def _make_decision(gate: int, verb: DecisionVerb, confidence: float) -> Decision:
    name = "signalscribe" if gate <= 3 else ("buatlas" if gate <= 5 else "pushpilot")
    return Decision(
        gate=gate,
        verb=verb,
        reason="test",
        confidence=confidence,
        decided_at=datetime.now(UTC),
        agent=DecisionAgent(name=name, version="1.0"),
    )


def _make_policy(
    gate_1_communicate: float = 0.7,
    commitments: list[str] | None = None,
    sensitive: list[str] | None = None,
) -> Policy:
    return Policy(
        confidence_thresholds=ConfidenceThresholds(
            signalscribe=SignalScribeThresholds(
                gate_1_communicate=gate_1_communicate,
                gate_1_archive=0.6,
                gate_2_ripe=0.7,
                gate_3_ready=0.75,
            ),
            buatlas=BUAtlasThresholds(
                gate_4_affected=0.7,
                gate_4_any=0.6,
                gate_5_worth_sending=0.65,
            ),
            pushpilot=PushPilotThresholds(gate_6_any=0.6),
        ),
        hitl_triggers=[],
        restricted_terms=RestrictedTerms(
            commitments_and_dates=commitments or [],
            scientific_communication=[],
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


def _ctx(
    decisions: list[Decision],
    message_text: str = "",
    policy: Policy | None = None,
    agent_name: str = "signalscribe",
) -> HookContext:
    return HookContext(
        stage="post_agent",
        change_id="change-001",
        payload={
            "agent_name": agent_name,
            "decisions": decisions,
            "message_text": message_text,
            "policy": policy or _make_policy(),
        },
    )


def test_passes_high_confidence_no_restricted_terms():
    d = _make_decision(1, DecisionVerb.COMMUNICATE, 0.9)
    result = run(_ctx([d]))
    assert result.outcome == "pass"
    assert result.details.get("decisions_checked") == 1


def test_fails_when_confidence_below_threshold():
    d = _make_decision(1, DecisionVerb.COMMUNICATE, 0.5)
    result = run(_ctx([d], policy=_make_policy(gate_1_communicate=0.7)))
    assert result.outcome == "fail"
    assert any("confidence" in f for f in result.details.get("failures", []))


def test_fails_when_restricted_term_in_message():
    policy = _make_policy(commitments=["will ship by"])
    d = _make_decision(1, DecisionVerb.COMMUNICATE, 0.9)
    result = run(_ctx([d], message_text="We will ship by Q2.", policy=policy))
    assert result.outcome == "fail"
    assert any("restricted_term" in f for f in result.details.get("failures", []))


def test_passes_when_no_policy():
    ctx = HookContext(
        stage="post_agent",
        change_id="c1",
        payload={"agent_name": "signalscribe", "decisions": [], "message_text": "", "policy": None},
    )
    result = run(ctx)
    assert result.outcome == "skip"


def test_passes_empty_decisions_no_message():
    result = run(_ctx([]))
    assert result.outcome == "pass"


def test_multiple_failures_collected():
    policy = _make_policy(gate_1_communicate=0.9, commitments=["guarantee"])
    d1 = _make_decision(1, DecisionVerb.COMMUNICATE, 0.5)
    d2 = _make_decision(2, DecisionVerb.RIPE, 0.4)
    result = run(_ctx([d1, d2], message_text="We guarantee delivery.", policy=policy))
    assert result.outcome == "fail"
    assert len(result.details.get("failures", [])) >= 2


def test_no_restricted_terms_in_clean_message():
    policy = _make_policy(commitments=["will ship by"])
    d = _make_decision(1, DecisionVerb.COMMUNICATE, 0.9)
    result = run(_ctx([d], message_text="This is an informational update.", policy=policy))
    assert result.outcome == "pass"


def test_empty_message_text_skips_restricted_check():
    policy = _make_policy(commitments=["some phrase"])
    d = _make_decision(1, DecisionVerb.COMMUNICATE, 0.9)
    result = run(_ctx([d], message_text="", policy=policy))
    assert result.outcome == "pass"


def test_sensitive_data_marker_fails():
    policy = _make_policy(sensitive=["patient id"])
    d = _make_decision(1, DecisionVerb.COMMUNICATE, 0.9)
    result = run(_ctx([d], message_text="Reference patient id 123.", policy=policy))
    assert result.outcome == "fail"
