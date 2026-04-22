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

**Prompts remaining:**
- ⏳ 04 — CLAUDE.md orchestrator spec (extends this file with orchestrator section)
- ⏳ 05 — Agent: SignalScribe (gates 1, 2, 3)
- ⏳ 06 — Agent: BUAtlas (gates 4, 5, parallel per-BU)
- ⏳ 07 — Agent: PushPilot (gate 6)
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

<!-- Populated as prompts 05–07 land. -->

*(none yet — populated starting prompt 05)*

## Hooks configured so far

<!-- Populated as prompt 12 lands. -->

*(none yet — populated in prompt 12)*

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

*Last updated: prompt 03.6 (repo hygiene — tracked architecture diagrams, prompt archives, build plan).*
*Next prompt: 04 — orchestrator spec (will extend this file with an "Orchestrator" section).*
