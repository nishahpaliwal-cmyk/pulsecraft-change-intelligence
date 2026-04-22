"""PulseCraft CLI — operator commands for running and inspecting changes."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

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
) -> None:
    """Drive a ChangeArtifact through the pipeline with mock agents.

    Prints each state transition and the final terminal state.
    Uses mock agents that return scripted defaults — no LLM calls.
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

    # Wire up infrastructure
    audit_writer = AuditWriter(root=audit_dir)
    hitl_queue = HITLQueue(audit_writer=audit_writer, root=queue_dir)
    orchestrator = Orchestrator(
        signalscribe=MockSignalScribe(),
        buatlas=MockBUAtlas(),
        pushpilot=MockPushPilot(),
        audit_writer=audit_writer,
        hitl_queue=hitl_queue,
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


def main() -> None:
    app()


if __name__ == "__main__":
    main()
