"""BUAtlas fan-out — parallel per-BU personalization.

Takes a ChangeBrief + list of candidate BUProfiles, invokes BUAtlas in parallel
(asyncio.gather + asyncio.to_thread), and returns results in the same order as
the input. Each invocation is fully isolated — no shared state between BUs.

One BU's failure becomes a FanoutFailure object; it does not kill the others.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass

import structlog

from pulsecraft.orchestrator.agent_protocol import BUAtlasProtocol
from pulsecraft.schemas.bu_profile import BUProfile
from pulsecraft.schemas.change_brief import ChangeBrief
from pulsecraft.schemas.past_engagement import PastEngagement
from pulsecraft.schemas.personalized_brief import PersonalizedBrief

logger = structlog.get_logger(__name__)


@dataclass
class FanoutFailure:
    """Returned when a single BU's BUAtlas invocation fails.

    The orchestrator decides what to do with failures (v1: drop with audit trail).
    """

    bu_id: str
    error_type: str
    error_message: str
    retriable: bool


async def buatlas_fanout(
    change_brief: ChangeBrief,
    candidate_bus: list[BUProfile],
    factory: Callable[[], BUAtlasProtocol],
    past_engagement_lookup: Callable[[str], PastEngagement | None] | None = None,
    max_concurrent: int = 5,
) -> list[PersonalizedBrief | FanoutFailure]:
    """Invoke BUAtlas in parallel, one per candidate BU.

    Returns results in the same order as `candidate_bus`. Failures are returned
    as FanoutFailure objects — one BU failing does not kill the others.

    Args:
        change_brief: The ChangeBrief from SignalScribe (shared, read-only).
        candidate_bus: Ordered list of BUProfiles to evaluate.
        factory: Callable that creates a fresh BUAtlasProtocol instance per invocation.
            Using a factory ensures no shared state between parallel invocations.
        past_engagement_lookup: Optional callable mapping bu_id → PastEngagement.
        max_concurrent: Maximum parallel invocations (semaphore). Default 5.
    """
    if not candidate_bus:
        return []

    semaphore = asyncio.Semaphore(max_concurrent)

    async def invoke_one(bu_profile: BUProfile) -> PersonalizedBrief | FanoutFailure:
        async with semaphore:
            past_engagement = (
                past_engagement_lookup(bu_profile.bu_id)
                if past_engagement_lookup is not None
                else None
            )
            agent = factory()
            try:
                result = await asyncio.to_thread(
                    agent.invoke,
                    change_brief,
                    bu_profile,
                    past_engagement,
                )
                logger.debug(
                    "buatlas_fanout_invocation_done",
                    bu_id=bu_profile.bu_id,
                    relevance=str(result.relevance),
                )
                return result
            except Exception as exc:
                from pulsecraft.agents.buatlas import (
                    AgentOutputValidationError,
                )

                retriable = not isinstance(exc, AgentOutputValidationError)
                logger.warning(
                    "buatlas_fanout_invocation_failed",
                    bu_id=bu_profile.bu_id,
                    error_type=type(exc).__name__,
                    error=str(exc)[:200],
                )
                return FanoutFailure(
                    bu_id=bu_profile.bu_id,
                    error_type=type(exc).__name__,
                    error_message=str(exc)[:500],
                    retriable=retriable,
                )

    tasks = [invoke_one(bu) for bu in candidate_bus]
    results = await asyncio.gather(*tasks)
    return list(results)


def buatlas_fanout_sync(
    change_brief: ChangeBrief,
    candidate_bus: list[BUProfile],
    factory: Callable[[], BUAtlasProtocol],
    past_engagement_lookup: Callable[[str], PastEngagement | None] | None = None,
    max_concurrent: int = 5,
) -> list[PersonalizedBrief | FanoutFailure]:
    """Synchronous wrapper around buatlas_fanout for callers that don't manage an event loop.

    The orchestrator (which is synchronous) calls this wrapper. The async work
    runs in a fresh event loop created by asyncio.run().
    """
    return asyncio.run(
        buatlas_fanout(
            change_brief=change_brief,
            candidate_bus=candidate_bus,
            factory=factory,
            past_engagement_lookup=past_engagement_lookup,
            max_concurrent=max_concurrent,
        )
    )
