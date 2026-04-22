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
