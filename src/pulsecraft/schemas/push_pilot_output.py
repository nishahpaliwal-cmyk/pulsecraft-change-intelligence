"""PushPilotOutput schema — PushPilot agent's gate-6 decision (pre-enrichment)."""

from __future__ import annotations

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from pulsecraft.schemas.decision import Decision
from pulsecraft.schemas.delivery_plan import Channel, DeliveryDecision


class PushPilotOutput(BaseModel):
    """Gate-6 decision from PushPilot.

    The agent returns this lighter contract. The orchestrator enriches it into
    a full DeliveryPlan by adding recipient details, dedupe keys, and retry
    policies before persisting or executing.
    """

    model_config = ConfigDict(extra="forbid", frozen=False, str_strip_whitespace=True)

    decision: DeliveryDecision = Field(description="Gate 6 delivery decision verb.")
    channel: Channel | None = Field(
        default=None,
        description="Preferred delivery channel. None when decision is escalate.",
    )
    scheduled_time: AwareDatetime | None = Field(
        default=None,
        description="UTC delivery time for hold_until decisions. None otherwise.",
    )
    reason: str = Field(
        description="Required explanation naming the specific signals that drove the decision. "
        "Must not contain PII or internal secrets.",
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="PushPilot's confidence in the gate 6 decision.",
    )
    gate_decision: Decision = Field(
        description="Gate 6 Decision object for audit / decision trail."
    )
    usd_estimate: float | None = Field(
        default=None,
        exclude=True,
        description="LLM cost estimate in USD. Internal orchestration field; not from LLM output.",
    )
