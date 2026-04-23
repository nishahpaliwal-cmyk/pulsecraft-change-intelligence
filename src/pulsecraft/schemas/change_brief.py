"""ChangeBrief schema — SignalScribe output (gates 1-3)."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from pulsecraft.schemas.change_artifact import SourceType
from pulsecraft.schemas.decision import Decision

UUIDStr = Annotated[
    str,
    Field(pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"),
]


class ChangeType(StrEnum):
    """Taxonomy of change types that SignalScribe classifies."""

    BUGFIX = "bugfix"
    BEHAVIOR_CHANGE = "behavior_change"
    NEW_FEATURE = "new_feature"
    DEPRECATION = "deprecation"
    ROLLBACK = "rollback"
    CONFIGURATION_CHANGE = "configuration_change"


class TimelineStatus(StrEnum):
    """Gate 2 timing verdict."""

    RIPE = "ripe"
    HELD_UNTIL = "held_until"
    HELD_INDEFINITE = "held_indefinite"
    ALREADY_SHIPPED = "already_shipped"


class ProducedBy(BaseModel):
    """Producer identity for a ChangeBrief."""

    model_config = ConfigDict(extra="forbid", frozen=False, str_strip_whitespace=True)

    agent: str = Field(default="signalscribe", pattern="^signalscribe$")
    version: str = Field(description="SignalScribe agent version.")


class Timeline(BaseModel):
    """Timing status and rollout schedule for the change."""

    model_config = ConfigDict(extra="forbid", frozen=False, str_strip_whitespace=True)

    status: TimelineStatus
    start_date: str | None = Field(default=None, description="ISO-8601 date (YYYY-MM-DD).")
    ramp: str | None = None
    reevaluate_at: str | None = Field(
        default=None, description="ISO-8601 date to re-evaluate ripeness."
    )
    reevaluate_trigger: str | None = Field(
        default=None, description="Human-readable event that triggers re-evaluation."
    )


class FAQEntry(BaseModel):
    """A question-answer pair anticipating stakeholder questions."""

    model_config = ConfigDict(extra="forbid", frozen=False, str_strip_whitespace=True)

    q: str
    a: str


class SourceCitation(BaseModel):
    """A source citation supporting a claim in the brief."""

    model_config = ConfigDict(extra="forbid", frozen=False, str_strip_whitespace=True)

    type: SourceType
    ref: str = Field(description="Opaque source-system reference identifier.")
    quote: str = Field(
        max_length=200,
        description="Short verbatim snippet from the source. Must not contain PII or secrets.",
    )


class ChangeBrief(BaseModel):
    """SignalScribe's structured interpretation of a ChangeArtifact.

    Carries gate 1-3 decisions in decisions[]. Consumed by the orchestrator which
    fans it out to BUAtlas (one invocation per candidate BU).
    """

    model_config = ConfigDict(extra="forbid", frozen=False, str_strip_whitespace=True)

    schema_version: str = Field(default="1.0")
    brief_id: UUIDStr = Field(description="UUID v4 for this ChangeBrief.")
    change_id: UUIDStr = Field(description="Matches the ChangeArtifact's change_id.")
    produced_at: AwareDatetime = Field(description="UTC timestamp of production.")
    produced_by: ProducedBy = Field(description="SignalScribe producer identity and version.")
    summary: str = Field(
        max_length=500, description="1-2 sentence plain-English summary of the change."
    )
    before: str = Field(description="Prior state. Use 'unknown' if genuinely unknown.")
    after: str = Field(description="New state after the change.")
    change_type: ChangeType
    impact_areas: list[str] = Field(
        description="Functional areas impacted. Freeform in v1; will align with BU registry taxonomy."
    )
    affected_segments: list[str] = Field(description="User or stakeholder segments affected.")
    timeline: Timeline
    required_actions: list[str] = Field(description="Actions required of BU stakeholders.")
    risks: list[str] = Field(description="Identified risks. Empty list if none.")
    mitigations: list[str] = Field(description="Known mitigations for identified risks.")
    faq: list[FAQEntry] = Field(description="Anticipated Q&A pairs.")
    sources: list[SourceCitation] = Field(description="Source citations for claims in this brief.")
    confidence_score: float = Field(
        ge=0.0, le=1.0, description="Aggregate confidence in the brief."
    )
    decisions: list[Decision] = Field(description="Gate 1-3 decisions in the order they were made.")
    open_questions: list[str] = Field(
        default_factory=list,
        description="Specific questions for HITL. Populated when gate 3 returns NEED_CLARIFICATION.",
    )
    escalation_reason: str | None = Field(
        default=None,
        description="Reason for escalation. Populated when any gate returns ESCALATE.",
    )
    usd_estimate: float | None = Field(
        default=None,
        exclude=True,
        description="LLM cost estimate in USD. Internal orchestration field; not from LLM output.",
    )
