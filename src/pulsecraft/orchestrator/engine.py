"""Orchestrator engine — deterministic workflow service.

run_change() drives a ChangeArtifact through the full pipeline:
  SignalScribe (gates 1-3) → BU pre-filter → BUAtlas per-BU (gates 4-5) →
  policy HITL checks → PushPilot (gate 6) → mock delivery.

No LLM calls here. Agents are injected via Protocols. Policy is enforced as
code invariants — agents reason within policy; orchestrator enforces policy.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from datetime import time as dt_time
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import structlog

from pulsecraft.config.loader import get_bu_profile, get_bu_registry, get_channel_policy, get_policy
from pulsecraft.hooks.base import HookContext, HookResult
from pulsecraft.hooks.config import HookRegistration, load_hook_registrations
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
from pulsecraft.schemas.bu_profile import BUProfile
from pulsecraft.schemas.change_artifact import ChangeArtifact
from pulsecraft.schemas.change_brief import ChangeBrief
from pulsecraft.schemas.decision import Decision, DecisionAgent, DecisionVerb
from pulsecraft.schemas.delivery_payloads import ScheduledDelivery
from pulsecraft.schemas.delivery_plan import Channel as DeliveryChannel
from pulsecraft.schemas.delivery_plan import DeliveryDecision
from pulsecraft.schemas.personalized_brief import (
    MessageQuality,
    PersonalizedBrief,
    Relevance,
)
from pulsecraft.schemas.policy import Policy
from pulsecraft.schemas.push_pilot_output import PushPilotOutput
from pulsecraft.skills.dedupe import compute_dedupe_key, has_recent_duplicate
from pulsecraft.skills.delivery.common import RenderingError
from pulsecraft.skills.policy import check_confidence_threshold, evaluate_hitl_triggers
from pulsecraft.skills.registry import lookup_bu_candidates

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

    When buatlas_fanout_fn is provided, the orchestrator uses it for parallel
    per-BU invocations instead of the sequential mock-compatible loop. The
    buatlas argument is still required (used for audit actor name/version).
    """

    def __init__(
        self,
        signalscribe: SignalScribeProtocol,
        buatlas: BUAtlasProtocol,
        pushpilot: PushPilotProtocol,
        audit_writer: AuditWriter,
        hitl_queue: HITLQueue,
        buatlas_fanout_fn: Callable | None = None,
    ) -> None:
        self._signalscribe = signalscribe
        self._buatlas = buatlas
        self._pushpilot = pushpilot
        self._audit = audit_writer
        self._hitl = hitl_queue
        self._buatlas_fanout_fn = buatlas_fanout_fn
        self._hooks: dict[str, HookRegistration] = load_hook_registrations()
        self._hook_modules: dict[str, object] = {}

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

    def _write_hook_fired(
        self,
        change_id: str,
        hook_name: str,
        outcome: str,
        reason: str,
    ) -> None:
        record = AuditRecord(
            audit_id=str(uuid.uuid4()),
            timestamp=_utcnow(),
            event_type=EventType.HOOK_FIRED,
            change_id=change_id,
            actor=Actor(type=ActorType.HOOK, id=hook_name, version=None),
            action=hook_name,
            input_hash=_sha256({"hook": hook_name}),
            output_summary=f"{outcome.upper()}: {reason}"[:500],
            outcome=AuditOutcome.SUCCESS if outcome == "pass" else AuditOutcome.FAILURE,
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
        dedupe_key: str | None = None,
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
            dedupe_key=dedupe_key,
        )
        self._audit.log_event(record)

    def _invoke_hook(self, hook_name: str, ctx: HookContext) -> HookResult:
        """Invoke a registered hook by name. Write HOOK_FIRED record. Return result."""
        import importlib

        reg = self._hooks.get(hook_name)
        if reg is None or not reg.enabled:
            return HookResult.skipped(f"hook {hook_name!r} not registered or disabled")

        try:
            if hook_name not in self._hook_modules:
                self._hook_modules[hook_name] = importlib.import_module(reg.module)
            mod = self._hook_modules[hook_name]
            fn = getattr(mod, reg.entrypoint)
            hook_result: HookResult = fn(ctx)  # type: ignore[assignment]
        except Exception as exc:
            err_reason = f"hook raised: {str(exc)[:200]}"
            logger.error("hook_invoke_error", hook_name=hook_name, error=str(exc)[:200])
            if ctx.change_id:
                self._write_hook_fired(ctx.change_id, hook_name, "fail", err_reason)
            if reg.fail == "closed":
                return HookResult.failed(err_reason)
            return HookResult.passed(reason=f"hook {hook_name!r} errored (fail=open)")

        if ctx.change_id:
            self._write_hook_fired(ctx.change_id, hook_name, hook_result.outcome, hook_result.reason)
        return hook_result

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

    # ── PushPilot policy enforcement ──────────────────────────────────────

    @staticmethod
    def _is_in_quiet_hours(
        bu_profile: BUProfile, now_utc: datetime
    ) -> tuple[bool, datetime | None]:
        """Check if now_utc falls within the BU's quiet hours.

        Returns (in_quiet, end_of_quiet_utc). end_of_quiet_utc is None when not in quiet hours.
        Uses IANA timezone from bu_profile.preferences.quiet_hours.
        """
        qh = bu_profile.preferences.quiet_hours
        try:
            tz = ZoneInfo(qh.timezone)
        except ZoneInfoNotFoundError:
            # Unknown timezone — skip quiet-hours check to avoid false positives
            logger.warning("quiet_hours_timezone_unknown", timezone=qh.timezone)
            return False, None

        now_local = now_utc.astimezone(tz)
        sh, sm = map(int, qh.start.split(":"))
        eh, em = map(int, qh.end.split(":"))
        start = dt_time(sh, sm)
        end = dt_time(eh, em)
        current = now_local.time().replace(second=0, microsecond=0)

        # Overnight window (start > end, e.g. 19:00 → 07:00)
        in_quiet = current >= start or current < end if start > end else start <= current < end

        if not in_quiet:
            return False, None

        # Compute end-of-quiet in UTC
        today = now_local.date()
        end_naive = datetime(today.year, today.month, today.day, eh, em)
        end_local = end_naive.replace(tzinfo=tz)
        if end_local <= now_local:
            end_local = (end_naive + timedelta(days=1)).replace(tzinfo=tz)
        return True, end_local.astimezone(UTC)

    @staticmethod
    def _select_channel(
        bu_profile: BUProfile, agent_channel: DeliveryChannel | None
    ) -> DeliveryChannel:
        """Return an approved channel for this BU.

        If the agent's preference is globally approved and in the BU's channel list, use it.
        Otherwise, return the first BU-approved channel that is globally approved.
        """
        try:
            channel_policy = get_channel_policy()
            global_approved = {c.lower() for c in channel_policy.approved_channels.global_channels}
        except Exception:
            global_approved = {"teams", "email"}

        bu_channels = [str(c).lower() for c in bu_profile.preferences.channels]

        if agent_channel is not None:
            agent_str = str(agent_channel).lower()
            if agent_str in global_approved and agent_str in bu_channels:
                return agent_channel

        # Fall back to first BU channel that is globally approved
        for ch_str in bu_channels:
            if ch_str in global_approved:
                try:
                    return DeliveryChannel(ch_str)
                except ValueError:
                    continue

        return DeliveryChannel.EMAIL

    def _enforce_pushpilot_policy(
        self,
        change_id: str,
        bu_id: str,
        output: PushPilotOutput,
        bu_profile: BUProfile,
        policy: Policy,
        correlation_ids: CorrelationIds | None = None,
    ) -> PushPilotOutput:
        """Apply code-level policy invariants after PushPilot returns.

        If agent says SEND_NOW but policy forbids it, downgrade to HOLD_UNTIL.
        Both the agent's original preference and the override are logged.
        The returned PushPilotOutput may differ from the input.
        """
        now_utc = datetime.now(UTC)
        agent_decision = output.decision
        final_output = output

        # ── Quiet hours check ──────────────────────────────────────────────
        if output.decision == DeliveryDecision.SEND_NOW:
            in_quiet, quiet_end = self._is_in_quiet_hours(bu_profile, now_utc)
            if in_quiet and quiet_end is not None:
                self._write_policy_check(
                    change_id,
                    "quiet_hours_override",
                    passed=False,
                    reason=f"bu={bu_id} agent=SEND_NOW overridden to HOLD_UNTIL(quiet_end={quiet_end.isoformat()})",
                    correlation_ids=correlation_ids,
                )
                logger.info(
                    "pushpilot_policy_override",
                    change_id=change_id,
                    bu_id=bu_id,
                    agent_decision=str(agent_decision),
                    override="hold_until",
                    reason="quiet_hours",
                    quiet_end=quiet_end.isoformat(),
                )
                # Build an override Decision that records both preferences
                gate_dec = Decision(
                    gate=6,
                    verb=DecisionVerb.HOLD_UNTIL,
                    reason=f"Policy override: agent preferred SEND_NOW but quiet hours active until {quiet_end.isoformat()}. Original reason: {output.reason[:200]}",
                    confidence=output.confidence_score,
                    decided_at=now_utc,
                    agent=DecisionAgent(name="pushpilot", version="1.0"),
                )
                final_output = PushPilotOutput(
                    decision=DeliveryDecision.HOLD_UNTIL,
                    channel=output.channel,
                    scheduled_time=quiet_end,
                    reason=f"[POLICY OVERRIDE: quiet_hours] Agent preferred SEND_NOW. {output.reason[:400]}",
                    confidence_score=output.confidence_score,
                    gate_decision=gate_dec,
                )

        # ── Channel approval check ─────────────────────────────────────────
        if final_output.decision != DeliveryDecision.ESCALATE:
            approved_channel = self._select_channel(bu_profile, final_output.channel)
            if approved_channel != final_output.channel:
                self._write_policy_check(
                    change_id,
                    "channel_approval",
                    passed=False,
                    reason=f"bu={bu_id} agent preferred channel={final_output.channel} not approved; using {approved_channel}",
                    correlation_ids=correlation_ids,
                )
                final_output = PushPilotOutput(
                    decision=final_output.decision,
                    channel=approved_channel,
                    scheduled_time=final_output.scheduled_time,
                    reason=final_output.reason,
                    confidence_score=final_output.confidence_score,
                    gate_decision=final_output.gate_decision,
                )
            else:
                self._write_policy_check(
                    change_id,
                    "channel_approval",
                    passed=True,
                    reason=f"bu={bu_id} channel={approved_channel} approved",
                    correlation_ids=correlation_ids,
                )

        # ── Confidence threshold check ─────────────────────────────────────
        threshold = policy.confidence_thresholds.pushpilot.gate_6_any
        if output.confidence_score < threshold:
            self._write_policy_check(
                change_id,
                "pushpilot_confidence_check",
                passed=False,
                reason=f"bu={bu_id} confidence {output.confidence_score:.2f} < {threshold:.2f}",
                correlation_ids=correlation_ids,
            )
        else:
            self._write_policy_check(
                change_id,
                "pushpilot_confidence_check",
                passed=True,
                reason=f"bu={bu_id} confidence {output.confidence_score:.2f} >= {threshold:.2f}",
                correlation_ids=correlation_ids,
            )

        return final_output

    # ── delivery execution ────────────────────────────────────────────────

    def _execute_delivery(
        self,
        change_id: str,
        bu_id: str,
        output: PushPilotOutput,
        pb: PersonalizedBrief,
        bu_profile: BUProfile,
    ) -> tuple[str, bool]:
        """Execute delivery for one BU via render → dedupe-check → send chain.

        Returns (decision_str, is_dedupe_conflict). Caller routes to HITL when
        is_dedupe_conflict is True.
        """
        channel = output.channel
        decision = output.decision
        channel_str = str(channel) if channel else "unspecified"
        decision_str = str(decision)
        correlation = CorrelationIds(personalized_brief_id=pb.personalized_brief_id)
        recipient_id = f"{bu_id}:head"

        # 1. Render payload by channel
        variant_text = f"{bu_id}:{channel_str}:{change_id}"
        payload_obj: object = None

        if decision != DeliveryDecision.ESCALATE:
            try:
                if channel == DeliveryChannel.TEAMS:
                    from pulsecraft.skills.delivery.render_teams_card import render_teams_card

                    teams_payload = render_teams_card(pb, bu_profile)
                    payload_obj = teams_payload
                    import json as _json

                    variant_text = _json.dumps(teams_payload.card_json, sort_keys=True)
                elif channel == DeliveryChannel.EMAIL:
                    from pulsecraft.skills.delivery.render_email import render_email

                    email_payload = render_email(pb, bu_profile)
                    payload_obj = email_payload
                    variant_text = email_payload.body_text
                elif channel == DeliveryChannel.PUSH:
                    from pulsecraft.skills.delivery.render_push import render_push

                    push_payload = render_push(pb, bu_profile)
                    payload_obj = push_payload
                    variant_text = f"{push_payload.title} {push_payload.body}"
            except RenderingError as exc:
                logger.warning(
                    "render_failed",
                    change_id=change_id,
                    bu_id=bu_id,
                    error=str(exc)[:200],
                )
                self._write_delivery(
                    change_id=change_id,
                    bu_id=bu_id,
                    decision=decision_str,
                    channel=channel_str,
                    reason=f"render_failed: {str(exc)[:200]}",
                    correlation_ids=correlation,
                )
                return decision_str, False

        # 2. Compute dedupe key from (change_id, bu_id, recipient_id, variant content)
        variant_id = _sha256(variant_text)
        dedupe_key = compute_dedupe_key(change_id, bu_id, recipient_id, variant_id)

        # 3. Dedupe check — only for SEND_NOW; DIGEST/HOLD_UNTIL are scheduled, not sent
        if decision == DeliveryDecision.SEND_NOW:
            try:
                window_hours = get_channel_policy().dedupe.window_hours
            except Exception:
                window_hours = 24
            if has_recent_duplicate(dedupe_key, self._audit, window_hours):
                logger.info(
                    "dedupe_conflict_detected",
                    change_id=change_id,
                    bu_id=bu_id,
                    dedupe_key=dedupe_key[:16],
                )
                return decision_str, True

        # 4. Write delivery_attempt audit record with dedupe_key populated
        self._write_delivery(
            change_id=change_id,
            bu_id=bu_id,
            decision=decision_str,
            channel=channel_str,
            reason=output.reason,
            correlation_ids=correlation,
            dedupe_key=dedupe_key,
        )

        if decision == DeliveryDecision.SEND_NOW:
            # 5. Send immediately via channel-specific adapter
            try:
                from pulsecraft.schemas.delivery_payloads import DeliveryResult

                delivery_result: DeliveryResult
                if channel == DeliveryChannel.TEAMS and payload_obj is not None:
                    from pulsecraft.skills.delivery.send_teams import send_teams

                    delivery_result = send_teams(payload_obj, recipient_id)  # type: ignore[arg-type]
                elif channel == DeliveryChannel.EMAIL and payload_obj is not None:
                    from pulsecraft.skills.delivery.send_email import send_email

                    delivery_result = send_email(payload_obj, recipient_id)  # type: ignore[arg-type]
                elif channel == DeliveryChannel.PUSH and payload_obj is not None:
                    from pulsecraft.skills.delivery.send_push import send_push

                    delivery_result = send_push(payload_obj, recipient_id)  # type: ignore[arg-type]
                else:
                    delivery_result = DeliveryResult(
                        delivery_id=str(uuid.uuid4()),
                        outcome="sent",
                        transport_ref="dev_mode_no_renderer",
                        sent_at=_utcnow(),
                    )
                logger.info(
                    "delivery_sent",
                    change_id=change_id,
                    bu_id=bu_id,
                    channel=channel_str,
                    outcome=delivery_result.outcome,
                )
            except Exception as exc:
                logger.warning(
                    "send_failed",
                    change_id=change_id,
                    bu_id=bu_id,
                    error=str(exc)[:200],
                )

        elif decision in (DeliveryDecision.HOLD_UNTIL, DeliveryDecision.DIGEST):
            # 6. Schedule for future delivery
            try:
                from pulsecraft.skills.delivery.schedule_send import schedule_send

                tz = bu_profile.preferences.quiet_hours.timezone
                scheduled = schedule_send(
                    decision=decision,
                    channel=channel,
                    scheduled_time=output.scheduled_time,
                    delivery_id=str(uuid.uuid4()),
                    recipient_timezone=tz,
                )
                self._persist_scheduled_delivery(change_id, bu_id, scheduled)
                logger.info(
                    "delivery_scheduled",
                    change_id=change_id,
                    bu_id=bu_id,
                    send_at=scheduled.send_at.isoformat(),
                    decision=decision_str,
                )
            except Exception as exc:
                logger.warning(
                    "schedule_failed",
                    change_id=change_id,
                    bu_id=bu_id,
                    error=str(exc)[:200],
                )

        return decision_str, False

    def _persist_scheduled_delivery(
        self,
        change_id: str,
        bu_id: str,
        scheduled: ScheduledDelivery,
    ) -> None:
        """Write a ScheduledDelivery to queue/scheduled/<YYYY-MM-DD>/<delivery_id>.json."""
        import json as _json

        try:
            scheduled_root = self._hitl._root.parent / "scheduled"
            date_dir = scheduled_root / scheduled.send_at.strftime("%Y-%m-%d")
            date_dir.mkdir(parents=True, exist_ok=True)
            file_path = date_dir / f"{scheduled.delivery_id}.json"
            file_path.write_text(
                _json.dumps(
                    {
                        "delivery_id": scheduled.delivery_id,
                        "change_id": change_id,
                        "bu_id": bu_id,
                        "send_at": scheduled.send_at.isoformat(),
                        "channel": scheduled.channel,
                        "reason": scheduled.reason,
                    },
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning(
                "persist_scheduled_delivery_failed",
                change_id=change_id,
                bu_id=bu_id,
                error=str(exc)[:200],
            )

    # ── main entry point ──────────────────────────────────────────────────

    def run_change(
        self,
        artifact: ChangeArtifact,
        on_event: Callable[[dict[str, Any]], None] | None = None,
    ) -> RunResult:
        """Drive a single ChangeArtifact through the full pipeline.

        Returns a RunResult summarizing the terminal state. Any unexpected exception
        transitions state to FAILED and writes an error audit record before re-raising.

        on_event: optional callback invoked at key pipeline points; used by the demo
        UI layer. Callers that omit it (all existing code and tests) are unaffected.
        """
        change_id = artifact.change_id
        state = WorkflowState.RECEIVED
        result = RunResult(change_id=change_id, terminal_state=state)

        try:
            return self._run(artifact, state, result, on_event=on_event)
        except Exception as exc:
            error_msg = str(exc)[:400]
            self._write_error(change_id, "UNEXPECTED_ERROR", error_msg)
            result.terminal_state = WorkflowState.FAILED
            result.errors.append(error_msg)
            result.audit_record_count = self._audit.record_count(change_id)
            logger.exception("orchestrator_unexpected_error", change_id=change_id)
            if on_event:
                on_event({"type": "error", "stage": "unexpected", "message": error_msg, "recoverable": False})
                on_event({"type": "terminal_state", "state": "FAILED", "bu_outcomes": [], "total_cost_usd": 0.0, "elapsed_s": 0.0})
            return result

    def _emit(self, on_event: Callable[[dict[str, Any]], None] | None, event_type: str, **payload: Any) -> None:
        """Fire an event to the optional observer. Never raises."""
        if on_event is None:
            return
        with contextlib.suppress(Exception):
            on_event({"type": event_type, **payload})

    def _run(
        self,
        artifact: ChangeArtifact,
        state: WorkflowState,
        result: RunResult,
        on_event: Callable[[dict[str, Any]], None] | None = None,
    ) -> RunResult:
        change_id = artifact.change_id
        policy = get_policy()

        # ── Step 1: RECEIVED ──────────────────────────────────────────────
        self._write_transition(change_id, None, WorkflowState.RECEIVED, "artifact accepted")
        self._emit(on_event, "run_started",
                   change_id=change_id,
                   title=artifact.title,
                   source_type=str(artifact.source_type),
                   source_ref=str(artifact.source_ref or ""),
                   raw_text=artifact.raw_text[:2000])

        # ── Step 2: SignalScribe ──────────────────────────────────────────
        _pi_ctx = HookContext(
            stage="pre_ingest", change_id=change_id, payload={"raw_text": artifact.raw_text}
        )
        _pi_result = self._invoke_hook("pre_ingest", _pi_ctx)
        self._emit(on_event, "hook_fired", stage="pre_ingest", name="pre_ingest",
                   outcome=_pi_result.outcome, reason=_pi_result.reason or "")
        if _pi_result.outcome == "fail":
            _pi_reg = self._hooks.get("pre_ingest")
            if _pi_reg and _pi_reg.fail == "closed":
                state = self._transition(
                    change_id, state, "error", f"pre_ingest blocked: {_pi_result.reason}"
                )
                result.terminal_state = state
                result.errors.append(_pi_result.reason)
                result.audit_record_count = self._audit.record_count(change_id)
                self._emit(on_event, "terminal_state", state=str(state), bu_outcomes=[], total_cost_usd=0.0, elapsed_s=0.0)
                return result
        elif _pi_result.outcome == "pass":
            _redacted = _pi_result.details.get("redacted_text")
            if isinstance(_redacted, str):
                artifact.raw_text = _redacted
        self._emit(on_event, "agent_started", agent="signalscribe", gate_batch=[1, 2, 3])
        change_brief = self._signalscribe.invoke(artifact)
        result.change_brief = change_brief
        for _d in change_brief.decisions:
            self._emit(on_event, "gate_decision", agent="signalscribe", gate=_d.gate,
                       verb=str(_d.verb), confidence=_d.confidence, reason=_d.reason)

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
            metrics=AuditMetrics(cost_usd=change_brief.usd_estimate)
            if change_brief.usd_estimate
            else None,
        )
        _pa_ss_ctx = HookContext(
            stage="post_agent",
            change_id=change_id,
            payload={
                "agent_name": self._signalscribe.agent_name,
                "decisions": change_brief.decisions,
                "message_text": "",
                "policy": policy,
            },
        )
        _pa_ss_result = self._invoke_hook("post_agent", _pa_ss_ctx)
        self._emit(on_event, "hook_fired", stage="post_agent", name="post_agent_signalscribe",
                   outcome=_pa_ss_result.outcome, reason=_pa_ss_result.reason or "")
        if _pa_ss_result.outcome == "fail":
            _pa_ss_reg = self._hooks.get("post_agent")
            if _pa_ss_reg and _pa_ss_reg.fail == "closed":
                state = self._transition(
                    change_id, state, "error", f"post_agent blocked: {_pa_ss_result.reason}"
                )
                result.terminal_state = state
                result.errors.append(_pa_ss_result.reason)
                result.audit_record_count = self._audit.record_count(change_id)
                self._emit(on_event, "terminal_state", state=str(state), bu_outcomes=[], total_cost_usd=0.0, elapsed_s=0.0)
                return result

        # State machine event from SignalScribe decisions — explicit agent decisions
        # (ESCALATE, NEED_CLARIFICATION, UNRESOLVABLE, HOLD_UNTIL, ARCHIVE) take
        # precedence over the confidence threshold check. Confidence is only checked
        # when the agent returns a positive COMMUNICATE+RIPE+READY path.
        event = self._signalscribe_event(change_brief)

        if event == "signalscribe_communicate_ripe_ready":
            # Only check confidence when agent fully committed to proceeding
            conf_ok = True
            conf_reason = "all thresholds met"
            for _d in change_brief.decisions:
                if not check_confidence_threshold(_d, policy):
                    conf_ok = False
                    conf_reason = f"gate_{_d.gate} confidence {_d.confidence:.2f} below threshold"
                    break
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
                self._emit(on_event, "hitl_triggered", reason=conf_reason, trigger_type="confidence_low")
                self._emit(on_event, "terminal_state", state=str(state), bu_outcomes=[], total_cost_usd=change_brief.usd_estimate or 0.0, elapsed_s=0.0)
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
                self._emit(on_event, "hitl_triggered", reason=str(hitl_reason), trigger_type=str(hitl_reason))
            result.terminal_state = state
            result.audit_record_count = self._audit.record_count(change_id)
            self._emit(on_event, "terminal_state", state=str(state), bu_outcomes=[], total_cost_usd=change_brief.usd_estimate or 0.0, elapsed_s=0.0)
            return result

        # ── Step 3: BU pre-filter → ROUTED ───────────────────────────────
        candidate_buses = lookup_bu_candidates(change_brief, get_bu_registry())
        if not candidate_buses:
            state = self._transition(change_id, state, "no_candidate_bus", "no BU registry matches")
            result.terminal_state = state
            result.audit_record_count = self._audit.record_count(change_id)
            self._emit(on_event, "terminal_state", state=str(state), bu_outcomes=[], total_cost_usd=change_brief.usd_estimate or 0.0, elapsed_s=0.0)
            return result

        state = self._transition(
            change_id,
            state,
            "bu_candidates_found",
            f"candidates: {candidate_buses}",
            CorrelationIds(brief_id=change_brief.brief_id),
        )

        # ── Step 4: BUAtlas fan-out → PERSONALIZED ───────────────────────
        personalized_briefs: dict[str, PersonalizedBrief] = {}
        buatlas_hitl_triggered = False

        # Emit started events for all candidate BUs so shimmer cards appear immediately
        for _bu_id_pre in candidate_buses:
            _bu_prof_pre = get_bu_profile(_bu_id_pre)
            self._emit(on_event, "buatlas_instance_started", bu_id=_bu_id_pre, bu_name=_bu_prof_pre.name)

        if self._buatlas_fanout_fn is not None:
            # Real parallel fan-out via buatlas_fanout_sync
            bu_profiles = [get_bu_profile(bu_id) for bu_id in candidate_buses]
            fanout_results = self._buatlas_fanout_fn(change_brief, bu_profiles)

            for bu_profile, fanout_item in zip(bu_profiles, fanout_results, strict=True):
                bu_id = bu_profile.bu_id
                from pulsecraft.agents.buatlas_fanout import FanoutFailure

                if isinstance(fanout_item, FanoutFailure):
                    # v1: drop failures with audit trail; do not kill the pipeline
                    self._write_error(
                        change_id,
                        f"BUATLAS_FANOUT_FAILURE_{fanout_item.error_type}",
                        f"bu={bu_id} {fanout_item.error_message}",
                    )
                    logger.warning(
                        "buatlas_fanout_failure_dropped",
                        change_id=change_id,
                        bu_id=bu_id,
                        error_type=fanout_item.error_type,
                        retriable=fanout_item.retriable,
                    )
                    self._emit(on_event, "buatlas_instance_completed", bu_id=bu_id, verdict="FAILED")
                    continue

                pb = fanout_item
                personalized_briefs[bu_id] = pb
                for _d in pb.decisions:
                    self._emit(on_event, "gate_decision", agent="buatlas", gate=_d.gate,
                               verb=str(_d.verb), confidence=_d.confidence, reason=_d.reason, bu_id=bu_id)
                self._emit(on_event, "buatlas_instance_completed", bu_id=bu_id,
                           verdict=str(pb.message_quality), relevance=str(pb.relevance))
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
                    output_summary=f"bu={bu_id} relevance={pb.relevance} quality={pb.message_quality}",
                    correlation_ids=CorrelationIds(
                        brief_id=change_brief.brief_id,
                        personalized_brief_id=pb.personalized_brief_id,
                    ),
                    metrics=AuditMetrics(cost_usd=pb.usd_estimate) if pb.usd_estimate else None,
                )
                _pa_ba_ctx = HookContext(
                    stage="post_agent",
                    change_id=change_id,
                    payload={
                        "agent_name": self._buatlas.agent_name,
                        "decisions": pb.decisions,
                        "message_text": "",
                        "policy": policy,
                    },
                )
                _pa_ba_result = self._invoke_hook("post_agent", _pa_ba_ctx)
                self._emit(on_event, "hook_fired", stage="post_agent", name=f"post_agent_buatlas_{bu_id}",
                           outcome=_pa_ba_result.outcome, reason=_pa_ba_result.reason or "")
                if _pa_ba_result.outcome == "fail":
                    _pa_ba_reg = self._hooks.get("post_agent")
                    if _pa_ba_reg and _pa_ba_reg.fail == "closed":
                        state = self._transition(
                            change_id,
                            state,
                            "error",
                            f"post_agent blocked for {bu_id}: {_pa_ba_result.reason}",
                        )
                        result.terminal_state = state
                        result.errors.append(_pa_ba_result.reason)
                        result.audit_record_count = self._audit.record_count(change_id)
                        self._emit(on_event, "terminal_state", state=str(state), bu_outcomes=[], total_cost_usd=0.0, elapsed_s=0.0)
                        return result
                for d in pb.decisions:
                    if d.verb == DecisionVerb.ESCALATE:
                        buatlas_hitl_triggered = True
        else:
            # Sequential mock-compatible path (default; used by all existing tests)
            for bu_id in candidate_buses:
                bu_profile = get_bu_profile(bu_id)
                pb = self._buatlas.invoke(change_brief, bu_profile)
                personalized_briefs[bu_id] = pb
                for _d in pb.decisions:
                    self._emit(on_event, "gate_decision", agent="buatlas", gate=_d.gate,
                               verb=str(_d.verb), confidence=_d.confidence, reason=_d.reason, bu_id=bu_id)
                self._emit(on_event, "buatlas_instance_completed", bu_id=bu_id,
                           verdict=str(pb.message_quality), relevance=str(pb.relevance))

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
                    metrics=AuditMetrics(cost_usd=pb.usd_estimate) if pb.usd_estimate else None,
                )
                _pa_ba_ctx = HookContext(
                    stage="post_agent",
                    change_id=change_id,
                    payload={
                        "agent_name": self._buatlas.agent_name,
                        "decisions": pb.decisions,
                        "message_text": "",
                        "policy": policy,
                    },
                )
                _pa_ba_result = self._invoke_hook("post_agent", _pa_ba_ctx)
                self._emit(on_event, "hook_fired", stage="post_agent", name=f"post_agent_buatlas_{bu_id}",
                           outcome=_pa_ba_result.outcome, reason=_pa_ba_result.reason or "")
                if _pa_ba_result.outcome == "fail":
                    _pa_ba_reg = self._hooks.get("post_agent")
                    if _pa_ba_reg and _pa_ba_reg.fail == "closed":
                        state = self._transition(
                            change_id,
                            state,
                            "error",
                            f"post_agent blocked for {bu_id}: {_pa_ba_result.reason}",
                        )
                        result.terminal_state = state
                        result.errors.append(_pa_ba_result.reason)
                        result.audit_record_count = self._audit.record_count(change_id)
                        self._emit(on_event, "terminal_state", state=str(state), bu_outcomes=[], total_cost_usd=0.0, elapsed_s=0.0)
                        return result
                for d in pb.decisions:
                    if d.verb == DecisionVerb.ESCALATE:
                        buatlas_hitl_triggered = True

        result.personalized_briefs = personalized_briefs

        # All BUs failed in fanout? Treat as no candidates found.
        if not personalized_briefs:
            state = self._transition(
                change_id, state, "no_candidate_bus", "all BUAtlas invocations failed"
            )
            result.terminal_state = state
            result.audit_record_count = self._audit.record_count(change_id)
            return result

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
            self._emit(on_event, "hitl_triggered", reason="BUAtlas ESCALATE", trigger_type="agent_escalate")
            self._emit(on_event, "terminal_state", state=str(state), bu_outcomes=[], total_cost_usd=0.0, elapsed_s=0.0)
            return result

        state = self._transition(
            change_id,
            state,
            "personalization_complete",
            f"{len(personalized_briefs)} BUs personalized",
        )

        # ── Step 5: HITL trigger evaluation ──────────────────────────────
        hitl_triggers = evaluate_hitl_triggers(personalized_briefs, policy)
        hitl_fired = len(hitl_triggers) > 0
        hitl_desc = hitl_triggers[0].description if hitl_triggers else "no HITL triggers fired"
        self._write_policy_check(change_id, "hitl_trigger_evaluation", not hitl_fired, hitl_desc)

        if hitl_fired:
            step5_reason = hitl_triggers[0].reason
            state = self._transition(change_id, state, "hitl_triggered", hitl_desc)
            self._hitl.enqueue(
                change_id, step5_reason, {"brief_id": change_brief.brief_id, "reason": hitl_desc}
            )
            result.hitl_queued = True
            result.hitl_reason = step5_reason
            result.terminal_state = state
            result.audit_record_count = self._audit.record_count(change_id)
            self._emit(on_event, "hitl_triggered", reason=hitl_desc, trigger_type=str(step5_reason))
            self._emit(on_event, "terminal_state", state=str(state), bu_outcomes=[], total_cost_usd=0.0, elapsed_s=0.0)
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
            self._emit(on_event, "terminal_state", state=str(state), bu_outcomes=[], total_cost_usd=0.0, elapsed_s=0.0)
            return result

        delivery_outputs: dict[str, PushPilotOutput] = {}
        pushpilot_hitl = False

        for bu_id, pb in worth_sending.items():
            bu_profile = get_bu_profile(bu_id)
            self._emit(on_event, "agent_started", agent="pushpilot", gate_batch=[6], bu_id=bu_id)
            raw_output = self._pushpilot.invoke(pb, bu_profile)
            correlation = CorrelationIds(
                brief_id=change_brief.brief_id,
                personalized_brief_id=pb.personalized_brief_id,
            )

            # Log agent's raw preference before policy enforcement
            pp_decision_audit = AuditDecision(
                gate=6,
                verb=str(raw_output.decision),
                reason=raw_output.reason[:200],
            )
            self._write_agent_invocation(
                change_id=change_id,
                agent_name=self._pushpilot.agent_name,
                agent_version=self._pushpilot.version,
                input_data={"change_id": change_id, "bu_id": bu_id},
                decisions=[pp_decision_audit],
                output_summary=f"bu={bu_id} decision={raw_output.decision} channel={raw_output.channel}",
                correlation_ids=correlation,
                metrics=AuditMetrics(cost_usd=raw_output.usd_estimate)
                if raw_output.usd_estimate
                else None,
            )
            _pa_pp_ctx = HookContext(
                stage="post_agent",
                change_id=change_id,
                payload={
                    "agent_name": self._pushpilot.agent_name,
                    "decisions": [raw_output.gate_decision],
                    "message_text": "",
                    "policy": policy,
                },
            )
            _pa_pp_result = self._invoke_hook("post_agent", _pa_pp_ctx)
            self._emit(on_event, "hook_fired", stage="post_agent", name=f"post_agent_pushpilot_{bu_id}",
                       outcome=_pa_pp_result.outcome, reason=_pa_pp_result.reason or "")
            if _pa_pp_result.outcome == "fail":
                _pa_pp_reg = self._hooks.get("post_agent")
                if _pa_pp_reg and _pa_pp_reg.fail == "closed":
                    state = self._transition(
                        change_id,
                        state,
                        "error",
                        f"post_agent blocked for {bu_id}: {_pa_pp_result.reason}",
                    )
                    result.terminal_state = state
                    result.errors.append(_pa_pp_result.reason)
                    result.audit_record_count = self._audit.record_count(change_id)
                    self._emit(on_event, "terminal_state", state=str(state), bu_outcomes=[], total_cost_usd=0.0, elapsed_s=0.0)
                    return result

            # Apply code-level policy invariants (quiet hours, channel approval, confidence)
            output = self._enforce_pushpilot_policy(
                change_id, bu_id, raw_output, bu_profile, policy, correlation
            )
            delivery_outputs[bu_id] = output

            _diverged = (raw_output.decision != output.decision or raw_output.channel != output.channel)
            self._emit(on_event, "pushpilot_decision",
                       bu_id=bu_id,
                       preference={"verb": str(raw_output.decision), "channel": str(raw_output.channel), "reason": raw_output.reason[:300]},
                       enforced={"verb": str(output.decision), "channel": str(output.channel), "reason": output.reason[:300]},
                       diverged=_diverged)

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
            self._emit(on_event, "hitl_triggered", reason="PushPilot ESCALATE", trigger_type="agent_escalate")
            self._emit(on_event, "terminal_state", state=str(state), bu_outcomes=[], total_cost_usd=0.0, elapsed_s=0.0)
            return result

        # ── Step 7: Execute deliveries ────────────────────────────────────
        dedupe_conflict_bu: str | None = None
        for bu_id, output in delivery_outputs.items():
            pb = worth_sending[bu_id]
            bu_profile = get_bu_profile(bu_id)
            try:
                _cp = get_channel_policy()
            except Exception:
                _cp = None
            _pd_ctx = HookContext(
                stage="pre_deliver",
                change_id=change_id,
                payload={
                    "channel": str(output.channel) if output.channel else "unspecified",
                    "bu_profile": bu_profile,
                    "channel_policy": _cp,
                },
            )
            _pd_result = self._invoke_hook("pre_deliver", _pd_ctx)
            self._emit(on_event, "hook_fired", stage="pre_deliver", name=f"pre_deliver_{bu_id}",
                       outcome=_pd_result.outcome, reason=_pd_result.reason or "")
            if _pd_result.outcome == "fail":
                _pd_reg = self._hooks.get("pre_deliver")
                if _pd_reg and _pd_reg.fail == "closed":
                    state = self._transition(
                        change_id,
                        state,
                        "error",
                        f"pre_deliver blocked for {bu_id}: {_pd_result.reason}",
                    )
                    result.terminal_state = state
                    result.errors.append(_pd_result.reason)
                    result.audit_record_count = self._audit.record_count(change_id)
                    self._emit(on_event, "terminal_state", state=str(state), bu_outcomes=[], total_cost_usd=0.0, elapsed_s=0.0)
                    return result
            _decision_str, is_dedupe_conflict = self._execute_delivery(
                change_id, bu_id, output, pb, bu_profile
            )
            if not is_dedupe_conflict:
                self._emit(on_event, "delivery_rendered",
                           bu_id=bu_id,
                           channel=str(output.channel) if output.channel else "unspecified",
                           variant=_decision_str)
            if is_dedupe_conflict:
                dedupe_conflict_bu = bu_id
                break

        if dedupe_conflict_bu is not None:
            state = self._transition(
                change_id,
                state,
                "dedupe_conflict",
                f"duplicate delivery detected for bu={dedupe_conflict_bu}",
            )
            self._hitl.enqueue(
                change_id,
                HITLReason.DEDUPE_OR_RATE_LIMIT_CONFLICT,
                {
                    "brief_id": change_brief.brief_id,
                    "reason": f"dedupe conflict for bu={dedupe_conflict_bu}",
                },
            )
            result.hitl_queued = True
            result.hitl_reason = HITLReason.DEDUPE_OR_RATE_LIMIT_CONFLICT
            result.terminal_state = state
            result.audit_record_count = self._audit.record_count(change_id)
            self._emit(on_event, "hitl_triggered", reason="dedupe conflict", trigger_type="dedupe_conflict", bu_id=dedupe_conflict_bu)
            self._emit(on_event, "terminal_state", state=str(state), bu_outcomes=[], total_cost_usd=0.0, elapsed_s=0.0)
            return result

        # ── Step 8: Determine terminal state from delivery decisions ──────
        decisions_made = [o.decision for o in delivery_outputs.values()]
        terminal_event = self._delivery_terminal_event(decisions_made)
        state = self._transition(
            change_id, state, terminal_event, f"delivery outcomes: {decisions_made}"
        )

        bu_outcomes = [
            {"bu_id": bid, "state": str(o.decision), "channel": str(o.channel) if o.channel else "unspecified", "reason": o.reason[:200]}
            for bid, o in delivery_outputs.items()
        ]
        result.terminal_state = state
        result.audit_record_count = self._audit.record_count(change_id)
        self._emit(on_event, "terminal_state", state=str(state), bu_outcomes=bu_outcomes, total_cost_usd=0.0, elapsed_s=0.0)
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
