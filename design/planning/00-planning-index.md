# PulseCraft — Planning Index

> **Purpose.** Single place to check *what has been decided, what is in flight, what is next, and where each artifact lives.*
>
> **Owner:** Oṁ

---

## Current phase

**Phase:** Active implementation — schemas and config complete, agent authoring next.

**Last completed:** Prompt 04 (deterministic orchestrator — state machine, agent Protocols, mock agents, audit writer, HITL queue, engine, CLI command, 187 tests).

Planning phases P0–P2 are complete. The prompt-driven build sequence is at prompt 04 of 14. Schemas (02), config/fixtures (03), session-continuity (03.5), repo hygiene (03.6), and the full orchestrator (04) are done. Prompt 05 (SignalScribe agent) is next.

---

## Planning phases

| Phase | Deliverables | Status |
|---|---|---|
| **P0 — Problem framing** | Problem statement, sponsor alignment | ✅ Done |
| **P1 — Pattern decision** | ADR-001 (pattern), ADR-002 (topology) | ✅ Done |
| **P2 — Decision design** | Six-gate decision criteria, architecture | ✅ Done |
| **P3 — Agent prompt authoring** | CLAUDE.md, signalscribe.md, buatlas.md, pushpilot.md | 🚧 In progress (CLAUDE.md done in prompt 03.5; agents next in prompts 05–07) |
| **P4 — Schemas and contracts** | JSON schemas + Pydantic models for data contracts | ✅ Done (completed ahead of schedule in prompt 02) |
| **P5 — Config + fixtures** | BU registry, profiles, policy, synthetic change fixtures | ✅ Done (completed ahead of schedule in prompt 03) |
| **P6 — Skills** | Skill definitions and implementations | ⏳ Prompts 08–10 |
| **P7 — Commands** | Slash command prompts | ⏳ Prompt 11 |
| **P8 — Hooks** | Hook definitions + policy enforcement | ⏳ Prompt 12 |
| **P9 — Dryrun + Evals** | First end-to-end dryrun, eval harness | ⏳ Prompts 13–14 |

---

## Completed artifacts

| # | Artifact | Path | Prompt | Purpose |
|---|---|---|---|---|
| 1 | Problem Statement v1 | `design/00-problem-statement.md` | 01/03.5 | Problem framing, scope, assumptions, risks |
| 2 | ADR-001 — Workflow with subagents | `design/adr/ADR-001-workflow-with-subagents.md` | 01/03.5 | Pattern decision |
| 3 | ADR-002 — Subagent topology | `design/adr/ADR-002-subagent-topology.md` | 01/03.5 | Topology, fan-out, tool scoping, decision rubric |
| 4 | Decision Criteria v1 | `design/planning/01-decision-criteria.md` | 01/03.5 | Six-gate judgment — source of truth for agent prompts |
| 5 | Architecture | `design/architecture.svg` + `design/architecture.png` | 01 | The architecture diagram |
| 6 | design README | `design/README.md` | 01/03.5 | Architecture explainer |
| 7 | Planning Index (this doc) | `design/planning/00-planning-index.md` | 01/03.5 | Status tracker and artifact registry |
| 8 | JSON schemas | `schemas/` (7 files) | 02 | Data contracts: ChangeArtifact, ChangeBrief, BUProfile, Decision, PersonalizedBrief, DeliveryPlan, AuditRecord |
| 9 | Pydantic models | `src/pulsecraft/schemas/` (7 files) | 02 | Python counterparts to JSON schemas; 37 schema tests |
| 10 | BU registry | `config/bu_registry.yaml` | 03 | 6 synthetic BUs, product areas, keywords |
| 11 | BU profiles | `config/bu_profiles.yaml` | 03 | Preferences, quiet hours, initiatives per BU |
| 12 | Policy config | `config/policy.yaml` | 03 | Thresholds, restricted terms, HITL triggers, rate limits |
| 13 | Channel policy | `config/channel_policy.yaml` | 03 | Approved channels, routing rules, dedupe, digest cadence |
| 14 | Config loader | `src/pulsecraft/config/` | 03 | Typed loader API: get_bu_registry, get_bu_profile, get_policy, get_channel_policy |
| 15 | Synthetic change fixtures | `fixtures/changes/` (8 files) | 03 | Decision-verb coverage fixture set |
| 16 | CLAUDE.md | `CLAUDE.md` | 03.5 | Standing instructions for all future Claude Code sessions |
| 17 | Build plan | `prompts/build-plan.md` | 03.6 | Single-page build overview: phases, prompts, what each produces |
| 18 | Architecture diagram | `design/architecture.svg` + `design/architecture.png` | 03.6 | Now tracked in git; generated in prompt 01 |
| 19 | Prompt archives (00–02) | `prompts/00-repo-scaffold.md`, `prompts/01-commit-planning-docs.md`, `prompts/02-schemas.md` | 03.6 | Prompt source files now tracked (03 and 03.5 were already committed) |
| 20 | Orchestrator state machine | `src/pulsecraft/orchestrator/states.py` | 04 | WorkflowState StrEnum, TERMINAL_STATES, _TRANSITIONS, apply_transition |
| 21 | Agent Protocol interfaces | `src/pulsecraft/orchestrator/agent_protocol.py` | 04 | SignalScribeProtocol, BUAtlasProtocol, PushPilotProtocol |
| 22 | Mock agents | `src/pulsecraft/orchestrator/mock_agents.py` | 04 | MockSignalScribe, MockBUAtlas, MockPushPilot — scripted, no LLM |
| 23 | Audit writer | `src/pulsecraft/orchestrator/audit.py` | 04 | Append-only JSONL audit chain; read_chain; summary |
| 24 | HITL queue | `src/pulsecraft/orchestrator/hitl.py` | 04 | File-based queue; HITLReason StrEnum; approve/reject/edit/answer |
| 25 | Orchestrator engine | `src/pulsecraft/orchestrator/engine.py` | 04 | Orchestrator.run_change(), RunResult dataclass |
| 26 | CLI command | `src/pulsecraft/cli/main.py` | 04 | `pulsecraft <fixture>` — mock pipeline, Rich output |
| 27 | New schemas (prompt 04) | `src/pulsecraft/schemas/past_engagement.py`, `push_pilot_output.py` | 04 | PastEngagement (BUAtlas context), PushPilotOutput (gate-6 agent return) |
| 28 | Orchestrator tests | `tests/unit/orchestrator/`, `tests/integration/orchestrator/` | 04 | 187 total tests; 8 fixture paths, idempotency, audit chain reconstruction |

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

## Open decisions (resolved during remaining prompts)

| ID | Decision | Resolution target |
|---|---|---|
| ~~O1~~ | ~~Exact orchestrator code structure~~ | ✅ Resolved — prompt 04 |
| O2 | Exact prompt format per agent | Prompts 05–07 |
| O3 | Confidence thresholds (numeric) — draft in config/policy.yaml | Tuned in eval (prompt 14) |
| O4 | WEAK regeneration retry policy | Prompt 05 |
| O5 | HOLD_UNTIL re-evaluation mechanism | Prompt 08 |
| O6 | Digest cadence per channel | Done in channel_policy.yaml (prompt 03); may tune |
| O7 | Skill inventory — final list and per-skill prompts | Prompts 08–10 |
| O8 | Slash command contracts | Prompt 11 |
| O9 | Hook invocation points and exact rules | Prompt 12 |
| O10 | Fixture set for first dryrun | Prompt 13 (uses fixtures from prompt 03) |

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
| 01 | `prompts/01-commit-planning-docs.md` | Commit planning artifacts (docs created in 03.5) | ✅ Done |
| 02 | `prompts/02-schemas.md` | JSON schemas for data contracts | ✅ Done |
| 03 | `prompts/03-config-fixtures.md` | BU registry, profiles, policy, fixtures | ✅ Done |
| 03.5 | `prompts/03.5-session-continuity.md` | CLAUDE.md, design docs, planning index update | ✅ Done |
| 03.6 | *(inline)* | Repo hygiene — track untracked files, revert hello.py, sync CLAUDE.md + planning index | ✅ Done |
| 04 | `prompts/04-orchestrator.md` | Deterministic orchestrator + CLI + 187 tests | ✅ Done |
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
