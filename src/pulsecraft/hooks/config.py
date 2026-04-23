"""Hook configuration loader — reads .claude/settings.json."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


class ConfigError(Exception):
    pass


@dataclass
class HookRegistration:
    name: str
    module: str
    entrypoint: str
    fail: Literal["closed", "open"]
    enabled: bool


def load_hook_registrations(
    settings_path: Path = Path(".claude/settings.json"),
) -> dict[str, HookRegistration]:
    """Load hook registrations from settings file.

    Returns empty dict if file is missing (graceful degradation).
    Raises ConfigError if the file exists but is malformed.
    """
    if not settings_path.exists():
        return {}
    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ConfigError(f"Malformed {settings_path}: {e}") from e

    hooks_raw = data.get("hooks", {})
    if not isinstance(hooks_raw, dict):
        raise ConfigError(f"'hooks' in {settings_path} must be an object")

    registrations: dict[str, HookRegistration] = {}
    for name, cfg in hooks_raw.items():
        if not isinstance(cfg, dict):
            raise ConfigError(f"Hook '{name}' config must be an object, got {type(cfg).__name__}")
        if "module" not in cfg:
            raise ConfigError(f"Hook '{name}' missing required field 'module'")
        registrations[name] = HookRegistration(
            name=name,
            module=cfg["module"],
            entrypoint=cfg.get("entrypoint", "run"),
            fail=cfg.get("fail", "open"),
            enabled=cfg.get("enabled", True),
        )

    return registrations
