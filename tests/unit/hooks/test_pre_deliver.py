"""Unit tests for pre_deliver hook."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from pulsecraft.hooks.base import HookContext
from pulsecraft.hooks.pre_deliver import run
from pulsecraft.schemas.bu_profile import (
    BUHead,
    BUProfile,
    Channel,
    EscalationContact,
    Preferences,
    QuietHours,
)
from pulsecraft.schemas.channel_policy import (
    ApprovedChannels,
    ChannelPolicy,
    ChannelSelectionDefault,
    ChannelSelectionRule,
    DedupeConfig,
    DigestConfig,
)


def _make_bu_profile(
    quiet_start: str = "20:00",
    quiet_end: str = "08:00",
    tz: str = "UTC",
) -> BUProfile:
    return BUProfile(
        bu_id="bu_alpha",
        name="Alpha BU",
        head=BUHead(name="<head-alpha>", role="BU Head"),
        therapeutic_area=None,
        owned_product_areas=["area_a"],
        active_initiatives=[],
        escalation_contact=EscalationContact(name="<esc-alpha>", role="VP"),
        preferences=Preferences(
            channels=[Channel.TEAMS, Channel.EMAIL],
            quiet_hours=QuietHours(timezone=tz, start=quiet_start, end=quiet_end),
            digest_opt_in=False,
        ),
    )


def _make_channel_policy(global_channels: list[str] | None = None) -> ChannelPolicy:
    return ChannelPolicy(
        approved_channels=ApprovedChannels(**{"global": global_channels or ["teams", "email"]}),
        channel_selection_rules=[
            ChannelSelectionRule(when={"priority": "P0"}, channel="teams"),
        ],
        channel_selection_default=ChannelSelectionDefault(channel="email"),
        dedupe=DedupeConfig(window_hours=24, key_components=["change_id", "bu_id"]),
        digest=DigestConfig(
            cadence="daily",
            send_time_recipient_local="08:00",
            max_items_per_digest=10,
            priority_filter=["P2"],
        ),
    )


def _ctx(
    channel: str = "teams",
    bu_profile: BUProfile | None = None,
    channel_policy: ChannelPolicy | None = None,
    now_utc: datetime | None = None,
) -> HookContext:
    payload: dict = {
        "channel": channel,
        "bu_profile": bu_profile or _make_bu_profile(),
        "channel_policy": channel_policy or _make_channel_policy(),
    }
    if now_utc is not None:
        payload["now_utc"] = now_utc
    return HookContext(stage="pre_deliver", change_id="change-001", payload=payload)


def test_passes_approved_channel_outside_quiet():
    now = datetime(2024, 6, 15, 12, 0, tzinfo=UTC)  # noon UTC, outside 20:00-08:00
    result = run(_ctx(channel="teams", now_utc=now))
    assert result.outcome == "pass"


def test_fails_during_quiet_hours():
    now = datetime(2024, 6, 15, 21, 0, tzinfo=UTC)  # 9pm UTC, inside 20:00-08:00
    result = run(_ctx(channel="teams", now_utc=now))
    assert result.outcome == "fail"
    assert "quiet hours" in result.reason.lower() or any(
        "quiet" in f for f in result.details.get("failures", [])
    )
    assert result.details.get("downgrade") == "hold_until"


def test_fails_unapproved_channel():
    cp = _make_channel_policy(global_channels=["email"])
    now = datetime(2024, 6, 15, 12, 0, tzinfo=UTC)
    result = run(_ctx(channel="teams", channel_policy=cp, now_utc=now))
    assert result.outcome == "fail"
    assert any("not approved" in f for f in result.details.get("failures", []))
    assert result.details.get("downgrade") == "hitl"


def test_passes_no_bu_profile():
    ctx = HookContext(
        stage="pre_deliver",
        change_id="c1",
        payload={"channel": "teams", "bu_profile": None, "channel_policy": _make_channel_policy()},
    )
    result = run(ctx)
    assert result.outcome == "pass"


def test_passes_no_channel_policy():
    now = datetime(2024, 6, 15, 12, 0, tzinfo=UTC)
    ctx = HookContext(
        stage="pre_deliver",
        change_id="c1",
        payload={
            "channel": "teams",
            "bu_profile": _make_bu_profile(),
            "channel_policy": None,
            "now_utc": now,
        },
    )
    result = run(ctx)
    assert result.outcome == "pass"


def test_overnight_quiet_hours_before_midnight():
    # 22:00 UTC should be inside 20:00-08:00 window
    now = datetime(2024, 6, 15, 22, 0, tzinfo=UTC)
    result = run(_ctx(channel="teams", now_utc=now))
    assert result.outcome == "fail"


def test_overnight_quiet_hours_after_midnight():
    # 03:00 UTC should be inside 20:00-08:00 window
    now = datetime(2024, 6, 16, 3, 0, tzinfo=UTC)
    result = run(_ctx(channel="teams", now_utc=now))
    assert result.outcome == "fail"


def test_both_quiet_and_unapproved_returns_hold_until():
    # quiet hours takes priority for downgrade
    cp = _make_channel_policy(global_channels=["email"])
    now = datetime(2024, 6, 15, 21, 0, tzinfo=UTC)
    result = run(_ctx(channel="teams", channel_policy=cp, now_utc=now))
    assert result.outcome == "fail"
    assert result.details.get("downgrade") == "hold_until"
