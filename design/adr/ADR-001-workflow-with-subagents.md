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
