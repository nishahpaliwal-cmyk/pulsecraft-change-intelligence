"""Unit tests for the demo event bus."""

from __future__ import annotations

import asyncio

from pulsecraft.demo.event_bus import EventBus
from pulsecraft.demo.events import Event


def _make_event(run_id: str, event_type: str = "hook_fired") -> Event:
    return Event(run_id=run_id, event_type=event_type, payload={"test": True})


def _make_terminal(run_id: str) -> Event:
    return Event(run_id=run_id, event_type="terminal_state", payload={"state": "DELIVERED"})


class TestEventBus:
    def test_create_run_returns_unique_ids(self) -> None:
        bus = EventBus()
        id1 = bus.create_run()
        id2 = bus.create_run()
        assert id1 != id2
        assert id1.startswith("run_")

    def test_publish_and_subscribe_delivers_events_in_order(self) -> None:
        bus = EventBus()
        run_id = bus.create_run()

        events = [_make_event(run_id, f"step_{i}") for i in range(3)]
        terminal = _make_terminal(run_id)

        for ev in events:
            bus.publish(run_id, ev)
        bus.publish(run_id, terminal)

        received: list[Event] = []

        async def collect() -> None:
            async for ev in bus.subscribe(run_id):
                received.append(ev)

        asyncio.run(collect())

        assert len(received) == 4
        assert received[0].type == "step_0"
        assert received[3].type == "terminal_state"

    def test_subscribe_stops_at_terminal_state(self) -> None:
        bus = EventBus()
        run_id = bus.create_run()

        bus.publish(run_id, _make_event(run_id, "hook_fired"))
        bus.publish(run_id, _make_terminal(run_id))
        bus.publish(run_id, _make_event(run_id, "should_not_arrive"))

        received: list[Event] = []

        async def collect() -> None:
            async for ev in bus.subscribe(run_id):
                received.append(ev)

        asyncio.run(collect())
        assert len(received) == 2
        assert received[-1].is_terminal()

    def test_cleanup_removes_queue(self) -> None:
        bus = EventBus()
        run_id = bus.create_run()
        assert run_id in bus._queues
        bus.cleanup(run_id)
        assert run_id not in bus._queues

    def test_publish_to_unknown_run_does_nothing(self) -> None:
        bus = EventBus()
        bus.publish("nonexistent_run", _make_event("nonexistent_run"))

    def test_expire_stale_removes_old_runs(self) -> None:
        import time

        bus = EventBus()
        run_id = bus.create_run()
        bus._last_activity[run_id] = time.monotonic() - bus._EXPIRE_AFTER_S - 1
        bus.expire_stale()
        assert run_id not in bus._queues

    def test_is_terminal_event(self) -> None:
        run_id = "run_test"
        assert Event(run_id, "terminal_state", {}).is_terminal()
        assert not Event(run_id, "hook_fired", {}).is_terminal()
