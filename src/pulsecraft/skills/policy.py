"""Policy skill — confidence threshold checks, restricted term scanning, HITL trigger evaluation."""

from __future__ import annotations

from dataclasses import dataclass

from pulsecraft.orchestrator.hitl import HITLReason
from pulsecraft.schemas.decision import Decision, DecisionVerb
from pulsecraft.schemas.personalized_brief import (
    MessageQuality,
    PersonalizedBrief,
    Priority,
    Relevance,
)
from pulsecraft.schemas.policy import Policy


@dataclass
class RestrictedTermHit:
    """A single hit when scanning text for restricted terms."""

    category: str
    term: str
    position: int


@dataclass
class HITLTrigger:
    """A single HITL trigger raised during policy evaluation."""

    reason: HITLReason
    description: str
    bu_id: str | None = None


def check_confidence_threshold(decision: Decision, policy: Policy) -> bool:
    """Return True if decision.confidence meets the policy threshold for its gate+verb.

    Gates 1-3 use signalscribe thresholds; 4-5 use buatlas; 6 uses pushpilot.
    Unknown gate/verb combinations pass by default (no threshold defined).
    """
    t = policy.confidence_thresholds
    gate = decision.gate
    verb = decision.verb

    if gate == 1:
        threshold = (
            t.signalscribe.gate_1_communicate
            if verb == DecisionVerb.COMMUNICATE
            else t.signalscribe.gate_1_archive
        )
        return decision.confidence >= threshold
    if gate == 2:
        return decision.confidence >= t.signalscribe.gate_2_ripe
    if gate == 3:
        return decision.confidence >= t.signalscribe.gate_3_ready
    if gate == 4:
        return decision.confidence >= t.buatlas.gate_4_any
    if gate == 5:
        return decision.confidence >= t.buatlas.gate_5_worth_sending
    if gate == 6:
        return decision.confidence >= t.pushpilot.gate_6_any
    return True


def check_restricted_terms(text: str, policy: Policy) -> list[RestrictedTermHit]:
    """Scan text for any phrase from policy.restricted_terms.

    Returns a list of RestrictedTermHit, one per matched term. Matching is
    case-insensitive; position is the character index in the lowercased text.
    Returns an empty list if no hits.
    """
    hits: list[RestrictedTermHit] = []
    lowered = text.lower()
    if not lowered:
        return hits

    for term in policy.restricted_terms.sensitive_data_markers:
        pos = lowered.find(term.lower())
        if pos >= 0:
            hits.append(
                RestrictedTermHit(category="sensitive_data_markers", term=term, position=pos)
            )

    for term in policy.restricted_terms.commitments_and_dates:
        pos = lowered.find(term.lower())
        if pos >= 0:
            hits.append(
                RestrictedTermHit(category="commitments_and_dates", term=term, position=pos)
            )

    for term in policy.restricted_terms.scientific_communication:
        pos = lowered.find(term.lower())
        if pos >= 0:
            hits.append(
                RestrictedTermHit(category="scientific_communication", term=term, position=pos)
            )

    return hits


def _collect_message_text(brief: PersonalizedBrief) -> str:
    """Concatenate all message variants for term scanning."""
    if brief.message_variants is None:
        return ""
    parts = [
        brief.message_variants.push_short or "",
        brief.message_variants.teams_medium or "",
        brief.message_variants.email_long or "",
    ]
    return " ".join(parts).lower()


def evaluate_hitl_triggers(
    personalized_briefs: dict[str, PersonalizedBrief],
    policy: Policy,
) -> list[HITLTrigger]:
    """Aggregate HITL triggers across all briefs. Returns empty list if no triggers fire.

    Checks in order: priority_p0, second_weak_from_gate_5, confidence_below_threshold,
    any_agent_escalate, restricted terms. Returns at most one trigger (early exit).
    """
    active_triggers = set(policy.hitl_triggers)

    for bu_id, brief in personalized_briefs.items():
        if brief.relevance == Relevance.NOT_AFFECTED:
            continue

        if "priority_p0" in active_triggers and brief.priority == Priority.P0:
            return [HITLTrigger(HITLReason.PRIORITY_P0, f"bu={bu_id} has priority P0", bu_id)]

        if (
            "second_weak_from_gate_5" in active_triggers
            and brief.message_quality == MessageQuality.WEAK
            and brief.regeneration_attempts >= 1
        ):
            return [
                HITLTrigger(
                    HITLReason.SECOND_WEAK_FROM_GATE_5, f"bu={bu_id} WEAK after regen", bu_id
                )
            ]

        if "confidence_below_threshold" in active_triggers:
            for d in brief.decisions:
                if not check_confidence_threshold(d, policy):
                    return [
                        HITLTrigger(
                            HITLReason.CONFIDENCE_BELOW_THRESHOLD,
                            f"bu={bu_id} gate_{d.gate} confidence {d.confidence:.2f} below threshold",
                            bu_id,
                        )
                    ]

        if "any_agent_escalate" in active_triggers:
            for d in brief.decisions:
                if d.verb == DecisionVerb.ESCALATE:
                    return [
                        HITLTrigger(
                            HITLReason.AGENT_ESCALATE, f"bu={bu_id} BUAtlas ESCALATE", bu_id
                        )
                    ]

        text = _collect_message_text(brief)
        hits = check_restricted_terms(text, policy)
        if hits:
            hit = hits[0]
            hitl_reason: HITLReason
            if hit.category == "sensitive_data_markers":
                hitl_reason = HITLReason.RESTRICTED_TERM_DETECTED
            elif hit.category == "commitments_and_dates":
                hitl_reason = HITLReason.DRAFT_HAS_COMMITMENT
            else:
                hitl_reason = HITLReason.MLR_SENSITIVE
            return [HITLTrigger(hitl_reason, f"bu={bu_id} {hit.category}: '{hit.term}'", bu_id)]

    return []
