"""explain command — human-readable decision trail for a change_id.

This is the observability command for PulseCraft. It reconstructs and narrates
every decision gate, policy enforcement step, and HITL event that a change
experienced as it moved through the pipeline.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from pulsecraft.cli.common import DEFAULT_AUDIT_DIR, DEFAULT_QUEUE_DIR, resolve_change_id

console = Console()
err_console = Console(stderr=True)

_GATE_LABELS = {
    1: "worth communicating?",
    2: "ripe?",
    3: "clear?",
    4: "affected?",
    5: "worth sending?",
    6: "delivery timing?",
}

_AGENT_LABELS = {
    "signalscribe": "SignalScribe",
    "buatlas": "BUAtlas",
    "pushpilot": "PushPilot",
}

_VERB_COLORS = {
    "COMMUNICATE": "green",
    "RIPE": "green",
    "READY": "green",
    "AFFECTED": "green",
    "WORTH_SENDING": "green",
    "SEND_NOW": "green",
    "ARCHIVE": "dim",
    "NOT_AFFECTED": "dim",
    "HOLD_UNTIL": "yellow",
    "HOLD_INDEFINITE": "yellow",
    "DIGEST": "blue",
    "NEED_CLARIFICATION": "yellow",
    "UNRESOLVABLE": "red",
    "ESCALATE": "red",
}

JOURNEY_TRUNCATE = 12


def register(app: typer.Typer) -> None:
    @app.command("explain")
    def explain(
        change_id: str = typer.Argument(  # noqa: B008
            ...,
            help="change_id (full UUID or first 8 chars).",
        ),
        audit_dir: Path = typer.Option(DEFAULT_AUDIT_DIR, "--audit-dir"),  # noqa: B008
        queue_dir: Path = typer.Option(DEFAULT_QUEUE_DIR, "--queue-dir"),  # noqa: B008
        output_json: bool = typer.Option(  # noqa: B008
            False,
            "--json",
            help="Output the full Explanation object as JSON.",
        ),
        verbose: bool = typer.Option(  # noqa: B008
            False,
            "--verbose",
            help="Include policy check details.",
        ),
        no_draft: bool = typer.Option(  # noqa: B008
            False,
            "--no-draft",
            help="Skip delivery/HITL action blocks (briefer output).",
        ),
        run_selector: int = typer.Option(  # noqa: B008
            -1,
            "--run",
            "-r",
            help="Run index. -1=latest (default), 1=earliest, 2=second, etc.",
        ),
        show_all: bool = typer.Option(  # noqa: B008
            False,
            "--all",
            "-a",
            help="Show all runs combined (full chain view).",
        ),
        list_runs: bool = typer.Option(  # noqa: B008
            False,
            "--list-runs",
            help="List all pipeline runs without full explanation.",
        ),
    ) -> None:
        """Human-readable decision trail for a change_id.

        Narrates every agent gate, policy override, HITL event, and delivery
        outcome that the change experienced. The demo-day observability command.

        By default shows only the most recent pipeline run. Use --all to see
        all runs combined, or --run N to select a specific run.

        Examples:
          pulsecraft explain a1b2c3d4
          pulsecraft explain a1b2c3d4 --json
          pulsecraft explain a1b2c3d4 --verbose
          pulsecraft explain a1b2c3d4 --list-runs
          pulsecraft explain a1b2c3d4 --run 1
          pulsecraft explain a1b2c3d4 --all
        """
        from pulsecraft.cli.common import load_audit_writer
        from pulsecraft.skills.explain_chain import RunNotFound, build_explanation, detect_runs

        full_id = resolve_change_id(change_id, audit_dir)
        audit_writer = load_audit_writer(audit_dir)

        # --list-runs: show run table and exit
        if list_runs:
            all_records = audit_writer.read_chain(full_id)
            if not all_records:
                err_console.print(f"[red]No audit records found for:[/red] {full_id}")
                raise typer.Exit(code=2)
            runs = detect_runs(all_records)
            _render_run_list(full_id, runs, all_records)
            return

        from typing import Literal

        run_sel: int | Literal["all"] = "all" if show_all else run_selector

        try:
            exp = build_explanation(full_id, audit_writer, run_selector=run_sel)
        except RunNotFound as exc:
            err_console.print(f"[red]Run not found:[/red] {exc}")
            raise typer.Exit(code=2) from exc

        if not exp.state_transitions and not exp.agent_decisions:
            err_console.print(f"[red]No audit records found for:[/red] {full_id}")
            raise typer.Exit(code=2)

        if output_json:
            from pulsecraft.cli.common import print_json_output

            print_json_output(exp)
            return

        _render_explain(
            exp,
            verbose=verbose,
            no_draft=no_draft,
            queue_dir=queue_dir,
            show_all=show_all,
            run_selector=run_selector,
        )


# ── rendering ─────────────────────────────────────────────────────────────────


def _render_run_list(change_id: str, runs, all_records) -> None:
    """Print a table of all detected pipeline runs."""
    from rich.table import Table

    short_id = change_id[:8]
    table = Table(title=f"Pipeline runs for {short_id}…", show_header=True)
    table.add_column("#", style="bold", width=4)
    table.add_column("Started (UTC)", width=18)
    table.add_column("Duration", width=10)
    table.add_column("Terminal", width=16)
    table.add_column("Records", width=9)

    for run in runs:
        duration = run.end_timestamp - run.start_timestamp
        dur_str = f"{duration.total_seconds():.1f}s"
        terminal = run.terminal_state or "—"
        terminal_color = _terminal_color(terminal) if run.terminal_state else "dim"
        record_count = run.end_idx - run.start_idx + 1
        table.add_row(
            str(run.run_index),
            run.start_timestamp.strftime("%H:%M:%S"),
            dur_str,
            f"[{terminal_color}]{terminal}[/{terminal_color}]",
            str(record_count),
        )

    console.print(table)
    console.print(f"\n[dim]Total: {len(runs)} run(s) · {len(all_records)} audit records[/dim]\n")


def _render_explain(
    exp,
    *,
    verbose: bool,
    no_draft: bool,
    queue_dir: Path,
    show_all: bool = False,
    run_selector: int = -1,
) -> None:
    short_id = exp.change_id[:8]
    terminal = exp.terminal_state or "unknown"

    # ── Header panel ──────────────────────────────────────────────────────
    latency_str = f"{exp.total_latency_seconds:.1f}s" if exp.total_latency_seconds else "—"
    period_str = ""
    if exp.first_record_at and exp.last_record_at:
        period_str = (
            f"{exp.first_record_at.strftime('%H:%M:%S')} → "
            f"{exp.last_record_at.strftime('%H:%M:%S')} UTC"
        )

    header_lines = [f"[bold]Change:[/bold]  {short_id}…"]
    if period_str:
        header_lines.append(f"[bold]Period:[/bold]  {period_str}  ({latency_str} end-to-end)")

    terminal_color = _terminal_color(terminal)
    header_lines.append(f"[bold]Status:[/bold]  [{terminal_color}]{terminal}[/{terminal_color}]")

    # Run context line
    if not show_all and exp.run_count > 0:
        if run_selector == -1:
            run_line = f"[bold]Run:[/bold]     latest (run {exp.run_index} of {exp.run_count})"
        else:
            run_line = f"[bold]Run:[/bold]     {exp.run_index} of {exp.run_count}"
        header_lines.append(run_line)
    elif show_all and exp.run_count > 1:
        header_lines.append(f"[bold]Run:[/bold]     all ({exp.run_count} runs combined)")

    console.print(
        Panel(
            "\n".join(header_lines),
            title="[bold]PulseCraft /explain[/bold]",
        )
    )

    # ── State journey ─────────────────────────────────────────────────────
    if exp.state_transitions:
        states: list[str] = []
        for t in exp.state_transitions:
            if t.from_state is None or not states or states[-1] != t.to_state:
                states.append(t.to_state)

        n = len(states)
        if n <= JOURNEY_TRUNCATE:
            journey = " → ".join(states)
            console.print(f"\n  [dim]Journey ({n} steps):[/dim]  {journey}\n")
        else:
            # Show first 5 + … + last 2
            head = " → ".join(states[:5])
            tail = " → ".join(states[-2:])
            console.print(f"\n  [dim]Journey ({n} steps):[/dim]  {head} … {tail}\n")

    # ── Pipeline trace ────────────────────────────────────────────────────
    console.print("  [bold]Pipeline trace[/bold]\n")

    for event in exp.agent_decisions:
        _render_agent_event(event)

    # ── Policy checks (verbose only) ──────────────────────────────────────
    if verbose and exp.policy_events:
        console.print("\n  [dim]Policy checks:[/dim]")
        for pe in exp.policy_events:
            symbol = "[green]✓[/green]" if pe.passed else "[red]✗[/red]"
            console.print(f"    {symbol} [dim]{pe.check_name}:[/dim] {pe.summary}")

    if not no_draft:
        # ── HITL events ───────────────────────────────────────────────────
        if exp.hitl_events:
            console.print()
            for he in exp.hitl_events:
                _render_hitl_event(he)

        # ── Delivery events ───────────────────────────────────────────────
        if exp.delivery_events:
            console.print("\n  [bold]Delivery:[/bold]")
            for de in exp.delivery_events:
                verb_color = _VERB_COLORS.get(de.decision.upper(), "white")
                console.print(
                    f"    [{verb_color}]{de.bu_id}[/{verb_color}] → "
                    f"[bold]{de.channel}[/bold] "
                    f"([{verb_color}]{de.decision}[/{verb_color}])"
                )
                if de.reason:
                    console.print(f'      [dim]"{_truncate(de.reason, 80)}"[/dim]')

        # ── HITL queue status ─────────────────────────────────────────────
        if terminal == "AWAITING_HITL":
            _render_hitl_queue_hint(exp.change_id, queue_dir)

    # ── Errors ───────────────────────────────────────────────────────────
    if exp.errors:
        console.print("\n  [red]Errors recorded:[/red]")
        for err in exp.errors:
            console.print(f"    [red]•[/red] {err}")

    # ── Totals ────────────────────────────────────────────────────────────
    cost_str = f"${exp.total_cost_usd:.4f}" if exp.total_cost_usd else "$0.00"
    console.print(
        f"\n[dim]Total: {exp.invocation_count} LLM invocation"
        f"{'s' if exp.invocation_count != 1 else ''} · "
        f"{cost_str} · {latency_str} end-to-end.[/dim]\n"
    )


def _render_agent_event(event) -> None:
    agent_label = _AGENT_LABELS.get(event.agent, event.agent)
    bu_suffix = f" — [cyan]{event.bu_id}[/cyan]" if event.bu_id else ""
    ts_str = event.timestamp.strftime("%H:%M:%S")

    console.print(f"  [{ts_str}]  [bold]{agent_label}[/bold]{bu_suffix}")

    # Primary gate
    _render_gate_line(event.gate, event.verb, event.reason, indent="    ")

    # Extra gates (e.g. gates 2+3 from SignalScribe, gate 5 from BUAtlas)
    for extra_gate, extra_verb in event.extra_verbs:
        _render_gate_line(extra_gate, extra_verb, "", indent="    ")

    console.print()


def _render_gate_line(gate: int, verb: str, reason: str, indent: str) -> None:
    gate_label = _GATE_LABELS.get(gate, f"gate {gate}")
    verb_color = _VERB_COLORS.get(verb.upper(), "white")
    gate_prefix = f"[dim]Gate {gate} ({gate_label}):[/dim]"
    verb_str = f"[{verb_color}]{verb}[/{verb_color}]"
    console.print(f"{indent}→ {gate_prefix}  {verb_str}")
    if reason:
        console.print(f'{indent}  [dim]"{_truncate(reason, 100)}"[/dim]')


def _render_hitl_event(event) -> None:
    action = event.action
    ts_str = event.timestamp.strftime("%H:%M:%S")

    if action == "enqueued":
        reason = _extract_hitl_reason(event.notes or "")
        console.print(f"  [{ts_str}]  [yellow]HITL triggered[/yellow]  →  [bold]{reason}[/bold]")
        if event.notes:
            console.print(f'    [dim]"{_truncate(event.notes, 80)}"[/dim]')
    elif action in ("approved", "rejected"):
        color = "green" if action == "approved" else "red"
        console.print(
            f"  [{ts_str}]  [{color}]HITL {action}[/{color}]  by [bold]{event.actor}[/bold]"
        )
        if event.notes:
            console.print(f'    [dim]"{_truncate(event.notes, 80)}"[/dim]')
    else:
        console.print(f"  [{ts_str}]  [dim]HITL {action}[/dim]  ({event.actor})")


def _render_hitl_queue_hint(change_id: str, queue_dir: Path) -> None:
    short = change_id[:8]
    pending_path = queue_dir / "pending" / f"{change_id}.json"
    location = str(pending_path) if pending_path.exists() else "queue/hitl/pending/"
    console.print(
        f"\n  [yellow]Awaiting review[/yellow] → {location}\n"
        f"  Run [bold]pulsecraft approve {short}[/bold] to release to delivery.\n"
        f"  Run [bold]pulsecraft reject {short} --reason <text>[/bold] to reject."
    )


# ── helpers ───────────────────────────────────────────────────────────────────


def _extract_hitl_reason(notes: str) -> str:
    import re

    m = re.search(r"reason=(\S+)", notes)
    return m.group(1) if m else notes[:40]


def _terminal_color(terminal: str) -> str:
    return {
        "DELIVERED": "green",
        "ARCHIVED": "dim",
        "HELD": "yellow",
        "DIGESTED": "blue",
        "AWAITING_HITL": "yellow",
        "REJECTED": "red",
        "FAILED": "red bold",
    }.get(terminal, "white")


def _truncate(s: str, n: int) -> str:
    if len(s) <= n:
        return s
    return s[: n - 1] + "…"
