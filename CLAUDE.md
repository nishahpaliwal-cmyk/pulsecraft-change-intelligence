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
- ✅ 08 — Skills: ingest adapters (5 adapters + normalizer + redaction + CLI restructure, 390 tests)
- ✅ 09 — Skills: registry, policy, dedupe, audit, past_engagement (extracted from engine.py, 442 tests)
- ✅ 10 — Skills: delivery rendering (render + send + schedule, 4 renderers, 3 send adapters, 1 scheduler, dedupe audit fix, 495 tests)
- ✅ 11 — Operator slash commands (11 subcommands incl. /explain decision trail, CLI refactor, explain_chain skill, 545 tests)
- ✅ 11.5 — Explain scoping fix: /explain scoped to latest run by default, run-boundary detection, --run/--all/--list-runs flags, cost wired to audit records, 557 tests
- ✅ 12 — Guardrail hooks: pre_ingest, post_agent, pre_deliver, audit_hook; HookContext/HookResult base types; config loader; 5 engine lifecycle call sites; 43 new tests (600 total)
- ✅ 13 — First end-to-end dryrun: all 8 fixtures with real agents, 2 bugs fixed (HOLD_INDEFINITE routing verb; mixed-decision confidence semantics), dryrun report in design/dryrun/, 606 tests
- ✅ 14 — Eval harness: per-agent variance-aware eval, 15 cases × 3 agents, classifier + runner + reporter + aggregator, baseline report (stable=10/acceptable=1/unstable=1, PASS), 619 tests
- ✅ 14.5 — README overhaul (publication-quality front door for the repo)

**Prompts remaining:**
- *(none — P3 build sequence complete)*

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

### Ingest skills (prompt 08)
Location: `src/pulsecraft/skills/ingest/`

| Skill | Purpose |
|---|---|
| `fetch_release_note` | Fetch + normalize release note → ChangeArtifact |
| `fetch_work_item` | Fetch + normalize Jira/ADO work item → ChangeArtifact |
| `fetch_doc` | Fetch + normalize document → ChangeArtifact |
| `fetch_feature_flag` | Fetch + normalize feature flag → ChangeArtifact |
| `fetch_incident` | Fetch + normalize incident → ChangeArtifact |
| `normalize_to_change_artifact` | Shared normalization + validation layer |
| `redact` | Regex-based PII/credential scrub (belt-and-suspenders; full guardrail in prompt 12) |

Each adapter accepts an optional `transport: Callable[[str], dict] | None` parameter. When `None`, reads from `fixtures/sources/<type>/<ref>.json` (dev mode). Errors: `IngestNotFound`, `IngestUnauthorized`, `IngestMalformed`.

### Registry / policy / audit skills (prompt 09)
Location: `src/pulsecraft/skills/`

| Skill | Purpose | Inputs |
|---|---|---|
| `lookup_bu_candidates` | BU pre-filter: intersect ChangeBrief.impact_areas with registry (exact owned_product_areas match) | ChangeBrief, BURegistry |
| `check_confidence_threshold` | Compare a Decision's confidence against the policy threshold for its gate+verb | Decision, Policy |
| `check_restricted_terms` | Scan text for commitment/MLR/sensitive-data phrases; returns list of RestrictedTermHit | str, Policy |
| `evaluate_hitl_triggers` | Aggregate all HITL triggers across PersonalizedBriefs; returns list of HITLTrigger (empty = no triggers) | dict[str,PersonalizedBrief], Policy |
| `compute_dedupe_key` | Deterministic SHA-256 hash for (change_id, bu_id, recipient_id, variant_id) | 4 strings |
| `has_recent_duplicate` | Scan DELIVERY_ATTEMPT audit records for matching dedupe_key within window | dedupe_key, AuditReader, window_hours |
| `write_audit` | Thin wrapper over AuditWriter.log_event for use in hooks/commands | AuditRecord, AuditWriter |
| `lookup_past_engagement` | Reconstruct PastEngagement from DELIVERY_ATTEMPT audit history for a BU | bu_id, recipient_id, AuditReader |

Called from: orchestrator (engine.py), hooks (prompt 12), operator commands (prompt 11).

New types: `RestrictedTermHit` and `HITLTrigger` (dataclasses in `skills/policy.py`).
`AuditReader` Protocol defined in `orchestrator/audit.py`; `AuditWriter` satisfies it.

### Delivery skills (prompt 10)
Location: `src/pulsecraft/skills/delivery/`

| Skill | Purpose | Inputs → Output |
|---|---|---|
| `render_teams_card` | Render Adaptive Card v1.5 JSON for Teams channel | PersonalizedBrief, BUProfile → TeamsCardPayload |
| `render_email` | Render plain-text + HTML email with subject | PersonalizedBrief, BUProfile → EmailPayload |
| `render_push` | Render short push notification (title ≤65, body ≤240) | PersonalizedBrief, BUProfile → PushPayload |
| `render_portal_digest` | Render combined Markdown digest for multiple briefs | list[PersonalizedBrief], BUProfile → DigestPayload |
| `send_teams` | Dev-mode send (writes JSON file) or injectable transport | TeamsCardPayload, recipient, transport? → DeliveryResult |
| `send_email` | Dev-mode send or injectable transport | EmailPayload, recipient, transport? → DeliveryResult |
| `send_push` | Dev-mode send or injectable transport | PushPayload, recipient, transport? → DeliveryResult |
| `schedule_send` | Compute send_at for SEND_NOW / HOLD_UNTIL / DIGEST | DeliveryDecision, channel, scheduled_time, tz → ScheduledDelivery |

Templates: `templates/*.j2` (teams_card.j2, email.txt.j2, email.html.j2, push.j2, portal_digest.md.j2)
New schemas: `delivery_payloads.py` — TeamsCardPayload, EmailPayload, PushPayload, DigestPayload, DeliveryResult, ScheduledDelivery
Errors: `DeliveryFailed`, `DeliveryRetriable`, `DeliveryUnauthorized` (in send_teams.py, re-exported from `__init__.py`)
Dedupe audit fix: `AuditRecord.dedupe_key` field added; `has_recent_duplicate` now queries `r.dedupe_key`; `_execute_delivery` populates it.
New state transition: `(SCHEDULED, "dedupe_conflict") → AWAITING_HITL`

## Commands authored so far

<!-- Populated as prompt 11 lands. Each entry: command, purpose, file, producer prompt. -->

### CLI subcommands (prompt 11)
CLI root: `src/pulsecraft/cli/` — refactored into `commands/` with one module per command.

| Command | Module | Purpose |
|---|---|---|
| `run-change` | `commands/run_change.py` | Run a fixture through the full mock pipeline |
| `ingest` | `commands/ingest.py` | Ingest a source artifact into ChangeArtifact form |
| `dryrun` | `commands/dryrun.py` | Preview pipeline decisions without side effects |
| `approve` | `commands/approve.py` | Approve a HITL-pending change |
| `reject` | `commands/reject.py` | Reject a HITL-pending change |
| `edit` | `commands/edit.py` | Edit the pending payload of a HITL item |
| `answer` | `commands/answer.py` | Answer gate-3 clarification questions |
| `replay` | `commands/replay.py` | Re-run a completed change through the pipeline |
| `pending` | `commands/pending.py` | List pending HITL queue items |
| `digest` | `commands/digest.py` | Dispatch digest items that are due |
| `audit` | `commands/audit.py` | Show full audit chain for a change_id (`--list` for all IDs) |
| `metrics` | `commands/metrics.py` | Aggregate pipeline metrics over a time window |
| `explain` | `commands/explain.py` | Human-readable decision trail for a change_id (demo-day command) |

**Supporting skills:**
- `explain_chain` skill: `src/pulsecraft/skills/explain_chain.py` — builds `Explanation` dataclass from audit chain; classifies records into AgentDecisionEvent, HITLEvent, DeliveryEvent, StateTransitionEvent.
- `resolve_change_id`: `src/pulsecraft/cli/common.py` — resolves 8-char prefix to full UUID by scanning audit JSONL filenames.

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

### Guardrail hooks (prompt 12)
Location: `src/pulsecraft/hooks/`

| Hook | Module | Fail mode | Stage | Purpose |
|---|---|---|---|---|
| `pre_ingest` | `pulsecraft.hooks.pre_ingest` | closed | Before SignalScribe | Redact PII/credentials in raw_text; fail if not a string |
| `post_agent` | `pulsecraft.hooks.post_agent` | closed | After each agent | Check confidence thresholds (positive verbs only) + restricted terms in message_text |
| `pre_deliver` | `pulsecraft.hooks.pre_deliver` | closed | Before each delivery | Enforce quiet hours + channel approval |
| `audit` | `pulsecraft.hooks.audit_hook` | open | Written by engine via `_write_hook_fired` | HOOK_FIRED AuditRecord per hook invocation; fail-open always |

**Key design decisions:**
- `fail="closed"` + hook failure → pipeline transitions via `"error"` event → FAILED
- Confidence check in `post_agent` skips ESCALATE/NEED_CLARIFICATION/UNRESOLVABLE/ARCHIVE — intentional routing decisions, not policy violations
- BUAtlas post_agent receives `message_text=""` — MLR/restricted-term detection in drafts is owned by HITL trigger evaluation (step 5), not the hook
- Hook modules are lazy-loaded and cached in `_hook_modules` on the Orchestrator
- `audit_hook.py` exists as a standalone module but `_write_hook_fired` writes records directly to avoid recursion
- `pre_deliver.py` replicates quiet-hours logic locally to avoid circular imports with `engine.py`

Registrations live in `.claude/settings.json`.

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

## Dryrun artifacts (prompt 13)

Report: `design/dryrun/2026-04-23-dryrun-report.md`

All 8 fixtures ran with real agents (claude-sonnet-4-6). Two bugs were found and fixed:

1. **`HOLD_INDEFINITE` missing from `_ROUTING_VERBS`** (`post_agent.py`) — routing decisions must not trigger confidence checks.
2. **Mixed decision set `[COMMUNICATE, HOLD_INDEFINITE]` still failed** — fix: if ANY decision in the set is a routing verb, skip ALL confidence checks. The routing decision is itself the safeguard.

Key observation: `post_agent` confidence checks should only fire when the agent is on the positive commit path (all decisions are actionable verbs). If the agent self-routes, the confidence of earlier gates is irrelevant.

## Eval harness (prompt 14)

Location: `src/pulsecraft/eval/`

| Module | Purpose |
|---|---|
| `expectations.py` | 15 `ExpectedOutcome` entries (8 SS, 4 BA, 3 PP) with expected/acceptable/false_positive verb sets |
| `classifier.py` | Asymmetric 5-tier: `false_positive_risk > mismatch > unstable > acceptable_variance > stable` |
| `runner.py` | Per-agent isolated runners: BA setup = SS once; PP setup = SS+BA once; target runs N times |
| `reporter.py` | Per-agent `report_{agent}.md` + `summary_{agent}.json` |
| `aggregator.py` | Grand-total `aggregate.md` + `aggregate.json` with pass criteria |

Entry points: `scripts/eval/run_signalscribe.py`, `run_buatlas.py`, `run_pushpilot.py`, `run_all.py`

Pytest integration: `tests/eval/test_agent_evals.py` — opt-in via `PULSECRAFT_RUN_EVAL_TESTS=1`; `@pytest.mark.eval`

Baseline report: `audit/eval/2026-04-23-baseline/` — stable=10 / acceptable=1 / unstable=1 / skipped=3 / PASS ($1.741, 26.9 min)

Notable baseline observations:
- SS 007_mlr_sensitive: unstable (READY 2/3, NEED_CLARIFICATION 1/3) — MLR boundary fixture, expected variance
- SS 003_ambiguous_escalate: acceptable_variance (ARCHIVE 2/3, ESCALATE 1/3) — designed-ambiguous, ARCHIVE defensible
- BUAtlas 006 bu_zeta + bu_delta, PushPilot 006 bu_zeta: skipped — fixture 006 impact_areas don't overlap those BUs

Pass gate: 0 `false_positive_risk` + 0 `mismatch` = PASS. False positives are asymmetrically penalized because unwanted notifications erode BU trust faster than holding back.

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

*Last updated: prompt 14.5 (README overhaul — 854-line publication-quality README with SVG architecture diagram, decision guides, use cases table, comparison table, roadmap; all metrics grounded in repo artifacts).*
*P3 build sequence complete. No further prompts planned.*
