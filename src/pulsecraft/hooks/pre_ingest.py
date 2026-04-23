"""PreIngest hook — redact raw_text before any agent sees it."""

from __future__ import annotations

from pulsecraft.hooks.base import HookContext, HookResult
from pulsecraft.skills.ingest.redaction import redact


def run(ctx: HookContext) -> HookResult:
    """Redact sensitive patterns in raw_text. Fail closed if raw_text is not a string.

    Expects ctx.payload['raw_text'] (str).
    Returns details['redacted_text'] with the scrubbed content.
    """
    raw = ctx.payload.get("raw_text")
    if not isinstance(raw, str):
        return HookResult.failed(
            "raw_text missing or not a string",
            raw_text_type=type(raw).__name__,
        )

    redacted = redact(raw)
    changed = redacted != raw

    return HookResult(
        outcome="pass",
        reason="redaction applied" if changed else "no sensitive markers found",
        details={"redacted_text": redacted},
        audit_payload={
            "chars_in": len(raw),
            "chars_out": len(redacted),
            "redaction_applied": changed,
        },
    )
