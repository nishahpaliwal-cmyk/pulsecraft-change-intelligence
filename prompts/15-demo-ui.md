# Prompt 15 — Demo UI (Level 1)

> **Character.** Build a beautiful, document-like web UI that visualizes the PulseCraft pipeline end-to-end for a Head of AI audience. FastAPI + Server-Sent Events + static HTML/CSS/JS. Runs on `localhost:8000`. Five scenarios, real agents, live streaming, polished animation, agent-vs-code moment highlighted, HITL and delivery renderings preview, audit trail one click away.
>
> **Why this matters.** This is the demo deliverable. The audience is the Head of AI and senior stakeholders. The UI is the thing they'll remember.
>
> **How to use.** Paste below the `---` line into Claude Code.
>
> **Expected duration:** One focused 3-4 hour session. Possibly a second polish session after reviewing the first version.
>
> **Prerequisite:** Prompts 00–14.6 done. 606 tests passing. README polished. AbbVie references removed. Baseline eval committed.
>
> **Budget:** ~$2-3 in LLM costs for 10-15 scenario runs during build and smoke-testing. Rehearsal after this is separate — plan ~$7-10 for demo prep runs.

---

# Instructions for Claude Code

You are building the PulseCraft demo UI. The system's walking skeleton is complete; your job is purely additive — a new visualization layer wrapping the existing orchestrator, agents, hooks, and skills. **Do not modify any existing agent, hook, skill, schema, or orchestrator logic.** The UI should observe and display; never drive behavior.

## Environment discipline

Python 3.14. Use `.venv/bin/python` explicitly. Add new dependencies via `uv add`. FastAPI, uvicorn, and httpx may already be present; if not, add them. No JavaScript build tooling — vanilla JS only. No React. No frameworks. This is a single static page served from FastAPI.

## Context to read before starting

1. **`CLAUDE.md`** — current state, standing orders, build log.
2. **`src/pulsecraft/orchestrator/engine.py`** — the orchestrator entrypoint; understand how `run_change()` sequences the pipeline.
3. **`src/pulsecraft/orchestrator/audit.py`** — how audit records are written; you'll subscribe to this stream.
4. **`src/pulsecraft/skills/audit_skill.py`** — audit record schema and types.
5. **`src/pulsecraft/schemas/`** — ChangeArtifact, ChangeBrief, PersonalizedBrief, DeliveryPlan, AuditRecord.
6. **`src/pulsecraft/cli/commands/explain.py`** — the `/explain` implementation; you'll reuse it for the audit trail drawer.
7. **`fixtures/changes/`** — the 5 fixtures we're featuring: 001, 002, 006, 007, 008.
8. **`templates/`** — Jinja2 templates for rendered messages; the UI will preview these.

## What "done" looks like

When you finish:

1. A new `pulsecraft demo` CLI subcommand starts a FastAPI server on `http://localhost:8000`.
2. Visiting the URL loads a polished, document-like single-page UI with five scenario cards in a left sidebar and a main document area.
3. Clicking a scenario runs the real pipeline with real LLM agents and streams decisions into the document area as they happen — not token-by-token, but decision-by-decision (gate verdicts, hook outcomes, terminal state).
4. BUAtlas parallel fan-out is visually represented — multiple BU cards appear side-by-side and fill in asynchronously as each instance completes.
5. When PushPilot's preference differs from the code-enforced outcome, the UI shows both side-by-side as a dedicated "agent preference vs. code enforcement" block.
6. Terminal state is rendered as either: (a) a mock Teams card / email preview for `DELIVERED`, (b) a HITL operator panel for `AWAITING_HITL`, (c) a clear "archived" or "held" explanation for those states.
7. A left-edge progress rail visualizes where the pipeline currently is; stays sticky during scroll.
8. A cost and elapsed-time counter ticks in the top bar.
9. Keyboard shortcuts `1`–`5` run the corresponding scenario.
10. A "View audit trail" button opens a drawer with the full `/explain` output.
11. A subtle "demo mode — synthetic BUs, stubbed transports" indicator in the header.
12. No existing tests break; ideally, a small number of new tests cover the FastAPI routes and SSE event emission.
13. One commit with a clean message.

## Scope boundaries — do not do

- **Do not** modify orchestrator, agent, hook, skill, or schema logic. Purely additive.
- **Do not** build a deployment pipeline, Dockerfile, or CI job for the demo server. Laptop-only.
- **Do not** add React, Vue, Svelte, or any JS framework. Vanilla JS only.
- **Do not** add a JS build step (no webpack, no vite, no bundler). The browser loads the JS directly.
- **Do not** persist demo state to a new database. Use the existing audit chain as the data source.
- **Do not** add auth, rate limiting, or production concerns. This is a local demo server.
- **Do not** fabricate metrics. Cost counter must reflect real LLM cost; elapsed time must reflect real wall-clock.

## Technology choices

- **Web framework:** FastAPI
- **ASGI server:** uvicorn
- **Streaming:** Server-Sent Events (SSE) — simple, reliable, no WebSocket complexity
- **Frontend:** Single HTML file + separate `style.css` + separate `app.js`. No framework.
- **Fonts:** Google Fonts CDN for Fraunces (serif headings) and Inter (sans body) and JetBrains Mono (monospace). Fallbacks to system fonts if offline.
- **Icons:** Inline SVG only. No icon library dependencies.
- **Backend integration:** Event bus subscribes to audit writes; SSE endpoint drains per-run event queues.

## File layout to produce

Create these files (and only these):

```
src/pulsecraft/demo/
├── __init__.py
├── server.py                    # FastAPI app
├── event_bus.py                 # In-memory async event bus keyed by run_id
├── events.py                    # Event types and serialization
├── instrumented_run.py          # Wraps orchestrator.run_change() to emit events
└── static/
    ├── index.html               # Single-page app
    ├── style.css                # All styles
    ├── app.js                   # All client logic
    └── fonts.css                # Google Fonts imports (or empty if using CDN link)

src/pulsecraft/cli/commands/
└── demo.py                      # New `pulsecraft demo serve` subcommand

tests/demo/
├── __init__.py
├── test_server_routes.py        # FastAPI route tests (TestClient)
└── test_event_bus.py            # Event bus unit tests
```

Update `pyproject.toml` dependencies (add `fastapi`, `uvicorn`, `sse-starlette` if not already present; `sse-starlette` is optional — raw SSE via FastAPI works too).

Update the main CLI to register the `demo` subcommand.

## Event contract — define this first

The backend emits events via SSE. The frontend consumes them. Defining the event contract clearly before writing either side prevents drift.

### Event types

Every event is a JSON object with these fields:

```python
{
  "event_id": "ev_01HX...",          # ULID for deduplication
  "run_id": "run_01HX...",           # which run this belongs to
  "timestamp": "2026-04-23T...",      # ISO 8601
  "type": "<one of the types below>", # discriminator
  "payload": { ... }                  # type-specific
}
```

### Event type catalog

| Type | Payload | Purpose |
|---|---|---|
| `run_started` | `{ scenario_id, fixture_path, change_artifact }` | The pipeline began. Frontend renders the change header. |
| `hook_fired` | `{ stage, name, outcome, latency_ms, reason? }` | A hook completed. Stage is "pre_ingest", "post_agent", "pre_deliver", "audit". Outcome is "passed", "blocked", "downgraded". |
| `agent_started` | `{ agent, gate_batch }` | An agent invocation started. agent is "signalscribe" / "buatlas" / "pushpilot". gate_batch is the gates this invocation will decide. Used to trigger shimmer placeholders. |
| `gate_decision` | `{ agent, gate, verb, confidence, reason, sources?, bu_id? }` | A single gate verdict. bu_id is present for gates 4/5. |
| `buatlas_instance_started` | `{ bu_id, bu_name }` | A BUAtlas instance started for a specific BU. Triggers a loading BU card. |
| `buatlas_instance_completed` | `{ bu_id, verdict: "WORTH_SENDING"\|"WEAK"\|"NOT_AFFECTED"\|... , personalized_brief? }` | A BUAtlas instance completed. |
| `pushpilot_decision` | `{ bu_id, preference: { verb, reason }, enforced: { verb, reason }, diverged: bool }` | Gate 6 outcome. **This is the agent-vs-code moment.** diverged flag tells the frontend to show the side-by-side comparison. |
| `hitl_triggered` | `{ bu_id?, reason, trigger_type, priority? }` | A HITL trigger fired. trigger_type is "priority_p0" / "mlr_sensitive" / "confidence_low" / "dedupe_conflict" / etc. |
| `delivery_rendered` | `{ bu_id, channel, variant, rendered_content }` | A message was rendered for a channel. Frontend displays it as a preview. |
| `terminal_state` | `{ state, bu_outcomes: [{ bu_id, state, reason }], total_cost_usd, elapsed_s }` | The run ended. |
| `error` | `{ stage, message, recoverable }` | Something errored. Frontend shows a graceful failure state. |

### Event ordering guarantees

- `run_started` is always first.
- `terminal_state` is always last.
- Events within a run maintain monotonic `timestamp` ordering.
- BUAtlas events may arrive interleaved across BUs (that's the whole point — it's parallel).
- The frontend must be resilient to out-of-order arrival within BUAtlas events (unlikely but possible).

### Error handling

If any error occurs mid-run, emit an `error` event followed by `terminal_state` with state `FAILED`. The frontend shows the error gracefully without appearing broken.

## How to emit events — integration with the orchestrator

You must not modify `orchestrator/engine.py`. Instead:

1. Create `src/pulsecraft/demo/instrumented_run.py` that wraps `run_change()`.
2. The wrapper subscribes to the audit writer via a callback/hook.
3. Audit records are translated into UI events and pushed to the event bus for this run_id.
4. The wrapper returns normally when the orchestrator returns.

The audit writer already produces structured records; use them as the source of truth. If you find that audit records don't carry everything needed for the UI (e.g., the agent-vs-code comparison isn't a single audit record), construct those events by reading adjacent audit records together — but do this in the instrumented_run layer, not by modifying the orchestrator.

**Critical:** if this approach proves too awkward (audit records aren't granular enough), then add an optional `on_event: Callable[[Event], None] | None = None` parameter to `run_change()` that gets called at key points. This is a minimally invasive change — orchestrator behavior is unchanged when `on_event` is `None`. Use this fallback only if the audit-subscription approach hits walls.

## Visual design specification

### Palette

Exact hex values. Use these consistently.

```
Background (primary)          #FAF7F2   warm cream, paper-like
Background (secondary/cards)  #FFFFFF   crisp white for contrast
Background (subtle surfaces)  #F1EDE4   slight depression
Text (primary)                #1F1D18   near-black, warm
Text (secondary)              #5F5B52   muted warm gray
Text (tertiary/captions)      #8D877B   soft warm gray
Border (default)              #E5DFD4   quiet hairline
Border (hover/focus)          #C9C1B0   visible but restrained

Agent colors (from architecture diagram):
SignalScribe (purple)         #534AB7 primary, #EEEDFE surface, #3C3489 text
BUAtlas     (teal)            #0F6E56 primary, #E1F5EE surface, #085041 text
PushPilot   (coral)           #993C1D primary, #FAECE7 surface, #712B13 text

Hook color (amber)            #854F0B primary, #FAEEDA surface, #633806 text

Semantic colors:
Success (DELIVERED)           #3B6D11 primary, #EAF3DE surface
Warning (HELD, DIGEST)        #854F0B  reuse amber
Danger  (FAILED)              #A32D2D primary, #FCEBEB surface
Info    (AWAITING_HITL)       #185FA5 primary, #E6F1FB surface
Neutral (ARCHIVED)            #444441 primary, #F1EFE8 surface
```

### Typography

Fonts (load via Google Fonts at the top of `index.html`):
- **Fraunces** (400, 500, 600 weights) — for headings, section dividers, the project name.
- **Inter** (400, 500, 600 weights) — for body text, labels, buttons.
- **JetBrains Mono** (400 weight) — for code, JSON, audit trail, IDs.

Type scale:
```
h1 (page title)          Fraunces 500 · 32px · line-height 1.2
h2 (section divider)     Fraunces 500 · 22px · line-height 1.3
h3 (subsection)          Fraunces 500 · 18px · line-height 1.35
Body                     Inter 400 · 15px · line-height 1.65
Body-strong              Inter 500 · 15px · line-height 1.65
Label/small              Inter 500 · 13px · line-height 1.4
Micro                    Inter 400 · 12px · line-height 1.4 · tracking 0.02em
Mono                     JetBrains Mono 400 · 13px · line-height 1.5
```

Sentence case always except the top-level brand word "PulseCraft".

### Layout

Three columns on desktop (≥1200px wide):

```
┌─────────────────────────────────────────────────────────────────┐
│  Top bar (56px tall, sticky)                                    │
│  PulseCraft · Change Intelligence    [demo mode]    $0.00 · 0s  │
├──────────────┬──────────────────────────────────┬───────────────┤
│              │                                  │               │
│  Scenario    │  Decision document               │  Progress     │
│  sidebar     │  (main area)                     │  rail         │
│  (300px)     │  (fluid, max 780px content)      │  (80px)       │
│              │                                  │               │
│  5 cards     │  scrolls freely                  │  sticky       │
│              │                                  │               │
│              │                                  │               │
└──────────────┴──────────────────────────────────┴───────────────┘
```

On smaller screens (< 1200px): the progress rail collapses to a top-of-document pipeline; layout becomes two columns. Below 900px: sidebar becomes a dropdown. (Demo will run on full laptop, so this is belt-and-suspenders.)

Outer page padding: 32px on desktop. Gutter between columns: 40px.

### Component spec

#### Top bar

Height 56px, sticky, bottom border hairline. Contents from left to right:
- **Project word mark** — "PulseCraft" in Fraunces 500 at 18px, with a small subtitle "· Change Intelligence" in Inter 400 at 13px secondary color.
- **"demo mode" pill** — center-ish; Inter 500 at 11px, uppercase, tracking 0.05em; amber surface with amber text; small and unobtrusive.
- **Cost and elapsed counter** — right side. Format: `$0.183 · 42s`. Mono font, 13px. Updates as events arrive. While a run is idle, shows `—`.

#### Scenario sidebar

5 cards, each ~88px tall, with 12px vertical spacing between. Cards have:
- Small fixture number in top-left corner (Mono, 11px, tertiary color): `01`, `02`, `06`, `07`, `08`.
- Scenario title in Fraunces 500 at 16px.
- One-line description in Inter 400 at 13px secondary color, clamped to one line with ellipsis.
- A subtle "Run →" affordance appearing in bottom-right on hover.
- When a scenario is actively running: left border turns purple; a thin progress bar at the bottom of the card fills left-to-right over the run's duration.
- When a scenario has completed this session: a small terminal-state badge appears in the top-right corner (e.g., "archived" in neutral gray, "delivered" in success green, "awaiting review" in info blue).

Card data for each fixture (use this exactly):

```
01  A clearcut customer-visible change    → Happy path to delivery with priority review
02  A pure internal refactor              → System correctly refuses to send
06  A change affecting multiple BUs       → Parallel per-BU reasoning in action
07  An MLR-sensitive educational update   → Policy layer catches regulated content
08  A post-hoc already-shipped change     → Retrospective notification, full delivery
```

Map to fixture filenames:
```
01 → fixtures/changes/change_001_clearcut_communicate.json
02 → fixtures/changes/change_002_pure_internal_refactor.json
06 → fixtures/changes/change_006_multi_bu_affected_vs_adjacent.json
07 → fixtures/changes/change_007_mlr_sensitive.json
08 → fixtures/changes/change_008_post_hoc_already_shipped.json
```

#### Decision document (main area)

The document grows top-to-bottom as events arrive. Sections in order:

**0. Welcome state (before any run)** — centered, vertically in the middle of the viewport. A subtle three-circle abstract illustration in purple/teal/coral at ~40% opacity, with Fraunces heading below: *"Select a scenario to watch PulseCraft reason about a change."* Below that, in body text: *"Each scenario runs the real pipeline with real LLM agents. Expect ~30-50 seconds per run."* Below that: *"Keyboard shortcuts: 1–5"* in micro type.

**1. Change header** — a card with:
- Source system icon (small SVG) and name
- Change title in Fraunces 500 at 22px
- Change ID in Mono micro
- Timestamp
- Expandable "raw text" block (collapsed by default, 3 lines shown with fade-out, click to expand)
- Slides in from above with a 300ms cubic-bezier(0.4, 0, 0.2, 1) ease, opacity 0 → 1, translateY -8px → 0.

**2. Pipeline sections** (pre_ingest hook, SignalScribe, post_agent hook, BU pre-filter, BUAtlas, post_agent hook, PushPilot, pre_deliver hook) — each as its own labeled section.

Each section has:
- Section header with agent color accent (a 3px left border or a small colored dot) plus the section name in Fraunces 500 at 18px, and a micro-type subtitle.
- Body area where decision cards appear.

For sections driven by LLM agents, a **"thinking" state** appears before any decision card:
- A shimmer effect (subtle animated gradient from 0% to 100% horizontal position over 1.5s, infinite) across 3 ghost placeholder rectangles matching where the decision cards will appear.
- **No "analyzing..." text. No spinning dots. No bouncing ellipsis.** Just the shimmer. Silent elegance.

**3. Decision cards** — each gate verdict is a card:
- Top row: verb badge (colored by verdict severity) + gate label (e.g., "Gate 1 · worth communicating?") + confidence bar (a thin horizontal bar, animated from 0 → actual width over 600ms, filling left-to-right; color matches agent; label "0.92" to the right).
- Reasoning paragraph in body text.
- Expandable "sources" footer (Inter 500, 12px, secondary color, chevron icon) — clicking reveals cited source excerpts.

Card appears with opacity 0 → 1, translateY 8px → 0 over 400ms, cubic-bezier(0.4, 0, 0.2, 1). Staggered: each card appears 80ms after the previous one in the same section.

**4. BUAtlas section — the centerpiece** — a grid of BU cards:
- If 3 or fewer BUs: 3-column grid, cards side-by-side.
- If 4-6 BUs: wraps to 2 rows.
- All cards appear simultaneously in "loading shimmer" state.
- Each card fills in independently as its BU's events arrive. This asynchronous fill is the visual proof of parallelism.
- Card structure:
  - BU name (Fraunces 500 at 16px) + BU id (Mono micro, secondary color)
  - Gate 4 verdict with verb badge and confidence
  - Gate 5 verdict with verb badge and confidence (appears after gate 4)
  - If WORTH_SENDING: below the verdicts, a "message preview" block with tabs for "Push", "Teams", "Email" (pick one to show by default; tab switching is free with vanilla JS).
  - If NOT_AFFECTED or WEAK or NOT_WORTH: the card gracefully dims (opacity 0.6) and collapses to just the header + verdict — still visible for audit, but visually demoted.

**5. PushPilot section** — for each WORTH_SENDING BU card from above, a corresponding PushPilot decision section below:
- Header: "PushPilot · Gate 6 for bu_alpha" (in coral accent).
- **Default case (preference matches enforcement):** a single decision card showing verb, confidence, reason.
- **Diverged case (agent preference vs code override):** this is the architectural showpiece. Show **two stacked cards with a vertical arrow between them**:
  - Upper card, labeled "Agent preference" in coral accent: verb + reason + a tooltip "what PushPilot wanted to do based on its reading of the situation."
  - Arrow down (a simple SVG arrow, gray, 24px tall).
  - Lower card, labeled "Code enforcement" in neutral/gray accent: verb + reason + a tooltip "what the pre_deliver hook enforced per policy invariants."
  - Below both cards, a micro-type caption: *"This separation lets us calibrate policy by comparing agent judgment against enforced outcomes."*
- This block gets a subtle background tint (warm cream darker by ~3%) to make it feel special.

**6. Pre_deliver hook section** — compact unless a HITL trigger fires. Fired case:
- Amber left border (3px).
- Clear label: "Routed to human review" with the trigger type in bold.
- Reason: "Matched restricted term 'contraindication' in recipient context: MLR-sensitive content detected."
- Shows which fields matched, which patterns fired.

**7. Terminal state** — the closing section. Depending on state:

For `DELIVERED`:
- Success green accent.
- Header: "Delivered to bu_alpha head via Teams" (or whichever channel).
- Below it, the **rendered message preview** — a faithful mock of how the message would appear in its target channel:
  - **Teams card mock:** rounded rectangle with avatar on left (initials), title, body, action buttons. Match Teams's visual language reasonably.
  - **Email mock:** subject line in bold, from/to headers, body area with typography matching email conventions.
  - **Push mock:** small notification-style banner with app icon, title, body.
  - Use CSS only — no images — to build these.

For `AWAITING_HITL`:
- Info blue accent.
- Header: "Awaiting human review" + trigger type badge.
- Below it, a **HITL operator panel preview** showing what the operator would see:
  - The change summary
  - The proposed message (same preview as DELIVERED would show)
  - Four action buttons: "Approve", "Reject", "Edit", "Answer question". (These are visual only in the demo — don't wire them up. The audience just needs to see the workflow exists.)
  - A note: "In production, operators receive a Slack notification and approve via `pulsecraft approve` CLI or a dashboard."

For `ARCHIVED`:
- Neutral gray accent.
- Header: "Archived — no action required"
- Below: the reason from the gate that archived it (e.g., "Gate 1: this is an internal refactor with no user-visible change. Communicating would be noise.").

For `HELD`:
- Warning amber accent.
- Header: "Held — waiting for rollout"
- Below: the reason and the `HOLD_UNTIL` target date if known.

For `FAILED`:
- Danger red accent.
- Header: "Pipeline failed"
- Below: the error reason, the stage where it failed, and a "Retry" button that re-runs the scenario.

**8. Footer actions** — two buttons:
- **"View audit trail"** — opens a side drawer from the right, 480px wide, containing the full `/explain` output. Monospaced, syntax-highlighted (subtle — just structural colors, not ostentatious). Closable via X button or ESC key.
- **"Run again"** — re-runs the current scenario. Fades out the decision document, fades back in with a new run.

#### Progress rail (right column, sticky)

A vertical track ~320px tall positioned at the top of the right column. Stays sticky as the document scrolls. Contains:
- One dot per pipeline stage (7 dots for a typical run: pre_ingest, SignalScribe, post_agent, BUAtlas, post_agent, PushPilot, pre_deliver).
- Each dot is 12px diameter, separated by ~40px of vertical line (1px wide, border color).
- Dot states:
  - **Pending** — empty circle with border color.
  - **Active** — filling with a subtle pulse animation (scale 1 → 1.1 → 1, opacity 0.8 → 1 → 0.8, 1.2s duration, infinite while active).
  - **Completed** — filled with agent/hook color.
- On hover of a completed dot: a small floating label appears showing the stage name and its outcome (e.g., "SignalScribe · 18.3s · READY").
- Clicking a completed dot scrolls the document to that section (bonus: smooth scroll).

### Animation spec

Unified easing curve for most animations: `cubic-bezier(0.4, 0, 0.2, 1)` — the "Material standard" curve, smooth and professional.

Timings:
- Card appearance: 400ms opacity + translateY
- Decision card staggering: 80ms between siblings
- Confidence bar fill: 600ms width
- Shimmer loop: 1.5s, linear, infinite
- Progress dot pulse: 1.2s, ease-in-out, infinite while active
- Drawer slide-in (audit trail): 320ms ease-out
- Section scroll: 500ms ease-in-out

**All animations respect `prefers-reduced-motion: reduce`.** If the user has that preference set, animations are reduced to fade-only, ~200ms, no translate or pulse.

### Accessibility

- All interactive elements keyboard-accessible. Tab order is logical (top bar → sidebar cards → main content → footer buttons).
- Focus states are visible — 2px purple outline with 2px offset.
- All colored indicators paired with text (don't rely on color alone).
- ARIA labels on buttons and sections.
- SSE events announced to screen readers via an aria-live region (visually hidden).

## CLI subcommand

Create `src/pulsecraft/cli/commands/demo.py` with a `pulsecraft demo serve` subcommand:

```
pulsecraft demo serve [OPTIONS]

Options:
  --host TEXT          Host to bind to  [default: 127.0.0.1]
  --port INTEGER       Port to bind to  [default: 8000]
  --open-browser       Automatically open http://localhost:PORT in the default browser
  --log-level TEXT     uvicorn log level  [default: warning]
```

Wire it into `src/pulsecraft/cli/main.py` alongside the existing commands.

The command starts uvicorn programmatically with the FastAPI app from `src/pulsecraft/demo/server.py`.

## Backend implementation plan

### `src/pulsecraft/demo/events.py`

Define Pydantic models for each event type. Include a discriminated union for validation. Provide a `serialize_to_sse(event) -> str` helper that produces the SSE wire format (`data: {json}\n\n`).

### `src/pulsecraft/demo/event_bus.py`

An in-memory event bus keyed by run_id. Each run_id has its own `asyncio.Queue`. Methods:

```python
class EventBus:
    def create_run(self) -> str:                          # returns new run_id
    async def publish(self, run_id: str, event: Event)   # push to run's queue
    async def subscribe(self, run_id: str) -> AsyncIterator[Event]:
                                                          # yields events until terminal_state
    def cleanup(self, run_id: str)                       # remove closed runs
```

Expire runs after 10 minutes of inactivity to prevent memory leaks during long demos.

### `src/pulsecraft/demo/instrumented_run.py`

The bridge between orchestrator and event bus. Implementation approach:

1. Read the change artifact from the fixture.
2. Call `orchestrator.run_change()` with an `on_event` callback (you'll need to add this parameter to `run_change` — this is the **one** minimally-invasive change allowed to the orchestrator; default `None` preserves all existing behavior and tests).
3. The callback translates orchestrator state-change/audit records into UI `Event` objects and publishes them to the event bus.
4. Also emit events the orchestrator doesn't explicitly produce — specifically, the `pushpilot_decision` event with the `diverged` flag is a derived event: look at PushPilot's decision + pre_deliver's downgrade decision and produce the combined event.

If adding `on_event` to `run_change` is too invasive and touches tests: fallback is to subscribe to audit writes via an audit-writer-side callback. Choose the cleaner path.

### `src/pulsecraft/demo/server.py`

FastAPI app with routes:

```
GET  /                              → serves static/index.html
GET  /static/{path:path}            → serves static assets
GET  /api/scenarios                 → lists the 5 scenarios with metadata
POST /api/runs                      → body: {scenario_id}; starts a run; returns {run_id}
GET  /api/runs/{run_id}/events      → SSE stream of events for a run
GET  /api/runs/{run_id}/explain     → the full /explain output as text
GET  /health                        → simple 200 OK for sanity
```

POST `/api/runs` starts the run in a background task (using `asyncio.create_task`). The client immediately receives the run_id and connects to the SSE endpoint.

SSE endpoint streams events from the event bus. Handle client disconnects gracefully (mark the run as closed; the background task continues to completion for audit integrity).

## Frontend implementation plan

### `src/pulsecraft/demo/static/index.html`

Single file. Structure:

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PulseCraft · Change Intelligence</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=Inter:wght@400;500;600&family=JetBrains+Mono&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
  <div id="app">
    <header class="top-bar">...</header>
    <aside class="sidebar">... 5 scenario cards ...</aside>
    <main class="document">... decision document ...</main>
    <aside class="progress-rail">...</aside>
    <div class="drawer" hidden>... audit trail ...</div>
  </div>
  <script src="/static/app.js" type="module"></script>
</body>
</html>
```

### `src/pulsecraft/demo/static/style.css`

All styles. Use CSS variables for the palette. Avoid CSS frameworks. ~600-900 lines of carefully-written CSS. Prefer modern CSS (grid, flex, custom properties, `@supports`). Graceful fallback to basic layouts if features aren't available.

Structure the CSS in logical sections:
1. CSS variables and resets
2. Typography
3. Layout (top bar, sidebar, document, rail, drawer)
4. Components (scenario card, decision card, BU card, agent-vs-code block, message previews, HITL panel)
5. States (loading shimmer, focus, hover, disabled)
6. Animations (keyframes)
7. Responsive tweaks
8. Reduced-motion

### `src/pulsecraft/demo/static/app.js`

ES modules. Structure:

- **Top-level:** fetch `/api/scenarios` on load, render sidebar.
- **Scenario click handler:** POST `/api/runs`, get run_id, connect to SSE, clear document, start rendering.
- **SSE event router:** switch on `event.type`, dispatch to per-type handler.
- **Per-type handlers:** `renderRunStarted`, `renderHookFired`, `renderAgentStarted`, `renderGateDecision`, `renderBUAtlasInstanceStarted`, `renderBUAtlasInstanceCompleted`, `renderPushpilotDecision`, `renderHITLTriggered`, `renderDeliveryRendered`, `renderTerminalState`, `renderError`.
- **Helpers:** DOM creation, animation choreography, confidence-bar rendering, verb-badge styling, message-preview rendering.
- **Keyboard shortcut handler:** `document.addEventListener('keydown', ...)`, map `1`-`5` to scenarios.
- **Progress rail updater:** subscribes to the same event stream, updates dot states.
- **Cost/elapsed counter:** ticks based on event timestamps; resets between runs.
- **Audit trail drawer:** lazy-loaded on first click; fetches `/api/runs/{id}/explain`.

Keep the JavaScript readable and well-commented. This is code the sponsor might someday ask to see. ~400-600 lines.

## Testing

Minimal but meaningful. Add to `tests/demo/`:

### `test_server_routes.py`

Using `fastapi.testclient.TestClient`:

- `GET /health` returns 200
- `GET /` returns HTML with expected content
- `GET /api/scenarios` returns 5 scenarios
- `POST /api/runs` with invalid scenario returns 400
- `POST /api/runs` with valid scenario returns run_id (don't actually run a real LLM pipeline in tests — mock `instrumented_run` to emit a canned event sequence)
- `GET /api/runs/{id}/events` can be consumed as SSE (consume the first few events from a mocked run)

### `test_event_bus.py`

- Creating a run returns a unique run_id
- Publishing and subscribing to a run delivers events in order
- Multiple subscribers to the same run each receive events (if that's a feature — check the implementation)
- Cleanup removes queues

Mark real-pipeline tests with `pytest.mark.slow` and skip by default. Manual smoke-testing covers the LLM-integration path.

## Rehearsal checklist (for after the UI is built)

Add to `CLAUDE.md` or a new `design/demo/rehearsal-checklist.md`:

1. Run each scenario 3 times. Note any UI states you hadn't seen before.
2. Run on the actual demo laptop. Test in the actual browser (Chrome, presumably).
3. Test with the laptop disconnected from Wi-Fi briefly — what fails gracefully and what breaks?
4. Test with a large browser zoom (150%+) — does the layout hold?
5. Rehearse the narration: what do you say while each scenario runs?
6. Identify a "backup scenario" in case one is having a bad variance day. Plan a smooth pivot.
7. Have a pre-recorded video backup of each scenario's successful run (10 minutes of screen recording work).

Don't do any of this in this prompt — just leave the checklist for you to use later.

## Step-by-step work

### Step 1 — Pre-flight

1. `git status` clean.
2. Verify tests pass: `.venv/bin/pytest tests/ -q -m "not llm and not eval" 2>&1 | tail -3` — should show 606 passing.
3. Check whether `fastapi`, `uvicorn`, `sse-starlette` are in dependencies. If not, add them via `uv add fastapi uvicorn sse-starlette`.

### Step 2 — Event contract

Write `src/pulsecraft/demo/events.py` first. Get the Pydantic models right; get the SSE serializer working. Unit-test the serializer (one test in `test_event_bus.py` or a new file).

### Step 3 — Event bus

Write `src/pulsecraft/demo/event_bus.py`. Unit-test it.

### Step 4 — Instrumented run

Write `src/pulsecraft/demo/instrumented_run.py`. Add the `on_event` parameter to `orchestrator.run_change()` if needed — this is the allowed one-line change. Verify no existing tests break.

Write a small unit test that runs a mocked pipeline with a capturing `on_event` callback and asserts the expected event sequence.

### Step 5 — FastAPI server

Write `src/pulsecraft/demo/server.py`. Wire up routes. Test with `TestClient`.

### Step 6 — CLI subcommand

Write `src/pulsecraft/cli/commands/demo.py`. Wire into `main.py`. Smoke-test: `.venv/bin/pulsecraft demo serve --port 8000` should start the server.

### Step 7 — Frontend scaffolding

Write `index.html` with the basic three-column layout, no interactivity yet. Serve it. Open in browser. Confirm the layout looks close to the spec.

### Step 8 — CSS polish

Write `style.css`. Bring the design to life. Iterate on palette, typography, spacing, until it looks right. This is the most time-consuming step — budget 45-60 minutes.

### Step 9 — JavaScript — static first

Write `app.js` to render a static mock event sequence first (hard-coded in JS). This lets you perfect the animations and component rendering without worrying about backend integration.

### Step 10 — JavaScript — wire up SSE

Replace the static mock with real SSE. Run a real scenario. Confirm events arrive and render correctly.

### Step 11 — Edge cases

Test each of the 5 scenarios. Handle:
- Fixture 001's happy path with HITL trigger
- Fixture 002's short-circuit at SignalScribe's ARCHIVE
- Fixture 006's parallel fan-out
- Fixture 007's MLR HITL trigger
- Fixture 008's clean DELIVERED path

If any scenario surfaces a UI state you haven't designed for (e.g., BUAtlas returns zero affected BUs), add a graceful handler.

### Step 12 — Polish pass

- Animation timings feel right?
- Typography hierarchy clear?
- Colors restrained where they should be, bold where they should be?
- Shimmer effect subtle?
- Agent-vs-code block visually distinct?
- Message previews (Teams card, email, push) look faithful?
- HITL panel convincing?
- Keyboard shortcuts work?
- Cost counter accurate?

### Step 13 — Test and commit

Run tests. Run ruff and mypy. All clean.

Take a few screenshots of the five scenarios at interesting moments. Save to `design/demo/screenshots/` — these will be useful for the one-pager leave-behind and for future documentation.

Commit:

```
feat(demo): Level-1 web UI for Head of AI demo (prompt 15)

Adds a polished, document-like single-page web UI that visualizes the
PulseCraft pipeline end-to-end with real LLM agents. Built for sponsor
demo to the Head of AI.

Architecture:
- FastAPI server with SSE streaming at localhost:8000
- In-memory event bus keyed by run_id
- Instrumented wrapper around orchestrator.run_change() (orchestrator
  unchanged except for one optional on_event parameter)
- Vanilla JS frontend, no framework, no build step
- Typography: Fraunces (serif), Inter (sans), JetBrains Mono
- Warm cream palette with agent-colored accents

Visual moments optimized for Head of AI audience:
- Parallel BUAtlas fan-out with asynchronous card fill-in
- Agent-vs-code split shown as side-by-side preference/enforcement
- Rendered message preview for DELIVERED (Teams card, email, push mocks)
- HITL operator panel preview for AWAITING_HITL
- Progress rail showing pipeline state with clickable stage navigation
- Confidence bars, verb badges, cited-sources expansion
- Full /explain audit trail in a side drawer

Five scenarios featured:
- 01: Clearcut customer-visible change (all agents + priority HITL)
- 02: Internal refactor (system refuses to send)
- 06: Multi-BU parallel fan-out (architectural showpiece)
- 07: MLR-sensitive (policy layer catches it)
- 08: Post-hoc shipped change (clean delivery)

Runs on laptop via `.venv/bin/pulsecraft demo serve`.

All 606 existing tests still pass. 12 new tests for the demo layer.
Zero changes to agent logic, hook logic, or schemas.
```

Do not push unless user asks.

## Rules for this session

- **Additive only.** Orchestrator, agents, hooks, skills, schemas — untouched. One optional parameter added to `run_change` is the only allowed surgical change.
- **No fabricated data in the UI.** Cost, elapsed time, BU names, decisions — all from real runs.
- **No framework creep.** Vanilla JS, vanilla CSS.
- **No deployment.** Laptop-only.
- **Animations respect reduced-motion.** Every animation has a reduced-motion fallback.
- **Budget guard.** If build-time rehearsal runs exceed $5, stop and report. Normal budget should be $2-3.

## Final report

1. Files created (list).
2. Dependencies added to `pyproject.toml`.
3. Test count before/after (606 → ~618).
4. The one-line change to `orchestrator.run_change()` (if used), or confirmation the audit-subscription approach worked without orchestrator changes.
5. Screenshot file paths saved to `design/demo/screenshots/`.
6. Startup command confirmed: `.venv/bin/pulsecraft demo serve` starts the server, `http://localhost:8000` loads.
7. Smoke test: ran all 5 scenarios, all reached expected terminal states.
8. Total LLM cost during build (aim for $2-3).
9. Commit hash.
10. Next: "Ready for demo rehearsal."

---

## [Post-commit] Save this prompt file to the repo

After the main commit lands: **"Save prompt 15 to `prompts/15-demo-ui.md`? (yes/no)"**

If yes: write verbatim, commit with `chore(prompts): archive prompt 15 (demo UI) in repo`.