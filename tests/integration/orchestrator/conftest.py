"""Shared fixtures for orchestrator integration tests."""

from pathlib import Path

import pytest

from pulsecraft.config.loader import reload_config

CONFIG_DIR = Path(__file__).parent.parent.parent.parent / "config"
FIXTURES_DIR = Path(__file__).parent.parent.parent.parent / "fixtures" / "changes"


@pytest.fixture(autouse=True)
def config_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PULSECRAFT_CONFIG_DIR", str(CONFIG_DIR))
    reload_config()
    yield
    reload_config()
