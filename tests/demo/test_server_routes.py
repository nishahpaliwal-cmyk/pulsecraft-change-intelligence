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


class TestAppJsSyntax:
    def test_app_js_has_no_unclosed_template_expressions(self) -> None:
        """Regression: escHtml( call in change-header__meta was missing closing )."""
        resp = client.get("/static/app.js")
        assert resp.status_code == 200
        # The broken form had one fewer closing paren than required
        assert "${escHtml((p.change_id || '').slice(0, 8)}…" not in resp.text
        assert "${escHtml((p.change_id || '').slice(0, 8))}…" in resp.text


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

    def test_scenario_002_emits_archived_terminal_state(self) -> None:
        """Regression: HITLQueue was constructed without audit_writer, crashing _run_pipeline."""
        import json

        async def _mock_start(scenario_id: str) -> str:
            from pulsecraft.demo.event_bus import bus
            from pulsecraft.demo.events import Event
            run_id = bus.create_run()
            bus.publish(run_id, Event(run_id, "run_started", {"title": "pure internal refactor"}))
            bus.publish(run_id, Event(run_id, "terminal_state", {"state": "ARCHIVED"}))
            return run_id

        with patch("pulsecraft.demo.server.start_run", new=_mock_start):
            resp = client.post("/api/runs", json={"scenario_id": "002"})
        assert resp.status_code == 200
        run_id = resp.json()["run_id"]

        sse_resp = client.get(f"/api/runs/{run_id}/events")
        assert sse_resp.status_code == 200
        data_lines = [ln for ln in sse_resp.text.strip().split("\n") if ln.startswith("data:")]
        last = json.loads(data_lines[-1][len("data: "):])
        assert last["type"] == "terminal_state"
        assert last["payload"]["state"] == "ARCHIVED"


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


class TestArchitectureTab:
    def test_architecture_js_served(self) -> None:
        """architecture.js must be reachable and export initArchitecture."""
        resp = client.get("/static/architecture.js")
        assert resp.status_code == 200
        assert "initArchitecture" in resp.text
        assert "ARCH" in resp.text

    def test_architecture_css_served(self) -> None:
        """architecture.css must be reachable and contain key selectors."""
        resp = client.get("/static/architecture.css")
        assert resp.status_code == 200
        assert ".arch-root" in resp.text
        assert ".arch-canvas" in resp.text

    def test_index_html_has_architecture_tab_button(self) -> None:
        """Architecture tab button must be present and enabled (not disabled)."""
        resp = client.get("/")
        assert resp.status_code == 200
        assert 'data-tab="architecture"' in resp.text
        # Must NOT carry the old disabled / coming-soon state
        assert 'Architecture — coming soon' not in resp.text

    def test_index_html_has_arch_tab_container(self) -> None:
        """Architecture tab wrapper div must exist in the page markup."""
        resp = client.get("/")
        assert 'id="arch-tab"' in resp.text
        assert 'id="arch-root"' in resp.text

    def test_app_js_imports_architecture_module(self) -> None:
        """app.js must import initArchitecture from architecture.js."""
        resp = client.get("/static/app.js")
        assert resp.status_code == 200
        assert "initArchitecture" in resp.text
        assert "architecture.js" in resp.text
