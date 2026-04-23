"""PersonalizedBrief schema — BUAtlas per-BU output (gates 4-5)."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from pulsecraft.schemas.decision import Decision

UUIDStr = Annotated[
    str,
    Field(pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"),
]

BUIdStr = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_-]*$")]


class Relevance(StrEnum):
    """Gate 4 verdict on BU relevance."""

    AFFECTED = "affected"
    ADJACENT = "adjacent"
    NOT_AFFECTED = "not_affected"


class Priority(StrEnum):
    """Notification priority. None when relevance is not_affected."""

    P0 = "P0"
    P1 = "P1"
    P2 = "P2"


class MessageQuality(StrEnum):
    """Gate 5 self-assessment of the drafted message quality."""

    WORTH_SENDING = "worth_sending"
    WEAK = "weak"
    NOT_WORTH = "not_worth"


class ProducedBy(BaseModel):
    """Producer identity for a PersonalizedBrief."""

    model_config = ConfigDict(extra="forbid", frozen=False, str_strip_whitespace=True)

    agent: str = Field(default="buatlas", pattern="^buatlas$")
    version: str = Field(description="BUAtlas agent version.")
    invocation_id: UUIDStr = Field(
        description="UUID v4 disambiguating parallel per-BU invocations for the same change event."
    )


class RecommendedAction(BaseModel):
    """A concrete BU-specific action with an identified owner."""

    model_config = ConfigDict(extra="forbid", frozen=False, str_strip_whitespace=True)

    owner: str = Field(description="Role or name of who should take this action.")
    action: str = Field(description="Concrete action description.")
    by_when: str | None = Field(default=None, description="Optional deadline or timing hint.")


class MessageVariants(BaseModel):
    """Channel-specific message drafts produced by BUAtlas."""

    model_config = ConfigDict(extra="forbid", frozen=False, str_strip_whitespace=True)

    push_short: str | None = Field(
        default=None,
        max_length=240,
        description="Push notification text. Max 240 characters.",
    )
    teams_medium: str | None = Field(
        default=None,
        max_length=600,
        description="Teams message body. Max ~6 lines / 600 characters.",
    )
    email_long: str | None = Field(
        default=None,
        max_length=1200,
        description="Email body. Max ~200 words (approximately 1200 characters).",
    )


class PersonalizedBrief(BaseModel):
    """BUAtlas's per-BU interpretation and message draft.

    Produced in parallel — one instance per candidate BU per change event.
    Carries gate 4 (relevance) and gate 5 (message quality) decisions in decisions[].
    Consumed by the orchestrator which routes WORTH_SENDING briefs to PushPilot.
    """

    model_config = ConfigDict(extra="forbid", frozen=False, str_strip_whitespace=True)

    schema_version: str = Field(default="1.0")
    personalized_brief_id: UUIDStr = Field(description="UUID v4 for this PersonalizedBrief.")
    change_id: UUIDStr = Field(description="Traces back to the originating ChangeArtifact.")
    brief_id: UUIDStr = Field(description="Traces back to the ChangeBrief from SignalScribe.")
    bu_id: BUIdStr = Field(description="BU registry ID (e.g., 'immunology', 'oncology').")
    produced_at: AwareDatetime = Field(description="UTC timestamp of production.")
    produced_by: ProducedBy
    relevance: Relevance = Field(description="Gate 4 verdict.")
    priority: Priority | None = Field(
        description="Notification priority. None when relevance is not_affected."
    )
    why_relevant: str = Field(
        description="Concrete, BU-specific mechanism of impact. Populated when relevance is 'affected'; "
        "empty string otherwise.",
    )
    recommended_actions: list[RecommendedAction] = Field(
        description="BU-specific actions. Empty when relevance is not_affected or adjacent."
    )
    assumptions: list[str] = Field(
        description="Explicit assumptions made during relevance assessment or message drafting."
    )
    message_variants: MessageVariants | None = Field(
        default=None,
        description="Required when relevance is 'affected' AND message_quality is 'worth_sending' or 'weak'.",
    )
    message_quality: MessageQuality | None = Field(
        description="Gate 5 message quality self-assessment. None when relevance is not_affected."
    )
    confidence_score: float = Field(
        ge=0.0, le=1.0, description="Aggregate confidence across gates 4 and 5."
    )
    decisions: list[Decision] = Field(description="Gate 4 and 5 decisions in order.")
    regeneration_attempts: int = Field(
        default=0,
        ge=0,
        description="Times BUAtlas regenerated the message after a WEAK self-assessment.",
    )
    usd_estimate: float | None = Field(
        default=None,
        exclude=True,
        description="LLM cost estimate in USD. Internal orchestration field; not from LLM output.",
    )
