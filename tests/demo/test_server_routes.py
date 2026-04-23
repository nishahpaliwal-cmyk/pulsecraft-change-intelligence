"""FastAPI route tests for the demo server."""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from pulsecraft.demo.events import Event
from pulsecraft.demo.server import app

client = TestClient(app)


class TestHealthRoute:
    def test_health_returns_200(self) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestIndexRoute:
    def test_index_returns_html(self) -> None:
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "PulseCraft" in resp.text


class TestScenariosRoute:
    def test_scenarios_returns_five_entries(self) -> None:
        resp = client.get("/api/scenarios")
        assert resp.status_code == 200
        data = resp.json()
        assert "scenarios" in data
        assert len(data["scenarios"]) == 5

    def test_scenario_fields_present(self) -> None:
        resp = client.get("/api/scenarios")
        for s in resp.json()["scenarios"]:
            assert "id" in s
            assert "title" in s
            assert "description" in s
            assert "fixture" in s


class TestCreateRunRoute:
    def test_invalid_scenario_returns_400(self) -> None:
        resp = client.post("/api/runs", json={"scenario_id": "999"})
        assert resp.status_code == 400

    def test_valid_scenario_returns_run_id(self) -> None:
        # Mock start_run to avoid spinning up real LLM agents
        async def _mock_start(scenario_id: str) -> str:
            from pulsecraft.demo.event_bus import bus
            from pulsecraft.demo.events import Event
            run_id = bus.create_run()
            # Immediately push a terminal event so subscribe() doesn't hang
            bus.publish(run_id, Event(run_id, "terminal_state", {"state": "ARCHIVED"}))
            return run_id

        with patch("pulsecraft.demo.server.start_run", new=_mock_start):
            resp = client.post("/api/runs", json={"scenario_id": "001"})
        assert resp.status_code == 200
        assert "run_id" in resp.json()
        assert resp.json()["run_id"].startswith("run_")


class TestSSERoute:
    def test_unknown_run_id_returns_404(self) -> None:
        resp = client.get("/api/runs/nonexistent_run/events")
        assert resp.status_code == 404

    def test_sse_stream_delivers_events(self) -> None:
        from pulsecraft.demo.event_bus import bus

        run_id = bus.create_run()
        bus.publish(run_id, Event(run_id, "run_started", {"title": "Test"}))
        bus.publish(run_id, Event(run_id, "terminal_state", {"state": "DELIVERED"}))

        resp = client.get(f"/api/runs/{run_id}/events")
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        # Collect a few lines
        lines = resp.text.strip().split("\n")
        data_lines = [ln for ln in lines if ln.startswith("data:")]
        assert len(data_lines) >= 2

        import json
        first = json.loads(data_lines[0][len("data: "):])
        assert first["type"] == "run_started"
        last = json.loads(data_lines[-1][len("data: "):])
        assert last["type"] == "terminal_state"
