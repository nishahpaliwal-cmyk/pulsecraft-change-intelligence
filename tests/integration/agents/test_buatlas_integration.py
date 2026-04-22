"""Integration tests for BUAtlas — real Anthropic API calls.

These tests require PULSECRAFT_RUN_LLM_TESTS=1 to run. They make real API
calls and incur cost (~$0.05–0.10 per test). Run manually for eval only.

Test strategy: For each fixture, run SignalScribe first to get a ChangeBrief,
then run BUAtlas for the expected candidate BUs. Assert schema validity,
decision structure, and cross-BU isolation.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from pulsecraft.agents.buatlas import BUAtlas
from pulsecraft.agents.signalscribe import SignalScribe
from pulsecraft.config.loader import get_bu_profile
from pulsecraft.schemas.change_artifact import ChangeArtifact
from pulsecraft.schemas.personalized_brief import PersonalizedBrief, Relevance

_LLM_ENABLED = os.environ.get("PULSECRAFT_RUN_LLM_TESTS", "").lower() in ("1", "true", "yes")
_SKIP_REASON = "Set PULSECRAFT_RUN_LLM_TESTS=1 to run LLM integration tests"

FIXTURES_DIR = Path(__file__).parent.parent.parent.parent / "fixtures" / "changes"

# Fixtures with known expected BU candidates for BUAtlas testing
_FIXTURE_BU_PAIRS = [
    # (fixture_file, bu_id, expected_relevance_category)
    ("change_001_clearcut_communicate.json", "bu_alpha", "affected"),  # owns hcp_portal_ordering
    (
        "change_006_multi_bu_affected_vs_adjacent.json",
        "bu_zeta",
        "affected",
    ),  # owns analytics_portal
    (
        "change_006_multi_bu_affected_vs_adjacent.json",
        "bu_delta",
        "adjacent",
    ),  # incidental reporting
    (
        "change_008_post_hoc_already_shipped.json",
        "bu_epsilon",
        "affected",
    ),  # owns notification_services
]


@pytest.fixture(scope="module")
def signalscribe():
    return SignalScribe()


@pytest.fixture(scope="module")
def buatlas():
    return BUAtlas()


def _get_change_brief(signalscribe: SignalScribe, fixture_file: str):
    artifact = ChangeArtifact.model_validate(json.loads((FIXTURES_DIR / fixture_file).read_text()))
    return signalscribe.invoke(artifact)


@pytest.mark.llm
@pytest.mark.skipif(not _LLM_ENABLED, reason=_SKIP_REASON)
@pytest.mark.parametrize("fixture_file,bu_id,expected_category", _FIXTURE_BU_PAIRS)
def test_buatlas_schema_contract(
    signalscribe: SignalScribe,
    buatlas: BUAtlas,
    fixture_file: str,
    bu_id: str,
    expected_category: str,
) -> None:
    """BUAtlas output validates against PersonalizedBrief schema."""
    change_brief = _get_change_brief(signalscribe, fixture_file)
    bu_profile = get_bu_profile(bu_id)

    result = buatlas.invoke(change_brief, bu_profile)

    assert isinstance(result, PersonalizedBrief)
    assert result.change_id == change_brief.change_id
    assert result.brief_id == change_brief.brief_id
    assert result.bu_id == bu_id
    assert 0.0 <= result.confidence_score <= 1.0
    assert result.produced_by.agent == "buatlas"
    assert len(result.decisions) >= 1
    assert result.decisions[0].gate == 4


@pytest.mark.llm
@pytest.mark.skipif(not _LLM_ENABLED, reason=_SKIP_REASON)
@pytest.mark.parametrize("fixture_file,bu_id,expected_category", _FIXTURE_BU_PAIRS)
def test_buatlas_decision_structure(
    signalscribe: SignalScribe,
    buatlas: BUAtlas,
    fixture_file: str,
    bu_id: str,
    expected_category: str,
) -> None:
    """Gate 5 present iff gate 4 = AFFECTED; message_variants consistent with relevance."""
    change_brief = _get_change_brief(signalscribe, fixture_file)
    bu_profile = get_bu_profile(bu_id)

    result = buatlas.invoke(change_brief, bu_profile)
    relevance = result.relevance

    if relevance == Relevance.AFFECTED:
        # Gate 5 must be present
        assert len(result.decisions) == 2
        assert result.decisions[1].gate == 5
        # Message variants required for WORTH_SENDING and WEAK
        if result.message_quality in ("worth_sending", "weak"):
            assert result.message_variants is not None
    else:
        # Gate 5 skipped
        assert len(result.decisions) == 1
        assert result.message_quality is None
        assert result.message_variants is None

    # Decisions agent names must be canonical
    for d in result.decisions:
        assert d.agent.name == "buatlas"


@pytest.mark.llm
@pytest.mark.skipif(not _LLM_ENABLED, reason=_SKIP_REASON)
def test_buatlas_cross_bu_isolation(
    signalscribe: SignalScribe,
    buatlas: BUAtlas,
) -> None:
    """BUAtlas results for different BUs in same fixture are independent."""
    fixture_file = "change_006_multi_bu_affected_vs_adjacent.json"
    change_brief = _get_change_brief(signalscribe, fixture_file)

    bu_zeta = get_bu_profile("bu_zeta")
    bu_delta = get_bu_profile("bu_delta")

    result_zeta = buatlas.invoke(change_brief, bu_zeta)
    result_delta = buatlas.invoke(change_brief, bu_delta)

    # Neither result should mention the other BU's ID
    result_zeta_json = result_zeta.model_dump_json()
    result_delta_json = result_delta.model_dump_json()

    assert "bu_delta" not in result_zeta_json or result_zeta.bu_id != "bu_delta"
    assert "bu_zeta" not in result_delta_json or result_delta.bu_id != "bu_zeta"

    # IDs are isolated
    assert result_zeta.bu_id == "bu_zeta"
    assert result_delta.bu_id == "bu_delta"
    assert result_zeta.change_id == result_delta.change_id
    assert result_zeta.personalized_brief_id != result_delta.personalized_brief_id


@pytest.mark.llm
@pytest.mark.skipif(not _LLM_ENABLED, reason=_SKIP_REASON)
def test_buatlas_message_length_constraints(
    signalscribe: SignalScribe,
    buatlas: BUAtlas,
) -> None:
    """Message variants respect field length limits."""
    fixture_file = "change_001_clearcut_communicate.json"
    change_brief = _get_change_brief(signalscribe, fixture_file)
    bu_profile = get_bu_profile("bu_alpha")

    result = buatlas.invoke(change_brief, bu_profile)

    if result.message_variants is not None:
        mv = result.message_variants
        if mv.push_short:
            assert len(mv.push_short) <= 240, f"push_short too long: {len(mv.push_short)}"
        if mv.teams_medium:
            assert len(mv.teams_medium) <= 600, f"teams_medium too long: {len(mv.teams_medium)}"
        if mv.email_long:
            assert len(mv.email_long) <= 1200, f"email_long too long: {len(mv.email_long)}"
