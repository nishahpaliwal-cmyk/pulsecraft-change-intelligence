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
