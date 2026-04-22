# CLAUDE.md — Standing Instructions for Claude Code Sessions

> This file is read automatically at the start of every Claude Code session in this repo.
> It is the single source of truth for how a session should behave.
> **If you are a Claude Code session reading this for the first time: read this file completely before taking any action.**

---

## About this project

**PulseCraft** is an AbbVie-internal AI service that turns marketplace product/feature changes into BU-ready, personalized notifications for BU leadership. It's implemented as a team of three specialist AI agents — **SignalScribe**, **BUAtlas**, **PushPilot** — each acting as decision-makers at six judgment gates, orchestrated by a deterministic Python service built on the Claude Agent SDK.

**Sponsor:** Head of AI, AbbVie.
**Status:** Planning complete; implementation in progress via prompt-driven development.

## Current phase

<!-- Every prompt that lands a commit updates this section. -->

**Phase:** P3 — Agent prompt authoring (in progress)

**Prompts completed:**
- ✅ 00 — Repo scaffold + Python project setup
- ✅ 01 — Commit planning documents (problem statement, ADRs, decision criteria, architecture)
- ✅ 02 — JSON schemas + Pydantic models for data contracts
- ✅ 03 — Config files (BU registry, profiles, policy, channel policy) + synthetic change fixtures
- ✅ 03.5 — Session continuity setup (CLAUDE.md, design docs, planning index)
- ✅ 03.6 — Repo hygiene (track untracked files, revert hello.py, sync CLAUDE.md + planning index)
- ✅ 04 — Deterministic orchestrator: state machine, agent Protocols, mock agents, audit writer, HITL queue, engine, CLI, 187 tests
- ✅ 05 — SignalScribe agent (gates 1, 2, 3) — real LLM-backed, Claude Sonnet 4.6
- ✅ 06 — BUAtlas agent (gates 4, 5) — parallel per-BU personalization, asyncio fan-out, FanoutFailure isolation
- ✅ 07 — PushPilot agent (gate 6) — delivery timing, agent-vs-code split, policy enforcement layer
- ✅ 07.7 — Demo reliability fix: BU pre-filter vocabulary expansion for fixture 001 determinism

**Prompts remaining:**
- ⏳ 08 — Skills: ingest adapters
- ⏳ 09 — Skills: registry, policy, audit
- ⏳ 10 — Skills: delivery rendering
- ⏳ 11 — Operator slash commands
- ⏳ 12 — Guardrail hooks
- ⏳ 13 — First end-to-end dryrun
- ⏳ 14 — Eval harness

## Where to find context

Before doing any non-trivial work, read these (in this order):

1. **`design/README.md`** — architecture overview, agent roles, key properties
2. **`design/planning/01-decision-criteria.md`** — the six-gate agent judgment spec. **This is the source of truth for every agent prompt.** If any prompt or piece of code disagrees with this document, this document wins.
3. **`design/planning/00-planning-index.md`** — current phase, open decisions, open questions, prompt-driven build status
4. **`design/00-problem-statement.md`** — scope, constraints, scale envelope, assumptions, risks
5. **`design/adr/ADR-001-workflow-with-subagents.md`** — the pattern decision (workflow + agentic subagents, not peer agents, not monolith)
6. **`design/adr/ADR-002-subagent-topology.md`** — fan-out strategy, component-to-primitive map, decision rubric

## Build process — prompt-driven development

All implementation happens via prompts in `prompts/`, run one at a time in Claude Code.

- Each prompt produces a specific set of files + a single commit.
- Prompts are numbered (`00-`, `01-`, ..., `14-`). Run in order unless told otherwise.
- Each prompt is **self-contained** — it includes its own pre-flight checks, step-by-step instructions, verification, commit message, and final report format.
- Prompts are archived in `prompts/` after they run, so the repo carries the full build trail.

**Do not invent steps that aren't in the prompt.** If a prompt doesn't specify something, ask the user rather than improvise.

## Environment rules

- **Python version:** 3.14 (may pin to 3.13 later if Claude Agent SDK compatibility surprises us)
- **Virtual environment:** `.venv/` at repo root, created via `uv venv`. No `pip` binary inside — use `uv pip install` or `.venv/bin/python -m pip` (after installing pip into the venv).
- **Always invoke tools via `.venv/bin/`** — `.venv/bin/python`, `.venv/bin/pytest`, `.venv/bin/ruff`, `.venv/bin/mypy`. Never rely on `source .venv/bin/activate` persisting between tool calls — shell state may reset.
- **`uv run <cmd>`** is an acceptable alternative; it handles activation.
- **Package manager:** `uv` preferred. Fall back to `.venv/bin/python -m pip` if `uv` is unavailable.

## Project conventions

- **No real AbbVie data.** No real product names, no real BU names (we use `bu_alpha` through `bu_zeta`), no real people (placeholders like `<head-alpha>`), no real internal system names. Real data lands via Track A discovery, not via Claude Code.
- **Placeholder pattern for unknowns:** use `<descriptor>` in angle brackets (e.g., `<head-alpha>`, `<delegate-1>`). Never invent realistic-sounding fake names.
- **Decision criteria is the source of truth.** For any agent behavior question, the answer comes from `design/planning/01-decision-criteria.md`. Do not encode conflicting rules elsewhere.
- **Schemas are invariant across agent iterations.** Agent prompts may change; data contracts (defined in `schemas/` and `src/pulsecraft/schemas/`) stay stable. If a schema change is genuinely needed, pause and ask rather than break the contract.
- **Snake case everywhere:** BU IDs (`bu_alpha`), file names (`change_001_*.json`), Python identifiers.
- **ISO-8601 UTC timestamps** everywhere. Never epoch seconds. Never local time.
- **No PII, PHI, or secrets** in any committed file — ever. This includes fixtures, examples, docstrings, test data.

## Commit conventions

- **Conventional commit prefixes:** `feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`.
- **Commit message body** explains what, why, and references which prompt produced it.
- **Co-author attribution** — if Claude Code made the commit, include a `Co-Authored-By: Claude ...` trailer.
- **One prompt = one feature commit + optionally one prompt-archive commit.** Don't batch unrelated work.
- **Never force-push. Never rebase shared branches. Never push to remote without the user asking.**

## Testing norms

- Every prompt that adds code adds tests.
- Tests use `.venv/bin/pytest` explicitly.
- Tests live under `tests/unit/` or `tests/integration/`.
- Fixtures live under `tests/fixtures/` (for unit test fixtures) or `fixtures/` (for shared domain fixtures like change artifacts).
- Don't silently weaken a test to make it pass. If a test is genuinely wrong, fix the test with a clear commit message. If the test is right and the code is wrong, fix the code.
- **Enum parity tests between JSON schema and Python `StrEnum` are deliberately strict.** If one fails, the schemas and Pydantic models have drifted — fix the drift, don't weaken the test.

## After every commit — MANDATORY updates

Every prompt that lands a commit must, as part of the same session:

1. Update the **"Current phase"** section of this `CLAUDE.md` — add the completed prompt to the ✅ list, update "in progress" marker.
2. Update **`design/planning/00-planning-index.md`** — mark the prompt as done in the phase table and the prompt-workflow table; add to the "Completed artifacts" section.
3. Update the root **`README.md`** — current phase indicator stays in sync.

If a prompt authors **skills**, list them in the Skills section of this file.
If a prompt authors **commands**, list them in the Commands section of this file.

## Skills authored so far

<!-- Populated as prompts 08–10 land. Each entry: name, purpose, location, producer prompt. -->

*(none yet — populated starting prompt 08)*

## Commands authored so far

<!-- Populated as prompt 11 lands. Each entry: command, purpose, file, producer prompt. -->

*(none yet — populated in prompt 11)*

## Agents authored so far

### SignalScribe (prompt 05)
- **Location:** `src/pulsecraft/agents/signalscribe.py`
- **Prompt:** `.claude/agents/signalscribe.md`
- **Owns gates:** 1, 2, 3
- **Protocol:** `SignalScribeProtocol` (see `orchestrator/agent_protocol.py`)
- **Model:** `claude-sonnet-4-6` via Anthropic API
- **Tools:** none yet (gate-3 clarification tools come in a future prompt)
- **Eval script:** `scripts/eval_signalscribe.py`

### BUAtlas (prompt 06)
- **Location:** `src/pulsecraft/agents/buatlas.py`
- **Fan-out:** `src/pulsecraft/agents/buatlas_fanout.py` (`buatlas_fanout` async, `buatlas_fanout_sync` wrapper)
- **Prompt:** `.claude/agents/buatlas.md`
- **Owns gates:** 4, 5
- **Protocol:** `BUAtlasProtocol` (see `orchestrator/agent_protocol.py`)
- **Model:** `claude-sonnet-4-6` via Anthropic API
- **Default bias:** ADJACENT (false positives are the single largest trust-erosion risk)
- **Eval script:** `scripts/eval_buatlas.py`

### PushPilot (prompt 07)
- **Location:** `src/pulsecraft/agents/pushpilot.py`
- **Prompt:** `.claude/agents/pushpilot.md`
- **Owns gates:** 6
- **Protocol:** `PushPilotProtocol` (see `orchestrator/agent_protocol.py`)
- **Model:** `claude-sonnet-4-6` via Anthropic API
- **Agent-vs-code split:** agent expresses unvarnished delivery preference; orchestrator enforces quiet hours, channel approval, rate limits via `_enforce_pushpilot_policy`
- **Eval script:** `scripts/eval_pushpilot.py`

## Hooks configured so far

<!-- Populated as prompt 12 lands. -->

*(none yet — populated in prompt 12)*

## Orchestrator

The orchestrator lives in `src/pulsecraft/orchestrator/`. It is the deterministic spine of PulseCraft — no LLM calls, all branching driven by agent outputs and policy config.

### Key modules

| Module | Purpose |
|---|---|
| `states.py` | `WorkflowState` StrEnum (12 states), `TERMINAL_STATES`, `_TRANSITIONS` dict, `apply_transition()` |
| `agent_protocol.py` | `SignalScribeProtocol`, `BUAtlasProtocol`, `PushPilotProtocol` — `@runtime_checkable` Protocols |
| `mock_agents.py` | `MockSignalScribe`, `MockBUAtlas`, `MockPushPilot` — scripted defaults, no LLM calls |
| `audit.py` | `AuditWriter` — append-only JSONL per `<root>/YYYY-MM-DD/<change_id>.jsonl` |
| `hitl.py` | `HITLQueue` — file-based HITL queue; `HITLReason` StrEnum (10 reasons) |
| `engine.py` | `Orchestrator.run_change()` — main pipeline; `RunResult` dataclass |

### State machine

States: `RECEIVED → INTERPRETED → ROUTED → PERSONALIZED → SCHEDULED → DELIVERED`

Terminal states: `DELIVERED`, `ARCHIVED`, `HELD`, `DIGESTED`, `REJECTED`, `FAILED`, `AWAITING_HITL`.

Transitions are defined in `_TRANSITIONS: dict[tuple[WorkflowState, str], WorkflowState]`. Calling `apply_transition()` with an undefined `(state, event)` pair raises `IllegalTransitionError`.

### Agent Protocol pattern

Real agents (prompts 05–07) and mock agents both satisfy the same `Protocol` interface. The orchestrator imports only Protocols — never concrete agent classes. This means agent implementations can change without touching the engine.

- `agent_name` attribute: uses `"_mock"` suffix for mocks (e.g., `"signalscribe_mock"`), so audit logs distinguish mock vs real.
- `Decision.agent.name`: must match schema pattern `^(signalscribe|buatlas|pushpilot)$`. Mock agents produce Decisions with canonical names.

### Orchestrator pipeline (run_change)

1. **RECEIVED** — accept artifact, write state-transition record
2. **SignalScribe** — gates 1+2+3: explicit decisions (ESCALATE, NEED_CLARIFICATION, HOLD, ARCHIVE) route to HITL/HELD/ARCHIVED *before* confidence check; confidence only checked on positive `COMMUNICATE+RIPE+READY` path
3. **BU routing** — `get_bu_registry()` → filter by `owned_product_areas ∩ impact_areas`; empty candidate set → FAILED
4. **BUAtlas fan-out** — parallel (currently sequential) per-BU personalization; `NOT_AFFECTED` BUs dropped
5. **HITL trigger evaluation** — ordered: priority_p0, second_weak_from_gate_5, confidence_below_threshold, agent_escalate, restricted_term / MLR_SENSITIVE / draft_has_commitment, dedupe_or_rate_limit_conflict
6. **PushPilot** — gate 6 per `worth_sending` BUs; `HOLD` decisions route to HELD; all DIGEST → DIGESTED; mix → DELIVERED
7. **Delivery** — mock delivery logs structlog event; real delivery via PushPilot skill (prompt 10)

### Audit writer

- **Never propagates exceptions** — audit is observability, not correctness. Write failures are logged via structlog only.
- `read_chain(change_id)` returns `list[AuditRecord]` sorted by timestamp, scanning all date-sharded files.
- `summary(change_id)` returns a human-readable string suitable for operator review.

### HITL queue

- Files live in `<root>/pending/`, `approved/`, `rejected/`, `archived/`.
- Every operation writes an `AuditRecord` to the audit chain.
- `edit()` and `answer_clarification()` modify the pending payload in place (safe — HITL files are single-writer under the orchestrator).

### CLI

```
pulsecraft <fixture_path> [--audit-dir <path>] [--queue-dir <path>]
```

Uses default mock agents. Prints Rich tables: state-transition audit chain, BU results, terminal state panel. Useful for local smoke testing of fixtures without any LLM calls.

### Failure modes specific to the orchestrator

- **`IllegalTransitionError`** → an event string was produced that doesn't have a transition defined from the current state. Check `_TRANSITIONS` in `states.py`.
- **`structlog TypeError: multiple values for argument 'event'`** → `logger.info()` first positional arg IS the `event` field. Never pass `event=...` as a kwarg. Rename to `trigger=` or similar.
- **BU not in candidate set** → the mock `impact_areas` don't overlap with any BU's `owned_product_areas`. Check `config/bu_registry.yaml` and the mock's default `impact_areas`.
- **HITL reason mismatch** → explicit agent decisions (ESCALATE, HOLD, etc.) must be checked *before* the confidence threshold check. See `engine.py:_run()` step 2.

## Common failure modes and fixes

- **`ModuleNotFoundError: No module named 'pulsecraft'`** → you're running system `pytest` instead of venv. Use `.venv/bin/pytest`.
- **`No module named pip` in venv** → venv was created by `uv`, which omits pip. Use `uv pip install <pkg>` instead of `pip install`.
- **`pytest-asyncio` DeprecationWarning about event loop policy** → harmless, from pytest-asyncio internals. Ignore.
- **Python 3.14 compatibility issue with an LLM SDK** → pin to 3.13 via `uv venv --python 3.13` and rebuild venv. Flag to user before doing this.
- **Schema/Pydantic drift** (enum parity test fails) → one side was edited without the other. Align both and verify round-trip tests pass.

## What Claude Code should NOT do in this repo

- **Do not push to remote** unless the user explicitly asks.
- **Do not create branches.** Work on the current branch.
- **Do not invent design decisions.** If a prompt is ambiguous, ask the user.
- **Do not add `metadata: {}` escape-hatch fields to schemas.** If a shape is unknown, use a named sub-object with a TODO.
- **Do not add realistic-sounding fake names** (e.g., "John Smith"). Use explicit placeholders (`<head-alpha>`).
- **Do not commit real AbbVie data of any kind** — names, system IDs, product names, internal URLs.
- **Do not skip verification steps** even when everything seems fine. The verification steps catch the subtle bugs.
- **Do not batch work across multiple prompts in one commit.** One prompt = one feature commit.
- **Do not silently work around SDK installation failures.** If `claude-agent-sdk` won't install, stop and ask.

## When in doubt

1. Re-read this file.
2. Re-read `design/planning/01-decision-criteria.md` if the question is about agent behavior.
3. Re-read `design/adr/ADR-002-subagent-topology.md` if the question is about where work belongs (subagent vs. skill vs. code).
4. Ask the user. Never guess on architecture.

---

*Last updated: prompt 07.7 (demo reliability fix — expanded bu_alpha owned_product_areas to align with SignalScribe's observed impact_areas vocabulary; fixture 001 now deterministically reaches AWAITING_HITL).*
*Next prompt: 08 — Skills: ingest adapters.*
