# Prompt 04 — Orchestrator

> **How to use this prompt.** Paste below the `---` line into Claude Code, running inside the repo. Claude Code builds the orchestrator, tests it against mock agents, commits.
>
> **Expected duration:** 90–120 minutes.
>
> **Prerequisite:** Prompts 00–03.6 completed. 84 tests passing. `CLAUDE.md` exists at repo root.
>
> **What this prompt does NOT do:** no real LLM calls. Agents are mocked. Real SignalScribe arrives in prompt 05. This prompt builds the *plumbing* that will host real agents later.

---

# Instructions for Claude Code

You are authoring the **orchestrator** for PulseCraft — the deterministic Python service that sequences work across the three agents (SignalScribe, BUAtlas, PushPilot), respects the decision verbs they return, manages the HITL queue, and writes the audit trail. The orchestrator is *not itself an agent* — it's state-machine code that hosts and coordinates agentic subagents.

Agents don't exist yet as LLM prompts. This prompt uses **mock agents** that return pre-scripted decisions so the orchestrator's plumbing is fully testable. Real agents replace the mocks in prompts 05, 06, 07 — and because the orchestrator depends on the Pydantic contracts from prompt 02, not on agent internals, that swap is clean.

## Environment discipline

Always invoke Python tools via the venv binary: `.venv/bin/python`, `.venv/bin/pytest`, `.venv/bin/ruff`, `.venv/bin/mypy`. `uv run <cmd>` is acceptable. Never rely on `source .venv/bin/activate` persisting between tool calls.

## Context to read before starting

1. `CLAUDE.md` — standing instructions
2. `design/planning/01-decision-criteria.md` — the decision verbs the orchestrator must respect (critical for state-transition logic)
3. `design/adr/ADR-002-subagent-topology.md` — fan-out strategy, tool scoping, component-to-primitive map
4. `src/pulsecraft/schemas/` — all existing Pydantic models (ChangeArtifact, ChangeBrief, PersonalizedBrief, DeliveryPlan, BUProfile, AuditRecord, Decision, DecisionVerb)
5. `src/pulsecraft/config/loader.py` — how configs are loaded
6. `fixtures/changes/` — scan filenames to know what fixtures exist

If anything in this prompt contradicts the decision criteria doc, the decision criteria wins.

## What "done" looks like

When you finish:

1. `src/pulsecraft/orchestrator/` has a complete, typed, tested orchestrator.
2. Workflow state machine with explicit states and transitions.
3. Mock agents that return scripted decisions, used only in tests.
4. HITL queue management (pending, approved, rejected, held, digested, archived).
5. Append-only audit writer that records every state transition, agent invocation, and decision.
6. A `pulsecraft run-change` CLI command that takes a fixture file and drives it through the pipeline end-to-end with mock agents, printing the state transitions and final outcome.
7. Integration tests that run each of the 8 fixtures through the pipeline with scripted mock responses and assert the expected terminal state.
8. `CLAUDE.md` extended with an **Orchestrator** section.
9. One feature commit + optional prompt-archive commit.
10. All 84 prior tests still pass; ~30-50 new tests added.

## Design principles

1. **Deterministic code, no LLM reasoning.** The orchestrator is a state machine. Every decision is either an input from an agent (which hands back a decision verb) or a rule (confidence threshold, policy check, HITL trigger). No "figure out what to do" LLM calls anywhere in the orchestrator itself.
2. **Agents are called via a narrow interface.** Define an `AgentProtocol` (Python `typing.Protocol`) with methods like `invoke(input_contract) -> output_contract`. Real agents (prompts 05-07) and mock agents both implement this interface. The orchestrator never imports or knows anything about Anthropic SDKs, Claude Code, prompts, or LLM specifics.
3. **Every state transition is atomic and audited.** You cannot transition without writing an audit record. Crash between write and transition → replay is possible because the audit is authoritative, not the in-memory state.
4. **Idempotency is non-negotiable.** Running the same change twice produces the same output. `change_id` is the idempotency key.
5. **HITL is a first-class state, not an exception.** When an agent returns `ESCALATE`, `NEED_CLARIFICATION`, `UNRESOLVABLE`, or a confidence threshold fails, the work enters the HITL queue. The queue is a proper data structure, not a folder of files.
6. **Policy invariants belong in code, not in agent prompts.** The orchestrator refuses to transition to `DELIVERED` if policy hooks say no, even if PushPilot returned `SEND_NOW`. Agent reasons *within* policy; orchestrator enforces policy.
7. **Single-process, single-threaded for v1.** No async except where clearly needed for parallel BUAtlas fan-out (and even that can be `asyncio.gather` over sync calls wrapped in `asyncio.to_thread` — we're not optimizing for concurrency yet).
8. **No real network calls, no real LLM calls.** Mock agents only. The code is structured so real calls drop in later via the `AgentProtocol`.

## Step-by-step work

### Step 1 — Design the state machine

Create `src/pulsecraft/orchestrator/states.py`:

- `WorkflowState` as a `StrEnum` with exactly these values (match what's in `design/planning/01-decision-criteria.md` and the architecture diagram):
  - `RECEIVED` — change artifact accepted, validated, pending interpretation
  - `INTERPRETED` — SignalScribe returned a ChangeBrief; decisions from gates 1-3 recorded
  - `ROUTED` — BU pre-filter has identified candidate BUs
  - `PERSONALIZED` — BUAtlas fan-out complete for all candidate BUs; gates 4-5 decisions recorded
  - `AWAITING_HITL` — change is queued for human review
  - `SCHEDULED` — PushPilot's gate-6 decision made, delivery scheduled (including `HOLD_UNTIL` dates)
  - `DELIVERED` — at least one notification successfully delivered
  - Terminal states: `ARCHIVED`, `HELD`, `DIGESTED`, `REJECTED`, `FAILED`

- `TransitionRule` as a dataclass / named tuple mapping (from_state, decision_verb_or_event) → to_state. Examples:
  - `(RECEIVED, "signalscribe_completed_communicate_ripe_ready")` → `INTERPRETED`
  - `(RECEIVED, "signalscribe_archive")` → `ARCHIVED` (terminal)
  - `(RECEIVED, "signalscribe_hold_until")` → `HELD`
  - `(RECEIVED, "signalscribe_escalate_or_need_clarification")` → `AWAITING_HITL`
  - `(INTERPRETED, "buatlas_all_not_affected")` → `ARCHIVED`
  - `(PERSONALIZED, "any_affected_worth_sending")` → (either `AWAITING_HITL` or `SCHEDULED` depending on HITL triggers)
  - `(SCHEDULED, "pushpilot_send_now_policy_ok")` → `DELIVERED`
  - etc.

- A function `valid_transitions(from_state) -> set[WorkflowState]` for introspection.

- A function `apply_transition(current_state, event) -> WorkflowState | raise IllegalTransitionError`.

Write tests enumerating every expected valid transition and asserting that invalid transitions raise.

### Step 2 — The `AgentProtocol` interface

Create `src/pulsecraft/orchestrator/agent_protocol.py`:

```python
from typing import Protocol, runtime_checkable
# + imports from pulsecraft.schemas

@runtime_checkable
class SignalScribeProtocol(Protocol):
    agent_name: str  # "signalscribe"
    version: str

    def invoke(self, artifact: ChangeArtifact) -> ChangeBrief:
        """Interpret a change artifact. Must return a ChangeBrief with
        decisions[] populated from gates 1, 2, 3."""
        ...

@runtime_checkable
class BUAtlasProtocol(Protocol):
    agent_name: str  # "buatlas"
    version: str

    def invoke(
        self,
        change_brief: ChangeBrief,
        bu_profile: BUProfile,
        past_engagement: PastEngagement | None = None,
    ) -> PersonalizedBrief:
        """Personalize for one BU. Must return a PersonalizedBrief with
        decisions[] populated from gates 4, 5."""
        ...

@runtime_checkable
class PushPilotProtocol(Protocol):
    agent_name: str  # "pushpilot"
    version: str

    def invoke(
        self,
        personalized_brief: PersonalizedBrief,
        recipient_preferences: RecipientPreferences,
    ) -> DeliveryDecision:
        """Decide gate 6 for one notification. Returns a DeliveryDecision
        (subset of DeliveryPlan focused on the decision itself)."""
        ...
```

If `PastEngagement`, `RecipientPreferences`, or `DeliveryDecision` aren't yet defined as schemas, add minimal Pydantic models to `src/pulsecraft/schemas/` with only the fields the orchestrator actually needs. Update the schema JSON files (in `schemas/`) accordingly and add to the enum-parity tests if they touch decision verbs. Flag any schema additions in the final report.

### Step 3 — Mock agents for testing

Create `src/pulsecraft/orchestrator/mock_agents.py`:

- `MockSignalScribe` — constructor takes a `script: dict[str, Decision]` mapping `change_id` to a scripted gate-3-terminal decision (or earlier terminal like `ARCHIVE`). The mock returns a ChangeBrief whose `decisions[]` matches the script. For fixtures where no script is provided, default to `COMMUNICATE → RIPE → READY` with dummy confidence 0.85.
- `MockBUAtlas` — constructor takes a `script: dict[tuple[change_id, bu_id], tuple[Decision, Decision]]` mapping (change, BU) pairs to (gate-4, gate-5) decisions. Defaults to `AFFECTED + WORTH_SENDING` for BUs that match owned_product_areas, else `NOT_AFFECTED`.
- `MockPushPilot` — constructor takes a `script: dict[personalized_brief_id, Decision]`. Defaults to `SEND_NOW`.

The mocks implement the respective Protocols. They do NOT make any network or LLM calls. They do NOT read config. They return deterministic results.

In mocks, `agent_name` is `"signalscribe_mock"`, `"buatlas_mock"`, `"pushpilot_mock"`, and `version` is `"mock-1.0"`. This keeps real vs. mock clearly distinguishable in audit logs.

### Step 4 — The audit writer

Create `src/pulsecraft/orchestrator/audit.py`:

- `AuditWriter` — append-only writer that writes `AuditRecord` instances to JSONL files in `audit/YYYY-MM-DD/<change_id>.jsonl`. One file per change per day. Atomic appends (open in `'a'`, write line, `fsync`, close).
- Methods:
  - `log_event(record: AuditRecord) -> None`
  - `read_chain(change_id: str) -> list[AuditRecord]` — reads all audit records for a change, ordered by timestamp. Used by `/explain` later.
  - `summary(change_id: str) -> str` — human-readable decision chain summary.
- `AuditWriter` is injected into the orchestrator (don't use a global singleton). Tests use a temp directory fixture.
- Audit writes never block or throw — if write fails, log a structured error via `structlog` but do NOT propagate the failure up to the orchestrator (audit is observability, not correctness). Exception: at the end of a change run, verify the expected number of audit records landed and warn loudly if not.

### Step 5 — The HITL queue

Create `src/pulsecraft/orchestrator/hitl.py`:

- `HITLQueue` — storage-backed queue with these methods:
  - `enqueue(change_id: str, reason: HITLReason, payload: dict) -> None`
  - `list_pending() -> list[HITLItem]`
  - `approve(change_id: str, reviewer: str, notes: str | None) -> None`
  - `reject(change_id: str, reviewer: str, reason: str) -> None`
  - `edit(change_id: str, field_path: str, new_value: Any, reviewer: str) -> None` — for editing drafted messages before approval; writes the edit to the audit log and re-runs downstream gates if needed (for v1, just record the edit; full re-run logic is a future prompt)
  - `answer_clarification(change_id: str, answers: dict[str, str], reviewer: str) -> None` — for responding to SignalScribe's gate-3 questions
- `HITLReason` is an enum:
  - `agent_escalate`, `need_clarification`, `unresolvable`, `confidence_below_threshold`, `priority_p0`, `draft_has_commitment`, `restricted_term_detected`, `mlr_sensitive`, `second_weak_from_gate_5`, `dedupe_or_rate_limit_conflict`
- Storage for v1: JSON files in `queue/hitl/pending/`, `queue/hitl/approved/`, etc. Each item is one file named `<change_id>.json`. This is intentionally file-based — simple, observable (operator can `ls queue/hitl/pending/` to see what's waiting), no DB setup required. Later prompts may move to a real queue.
- Every HITL operation writes to audit.

### Step 6 — The orchestrator engine

Create `src/pulsecraft/orchestrator/engine.py`:

This is the core module. It exposes:

```python
class Orchestrator:
    def __init__(
        self,
        signalscribe: SignalScribeProtocol,
        buatlas: BUAtlasProtocol,
        pushpilot: PushPilotProtocol,
        audit_writer: AuditWriter,
        hitl_queue: HITLQueue,
        config: Config,  # from pulsecraft.config
    ): ...

    def run_change(self, artifact: ChangeArtifact) -> RunResult:
        """Drive a single change artifact through the full pipeline.
        Returns a RunResult summarizing the terminal state and outcomes."""
```

The `run_change` logic (pseudocode — you implement cleanly):

```
1. Write audit: event=state_transition, from=None, to=RECEIVED
2. Validate artifact against schema (redundant but cheap)
3. Call signalscribe.invoke(artifact) → change_brief
4. Write audit: event=agent_invocation, actor=signalscribe, decisions=change_brief.decisions
5. Look at change_brief.decisions to determine gate outcomes:
    - If gate 1 ARCHIVE → transition to ARCHIVED; return
    - If gate 1 ESCALATE or gate 3 NEED_CLARIFICATION/UNRESOLVABLE → enqueue HITL; transition AWAITING_HITL; return
    - If gate 2 HOLD_UNTIL or HOLD_INDEFINITE → transition HELD; persist re-eval trigger; return
    - If gate 1 COMMUNICATE + gate 2 RIPE + gate 3 READY → transition INTERPRETED; continue
6. BU pre-filter via lookup-bu-registry (use config): candidate_bus = list of BUProfile objects
7. Transition to ROUTED; write audit
8. For each candidate BU (can be sequential in v1 to keep things simple; parallelize later):
    - bu_profile = load profile
    - personalized_brief = buatlas.invoke(change_brief, bu_profile)
    - Write audit: event=agent_invocation, actor=buatlas, bu_id=bu_id, decisions=personalized_brief.decisions
9. Aggregate personalized_briefs
    - If ALL NOT_AFFECTED → transition ARCHIVED (no one to notify); return
    - Split into: affected_worth_sending, affected_weak (regenerate once if not already retried — then HITL), adjacent (digest-only), not_affected (drop)
10. Transition PERSONALIZED; write audit
11. Check HITL triggers on the aggregated result:
    - Any priority_p0? commitment/dates in any message? restricted_term hit? mlr_sensitive flag? confidence below threshold?
    - If yes: enqueue HITL per policy; transition AWAITING_HITL; return
12. For each worth-sending personalized_brief:
    - delivery_decision = pushpilot.invoke(personalized_brief, recipient_preferences)
    - Apply code-enforced policy checks (quiet hours, rate limits, approved channels, dedupe)
    - If policy forbids SEND_NOW: downgrade to HOLD_UNTIL with policy reason
    - Record delivery_decision
13. Transition SCHEDULED; write audit
14. For send_now decisions: execute "delivery" (in v1 with mock, just log "would send X to Y via channel Z")
15. Transition DELIVERED (if at least one send attempted); write final audit
```

A few implementation notes:

- Use the Pydantic contracts from prompt 02 verbatim. Don't invent new data shapes.
- Every `transition_to(state)` call writes audit automatically. Wrap in a helper.
- Decision interpretation — mapping from `Decision` objects to state-machine events — lives in one place: `state_machine_events.py` or similar. One function maps `list[Decision] + context → event name`. This is the "respect the agent's decision" logic.
- Confidence thresholds come from `config.policy.confidence_thresholds`. Never hardcode.
- HITL triggers come from `config.policy.hitl_triggers`. Never hardcode.
- Don't worry about parallelizing BUAtlas in v1. Sequential is fine and simpler. Add a `TODO(prompt-XX)` comment.
- RunResult includes: `change_id`, `terminal_state`, `personalized_briefs` (as dict bu_id → PersonalizedBrief), `audit_record_count`, `hitl_queued`, `errors`.

### Step 7 — CLI entry point

Extend `src/pulsecraft/cli/` with a `run-change` command:

```bash
.venv/bin/python -m pulsecraft run-change fixtures/changes/change_001_clearcut_communicate.json
```

- Loads the fixture, constructs mock agents (with defaults), runs through the orchestrator, prints:
  - Each state transition with a timestamp
  - Each agent invocation summary
  - HITL queue entries if any
  - Final terminal state and reason
- Uses `rich` for formatting.
- Exit code: 0 for any valid terminal state, 1 for FAILED or uncaught errors.

Add the command to the existing Typer `app` in `src/pulsecraft/cli/main.py`.

### Step 8 — Tests

In `tests/unit/orchestrator/` (new folder):

1. `test_state_machine.py` — enumerates every valid transition from every state + asserts invalid transitions raise.
2. `test_audit_writer.py` — writes records to tmp dir, reads back, verifies ordering + content; verifies atomicity (partial writes don't corrupt).
3. `test_hitl_queue.py` — enqueue/approve/reject/edit round-trips; reasons propagate; audit records written.
4. `test_mock_agents.py` — scripted responses match; default responses work; all Protocols satisfied at runtime.

In `tests/integration/orchestrator/` (new folder):

5. `test_run_change_fixtures.py` — one test per fixture in `fixtures/changes/`, parameterized. Each runs through the orchestrator with appropriately-scripted mocks, asserts expected terminal state. Examples:
   - Fixture 001 (clearcut_communicate) → scripted SignalScribe returns `COMMUNICATE + RIPE + READY`; BUAtlas returns `AFFECTED + WORTH_SENDING` for bu_alpha, `NOT_AFFECTED` for others; PushPilot returns `SEND_NOW`. Expected terminal: `DELIVERED`.
   - Fixture 002 (pure_internal_refactor) → SignalScribe `ARCHIVE`. Expected terminal: `ARCHIVED`.
   - Fixture 003 (ambiguous_escalate) → SignalScribe `ESCALATE`. Expected terminal: `AWAITING_HITL`.
   - Fixture 004 (early_flag_hold_until) → SignalScribe `COMMUNICATE + HOLD_UNTIL(date)`. Expected terminal: `HELD`.
   - Fixture 005 (muddled_need_clarification) → SignalScribe `NEED_CLARIFICATION(qs=[...])`. Expected terminal: `AWAITING_HITL`.
   - Fixture 006 (multi_bu_affected_vs_adjacent) → BUAtlas returns mixed verbs across BUs. Expected terminal: `DELIVERED` (if worth-sending BU exists) or `ARCHIVED` (if all adjacent/not_affected).
   - Fixture 007 (mlr_sensitive) → restricted-term hit in the drafted message → HITL. Expected terminal: `AWAITING_HITL`.
   - Fixture 008 (post_hoc_already_shipped) → worth-sending at P2 with digest_opt_in → PushPilot `DIGEST`. Expected terminal: `SCHEDULED` (since digest hasn't run yet) or `DIGESTED` if we terminate at digest-scheduling — pick one and document.
6. `test_idempotency.py` — running same fixture twice produces identical audit content for the second run (modulo timestamps).
7. `test_audit_chain_reconstruction.py` — after running fixture 001, reading the audit chain reconstructs the full state transitions and decisions.

Every test uses `.venv/bin/pytest`. Use `tmp_path` fixture for audit and HITL directories — never touch the real `audit/` or `queue/` dirs in tests.

### Step 9 — Extend `CLAUDE.md`

Open `CLAUDE.md`. Append a new section after "Agents authored so far" (or insert logically wherever it fits — look for a good spot):

```markdown
## Orchestrator

**Location:** `src/pulsecraft/orchestrator/`

**Purpose:** Deterministic workflow service that sequences agent invocations, respects decision verbs, manages HITL queue, writes audit trail. NOT an agent — code only.

**Key modules:**
- `states.py` — `WorkflowState` enum + `TransitionRule` + `apply_transition`
- `agent_protocol.py` — `SignalScribeProtocol`, `BUAtlasProtocol`, `PushPilotProtocol` (narrow interfaces)
- `mock_agents.py` — scripted mocks implementing the protocols (testing only)
- `audit.py` — `AuditWriter` — append-only JSONL per change per day
- `hitl.py` — `HITLQueue` — file-based pending/approved/rejected/etc queue
- `engine.py` — `Orchestrator.run_change(artifact) -> RunResult` — the main loop

**State machine:** RECEIVED → INTERPRETED → ROUTED → PERSONALIZED → [AWAITING_HITL?] → SCHEDULED → DELIVERED, with branch-offs to ARCHIVED, HELD, DIGESTED, REJECTED, FAILED.

**How real agents plug in:** Replace the mock agents with implementations satisfying the Protocols. Orchestrator doesn't know or care how agents reason internally. Real agents arrive in prompts 05, 06, 07.

**HITL triggers** (from `config/policy.yaml`): any agent ESCALATE, NEED_CLARIFICATION, UNRESOLVABLE, confidence below threshold, priority_p0, commitment/date in draft, restricted term, MLR-sensitive content, second WEAK from gate 5, dedupe/rate-limit conflict.

**Policy enforcement:** Code-level checks (quiet hours, rate limits, approved channels, dedupe) run in PreDeliver step. If policy forbids a `SEND_NOW`, the orchestrator downgrades to `HOLD_UNTIL` with policy reason. Agent reasons within policy; orchestrator enforces policy.

**Audit invariants:** Every state transition, agent invocation, HITL action, and policy check writes one `AuditRecord`. `read_chain(change_id)` reconstructs the full decision trail. Used by `/explain` (future prompt 11).
```

Also update the **"Current phase"** section to mark prompt 04 as done and list the orchestrator under "Orchestrator" (add a new section if not already present from the template).

Update the last-updated footer:
```
*Last updated: prompt 04 (orchestrator).*
*Next prompt: 05 — SignalScribe agent (first real LLM-backed agent, gates 1-3).*
```

### Step 10 — Update `design/planning/00-planning-index.md`

Mark prompt 04 done in both tables. Add an entry in Completed Artifacts:

```markdown
| N | Orchestrator | `src/pulsecraft/orchestrator/` + CLI | P3 | Deterministic workflow service with state machine, HITL queue, audit. Uses mock agents; real agents plug in via Protocols in prompts 05-07. |
```

### Step 11 — Verify

Run in order using venv binaries:

1. `.venv/bin/ruff check .` — passes
2. `.venv/bin/ruff format --check .` — passes
3. `.venv/bin/mypy src/pulsecraft/orchestrator/ src/pulsecraft/cli/` — passes
4. `.venv/bin/pytest tests/ -v` — all prior 84 tests pass; new orchestrator tests pass. Expect ~120-140 total tests.
5. Run the CLI smoke test: `.venv/bin/python -m pulsecraft run-change fixtures/changes/change_001_clearcut_communicate.json` — prints state transitions and terminates in `DELIVERED`.
6. Run the full fixture set through CLI (bash loop or a small test script) — each produces the expected terminal state.
7. Sanity-check audit output: `ls audit/` shows date-prefixed folders with JSONL files.

If any fails, fix before committing.

### Step 12 — Commit

```
feat(orchestrator): add deterministic workflow engine + mock agents (prompt 04)

Orchestrator (src/pulsecraft/orchestrator/):
- states.py — WorkflowState enum, TransitionRule, apply_transition
- agent_protocol.py — SignalScribe/BUAtlas/PushPilot Protocols (narrow interfaces)
- mock_agents.py — scripted mocks for testing (no LLM calls)
- audit.py — append-only JSONL writer + read_chain reconstruction
- hitl.py — file-based pending/approved/rejected queue
- engine.py — Orchestrator.run_change(artifact) main loop

CLI: `pulsecraft run-change <fixture>` — drive a fixture through the pipeline
with mock agents, print state transitions and decisions.

Tests:
- tests/unit/orchestrator/ — state machine, audit, HITL, mock agents
- tests/integration/orchestrator/ — every fixture through the pipeline,
  idempotency, audit chain reconstruction

State machine: RECEIVED → INTERPRETED → ROUTED → PERSONALIZED → [HITL?] →
SCHEDULED → DELIVERED, with branch-offs to ARCHIVED, HELD, DIGESTED,
REJECTED, FAILED.

Real agents (prompts 05-07) plug in via the Protocol interfaces; orchestrator
code does not change.

CLAUDE.md extended with Orchestrator section.

Next: prompt 05 — SignalScribe (first real LLM-backed agent, gates 1-3).
```

Do not push to remote unless the user asks.

## Rules for this session

- **No LLM calls anywhere.** If tempted to call the Anthropic SDK or the Claude Agent SDK in this prompt's code, stop — that's prompt 05.
- **No changes to schemas, config, or fixtures.** They're fixed contracts from prompts 02-03. If you notice a schema gap while implementing the orchestrator, flag it in the final report and suggest a follow-up prompt rather than edit in-place.
- **No async complexity unless strictly needed.** V1 orchestrator is synchronous. Fan-out can be a simple `for` loop.
- **No background threads, no workers, no daemons.** CLI command runs, completes, exits. The HITL queue is checked by operator commands (future prompt), not by a daemon.
- **Audit is not optional.** Every event writes audit. If a test passes but doesn't verify audit content, the test is incomplete.
- **Don't take shortcuts on idempotency.** If running the same fixture twice produces different non-timestamp output, something's wrong.
- **Never catch-and-swallow exceptions.** Any unexpected exception should propagate up, transition state to FAILED, write an error audit record, and exit cleanly. Silent failures are the worst bug in a workflow engine.

## Final report

1. **Files created/modified** — full tree with line counts.
2. **Schema additions (if any)** — if you added `PastEngagement`, `RecipientPreferences`, or `DeliveryDecision`, list them and flag for follow-up.
3. **Verification results** — each step pass/fail; total test count before/after.
4. **CLI smoke test output** — paste the output of running fixture 001 through the CLI.
5. **Fixture terminal-state results** — table showing each fixture and its observed terminal state when run through the orchestrator with scripted mocks.
6. **Commit hashes** — both commits.
7. **Any TODOs or design questions** flagged for follow-up.
8. **Next prompt** — "Ready for prompt 05: SignalScribe agent."

---

## [Post-commit] Save this prompt file to the repo

After the main commit lands, ask the user: **"Save this prompt file (prompt 04) to `prompts/04-orchestrator.md` as a commit archive? (yes/no)"**

If yes:
- Write the prompt verbatim to `prompts/04-orchestrator.md`.
- Commit with: `chore(prompts): archive prompt 04 (orchestrator) in repo`.

If no: skip.
