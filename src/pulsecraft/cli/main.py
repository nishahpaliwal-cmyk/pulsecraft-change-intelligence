"""PulseCraft CLI — operator commands for running and inspecting changes."""

from __future__ import annotations

import os
from pathlib import Path


def _load_env() -> None:
    env_path = Path(__file__).parent.parent.parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


_load_env()

import typer  # noqa: E402

from pulsecraft.cli.commands import (  # noqa: E402
    answer,
    approve,
    audit,
    demo,
    digest,
    dryrun,
    edit,
    explain,
    ingest,
    metrics,
    pending,
    reject,
    replay,
    run_change,
)

app = typer.Typer(
    name="pulsecraft",
    help="PulseCraft — marketplace change → BU-ready notifications.",
    no_args_is_help=True,
)

# Register all commands
run_change.register(app)
demo.register(app)
ingest.register(app)
dryrun.register(app)
approve.register(app)
reject.register(app)
edit.register(app)
answer.register(app)
replay.register(app)
pending.register(app)
digest.register(app)
audit.register(app)
metrics.register(app)
explain.register(app)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
