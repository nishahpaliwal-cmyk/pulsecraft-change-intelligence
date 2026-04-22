"""Agent Protocol interfaces — the narrow contracts between the orchestrator and agents.

The orchestrator depends on these Protocols, not on any agent implementation.
Real agents (prompts 05-07) and mock agents (mock_agents.py) both satisfy these
interfaces. Swapping implementations requires no orchestrator changes.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pulsecraft.schemas.bu_profile import BUProfile
from pulsecraft.schemas.change_artifact import ChangeArtifact
from pulsecraft.schemas.change_brief import ChangeBrief
from pulsecraft.schemas.past_engagement import PastEngagement
from pulsecraft.schemas.personalized_brief import PersonalizedBrief
from pulsecraft.schemas.push_pilot_output import PushPilotOutput


@runtime_checkable
class SignalScribeProtocol(Protocol):
    """Contract for SignalScribe — interprets a change artifact (gates 1, 2, 3)."""

    agent_name: str  # "signalscribe" for real agent, "signalscribe_mock" for mock
    version: str

    def invoke(self, artifact: ChangeArtifact) -> ChangeBrief:
        """Interpret a ChangeArtifact and return a ChangeBrief with gate 1-3 decisions."""
        ...


@runtime_checkable
class BUAtlasProtocol(Protocol):
    """Contract for BUAtlas — personalizes a change for one BU (gates 4, 5)."""

    agent_name: str  # "buatlas" for real agent, "buatlas_mock" for mock
    version: str

    def invoke(
        self,
        change_brief: ChangeBrief,
        bu_profile: BUProfile,
        past_engagement: PastEngagement | None = None,
    ) -> PersonalizedBrief:
        """Personalize a ChangeBrief for one BU.

        Returns a PersonalizedBrief with gate 4 and 5 decisions. When gate 4
        returns NOT_AFFECTED, gate 5 is skipped and message_quality is None.
        """
        ...


@runtime_checkable
class PushPilotProtocol(Protocol):
    """Contract for PushPilot — decides timing and format for one notification (gate 6)."""

    agent_name: str  # "pushpilot" for real agent, "pushpilot_mock" for mock
    version: str

    def invoke(
        self,
        personalized_brief: PersonalizedBrief,
        bu_profile: BUProfile,
    ) -> PushPilotOutput:
        """Decide gate 6 for one WORTH_SENDING notification.

        Returns a PushPilotOutput with the delivery decision and reason.
        The orchestrator enriches this into a full DeliveryPlan and enforces
        policy invariants — agent reasons within policy; code enforces policy.
        """
        ...
