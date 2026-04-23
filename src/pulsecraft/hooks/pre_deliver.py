"""PreDeliver hook — enforce delivery policy invariants before any send."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from datetime import time as dt_time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pulsecraft.hooks.base import HookContext, HookResult


def run(ctx: HookContext) -> HookResult:
    """Final policy gates before a delivery attempt executes.

    Expects ctx.payload:
    - 'channel': str  (selected delivery channel)
    - 'bu_profile': BUProfile
    - 'now_utc': datetime  (current UTC time; defaults to utcnow if omitted)
    - 'channel_policy': ChannelPolicy

    Returns pass if all checks clear.
    Returns fail with details['downgrade'] = 'hold_until' | 'hitl' on policy violation.
    """
    channel = ctx.payload.get("channel")
    bu_profile = ctx.payload.get("bu_profile")
    now_utc = ctx.payload.get("now_utc") or datetime.now(UTC)
    channel_policy = ctx.payload.get("channel_policy")

    failures: list[str] = []
    downgrade: str | None = None

    # 1. Quiet hours check
    if bu_profile is not None:
        in_quiet, _ = _check_quiet_hours(bu_profile, now_utc)
        if in_quiet:
            failures.append("delivery during quiet hours")
            downgrade = "hold_until"

    # 2. Channel approval check
    if channel is not None and channel_policy is not None:
        global_approved = {c.lower() for c in channel_policy.approved_channels.global_channels}
        bu_id = bu_profile.bu_id if bu_profile else None

        # Check BU-specific restricted channels
        bu_restricted = channel_policy.approved_channels.restricted or {}
        channel_in_restricted = channel.lower() in bu_restricted
        bu_in_restricted_list = bu_id is not None and bu_id in bu_restricted.get(
            channel.lower(), []
        )

        channel_ok = channel.lower() in global_approved or (
            channel_in_restricted and bu_in_restricted_list
        )
        if not channel_ok:
            failures.append(f"channel '{channel}' not approved for this delivery")
            downgrade = downgrade or "hitl"

    if failures:
        return HookResult.failed(
            "pre_deliver policy check failed",
            failures=failures,
            downgrade=downgrade or "hitl",
        )

    return HookResult.passed(reason="pre_deliver checks passed")


def _check_quiet_hours(bu_profile: object, now_utc: datetime) -> tuple[bool, datetime | None]:
    """Check if now_utc falls within the BU's quiet hours.

    Returns (in_quiet, end_of_quiet_utc). end_of_quiet_utc is None when not in quiet.
    Mirrors Orchestrator._is_in_quiet_hours to avoid circular imports.
    """
    try:
        qh = bu_profile.preferences.quiet_hours  # type: ignore[attr-defined]
    except AttributeError:
        return False, None

    try:
        tz = ZoneInfo(qh.timezone)
    except ZoneInfoNotFoundError:
        return False, None

    now_local = now_utc.astimezone(tz)
    sh, sm = map(int, qh.start.split(":"))
    eh, em = map(int, qh.end.split(":"))
    start = dt_time(sh, sm)
    end = dt_time(eh, em)
    current = now_local.time().replace(second=0, microsecond=0)

    in_quiet = current >= start or current < end if start > end else start <= current < end

    if not in_quiet:
        return False, None

    today = now_local.date()
    end_naive = datetime(today.year, today.month, today.day, eh, em)
    end_local = end_naive.replace(tzinfo=tz)
    if end_local <= now_local:
        end_local = (end_naive + timedelta(days=1)).replace(tzinfo=tz)
    return True, end_local.astimezone(UTC)
