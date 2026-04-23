"""Bridge between the orchestrator and the demo event bus.

Loads a fixture, wires up real agents, runs run_change() in a thread pool
executor so the FastAPI event loop stays responsive, and translates on_event
payloads into typed Event objects pushed to the bus.
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

import structlog

from pulsecraft.demo.event_bus import bus
from pulsecraft.demo.events import make_event

logger = structlog.get_logger(__name__)

# ── fixture registry ──────────────────────────────────────────────────────────

_FIXTURE_ROOT = Path(__file__).parent.parent.parent.parent / "fixtures" / "changes"

SCENARIOS: list[dict[str, Any]] = [
    {
        "id": "001",
        "fixture": "change_001_clearcut_communicate.json",
        "title": "A clearcut customer-visible change",
        "description": "Happy path to delivery with priority review",
    },
    {
        "id": "002",
        "fixture": "change_002_pure_internal_refactor.json",
        "title": "A pure internal refactor",
        "description": "System correctly refuses to send",
    },
    {
        "id": "006",
        "fixture": "change_006_multi_bu_affected_vs_adjacent.json",
        "title": "A change affecting multiple BUs",
        "description": "Parallel per-BU reasoning in action",
    },
    {
        "id": "007",
        "fixture": "change_007_mlr_sensitive.json",
        "title": "An MLR-sensitive educational update",
        "description": "Policy layer catches regulated content",
    },
    {
        "id": "008",
        "fixture": "change_008_post_hoc_already_shipped.json",
        "title": "A post-hoc already-shipped change",
        "description": "Retrospective notification, full delivery",
    },
]


def get_scenario(scenario_id: str) -> dict[str, Any] | None:
    return next((s for s in SCENARIOS if s["id"] == scenario_id), None)


def load_fixture(fixture_filename: str) -> dict[str, Any]:
    path = _FIXTURE_ROOT / fixture_filename
    return json.loads(path.read_text(encoding="utf-8"))


# ── run ───────────────────────────────────────────────────────────────────────

def _run_pipeline(run_id: str, fixture_data: dict[str, Any]) -> None:
    """Synchronous pipeline execution — called from thread pool executor."""
    from pulsecraft.agents.buatlas import BUAtlas
    from pulsecraft.agents.buatlas_fanout import buatlas_fanout_sync
    from pulsecraft.agents.pushpilot import PushPilot
    from pulsecraft.agents.signalscribe import SignalScribe
    from pulsecraft.orchestrator.audit import AuditWriter
    from pulsecraft.orchestrator.engine import Orchestrator
    from pulsecraft.orchestrator.hitl import HITLQueue
    from pulsecraft.schemas.change_artifact import ChangeArtifact

    artifact = ChangeArtifact.model_validate(fixture_data)
    start_time = time.monotonic()

    def on_event(raw: dict[str, Any]) -> None:
        elapsed = time.monotonic() - start_time
        raw_copy = dict(raw)
        # Inject elapsed time into terminal_state
        if raw_copy.get("type") == "terminal_state":
            raw_copy["elapsed_s"] = round(elapsed, 1)
        event = make_event(run_id, raw_copy)
        bus.publish(run_id, event)

    audit_writer = AuditWriter()
    orchestrator = Orchestrator(
        signalscribe=SignalScribe(),
        buatlas=BUAtlas(),
        pushpilot=PushPilot(),
        audit_writer=audit_writer,
        hitl_queue=HITLQueue(audit_writer=audit_writer),
        buatlas_fanout_fn=buatlas_fanout_sync,
    )

    try:
        orchestrator.run_change(artifact, on_event=on_event)
    except Exception as exc:
        logger.exception("instrumented_run_error", run_id=run_id)
        elapsed = time.monotonic() - start_time
        on_event({"type": "error", "stage": "pipeline", "message": str(exc)[:400], "recoverable": False})
        on_event({"type": "terminal_state", "state": "FAILED", "bu_outcomes": [], "total_cost_usd": 0.0, "elapsed_s": round(elapsed, 1)})


async def start_run(scenario_id: str) -> str:
    """Create a run_id, start the pipeline in background, return run_id immediately."""
    scenario = get_scenario(scenario_id)
    if scenario is None:
        raise ValueError(f"Unknown scenario_id: {scenario_id!r}")

    fixture_data = load_fixture(scenario["fixture"])
    run_id = bus.create_run()

    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, _run_pipeline, run_id, fixture_data)

    return run_id
