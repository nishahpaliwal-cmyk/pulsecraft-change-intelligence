"""Tests for the WorkflowState state machine."""

import pytest

from pulsecraft.orchestrator.states import (
    TERMINAL_STATES,
    IllegalTransitionError,
    WorkflowState,
    apply_transition,
    valid_transitions,
)


class TestWorkflowState:
    def test_all_states_are_strings(self) -> None:
        for state in WorkflowState:
            assert isinstance(state, str)

    def test_terminal_states_are_subset_of_all_states(self) -> None:
        for s in TERMINAL_STATES:
            assert s in WorkflowState

    def test_expected_terminal_states(self) -> None:
        assert WorkflowState.DELIVERED in TERMINAL_STATES
        assert WorkflowState.ARCHIVED in TERMINAL_STATES
        assert WorkflowState.HELD in TERMINAL_STATES
        assert WorkflowState.DIGESTED in TERMINAL_STATES
        assert WorkflowState.REJECTED in TERMINAL_STATES
        assert WorkflowState.FAILED in TERMINAL_STATES
        assert WorkflowState.AWAITING_HITL in TERMINAL_STATES

    def test_non_terminal_states(self) -> None:
        assert WorkflowState.RECEIVED not in TERMINAL_STATES
        assert WorkflowState.INTERPRETED not in TERMINAL_STATES
        assert WorkflowState.ROUTED not in TERMINAL_STATES
        assert WorkflowState.PERSONALIZED not in TERMINAL_STATES
        assert WorkflowState.SCHEDULED not in TERMINAL_STATES


class TestApplyTransition:
    # ── RECEIVED transitions ──────────────────────────────────────────────

    def test_received_communicate_ripe_ready(self) -> None:
        assert (
            apply_transition(WorkflowState.RECEIVED, "signalscribe_communicate_ripe_ready")
            == WorkflowState.INTERPRETED
        )

    def test_received_archive(self) -> None:
        assert (
            apply_transition(WorkflowState.RECEIVED, "signalscribe_archive")
            == WorkflowState.ARCHIVED
        )

    def test_received_hold(self) -> None:
        assert apply_transition(WorkflowState.RECEIVED, "signalscribe_hold") == WorkflowState.HELD

    def test_received_hitl(self) -> None:
        assert (
            apply_transition(WorkflowState.RECEIVED, "signalscribe_hitl")
            == WorkflowState.AWAITING_HITL
        )

    def test_received_error(self) -> None:
        assert apply_transition(WorkflowState.RECEIVED, "error") == WorkflowState.FAILED

    # ── INTERPRETED transitions ───────────────────────────────────────────

    def test_interpreted_candidates_found(self) -> None:
        assert (
            apply_transition(WorkflowState.INTERPRETED, "bu_candidates_found")
            == WorkflowState.ROUTED
        )

    def test_interpreted_no_candidates(self) -> None:
        assert (
            apply_transition(WorkflowState.INTERPRETED, "no_candidate_bus")
            == WorkflowState.ARCHIVED
        )

    def test_interpreted_error(self) -> None:
        assert apply_transition(WorkflowState.INTERPRETED, "error") == WorkflowState.FAILED

    # ── ROUTED transitions ────────────────────────────────────────────────

    def test_routed_personalization_complete(self) -> None:
        assert (
            apply_transition(WorkflowState.ROUTED, "personalization_complete")
            == WorkflowState.PERSONALIZED
        )

    def test_routed_all_not_affected(self) -> None:
        assert apply_transition(WorkflowState.ROUTED, "all_not_affected") == WorkflowState.ARCHIVED

    def test_routed_buatlas_hitl(self) -> None:
        assert apply_transition(WorkflowState.ROUTED, "buatlas_hitl") == WorkflowState.AWAITING_HITL

    def test_routed_error(self) -> None:
        assert apply_transition(WorkflowState.ROUTED, "error") == WorkflowState.FAILED

    # ── PERSONALIZED transitions ──────────────────────────────────────────

    def test_personalized_hitl_triggered(self) -> None:
        assert (
            apply_transition(WorkflowState.PERSONALIZED, "hitl_triggered")
            == WorkflowState.AWAITING_HITL
        )

    def test_personalized_scheduling_complete(self) -> None:
        assert (
            apply_transition(WorkflowState.PERSONALIZED, "scheduling_complete")
            == WorkflowState.SCHEDULED
        )

    def test_personalized_all_not_worth(self) -> None:
        assert (
            apply_transition(WorkflowState.PERSONALIZED, "all_not_worth") == WorkflowState.ARCHIVED
        )

    def test_personalized_error(self) -> None:
        assert apply_transition(WorkflowState.PERSONALIZED, "error") == WorkflowState.FAILED

    # ── SCHEDULED transitions ─────────────────────────────────────────────

    def test_scheduled_delivered(self) -> None:
        assert apply_transition(WorkflowState.SCHEDULED, "delivered") == WorkflowState.DELIVERED

    def test_scheduled_all_digested(self) -> None:
        assert apply_transition(WorkflowState.SCHEDULED, "all_digested") == WorkflowState.DIGESTED

    def test_scheduled_all_held(self) -> None:
        assert apply_transition(WorkflowState.SCHEDULED, "all_held") == WorkflowState.HELD

    def test_scheduled_pushpilot_hitl(self) -> None:
        assert (
            apply_transition(WorkflowState.SCHEDULED, "pushpilot_hitl")
            == WorkflowState.AWAITING_HITL
        )

    def test_scheduled_error(self) -> None:
        assert apply_transition(WorkflowState.SCHEDULED, "error") == WorkflowState.FAILED

    # ── AWAITING_HITL transitions ─────────────────────────────────────────

    def test_awaiting_hitl_approved(self) -> None:
        assert (
            apply_transition(WorkflowState.AWAITING_HITL, "hitl_approved")
            == WorkflowState.PERSONALIZED
        )

    def test_awaiting_hitl_rejected(self) -> None:
        assert (
            apply_transition(WorkflowState.AWAITING_HITL, "hitl_rejected") == WorkflowState.REJECTED
        )


class TestIllegalTransitions:
    def test_from_delivered_is_terminal(self) -> None:
        with pytest.raises(IllegalTransitionError):
            apply_transition(WorkflowState.DELIVERED, "signalscribe_archive")

    def test_from_archived_is_terminal(self) -> None:
        with pytest.raises(IllegalTransitionError):
            apply_transition(WorkflowState.ARCHIVED, "bu_candidates_found")

    def test_from_failed_is_terminal(self) -> None:
        with pytest.raises(IllegalTransitionError):
            apply_transition(WorkflowState.FAILED, "signalscribe_communicate_ripe_ready")

    def test_unknown_event_raises(self) -> None:
        with pytest.raises(IllegalTransitionError):
            apply_transition(WorkflowState.RECEIVED, "not_a_real_event")

    def test_wrong_event_for_state_raises(self) -> None:
        with pytest.raises(IllegalTransitionError):
            # "bu_candidates_found" is valid from INTERPRETED, not RECEIVED
            apply_transition(WorkflowState.RECEIVED, "bu_candidates_found")

    def test_error_message_contains_state_and_event(self) -> None:
        with pytest.raises(IllegalTransitionError, match="DELIVERED"):
            apply_transition(WorkflowState.DELIVERED, "bad_event")


class TestValidTransitions:
    def test_received_has_five_valid_events(self) -> None:
        vt = valid_transitions(WorkflowState.RECEIVED)
        assert len(vt) == 5
        assert "signalscribe_communicate_ripe_ready" in vt
        assert "signalscribe_archive" in vt
        assert "signalscribe_hold" in vt
        assert "signalscribe_hitl" in vt
        assert "error" in vt

    def test_delivered_has_no_valid_transitions(self) -> None:
        vt = valid_transitions(WorkflowState.DELIVERED)
        assert vt == {}

    def test_archived_has_no_valid_transitions(self) -> None:
        vt = valid_transitions(WorkflowState.ARCHIVED)
        assert vt == {}

    def test_scheduled_has_five_valid_events(self) -> None:
        vt = valid_transitions(WorkflowState.SCHEDULED)
        assert len(vt) == 5
