"""PastEngagement schema — historical BU engagement context for BUAtlas."""

from __future__ import annotations

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class PastEngagement(BaseModel):
    """Minimal v1 engagement history for a BU, passed to BUAtlas as optional context.

    Sourced from the audit log or a future engagement-tracking service. Full shape
    is deferred until the feedback-loop skill is implemented (prompt 09).
    """

    model_config = ConfigDict(extra="forbid", frozen=False, str_strip_whitespace=True)

    bu_id: str = Field(pattern=r"^[a-z][a-z0-9_-]*$")
    last_notified_at: AwareDatetime | None = Field(
        default=None,
        description="UTC timestamp of the most recent notification sent to this BU.",
    )
    notification_count_last_30d: int = Field(
        default=0,
        ge=0,
        description="Count of notifications delivered to this BU in the last 30 days.",
    )
    last_feedback: str | None = Field(
        default=None,
        description="Most recent feedback signal from the BU head (e.g., 'not_relevant', "
        "'too_frequent'). Aggregate only — no PII.",
    )
