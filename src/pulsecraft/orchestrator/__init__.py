"""PulseCraft orchestrator — deterministic workflow engine + supporting infrastructure."""

from pulsecraft.orchestrator.agent_protocol import (
    BUAtlasProtocol,
    PushPilotProtocol,
    SignalScribeProtocol,
)
from pulsecraft.orchestrator.audit import AuditWriter
from pulsecraft.orchestrator.engine import Orchestrator, RunResult
from pulsecraft.orchestrator.hitl import HITLQueue, HITLReason
from pulsecraft.orchestrator.mock_agents import MockBUAtlas, MockPushPilot, MockSignalScribe
from pulsecraft.orchestrator.states import (
    TERMINAL_STATES,
    IllegalTransitionError,
    WorkflowState,
    apply_transition,
    valid_transitions,
)

__all__ = [
    "BUAtlasProtocol",
    "PushPilotProtocol",
    "SignalScribeProtocol",
    "AuditWriter",
    "Orchestrator",
    "RunResult",
    "HITLQueue",
    "HITLReason",
    "MockBUAtlas",
    "MockPushPilot",
    "MockSignalScribe",
    "TERMINAL_STATES",
    "IllegalTransitionError",
    "WorkflowState",
    "apply_transition",
    "valid_transitions",
]
