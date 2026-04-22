# Prompt 01 — Commit Planning Documents

> **How to use this prompt.**
> 1. Before running, manually copy `architecture.svg` and `architecture.png` into `design/` in your repo (from the planning output I produced earlier).
> 2. Copy the content below the `---` line into Claude Code, running inside the repo.
> 3. Claude Code will create the design documents, verify, and commit.
>
> **Expected duration:** 20–40 minutes.
>
> **Prerequisite:** Prompt 00 completed cleanly. `design/architecture.svg` and `design/architecture.png` exist in the repo (placed manually by you).
>
> **What this prompt does NOT do:** author any code, agents, skills, commands, or schemas. This prompt only populates `design/` with the planning artifacts from phases P0, P1, P2.

---

# Instructions for Claude Code

You are continuing work on the PulseCraft repository. Prompt 00 scaffolded the project. This prompt (01) populates the `design/` folder with the planning documents produced during phases P0 (problem framing), P1 (pattern decision), and P2 (decision design).

Your job in **this session** is to create the planning documents as text files in the repo, verify, and commit. You are **not** authoring any code, prompts, agent files, skills, schemas, or configuration. Those are separate sessions.

## What "done" looks like for this session

When you finish, the repo will have:

1. All of the design documents listed below, created with exactly the content specified.
2. The architecture diagram files (`architecture.svg` and `architecture.png`) verified to exist in `design/` — **the user placed these manually before running this prompt.**
3. A clean commit with a clear message.
4. A short final report summarizing what was created.

## Pre-flight checks (MANDATORY — do these first)

Before you touch any file, run these checks in order. If any check fails, **stop and report to the user**. Do not proceed.

1. Confirm the current working directory is the `pulsecraft-change-intelligence` repo with a clean or at-least-committed working tree from prompt 00.
2. Confirm `design/` exists.
3. Confirm `design/architecture.svg` exists and is a non-empty file.
4. Confirm `design/architecture.png` exists and is a non-empty file.
5. If either image is missing, stop and tell the user: *"The architecture diagram files are required in `design/` before running this prompt. Copy `architecture.svg` and `architecture.png` from the planning output into the `design/` folder, then re-run."*

## Step-by-step work

### Step 1 — Create `design/README.md`

Create `design/README.md` with the content from the **Appendix A — `design/README.md`** section at the end of this prompt.

### Step 2 — Create `design/00-problem-statement.md`

Create with the content from **Appendix B — `design/00-problem-statement.md`**.

### Step 3 — Create the ADR folder and ADRs

Ensure `design/adr/` exists. Create:

- `design/adr/ADR-001-workflow-with-subagents.md` — content from **Appendix C**
- `design/adr/ADR-002-subagent-topology.md` — content from **Appendix D**

### Step 4 — Create the planning folder and planning docs

Ensure `design/planning/` exists. Create:

- `design/planning/00-planning-index.md` — content from **Appendix E**
- `design/planning/01-decision-criteria.md` — content from **Appendix F** *(this is the largest file, ~500 lines — write it carefully, preserving all section structure and signal bullets)*

### Step 5 — Create the prompts-placeholder README

Ensure `design/prompts-placeholder/` exists (if not already from prompt 00 — it shouldn't be, this is new). Actually, **skip this folder** — we're using the top-level `prompts/` folder for actual Claude Code prompts instead, so a `prompts-placeholder` inside `design/` is no longer needed. If prompt 00 created one, leave it alone; if not, don't create it.

### Step 6 — Verify

Run these verifications in order:

1. **File presence:** every file listed below exists and is non-empty.
   - `design/README.md`
   - `design/00-problem-statement.md`
   - `design/adr/ADR-001-workflow-with-subagents.md`
   - `design/adr/ADR-002-subagent-topology.md`
   - `design/planning/00-planning-index.md`
   - `design/planning/01-decision-criteria.md`
   - `design/architecture.svg`
   - `design/architecture.png`
2. **Markdown sanity:** spot-check 2–3 files by reading the first and last few lines; confirm they start and end cleanly (no truncation, no stray prompt-delimiter markers leaking in).
3. **Image files:** confirm `architecture.png` is a valid PNG (first 8 bytes should be the PNG magic number `89 50 4E 47 0D 0A 1A 0A`). Confirm `architecture.svg` starts with `<?xml` or `<svg`.
4. **Cross-references:** do a quick grep to confirm no lingering references to `architecture-v2-agent-team-with-gates` or `architecture-option-A` or `architecture-option-B` in any of the new files. (Those were old naming conventions.)

If any verification fails, stop and fix before committing.

### Step 7 — Commit

Stage only the new design files and commit with:

```
docs: add P0-P2 planning artifacts (problem, ADRs, decision criteria, architecture)

- design/README.md — master architecture explainer for the repo
- design/00-problem-statement.md — AbbVie-contextualized problem framing, scope, assumptions, risks
- design/adr/ADR-001-workflow-with-subagents.md — pattern decision
- design/adr/ADR-002-subagent-topology.md — fan-out, tool scoping, component-to-primitive map
- design/planning/00-planning-index.md — phase tracker and artifact registry
- design/planning/01-decision-criteria.md — six-gate agent judgment spec (source for agent prompts)
- design/architecture.svg + architecture.png — the architecture diagram

These are the canonical source-of-truth documents. Subsequent prompts reference them; agent prompts derive from the decision criteria.

Next: prompt 02 — author JSON schemas for the data contracts (ChangeArtifact, ChangeBrief, PersonalizedBrief, DeliveryPlan, BUProfile, AuditRecord).
```

Do not push to remote unless the user asks.

## Rules for this session

- **Do not modify any file outside `design/`.** The root README, `src/`, `tests/`, etc. are off-limits in this prompt.
- **Do not "improve" the content of the appendices.** Write them verbatim. If you spot a typo or an inconsistency, note it in your final report but do not fix it without asking the user first. The planning docs are under version control for a reason — changes go through the prompt-driven workflow, not ad-hoc edits.
- **Do not create extra files** (FAQ, glossary, contributor notes, etc.) beyond what is specified. If you think one is needed, add it to your final report as a suggestion for a future prompt.
- **Preserve all markdown formatting exactly** — heading levels, bullet styles, table structure, blockquotes, code fences.
- **For the largest file (Appendix F, decision criteria),** work carefully section by section. It is fine to take multiple passes to make sure nothing is truncated. Verify the last line is present after writing.

## Final report

At the end of the session, produce a short report covering:

1. **Files created** — list with byte sizes or line counts.
2. **Verification results** — each check pass/fail.
3. **Any typos or inconsistencies you spotted** but did not fix (for user review).
4. **Commit hash** — `git log -1 --format="%h %s"`.
5. **Next prompt** — "Ready for prompt 02: schemas."

---

## Appendix A — `design/README.md`

```markdown
# PulseCraft

> **From release notes to BU-ready actions — automatically.**
>
> PulseCraft is an internal GenAI service that turns marketplace product/feature changes into timely, BU-relevant, actionable notifications for BU leadership at AbbVie. It is implemented as a team of three specialist AI agents, each a decision-maker at one or more gates in the change-communication workflow.

---

## Status

**Planning phase complete. Implementation in progress.**

- ✅ P0 — Problem framing
- ✅ P1 — Pattern decision (ADR-001, ADR-002)
- ✅ P2 — Decision design (six-gate criteria + architecture)
- 🚧 P3 — Agent prompt authoring (next)

See [`planning/00-planning-index.md`](planning/00-planning-index.md) for the current status and artifact registry.

---

## What PulseCraft does

BU leaders at AbbVie currently learn about marketplace product/feature changes too late, inconsistently, and with poor signal-to-noise. PulseCraft solves this by ingesting change artifacts, interpreting them, mapping impact to BUs, drafting personalized messages, and delivering (or queueing for approval) via enterprise-approved channels — with full auditability.

**Primary job-to-be-done:** *"When a marketplace feature changes, I (BU head) find out on time, in context, with a clear action — and nothing irrelevant."*

### What PulseCraft is not (v1)

- Not a replacement for the PM release-note authoring process
- Not a customer-facing (HCP, patient) communication system
- Not a GxP-validated system (v1 is explicitly non-GxP; guardrails prevent creep)
- Not a fully autonomous send system (v1 requires human approval for high-impact / low-confidence / policy-sensitive items)

---

## Architecture

![PulseCraft Architecture](architecture.png)

### The agent team

| Agent | Role | Gates owned | Decision verbs |
|---|---|---|---|
| **SignalScribe** | Change understanding | 1, 2, 3 | `COMMUNICATE` / `ARCHIVE` / `ESCALATE` / `RIPE` / `HOLD_UNTIL` / `HOLD_INDEFINITE` / `READY` / `NEED_CLARIFICATION` / `UNRESOLVABLE` |
| **BUAtlas** | Per-BU personalization (parallel) | 4, 5 | `AFFECTED` / `ADJACENT` / `NOT_AFFECTED` / `WORTH_SENDING` / `WEAK` / `NOT_WORTH` |
| **PushPilot** | Delivery orchestration | 6 | `SEND_NOW` / `HOLD_UNTIL` / `DIGEST` / `ESCALATE` |

Each agent's judgment is defined in detail in [`planning/01-decision-criteria.md`](planning/01-decision-criteria.md) — that document is the source of truth for what each agent decides, with what signals, and how to handle failure modes. Agent prompts are generated from this document.

### Key properties

- **Each agent is a decision-maker, not a task-executor.** Agents return decision verbs that the orchestrator respects. Any gate can stop the workflow, escalate to a human, or defer.
- **Orchestrator is deterministic code.** It sequences agent invocations, respects their decisions, manages workflow state, enforces policy invariants, handles the HITL queue, and writes the audit trail.
- **Policy is invariant, not negotiable.** Quiet hours, rate limits, PII redaction, approved channels are enforced in code hooks. Agents reason within policy; they cannot reason around it.
- **BUAtlas runs in parallel per BU with isolated context.** Prevents cross-BU contamination.
- **Every decision is logged with its reason.** `/explain <change-id>` shows the full decision chain.
- **Default bias is *not to send*** unless concrete signals argue for sending. Recipient attention is the scarce resource.

---

## Documents in this folder

| File | Purpose |
|---|---|
| [`README.md`](README.md) | This file — architecture explainer |
| [`00-problem-statement.md`](00-problem-statement.md) | Problem framing, scope, assumptions, risks |
| [`adr/ADR-001-workflow-with-subagents.md`](adr/ADR-001-workflow-with-subagents.md) | Pattern decision |
| [`adr/ADR-002-subagent-topology.md`](adr/ADR-002-subagent-topology.md) | Topology, fan-out, tool scoping |
| [`planning/00-planning-index.md`](planning/00-planning-index.md) | Phase tracker, artifact registry |
| [`planning/01-decision-criteria.md`](planning/01-decision-criteria.md) | Six-gate agent judgment spec |
| [`architecture.svg`](architecture.svg) / [`architecture.png`](architecture.png) | The architecture diagram |

---

## Sponsor

**Head of AI, AbbVie.**
```

## Appendix B — `design/00-problem-statement.md`

```markdown
# PulseCraft — Problem Statement (v1)

> **Status:** Draft for sponsor review
> **Owner:** Oṁ — AI / Architecture
> **Sponsor:** Head of AI
> **Phase:** Phase 0 output → input to Phase 1
> **Revision:** v1 (post Phase-0 discovery)

Assumption tags used throughout this document:
- `[A]` — **Assumption** carried forward for design purposes; must be validated in Track A discovery before freeze.
- `[I]` — **Industry-typical** reference (pharma / life-sciences norm). Not a claim about AbbVie's actual internal state.
- `[TBD]` — **To be determined** by the identified owner.

---

## 1. Executive Summary

PulseCraft is an internal GenAI service that turns marketplace product/feature changes into timely, BU-relevant, actionable notifications for BU leadership. The system ingests change artifacts (release notes, work items, docs, rollout plans), produces a structured, traceable interpretation of each change, maps impact to affected BUs, drafts tailored messages per recipient, and delivers (or queues for human approval) via enterprise-approved channels — with full auditability.

The initiative is sponsored by the **Head of AI** as a capability-building program. Specific target BU(s), validation posture, and production LLM runtime are open decisions to be resolved during Track A discovery.

## 2. Context

### 2.1 The observed problem

BU leaders at AbbVie `[A]` currently learn about marketplace product/feature changes **too late, inconsistently, and with poor signal-to-noise.** Some receive a firehose of release notes irrelevant to their BU; others miss changes that materially affect their team's workflows or customer experience. Downstream BU teams react instead of prepare, creating avoidable churn during rollouts.

### 2.2 Why now

- GenAI maturity has reached the point where structured interpretation of unstructured change artifacts is reliable enough for enterprise use, *provided* the system is architected with appropriate guardrails and human-in-the-loop controls. `[I]`
- The Head of AI sponsorship creates top-cover for establishing an agent-based pattern that can be reused beyond this initiative.
- No existing AbbVie GenAI reference architecture or agent-framework standard has been identified `[A-Q3]`; PulseCraft will likely set precedent, which raises the quality bar on its design artifacts.

### 2.3 What "marketplace" means here

**This term requires disambiguation in Track A** `[TBD-owner: Sponsor org]`. The downstream design is **invariant** to which candidate interpretation is chosen (the pattern, contracts, and topology remain the same), but the **concrete integrations**, **regulatory exposure**, and **source-artifact formats** depend on the answer.

## 3. Primary Job-to-Be-Done

> **"When a marketplace feature changes, I (BU head) find out on time, in context, with a clear action — and nothing irrelevant."**

Decomposed:
- **On time** — within minutes for high-priority items; same-business-day digests for lower-priority items.
- **In context** — why this change matters to *my* BU specifically, not to the enterprise in general.
- **With a clear action** — who on my team to loop in, what to prepare, what decision (if any) is mine.
- **Nothing irrelevant** — zero noise for changes that don't affect my BU; graceful handling of uncertainty ("might affect you — confirm?").

## 4. Users and Stakeholders

| Role | Description | Relationship to v1 |
|---|---|---|
| **BU head** | Primary recipient. Receives personalized notifications. | Primary user of output. |
| **BU delegate(s)** | Named delegates per BU head for routing and escalation. | Secondary recipients. |
| **Marketplace product teams** | Authors of the change artifacts ingested by the system. | Upstream; no change to their workflow in v1. |
| **Head of AI (sponsor)** | Accountable executive. | Approves scope, budget, pattern choice. |
| **Pilot BU co-sponsor** `[TBD]` | BU leader willing to partner for v1 pilot. | Must be identified before pilot go-live. |
| **InfoSec / Data Privacy** | Approves data handling and LLM runtime path. | Track A dependency. |
| **Enterprise Architecture** | Approves architecture pattern and runtime. | Track A dependency. |
| **Legal / Compliance** | Approves validation posture (GxP boundary). | Track A dependency. |
| **MLR (Medical, Legal, Regulatory)** `[I]` | Reviews any content that could constitute scientific or promotional communication. | In scope if messages touch scientific-communication territory; otherwise not. |
| **Operations (PulseCraft itself)** | Humans who review/approve notifications queued by HITL gate. | In scope; operating model TBD. |

## 5. Scope

### 5.1 In scope (v1)

1. Ingest marketplace feature-change artifacts from a **single, well-defined source type** for pilot (exact source `[TBD]`), with adapters scaffolded for release notes, Jira/ADO, docs, feature flags, and incidents.
2. Produce a structured, traceable `ChangeBrief` with confidence scoring and source citations.
3. Map impact to BUs using a **versioned product-area-to-BU registry**.
4. Generate per-BU personalized notifications with exec-appropriate framing and recommended action.
5. Deliver via **one approved channel for pilot** (e.g., Teams or email) to **2–3 pilot BU heads**; channel scaffolding for Teams, email, push, portal digest, ServiceNow.
6. HITL approval gate for high-priority / low-confidence / policy-sensitive items.
7. Full audit trail: sources used, interpretations generated, messages drafted, approvals granted, deliveries made.
8. Telemetry feedback loop (delivered / opened / marked-useful) to inform iteration.

### 5.2 Non-goals (v1)

- Customer-facing (HCP, patient) communications.
- Replacing or modifying the upstream PM release-note authoring process.
- Cross-enterprise change management outside the defined marketplace scope.
- Fully autonomous delivery with no human in the loop.
- Any writeback to regulated (GxP / PV / manufacturing / lab) systems.
- Any content that could constitute scientific or promotional communication without MLR review.
- Multi-region localization.

## 6. Constraints

### 6.1 Regulatory & compliance `[I]` unless noted

- **GxP posture:** v1 proposed as **explicitly non-GxP** with architectural guardrails preventing creep. Final call is Legal/Compliance's `[TBD]`.
- **21 CFR Part 11:** not in scope for v1; architecture preserves option value for later validation if scope expands.
- **HIPAA / PHI:** no PHI shall enter or persist in PulseCraft. Redaction hook at ingest boundary.
- **MLR review:** any drafted message whose content could be construed as scientific communication is routed to MLR queue before delivery.
- **Data residency:** enterprise tenancy; no data egress outside AbbVie-approved cloud boundaries.

### 6.2 Data handling

- No customer data, patient data, adverse-event data, or HCP-identifying data in any PulseCraft artifact.
- No AbbVie-internal secrets, credentials, or security details in drafted messages.
- Source artifacts may reference such data; ingest hook must redact before interpretation.
- Audit logs retained per enterprise retention policy `[TBD]`.

### 6.3 Technology

- **LLM runtime:** Bedrock or Azure AI Foundry `[A]` — final selection is part of this project's scope. Direct Anthropic API path permitted only for dev/eval, not production.
- **Agent framework:** Claude Agent SDK, running as a library inside a standalone Python service.
- **Multi-provider neutrality:** design must not lock in a single LLM vendor at the service layer.
- **Deployment:** enterprise cloud tenancy; containerized service; approved CI/CD `[TBD]`.

### 6.4 Operational

- HITL queue operating hours and SLAs `[TBD]`.
- Quiet hours and rate limits per recipient.
- Escalation path for undeliverable or unactioned high-priority items `[TBD]`.

## 7. Scale Envelope (v1)

| Dimension | v1 target | Design headroom (10×) |
|---|---|---|
| Change events ingested / day | 10–50 (relevant) | 500 |
| BUs in registry | 5–20 | 200 |
| Recipients per BU | 1–3 | 10 |
| Channels | 1 (pilot) → 2–4 (v1 exit) | 8 |
| HITL approval latency (p95) | 4 business hours | 30 minutes |
| Change → BU-head notification latency (p95, high-priority) | ≤ 15 min after approval | ≤ 5 min |

Contracts, schemas, and queue boundaries are shaped to scale to the headroom column without rewrite; throughput mechanisms (batching, parallelism, caching) are not v1 deliverables.

## 8. Success Criteria

### 8.1 v1 exit criteria (go / no-go for pilot-to-iteration)

- ≥ 80% of ingested relevant changes result in a draft notification to at least one BU. `[A]`
- ≥ 70% of delivered notifications marked "useful" or equivalent by pilot BU heads. `[A]`
- ≤ 5% false-positive rate (notifications routed to an irrelevant BU).
- Zero policy violations (sensitive data leakage, unapproved channel, quiet-hour breach, off-scope GxP content).
- 100% of delivered notifications are replayable from the audit log.
- HITL approval median latency within agreed SLA.

### 8.2 Leading indicators (observable during build)

- Schema validation pass rate on SignalScribe output.
- Agreement rate between pre-filter BU registry match and LLM confirmation.
- Guardrail hook trigger rate (healthy is non-zero; zero means hooks aren't wired right).

### 8.3 Lagging indicators (observable post-pilot)

- Time from change detection → BU-head acknowledgement.
- Follow-up actions created in BU tooling as a result of a notification.
- "Not relevant" feedback trend over time.

## 9. Open Assumptions

| ID | Assumption | Impact if wrong | Validation method | Owner |
|---|---|---|---|---|
| A-Q1 | Sponsor scope = "marketplace notifications for BU heads" as described | Rescope; unlikely to invalidate pattern | Sponsor alignment conversation | Oṁ |
| A-Q2 | "Marketplace" refers to a single, identifiable product surface | Increases scope; may require multiple registries | Sponsor + product-org conversation | Oṁ + Sponsor org |
| A-Q3 | No existing AbbVie GenAI reference architecture to conform to | If one exists, may require rework of ADR-001/002 | Direct check with EA, InfoSec, AI governance body | Oṁ |
| A-Q4 | LLM runtime selection is in-scope for this project | If pre-decided, accelerates runtime decision | EA / CloudOps conversation | Oṁ |
| A-Q5 | v1 explicitly non-GxP | If v1 is GxP-adjacent, validation posture rewrites cost/timeline | Legal / Compliance review | Sponsor → Legal |
| A-Q6 | Willing pilot BU is identifiable within sponsor's network | If not, pilot delayed | Sponsor office introduction | Oṁ + Sponsor |
| A-M1 | Product-area-to-BU ownership data exists somewhere (EA, PMO, portfolio tooling) | If truly absent, bootstrap cost rises 3–5× | EA / PMO discovery | Oṁ |
| A-M2 | BU heads currently receive change information at all (however poorly) | If they already have a good channel, solution is different | Pilot BU discovery interviews | Oṁ + Pilot BU |
| A-C1 | Enterprise approves Claude Agent SDK as the agent framework | If disapproved, pattern ports to alternative but costs ramp-up time | InfoSec / EA review | Oṁ |
| A-C2 | Bedrock or Azure AI Foundry tenancy with Claude models is available | If neither, LLM runtime becomes a procurement question | CloudOps check | Oṁ |

## 10. Open Risks

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-01 | Scope creep from non-GxP into GxP territory post-launch | Med | High | Hard architectural guardrail: no writeback to regulated systems; explicit GxP boundary |
| R-02 | BU registry maintenance is underestimated and decays | High | High | Versioned registry; ownership assigned to a human role; decay metrics surfaced |
| R-03 | HITL queue becomes a bottleneck; team routes around it | Med | High | SLAs + staffing plan before go-live; design for exception-based review as a graduation |
| R-04 | MLR gate interpretation becomes a political debate slowing delivery | Med | Med | Engage MLR early, not at go-live |
| R-05 | Sponsor mandate is capability-first, not pain-first; pilot BU lacks real urgency | Med | High | Validate real BU pain before committing to a pilot |
| R-06 | Agent framework locks design to single vendor | Low | Med | Multi-provider neutrality at service layer; abstract LLM calls behind an interface |
| R-07 | Source-artifact quality (release notes) is too poor for SignalScribe to extract reliably | Med | Med | Eval harness on fixture artifacts; fallback to "needs human interpretation" as a first-class output |
| R-08 | External GenAI use (design chats) conflicts with internal policy | Low-Med | Med | User confirms with InfoSec before continuing; no internal data in external sessions |

## 11. Dependencies on Track A discovery

Before v1 go-live, the following must be resolved:

1. **Scope confirmation** from sponsor: marketplace definition, target outcome, v1 boundaries.
2. **Validation posture decision** from Legal / Compliance.
3. **LLM runtime decision** from EA / CloudOps.
4. **GenAI governance alignment** — confirmation that no existing AbbVie standard must be conformed to.
5. **Pilot BU identification** — named co-sponsor willing to partner.
6. **Data handling sign-off** by InfoSec / Privacy.

## 12. Revision history

| Version | Author | Summary |
|---|---|---|
| v1 | Oṁ | First full Problem Statement with AbbVie context, assumption tags, risk register |
```

## Appendix C — `design/adr/ADR-001-workflow-with-subagents.md`

```markdown
# ADR-001: Workflow Orchestration with Agentic Subagents

> **Status:** Accepted
> **Deciders:** Oṁ (Architecture) → review by Head of AI, EA, InfoSec
> **Depends on:** Problem Statement v1 (`00-problem-statement.md`)
> **Related:** ADR-002 (subagent topology), ADR-003 (validation posture — pending), ADR-004 (LLM runtime — pending)

---

## Context

The PulseCraft specification describes the system as *"a team of three agents"* — SignalScribe, BUAtlas, PushPilot — that collaboratively understand feature changes, personalize them per BU, and deliver notifications. That framing is useful for **stakeholder communication** but is the wrong framing for **production implementation**.

The architecturally consequential question is not "how many agents?" but **"where do we need an LLM to dynamically decide its own next step, and where is the next step already known?"**

Anthropic's guidance on building effective agents draws a sharp line between:
- **Workflows** — LLMs orchestrated through predefined code paths. Cheaper, predictable, auditable.
- **Agents** — LLMs dynamically directing their own processes and tool use. More capable where flexibility is genuinely needed; harder to reason about, debug, and validate.

The prescription is to start with workflows and escalate to agentic behavior only where it demonstrably pays for itself.

PulseCraft's end-to-end flow is a **stable, well-understood sequence**: change artifact arrives → interpret → map to BUs (fan-out) → draft personalized messages → apply policy and channel rules → deliver or queue for HITL. There is no node in this flow where an LLM needs to decide *"what step do we take next?"* at the meta level. The flexibility and reasoning that LLMs contribute is needed **inside specific nodes** (understanding ambiguous release notes; judging BU relevance; drafting appropriately-toned messages; judging send timing), not *between* them.

This distinction maps directly onto pharma-context requirements `[industry-typical]`:

- **Auditability.** Workflow state transitions are deterministic and replayable. Agentic orchestration requires reconstructing the LLM's trajectory, which is fragile.
- **Validation readiness.** If PulseCraft ever expands toward GxP-adjacent use, a deterministic orchestrator is validatable under conventional software-validation practice; an agentic orchestrator requires a separate validation approach.
- **HITL integration.** Approval gates are first-class workflow states. In an agentic orchestrator they must be negotiated with the agent.
- **Cost predictability.** Workflow LLM calls are counted and budgeted. Agentic orchestration cost varies per run.
- **Failure isolation.** A failure in one node affects that node only.

## Decision

**PulseCraft's production runtime is a deterministic workflow service (Python, running the Claude Agent SDK as a library) that invokes agentic subagents at specific nodes where model-driven reasoning adds clear value. The orchestrator itself is not an agent.**

The "three agents" of the original specification are restructured as:

| Original role | Implementation form |
|---|---|
| Orchestrator / "PulseCraft Controller" | Deterministic workflow service (code). |
| SignalScribe | Agentic subagent (LLM + tools), invoked by the orchestrator. Owns gates 1-3. |
| BUAtlas | Parallel agentic subagent invocations, one per candidate BU. Owns gates 4-5. |
| PushPilot | Agentic subagent for gate 6 (send-timing judgment). Deterministic code around it handles actual delivery, dedupe, policy enforcement. |

Detailed subagent topology, tool scoping, and fan-out mechanics are covered in **ADR-002**.

## Rationale

### Why not a multi-agent peer team (the spec's literal framing)

A peer-agent team — three LLM agents communicating to reach consensus — would add coordination overhead, nondeterminism, and debugging difficulty without buying flexibility the problem actually needs. Peer-agent patterns shine when the division of labor itself is dynamic. PulseCraft's decomposition into "understand → personalize → deliver" does not require LLM-driven meta-coordination.

Additional concerns specific to AbbVie's operating context `[industry-typical]`:
- Validation scoping across a peer-agent system is substantially harder.
- Audit logs in a peer system must reconstruct agent-to-agent dialogues.
- InfoSec and EA review tends to favor patterns that look like "known software with LLM calls inside" over patterns that look like "autonomous entities that talk to each other."

### Why not a single monolithic agent with all the tools

A single agent with every tool would accumulate context bloat, lose per-stage evaluability, prevent parallelizing BU fan-out, and mix different trust boundaries (reading release notes vs. writing to Teams) into one prompt.

### Why not a pure deterministic pipeline with single LLM calls at each stage

Tempting for simplicity but under-powered for specific nodes. SignalScribe benefits from bounded agentic exploration (following document links, querying related work items, iterating on low-confidence interpretations). BUAtlas benefits from reasoning over BU context with scoped tools. PushPilot benefits from reasoning about timing, bundling, and escalation. Single-turn completions under-perform on these tasks.

### Why workflow-with-agentic-subagents

This pattern gives us:
1. Deterministic state progression, auditable and replayable.
2. Agentic reasoning where it earns its keep.
3. Clean HITL integration as workflow states.
4. Per-node evaluation against fixtures.
5. Cost predictability bounded by orchestrator calls.
6. Validation readiness if scope expands.
7. Multi-provider neutrality at the service layer.

## Consequences

### Positive

- Auditable, replayable, validatable system at the orchestrator layer.
- Each subagent is independently evaluatable, versionable, and swappable.
- HITL is a first-class concept.
- Cost and latency per change event are predictable.
- Failure modes are localized.
- Easier to brief EA / InfoSec reviewers.

### Negative

- Less "impressive" as a marketing framing than "three autonomous agents collaborating." Manage in communication.
- Requires us to write and maintain orchestration code.
- Recurring judgment calls about what belongs in code vs. subagent vs. skill (addressed by ADR-002's decision rubric).

### Neutral / requires discipline

- Boundary between "deterministic policy check" and "LLM-based judgment" must be drawn explicitly and re-evaluated as evals come in. First instinct: *code it; escalate to LLM only if code cannot.*
- Workflow state schema is a load-bearing contract.

## Alignment with pharma / enterprise constraints `[industry-typical]`

| Constraint | How this decision aligns |
|---|---|
| Auditability | Workflow state + deterministic transitions = directly auditable. |
| 21 CFR Part 11 readiness (if ever needed) | Non-LLM parts validate conventionally; LLM parts isolated. |
| HITL as default for v1 | Approval is a workflow state. |
| MLR review gating | Inserted as a workflow state; no agent decides to bypass. |
| Data minimization / PHI avoidance | Redaction hook at ingest boundary. |
| Multi-LLM-provider support | LLM calls behind provider-agnostic Agent SDK interface. |
| No writeback to regulated systems | Enforced by orchestrator, not left to agent's judgment. |

## Assumptions that would invalidate this decision

Revisit this ADR if:
- An existing AbbVie GenAI reference architecture mandates a different pattern (A-Q3).
- The Claude Agent SDK is not approved for enterprise use (A-C1).
- Scope expands to genuinely dynamic, open-ended tasks.
- Evals show that subagents do not outperform single-LLM-call alternatives → gracefully downgrade those nodes.

## Communication note (for sponsor conversations)

When presenting to Head of AI or executive audiences, **"team of specialist agents with a deterministic orchestrator"** is accurate and compatible with the "agent team" framing. We are not abandoning the agent framing; we are being precise about where agentic behavior lives. This is a *strengthening* of the original design, not a retreat.
```

## Appendix D — `design/adr/ADR-002-subagent-topology.md`

```markdown
# ADR-002: Subagent Topology and Fan-Out Strategy

> **Status:** Accepted
> **Deciders:** Oṁ (Architecture) → review by Head of AI, EA
> **Depends on:** ADR-001 (workflow-with-agentic-subagents pattern)

---

## Context

ADR-001 established that PulseCraft's production runtime is a deterministic workflow service that invokes **agentic subagents** at specific nodes, and uses **deterministic code** elsewhere.

This ADR specifies:
1. Which runtime components are subagents, which are code, and which are tool calls.
2. How BUAtlas fans out across candidate BUs.
3. The decision rubric for future "subagent vs. skill vs. tool vs. code" questions.
4. Subagent tool scoping and isolation boundaries.

## Decision

### Component-to-primitive mapping

| Component | Runtime form | Claude Agent SDK primitive |
|---|---|---|
| **Orchestrator** | Python service. Owns workflow state machine, queues, retries, idempotency, audit, HITL gate. | Consumes the SDK; not itself an SDK primitive. |
| **SignalScribe** | Agentic subagent invoked per change event. | **Subagent** with scoped read-only tools. Owns gates 1, 2, 3. |
| **BU candidate pre-filter** | Deterministic code (registry lookup). | Code + `lookup-bu-registry` skill. |
| **BUAtlas (per-BU)** | Agentic subagent invoked in parallel, one per candidate BU. | **Subagent** invocations (orchestrator-level parallelism). Owns gates 4, 5. |
| **PushPilot** | Agentic subagent for gate 6. | **Subagent**. Surrounding delivery logic is code. |
| **Policy checks** | Deterministic code + skills. | Skills + hooks (pre-delivery). |
| **Message rendering** | Deterministic code + skills. | Skills (`render-teams-card`, `render-email`, etc.). |
| **Delivery adapters** | Deterministic code. | MCP servers where external systems have MCP interfaces; plain Python clients otherwise. |

### The decision rubric (for future "what-is-this?" calls)

```
Is the step's next action knowable from the current state?
├── YES, and it's a rule check or transformation                   → CODE
├── YES, but needs consistent formatting/parsing/reuse             → SKILL
├── YES, but needs one LLM completion for judgment or generation   → TOOL CALL
└── NO — needs multi-turn reasoning, tool use iteration,
        or dynamic decision-making bounded by a specific goal      → SUBAGENT
```

**Default to the topmost answer that works.** Only escalate when the level above demonstrably cannot do the job.

### Fan-out strategy for BUAtlas

**Decision: orchestrator-level parallel subagent invocations, one per BU that passes the deterministic pre-filter.**

Rejected alternative: a single BUAtlas subagent that iterates over BUs internally.

Rationale:

| Criterion | Per-BU subagent (chosen) | Single-subagent loop |
|---|---|---|
| Cost control | Tight — per-BU cost cap enforced by orchestrator. | Loose — agent can drift. |
| Failure isolation | One BU failing does not affect others. | Partial state risk. |
| Parallelism | Native. | Sequential. |
| Context contamination | None; each invocation sees one BU's profile. | Real risk. |
| Evaluability | Per-BU fixtures, per-BU pass/fail. | Whole-trajectory evals. |
| Auditability | One invocation = one audit record. | Complex reconstruction. |
| Token efficiency | Slightly worse (mitigated by prompt caching). | Slightly better. |

All criteria except token efficiency favor per-BU fan-out. Token efficiency is mitigated by prompt-caching the `ChangeBrief` across parallel calls.

### BU candidate selection

**Decision: deterministic pre-filter from the BU registry, followed by LLM relevance confirmation inside each BUAtlas subagent invocation (gate 4).**

Flow:
1. Orchestrator queries BU registry using `ChangeBrief.impact_areas` → candidate BU set.
2. For each candidate, orchestrator invokes BUAtlas with `{ChangeBrief, BUProfile}`.
3. BUAtlas gate 4: *"Is this BU actually affected?"*
4. If not relevant (or confidence low), return `NOT_AFFECTED` / `ADJACENT` with reasoning. Orchestrator does not proceed to gate 5.
5. If `AFFECTED`, proceed to gate 5 (message-quality self-critique).

Pre-filter eliminates the cost of invoking a subagent for BUs with no possible match. LLM confirmation catches registry staleness and nuanced relevance.

### Message polishing

**Decision: templates-first. No separate LLM polish step in v1.**

BUAtlas produces message *content* (relevance, framing, action). Template skills render content into channel-specific payloads. LLM polish adds a second LLM call on the critical path, a second place for policy violations, and a separate eval target. Defer until evidence shows templates inadequate.

## Subagent specifications

Full prompts are produced in P3; this is the architectural contract.

### SignalScribe

| Aspect | Specification |
|---|---|
| Goal | Produce `ChangeBrief` with citations, confidence, and decision trail for gates 1-3. |
| Input | Raw change artifact + metadata. |
| Output | `ChangeBrief` JSON including `decisions[]` from gates 1-3. |
| Tools (read-only) | `follow-linked-doc`, `query-related-work-item`, `lookup-rollout-schedule`, `resolve-feature-flag` |
| Tools forbidden | Write operations. Channel-delivery tools. BU-registry access. |
| Isolation | One invocation per change event. Fresh context. |
| Max turns | Bounded (~10). |
| Failure mode | Return partial `ChangeBrief` with `status: needs_human_review` rather than fabricate. |

### BUAtlas (per-BU)

| Aspect | Specification |
|---|---|
| Goal | Execute gates 4 and 5; produce `PersonalizedBrief` (or a "not relevant" result). |
| Input | `{ChangeBrief, BUProfile, PastEngagement?}` for one BU. |
| Output | `PersonalizedBrief` JSON with decisions from gates 4-5. |
| Tools (read-only) | `lookup-bu-engagement-history`, `read-bu-profile` |
| Tools forbidden | Write operations. Other BUs' profiles during this invocation. |
| Isolation | One invocation per BU per change event. Fresh context. |
| Max turns | Bounded (~6). |

### PushPilot

| Aspect | Specification |
|---|---|
| Goal | Execute gate 6; produce delivery decision with reason. |
| Input | `{PersonalizedBrief, RecipientPreferences, RecentNotificationVolume, QuietHours}` |
| Output | `DeliveryDecision` JSON (`SEND_NOW` / `HOLD_UNTIL` / `DIGEST` / `ESCALATE`) with reason. |
| Tools (read-only) | Recipient preferences, quiet-hours schedule, recent-notification-volume |
| Tools forbidden | Write operations. Actual send operations (code does those). |
| Isolation | One invocation per notification. Fresh context. |
| Max turns | Bounded (~3). |
| Note | Agent decides; code executes and enforces policy invariants. |

### Shared constraints for all subagents

- **No customer data, PHI, or internal secrets** in any artifact. Redaction at ingest boundary.
- **No unstated commitments or dates.** Only information present in input contracts.
- **Citations required** where input artifacts support them.
- **Explicit uncertainty labeling.** No guessing without flagging.
- **Schema-validated output.** Validation failure → retry with corrective feedback, then HITL.

## Hooks and guardrails

| Hook point | Purpose |
|---|---|
| **PreIngest (code, before SignalScribe)** | PII / PHI / restricted-term redaction of raw artifact. |
| **PostToolUse on SignalScribe** | Schema validation + confidence thresholding + citation presence check. |
| **PostToolUse on BUAtlas** | Schema validation + relevance threshold + message-policy check. |
| **PreDelivery (code, before send)** | Channel eligibility, quiet hours, rate limits, dedupe keys, HITL-approval status check. |
| **Audit hook (all LLM calls)** | Every invocation logged: timestamp, actor (subagent id + version), inputs (hashed), outputs, tools used, decisions, reasons, token counts. |

## Consequences

### Positive

- Clear contracts enable independent development, versioning, evaluation.
- BU fan-out parallelism scales linearly within rate limits.
- No cross-BU contamination.
- Failure of one BU's subagent does not block others.
- Subagents swappable without orchestrator changes.
- Per-BU and per-event cost caps enforceable.

### Negative

- Higher total token consumption (mitigated by prompt caching).
- Orchestrator complexity owns concurrency, rate limiting, retry, aggregation.
- More invocations = more partial-failure surface; retry/fallback must be explicit.

### Neutral / requires discipline

- PushPilot subagent vs. tool call may be revisited after evals. If gate 6 reasoning is essentially single-turn, downgrade.
- Registry quality gates the whole system — decay metrics must be observable.

## Deferred decisions

| ID | Decision | When to resolve |
|---|---|---|
| D4 | HITL approval UI and operating model | Implementation phases |
| D5 | Workflow state store technology | After LLM runtime decision |
| D6 | Canonical idempotency / dedupe key definition | Schema work (prompt 02) |
| D7 | Confidence score calibration method and thresholds | Eval phase |
| D8 | Whether subagents may invoke mid-reasoning HITL | Default for v1: *no* |
```

## Appendix E — `design/planning/00-planning-index.md`

```markdown
# PulseCraft — Planning Index

> **Purpose.** Single place to check *what has been decided, what is in flight, what is next, and where each artifact lives.*
>
> **Owner:** Oṁ

---

## Current phase

**P3 — Agent prompt authoring.** Planning complete (P0-P2). Implementation in progress via prompt-driven Claude Code sessions.

---

## Planning phases

| Phase | Deliverables | Status |
|---|---|---|
| **P0 — Problem framing** | Problem statement, sponsor alignment | ✅ Done |
| **P1 — Pattern decision** | ADR-001 (pattern), ADR-002 (topology) | ✅ Done |
| **P2 — Decision design** | Six-gate decision criteria, architecture | ✅ Done |
| **P3 — Agent prompt authoring** | CLAUDE.md, signalscribe.md, buatlas.md, pushpilot.md | 🚧 In progress |
| **P4 — Schemas and contracts** | JSON schemas for data contracts | ⏳ Next |
| **P5 — Skill prompts and stubs** | Skill definitions, stub implementations | ⏳ After P3-P4 |
| **P6 — Commands** | Slash command prompts | ⏳ After P5 |
| **P7 — Hook prompts** | Hook definitions + policy enforcement logic | ⏳ After P5 |
| **P8 — Fixtures + dryrun** | Synthetic fixtures, first end-to-end dryrun | ⏳ After P3-P7 |
| **P9 — Implementation** | Full Claude Code build | ⏳ Next major phase |

---

## Completed artifacts

All artifacts live under `design/`.

| # | Artifact | Path | Phase | Purpose |
|---|---|---|---|---|
| 1 | Problem Statement v1 | `design/00-problem-statement.md` | P0 | Problem framing, scope, assumptions, risks |
| 2 | ADR-001 — Workflow with subagents | `design/adr/ADR-001-workflow-with-subagents.md` | P1 | Pattern decision |
| 3 | ADR-002 — Subagent topology | `design/adr/ADR-002-subagent-topology.md` | P1 | Topology, fan-out, tool scoping, decision rubric |
| 4 | Decision Criteria v1 | `design/planning/01-decision-criteria.md` | P2 | Six-gate judgment — source of truth for agent prompts |
| 5 | Architecture | `design/architecture.svg` + `design/architecture.png` | P2 | The architecture diagram |
| 6 | README | `design/README.md` | P2 | Architecture explainer |
| 7 | Planning Index (this doc) | `design/planning/00-planning-index.md` | P2 | Status tracker and artifact registry |

---

## Decisions made

| # | Decision | Rationale | Status |
|---|---|---|---|
| D1 | Pattern: workflow with specialized subagents | ADR-001 | Frozen |
| D2 | Three agents: SignalScribe, BUAtlas, PushPilot | ADR-001 | Frozen |
| D3 | Orchestrator is deterministic code | ADR-001 | Frozen |
| D4 | BUAtlas runs in parallel per BU, isolated context | ADR-002 | Frozen |
| D5 | BU candidate selection = pre-filter + LLM confirmation | ADR-002 | Frozen |
| D6 | Templates-first; no LLM polish in v1 | ADR-002 | Frozen |
| D7 | Six decision gates distributed across agents | Decision Criteria | Frozen |
| D8 | Policy is invariant, enforced in code | Decision Criteria | Frozen |
| D9 | Default bias is *not to send*; attention is scarce | Decision Criteria | Frozen |
| D10 | LLM runtime: Claude Code + Agent SDK | README | Frozen |

---

## Open decisions (resolved during P3-P9)

| ID | Decision | Resolution target |
|---|---|---|
| O1 | Exact JSON schema shape for contracts | P4 |
| O2 | Exact prompt format per agent | P3 |
| O3 | Confidence thresholds (numeric) | P3, tuned in evals |
| O4 | WEAK regeneration retry policy | P3 |
| O5 | HOLD_UNTIL re-evaluation mechanism | P5 |
| O6 | Digest cadence per channel | P5 |
| O7 | Skill inventory — final list and per-skill prompts | P5 |
| O8 | Slash command contracts | P6 |
| O9 | Hook invocation points and exact rules | P7 |
| O10 | Fixture set for first dryrun | P8 |

---

## Open questions (Track A dependencies)

| ID | Question | Who answers | Blocks |
|---|---|---|---|
| Q1 | "Marketplace" at AbbVie — which product surface? | Sponsor org | Pilot definition |
| Q2 | Which BU(s) partner for v1 pilot? | Sponsor | P8 fixtures, pilot |
| Q3 | LLM runtime — Bedrock or Azure AI Foundry or other? | EA / CloudOps | Deployment |
| Q4 | Validation posture — v1 is non-GxP? | Legal / Compliance | ADR-003 (pending) |
| Q5 | Existing AbbVie GenAI reference architecture? | EA / AI Governance | Possible rework |
| Q6 | Claude Code / Agent SDK approved by InfoSec? | InfoSec | Go-live |
| Q7 | Product-area-to-BU registry source? | EA / PMO | Registry bootstrap |
| Q8 | HITL operating model — reviewers, SLAs? | Sponsor + Ops | Go-live |
| Q9 | MLR integration — scientific communication risk? | Medical Affairs / MLR | Possible MLR queue state |
| Q10 | External GenAI use for design work allowed? | InfoSec | Design continuation |

---

## Prompt-driven build workflow

All implementation happens via prompts in `/prompts/`, run one at a time in Claude Code.

| Prompt | File | Purpose | Status |
|---|---|---|---|
| 00 | `prompts/00-repo-scaffold.md` | Scaffold repo + Python project | ✅ Done |
| 01 | `prompts/01-commit-planning-docs.md` | Commit planning artifacts | ✅ Done (this prompt) |
| 02 | `prompts/02-schemas.md` | JSON schemas for data contracts | ⏳ Next |
| 03 | `prompts/03-config-fixtures.md` | BU registry, profiles, policy, fixtures | ⏳ |
| 04 | `prompts/04-claude-md-orchestrator.md` | CLAUDE.md orchestrator spec | ⏳ |
| 05 | `prompts/05-agent-signalscribe.md` | SignalScribe prompt | ⏳ |
| 06 | `prompts/06-agent-buatlas.md` | BUAtlas prompt | ⏳ |
| 07 | `prompts/07-agent-pushpilot.md` | PushPilot prompt | ⏳ |
| 08 | `prompts/08-skills-ingest.md` | Ingest adapter skills | ⏳ |
| 09 | `prompts/09-skills-registry-policy.md` | Registry, policy, audit skills | ⏳ |
| 10 | `prompts/10-skills-delivery.md` | Delivery rendering skills | ⏳ |
| 11 | `prompts/11-commands.md` | Operator slash commands | ⏳ |
| 12 | `prompts/12-hooks.md` | Guardrail hooks in settings.json | ⏳ |
| 13 | `prompts/13-dryrun-walkthrough.md` | First end-to-end dryrun | ⏳ |
| 14 | `prompts/14-eval-harness.md` | Fixture-based evals | ⏳ |

---

## Versioning approach

Prompts, schemas, configs, and decision criteria are versioned together. A change to any of them bumps a version and triggers re-eval. The audit log records which version of each was active for any given change event.
```

## Appendix F — `design/planning/01-decision-criteria.md`

```markdown
# PulseCraft — Decision Criteria for Agent Judgment

> **Purpose of this document.** PulseCraft's agents are not task-executors. They are *decision-makers* at specific gates in the change-communication workflow. This document defines what each decision means, what signals to weigh, what the legitimate outputs are, and what failure modes to avoid. It is the load-bearing intellectual content of the agent prompts — the prompts will *encode* this document, not replace it.
>
> **How this document is used.** Each agent's prompt draws its judgment rules from the gate(s) it owns here. When we need to change how an agent decides, we change this document first, then regenerate the prompt.
>
> **Validation path.** Draft v1. Must be reviewed with a real AbbVie communications or change-management professional and adjusted to reflect AbbVie's actual norms before go-live.
>
> **Status:** Draft v1.

---

## Overview — the six gates

| # | Gate | Owner | Decision verbs |
|---|---|---|---|
| 1 | Is this change worth communicating at all? | SignalScribe | `COMMUNICATE` / `ARCHIVE` / `ESCALATE` |
| 2 | Is this change ripe (is the timing right to start communicating)? | SignalScribe | `RIPE` / `HOLD_UNTIL(date)` / `HOLD_INDEFINITE` |
| 3 | Is my understanding clear enough to hand off? | SignalScribe | `READY` / `NEED_CLARIFICATION(questions)` / `UNRESOLVABLE` |
| 4 | Is this BU actually affected (vs. merely adjacent)? | BUAtlas (per BU) | `AFFECTED` / `ADJACENT` / `NOT_AFFECTED` |
| 5 | Is the message I've drafted worth this BU head's attention? | BUAtlas (per BU) | `WORTH_SENDING` / `WEAK` / `NOT_WORTH` |
| 6 | Is right now the right time to send this? | PushPilot | `SEND_NOW` / `HOLD_UNTIL(time)` / `DIGEST` / `ESCALATE` |

Each gate can also emit `ESCALATE` to route to human review when confidence is too low.

**Flow between gates:**

- Gates 1 → 2 → 3 run inside SignalScribe, sequentially. If gate 1 returns `ARCHIVE`, gates 2 and 3 are skipped. If gate 2 returns `HOLD_UNTIL`, SignalScribe returns without attempting gate 3. If gate 3 returns `NEED_CLARIFICATION`, the whole change goes to HITL with questions.
- SignalScribe hands the `ChangeBrief` + decision trail to the orchestrator, which fans out to BUAtlas (one invocation per candidate BU).
- Gates 4 → 5 run inside each BUAtlas invocation. If gate 4 returns `NOT_AFFECTED`, gate 5 is skipped.
- The orchestrator collects all BUAtlas decisions and passes `WORTH_SENDING` personalized briefs to PushPilot.
- Gate 6 runs inside PushPilot, once per notification.

---

## Gate 1 — Is this change worth communicating at all?

**Owner:** SignalScribe
**Decision verbs:** `COMMUNICATE` | `ARCHIVE` | `ESCALATE`

### What this decision means

Not every release note or change artifact warrants a BU-head notification. A bug fix that no one noticed, a silent internal refactor, a copy tweak — these do not belong in a BU head's inbox. Pushing them through creates noise, erodes trust, and teaches recipients to ignore future notifications.

A thoughtful communications lead asks: *"Is there any party, inside or outside AbbVie, whose work or experience will change because of this?"* If no, archive. If yes, continue.

### Signals that favor `COMMUNICATE`

- **Visible behavior change** — users, HCPs, patients, partners, or internal operators will see or feel something different.
- **Customer-facing surface affected** — UI, API response, email content, notification wording, document output.
- **Workflow change** — a step is added, removed, reordered, or restricted.
- **Integration impact** — downstream systems (Veeva, ServiceNow, data pipelines, reporting) consume the affected behavior.
- **Support load implication** — the change will likely generate questions, tickets, or confusion if not pre-communicated.
- **Regulatory or compliance relevance** — even if minor, changes touching labeling, consent flows, audit trails, PV workflows, or data-retention behavior warrant communication.
- **Reversal of a previously communicated state** — we said X last month; now we're doing Y.
- **New capability introduced** — something recipients could now do that they couldn't before.

### Signals that favor `ARCHIVE`

- **Pure internal refactor** — code structure changed, no behavior change, no user impact.
- **Dependency version bumps** with no functional effect.
- **Copy-only edits** where the meaning is unchanged (typo fixes, grammar).
- **Infrastructure changes** transparent to users with no user-observable effect.
- **Bug fixes for edge cases statistically unlikely to have been noticed.**
- **Internal-tool-only changes** where no downstream or external party is affected.

### Signals that favor `ESCALATE`

- **Ambiguous scope** — the artifact says "various improvements" without specifics.
- **Security-sensitive** — the change touches authentication, authorization, or data access in ways that might be sensitive to communicate openly.
- **Unclear reversal** — appears to undo something previously communicated, but the original state is not referenced.
- **Potentially regulated territory** — looks like it might touch GxP, PV, or labeling; when in doubt, route to a human.

### Failure modes to avoid

- **Over-communicating to look thorough.** A communications system's job is to reduce cognitive load, not demonstrate its own work. If in doubt, favor `ARCHIVE` unless a specific signal above is present.
- **Under-communicating because "they'll find out."** If a real workflow or experience changes, communicate.
- **Routing "I'm not sure" to `COMMUNICATE`.** Use `ESCALATE` instead.

### Confidence calibration

- `COMMUNICATE` with confidence ≥ 0.75: proceed.
- `COMMUNICATE` with confidence 0.5–0.75: proceed but flag `low_confidence: true` for HITL sampling.
- `ARCHIVE` with confidence ≥ 0.6: archive with reason.
- Anything below those thresholds, or active uncertainty: `ESCALATE`.

---

## Gate 2 — Is this change ripe to communicate now?

**Owner:** SignalScribe
**Decision verbs:** `RIPE` | `HOLD_UNTIL(date)` | `HOLD_INDEFINITE`

### What this decision means

A change that's worth communicating is not automatically worth communicating *today*. A feature flagged to 1% of internal users is not the same as one ramping to GA next week. Communicating too early creates noise about a state that may never ship. Communicating too late creates surprise. The decision is: *"is the timing right to put this in front of BU leaders now?"*

### Signals that favor `RIPE`

- **Imminent user-visible rollout** — GA is within ~30 days, or a phased rollout begins within ~14 days.
- **A decision window is open** — BU heads may need to prepare teams, update documentation, or weigh in on rollout sequencing.
- **The change has shipped and was not previously communicated** — post-hoc awareness is still useful.
- **A dependency, documentation, or training artifact is now available.**
- **A previous `HOLD_UNTIL` date has arrived** and no signals have changed.

### Signals that favor `HOLD_UNTIL(date)`

- **Early-stage flag rollout** (<10% internal) with no imminent ramp.
- **Feature still being tuned** — behavior may change before GA.
- **Rollout window scheduled but far out** (>60 days) — hold until ~30 days before rollout unless P0.
- **Dependency not ready** — related documentation, training, or support material is still being authored.
- **Change blocked on approvals** — regulatory, legal, or leadership approval pending.

**When choosing `HOLD_UNTIL`, supply:** (a) the date to re-evaluate, and (b) the signal that would trigger re-evaluation.

### Signals that favor `HOLD_INDEFINITE`

- **Change is speculative** — marked as "exploring" or "prototype" with no committed path.
- **Change has been explicitly deferred** or deprioritized.
- **Change is contingent on external events** with no known timeline.

`HOLD_INDEFINITE` items are not forgotten — they go into a backlog reviewed periodically via `/pending`.

### Failure modes to avoid

- **Communicating experiments as if they were plans.** Hold until they graduate.
- **Holding indefinitely as a way to avoid a hard `ARCHIVE` decision.** If a change genuinely isn't worth communicating, archive it.
- **Missing the communication window.** When in doubt, `RIPE` with a note about early rollout is better than `HOLD_UNTIL` that crosses the rollout start.

---

## Gate 3 — Is my understanding clear enough to hand off?

**Owner:** SignalScribe
**Decision verbs:** `READY` | `NEED_CLARIFICATION(questions)` | `UNRESOLVABLE`

### What this decision means

Even if a change passes gates 1 and 2, the *interpretation* SignalScribe has produced may not be good enough to hand to BUAtlas. A muddled ChangeBrief produces muddled BU personalizations and poor notifications. The question is: *"Do I have enough to produce a useful message? Or should I go back, ask, or give up?"*

This gate is self-reflective. SignalScribe evaluates its own output.

### Signals that favor `READY`

- **Before/after behavior is concretely described.**
- **Impact areas are named, not gestured at** — "affects order submission for specialty pharmacy" beats "affects some workflows."
- **Timeline is specified** — even "Q3" is enough.
- **Confidence score ≥ 0.75** on the ChangeBrief as a whole.
- **Required actions, if any, are identifiable.**
- **Source citations support every non-trivial claim.**

### Signals that favor `NEED_CLARIFICATION`

- **Vague behavior description** — "improved," "optimized," "updated" without specifics.
- **Impact is inferred, not stated** — the artifact doesn't say what's affected; SignalScribe is guessing.
- **Timeline references are inconsistent** — the title says May 1, the body says "rolling out throughout Q3."
- **Key actors are missing** — no indication of who owns the change, who to ask, what team is affected.
- **Confidence score is 0.5–0.75.**

Supply specific, answerable questions — not "can you clarify?" but "does this change affect only US-region submissions, or all regions?"

### Signals that favor `UNRESOLVABLE`

- **Artifact is internally contradictory** and no external sources resolve it.
- **Artifact references documents that cannot be retrieved** and the referenced content is load-bearing.
- **Confidence < 0.5** after multiple interpretation attempts.
- **Change requires specialized domain knowledge** neither the artifact nor tools can surface.

### Failure modes to avoid

- **Proceeding with muddy interpretations.** When in doubt, `NEED_CLARIFICATION`.
- **Asking too many questions.** Aim for ≤3 sharp questions.
- **Using `NEED_CLARIFICATION` to avoid interpretive judgment.** Some ambiguity is normal; interpret confidently and mark uncertainty explicitly.

---

## Gate 4 — Is this BU actually affected?

**Owner:** BUAtlas (per-BU invocation)
**Decision verbs:** `AFFECTED` | `ADJACENT` | `NOT_AFFECTED`

### What this decision means

The BU registry pre-filter surfaces *candidate* BUs. But candidate does not mean affected. "My team uses the product that changed" is not the same as "my team's work will be different because of this change." BUAtlas's first responsibility for each candidate BU is to distinguish *real impact* from *topical proximity*.

This is the single most important quality gate in the system. False positives here produce "not relevant" feedback from BU heads and train them to ignore notifications.

### Signals that favor `AFFECTED`

- **The change touches a workflow the BU executes.**
- **The change alters an output the BU consumes** — a report format, a data feed, an API contract.
- **The change requires preparation the BU must do** — update training, SOPs, notify field teams, prepare FAQs.
- **The change creates a decision the BU must make** — opt in, opt out, configure, prioritize.
- **The change has a visible rollout inside the BU's user base.**
- **The BU owns or co-owns the affected product area.**

### Signals that favor `ADJACENT`

- **The BU uses the broader product but not the specific surface that changed.**
- **The change might theoretically interact with the BU's work but no concrete mechanism is identified.**
- **The BU has historical interest in the product area but no current active use.**
- **The BU would want to know "for awareness" but has no action to take.**

`ADJACENT` is legitimate — does not produce a push notification, may produce a digest line.

### Signals that favor `NOT_AFFECTED`

- **Registry match was on a stale relationship** — BU once owned this area but transferred it.
- **Keyword overlap is coincidental** — the change and the BU share a term but refer to different concepts.
- **Change is scoped to a user segment that excludes the BU.**

### Failure modes to avoid

- **Defaulting to `AFFECTED` to be safe.** The frame is *"would this BU head thank me for sending this, or curse me?"* When in doubt, choose `ADJACENT`.
- **Confusing topical match for functional impact.** Ask: *what will this BU's people do differently because of this change?* If the answer is "nothing concrete," it's `ADJACENT` or `NOT_AFFECTED`.
- **Inheriting the pre-filter's optimism.** Pre-filter is tuned for recall. It is BUAtlas's job to apply precision.

### Confidence calibration

- `AFFECTED` requires identifying at least one concrete mechanism of impact.
- Confidence < 0.6 on `AFFECTED` → downgrade to `ADJACENT` and note uncertainty.
- Confidence < 0.5 on any decision → `ESCALATE` to HITL.

---

## Gate 5 — Is the drafted message worth this BU head's attention?

**Owner:** BUAtlas (per-BU invocation, after gate 4 returns `AFFECTED`)
**Decision verbs:** `WORTH_SENDING` | `WEAK` | `NOT_WORTH`

### What this decision means

Even when a BU is genuinely affected, the message BUAtlas has drafted may not be worth sending. A notification that cannot clearly articulate *why this matters to you* and *what, if anything, you should do* is worse than no notification — it trains the recipient to tune out.

### Signals that favor `WORTH_SENDING`

- **The "why it matters" sentence names a specific BU-relevant consequence** — not "this may affect your team" but "your field reps will need updated talking points for the May forum."
- **The recommended action is concrete and owner-identified.**
- **The message length matches the message weight** — short for awareness, medium for actions required, long only when necessary.
- **The timing reference is specific enough to act on.**
- **A BU head reading this in 20 seconds could walk away knowing the one thing they need to do.**

### Signals that favor `WEAK`

- **"Why it matters" is generic** — could be sent to any BU unchanged.
- **Recommended action is vague** — "please review" without specifying what to review for.
- **The message restates the ChangeBrief without BU-specific framing.**
- **The message is defensively hedged** — "may," "could," "might potentially" to the point no one can tell the actual claim.

`WEAK` signals regeneration before sending, either by BUAtlas retry or HITL.

### Signals that favor `NOT_WORTH`

- **Affected technically but impact is trivially small.**
- **The BU's OKRs and current priorities make this a distraction.**
- **Adding this notification to recent volume would violate noise control.**

`NOT_WORTH` items may go into a digest, or be marked for delegate notification only.

### Failure modes to avoid

- **Marking everything `WORTH_SENDING` because gate 4 said `AFFECTED`.** Affected + weak draft ≠ worth sending.
- **Using `NOT_WORTH` to second-guess gate 4.** `NOT_WORTH` is about the *message*, not the *impact*. Weak draft of real impact → `WEAK`, not `NOT_WORTH`.
- **Hedging the self-critique.** This is where quality is actually decided.

### Confidence calibration

- `WORTH_SENDING` with confidence 0.6–0.75 → proceed but flag for HITL sampling.
- `WEAK` → orchestrator requests regeneration once; if still `WEAK`, HITL.

---

## Gate 6 — Is now the right time to send this?

**Owner:** PushPilot
**Decision verbs:** `SEND_NOW` | `HOLD_UNTIL(time)` | `DIGEST` | `ESCALATE`

### What this decision means

A correctly-interpreted, genuinely-relevant, well-drafted message can still be sent at the wrong moment. Quiet hours, weekends, crises, mid-submission windows, recent notification fatigue — all argue for holding, digesting, or escalating.

*Note on agent vs. code split:* The agent's job is to **decide** what should happen and **explain why**. The code's job is to **enforce invariants** policy forbids (never send during documented quiet-hours, never exceed per-BU weekly rate cap). If agent says `SEND_NOW` but policy forbids it, policy wins and result is `HOLD_UNTIL` with a policy reason.

### Signals that favor `SEND_NOW`

- **Priority is P0 or P1** and recipient is within working hours.
- **Rollout window is imminent** — delay would push delivery past the event.
- **No quiet-hours conflict, no rate-limit pressure, no dedupe hit.**
- **Message is time-sensitive** — "decision needed by Friday."

### Signals that favor `HOLD_UNTIL(time)`

- **Recipient is in quiet hours** — hold until end of quiet window.
- **After-hours Friday and the change is not urgent** — hold until Monday 9 AM recipient-local.
- **Recipient has on-calendar busy signal** (vacation, earnings, submission window) — hold until window ends.
- **Message is a weekly-cadence update** that should land predictably.

Supply time and reason.

### Signals that favor `DIGEST`

- **Priority is P2 (awareness-only)** — digest is the natural channel.
- **Recipient has opted into digest format.**
- **Notification volume for this recipient this week is already high.**
- **Multiple related changes are pending** — bundle them.

### Signals that favor `ESCALATE`

- **Dedupe conflict** with a recent send — human decides whether this supersedes.
- **Policy hook flagged content** after drafting — late-detected restricted term.
- **Rate limit would be breached** — human decides which to defer.
- **PushPilot itself is uncertain** — timing signals argue plausibly in opposite directions.

### Failure modes to avoid

- **Optimizing for "send fast" at the expense of recipient attention.** Faster is not better.
- **Defaulting to `SEND_NOW` because the message is "ready."** Content-ready and moment-ready are different.
- **Using `DIGEST` as a way to punt.** `HOLD_UNTIL` is for timing; `DIGEST` is for format-fit.
- **Overriding policy invariants via reasoning.** Policy-enforced rules cannot be reasoned around.

---

## Cross-cutting principles

### Principle 1 — Recipient attention is the scarce resource

Every gate has the option to stop the message. The default bias is toward *not sending* unless the signals to send are concrete and specific. A missed notification is a measurable cost (coverage). An unwanted notification is an unmeasurable cost (eroded trust). Optimize for the one we can measure, tightly.

### Principle 2 — Uncertainty is information, not failure

`ESCALATE`, `HOLD_UNTIL`, `NEED_CLARIFICATION`, `WEAK` are first-class outputs. An agent that always produces a decisive answer is a worse agent when underlying information is uncertain.

### Principle 3 — Decisions must be reasoned, not announced

Every decision includes a short reason naming specific signals. "The change is not ripe" is useless; "flag at 2% internal, no ramp scheduled, HOLD_UNTIL ramp announcement" is useful.

### Principle 4 — Gates do not second-guess upstream gates

BUAtlas does not re-decide whether a change is worth communicating. PushPilot does not re-decide whether a message is worth sending. Each gate owns its decision, trusts upstream decisions, and adds its own judgment. If an upstream decision was wrong, the fix is HITL, not downstream override.

### Principle 5 — Policy is the floor, not the ceiling

Code-enforced policies are invariants. Agents reason within them. Agents can be *more* conservative than policy (hold when policy would allow send), but never less. Conflict → policy wins, logged for review.

---

## What this document is *not*

- **Not a rulebook.** Signals above are heuristics, not complete specifications. Agents still need judgment.
- **Not final.** Draft v1. Must be reviewed with a real AbbVie change-management or internal-communications professional.
- **Not exhaustive.** Edge cases will surface during pilot. Update this document, regenerate prompts, re-eval.

---

## Revision history

| Version | Author | Summary |
|---|---|---|
| v1 | Oṁ | Initial draft covering all six gates with signals, failure modes, confidence calibration, cross-cutting principles. |
```
