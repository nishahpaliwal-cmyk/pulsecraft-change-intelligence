"""Registry skill — BU candidate lookup for the pre-filter stage."""

from __future__ import annotations

from pulsecraft.schemas.bu_registry import BURegistry
from pulsecraft.schemas.change_brief import ChangeBrief


def lookup_bu_candidates(change_brief: ChangeBrief, registry: BURegistry) -> list[str]:
    """Return BU IDs whose owned_product_areas intersect change_brief.impact_areas.

    Exact match on owned_product_areas. Recall-biased: prefer over-matching;
    BUAtlas (gate 4) applies precision. Returns BU IDs in registry order.
    """
    impact_areas = set(change_brief.impact_areas)
    candidates = []
    for entry in registry.bus:
        owned = set(entry.owned_product_areas)
        if owned & impact_areas:
            candidates.append(entry.bu_id)
    return candidates
