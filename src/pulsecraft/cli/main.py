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
from rich.console import Console  # noqa: E402
from rich.panel import Panel  # noqa: E402
from rich.table import Table  # noqa: E402
from rich.text import Text  # noqa: E402

app = typer.Typer(
    name="pulsecraft",
    help="PulseCraft — marketplace change → BU-ready notifications.",
    no_args_is_help=True,
)
console = Console()
err_console = Console(stderr=True)


@app.command("run-change")
def run_change(
    fixture_path: Path = typer.Argument(  # noqa: B008
        ...,
        help="Path to a ChangeArtifact JSON fixture file.",
        exists=True,
        dir_okay=False,
        readable=True,
    ),
    audit_dir: Path = typer.Option(  # noqa: B008
        Path("audit"),
        "--audit-dir",
        help="Directory for audit JSONL output.",
    ),
    queue_dir: Path = typer.Option(  # noqa: B008
        Path("queue/hitl"),
        "--queue-dir",
        help="Directory for HITL queue files.",
    ),
    real_signalscribe: bool = typer.Option(  # noqa: B008
        False,
        "--real-signalscribe",
        help="Use real SignalScribe (LLM) instead of mock. Requires ANTHROPIC_API_KEY.",
    ),
    real_buatlas: bool = typer.Option(  # noqa: B008
        False,
        "--real-buatlas",
        help="Use real BUAtlas (LLM) instead of mock. (Placeholder — implemented in prompt 06.)",
    ),
    real_pushpilot: bool = typer.Option(  # noqa: B008
        False,
        "--real-pushpilot",
        help="Use real PushPilot (LLM) instead of mock. (Placeholder — implemented in prompt 07.)",
    ),
) -> None:
    """Drive a ChangeArtifact through the pipeline.

    By default, uses mock agents (no LLM calls). Pass --real-signalscribe to
    use the real LLM-backed SignalScribe for gates 1, 2, 3.
    """
    import json

    from pulsecraft.orchestrator.audit import AuditWriter
    from pulsecraft.orchestrator.engine import Orchestrator
    from pulsecraft.orchestrator.hitl import HITLQueue
    from pulsecraft.orchestrator.mock_agents import MockBUAtlas, MockPushPilot, MockSignalScribe
    from pulsecraft.schemas.change_artifact import ChangeArtifact

    # Load fixture
    try:
        raw = json.loads(fixture_path.read_text(encoding="utf-8"))
        artifact = ChangeArtifact.model_validate(raw)
    except Exception as exc:
        err_console.print(f"[red]Failed to load fixture:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        Panel(
            f"[bold]change_id:[/bold] {artifact.change_id}\n"
            f"[bold]title:[/bold] {artifact.title}\n"
            f"[bold]source:[/bold] {artifact.source_type}",
            title="PulseCraft run-change",
            subtitle=str(fixture_path.name),
        )
    )

    # Build agents
    from pulsecraft.orchestrator.agent_protocol import (
        BUAtlasProtocol,
        PushPilotProtocol,
        SignalScribeProtocol,
    )

    signalscribe_agent: SignalScribeProtocol
    buatlas_agent: BUAtlasProtocol
    pushpilot_agent: PushPilotProtocol

    if real_signalscribe:
        from pulsecraft.agents.signalscribe import SignalScribe

        signalscribe_agent = SignalScribe()
        console.print("[cyan]SignalScribe:[/cyan] real (claude-sonnet-4-6)")
    else:
        signalscribe_agent = MockSignalScribe()

    buatlas_fanout_fn = None
    if real_buatlas:
        from pulsecraft.agents.buatlas import BUAtlas
        from pulsecraft.agents.buatlas_fanout import buatlas_fanout_sync

        buatlas_agent = BUAtlas()
        buatlas_fanout_fn = lambda briefs, bus: buatlas_fanout_sync(  # noqa: E731
            briefs, bus, factory=lambda: BUAtlas()
        )
        console.print("[cyan]BUAtlas:[/cyan] real (claude-sonnet-4-6, parallel fan-out)")
    else:
        buatlas_agent = MockBUAtlas()

    if real_pushpilot:
        from pulsecraft.agents.pushpilot import PushPilot

        pushpilot_agent = PushPilot()
        console.print("[cyan]PushPilot:[/cyan] real (claude-sonnet-4-6)")
    else:
        pushpilot_agent = MockPushPilot()

    # Wire up infrastructure
    audit_writer = AuditWriter(root=audit_dir)
    hitl_queue = HITLQueue(audit_writer=audit_writer, root=queue_dir)
    orchestrator = Orchestrator(
        signalscribe=signalscribe_agent,
        buatlas=buatlas_agent,
        pushpilot=pushpilot_agent,
        audit_writer=audit_writer,
        hitl_queue=hitl_queue,
        buatlas_fanout_fn=buatlas_fanout_fn,
    )

    # Run
    result = orchestrator.run_change(artifact)

    # Print audit chain as state transitions
    records = audit_writer.read_chain(artifact.change_id)
    table = Table(title="State transitions & events", show_lines=False)
    table.add_column("Time", style="dim", no_wrap=True)
    table.add_column("Event type", style="cyan")
    table.add_column("Actor", style="yellow")
    table.add_column("Decision", style="green")
    table.add_column("Summary")

    for r in records:
        decision_str = f"[{r.decision.verb}]" if r.decision else ""
        table.add_row(
            r.timestamp.strftime("%H:%M:%S.%f")[:-3],
            r.event_type,
            r.actor.id,
            decision_str,
            r.output_summary[:70],
        )
    console.print(table)

    # HITL notice
    if result.hitl_queued:
        console.print(
            Panel(
                f"[yellow]HITL triggered:[/yellow] {result.hitl_reason}\n"
                "Pending review in queue/hitl/pending/",
                title="Human-in-the-loop",
            )
        )

    # BU results
    if result.personalized_briefs:
        bu_table = Table(title="BU personalization results")
        bu_table.add_column("BU ID")
        bu_table.add_column("Relevance")
        bu_table.add_column("Quality")
        bu_table.add_column("Priority")
        for bu_id, pb in result.personalized_briefs.items():
            bu_table.add_row(
                bu_id,
                pb.relevance,
                str(pb.message_quality) if pb.message_quality else "-",
                str(pb.priority) if pb.priority else "-",
            )
        console.print(bu_table)

    # Terminal state
    state_color = {
        "DELIVERED": "green",
        "ARCHIVED": "dim",
        "HELD": "yellow",
        "DIGESTED": "blue",
        "AWAITING_HITL": "yellow",
        "REJECTED": "red",
        "FAILED": "red bold",
    }.get(str(result.terminal_state), "white")

    console.print(
        Panel(
            Text(str(result.terminal_state), style=state_color, justify="center"),
            title="Terminal state",
            subtitle=f"{result.audit_record_count} audit records written",
        )
    )

    if result.errors:
        for err in result.errors:
            err_console.print(f"[red]Error:[/red] {err}")

    exit_code = 1 if str(result.terminal_state) == "FAILED" else 0
    raise typer.Exit(code=exit_code)


@app.command("ingest")
def ingest(
    source_type: str = typer.Argument(  # noqa: B008
        ...,
        help=(
            "Source type: release_note, jira_work_item, ado_work_item, doc, feature_flag, incident"
        ),
    ),
    source_ref: str = typer.Argument(  # noqa: B008
        ...,
        help="Source reference identifier (e.g. RN-2026-042, JIRA-ALPHA-1234).",
    ),
    output_dir: Path = typer.Option(  # noqa: B008
        Path("fixtures/changes/generated"),
        "--output-dir",
        help="Directory to write the generated ChangeArtifact JSON file.",
    ),
    run: bool = typer.Option(  # noqa: B008
        False,
        "--run",
        help="After ingest, run the artifact through the pipeline with mock agents.",
    ),
    audit_dir: Path = typer.Option(  # noqa: B008
        Path("audit"),
        "--audit-dir",
        help="Directory for audit JSONL output (only used with --run).",
    ),
    queue_dir: Path = typer.Option(  # noqa: B008
        Path("queue/hitl"),
        "--queue-dir",
        help="Directory for HITL queue files (only used with --run).",
    ),
) -> None:
    """Ingest a source artifact and write a ChangeArtifact JSON file.

    Dispatches to the appropriate adapter based on SOURCE_TYPE, fetches the
    artifact from the dev-mode stub fixture, and writes the result to
    OUTPUT_DIR/<change_id>.json.

    Pass --run to also drive the artifact through the pipeline with mock agents.
    """
    from pulsecraft.skills.ingest import (
        IngestMalformed,
        IngestNotFound,
        IngestUnauthorized,
        fetch_doc,
        fetch_feature_flag,
        fetch_incident,
        fetch_release_note,
        fetch_work_item,
    )

    _DISPATCH = {
        "release_note": lambda ref: fetch_release_note(ref),
        "jira_work_item": lambda ref: fetch_work_item(ref, source_type="jira_work_item"),
        "ado_work_item": lambda ref: fetch_work_item(ref, source_type="ado_work_item"),
        "doc": lambda ref: fetch_doc(ref),
        "feature_flag": lambda ref: fetch_feature_flag(ref),
        "incident": lambda ref: fetch_incident(ref),
    }

    if source_type not in _DISPATCH:
        err_console.print(
            f"[red]Unknown source_type:[/red] {source_type!r}\n"
            f"Valid values: {', '.join(sorted(_DISPATCH))}"
        )
        raise typer.Exit(code=1)

    try:
        artifact = _DISPATCH[source_type](source_ref)
    except IngestNotFound as exc:
        err_console.print(f"[red]Not found:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    except IngestUnauthorized as exc:
        err_console.print(f"[red]Unauthorized:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    except IngestMalformed as exc:
        err_console.print(f"[red]Malformed payload:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    # Write artifact to output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{artifact.change_id}.json"
    output_path.write_text(artifact.model_dump_json(indent=2), encoding="utf-8")

    console.print(
        Panel(
            f"[bold]change_id:[/bold] {artifact.change_id}\n"
            f"[bold]source_type:[/bold] {artifact.source_type}\n"
            f"[bold]source_ref:[/bold] {artifact.source_ref}\n"
            f"[bold]title:[/bold] {artifact.title}\n"
            f"[bold]output:[/bold] {output_path}",
            title="PulseCraft ingest",
            subtitle=source_ref,
        )
    )

    if not run:
        return

    # --run: drive through pipeline with mock agents

    from pulsecraft.orchestrator.audit import AuditWriter
    from pulsecraft.orchestrator.engine import Orchestrator
    from pulsecraft.orchestrator.hitl import HITLQueue
    from pulsecraft.orchestrator.mock_agents import MockBUAtlas, MockPushPilot, MockSignalScribe

    audit_writer = AuditWriter(root=audit_dir)
    hitl_queue = HITLQueue(audit_writer=audit_writer, root=queue_dir)
    orchestrator = Orchestrator(
        signalscribe=MockSignalScribe(),
        buatlas=MockBUAtlas(),
        pushpilot=MockPushPilot(),
        audit_writer=audit_writer,
        hitl_queue=hitl_queue,
    )

    result = orchestrator.run_change(artifact)

    state_color = {
        "DELIVERED": "green",
        "ARCHIVED": "dim",
        "HELD": "yellow",
        "DIGESTED": "blue",
        "AWAITING_HITL": "yellow",
        "REJECTED": "red",
        "FAILED": "red bold",
    }.get(str(result.terminal_state), "white")

    console.print(
        Panel(
            Text(str(result.terminal_state), style=state_color, justify="center"),
            title="Pipeline result",
            subtitle=f"{result.audit_record_count} audit records written",
        )
    )

    if result.errors:
        for err in result.errors:
            err_console.print(f"[red]Error:[/red] {err}")

    exit_code = 1 if str(result.terminal_state) == "FAILED" else 0
    raise typer.Exit(code=exit_code)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
