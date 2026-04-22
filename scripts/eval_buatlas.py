#!/usr/bin/env python3
"""BUAtlas eval script — variance-aware, N=3 runs per fixture.

Runs SignalScribe first to obtain ChangeBriefs, then evaluates BUAtlas
for candidate BUs derived from the registry. Reports per-BU terminal
category distribution and flags instabilities or false-positive risks.

Usage:
    python scripts/eval_buatlas.py              # uses ANTHROPIC_API_KEY
    PULSECRAFT_RUN_LLM_TESTS=1 python scripts/eval_buatlas.py

Writes report to audit/eval/buatlas-<timestamp>.txt.
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path


# Load .env before imports that check ANTHROPIC_API_KEY
def _load_env() -> None:
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


_load_env()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pulsecraft.agents.buatlas import (  # noqa: E402
    AgentInvocationError,
    AgentOutputValidationError,
    BUAtlas,
)
from pulsecraft.agents.signalscribe import SignalScribe  # noqa: E402
from pulsecraft.config.loader import get_bu_profile, get_bu_registry  # noqa: E402
from pulsecraft.schemas.change_artifact import ChangeArtifact  # noqa: E402
from pulsecraft.schemas.change_brief import ChangeBrief  # noqa: E402
from pulsecraft.schemas.personalized_brief import Relevance  # noqa: E402

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "changes"
AUDIT_DIR = Path(__file__).parent.parent / "audit" / "eval"

# Expected terminal categories from fixtures/changes/README.md
# format: (fixture_file, bu_id, expected_gate4_category, expected_gate5_category_or_None)
# gate4 categories: "affected", "adjacent", "not_affected"
# gate5 categories: "worth_sending", "weak", "not_worth" or None (if gate4 not affected)
_EXPECTED: list[tuple[str, str, str, str | None]] = [
    ("change_001_clearcut_communicate.json", "bu_alpha", "affected", "worth_sending"),
    ("change_006_multi_bu_affected_vs_adjacent.json", "bu_zeta", "affected", "worth_sending"),
    ("change_006_multi_bu_affected_vs_adjacent.json", "bu_delta", "adjacent", None),
    ("change_008_post_hoc_already_shipped.json", "bu_epsilon", "affected", "worth_sending"),
]

# Semantically close category sets (same stop-action behavior)
_GATE4_CLOSE = {
    "not_affected": {"not_affected", "adjacent"},  # both = don't push-notify
    "adjacent": {"adjacent", "not_affected"},
    "affected": {"affected"},
}
_GATE5_CLOSE = {
    "worth_sending": {"worth_sending", "weak"},  # both = draft exists, may send
    "weak": {"weak", "worth_sending"},
    "not_worth": {"not_worth"},
}

RUNS_PER_FIXTURE = 3


def _terminal_category(pb) -> tuple[str, str | None]:
    """Return (gate4_verb, gate5_verb_or_none) from a PersonalizedBrief."""
    gate4_verb = str(pb.relevance)
    if pb.relevance == Relevance.AFFECTED and pb.message_quality is not None:
        gate5_verb = str(pb.message_quality)
    else:
        gate5_verb = None
    return gate4_verb, gate5_verb


def _classify_run(
    actual_gate4: str,
    actual_gate5: str | None,
    expected_gate4: str,
    expected_gate5: str | None,
) -> str:
    """Return classification for one run."""
    # Check gate4
    close4 = _GATE4_CLOSE.get(expected_gate4, {expected_gate4})
    gate4_match = actual_gate4 in close4
    gate4_exact = actual_gate4 == expected_gate4

    if (
        not gate4_exact
        and actual_gate4 == "affected"
        and expected_gate4 in ("adjacent", "not_affected")
    ):
        return "false_positive"  # stricter than expected (AFFECTED when should be adjacent/not)

    if not gate4_match:
        return "mismatch"

    # Gate4 matched (exact or close) — check gate5
    if expected_gate5 is None:
        # Gate5 not expected (not affected / adjacent)
        return "match" if gate4_exact else "close"

    if actual_gate5 is None:
        # Gate4 returned "affected" from close set but gate5 is skipped — inconsistency
        return "close"

    close5 = _GATE5_CLOSE.get(expected_gate5, {expected_gate5})
    if actual_gate5 in close5:
        return "match" if (gate4_exact and actual_gate5 == expected_gate5) else "close"
    return "mismatch"


def _get_signalscribe_brief(ss: SignalScribe, fixture_file: str) -> ChangeBrief | None:
    try:
        artifact = ChangeArtifact.model_validate(
            json.loads((FIXTURES_DIR / fixture_file).read_text())
        )
        return ss.invoke(artifact)
    except Exception as exc:
        print(f"  SignalScribe failed for {fixture_file}: {exc}", flush=True)
        return None


def _get_candidate_bus(change_brief: ChangeBrief) -> list[str]:
    registry = get_bu_registry()
    impact = set(change_brief.impact_areas)
    return [entry.bu_id for entry in registry.bus if set(entry.owned_product_areas) & impact]


def main() -> None:
    now_str = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    model = "claude-sonnet-4-6"
    print(
        f"\nBUAtlas Eval Report (model: {model}, runs per fixture: {RUNS_PER_FIXTURE}, "
        f"date: {datetime.now(UTC).strftime('%Y-%m-%d')})\n",
        flush=True,
    )

    ss = SignalScribe()
    ba = BUAtlas()

    total_latency = 0.0
    issues: list[str] = []
    report_lines: list[str] = []

    # Group expected by fixture

    fixture_groups: dict[str, list[tuple[str, str, str | None]]] = {}
    for fixture_file, bu_id, exp_gate4, exp_gate5 in _EXPECTED:
        fixture_groups.setdefault(fixture_file, []).append((bu_id, exp_gate4, exp_gate5))

    for fixture_file, bu_expectations in fixture_groups.items():
        sep = "─" * 77
        header = f"\nFixture: {fixture_file}"
        print(sep)
        print(header)
        print(sep)
        report_lines += [sep, header, sep]

        # Get ChangeBrief via SignalScribe (once per fixture)
        print("  Running SignalScribe...", flush=True)
        cb = _get_signalscribe_brief(ss, fixture_file)
        if cb is None:
            msg = "  ERROR: SignalScribe failed — skipping fixture"
            print(msg)
            report_lines.append(msg)
            issues.append(f"{fixture_file}: SignalScribe failure")
            continue

        candidate_buses = _get_candidate_bus(cb)
        print(f"  SignalScribe: change_id={cb.change_id[:8]}... impact_areas={cb.impact_areas}")
        print(f"  Candidate BUs from registry: {candidate_buses}")

        # Evaluate each expected BU
        for bu_id, exp_gate4, exp_gate5 in bu_expectations:
            if bu_id not in candidate_buses:
                msg = f"  ⚠️  {bu_id}: NOT IN CANDIDATE SET (impact_areas mismatch — SignalScribe returned different areas)"
                print(msg)
                report_lines.append(msg)
                issues.append(
                    f"{fixture_file} {bu_id}: not in candidate set from real SignalScribe"
                )
                continue

            bu_profile = get_bu_profile(bu_id)
            gate4_results: list[str] = []
            gate5_results: list[str | None] = []
            run_classifications: list[str] = []

            print(f"\n  BU: {bu_id} (expected: gate4={exp_gate4}, gate5={exp_gate5})")

            for run_n in range(1, RUNS_PER_FIXTURE + 1):
                print(f"    Run {run_n}/{RUNS_PER_FIXTURE}...", end=" ", flush=True)
                t0 = time.monotonic()
                try:
                    pb = ba.invoke(cb, bu_profile)
                    elapsed = time.monotonic() - t0
                    total_latency += elapsed
                    g4, g5 = _terminal_category(pb)
                    gate4_results.append(g4)
                    gate5_results.append(g5)
                    classification = _classify_run(g4, g5, exp_gate4, exp_gate5)
                    run_classifications.append(classification)
                    print(f"gate4={g4} gate5={g5} ({elapsed:.1f}s) [{classification}]")
                except (AgentInvocationError, AgentOutputValidationError, Exception) as exc:
                    elapsed = time.monotonic() - t0
                    total_latency += elapsed
                    gate4_results.append("ERROR")
                    gate5_results.append(None)
                    run_classifications.append("error")
                    print(f"ERROR: {type(exc).__name__}: {str(exc)[:80]}")

            # Summarize
            g4_counter = Counter(gate4_results)
            g5_counter = Counter(str(g) for g in gate5_results if g is not None)
            all_match = all(c == "match" for c in run_classifications)
            all_close = all(c in ("match", "close") for c in run_classifications)
            any_false_positive = any(c == "false_positive" for c in run_classifications)
            any_mismatch = any(c == "mismatch" for c in run_classifications)
            any_error = any(c == "error" for c in run_classifications)

            g4_str = ", ".join(f"{v}({n}/{RUNS_PER_FIXTURE})" for v, n in g4_counter.most_common())
            g5_str = (
                ", ".join(f"{v}({n})" for v, n in g5_counter.most_common())
                if g5_counter
                else "(skipped)"
            )

            if any_false_positive:
                status = f"⚠️  FALSE-POSITIVE RISK — AFFECTED when expected {exp_gate4}"
                issues.append(f"{fixture_file} {bu_id}: false-positive risk ({g4_str})")
            elif any_mismatch or any_error:
                status = f"❌  mismatch/error — gate4={g4_str}"
                issues.append(f"{fixture_file} {bu_id}: mismatch/error ({g4_str})")
            elif all_match:
                status = "✅  stable match"
            elif all_close:
                status = "✅  acceptable variance"
            else:
                status = "🟡  unstable"
                issues.append(f"{fixture_file} {bu_id}: unstable across runs ({g4_str})")

            stability_g4 = "✅ stable" if len(g4_counter) == 1 else "🟡 unstable"
            stability_g5 = "✅ stable" if len(g5_counter) <= 1 else "🟡 unstable"

            summary = (
                f"  {bu_id}:\n"
                f"    Gate 4: {g4_str:40s}  {stability_g4}\n"
                f"    Gate 5: {g5_str:40s}  {stability_g5}\n"
                f"    Expected: gate4={exp_gate4}, gate5={exp_gate5}\n"
                f"    Status: {status}"
            )
            print(summary)
            report_lines.append(summary)

    # Summary
    total_invocations = sum(
        RUNS_PER_FIXTURE
        for fixture_file, bu_expectations in fixture_groups.items()
        for _ in bu_expectations
    )

    footer = (
        f"\n{'─' * 77}\n"
        f"Total BU-eval invocations: ~{total_invocations} "
        f"({len(fixture_groups)} fixtures × avg {RUNS_PER_FIXTURE} BU-eval events × {RUNS_PER_FIXTURE} runs)\n"
        f"Total latency: {total_latency:.1f}s (mostly parallelized per BU within a run)\n"
    )
    print(footer)
    report_lines.append(footer)

    if issues:
        issues_block = "Items worth reviewing:\n" + "\n".join(f"  - {i}" for i in issues)
        print(issues_block)
        report_lines.append(issues_block)
    else:
        ok_msg = "No issues — all BU-eval events stable and matching expected categories."
        print(ok_msg)
        report_lines.append(ok_msg)

    # Write report
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = AUDIT_DIR / f"buatlas-{now_str}.txt"
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"\nReport saved to: {report_path}")


if __name__ == "__main__":
    main()
