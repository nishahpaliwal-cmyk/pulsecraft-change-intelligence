# Prompt 06 — BUAtlas (Second Real Agent, Parallel Per-BU)

> **Character note.** Like SignalScribe, BUAtlas is LLM-backed — quality is judged against the decision criteria, not just schema validation. Unlike SignalScribe, BUAtlas runs **in parallel per BU** via `asyncio.gather`. Orchestrator code from prompt 04 already expects this fan-out; your job here is to make it real.
>
> **Lesson carried from prompt 05.** LLM outputs vary run-to-run on ambiguous inputs. The eval in this prompt uses **variance-aware matching** — expected *terminal category* (affected / adjacent / not_affected / weak / not_worth), not exact verb. Multiple runs per fixture to measure stability.
>
> **How to use this prompt.**
> 1. Ensure `ANTHROPIC_API_KEY` is still set.
> 2. Paste below the `---` line into Claude Code.
> 3. Claude Code builds BUAtlas, runs it against multi-BU fixtures, produces eval report, commits.
>
> **Expected duration:** 2–3 hours. First agent to run LLM calls in parallel.
>
> **Prerequisite:** Prompts 00–05 done. SignalScribe working (6/8 eval or better). Orchestrator expects a `BUAtlasProtocol`-compliant implementation.
>
> **Budget note:** Expect $1–3 in API costs. BUAtlas runs once per candidate BU per change, so a fixture matching 3 BUs = 3 invocations. Across 8 fixtures × avg 2-3 BUs each × 3 runs per fixture for variance = ~60 invocations. Stop if you hit $8.

---

# Instructions for Claude Code

You are authoring **BUAtlas** — the second real LLM-backed agent. It owns gates 4 (*is this BU actually affected?*) and 5 (*is the drafted message worth this BU head's attention?*) from `design/planning/01-decision-criteria.md`. It runs once per candidate BU in parallel, with isolated context per invocation.

## Environment discipline

Use `.venv/bin/python`, `.venv/bin/pytest`, `.venv/bin/ruff`, `.venv/bin/mypy` explicitly. `uv run <cmd>` is acceptable.

## Context to read before starting

1. **`design/planning/01-decision-criteria.md`** — Gate 4 and Gate 5 sections in full, including all "signals that favor" lists, failure modes, confidence calibration. Critical reading.
2. **`.claude/agents/signalscribe.md`** — the pattern to mirror. BUAtlas's prompt should feel like a sibling to SignalScribe's in structure and tone.
3. **`src/pulsecraft/agents/signalscribe.py`** — the implementation pattern to mirror (prompt loading, retries, validation, error handling).
4. **`src/pulsecraft/schemas/personalized_brief.py`** — the output contract. BUAtlas produces one per (change, BU) pair.
5. **`src/pulsecraft/schemas/bu_profile.py`** — the input contract for BU context.
6. **`src/pulsecraft/orchestrator/agent_protocol.py`** — `BUAtlasProtocol` interface.
7. **`src/pulsecraft/orchestrator/mock_agents.py`** — `MockBUAtlas` for the Protocol shape reference.
8. **`src/pulsecraft/orchestrator/engine.py`** — specifically how it fans out to BUAtlas; understand the interface already expected.
9. **`config/bu_profiles.yaml`** + **`config/bu_registry.yaml`** — the BU context that gets passed in.
10. **Fixtures 001 (single BU affected), 006 (multi-BU affected vs adjacent), 008 (post-hoc)** — primary fixtures that exercise BUAtlas.

If anything in this prompt contradicts the decision criteria doc, the decision criteria wins.

## What "done" looks like

When you finish:

1. `.claude/agents/buatlas.md` — canonical system prompt (400–700 lines). Mirrors gate 4 and gate 5 from the decision criteria verbatim.
2. `src/pulsecraft/agents/buatlas.py` — `BUAtlas` class satisfying `BUAtlasProtocol`. Calls Sonnet 4.6 via Anthropic API. Single-BU invocation. The *parallelism* happens at the orchestrator layer, not inside BUAtlas itself.
3. `src/pulsecraft/agents/buatlas_fanout.py` — an async wrapper that takes a `ChangeBrief` + list of candidate `BUProfile`s, invokes `BUAtlas` in parallel (`asyncio.gather`), returns a list of `PersonalizedBrief`s. Each invocation has an isolated `BUAtlas` instance / isolated context. Handles per-invocation failures gracefully (one BU failing doesn't kill the whole fan-out — its PersonalizedBrief becomes a failure marker the orchestrator handles).
4. Orchestrator (`engine.py`) updated to use `buatlas_fanout` when `--real-buatlas` is passed. Default still uses `MockBUAtlas`.
5. Tests:
   - `tests/unit/agents/test_buatlas_unit.py` — mocked client, contract adherence, error handling, isolation invariants
   - `tests/unit/agents/test_buatlas_fanout_unit.py` — parallelism correctness, failure isolation, per-BU result ordering
   - `tests/integration/agents/test_buatlas_integration.py` — real API, marked `@pytest.mark.llm`, parametrized over multi-BU fixtures
6. Eval script: `scripts/eval_buatlas.py` — variance-aware. Runs each fixture N=3 times, reports per-BU terminal category distribution, flags instabilities.
7. CLAUDE.md updated with BUAtlas under "Agents authored so far." Current phase updated. Last-updated footer updated.
8. Planning index updated.
9. One feature commit + optional archive commit.
10. All prior tests still pass. Unit tests pass. Integration tests run cleanly under flag.

## Pre-flight checks

1. `git status` clean (or warn).
2. `.venv/bin/pytest tests/ -q -m "not llm"` shows ~200 passing (from prompt 05).
3. `ANTHROPIC_API_KEY` set.
4. Verify SignalScribe eval still works: `.venv/bin/python -m pulsecraft run-change fixtures/changes/change_001_clearcut_communicate.json --real-signalscribe` runs to DELIVERED without error.
5. Confirm `pytest-asyncio` is installed (it's a dev dep — sanity check).

## Design principles — mostly the same as prompt 05, with three additions

1. **Structured output via Anthropic API** — return JSON matching `PersonalizedBrief` schema. Validate on the way out. Retry once with corrective feedback. Escalate to HITL on second failure.
2. **Prompt loaded from disk** — `.claude/agents/buatlas.md`. Python code reads it at runtime.
3. **Decisions[] populated by the prompt** — gate 4 decision always; gate 5 decision only when gate 4 returns `AFFECTED`.
4. **Citations mandatory** — when BUAtlas's `why_relevant` or message variant references a claim, it must trace back to the ChangeBrief (which already has sources from SignalScribe).
5. **Policy thresholds from config** — confidence thresholds for gate 4 and gate 5 come from `policy.yaml`, not hardcoded.
6. **No AbbVie-specific knowledge in the prompt** — BU names are inputs, not prompt content.

**New for BUAtlas:**

7. **Isolation per BU is non-negotiable.** Each BUAtlas invocation sees only one BU's profile. Never include other BUs' data in an invocation's input. The invocation doesn't know how many BUs are being evaluated total, doesn't know the others' verdicts, can't be influenced by them. This is the whole point of per-BU fan-out — preventing cross-BU reasoning contamination.

8. **Default bias toward ADJACENT, not AFFECTED.** From the decision criteria: *"When in doubt between AFFECTED and ADJACENT, choose ADJACENT."* The prompt must encode this bias. False positives on gate 4 (messaging an uninvolved BU) are the single largest trust-erosion risk.

9. **Gate 5's self-critique must be honest, not defensive.** If gate 4 said AFFECTED, gate 5 is asked "is the draft worth sending?" Too many LLMs will rubber-stamp their own work. Prompt must explicitly frame gate 5 as self-critique: *"would this BU head thank me for this, or curse me?"*

## Step-by-step work

### Step 1 — Context review

Read all 10 context files. Pay special attention to:
- Gate 4's failure modes (especially "confusing topical match for functional impact" and "defaulting to AFFECTED to be safe")
- Gate 5's failure modes (especially "marking everything WORTH_SENDING because gate 4 said AFFECTED")
- The decision criteria's Principle 4: *"Gates do not second-guess upstream gates."* BUAtlas does not re-decide whether the change is worth communicating — SignalScribe already decided that. BUAtlas asks only "for this specific BU, does it matter, and is my draft good enough?"

### Step 2 — Author `.claude/agents/buatlas.md`

Structure mirrors SignalScribe's prompt. Required sections:

````markdown
# BUAtlas — Per-BU Personalization Agent

## Your role

You are BUAtlas, the second agent in the PulseCraft pipeline at AbbVie. You take a ChangeBrief from SignalScribe + a single BU's profile, and decide:
- Gate 4: Is this BU actually affected by the change (versus merely adjacent)?
- Gate 5: If the BU is affected, is the message draft worth this BU head's attention?

You run ONCE for ONE BU. You do not know how many other BUs are being evaluated. You cannot be influenced by their verdicts. This isolation is intentional.

## Non-negotiable rules

- You do not second-guess SignalScribe. SignalScribe already decided the change is worth communicating; your job is BU-specific relevance and draft quality.
- NEVER include patient data, PHI, employee names, or secrets in any output.
- NEVER fabricate citations. Messages and reasoning must trace back to ChangeBrief sources.
- Default bias toward ADJACENT when uncertain between AFFECTED and ADJACENT. False positives erode trust.
- Gate 5 is self-critique. Be honest. If the draft is weak, say WEAK — don't rubber-stamp your own work because gate 4 was AFFECTED.
- Length matches weight. Short for awareness, medium for actions, long only when truly necessary.

## Gate 4 — Is this BU actually affected?

[... full text from Gate 4 section of decision criteria, including all "signals that favor AFFECTED / ADJACENT / NOT_AFFECTED", failure modes, and confidence calibration ...]

## Gate 5 — Is the drafted message worth this BU head's attention?

[... full text from Gate 5 section ...]

## Input contract

You receive:
- `change_brief`: SignalScribe's structured interpretation — this is the authoritative statement of what changed. Trust it. Do not re-interpret.
- `bu_profile`: the single BU under consideration — heads, owned product areas, active initiatives, preferences
- `past_engagement` (optional): recent notification history for this BU, useful for noise sensitivity

## Output contract

Produce JSON matching the PersonalizedBrief schema:
- `relevance` enum: affected | adjacent | not_affected — gate 4 outcome
- `priority`: P0 | P1 | P2 | null (null if not affected)
- `why_relevant`: string — BU-specific, concrete. Populated only if relevance = affected. NOT generic. Specifies what this BU's people will do differently because of this change.
- `recommended_actions`: array of {owner, action, by_when?}
- `assumptions`: array of strings — things you assumed
- `message_variants`: {push_short?, teams_medium?, email_long?} — required if affected + not not_worth
- `message_quality` enum: worth_sending | weak | not_worth | null (null if not affected) — gate 5 outcome
- `confidence_score`: 0-1
- `decisions`: array — gate 4 always present; gate 5 only when gate 4 = affected

[... inline a concise description of each field ...]

## How to reason

1. Read the ChangeBrief carefully. Read the BU profile carefully. Note what overlaps, what doesn't.
2. Gate 4: work through the signals. Is this BU *functionally* affected or only *topically* proximate? When in doubt → ADJACENT.
3. If not affected, return relevance=not_affected with a one-sentence reason. Skip gate 5.
4. If adjacent, return relevance=adjacent with why. Skip gate 5. Draft a short digest line.
5. If affected, proceed to gate 5. Draft the message variants. Critique your own draft honestly.
6. If the draft is weak or not worth sending, say so. The orchestrator will handle it (regenerate or drop).

## Output format

Respond with ONLY a valid JSON object matching PersonalizedBrief. No prose before or after. No markdown code fences. Just the JSON.
````

Fill in `[...]` sections by copying the relevant text from `design/planning/01-decision-criteria.md`. Copy, don't paraphrase — the signal lists and failure modes are load-bearing.

**Target length:** 400–700 lines. If shorter, detail was omitted.

### Step 3 — Author `src/pulsecraft/agents/buatlas.py`

Mirror the SignalScribe class structure:

```python
class BUAtlas:
    """Real BUAtlas implementation using Claude Sonnet 4.6. Single-BU invocation."""

    agent_name = "buatlas"
    version = "1.0"

    def __init__(
        self,
        anthropic_client: anthropic.Anthropic | None = None,
        model: str = "claude-sonnet-4-6",
        max_retries: int = 2,
        prompt_path: Path | None = None,
    ): ...

    def invoke(
        self,
        change_brief: ChangeBrief,
        bu_profile: BUProfile,
        past_engagement: PastEngagement | None = None,
    ) -> PersonalizedBrief:
        """Gate 4 (always) + Gate 5 (only if gate 4 = AFFECTED). Returns validated PersonalizedBrief."""
        ...
```

Implementation requirements identical to SignalScribe:
- Load prompt from `.claude/agents/buatlas.md` on init (cache in-memory)
- Call Anthropic API with system prompt + user message
- Parse JSON response, validate against `PersonalizedBrief` schema
- One retry with corrective feedback on validation failure
- After second failure, raise `AgentOutputValidationError`
- `tenacity` retries on API errors
- `structlog` for structured logging
- Cost estimation logged as `usd_estimate`

### Step 4 — Author `src/pulsecraft/agents/buatlas_fanout.py`

This is the new pattern. Async wrapper for parallel per-BU invocation.

```python
async def buatlas_fanout(
    change_brief: ChangeBrief,
    candidate_bus: list[BUProfile],
    factory: Callable[[], BUAtlasProtocol],   # factory so each invocation gets a fresh instance
    past_engagement_lookup: Callable[[str], PastEngagement | None] | None = None,
    max_concurrent: int = 5,
) -> list[PersonalizedBrief | FanoutFailure]:
    """Invoke BUAtlas in parallel, one per candidate BU. Returns results in same order as input.

    Failures are returned as FanoutFailure objects, not raised — one BU failing
    does not kill the whole fan-out. The orchestrator decides what to do with failures.
    """
    ...
```

Requirements:

- Uses `asyncio.gather` with `return_exceptions=True` semantics, but wrap exceptions as `FanoutFailure` objects (typed, serializable) rather than re-raising
- `max_concurrent` limits parallelism via `asyncio.Semaphore` — default 5; avoids rate-limit pressure on Anthropic API
- Each invocation is **fully isolated**: new `BUAtlas` instance per BU (via `factory`), fresh context. No shared state beyond the `ChangeBrief` input (which is read-only).
- Because `BUAtlas.invoke` is synchronous, wrap calls in `asyncio.to_thread` to avoid blocking the event loop
- `FanoutFailure` includes: `bu_id`, `error_type`, `error_message`, `retriable: bool`
- Results preserve input order (caller indexes by position, not BU ID)

Also add a synchronous wrapper `buatlas_fanout_sync(...)` that wraps `buatlas_fanout(...)` via `asyncio.run(...)`, for callers who don't want to deal with async (including the orchestrator, which is sync).

### Step 5 — Update the orchestrator

In `src/pulsecraft/orchestrator/engine.py`:

- The orchestrator's existing BUAtlas-fan-out logic (with mocks) currently calls `buatlas.invoke(...)` per candidate BU in a loop. Update it to optionally use `buatlas_fanout_sync(...)` when a real fan-out function is provided.
- Handle `FanoutFailure` results: for any failure, record an audit entry with the error details, treat the BU as "unresolved" (route to HITL or drop based on policy — for v1, drop with audit trail; document this choice in a code comment).
- Keep the mock path working unchanged for existing tests.

In `src/pulsecraft/cli/main.py`:

- Wire up `--real-buatlas` flag. When passed, the orchestrator uses real `BUAtlas` with `buatlas_fanout_sync`.
- Compatible with `--real-signalscribe` — both flags can be passed together.

### Step 6 — Tests

In `tests/unit/agents/`:

1. `test_buatlas_unit.py`:
   - Prompt loads from file
   - Contract adherence: returns PersonalizedBrief, decisions[] populated correctly (1 if not_affected, 2 if affected)
   - Isolation: same `BUAtlas` instance called twice with different BU profiles returns independent results (no shared state between calls)
   - Retry on malformed response
   - Raises `AgentOutputValidationError` after two failed validations
   - `tenacity` retry on API errors, then raises `AgentInvocationError`

2. `test_buatlas_fanout_unit.py`:
   - Parallel fan-out over 3 BUs completes in roughly the time of one call (not 3×)
   - Failure isolation: one BU's invocation raising doesn't affect others; result is FanoutFailure in that position
   - Result ordering preserved
   - `max_concurrent=1` forces sequential (useful for debugging)
   - Empty candidate list returns empty result

In `tests/integration/agents/`:

3. `test_buatlas_integration.py`:
   - Real API, `@pytest.mark.llm`, skipped unless `PULSECRAFT_RUN_LLM_TESTS=1`
   - Tests for fixtures 001, 006, 008 (fixtures where BUAtlas is exercised)
   - For each fixture: run SignalScribe first to get ChangeBrief, then BUAtlas per candidate BU
   - Assert: PersonalizedBrief validates against schema, decisions[] correct, confidence 0-1, no cross-BU contamination (bu_alpha result doesn't mention bu_beta)

### Step 7 — Eval script with variance-aware matching

`scripts/eval_buatlas.py` — runs each multi-BU fixture **N=3 times** and reports the distribution of gate-4 and gate-5 verbs per BU.

Expected output format:

```
BUAtlas Eval Report (model: claude-sonnet-4-6, runs per fixture: 3, date: 2026-04-22)

─────────────────────────────────────────────────────────────────────────────
Fixture 001 — clearcut_communicate
─────────────────────────────────────────────────────────────────────────────
  bu_alpha:
    Gate 4: AFFECTED (3/3)                  ✅ stable
    Gate 5: WORTH_SENDING (3/3)             ✅ stable
    Expected terminal category: affected + worth_sending
    Status: ✅ stable match
  bu_beta:
    Gate 4: NOT_AFFECTED (3/3)              ✅ stable
    Gate 5: (skipped — not affected)
    Expected terminal category: not_affected
    Status: ✅ stable match

─────────────────────────────────────────────────────────────────────────────
Fixture 006 — multi_bu_affected_vs_adjacent
─────────────────────────────────────────────────────────────────────────────
  bu_zeta:
    Gate 4: AFFECTED (3/3)                  ✅ stable
    Gate 5: WORTH_SENDING (2/3), WEAK (1/3) 🟡 unstable
    Expected terminal category: affected + (worth_sending or weak)
    Status: ✅ acceptable variance
  bu_delta:
    Gate 4: ADJACENT (2/3), AFFECTED (1/3)  🟡 unstable — potential false positive
    Gate 5: (n/a for adjacent runs)
    Expected terminal category: adjacent
    Status: ⚠️  false-positive risk — AFFECTED verdict on 1/3 runs

─────────────────────────────────────────────────────────────────────────────
Fixture 008 — post_hoc_already_shipped
─────────────────────────────────────────────────────────────────────────────
  bu_epsilon:
    Gate 4: AFFECTED (3/3)                  ✅ stable
    Gate 5: WORTH_SENDING (3/3)             ✅ stable
    Status: ✅ stable match

Total invocations: ~18 (3 runs × 6 BU-eval events)
Total cost: $X.XX
Total latency: Xs (mostly parallelized)

Items worth reviewing:
  - Fixture 006 bu_delta: 1/3 runs said AFFECTED for a BU expected to be ADJACENT.
    Recommend reading the audit log for that run to understand the reasoning.
```

Expected terminal categories come from `fixtures/changes/README.md` coverage table.

**Matching logic:**

- ✅ **stable match** — all N runs landed in the expected terminal category
- ✅ **acceptable variance** — all N runs landed in a set of defensibly-close categories (e.g., worth_sending vs. weak are both "affected and draft exists" — close; not_affected vs. adjacent are both "don't push-notify" — close)
- 🟡 **unstable** — different categories across runs but none clearly wrong
- ⚠️ **false-positive risk** — at least one run landed in a *stricter* category than expected (AFFECTED when we expected ADJACENT; WORTH_SENDING when we expected NOT_WORTH). This is the asymmetric error that matters most — we'd rather under-notify than spam.
- ❌ **mismatch** — all N runs landed in an unexpected category

Script exits 0 always. Writes report to `audit/eval/buatlas-<timestamp>.txt`.

### Step 8 — Update CLAUDE.md and planning index

CLAUDE.md additions:

```markdown
### BUAtlas (prompt 06)
- **Location:** `src/pulsecraft/agents/buatlas.py`
- **Fan-out wrapper:** `src/pulsecraft/agents/buatlas_fanout.py` (async, parallel per BU, failure-isolated)
- **Prompt:** `.claude/agents/buatlas.md`
- **Owns gates:** 4, 5
- **Protocol:** `BUAtlasProtocol`
- **Model:** `claude-sonnet-4-6` via Anthropic API
- **Invocation pattern:** one per candidate BU, in parallel via `asyncio.gather` + `asyncio.to_thread`, semaphore-limited (default 5)
- **Isolation invariant:** each invocation sees only its own BU's profile; no cross-BU data leakage
- **Eval script:** `scripts/eval_buatlas.py` (variance-aware, N=3 runs per fixture)
```

Update "Current phase":
- Add ✅ 06 — BUAtlas agent (gates 4, 5, parallel per BU)
- Next → 07 — PushPilot agent

Update last-updated footer.

Update `design/planning/00-planning-index.md`:
- Mark prompt 06 as ✅ Done in the prompt-driven build workflow table
- Add entry to Completed Artifacts for BUAtlas

### Step 9 — Verify

1. `.venv/bin/ruff check .` — passes
2. `.venv/bin/ruff format --check .` — passes
3. `.venv/bin/mypy src/pulsecraft/agents/ src/pulsecraft/orchestrator/` — passes
4. `.venv/bin/pytest tests/ -v -m "not llm"` — all prior tests pass, new unit tests pass. Expect ~215-230 total.
5. `PULSECRAFT_RUN_LLM_TESTS=1 .venv/bin/pytest tests/integration/agents/test_buatlas_integration.py -v -m llm` — integration tests pass.
6. `.venv/bin/python scripts/eval_buatlas.py` — produces eval report. Include output in final report.
7. CLI smoke test: `.venv/bin/python -m pulsecraft run-change fixtures/changes/change_006_multi_bu_affected_vs_adjacent.json --real-signalscribe --real-buatlas` — runs with real SignalScribe + real BUAtlas (mock PushPilot). Should terminate in DELIVERED, HELD, or AWAITING_HITL depending on outcomes.

**Eval acceptability:** if ≥6 of the BU-eval events are ✅ stable match or ✅ acceptable variance and no ⚠️ false-positive risk items exist, proceed to prompt 07. If any false-positive risk exists (BU marked AFFECTED when it should be ADJACENT), pause and flag before committing — false positives are the most expensive failure mode.

### Step 10 — Commit

```
feat(agents): add BUAtlas — parallel per-BU personalization agent (prompt 06)

Implements decision gates 4, 5 per design/planning/01-decision-criteria.md.
Model: claude-sonnet-4-6 via Anthropic API. Parallel fan-out per candidate BU.

Files:
- .claude/agents/buatlas.md — canonical prompt (N lines)
- src/pulsecraft/agents/buatlas.py — BUAtlas class, single-BU invocation
- src/pulsecraft/agents/buatlas_fanout.py — async parallel wrapper with failure isolation
- src/pulsecraft/orchestrator/engine.py — updated to use real fan-out when --real-buatlas
- src/pulsecraft/cli/main.py — --real-buatlas flag
- scripts/eval_buatlas.py — variance-aware eval (N=3 runs per fixture)
- tests/unit/agents/test_buatlas_unit.py — contract + isolation tests
- tests/unit/agents/test_buatlas_fanout_unit.py — parallelism + failure-isolation tests
- tests/integration/agents/test_buatlas_integration.py — real-API tests (@pytest.mark.llm)

Isolation invariant: each BUAtlas invocation sees only one BU's profile. No
cross-BU reasoning contamination. Per-BU failures don't kill the fan-out.

Eval results:
- [summarize: stable matches, acceptable variance, unstable, false-positive risks]
- Total cost: $X.XX; total latency: Xs (parallelized)

Next: prompt 07 — PushPilot (gate 6).
```

Do not push to remote unless the user asks.

## Rules for this session

- **Do not modify SignalScribe's prompt or code.** BUAtlas builds on SignalScribe; don't touch upstream.
- **Do not batch BU invocations into a single LLM call.** "One BU per invocation" is a hard invariant. Batching would violate isolation and cross-contaminate reasoning.
- **Do not add retry logic that hides genuine failures.** Retries on transient errors = yes. Retries that paper over schema mismatches or API errors = no.
- **Do not weaken the decision-criteria text** when adapting it for the prompt. If gate 4 says "default to ADJACENT when uncertain," the prompt must say that — not "consider ADJACENT when uncertain."
- **Do not change schemas.** If you need data that doesn't fit existing schemas, flag in the final report as a future-prompt item.
- **Do not invent Anthropic API specifics.** Mirror the patterns from SignalScribe exactly. Model string `claude-sonnet-4-6` (same as prompt 05); if it needs to change, check installed `anthropic` library rather than guess.
- **Budget guard:** if total cost during this session exceeds $8, stop and ask. Normal expectation is $1-3.

## Final report

1. **Files created/modified** — full tree with line counts.
2. **Prompt length** (`.claude/agents/buatlas.md`): X lines.
3. **Verification results** — each step pass/fail. Total tests before/after.
4. **Eval report** — paste full output of `scripts/eval_buatlas.py`. Highlight any ⚠️ false-positive risks with commentary.
5. **Parallelism validation** — confirm 3-BU fan-out completes in ~the time of one invocation (not 3×).
6. **Observations** — anything surprising about BUAtlas's reasoning on specific BU/fixture pairs.
7. **Total API cost incurred** during this session.
8. **Commit hashes** — both commits.
9. **Next prompt** — "Ready for prompt 07: PushPilot (gate 6)."

---

## [Post-commit] Save this prompt file to the repo

After the main commit lands, ask the user: **"Save this prompt file (prompt 06) to `prompts/06-agent-buatlas.md` as a commit archive? (yes/no)"**

If yes:
- Write verbatim to `prompts/06-agent-buatlas.md`.
- Commit with: `chore(prompts): archive prompt 06 (BUAtlas) in repo`.

If no: skip.
