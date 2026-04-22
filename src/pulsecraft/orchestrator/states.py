"""Workflow state machine for the PulseCraft orchestrator.

States and transitions are the authoritative description of what the orchestrator
does. Every call to apply_transition writes an audit record in engine.py — this
module is pure data/logic with no side effects.
"""

from __future__ import annotations

from enum import StrEnum


class WorkflowState(StrEnum):
    """All possible states in a change-event workflow run."""

    RECEIVED = "RECEIVED"
    INTERPRETED = "INTERPRETED"
    ROUTED = "ROUTED"
    PERSONALIZED = "PERSONALIZED"
    AWAITING_HITL = "AWAITING_HITL"
    SCHEDULED = "SCHEDULED"
    DELIVERED = "DELIVERED"
    ARCHIVED = "ARCHIVED"
    HELD = "HELD"
    DIGESTED = "DIGESTED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


TERMINAL_STATES: frozenset[WorkflowState] = frozenset(
    {
        WorkflowState.DELIVERED,
        WorkflowState.ARCHIVED,
        WorkflowState.HELD,
        WorkflowState.DIGESTED,
        WorkflowState.REJECTED,
        WorkflowState.FAILED,
        WorkflowState.AWAITING_HITL,
    }
)


class IllegalTransitionError(Exception):
    """Raised when an (from_state, event) pair has no defined transition."""


# Transition table: (from_state, event_name) → to_state
#
# Event names are stable string identifiers emitted by engine.py's decision
# interpretation logic. Adding a new event here is the authoritative way to
# extend the state machine.
_TRANSITIONS: dict[tuple[WorkflowState, str], WorkflowState] = {
    # ── RECEIVED ──────────────────────────────────────────────────────────
    # SignalScribe gates 1-3 all positive → proceed to BU matching
    (WorkflowState.RECEIVED, "signalscribe_communicate_ripe_ready"): WorkflowState.INTERPRETED,
    # Gate 1 ARCHIVE → done, no one to notify
    (WorkflowState.RECEIVED, "signalscribe_archive"): WorkflowState.ARCHIVED,
    # Gate 2 hold (HOLD_UNTIL or HOLD_INDEFINITE) → defer this change
    (WorkflowState.RECEIVED, "signalscribe_hold"): WorkflowState.HELD,
    # Any SignalScribe gate escalates or needs clarification → HITL
    (WorkflowState.RECEIVED, "signalscribe_hitl"): WorkflowState.AWAITING_HITL,
    (WorkflowState.RECEIVED, "error"): WorkflowState.FAILED,
    # ── INTERPRETED ───────────────────────────────────────────────────────
    (WorkflowState.INTERPRETED, "bu_candidates_found"): WorkflowState.ROUTED,
    (WorkflowState.INTERPRETED, "no_candidate_bus"): WorkflowState.ARCHIVED,
    (WorkflowState.INTERPRETED, "error"): WorkflowState.FAILED,
    # ── ROUTED ────────────────────────────────────────────────────────────
    # BUAtlas fan-out complete; at least one not-rejected result
    (WorkflowState.ROUTED, "personalization_complete"): WorkflowState.PERSONALIZED,
    # All BUs returned NOT_AFFECTED → nothing to send
    (WorkflowState.ROUTED, "all_not_affected"): WorkflowState.ARCHIVED,
    # BUAtlas ESCALATE → HITL
    (WorkflowState.ROUTED, "buatlas_hitl"): WorkflowState.AWAITING_HITL,
    (WorkflowState.ROUTED, "error"): WorkflowState.FAILED,
    # ── PERSONALIZED ──────────────────────────────────────────────────────
    # Policy / priority HITL triggers fire
    (WorkflowState.PERSONALIZED, "hitl_triggered"): WorkflowState.AWAITING_HITL,
    # PushPilot scheduling done; at least one actionable delivery plan
    (WorkflowState.PERSONALIZED, "scheduling_complete"): WorkflowState.SCHEDULED,
    # All personalized briefs were NOT_WORTH or NOT_AFFECTED
    (WorkflowState.PERSONALIZED, "all_not_worth"): WorkflowState.ARCHIVED,
    (WorkflowState.PERSONALIZED, "error"): WorkflowState.FAILED,
    # ── SCHEDULED ─────────────────────────────────────────────────────────
    # At least one SEND_NOW notification dispatched
    (WorkflowState.SCHEDULED, "delivered"): WorkflowState.DELIVERED,
    # All notifications routed to digest queue
    (WorkflowState.SCHEDULED, "all_digested"): WorkflowState.DIGESTED,
    # All notifications held until a future time
    (WorkflowState.SCHEDULED, "all_held"): WorkflowState.HELD,
    # PushPilot ESCALATE or post-schedule policy conflict
    (WorkflowState.SCHEDULED, "pushpilot_hitl"): WorkflowState.AWAITING_HITL,
    (WorkflowState.SCHEDULED, "error"): WorkflowState.FAILED,
    # ── AWAITING_HITL (transitions driven by future HITL command prompt) ──
    (WorkflowState.AWAITING_HITL, "hitl_approved"): WorkflowState.PERSONALIZED,
    (WorkflowState.AWAITING_HITL, "hitl_rejected"): WorkflowState.REJECTED,
    (WorkflowState.AWAITING_HITL, "error"): WorkflowState.FAILED,
}


def valid_transitions(from_state: WorkflowState) -> dict[str, WorkflowState]:
    """Return all (event → to_state) pairs reachable from from_state."""
    return {
        event: to_state for (state, event), to_state in _TRANSITIONS.items() if state == from_state
    }


def apply_transition(current_state: WorkflowState, event: str) -> WorkflowState:
    """Return the next state for (current_state, event), or raise IllegalTransitionError."""
    key = (current_state, event)
    if key not in _TRANSITIONS:
        raise IllegalTransitionError(
            f"No transition defined for state={current_state!r} + event={event!r}. "
            f"Valid events from {current_state!r}: {sorted(valid_transitions(current_state))}"
        )
    return _TRANSITIONS[key]
