"""PostAgent hook — validate agent output after each invocation."""

from __future__ import annotations

from pulsecraft.hooks.base import HookContext, HookResult


def run(ctx: HookContext) -> HookResult:
    """Check confidence thresholds and scan for restricted terms.

    Expects ctx.payload:
    - 'agent_name': str
    - 'decisions': list[Decision] (pulsecraft.schemas.decision.Decision)
    - 'message_text': str  (drafted message content; empty for SignalScribe/PushPilot)
    - 'policy': Policy object

    Returns fail if any decision is below threshold, or restricted terms are found.
    """
    from pulsecraft.schemas.decision import DecisionVerb
    from pulsecraft.skills.policy import check_confidence_threshold, check_restricted_terms

    decisions = ctx.payload.get("decisions") or []
    message_text = ctx.payload.get("message_text") or ""
    policy = ctx.payload.get("policy")
    agent_name = ctx.payload.get("agent_name", "unknown")

    if policy is None:
        return HookResult.skipped("no policy provided")

    # Decisions that intentionally route to HITL or HELD are not confidence violations.
    _ROUTING_VERBS = frozenset(
        {
            DecisionVerb.ESCALATE,
            DecisionVerb.NEED_CLARIFICATION,
            DecisionVerb.UNRESOLVABLE,
            DecisionVerb.ARCHIVE,
        }
    )

    failures: list[str] = []

    for d in decisions:
        if d.verb in _ROUTING_VERBS:
            continue
        if not check_confidence_threshold(d, policy):
            failures.append(f"gate_{d.gate} confidence {d.confidence:.2f} below threshold")

    if message_text:
        hits = check_restricted_terms(message_text, policy)
        for hit in hits:
            failures.append(f"restricted_term [{hit.category}]: '{hit.term}'")

    if failures:
        return HookResult.failed(
            f"post_agent validation failed for {agent_name}",
            failures=failures,
        )

    return HookResult.passed(
        reason=f"{agent_name} output passed validation",
        decisions_checked=len(decisions),
    )
