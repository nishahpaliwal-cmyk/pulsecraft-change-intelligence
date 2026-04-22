"""Orchestrator engine — deterministic workflow service.

run_change() drives a ChangeArtifact through the full pipeline:
  SignalScribe (gates 1-3) → BU pre-filter → BUAtlas per-BU (gates 4-5) →
  policy HITL checks → PushPilot (gate 6) → mock delivery.

No LLM calls here. Agents are injected via Protocols. Policy is enforced as
code invariants — agents reason within policy; orchestrator enforces policy.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

from pulsecraft.config.loader import get_bu_profile, get_bu_registry, get_policy
from pulsecraft.orchestrator.agent_protocol import (
    BUAtlasProtocol,
    PushPilotProtocol,
    SignalScribeProtocol,
)
from pulsecraft.orchestrator.audit import AuditWriter
from pulsecraft.orchestrator.hitl import HITLQueue, HITLReason
from pulsecraft.orchestrator.states import (
    TERMINAL_STATES,
    WorkflowState,
    apply_transition,
)
from pulsecraft.schemas.audit_record import (
    Actor,
    ActorType,
    AuditDecision,
    AuditError,
    AuditMetrics,
    AuditOutcome,
    AuditRecord,
    CorrelationIds,
    EventType,
)
from pulsecraft.schemas.change_artifact import ChangeArtifact
from pulsecraft.schemas.change_brief import ChangeBrief
from pulsecraft.schemas.decision import DecisionVerb
from pulsecraft.schemas.delivery_plan import DeliveryDecision
from pulsecraft.schemas.personalized_brief import (
    MessageQuality,
    PersonalizedBrief,
    Priority,
    Relevance,
)
from pulsecraft.schemas.policy import Policy
from pulsecraft.schemas.push_pilot_output import PushPilotOutput

logger = structlog.get_logger(__name__)

_ORCHESTRATOR_ACTOR = Actor(
    type=ActorType.ORCHESTRATOR,
    id="orchestrator",
    version="1.0",
)


@dataclass
class RunResult:
    """Summary of one change-event workflow run."""

    change_id: str
    terminal_state: WorkflowState
    change_brief: ChangeBrief | None = None
    personalized_briefs: dict[str, PersonalizedBrief] = field(default_factory=dict)
    delivery_outputs: dict[str, PushPilotOutput] = field(default_factory=dict)
    audit_record_count: int = 0
    hitl_queued: bool = False
    hitl_reason: HITLReason | None = None
    errors: list[str] = field(default_factory=list)


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


def _sha256(data: Any) -> str:
    serialized = json.dumps(data, default=str, sort_keys=True)
    return hashlib.sha256(serialized.encode()).hexdigest()


class Orchestrator:
    """Deterministic workflow service that sequences agent invocations.

    Inject agents and infrastructure; call run_change() per change event.
    """

    def __init__(
        self,
        signalscribe: SignalScribeProtocol,
        buatlas: BUAtlasProtocol,
        pushpilot: PushPilotProtocol,
        audit_writer: AuditWriter,
        hitl_queue: HITLQueue,
    ) -> None:
        self._signalscribe = signalscribe
        self._buatlas = buatlas
        self._pushpilot = pushpilot
        self._audit = audit_writer
        self._hitl = hitl_queue

    # ── audit helpers ─────────────────────────────────────────────────────

    def _write_transition(
        self,
        change_id: str,
        from_state: WorkflowState | None,
        to_state: WorkflowState,
        reason: str,
        correlation_ids: CorrelationIds | None = None,
    ) -> None:
        record = AuditRecord(
            audit_id=str(uuid.uuid4()),
            timestamp=_utcnow(),
            event_type=EventType.STATE_TRANSITION,
            change_id=change_id,
            correlation_ids=correlation_ids,
            actor=_ORCHESTRATOR_ACTOR,
            action="transition",
            input_hash=_sha256({"from": from_state, "to": to_state}),
            output_summary=f"{from_state} → {to_state}: {reason}"[:500],
            outcome=AuditOutcome.SUCCESS,
        )
        self._audit.log_event(record)

    def _write_agent_invocation(
        self,
        change_id: str,
        agent_name: str,
        agent_version: str,
        input_data: Any,
        decisions: list[AuditDecision],
        output_summary: str,
        correlation_ids: CorrelationIds | None = None,
        metrics: AuditMetrics | None = None,
    ) -> None:
        primary_decision = decisions[0] if decisions else None
        record = AuditRecord(
            audit_id=str(uuid.uuid4()),
            timestamp=_utcnow(),
            event_type=EventType.AGENT_INVOCATION,
            change_id=change_id,
            correlation_ids=correlation_ids,
            actor=Actor(type=ActorType.AGENT, id=agent_name, version=agent_version),
            action="invoked",
            input_hash=_sha256(input_data),
            output_summary=output_summary[:500],
            decision=primary_decision,
            metrics=metrics,
            outcome=AuditOutcome.SUCCESS,
        )
        self._audit.log_event(record)

    def _write_policy_check(
        self,
        change_id: str,
        check_name: str,
        passed: bool,
        reason: str,
        correlation_ids: CorrelationIds | None = None,
    ) -> None:
        record = AuditRecord(
            audit_id=str(uuid.uuid4()),
            timestamp=_utcnow(),
            event_type=EventType.POLICY_CHECK,
            change_id=change_id,
            correlation_ids=correlation_ids,
            actor=_ORCHESTRATOR_ACTOR,
            action=check_name,
            input_hash=_sha256({"check": check_name}),
            output_summary=f"{'PASSED' if passed else 'FAILED'}: {reason}"[:500],
            outcome=AuditOutcome.SUCCESS if passed else AuditOutcome.ESCALATED,
        )
        self._audit.log_event(record)

    def _write_error(self, change_id: str, code: str, message: str) -> None:
        record = AuditRecord(
            audit_id=str(uuid.uuid4()),
            timestamp=_utcnow(),
            event_type=EventType.ERROR,
            change_id=change_id,
            actor=_ORCHESTRATOR_ACTOR,
            action="error",
            input_hash=_sha256({"change_id": change_id}),
            output_summary=f"{code}: {message}"[:500],
            outcome=AuditOutcome.FAILURE,
            error=AuditError(code=code, message=message),
        )
        self._audit.log_event(record)

    def _write_delivery(
        self,
        change_id: str,
        bu_id: str,
        decision: str,
        channel: str | None,
        reason: str,
        correlation_ids: CorrelationIds | None = None,
    ) -> None:
        record = AuditRecord(
            audit_id=str(uuid.uuid4()),
            timestamp=_utcnow(),
            event_type=EventType.DELIVERY_ATTEMPT,
            change_id=change_id,
            correlation_ids=correlation_ids,
            actor=_ORCHESTRATOR_ACTOR,
            action="deliver",
            input_hash=_sha256({"bu_id": bu_id, "decision": decision}),
            output_summary=f"bu_id={bu_id} decision={decision} channel={channel}: {reason}"[:500],
            outcome=AuditOutcome.SUCCESS,
        )
        self._audit.log_event(record)

    # ── decision interpretation ───────────────────────────────────────────

    def _signalscribe_event(self, change_brief: ChangeBrief) -> str:
        """Map SignalScribe's gate decisions to a state-machine event string."""
        verbs_by_gate: dict[int, DecisionVerb] = {d.gate: d.verb for d in change_brief.decisions}
        gate1 = verbs_by_gate.get(1)
        gate2 = verbs_by_gate.get(2)
        gate3 = verbs_by_gate.get(3)

        if gate1 == DecisionVerb.ARCHIVE:
            return "signalscribe_archive"
        if gate1 == DecisionVerb.ESCALATE:
            return "signalscribe_hitl"
        if gate2 in (DecisionVerb.HOLD_UNTIL, DecisionVerb.HOLD_INDEFINITE):
            return "signalscribe_hold"
        if gate3 in (DecisionVerb.NEED_CLARIFICATION, DecisionVerb.UNRESOLVABLE):
            return "signalscribe_hitl"
        if gate3 == DecisionVerb.ESCALATE:
            return "signalscribe_hitl"
        if (
            gate1 == DecisionVerb.COMMUNICATE
            and gate2 == DecisionVerb.RIPE
            and gate3 == DecisionVerb.READY
        ):
            return "signalscribe_communicate_ripe_ready"
        # Unexpected combination — route to HITL
        return "signalscribe_hitl"

    def _hitl_reason_for_signalscribe(self, change_brief: ChangeBrief) -> HITLReason:
        """Pick the primary HITL reason for a SignalScribe-triggered escalation."""
        for d in change_brief.decisions:
            if d.verb == DecisionVerb.ESCALATE:
                return HITLReason.AGENT_ESCALATE
            if d.verb == DecisionVerb.NEED_CLARIFICATION:
                return HITLReason.NEED_CLARIFICATION
            if d.verb == DecisionVerb.UNRESOLVABLE:
                return HITLReason.UNRESOLVABLE
        return HITLReason.CONFIDENCE_BELOW_THRESHOLD

    # ── confidence threshold checks ───────────────────────────────────────

    def _check_signalscribe_confidence(
        self, change_brief: ChangeBrief, policy: Policy
    ) -> tuple[bool, str]:
        """Return (passed, reason). Fails if any gate confidence is below threshold."""
        thresholds = policy.confidence_thresholds.signalscribe
        for d in change_brief.decisions:
            if d.gate == 1:
                threshold = (
                    thresholds.gate_1_communicate
                    if d.verb == DecisionVerb.COMMUNICATE
                    else thresholds.gate_1_archive
                )
                if d.confidence < threshold:
                    return False, f"gate_1 confidence {d.confidence:.2f} < {threshold:.2f}"
            elif d.gate == 2 and d.confidence < thresholds.gate_2_ripe:
                return False, f"gate_2 confidence {d.confidence:.2f} < {thresholds.gate_2_ripe:.2f}"
            elif d.gate == 3 and d.confidence < thresholds.gate_3_ready:
                return (
                    False,
                    f"gate_3 confidence {d.confidence:.2f} < {thresholds.gate_3_ready:.2f}",
                )
        return True, "all thresholds met"

    def _check_buatlas_confidence(
        self, brief: PersonalizedBrief, policy: Policy
    ) -> tuple[bool, str]:
        thresholds = policy.confidence_thresholds.buatlas
        for d in brief.decisions:
            if d.gate == 4 and d.confidence < thresholds.gate_4_any:
                return False, f"gate_4 confidence {d.confidence:.2f} < {thresholds.gate_4_any:.2f}"
            elif d.gate == 5 and d.confidence < thresholds.gate_5_worth_sending:
                return (
                    False,
                    f"gate_5 confidence {d.confidence:.2f} < {thresholds.gate_5_worth_sending:.2f}",
                )
        return True, "all thresholds met"

    # ── restricted term checks ────────────────────────────────────────────

    def _collect_message_text(self, brief: PersonalizedBrief) -> str:
        """Concatenate all message variants for term scanning."""
        if brief.message_variants is None:
            return ""
        parts = [
            brief.message_variants.push_short or "",
            brief.message_variants.teams_medium or "",
            brief.message_variants.email_long or "",
        ]
        return " ".join(parts).lower()

    def _check_restricted_terms(
        self, brief: PersonalizedBrief, policy: Policy
    ) -> tuple[bool, HITLReason | None, str]:
        """Check message text against all restricted term categories.

        Returns (clean, hitl_reason_or_none, description).
        """
        text = self._collect_message_text(brief)
        if not text:
            return True, None, "no message text"

        for term in policy.restricted_terms.sensitive_data_markers:
            if term.lower() in text:
                return (
                    False,
                    HITLReason.RESTRICTED_TERM_DETECTED,
                    f"sensitive data marker: '{term}'",
                )

        for term in policy.restricted_terms.commitments_and_dates:
            if term.lower() in text:
                return False, HITLReason.DRAFT_HAS_COMMITMENT, f"commitment/date phrase: '{term}'"

        for term in policy.restricted_terms.scientific_communication:
            if term.lower() in text:
                return False, HITLReason.MLR_SENSITIVE, f"scientific communication term: '{term}'"

        return True, None, "no restricted terms detected"

    # ── HITL trigger evaluation ───────────────────────────────────────────

    def _evaluate_hitl_triggers(
        self,
        personalized_briefs: dict[str, PersonalizedBrief],
        policy: Policy,
        change_id: str,
    ) -> tuple[bool, HITLReason | None, str]:
        """Return (triggered, reason, description). Checks all HITL policy triggers."""
        active_triggers = set(policy.hitl_triggers)

        for bu_id, brief in personalized_briefs.items():
            if brief.relevance == Relevance.NOT_AFFECTED:
                continue

            # priority_p0
            if "priority_p0" in active_triggers and brief.priority == Priority.P0:
                return True, HITLReason.PRIORITY_P0, f"bu={bu_id} has priority P0"

            # second_weak_from_gate_5
            if (
                "second_weak_from_gate_5" in active_triggers
                and brief.message_quality == MessageQuality.WEAK
                and brief.regeneration_attempts >= 1
            ):
                return True, HITLReason.SECOND_WEAK_FROM_GATE_5, f"bu={bu_id} WEAK after regen"

            # confidence_below_threshold
            if "confidence_below_threshold" in active_triggers:
                conf_ok, conf_reason = self._check_buatlas_confidence(brief, policy)
                if not conf_ok:
                    return True, HITLReason.CONFIDENCE_BELOW_THRESHOLD, f"bu={bu_id} {conf_reason}"

            # buatlas escalate
            if "any_agent_escalate" in active_triggers:
                for d in brief.decisions:
                    if d.verb == DecisionVerb.ESCALATE:
                        return True, HITLReason.AGENT_ESCALATE, f"bu={bu_id} BUAtlas ESCALATE"

            # restricted term checks
            clean, reason, description = self._check_restricted_terms(brief, policy)
            if not clean:
                return True, reason, f"bu={bu_id} {description}"

        return False, None, "no HITL triggers fired"

    # ── BU pre-filter ─────────────────────────────────────────────────────

    def _find_candidate_bus(self, change_brief: ChangeBrief) -> list[str]:
        """Return BU IDs whose owned_product_areas overlap with change_brief.impact_areas."""
        impact_areas = set(change_brief.impact_areas)
        registry = get_bu_registry()
        candidates = []
        for entry in registry.bus:
            owned = set(entry.owned_product_areas)
            if owned & impact_areas:
                candidates.append(entry.bu_id)
        return candidates

    # ── delivery execution (mock) ─────────────────────────────────────────

    def _execute_delivery(
        self,
        change_id: str,
        bu_id: str,
        output: PushPilotOutput,
        brief_id: str,
    ) -> str:
        """Mock delivery: log what would happen. Returns the decision string."""
        channel_str = str(output.channel) if output.channel else "unspecified"
        decision_str = str(output.decision)
        correlation = CorrelationIds(personalized_brief_id=brief_id)

        if output.decision == DeliveryDecision.SEND_NOW:
            logger.info(
                "mock_delivery",
                change_id=change_id,
                bu_id=bu_id,
                channel=channel_str,
                decision=decision_str,
            )
        elif output.decision == DeliveryDecision.HOLD_UNTIL:
            logger.info(
                "mock_hold",
                change_id=change_id,
                bu_id=bu_id,
                until=str(output.scheduled_time),
            )
        elif output.decision == DeliveryDecision.DIGEST:
            logger.info("mock_digest", change_id=change_id, bu_id=bu_id)

        self._write_delivery(
            change_id=change_id,
            bu_id=bu_id,
            decision=decision_str,
            channel=channel_str,
            reason=output.reason,
            correlation_ids=correlation,
        )
        return decision_str

    # ── main entry point ──────────────────────────────────────────────────

    def run_change(self, artifact: ChangeArtifact) -> RunResult:
        """Drive a single ChangeArtifact through the full pipeline.

        Returns a RunResult summarizing the terminal state. Any unexpected exception
        transitions state to FAILED and writes an error audit record before re-raising.
        """
        change_id = artifact.change_id
        state = WorkflowState.RECEIVED
        result = RunResult(change_id=change_id, terminal_state=state)

        try:
            return self._run(artifact, state, result)
        except Exception as exc:
            error_msg = str(exc)[:400]
            self._write_error(change_id, "UNEXPECTED_ERROR", error_msg)
            result.terminal_state = WorkflowState.FAILED
            result.errors.append(error_msg)
            result.audit_record_count = self._audit.record_count(change_id)
            logger.exception("orchestrator_unexpected_error", change_id=change_id)
            return result

    def _run(
        self,
        artifact: ChangeArtifact,
        state: WorkflowState,
        result: RunResult,
    ) -> RunResult:
        change_id = artifact.change_id
        policy = get_policy()

        # ── Step 1: RECEIVED ──────────────────────────────────────────────
        self._write_transition(change_id, None, WorkflowState.RECEIVED, "artifact accepted")

        # ── Step 2: SignalScribe ──────────────────────────────────────────
        change_brief = self._signalscribe.invoke(artifact)
        result.change_brief = change_brief

        audit_decisions = [
            AuditDecision(gate=d.gate, verb=str(d.verb), reason=d.reason[:200])
            for d in change_brief.decisions
        ]
        self._write_agent_invocation(
            change_id=change_id,
            agent_name=self._signalscribe.agent_name,
            agent_version=self._signalscribe.version,
            input_data={"change_id": change_id, "source_type": str(artifact.source_type)},
            decisions=audit_decisions,
            output_summary=f"brief_id={change_brief.brief_id} decisions={[str(d.verb) for d in change_brief.decisions]}",
            correlation_ids=CorrelationIds(brief_id=change_brief.brief_id),
        )

        # State machine event from SignalScribe decisions — explicit agent decisions
        # (ESCALATE, NEED_CLARIFICATION, UNRESOLVABLE, HOLD_UNTIL, ARCHIVE) take
        # precedence over the confidence threshold check. Confidence is only checked
        # when the agent returns a positive COMMUNICATE+RIPE+READY path.
        event = self._signalscribe_event(change_brief)

        if event == "signalscribe_communicate_ripe_ready":
            # Only check confidence when agent fully committed to proceeding
            conf_ok, conf_reason = self._check_signalscribe_confidence(change_brief, policy)
            self._write_policy_check(
                change_id,
                "signalscribe_confidence_check",
                conf_ok,
                conf_reason,
                CorrelationIds(brief_id=change_brief.brief_id),
            )
            if not conf_ok and "confidence_below_threshold" in policy.hitl_triggers:
                state = self._transition(
                    change_id, state, "signalscribe_hitl", "confidence below threshold"
                )
                self._hitl.enqueue(
                    change_id, HITLReason.CONFIDENCE_BELOW_THRESHOLD, {"reason": conf_reason}
                )
                result.hitl_queued = True
                result.hitl_reason = HITLReason.CONFIDENCE_BELOW_THRESHOLD
                result.terminal_state = state
                result.audit_record_count = self._audit.record_count(change_id)
                return result

        state = self._transition(change_id, state, event, f"signalscribe event: {event}")

        if state in TERMINAL_STATES:
            if state == WorkflowState.AWAITING_HITL:
                hitl_reason = self._hitl_reason_for_signalscribe(change_brief)
                self._hitl.enqueue(
                    change_id,
                    hitl_reason,
                    {
                        "brief_id": change_brief.brief_id,
                        "open_questions": change_brief.open_questions,
                        "escalation_reason": change_brief.escalation_reason,
                    },
                )
                result.hitl_queued = True
                result.hitl_reason = hitl_reason
            result.terminal_state = state
            result.audit_record_count = self._audit.record_count(change_id)
            return result

        # ── Step 3: BU pre-filter → ROUTED ───────────────────────────────
        candidate_buses = self._find_candidate_bus(change_brief)
        if not candidate_buses:
            state = self._transition(change_id, state, "no_candidate_bus", "no BU registry matches")
            result.terminal_state = state
            result.audit_record_count = self._audit.record_count(change_id)
            return result

        state = self._transition(
            change_id,
            state,
            "bu_candidates_found",
            f"candidates: {candidate_buses}",
            CorrelationIds(brief_id=change_brief.brief_id),
        )

        # ── Step 4: BUAtlas fan-out → PERSONALIZED ───────────────────────
        # TODO(prompt-06): parallelize via asyncio.gather; sequential is correct for v1.
        personalized_briefs: dict[str, PersonalizedBrief] = {}
        buatlas_hitl_triggered = False

        for bu_id in candidate_buses:
            bu_profile = get_bu_profile(bu_id)
            pb = self._buatlas.invoke(change_brief, bu_profile)
            personalized_briefs[bu_id] = pb

            pb_decisions = [
                AuditDecision(gate=d.gate, verb=str(d.verb), reason=d.reason[:200])
                for d in pb.decisions
            ]
            self._write_agent_invocation(
                change_id=change_id,
                agent_name=self._buatlas.agent_name,
                agent_version=self._buatlas.version,
                input_data={"change_id": change_id, "bu_id": bu_id},
                decisions=pb_decisions,
                output_summary=(
                    f"bu={bu_id} relevance={pb.relevance} quality={pb.message_quality}"
                ),
                correlation_ids=CorrelationIds(
                    brief_id=change_brief.brief_id,
                    personalized_brief_id=pb.personalized_brief_id,
                ),
            )

            # Check for BUAtlas ESCALATE
            for d in pb.decisions:
                if d.verb == DecisionVerb.ESCALATE:
                    buatlas_hitl_triggered = True

        result.personalized_briefs = personalized_briefs

        # All NOT_AFFECTED?
        all_not_affected = all(
            pb.relevance == Relevance.NOT_AFFECTED for pb in personalized_briefs.values()
        )
        if all_not_affected:
            state = self._transition(
                change_id, state, "all_not_affected", "all BUs returned NOT_AFFECTED"
            )
            result.terminal_state = state
            result.audit_record_count = self._audit.record_count(change_id)
            return result

        if buatlas_hitl_triggered:
            state = self._transition(change_id, state, "buatlas_hitl", "BUAtlas returned ESCALATE")
            self._hitl.enqueue(
                change_id, HITLReason.AGENT_ESCALATE, {"brief_id": change_brief.brief_id}
            )
            result.hitl_queued = True
            result.hitl_reason = HITLReason.AGENT_ESCALATE
            result.terminal_state = state
            result.audit_record_count = self._audit.record_count(change_id)
            return result

        state = self._transition(
            change_id,
            state,
            "personalization_complete",
            f"{len(personalized_briefs)} BUs personalized",
        )

        # ── Step 5: HITL trigger evaluation ──────────────────────────────
        hitl_fired, step5_reason, hitl_desc = self._evaluate_hitl_triggers(
            personalized_briefs, policy, change_id
        )
        self._write_policy_check(change_id, "hitl_trigger_evaluation", not hitl_fired, hitl_desc)

        if hitl_fired:
            assert step5_reason is not None
            state = self._transition(change_id, state, "hitl_triggered", hitl_desc)
            self._hitl.enqueue(
                change_id, step5_reason, {"brief_id": change_brief.brief_id, "reason": hitl_desc}
            )
            result.hitl_queued = True
            result.hitl_reason = step5_reason
            result.terminal_state = state
            result.audit_record_count = self._audit.record_count(change_id)
            return result

        # ── Step 6: PushPilot scheduling ──────────────────────────────────
        worth_sending = {
            bu_id: pb
            for bu_id, pb in personalized_briefs.items()
            if pb.message_quality == MessageQuality.WORTH_SENDING
        }

        if not worth_sending:
            state = self._transition(change_id, state, "all_not_worth", "no WORTH_SENDING briefs")
            result.terminal_state = state
            result.audit_record_count = self._audit.record_count(change_id)
            return result

        delivery_outputs: dict[str, PushPilotOutput] = {}
        pushpilot_hitl = False

        for bu_id, pb in worth_sending.items():
            bu_profile = get_bu_profile(bu_id)
            output = self._pushpilot.invoke(pb, bu_profile)
            delivery_outputs[bu_id] = output

            pp_decision_audit = AuditDecision(
                gate=6,
                verb=str(output.decision),
                reason=output.reason[:200],
            )
            self._write_agent_invocation(
                change_id=change_id,
                agent_name=self._pushpilot.agent_name,
                agent_version=self._pushpilot.version,
                input_data={"change_id": change_id, "bu_id": bu_id},
                decisions=[pp_decision_audit],
                output_summary=f"bu={bu_id} decision={output.decision} channel={output.channel}",
                correlation_ids=CorrelationIds(
                    brief_id=change_brief.brief_id,
                    personalized_brief_id=pb.personalized_brief_id,
                ),
            )

            if output.decision == DeliveryDecision.ESCALATE:
                pushpilot_hitl = True

        result.delivery_outputs = delivery_outputs

        state = self._transition(
            change_id,
            state,
            "scheduling_complete",
            f"{len(delivery_outputs)} delivery decisions made",
        )

        if pushpilot_hitl:
            state = self._transition(change_id, state, "pushpilot_hitl", "PushPilot ESCALATE")
            self._hitl.enqueue(
                change_id, HITLReason.AGENT_ESCALATE, {"brief_id": change_brief.brief_id}
            )
            result.hitl_queued = True
            result.hitl_reason = HITLReason.AGENT_ESCALATE
            result.terminal_state = state
            result.audit_record_count = self._audit.record_count(change_id)
            return result

        # ── Step 7: Execute deliveries ────────────────────────────────────
        for bu_id, output in delivery_outputs.items():
            pb = worth_sending[bu_id]
            self._execute_delivery(change_id, bu_id, output, pb.personalized_brief_id)

        # ── Step 8: Determine terminal state from delivery decisions ──────
        decisions_made = [o.decision for o in delivery_outputs.values()]
        terminal_event = self._delivery_terminal_event(decisions_made)
        state = self._transition(
            change_id, state, terminal_event, f"delivery outcomes: {decisions_made}"
        )

        result.terminal_state = state
        result.audit_record_count = self._audit.record_count(change_id)
        return result

    def _delivery_terminal_event(self, decisions: list[DeliveryDecision]) -> str:
        """Map a list of delivery decisions to the terminal state-machine event."""
        if DeliveryDecision.SEND_NOW in decisions:
            return "delivered"
        if all(d == DeliveryDecision.DIGEST for d in decisions):
            return "all_digested"
        # Mixed HOLD_UNTIL / DIGEST with no SEND_NOW → treat as held
        return "all_held"

    def _transition(
        self,
        change_id: str,
        current: WorkflowState,
        event: str,
        reason: str,
        correlation_ids: CorrelationIds | None = None,
    ) -> WorkflowState:
        """Apply transition, write audit, return next state."""
        next_state = apply_transition(current, event)
        self._write_transition(change_id, current, next_state, reason, correlation_ids)
        logger.info(
            "state_transition",
            change_id=change_id,
            from_state=str(current),
            to_state=str(next_state),
            trigger=event,
        )
        return next_state
