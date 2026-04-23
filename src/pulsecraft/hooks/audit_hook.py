"""Audit hook — write an audit record for any hook invocation. Fail-open.

This module provides a standalone run() callable for external invocations.
Inside the orchestrator, _invoke_hook calls _write_hook_fired directly
(bypassing this module) to avoid recursion.
"""

from __future__ import annotations

import structlog

from pulsecraft.hooks.base import HookContext, HookResult

logger = structlog.get_logger(__name__)


def run(ctx: HookContext) -> HookResult:
    """Write an audit record capturing a hook invocation result.

    Fail-open: if the audit write fails, logs the error and returns pass anyway.
    Never blocks the pipeline.

    Expects ctx.payload:
    - 'audit_writer': AuditWriter instance
    - 'hook_name': str
    - 'hook_outcome': Literal["pass", "fail", "skip"]
    - 'hook_reason': str
    - 'change_id': str
    """
    audit_writer = ctx.payload.get("audit_writer")
    hook_name = ctx.payload.get("hook_name", "unknown")
    hook_outcome = ctx.payload.get("hook_outcome", "unknown")
    hook_reason = ctx.payload.get("hook_reason", "")
    change_id = ctx.change_id or ctx.payload.get("change_id")

    if audit_writer is None or change_id is None:
        return HookResult.passed(reason="no audit_writer or change_id; skipped audit write")

    try:
        import hashlib
        import json
        import uuid
        from datetime import UTC, datetime

        from pulsecraft.schemas.audit_record import (
            Actor,
            ActorType,
            AuditOutcome,
            AuditRecord,
            EventType,
        )

        outcome = AuditOutcome.SUCCESS if hook_outcome == "pass" else AuditOutcome.FAILURE
        record = AuditRecord(
            audit_id=str(uuid.uuid4()),
            timestamp=datetime.now(UTC),
            event_type=EventType.HOOK_FIRED,
            change_id=change_id,
            actor=Actor(type=ActorType.HOOK, id=hook_name, version=None),
            action=hook_name,
            input_hash=hashlib.sha256(
                json.dumps({"hook": hook_name}, sort_keys=True).encode()
            ).hexdigest(),
            output_summary=f"{hook_outcome.upper()}: {hook_reason}"[:500],
            outcome=outcome,
        )
        audit_writer.log_event(record)
    except Exception as exc:
        logger.error("audit_hook_write_failed", hook_name=hook_name, error=str(exc)[:200])

    return HookResult.passed(reason="audit record written")
