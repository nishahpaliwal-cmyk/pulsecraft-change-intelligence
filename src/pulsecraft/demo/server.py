"""PulseCraft demo FastAPI server."""

from __future__ import annotations

from pathlib import Path

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from pulsecraft.demo.event_bus import bus
from pulsecraft.demo.events import serialize_to_sse
from pulsecraft.demo.instrumented_run import SCENARIOS, get_scenario, start_run

logger = structlog.get_logger(__name__)

_STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="PulseCraft Demo", docs_url=None, redoc_url=None)

app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


# ── routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def index() -> FileResponse:
    return FileResponse(str(_STATIC_DIR / "index.html"))


@app.get("/api/scenarios")
async def list_scenarios() -> dict:
    return {"scenarios": SCENARIOS}


class RunRequest(BaseModel):
    scenario_id: str


@app.post("/api/runs")
async def create_run(body: RunRequest) -> dict[str, str]:
    scenario = get_scenario(body.scenario_id)
    if scenario is None:
        raise HTTPException(status_code=400, detail=f"Unknown scenario_id: {body.scenario_id!r}")
    run_id = await start_run(body.scenario_id)
    logger.info("demo_run_started", run_id=run_id, scenario_id=body.scenario_id)
    return {"run_id": run_id}


@app.get("/api/runs/{run_id}/events")
async def stream_events(run_id: str) -> StreamingResponse:
    """SSE endpoint — streams events for a run until terminal_state."""
    if run_id not in bus._queues:
        raise HTTPException(status_code=404, detail=f"run_id not found: {run_id!r}")

    async def event_generator():
        try:
            async for event in bus.subscribe(run_id):
                yield serialize_to_sse(event)
        except Exception as exc:
            logger.exception("sse_stream_error", run_id=run_id)
            error_payload = f"data: {{\"type\": \"error\", \"payload\": {{\"message\": \"{str(exc)[:200]}\"}}}}\n\n"
            yield error_payload
        finally:
            bus.cleanup(run_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.get("/api/runs/{run_id}/explain")
async def explain_run(run_id: str) -> dict[str, str]:
    """Return the /explain output for a completed run.

    Note: run_id is not the same as change_id. This endpoint returns a hint
    for the frontend to use the most-recent audit record instead.
    We return a stub that the frontend displays — full explain requires the
    change_id which is included in the run_started event payload.
    """
    return {"text": "Use the change_id from the run_started event with `pulsecraft explain <change_id>` for the full audit trail."}
