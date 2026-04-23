# PulseCraft

> AI agents that turn marketplace changes into BU-ready notifications — with safety gates, audit trails, and human-in-the-loop review.

[![Python](https://img.shields.io/badge/python-3.14-blue)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-619%20passing-brightgreen)](#testing)
[![Model](https://img.shields.io/badge/model-claude--sonnet--4--6-orange)](https://docs.anthropic.com/en/docs/about-claude/models/overview)
[![License](https://img.shields.io/badge/license-internal%20AbbVie-red)](#license)
[![Status](https://img.shields.io/badge/status-walking%20skeleton-yellow)](#roadmap)

---

## Overview

BU heads at scale miss important changes or drown in irrelevant ones. Vendor release notes arrive daily; most don't apply to any given BU, and the ones that do require judgment to interpret. Hand-written Slack summaries from PMs don't scale; rule engines break on phrasing changes and can't reason about business relevance; blanket email blasts condition recipients to ignore them.

PulseCraft addresses this with three specialist LLM agents collaborating at six judgment gates, wrapped in a deterministic orchestrator and four guardrail hooks. The system's default answer is always *no* — a change doesn't proceed to the next stage unless a gate affirmatively justifies it. SignalScribe decides whether the change is worth communicating at all and whether the timing is right. BUAtlas, running in parallel for each candidate BU, decides whether that specific BU is genuinely affected and whether the drafted message earns the BU head's attention. PushPilot decides whether now is the right moment to send.

What makes PulseCraft distinctive is the **agent-vs-code split**: agents express preferences ("I think this is worth sending now"); deterministic policy code enforces invariants ("quiet hours say no"). When agent preference conflicts with policy, policy wins and both decisions are logged. This separation keeps the system's safety properties auditable and calibratable without depending on any single LLM's judgment for anything that must be guaranteed. Every decision is captured in an append-only audit chain, replayable with `pulsecraft explain`. Current state: walking skeleton complete on synthetic data, ~$0.15 per change end-to-end with real agents.

---

## Quick start

**Run a fixture through the full pipeline (real agents):**

```bash
# Clone and install
git clone <repo-url> pulsecraft-change-intelligence
cd pulsecraft-change-intelligence
uv venv && uv pip install -e ".[dev]"
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env

# Run a fixture with real agents
.venv/bin/pulsecraft run-change fixtures/changes/change_001_clearcut_communicate.json \
  --real-signalscribe --real-buatlas --real-pushpilot
```

**Explain the decision trail for a processed change:**

```bash
.venv/bin/pulsecraft explain a1b2c3d4
# Resolves 8-char prefix to full change_id and prints the human-readable trail
```

**Review and action HITL-pending items:**

```bash
.venv/bin/pulsecraft pending                              # list all pending
.venv/bin/pulsecraft approve a1b2c3d4 --reviewer "<name>"
.venv/bin/pulsecraft reject  a1b2c3d4 --reason "not relevant to pilot scope"
```

No API key needed for mock-agent runs (default):

```bash
.venv/bin/pulsecraft run-change fixtures/changes/change_001_clearcut_communicate.json
# Uses scripted mock agents — zero cost, <1s response, useful for CLI/hook testing
```

---

## Who this is for

| Role | Pain point | What PulseCraft gives them |
|---|---|---|
| **Head of AI / Sponsor** | Hard to govern agent-based systems; hard to demonstrate to stakeholders | Full audit chain, HITL defaults, agent-vs-code policy split, `/explain` trail |
| **BU communication lead** | Too many irrelevant notifications erode inbox trust | Default-no bias at every gate; per-BU personalization via BUAtlas |
| **Operations / HITL reviewer** | Must approve outgoing notifications with limited context | Structured decision trail via `explain`; HITL queue with typed reasons; operator CLI |
| **InfoSec / compliance** | PII, MLR-sensitive language, and credential leak risk | `pre_ingest` redaction; `pre_deliver` restricted-term sweep; JSONL audit chain |
| **Pilot BU head** | Wants signal, not noise | Gate 4 defaults ADJACENT over AFFECTED when uncertain; gate 5 self-critiques the drafted message |

---

## Example output

After running fixture 001 (`change_001_clearcut_communicate.json`) through the full pipeline with real agents:

```
$ .venv/bin/pulsecraft explain a1b2c3d4
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PulseCraft · Decision Trail
 Change  : Prior Authorization Submission Form — Redesigned Validation UI
 Run     : 2026-04-23T11:44Z
 Journey : RECEIVED → INTERPRETED → ROUTED → PERSONALIZED → AWAITING_HITL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 [SignalScribe]
   Gate 1  COMMUNICATE   0.92   "Visible, customer-facing UI behavior change
                                 affecting all HCP portal users in the specialty
                                 pharmacy ordering workflow."
   Gate 2  RIPE          0.88   "Rollout imminent; decision window open for BU
                                 preparation."
   Gate 3  READY         0.85   "Sufficient context. Change scope and impact
                                 clearly stated."

 [BUAtlas — bu_alpha]
   Gate 4  AFFECTED      0.91   "bu_alpha owns specialty_pharmacy,
                                 hcp_portal_ordering, and prior_auth_workflow —
                                 all three primary impact areas of this change."
   Gate 5  WORTH_SENDING 0.87   "Message is actionable and concise.
                                 Recommended action is clearly scoped."

 [Orchestrator — policy layer]
   HITL trigger : priority_p0 (P0 changes always route to human review)
   → AWAITING_HITL

 Invocations : 2 LLM · $0.13 · 86s
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

For a pure internal refactor (fixture 002), the same command shows a one-gate trail:

```
 [SignalScribe]
   Gate 1  ARCHIVE       0.94   "Internal code refactoring. No external-facing
                                 behavior change. No user impact."
 Journey : RECEIVED → ARCHIVED
 Invocations : 1 LLM · $0.04 · 19s
```

---

## Architecture

The pipeline below shows the three LLM agents (SignalScribe, BUAtlas, PushPilot), the six decision gates they own, the four guardrail hooks that wrap them, and the deterministic orchestration that sequences the whole pipeline.

<svg width="100%" viewBox="0 0 680 1280" xmlns="http://www.w3.org/2000/svg" role="img">
<title>PulseCraft architecture — three agents, six gates, hooks, orchestrator</title>
<desc>Ingest feeds SignalScribe agent (gates 1-3), then BU pre-filter routes to BUAtlas agent running per BU in parallel (gates 4-5), then PushPilot agent decides timing (gate 6). Guardrail hooks wrap each stage. Deterministic orchestrator sequences the pipeline and writes an audit chain that /explain replays.</desc>
<defs>
<marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M2 1L8 5L2 9" fill="none" stroke="context-stroke" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></marker>
<style>
.t { font-family: sans-serif; font-size: 14px; fill: #1e293b; }
.ts { font-family: sans-serif; font-size: 12px; fill: #475569; }
.th { font-family: sans-serif; font-size: 14px; font-weight: 500; fill: #1e293b; }
.arr { stroke: #64748b; stroke-width: 1.5; fill: none; }
.c-purple rect { fill: #EEEDFE; stroke: #534AB7; }
.c-purple .th, .c-purple .t { fill: #3C3489; }
.c-purple .ts { fill: #534AB7; }
.c-teal rect { fill: #E1F5EE; stroke: #0F6E56; }
.c-teal .th, .c-teal .t { fill: #085041; }
.c-teal .ts { fill: #0F6E56; }
.c-coral rect { fill: #FAECE7; stroke: #993C1D; }
.c-coral .th, .c-coral .t { fill: #712B13; }
.c-coral .ts { fill: #993C1D; }
.c-amber rect { fill: #FAEEDA; stroke: #854F0B; }
.c-amber .th, .c-amber .t { fill: #633806; }
.c-amber .ts { fill: #854F0B; }
.c-gray rect { fill: #F1EFE8; stroke: #5F5E5A; }
.c-gray .th, .c-gray .t { fill: #444441; }
.c-gray .ts { fill: #5F5E5A; }
</style>
</defs>

<!-- INPUT: Ingest -->
<g class="c-gray">
<rect x="40" y="20" width="600" height="74" rx="10" stroke-width="0.5"/>
<text class="th" x="340" y="40" text-anchor="middle" dominant-baseline="central">Ingest</text>
<text class="ts" x="340" y="60" text-anchor="middle" dominant-baseline="central">release notes · Jira · ADO · docs · feature flags · incidents</text>
<text class="ts" x="340" y="78" text-anchor="middle" dominant-baseline="central">normalizer produces ChangeArtifact</text>
</g>
<line x1="340" y1="94" x2="340" y2="118" class="arr" marker-end="url(#arrow)"/>

<!-- HOOK: pre_ingest -->
<g class="c-amber">
<rect x="140" y="118" width="400" height="34" rx="6" stroke-width="0.5"/>
<text class="ts" x="340" y="135" text-anchor="middle" dominant-baseline="central">HOOK · pre_ingest · redact PII · fail closed</text>
</g>
<line x1="340" y1="152" x2="340" y2="176" class="arr" marker-end="url(#arrow)"/>

<!-- AGENT 1: SignalScribe -->
<g class="c-purple">
<rect x="40" y="176" width="600" height="186" rx="14" stroke-width="0.5"/>
<text class="th" x="64" y="200" dominant-baseline="central">AGENT · SignalScribe</text>
<text class="ts" x="64" y="218" dominant-baseline="central">interprets the change · produces ChangeBrief with citations</text>
</g>
<g class="c-purple">
<rect x="60" y="240" width="180" height="106" rx="8" stroke-width="0.5"/>
<text class="th" x="150" y="260" text-anchor="middle" dominant-baseline="central">Gate 1</text>
<text class="ts" x="150" y="280" text-anchor="middle" dominant-baseline="central">worth communicating?</text>
<text class="ts" x="150" y="306" text-anchor="middle" dominant-baseline="central">COMMUNICATE</text>
<text class="ts" x="150" y="322" text-anchor="middle" dominant-baseline="central">ARCHIVE</text>
<text class="ts" x="150" y="338" text-anchor="middle" dominant-baseline="central">ESCALATE</text>
</g>
<g class="c-purple">
<rect x="250" y="240" width="180" height="106" rx="8" stroke-width="0.5"/>
<text class="th" x="340" y="260" text-anchor="middle" dominant-baseline="central">Gate 2</text>
<text class="ts" x="340" y="280" text-anchor="middle" dominant-baseline="central">is it ripe?</text>
<text class="ts" x="340" y="306" text-anchor="middle" dominant-baseline="central">RIPE</text>
<text class="ts" x="340" y="322" text-anchor="middle" dominant-baseline="central">HOLD_UNTIL(date)</text>
<text class="ts" x="340" y="338" text-anchor="middle" dominant-baseline="central">HOLD_INDEFINITE</text>
</g>
<g class="c-purple">
<rect x="440" y="240" width="180" height="106" rx="8" stroke-width="0.5"/>
<text class="th" x="530" y="260" text-anchor="middle" dominant-baseline="central">Gate 3</text>
<text class="ts" x="530" y="280" text-anchor="middle" dominant-baseline="central">clear enough?</text>
<text class="ts" x="530" y="306" text-anchor="middle" dominant-baseline="central">READY</text>
<text class="ts" x="530" y="322" text-anchor="middle" dominant-baseline="central">NEED_CLARIFICATION</text>
<text class="ts" x="530" y="338" text-anchor="middle" dominant-baseline="central">UNRESOLVABLE</text>
</g>
<line x1="340" y1="362" x2="340" y2="386" class="arr" marker-end="url(#arrow)"/>

<!-- HOOK: post_agent (after SignalScribe) -->
<g class="c-amber">
<rect x="100" y="386" width="480" height="34" rx="6" stroke-width="0.5"/>
<text class="ts" x="340" y="403" text-anchor="middle" dominant-baseline="central">HOOK · post_agent · schema · citations · confidence · fail closed</text>
</g>
<line x1="340" y1="420" x2="340" y2="444" class="arr" marker-end="url(#arrow)"/>

<!-- BU pre-filter -->
<g class="c-gray">
<rect x="160" y="444" width="360" height="52" rx="6" stroke-width="0.5"/>
<text class="th" x="340" y="464" text-anchor="middle" dominant-baseline="central">BU pre-filter (code)</text>
<text class="ts" x="340" y="482" text-anchor="middle" dominant-baseline="central">intersects ChangeBrief.impact_areas with BU registry</text>
</g>
<line x1="340" y1="496" x2="340" y2="520" class="arr" marker-end="url(#arrow)"/>

<!-- AGENT 2: BUAtlas -->
<g class="c-teal">
<rect x="40" y="520" width="600" height="220" rx="14" stroke-width="0.5"/>
<text class="th" x="64" y="544" dominant-baseline="central">AGENT · BUAtlas</text>
<text class="ts" x="64" y="562" dominant-baseline="central">personalizes per BU · parallel fan-out · one invocation per candidate BU</text>
</g>
<g class="c-teal">
<rect x="60" y="580" width="180" height="140" rx="8" stroke-width="0.5"/>
<text class="th" x="150" y="600" text-anchor="middle" dominant-baseline="central">Instance · BU α</text>
<text class="ts" x="150" y="620" text-anchor="middle" dominant-baseline="central">Gate 4: affected?</text>
<text class="ts" x="150" y="636" text-anchor="middle" dominant-baseline="central">AFFECTED</text>
<text class="ts" x="150" y="652" text-anchor="middle" dominant-baseline="central">ADJACENT · NOT_AFFECTED</text>
<text class="ts" x="150" y="676" text-anchor="middle" dominant-baseline="central">Gate 5: worth sending?</text>
<text class="ts" x="150" y="692" text-anchor="middle" dominant-baseline="central">WORTH_SENDING</text>
<text class="ts" x="150" y="708" text-anchor="middle" dominant-baseline="central">WEAK · NOT_WORTH</text>
</g>
<g class="c-teal">
<rect x="250" y="580" width="180" height="140" rx="8" stroke-width="0.5"/>
<text class="th" x="340" y="600" text-anchor="middle" dominant-baseline="central">Instance · BU β</text>
<text class="ts" x="340" y="620" text-anchor="middle" dominant-baseline="central">Gate 4: affected?</text>
<text class="ts" x="340" y="636" text-anchor="middle" dominant-baseline="central">AFFECTED</text>
<text class="ts" x="340" y="652" text-anchor="middle" dominant-baseline="central">ADJACENT · NOT_AFFECTED</text>
<text class="ts" x="340" y="676" text-anchor="middle" dominant-baseline="central">Gate 5: worth sending?</text>
<text class="ts" x="340" y="692" text-anchor="middle" dominant-baseline="central">WORTH_SENDING</text>
<text class="ts" x="340" y="708" text-anchor="middle" dominant-baseline="central">WEAK · NOT_WORTH</text>
</g>
<g class="c-teal">
<rect x="440" y="580" width="180" height="140" rx="8" stroke-width="0.5"/>
<text class="th" x="530" y="600" text-anchor="middle" dominant-baseline="central">Instance · BU N</text>
<text class="ts" x="530" y="620" text-anchor="middle" dominant-baseline="central">Gate 4: affected?</text>
<text class="ts" x="530" y="636" text-anchor="middle" dominant-baseline="central">AFFECTED</text>
<text class="ts" x="530" y="652" text-anchor="middle" dominant-baseline="central">ADJACENT · NOT_AFFECTED</text>
<text class="ts" x="530" y="676" text-anchor="middle" dominant-baseline="central">Gate 5: worth sending?</text>
<text class="ts" x="530" y="692" text-anchor="middle" dominant-baseline="central">WORTH_SENDING</text>
<text class="ts" x="530" y="708" text-anchor="middle" dominant-baseline="central">WEAK · NOT_WORTH</text>
</g>
<line x1="340" y1="740" x2="340" y2="764" class="arr" marker-end="url(#arrow)"/>

<!-- HOOK: post_agent (after BUAtlas) -->
<g class="c-amber">
<rect x="100" y="764" width="480" height="34" rx="6" stroke-width="0.5"/>
<text class="ts" x="340" y="781" text-anchor="middle" dominant-baseline="central">HOOK · post_agent · validates each BU brief · fail closed</text>
</g>
<line x1="340" y1="798" x2="340" y2="822" class="arr" marker-end="url(#arrow)"/>

<!-- AGENT 3: PushPilot -->
<g class="c-coral">
<rect x="40" y="822" width="600" height="150" rx="14" stroke-width="0.5"/>
<text class="th" x="64" y="846" dominant-baseline="central">AGENT · PushPilot</text>
<text class="ts" x="64" y="864" dominant-baseline="central">decides delivery timing · preference only — code enforces invariants</text>
</g>
<g class="c-coral">
<rect x="140" y="884" width="400" height="74" rx="8" stroke-width="0.5"/>
<text class="th" x="340" y="902" text-anchor="middle" dominant-baseline="central">Gate 6 · right time to send?</text>
<text class="ts" x="340" y="924" text-anchor="middle" dominant-baseline="central">SEND_NOW · HOLD_UNTIL(time)</text>
<text class="ts" x="340" y="940" text-anchor="middle" dominant-baseline="central">DIGEST · ESCALATE</text>
</g>
<line x1="340" y1="972" x2="340" y2="996" class="arr" marker-end="url(#arrow)"/>

<!-- HOOK: pre_deliver -->
<g class="c-amber">
<rect x="60" y="996" width="560" height="68" rx="6" stroke-width="0.5"/>
<text class="th" x="340" y="1014" text-anchor="middle" dominant-baseline="central">HOOK · pre_deliver · policy enforcement · fail closed</text>
<text class="ts" x="340" y="1034" text-anchor="middle" dominant-baseline="central">quiet hours · rate limits · approved channels · dedupe</text>
<text class="ts" x="340" y="1050" text-anchor="middle" dominant-baseline="central">restricted terms (MLR · commitments · sensitive data)</text>
</g>
<line x1="340" y1="1064" x2="340" y2="1088" class="arr" marker-end="url(#arrow)"/>

<!-- Terminal states bar -->
<g class="c-gray">
<rect x="40" y="1088" width="600" height="60" rx="10" stroke-width="0.5"/>
<text class="th" x="340" y="1106" text-anchor="middle" dominant-baseline="central">Terminal state</text>
<text class="ts" x="340" y="1126" text-anchor="middle" dominant-baseline="central">DELIVERED · SCHEDULED · AWAITING_HITL · HELD · ARCHIVED · FAILED</text>
<text class="ts" x="340" y="1142" text-anchor="middle" dominant-baseline="central">render: Teams card · email · push · portal digest</text>
</g>

<!-- Side-channel annotations -->
<text class="ts" x="40" y="1172" dominant-baseline="central">Orchestrator (deterministic Python) sequences the pipeline, applies the state machine, routes anything uncertain to HITL queue.</text>
<text class="ts" x="40" y="1192" dominant-baseline="central">Audit hook (fail open) writes an append-only JSONL chain after every agent and every hook · replayable via pulsecraft explain</text>
<text class="ts" x="40" y="1212" dominant-baseline="central">Config: policy.yaml · channel_policy.yaml · bu_registry.yaml · bu_profiles.yaml — thresholds, quiet hours, approved channels, MLR terms</text>

<!-- Legend -->
<rect x="40" y="1238" width="14" height="10" class="c-purple" stroke-width="0.5" rx="2"/>
<text class="ts" x="62" y="1246" dominant-baseline="central">LLM agent</text>
<rect x="130" y="1238" width="14" height="10" class="c-teal" stroke-width="0.5" rx="2"/>
<text class="ts" x="152" y="1246" dominant-baseline="central">LLM agent · parallel</text>
<rect x="268" y="1238" width="14" height="10" class="c-coral" stroke-width="0.5" rx="2"/>
<text class="ts" x="290" y="1246" dominant-baseline="central">LLM agent</text>
<rect x="358" y="1238" width="14" height="10" class="c-amber" stroke-width="0.5" rx="2"/>
<text class="ts" x="380" y="1246" dominant-baseline="central">hook</text>
<rect x="420" y="1238" width="14" height="10" class="c-gray" stroke-width="0.5" rx="2"/>
<text class="ts" x="442" y="1246" dominant-baseline="central">deterministic code</text>
</svg>

### Architecture walkthrough

Read the diagram top to bottom. Each layer is described below.

**Ingest (gray, top)**
- Adapters for five source types: release notes, Jira tickets, ADO work items, documents, feature flags, incidents.
- Each adapter is a pure function with an injectable transport — fixtures in dev, real APIs in production.
- A shared normalizer converts source-specific payloads into the canonical `ChangeArtifact` schema.
- No LLM calls at this stage; pure data transformation.

**Hook · pre_ingest (amber)**
- Redacts sensitive markers (SSN, DOB, MRN, emails, phone numbers, API keys) from `raw_text` before any agent sees it.
- Fail closed: if redaction fails, the pipeline rejects the input with a `FAILED` terminal state rather than risk leaking PII into an agent prompt.

**AGENT · SignalScribe (purple)**
- The first LLM agent. Reads the `ChangeArtifact` and decides whether the change is *worth communicating at all*.
- Owns three gates in sequence:
  - **Gate 1 — worth communicating?** Verbs: `COMMUNICATE`, `ARCHIVE`, `ESCALATE`. Archives internal refactors; escalates genuinely ambiguous artifacts.
  - **Gate 2 — is it ripe?** Verbs: `RIPE`, `HOLD_UNTIL(date)`, `HOLD_INDEFINITE`. Holds changes that aren't yet visible to users.
  - **Gate 3 — clear enough to hand off?** Verbs: `READY`, `NEED_CLARIFICATION`, `UNRESOLVABLE`. Requests human clarification on muddled inputs.
- Produces a `ChangeBrief` with citations back to the source material, impact areas, and a confidence score.
- Any terminal verb other than Gate 3 `READY` short-circuits the pipeline (the change archives, holds, or routes to HITL).

**Hook · post_agent (amber)**
- Validates every agent's output after invocation.
- Checks: output validates against its Pydantic schema; any decision citing evidence has a corresponding source entry; confidence meets the policy threshold for its gate and verb combination.
- Fires after SignalScribe, after each BUAtlas fan-out instance, and after PushPilot.
- Fail closed: failures route to `AWAITING_HITL` with a `post_agent_validation_failed` reason.

**BU pre-filter (gray, code)**
- Deterministic Python. Intersects `ChangeBrief.impact_areas` with each BU's `owned_product_areas` from `bu_registry.yaml`.
- Produces the list of *candidate* BUs that BUAtlas will evaluate. BUs with no overlap don't even get examined.
- Recall-biased — when in doubt, include; BUAtlas (gate 4) applies precision at LLM cost.

**AGENT · BUAtlas (teal)**
- The second LLM agent. Runs **once per candidate BU, in parallel**, with isolated context per invocation.
- Each instance sees only its own BU's profile — never another BU's data. This isolation is the architectural guarantee that BUAtlas cannot be influenced by cross-BU reasoning.
- Owns two gates per BU:
  - **Gate 4 — is this BU actually affected?** Verbs: `AFFECTED`, `ADJACENT`, `NOT_AFFECTED`. Defaults toward ADJACENT when uncertain — false positives (notifying uninvolved BUs) are the highest trust-erosion risk.
  - **Gate 5 — is the drafted message worth this BU head's attention?** Verbs: `WORTH_SENDING`, `WEAK`, `NOT_WORTH`. Self-critiques its own draft.
- Produces one `PersonalizedBrief` per candidate BU, each with per-BU `why_relevant`, recommended actions, and message variants (push, Teams, email).
- Fan-out uses `asyncio.gather` with a semaphore to cap concurrency. Per-BU failures become `FanoutFailure` objects rather than killing the whole fan-out.

**AGENT · PushPilot (coral)**
- The third LLM agent. Runs once per `WORTH_SENDING` PersonalizedBrief.
- Owns one gate:
  - **Gate 6 — is now the right time?** Verbs: `SEND_NOW`, `HOLD_UNTIL(time)`, `DIGEST`, `ESCALATE`.
- Critical design choice: PushPilot expresses *preference*, code enforces *invariants*. PushPilot may say `SEND_NOW` even if recipient is in quiet hours — the subsequent `pre_deliver` hook will downgrade to `HOLD_UNTIL` and log both the agent's preference and the code override. This separation lets us calibrate policy by comparing agent judgment against enforced outcomes.

**Hook · pre_deliver (amber)**
- The last line of defense before anything gets sent.
- Enforces: quiet hours (recipient timezone), per-BU and per-recipient rate limits, approved channels per priority tier, dedupe (replay-safe via hash of change_id + BU + recipient + variant), restricted-term sweep on the rendered message (MLR-sensitive language, commitments, sensitive data markers).
- Fail closed with specific downgrade semantics: downgrade to `HOLD_UNTIL` for quiet hours and rate limits; route to `AWAITING_HITL` for dedupe conflicts, MLR hits, or restricted-term matches.

**Terminal state (gray, bottom)**
- Every change ends in one of six states:
  - `DELIVERED` — message sent; audit trail complete.
  - `SCHEDULED` — hold or digest queued for future delivery.
  - `AWAITING_HITL` — routed to human review (priority, MLR, low confidence, dedupe conflict, or explicit agent escalation).
  - `HELD` — gate 2 said hold; waiting for rollout signal.
  - `ARCHIVED` — gate 1 said archive; no further action.
  - `FAILED` — unrecoverable error, audit record captures the failure reason.
- Rendering happens inline on the `SEND_NOW` path: Jinja2 templates produce Teams adaptive cards, email bodies (text + HTML), push payloads, or portal digest markdown. Injectable send transports handle the wire call (file-write in dev; Microsoft Graph / SMTP / push services in production).

**Orchestrator (not a box — the whole vertical spine)**
- Deterministic Python. Not an agent, not an LLM call.
- Responsibilities: sequencing the pipeline, applying the state machine, loading configuration, routing on agent decisions, enforcing the fail-open/fail-closed semantics of each hook, and writing audit records after every step.
- Routes anything uncertain to the HITL queue (`queue/hitl/pending/`), where operator commands (`pulsecraft approve` / `reject` / `edit` / `answer`) let a human resolve.

**Audit (not a box — pervasive)**
- Every agent invocation, hook invocation, policy check, state transition, and delivery attempt writes an append-only JSONL record to `audit/<YYYY-MM-DD>/<change_id>.jsonl`.
- Records capture actor, timestamp, input hash, decision, reasoning summary, and (for agent invocations) LLM cost and latency.
- Replayable via `pulsecraft explain <change_id>` — produces a human-readable decision trail showing every gate that fired, every hook outcome, every HITL trigger, and the final drafted message (if any). Scoped to the latest run by default; `--all` shows full history.
- The audit hook itself is the only fail-open hook: if audit write fails, the pipeline continues and the error is logged. Losing a decision to an audit bug would be worse than a gap in audit history.

**Configuration — where the thresholds live**
- `policy.yaml` — confidence thresholds per gate and verb, HITL triggers (priority_p0, mlr_sensitive, etc.), restricted-term lists.
- `channel_policy.yaml` — approved channels per priority tier, digest cadence, dedupe window hours.
- `bu_registry.yaml` — BU identifiers and their owned product areas (used by BU pre-filter).
- `bu_profiles.yaml` — per-BU heads, timezones, communication preferences (used by BUAtlas and PushPilot).
- Policy is invariant-like: changing a threshold in YAML changes system behavior without touching code. Policy decisions are always code-enforced, never agent-enforced.

---

## How the system thinks

The central data structure is the `PersonalizedBrief` — BUAtlas's per-BU output, containing both the gate decisions and the drafted message. Here is a representative example from a `WORTH_SENDING` run on fixture 001 for bu_alpha:

```json
{
  "schema_version": "1.0",
  "personalized_brief_id": "f7e3c2b1-9d4a-4f86-b5e2-3a8c1d7f0e94",
  "change_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "brief_id": "f7e3c921-4b58-4d2a-9e06-1c8a5b2f0d73",
  "bu_id": "bu_alpha",
  "produced_at": "2026-04-23T11:57:08Z",
  "produced_by": { "agent": "buatlas", "version": "1.0",
                   "invocation_id": "9b1c2d3e-4f5a-6b7c-8d9e-0f1a2b3c4d5e" },
  "relevance": "affected",
  "priority": "P0",
  "why_relevant": "bu_alpha owns specialty_pharmacy, hcp_portal_ordering, and
                   prior_auth_workflow — all three primary impact areas of this
                   change. The prior auth form redesign directly changes the
                   daily workflow of the specialty pharmacy team.",
  "recommended_actions": [
    { "owner": "<head-alpha>",
      "action": "Brief specialty pharmacy staff on the new inline validation
                 behavior before rollout — field errors now surface in real time
                 rather than on form submission.",
      "by_when": "2026-04-27" }
  ],
  "message_variants": {
    "push_short": "HCP portal prior auth form updated: inline validation now live. Brief your team.",
    "teams_medium": "The prior authorization submission form in the HCP portal has been redesigned
                     with inline field validation. Errors surface in real time rather than on form
                     submission. Action for bu_alpha: brief specialty pharmacy staff before
                     rollout (target: 2026-04-28).",
    "email_long": "Subject: HCP Portal — Prior Authorization Form: inline validation redesign\n\n
                   The HCP portal prior authorization submission form has been updated. The
                   primary change: field-level validation now surfaces inline as users type,
                   replacing the previous submit-and-fail-with-errors behavior. ..."
  },
  "decisions": [
    { "gate": 4, "verb": "AFFECTED", "confidence": 0.91,
      "reason": "bu_alpha owns all three primary impact areas...", "agent": { "name": "buatlas" } },
    { "gate": 5, "verb": "WORTH_SENDING", "confidence": 0.87,
      "reason": "Message is actionable and concise. Recommended action clearly scoped.",
      "agent": { "name": "buatlas" } }
  ],
  "assumptions": ["Rollout to all HCP portal users confirmed for 2026-04-28."],
  "confidence_score": 0.87
}
```

The structure is six layers:
1. **Identity** — `personalized_brief_id`, `change_id`, `brief_id`, `bu_id` form a traceable chain back to the source artifact.
2. **Relevance verdict** — gate 4 `relevance` + `priority`, always explicit.
3. **Why** — `why_relevant` is a concrete, BU-specific mechanism of impact, not a generic summary.
4. **What to do** — `recommended_actions` with owner and optional deadline.
5. **What to say** — `message_variants` for three channel lengths (push ≤ 240 chars, Teams ≤ 600, email ≤ 1 200).
6. **How confident** — gate decisions with individual confidence scores; `assumptions` that could invalidate the analysis if wrong.

---

## Decision guides

### Gate 1 — worth communicating?

```
Is there a visible behavior change for any user, HCP, patient, partner, or system?
│
├─ NO  → ARCHIVE  (internal refactor, no user impact)
│
└─ YES → Is the change ambiguous, security-sensitive, or potentially regulated?
         │
         ├─ YES → ESCALATE  (route to human before gate 2)
         │
         └─ NO  → COMMUNICATE  (proceed to gate 2)
```

### Gate 4 — is this BU affected?

```
Do any of this BU's owned_product_areas appear in the change's impact_areas?
│
├─ NO  → NOT_AFFECTED  (skip entirely)
│
└─ YES → Is the BU's workflow directly changed, or only topically related?
         │
         ├─ Directly → AFFECTED   (proceed to gate 5)
         │
         └─ Topical  → ADJACENT   (note in digest; no priority notification)
```

Default bias is ADJACENT when uncertain. False positives (notifying uninvolved BUs) erode BU trust faster than false negatives.

### Gate 6 — right time to send?

```
Is the recipient in working hours (their timezone)?
│
├─ NO  → HOLD_UNTIL(next working window)
│
└─ YES → Would rate limit be breached?
         │
         ├─ YES → DIGEST (or HOLD_UNTIL if near cap)
         │
         └─ NO  → Is this a digest-channel recipient AND priority ≤ P2?
                  │
                  ├─ YES → DIGEST
                  │
                  └─ NO  → SEND_NOW
```

Note: PushPilot expresses this preference. Quiet hours and rate limits are re-enforced as hard constraints by the `pre_deliver` hook, regardless of what PushPilot said.

### HITL trigger routing

```
Evaluated in priority order — first match wins:
│
├─ priority_p0                    → AWAITING_HITL (high-stakes change, always reviewed)
├─ second_weak_from_gate_5        → AWAITING_HITL (two consecutive WEAK gate-5 verdicts)
├─ confidence_below_threshold     → AWAITING_HITL (uncertain decision)
├─ any_agent_escalate             → AWAITING_HITL (agent explicitly routed up)
├─ gate_3_need_clarification      → AWAITING_HITL (questions for operator)
├─ gate_3_unresolvable            → AWAITING_HITL (open-ended escalation)
├─ restricted_term_detected       → AWAITING_HITL (commitment / MLR / credential match)
├─ mlr_sensitive_content          → AWAITING_HITL (medical/legal/regulatory review)
└─ dedupe_or_rate_limit_conflict  → AWAITING_HITL (judgment call on duplication)

No trigger? → proceed to PushPilot.
```

---

## Configuration

### Confidence thresholds (`config/policy.yaml`, excerpt)

```yaml
confidence_thresholds:
  signalscribe:
    gate_1_communicate: 0.75   # below → ESCALATE
    gate_1_archive: 0.60
    gate_2_ripe: 0.70
    gate_3_ready: 0.75
  buatlas:
    gate_4_affected: 0.60      # below → downgrade to ADJACENT
    gate_5_worth_sending: 0.60
  pushpilot:
    gate_6_any: 0.60

hitl_triggers:
  - priority_p0
  - mlr_sensitive_content_detected
  - restricted_term_detected
  - confidence_below_threshold
  - any_agent_escalate
  - gate_3_need_clarification
  - gate_3_unresolvable
  - dedupe_or_rate_limit_conflict_requiring_judgment
```

### Channel routing (`config/channel_policy.yaml`, excerpt)

```yaml
approved_channels:
  global: [teams, email]      # approved for all BUs
  restricted:
    push: [bu_beta]            # opt-in only; most BUs use teams/email

channel_selection_rules:
  - when: { priority: P0 }
    channel: teams
    also_send_to: [email]      # P0 is dual-channel by default
  - when: { priority: P1 }
    channel: teams
  - when: { priority: P2 }
    channel: email

quiet_hours_default:
  timezone: "America/Chicago"
  start: "19:00"
  end: "07:00"
```

### Preset operating modes

Rather than switching config files, PulseCraft's three operating modes override `policy.yaml` values at startup:

**Strict (pilot default)** — minimum false positives; every uncertain decision goes to human review.

```yaml
# policy_overrides/strict.yaml
confidence_thresholds:
  signalscribe:
    gate_1_communicate: 0.85
    gate_3_ready: 0.85
  buatlas:
    gate_4_affected: 0.70
hitl_triggers:
  - priority_p0
  - confidence_below_threshold   # fires more often with higher thresholds
  - mlr_sensitive_content_detected
  - restricted_term_detected
  - any_agent_escalate
```

**Permissive (exploratory dev)** — higher tolerance; fewer HITL interruptions; useful when mapping fixture coverage.

```yaml
# policy_overrides/permissive.yaml
confidence_thresholds:
  signalscribe:
    gate_1_communicate: 0.60
    gate_3_ready: 0.60
  buatlas:
    gate_4_affected: 0.50
hitl_triggers:
  - priority_p0
  - mlr_sensitive_content_detected
```

**Demo (sponsor presentations)** — balanced; HITL fires for P0 and MLR; all other gates proceed. Uses mock agents so no API key needed.

```bash
# Demo mode: mock agents + demo policy overrides
.venv/bin/pulsecraft run-change fixtures/changes/change_001_clearcut_communicate.json
# --real-* flags absent → mock agents used automatically
```

---

## Hooks

| Hook | Stage | Reuses | Fail mode |
|---|---|---|---|
| `pre_ingest` | Before SignalScribe sees `raw_text` | `skills/ingest/redaction` | **closed** → `FAILED` |
| `post_agent` | After each agent invocation | `skills/policy` (confidence + restricted_terms) | **closed** → `AWAITING_HITL` |
| `pre_deliver` | Before render + send | `skills/policy` + `skills/dedupe` + config | **closed** → `HOLD_UNTIL` or `AWAITING_HITL` |
| `audit_hook` | Around all of above | `skills/audit_skill` | **open** — never blocks pipeline |

**The routing-verb exception.** When any agent decision in a set is a routing verb (`ESCALATE`, `ARCHIVE`, `HOLD_INDEFINITE`, etc.), the `post_agent` hook skips confidence checks for *all* decisions in that set. Reason: if the agent self-routed to a hold/review state, the positive-path confidence is irrelevant — the routing decision is itself the safeguard. This was discovered during the first dryrun and corrected before the eval baseline was recorded.

---

## Operator commands

All commands accept `--json` for machine-readable output. Change IDs can be provided as 8-character prefixes.

| Command | Purpose |
|---|---|
| `run-change` | Drive a fixture through the pipeline with selectable real or mock agents |
| `dryrun` | Same as `run-change` but defaults to mock agents; prints a decision summary without persisting |
| `ingest` | Fetch an artifact from a source system and optionally run it through the pipeline |
| `explain` | **Human-readable decision trail** for a change_id (default: latest run; `--all` for full history; `--list-runs` to enumerate) |
| `pending` | List HITL-pending items with status and trigger reasons |
| `approve` | Approve a HITL-pending change and advance the pipeline |
| `reject` | Reject a HITL-pending change with a reason |
| `edit` | Modify the pending payload before approving |
| `answer` | Supply answers to gate-3 clarification questions |
| `replay` | Re-run a completed change from saved inputs |
| `digest` | List and dispatch scheduled digest deliveries |
| `audit` | Print the raw audit JSONL chain for a change_id |
| `metrics` | Aggregate pipeline metrics (cost, latency, terminal-state distribution) over a time window |

`explain` is the observability star of the CLI. It reconstructs what every agent decided and why, which hook fired, which HITL trigger routed where, and what the drafted message looked like — all from the append-only audit chain, no live state required.

---

## Use cases

| Scenario | Change frequency | Key gates | Typical terminal state |
|---|---|---|---|
| Formulary update affecting specialty pharmacy BU | 5–20/quarter | Gate 4 identifies bu_alpha; gate 5 validates message quality | `DELIVERED` to bu_alpha head after HITL approval |
| MLR-sensitive HCP educational module update | 10–30/month | `pre_deliver` restricted-term sweep catches clinical language | `AWAITING_HITL` (mlr_sensitive trigger) |
| Feature flag ramping to 5% of internal users | 50–100/month | Gate 2: `HOLD_UNTIL(rollout_date)` — not yet ripe | `HELD` until rollout date |
| Multi-BU platform change (ordering + analytics) | 2–5/quarter | BUAtlas fan-out: `AFFECTED` for 2 BUs, `ADJACENT` for 1 | `DELIVERED` to 2 BUs; silent skip for 1 |
| Post-hoc: change shipped with no prior notice | Any | Gate 2: `ALREADY_SHIPPED` → `RIPE` — still worth communicating | `DELIVERED` or `AWAITING_HITL` (priority) |
| Pure internal dependency bump | Daily | Gate 1: `ARCHIVE` — no external impact | `ARCHIVED` in one LLM call (~19s, ~$0.04) |

---

## Repository structure

```
pulsecraft-change-intelligence/
│
├── src/pulsecraft/               # main Python package
│   ├── agents/                   #   real LLM-backed agents (signalscribe, buatlas, pushpilot)
│   │   └── buatlas_fanout.py     #   asyncio fan-out + FanoutFailure isolation
│   ├── orchestrator/             #   deterministic pipeline spine
│   │   ├── engine.py             #   run_change(); policy enforcement; HITL routing
│   │   ├── states.py             #   WorkflowState StrEnum; state machine transitions
│   │   ├── audit.py              #   append-only JSONL audit writer + read_chain
│   │   ├── hitl.py               #   HITL queue; HITLReason StrEnum
│   │   ├── agent_protocol.py     #   Protocol interfaces; no concrete agent imports
│   │   └── mock_agents.py        #   scripted mock agents; no LLM calls
│   ├── skills/                   #   reusable skill library
│   │   ├── ingest/               #   5 ingest adapters + normalizer + redaction
│   │   ├── delivery/             #   4 renderers + 3 send adapters + scheduler
│   │   ├── registry.py           #   lookup_bu_candidates (BU pre-filter)
│   │   ├── policy.py             #   check_confidence_threshold, check_restricted_terms
│   │   ├── dedupe.py             #   compute_dedupe_key, has_recent_duplicate
│   │   ├── explain_chain.py      #   build_explanation; run-boundary detection
│   │   └── past_engagement.py    #   lookup_past_engagement from audit history
│   ├── hooks/                    #   guardrail hooks (deterministic; no LLM)
│   │   ├── pre_ingest.py         #   PII + credential redaction
│   │   ├── post_agent.py         #   confidence threshold + restricted-term check
│   │   ├── pre_deliver.py        #   quiet hours + rate limits + channel approval
│   │   └── audit_hook.py         #   append HOOK_FIRED record (fail open)
│   ├── cli/                      #   Typer CLI; 13 subcommands
│   │   └── commands/             #   one module per command
│   ├── schemas/                  #   Pydantic models (ChangeArtifact → ChangeBrief →
│   │                             #     PersonalizedBrief → PushPilotOutput → AuditRecord)
│   ├── config/                   #   typed YAML loaders
│   └── eval/                     #   eval harness (classifier, runner, reporter, aggregator)
│
├── .claude/                      # Claude Code configuration
│   ├── agents/                   #   system prompts: signalscribe.md, buatlas.md, pushpilot.md
│   └── settings.json             #   hook registrations
│
├── schemas/                      # JSON Schema files (data contract source of truth)
├── config/                       # bu_registry.yaml, bu_profiles.yaml, policy.yaml,
│                                 #   channel_policy.yaml
├── templates/                    # Jinja2 templates (teams_card, email, push, portal_digest)
├── fixtures/                     # synthetic change artifacts
│   ├── changes/                  #   8 fixtures covering all gate paths
│   └── sources/                  #   per-adapter source fixtures (release_notes, Jira, …)
├── tests/                        # 619 tests; no LLM calls in default suite
│   ├── unit/                     #   per-module unit tests
│   ├── integration/              #   mock-agent pipeline + CLI smoke tests
│   └── eval/                     #   real-LLM eval (opt-in via PULSECRAFT_RUN_EVAL_TESTS=1)
├── scripts/eval/                 # per-agent eval entry points (run_signalscribe.py, run_all.py …)
├── audit/eval/2026-04-23-baseline/  # committed baseline: stable=10/acceptable=1/PASS
├── design/                       # planning docs, ADRs, decision criteria, dryrun report
├── prompts/                      # prompt-driven build trail (00 → 14.5)
├── pyproject.toml                # package config; pytest markers; ruff + mypy
└── CLAUDE.md                     # developer log: standing instructions for Claude Code sessions
```

---

## Testing

```bash
# Fast suite — unit + integration, zero LLM calls (~4s)
.venv/bin/pytest tests/ -m "not llm and not eval" -q
# 619 passed

# Type checking
.venv/bin/mypy src/pulsecraft/ --ignore-missing-imports

# Linting
.venv/bin/ruff check src/ tests/

# Eval harness — opt-in, real LLM calls (~$1.74, ~27 min full suite)
PULSECRAFT_RUN_EVAL_TESTS=1 .venv/bin/python scripts/eval/run_all.py --runs 3

# Single-agent eval (cheaper)
PULSECRAFT_RUN_EVAL_TESTS=1 .venv/bin/python scripts/eval/run_signalscribe.py --runs 3
```

Committed baseline (`audit/eval/2026-04-23-baseline/`): 15 cases × 3 runs, stable=10, acceptable_variance=1, unstable=1, skipped=3, **PASS** (0 false positives, 0 mismatches). Total cost $1.741 across all three agents.

---

## Comparison with alternatives

| Feature | PulseCraft | PM-written Slack | Email blasts | Rule engines | Generic LLM chat |
|---|---|---|---|---|---|
| Per-BU personalization | ✅ parallel per-BU agents | manual | none | manual authoring | possible via prompting |
| Default-no bias | ✅ structured gates | human judgment | no | depends on rules | depends on prompt |
| Audit trail | ✅ JSONL per change; replayable | message history | send logs | rule logs | chat history |
| Safety gates (PII, MLR) | ✅ hooks | human caution | none | explicit rules only | no built-in guards |
| Operator review workflow | ✅ HITL queue + CLI | ad-hoc | none | often absent | none |
| Handles nuance / phrasing | ✅ LLM reasoning | ✅ human | ❌ no | ❌ brittle | ✅ but uncalibrated |
| Cost at scale | ~$0.15/change | minutes of human time | near-zero | engineering maintenance | ~$0.05–0.20/change (no gates) |

Each alternative has real strengths. PM-written messages carry organizational context no model has. Rule engines are predictable and cheap when the domain is stable. Email blasts require zero infrastructure. PulseCraft trades some of each for the combination of per-BU reasoning, safety gates, and audit accountability.

---

## Roadmap

```
v0.1.0 — walking skeleton (current) ✅
  Three real LLM agents at six judgment gates
  Deterministic orchestrator: state machine, HITL queue, audit writer
  Four guardrail hooks: pre_ingest, post_agent, pre_deliver, audit_hook
  13 operator CLI subcommands including /explain with run scoping
  Per-agent variance-aware eval harness; committed baseline (PASS)
  619 tests; 8 fixtures; ~$0.15 per change end-to-end on synthetic data

v0.2.0 — pilot-ready 🟡
  Real ingest transports: Confluence, Jira API, LaunchDarkly, ServiceNow
  Real delivery transports: Microsoft Graph (Teams), SMTP, push service
  Semantic BU pre-filter: embedding-based similarity alongside keyword intersection
  Production LLM runtime: Bedrock or Azure AI Foundry (pending InfoSec approval)
  Two-BU pilot with real change artifacts and real BU heads
  CI/CD pipeline with deterministic test gate + opt-in eval gate

v0.3.0+ — scale
  MLR co-reviewer agent: auto-review loop with human sign-off
  Feedback loop: BU-head engagement rates feed back into gate-5 calibration
  Multi-channel orchestration: Teams + email + portal in coordinated sequence
  Change-family detection: group related changes into digests automatically
```

---

## Technology stack

| Component | Technology |
|---|---|
| Language | Python 3.14 |
| LLM | `claude-sonnet-4-6` via Anthropic SDK |
| Schema validation | Pydantic v2 + JSON Schema draft 2020-12 |
| CLI | Typer + Rich |
| Templates | Jinja2 |
| Structured logging | structlog |
| Retries | tenacity |
| Package manager | uv |
| Test framework | pytest + pytest-asyncio |

---

## Contributing

This is an internal AbbVie project in active development. The build is prompt-driven: each increment is specified in a prompt file under `prompts/`, run in Claude Code, and committed as a single feature commit with a conventional-commit message.

Before contributing:

1. Read [`CLAUDE.md`](CLAUDE.md) — standing instructions for all Claude Code sessions; explains the build model, naming conventions, and the complete list of what's done vs. planned.
2. Read [`design/planning/01-decision-criteria.md`](design/planning/01-decision-criteria.md) — source of truth for any question about agent behavior. If code and this document disagree, fix the code.
3. Run the default test suite: `.venv/bin/pytest tests/ -m "not llm and not eval" -q`

Convention reminders: snake_case everywhere; no real AbbVie identifiers in any committed file; one prompt = one feature commit; don't silently weaken a test to make it pass.

---

## References

- [Claude Sonnet 4.6 — Anthropic model docs](https://docs.anthropic.com/en/docs/about-claude/models/overview)
- [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python)
- [Pydantic v2](https://docs.pydantic.dev/latest/)
- [Typer](https://typer.tiangolo.com/)
- [Jinja2](https://jinja.palletsprojects.com/)
- [tenacity](https://tenacity.readthedocs.io/)
- [structlog](https://www.structlog.org/)
- [uv](https://docs.astral.sh/uv/)

---

## License

**Internal AbbVie project. All rights reserved. External use requires written permission.**

This repository contains proprietary internal tooling. It is not licensed for redistribution or modification outside AbbVie without written permission.

> **For Claude Code sessions:** read [`CLAUDE.md`](CLAUDE.md) before taking any action in this repo. It contains standing instructions, the full build state, and conventions that must be followed.
