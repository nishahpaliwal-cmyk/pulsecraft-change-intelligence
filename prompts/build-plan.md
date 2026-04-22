# PulseCraft — Build Plan

> **Purpose of this document.** A single-page view of the whole build from here to a working walking skeleton. Read this if you've lost track of where we are, what's left, and why the remaining prompts are shaped the way they are.

---

## The one-sentence summary

We are building a **team of three specialist AI agents** (SignalScribe, BUAtlas, PushPilot) + a **deterministic orchestrator** (Python) that together turn marketplace product changes into BU-ready notifications, using **Claude Code with the Claude Agent SDK** as the runtime, in an **explicitly prompt-driven build process** where every piece of code is authored by a numbered Claude Code prompt run one at a time.

---

## Where you are right now

**Phase:** Active implementation, roughly 30% through the build.

**What exists in the repo:**

- Scaffold: Python project (pyproject, venv, 37+84=84 tests passing), directory layout, .claude/ config stubs
- Design docs: problem statement, two ADRs, decision criteria (the six-gate judgment spec), architecture diagram, planning index
- Data contracts: 7 JSON schemas + matching Pydantic models, with decision-trail arrays on every agent output, enum-parity and round-trip tests
- Config + fixtures: 6 synthetic BUs, matching profiles, policy config, channel policy, loader module, 8 synthetic change artifacts covering every decision-verb scenario
- Session continuity: CLAUDE.md with standing instructions (being authored right now in prompt 03.5)

**What does not exist yet:**

- The agents themselves (no prompts for SignalScribe, BUAtlas, or PushPilot)
- The orchestrator (no state machine, no agent invocation logic, no HITL queue)
- The skills (no ingest adapters, no registry lookup, no rendering, no delivery)
- The operator commands (no `/ingest`, no `/approve`, no `/explain`)
- The guardrail hooks (no PII redaction, no policy enforcement at runtime)
- Any end-to-end run — nothing actually works yet; we're building the skeleton

---

## The arc — 11 phases, mapped to prompts

The build has **11 remaining prompts** (04 through 14). Each is scoped to one Claude Code session, 30 minutes to 2 hours. After each prompt, the repo is in a better state and you can stop cleanly.

### Where we've been

| Prompt | Delivered | Lines of code (approx) |
|---|---|---|
| 00 | Scaffold + Python project | 200 (config files) |
| 01 | Planning docs | 1500 (all markdown) |
| 02 | Schemas + Pydantic models | 1200 (schemas + tests) |
| 03 | Config + 8 fixtures + loader | 1500 (yaml + python + tests) |
| 03.5 | Session continuity (CLAUDE.md) | 300 (markdown) |

### The foundation layer (prompts 04, 05, 06, 07)

These four prompts author the **orchestrator and the three agents**. This is the core of the system. After these, we have all the "brains" — what's missing is the plumbing.

| Prompt | Delivers | What the repo can do after |
|---|---|---|
| **04 — Orchestrator** | `src/pulsecraft/orchestrator/` — state machine (RECEIVED → INTERPRETED → ROUTED → PERSONALIZED → HITL → SCHEDULED → DELIVERED), agent invocation sequencing, decision-verb handling, HITL queue management, audit writes. Extends CLAUDE.md with "Orchestrator" section. | Drive a change artifact through the state machine with *stub* agents that return hardcoded decisions. Verify audit trail, state transitions, HITL routing. |
| **05 — SignalScribe** | `.claude/agents/signalscribe.md` — the actual LLM prompt for Agent 1 implementing gates 1, 2, 3. Derived from decision criteria doc. Plus a Python wrapper that invokes it via the SDK. | Run real SignalScribe against fixture 001, 002, 003, 004, 005. Verify ChangeBrief output matches schema, decisions[] array populated correctly, confidence calibrated. |
| **06 — BUAtlas** | `.claude/agents/buatlas.md` — Agent 2 prompt for gates 4, 5. Parallel per-BU wrapper. | Run SignalScribe → parallel BUAtlas per candidate BU. Verify fixture 006 produces AFFECTED for one BU, ADJACENT for another. |
| **07 — PushPilot** | `.claude/agents/pushpilot.md` — Agent 3 prompt for gate 6. | Full three-agent pipeline runnable end-to-end with a fixture. Agent reasoning visible in the audit log. |

**After prompt 07, you have a runnable agent pipeline.** But the plumbing is still missing — no real ingest (we're using pre-authored fixtures), no real delivery (we just print what would be sent), no policy enforcement at runtime, no operator UX.

### The plumbing layer (prompts 08, 09, 10, 11, 12)

These wire the agents into something operationally sound. Each prompt focuses on one category of plumbing.

| Prompt | Delivers | Why it's a separate prompt |
|---|---|---|
| **08 — Ingest skills** | 5 fetch adapters (release-note, work-item, doc, feature-flag, incident) + normalizer that produces ChangeArtifact. Webhook + poll handlers. | Each source type has distinct shape; keeping adapters in one prompt means consistent error handling, retry logic, and normalization. |
| **09 — Registry, policy, audit skills** | `lookup-bu-registry`, `check-policy`, `compute-dedupe-key`, `write-audit` skills. | These are cross-cutting; they're called from orchestrator, agents, and hooks. Building them together keeps them consistent. |
| **10 — Delivery skills** | `render-teams-card`, `render-email`, `render-push`, `schedule-send`, `send-teams`, `send-email`. Per-channel adapters. | Channel-specific; isolating keeps per-channel bugs per-channel. |
| **11 — Operator commands** | Slash commands: `/ingest`, `/dryrun`, `/approve`, `/reject`, `/edit`, `/answer`, `/replay`, `/pending`, `/digest`, `/audit`, `/metrics`, `/explain`. Typer-based CLI. | These are the human interface — authored once, after agents + skills exist, so we know what they need to call. |
| **12 — Guardrail hooks** | `.claude/settings.json` populated: PreIngest (PII redaction), PostAgent (schema + confidence validation), PreDeliver (quiet hours, rate limits, approved channels, dedupe), Audit hook. | Hooks reference skills from 08-10 + agents from 05-07. Last piece before dryrun. |

**After prompt 12, the system is functionally complete.** Every piece exists. But we haven't actually run it end-to-end with real data yet — just unit tests of each piece.

### The proving layer (prompts 13, 14)

| Prompt | Delivers | Significance |
|---|---|---|
| **13 — First end-to-end dryrun** | A single fixture (say, change_001) run through the full pipeline with real LLM calls. Audit log examined. Decision chain produced via `/explain`. Any surprises fixed. Add integration test. | **The moment of truth.** Does the whole thing work? Usually this prompt surfaces 2-5 bugs that no unit test caught. |
| **14 — Eval harness** | Fixture-based eval assertions: for each of the 8 fixtures, the expected decision chain is encoded, and the eval runs the fixture through the real pipeline and asserts correctness. Plus metrics (coverage, latency, cost, token counts). | **Ongoing quality.** From here, any prompt change or agent tweak runs through the eval harness before merge. This is what lets us iterate safely. |

---

## What you'll have at the end

A repo that, when a fresh change artifact is dropped into it, will:

1. **Ingest** it via webhook or manual `/ingest`
2. **Interpret** it via SignalScribe, producing a ChangeBrief with a decision trail — or archiving, holding, or escalating with reasons
3. **Route** it to candidate BUs via deterministic registry lookup
4. **Personalize** it per BU via parallel BUAtlas invocations — deciding AFFECTED vs. ADJACENT vs. NOT_AFFECTED, and for affected BUs, whether the draft is WORTH_SENDING
5. **Queue** for HITL review if confidence is low, priority is P0, or policy flags fire
6. **Deliver** via approved channels at the right time — or hold for quiet hours, digest for awareness-only items
7. **Audit** every decision with its reason, replayable via `/explain <change-id>`

All running on your laptop against synthetic fixtures. Zero dependency on real AbbVie systems yet — those integrations come later, after the pattern is validated.

---

## What's deliberately *not* in scope

Worth naming explicitly so you don't think we're hiding anything:

- **Real AbbVie integrations.** Veeva, ServiceNow, actual Teams tenancy, actual email relays — these are Track A / enterprise-onboarding items. The code has adapter stubs; wiring up real endpoints happens later, outside this prompt sequence.
- **Production deployment.** We're building something you run locally via Claude Code + CLI. Containerization, CI/CD, cloud tenancy (Bedrock vs. Azure AI Foundry) — separate body of work, after validation.
- **Real BU data.** Real registry, real profiles, real HITL operators. Those need Track A discovery + onboarding. Our synthetic BUs (bu_alpha through bu_zeta) are drop-in replacements until real data arrives.
- **GitHub Pages site.** Explicitly deferred until after the walking skeleton works. Pretty docs come after working code.
- **ADR-003 (validation posture) and ADR-004 (LLM runtime).** These need Legal/Compliance and EA/CloudOps decisions from AbbVie — not blocking the build.

---

## Where the real risks are

Not all prompts are equal. Most are straightforward; a few are where things genuinely could go sideways.

**Low risk (mechanical work):** 00, 01, 02, 03, 03.5, 08, 10, 11. Schema work, config work, rendering skills, commands. Well-specified, Claude Code does them cleanly.

**Medium risk (integration points):** 04, 09, 12. Orchestrator state machine has edge cases around HITL and retries. Cross-cutting skills need consistent behavior across callers. Hooks are where policy meets runtime — must not have false negatives on sensitive content.

**High risk (agent quality):** 05, 06, 07, 13, 14.

- **Prompt 05 (SignalScribe)** is the first place LLM quality directly determines whether the system works. Bad prompt → bad ChangeBriefs → everything downstream is garbage. Expect to iterate on this prompt 2-3 times against fixtures before it's reliable.
- **Prompt 06 (BUAtlas)** is the quality gate for recipient experience. False positives (messaging an adjacent BU as if affected) are exactly what erodes trust. Gate 4 precision is load-bearing.
- **Prompt 13 (first dryrun)** surfaces bugs that unit tests can't — interaction effects between agents, schema validation failures under weird real-world inputs, LLM outputs that technically pass schema but are semantically wrong.

**The strongest mitigation we have:** the fixtures from prompt 03 are specifically designed so that every decision verb is exercisable. If SignalScribe can't correctly archive fixture 002 (pure internal refactor), we'll catch it before anyone real sees it.

---

## Decision points ahead

Things I'll need input on when we get there:

| When | Decision | Why |
|---|---|---|
| Prompt 05 | Confidence threshold numeric values (e.g., gate 1 COMMUNICATE at 0.75, ARCHIVE at 0.6) | These are in policy.yaml now as guesses; after prompt 05's first eval run, tune them. |
| Prompt 07 | Keep PushPilot as agent, or downgrade to tool-call? | If gate 6 reasoning turns out to be essentially single-turn lookup, agent is overkill. Decide based on prompt 05/06 patterns. |
| Prompt 09 | How `write-audit` handles storage (file-per-change? append-only JSONL? SQLite?) | Simple is fine for v1 walking skeleton; affects `/audit` and `/explain` performance later. |
| Prompt 12 | MLR review trigger sensitivity | The restricted_terms list in policy.yaml needs a real comms/MLR reviewer eventually; we pick conservatively for now. |
| Prompt 13 | Whether to pin Python to 3.13 | If 3.14 surfaces SDK incompatibilities during the real LLM run, we downgrade. |

None of these are blocking right now. Flagged so you see what conversations are coming.

---

## Time estimate to walking skeleton

Rough sizing. Each prompt includes Claude Code session time + your review time + any iteration.

| Prompt range | Elapsed time |
|---|---|
| 04 (orchestrator) | 2 hours |
| 05-07 (three agents) | 4-6 hours total, includes 1-2 iterations per agent against fixtures |
| 08-10 (plumbing skills) | 3 hours total |
| 11 (commands) | 1 hour |
| 12 (hooks) | 1 hour |
| 13 (dryrun + fixes) | 2-4 hours (the range reflects how many bugs surface) |
| 14 (evals) | 2 hours |

**Total: roughly 15-20 hours of focused work** to a working walking skeleton from where we are now. That's 2-4 days of real calendar time if you do it in focused blocks, or a couple weeks if you're fitting it around other work.

---

## A note on what's different from typical software builds

You might be feeling disoriented because this build has unusual properties compared to normal software projects:

1. **The hardest prompts are the shortest to author, and the longest to get right.** SignalScribe's prompt might be 500 words; iterating it against fixtures until it's reliable might take 3 sessions.
2. **Data contracts came before behavior.** In normal builds, you'd write the code and let schemas emerge. We wrote schemas first, which means agents *must* conform. This is intentional — contracts survive prompt iterations; agents don't.
3. **Every piece is testable in isolation before integration.** Normal builds integrate early and find problems in integration. This build tests each layer independently (schemas → config → agents → skills → orchestrator → end-to-end) so integration issues are rare by the time we hit prompt 13.
4. **The design docs are real work, not ceremony.** The decision criteria document *is* the source of truth for agent prompts. Changing an agent means changing that doc first, regenerating the prompt, re-evaling. This is slower than cowboy-coding but catches drift early.

---

## What to do right now

1. Finish prompt 03.5 (session continuity — CLAUDE.md creation).
2. Confirm commits and tests pass.
3. Run prompt 04 (orchestrator). This is a big one but still mechanical.
4. Then you can pause, take stock, and decide whether to continue with 05-07 (the agents, where quality begins to matter) in one push or spread across sessions.

---

## If you get lost again

Read `CLAUDE.md` at the repo root. It has the current-phase tracker updated on every commit. Read this document (`design/build-plan.md` — I can commit it via the next prompt if you want) for the arc. Ask me if the plan needs adjustment.

Plans are not sacred. If partway through prompt 07 you realize a phase should have gone differently, we re-plan. This doc will be wrong in some places by prompt 14 and that's expected.

---

*This document written at prompt 03.5, when the user asked for a panoramic view of the remaining work. Not a commitment to run every prompt exactly as described — it's the honest current best plan, subject to learning.*
