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
