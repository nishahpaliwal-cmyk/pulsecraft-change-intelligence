"""In-memory event bus keyed by run_id.

Uses threading.Queue for thread-safe sync publish (orchestrator runs in a
thread pool executor) and async polling for subscribe (FastAPI SSE endpoint).
"""

from __future__ import annotations

import asyncio
import queue
import time
import uuid
from collections.abc import AsyncIterator

from pulsecraft.demo.events import Event


class EventBus:
    """Per-run event queues with async subscribe and thread-safe publish."""

    _POLL_INTERVAL_S = 0.08   # 80ms polling — responsive without hammering
    _EXPIRE_AFTER_S = 600     # 10-minute inactivity expiry

    def __init__(self) -> None:
        self._queues: dict[str, queue.Queue[Event]] = {}
        self._last_activity: dict[str, float] = {}

    def create_run(self) -> str:
        """Create a new run queue and return its run_id."""
        run_id = f"run_{uuid.uuid4().hex[:16]}"
        self._queues[run_id] = queue.Queue()
        self._last_activity[run_id] = time.monotonic()
        return run_id

    def publish(self, run_id: str, event: Event) -> None:
        """Thread-safe publish — safe to call from a thread pool executor."""
        q = self._queues.get(run_id)
        if q is not None:
            q.put_nowait(event)
            self._last_activity[run_id] = time.monotonic()

    async def subscribe(self, run_id: str) -> AsyncIterator[Event]:
        """Async generator that yields events until a terminal_state event arrives."""
        q = self._queues.get(run_id)
        if q is None:
            return
        while True:
            try:
                event = q.get_nowait()
            except queue.Empty:
                await asyncio.sleep(self._POLL_INTERVAL_S)
                continue
            yield event
            if event.is_terminal():
                break

    def cleanup(self, run_id: str) -> None:
        """Remove a run's queue from memory."""
        self._queues.pop(run_id, None)
        self._last_activity.pop(run_id, None)

    def expire_stale(self) -> None:
        """Remove runs idle longer than _EXPIRE_AFTER_S. Call periodically."""
        cutoff = time.monotonic() - self._EXPIRE_AFTER_S
        stale = [rid for rid, t in self._last_activity.items() if t < cutoff]
        for rid in stale:
            self.cleanup(rid)


# Global singleton shared by server and instrumented_run.
bus = EventBus()
