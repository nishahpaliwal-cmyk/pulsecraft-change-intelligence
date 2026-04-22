"""Unit tests for buatlas_fanout — parallelism, failure isolation, ordering."""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

from pulsecraft.agents.buatlas_fanout import FanoutFailure, buatlas_fanout, buatlas_fanout_sync
from pulsecraft.config.loader import get_bu_profile
from pulsecraft.schemas.change_brief import ChangeBrief
from pulsecraft.schemas.decision import Decision, DecisionAgent, DecisionVerb
from pulsecraft.schemas.personalized_brief import (
    MessageQuality,
    MessageVariants,
    PersonalizedBrief,
    Priority,
    RecommendedAction,
    Relevance,
)
from pulsecraft.schemas.personalized_brief import ProducedBy as PBProducedBy

FIXTURES_DIR = Path(__file__).parent.parent.parent.parent / "fixtures" / "changes"


def _make_change_brief() -> ChangeBrief:
    import json

    from pulsecraft.schemas.change_artifact import ChangeArtifact
    from pulsecraft.schemas.change_brief import (
        ChangeType,
        SourceCitation,
        Timeline,
        TimelineStatus,
    )
    from pulsecraft.schemas.change_brief import (
        ProducedBy as CBProducedBy,
    )

    artifact = ChangeArtifact.model_validate(
        json.loads((FIXTURES_DIR / "change_001_clearcut_communicate.json").read_text())
    )
    now = datetime.now(tz=UTC)
    agent = DecisionAgent(name="signalscribe", version="1.0")
    return ChangeBrief(
        brief_id=str(uuid.uuid4()),
        change_id=artifact.change_id,
        produced_at=now,
        produced_by=CBProducedBy(version="1.0"),
        summary="Test change brief.",
        before="before state",
        after="after state",
        change_type=ChangeType.BEHAVIOR_CHANGE,
        impact_areas=["specialty_pharmacy"],
        affected_segments=["hcp_users"],
        timeline=Timeline(status=TimelineStatus.RIPE),
        required_actions=[],
        risks=[],
        mitigations=[],
        faq=[],
        sources=[SourceCitation(type="release_note", ref="REF-001", quote="test change")],
        confidence_score=0.90,
        decisions=[
            Decision(
                gate=1,
                verb=DecisionVerb.COMMUNICATE,
                reason="Visible change.",
                confidence=0.90,
                decided_at=now,
                agent=agent,
            ),
            Decision(
                gate=2,
                verb=DecisionVerb.RIPE,
                reason="Rollout imminent.",
                confidence=0.90,
                decided_at=now,
                agent=agent,
            ),
            Decision(
                gate=3,
                verb=DecisionVerb.READY,
                reason="Interpretation clear.",
                confidence=0.90,
                decided_at=now,
                agent=agent,
            ),
        ],
    )


def _make_mock_personalized_brief(bu_id: str, change_brief: ChangeBrief) -> PersonalizedBrief:
    now = datetime.now(tz=UTC)
    return PersonalizedBrief(
        personalized_brief_id=str(uuid.uuid4()),
        change_id=change_brief.change_id,
        brief_id=change_brief.brief_id,
        bu_id=bu_id,
        produced_at=now,
        produced_by=PBProducedBy(version="1.0", invocation_id=str(uuid.uuid4())),
        relevance=Relevance.AFFECTED,
        priority=Priority.P1,
        why_relevant=f"Mock: {bu_id} is affected.",
        recommended_actions=[RecommendedAction(owner="BU head", action="Review change.")],
        assumptions=["Mock assumption."],
        message_variants=MessageVariants(
            push_short=f"Change affects {bu_id}.",
            teams_medium=f"A change relevant to {bu_id} has been detected.",
            email_long=f"Full email body for {bu_id}.",
        ),
        message_quality=MessageQuality.WORTH_SENDING,
        confidence_score=0.88,
        decisions=[
            Decision(
                gate=4,
                verb=DecisionVerb.AFFECTED,
                reason=f"Mock: {bu_id} owns the affected area.",
                confidence=0.88,
                decided_at=now,
                agent=DecisionAgent(name="buatlas", version="1.0"),
            ),
            Decision(
                gate=5,
                verb=DecisionVerb.WORTH_SENDING,
                reason="Mock: message is specific.",
                confidence=0.87,
                decided_at=now,
                agent=DecisionAgent(name="buatlas", version="1.0"),
            ),
        ],
        regeneration_attempts=0,
    )


class MockBUAtlas:
    """Test double — returns a pre-built PersonalizedBrief, optionally sleeps."""

    agent_name = "buatlas"
    version = "mock-1.0"

    def __init__(self, result_or_exception, sleep_seconds: float = 0.0):
        self._result = result_or_exception
        self._sleep = sleep_seconds

    def invoke(self, change_brief, bu_profile, past_engagement=None) -> PersonalizedBrief:
        if self._sleep > 0:
            time.sleep(self._sleep)
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


class TestBUAtlasFanoutEmpty:
    def test_empty_bus_returns_empty_list(self) -> None:
        cb = _make_change_brief()
        result = buatlas_fanout_sync(cb, [], factory=lambda: MockBUAtlas(None))
        assert result == []


class TestBUAtlasFanoutOrdering:
    def test_results_preserve_input_order(self) -> None:
        cb = _make_change_brief()
        bu_ids = ["bu_alpha", "bu_beta", "bu_gamma"]
        bus = [get_bu_profile(bu_id) for bu_id in bu_ids]
        briefs = [_make_mock_personalized_brief(bu_id, cb) for bu_id in bu_ids]
        brief_iter = iter(briefs)

        def factory():
            pb = next(brief_iter)
            return MockBUAtlas(pb)

        results = buatlas_fanout_sync(cb, bus, factory=factory)
        assert len(results) == 3
        for i, bu_id in enumerate(bu_ids):
            assert isinstance(results[i], PersonalizedBrief)
            assert results[i].bu_id == bu_id

    def test_single_bu_returns_single_result(self) -> None:
        cb = _make_change_brief()
        bu = get_bu_profile("bu_alpha")
        pb = _make_mock_personalized_brief("bu_alpha", cb)
        results = buatlas_fanout_sync(cb, [bu], factory=lambda: MockBUAtlas(pb))
        assert len(results) == 1
        assert isinstance(results[0], PersonalizedBrief)


class TestBUAtlasFanoutFailureIsolation:
    def test_one_failure_does_not_kill_others(self) -> None:
        cb = _make_change_brief()
        bu_alpha = get_bu_profile("bu_alpha")
        bu_beta = get_bu_profile("bu_beta")
        bu_gamma = get_bu_profile("bu_gamma")

        pb_alpha = _make_mock_personalized_brief("bu_alpha", cb)
        pb_gamma = _make_mock_personalized_brief("bu_gamma", cb)

        factory_results = [pb_alpha, RuntimeError("API error for bu_beta"), pb_gamma]
        call_count = [0]

        def factory():
            idx = call_count[0]
            call_count[0] += 1
            res = factory_results[idx]
            return MockBUAtlas(res)

        results = buatlas_fanout_sync(cb, [bu_alpha, bu_beta, bu_gamma], factory=factory)
        assert len(results) == 3
        assert isinstance(results[0], PersonalizedBrief)
        assert isinstance(results[1], FanoutFailure)
        assert isinstance(results[2], PersonalizedBrief)
        assert results[1].bu_id == "bu_beta"

    def test_failure_captures_error_info(self) -> None:
        cb = _make_change_brief()
        bu = get_bu_profile("bu_beta")
        exc = ValueError("something went wrong")
        results = buatlas_fanout_sync(cb, [bu], factory=lambda: MockBUAtlas(exc))
        assert len(results) == 1
        assert isinstance(results[0], FanoutFailure)
        assert results[0].bu_id == "bu_beta"
        assert "something went wrong" in results[0].error_message
        assert results[0].error_type == "ValueError"

    def test_validation_error_is_not_retriable(self) -> None:
        from pulsecraft.agents.buatlas import AgentOutputValidationError

        cb = _make_change_brief()
        bu = get_bu_profile("bu_beta")
        exc = AgentOutputValidationError("validation failed after 2 attempts")
        results = buatlas_fanout_sync(cb, [bu], factory=lambda: MockBUAtlas(exc))
        assert isinstance(results[0], FanoutFailure)
        assert results[0].retriable is False

    def test_generic_error_is_retriable(self) -> None:
        cb = _make_change_brief()
        bu = get_bu_profile("bu_beta")
        exc = RuntimeError("transient network error")
        results = buatlas_fanout_sync(cb, [bu], factory=lambda: MockBUAtlas(exc))
        assert isinstance(results[0], FanoutFailure)
        assert results[0].retriable is True


class TestBUAtlasFanoutConcurrency:
    def test_max_concurrent_one_forces_sequential(self) -> None:
        """With max_concurrent=1, calls are sequential — result ordering still correct."""
        cb = _make_change_brief()
        bus = [get_bu_profile("bu_alpha"), get_bu_profile("bu_beta")]
        briefs = [
            _make_mock_personalized_brief("bu_alpha", cb),
            _make_mock_personalized_brief("bu_beta", cb),
        ]
        brief_iter = iter(briefs)
        factory = lambda: MockBUAtlas(next(brief_iter))  # noqa: E731

        results = buatlas_fanout_sync(cb, bus, factory=factory, max_concurrent=1)
        assert len(results) == 2
        assert results[0].bu_id == "bu_alpha"
        assert results[1].bu_id == "bu_beta"

    @pytest.mark.asyncio
    async def test_parallel_invocations_run_concurrently(self) -> None:
        """Three 0.1s sleeps should complete in roughly 0.1s total with async."""
        cb = _make_change_brief()
        bus = [get_bu_profile("bu_alpha"), get_bu_profile("bu_beta"), get_bu_profile("bu_gamma")]
        briefs = [
            _make_mock_personalized_brief("bu_alpha", cb),
            _make_mock_personalized_brief("bu_beta", cb),
            _make_mock_personalized_brief("bu_gamma", cb),
        ]
        brief_iter = iter(briefs)

        def factory():
            pb = next(brief_iter)
            return MockBUAtlas(pb, sleep_seconds=0.1)

        start = time.monotonic()
        results = await buatlas_fanout(cb, bus, factory=factory, max_concurrent=5)
        elapsed = time.monotonic() - start

        assert len(results) == 3
        # With parallelism, 3×0.1s should complete in <0.35s (not 0.3s sequential)
        assert elapsed < 0.35, f"Parallel fanout took {elapsed:.2f}s — expected ~0.1s"
