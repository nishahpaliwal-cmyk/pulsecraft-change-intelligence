"""Unit tests for the registry skill — BU candidate lookup."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pulsecraft.schemas.bu_registry import BURegistry, BURegistryEntry
from pulsecraft.schemas.change_brief import (
    ChangeBrief,
    ChangeType,
    ProducedBy,
    Timeline,
    TimelineStatus,
)
from pulsecraft.skills.registry import lookup_bu_candidates


def _make_registry(*entries: BURegistryEntry) -> BURegistry:
    return BURegistry(bus=list(entries))


def _make_entry(bu_id: str, owned: list[str], keywords: list[str] | None = None) -> BURegistryEntry:
    return BURegistryEntry(
        bu_id=bu_id,
        name=bu_id.upper(),
        owned_product_areas=owned,
        keywords=keywords or ["keyword"],
    )


def _make_brief(impact_areas: list[str]) -> ChangeBrief:
    now = datetime.now(UTC)
    return ChangeBrief(
        brief_id=str(uuid.uuid4()),
        change_id=str(uuid.uuid4()),
        produced_at=now,
        produced_by=ProducedBy(version="1.0"),
        summary="Test change.",
        before="old state",
        after="new state",
        change_type=ChangeType.NEW_FEATURE,
        impact_areas=impact_areas,
        affected_segments=[],
        timeline=Timeline(status=TimelineStatus.RIPE),
        required_actions=[],
        risks=[],
        mitigations=[],
        faq=[],
        sources=[],
        confidence_score=0.9,
        decisions=[],
    )


class TestLookupBUCandidates:
    def test_empty_impact_areas_returns_empty(self) -> None:
        registry = _make_registry(
            _make_entry("bu_alpha", ["specialty_pharmacy", "hcp_portal_ordering"]),
        )
        brief = _make_brief([])
        assert lookup_bu_candidates(brief, registry) == []

    def test_single_term_match_returns_correct_bu(self) -> None:
        registry = _make_registry(
            _make_entry("bu_alpha", ["specialty_pharmacy", "hcp_portal_ordering"]),
            _make_entry("bu_beta", ["patient_portal", "co_pay_programs"]),
        )
        brief = _make_brief(["specialty_pharmacy"])
        result = lookup_bu_candidates(brief, registry)
        assert result == ["bu_alpha"]

    def test_multi_term_spanning_multiple_bus(self) -> None:
        registry = _make_registry(
            _make_entry("bu_alpha", ["specialty_pharmacy"]),
            _make_entry("bu_beta", ["patient_portal"]),
            _make_entry("bu_gamma", ["medical_information_portal"]),
        )
        brief = _make_brief(["specialty_pharmacy", "patient_portal"])
        result = lookup_bu_candidates(brief, registry)
        assert "bu_alpha" in result
        assert "bu_beta" in result
        assert "bu_gamma" not in result

    def test_no_match_returns_empty_list(self) -> None:
        registry = _make_registry(
            _make_entry("bu_alpha", ["specialty_pharmacy"]),
        )
        brief = _make_brief(["analytics_portal"])
        assert lookup_bu_candidates(brief, registry) == []

    def test_exact_match_only_no_substring(self) -> None:
        registry = _make_registry(
            _make_entry("bu_alpha", ["specialty_pharmacy"]),
        )
        # "specialty" alone should NOT match "specialty_pharmacy"
        brief = _make_brief(["specialty"])
        assert lookup_bu_candidates(brief, registry) == []

    def test_registry_order_preserved(self) -> None:
        registry = _make_registry(
            _make_entry("bu_zeta", ["analytics_portal"]),
            _make_entry("bu_alpha", ["specialty_pharmacy"]),
        )
        brief = _make_brief(["analytics_portal", "specialty_pharmacy"])
        result = lookup_bu_candidates(brief, registry)
        assert result == ["bu_zeta", "bu_alpha"]

    def test_all_bus_match(self) -> None:
        registry = _make_registry(
            _make_entry("bu_alpha", ["area_a"]),
            _make_entry("bu_beta", ["area_b"]),
            _make_entry("bu_gamma", ["area_c"]),
        )
        brief = _make_brief(["area_a", "area_b", "area_c"])
        result = lookup_bu_candidates(brief, registry)
        assert len(result) == 3

    def test_keywords_not_used_in_matching(self) -> None:
        """Keywords are in the registry but the skill only checks owned_product_areas."""
        registry = _make_registry(
            _make_entry("bu_alpha", ["specialty_pharmacy"], keywords=["prior auth", "PA"]),
        )
        # "prior auth" is a keyword but NOT an owned_product_area
        brief = _make_brief(["prior auth"])
        assert lookup_bu_candidates(brief, registry) == []
