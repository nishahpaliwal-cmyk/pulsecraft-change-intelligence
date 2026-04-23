# PulseCraft — Planning Index

> **Purpose.** Single place to check *what has been decided, what is in flight, what is next, and where each artifact lives.*
>

---

## Current phase

**Phase:** Active implementation — schemas and config complete, agent authoring next.

**Last completed:** Prompt 15.5.1 (HITLQueue fix — instrumented_run called HITLQueue() without audit_writer, silently crashing background pipeline; pass audit_writer, wrap _run_pipeline in try/except; 636 tests passing).

Planning phases P0–P2 are complete. The prompt-driven build sequence is complete through prompt 15.5. P3 build sequence + demo are done.

---

## Planning phases

| Phase | Deliverables | Status |
|---|---|---|
| **P0 — Problem framing** | Problem statement, sponsor alignment | ✅ Done |
| **P1 — Pattern decision** | ADR-001 (pattern), ADR-002 (topology) | ✅ Done |
| **P2 — Decision design** | Six-gate decision criteria, architecture | ✅ Done |
| **P3 — Agent prompt authoring** | CLAUDE.md, signalscribe.md, buatlas.md, pushpilot.md | ✅ Done (CLAUDE.md done in 03.5; signalscribe.md done in 05; buatlas.md done in 06; pushpilot.md done in 07) |
| **P4 — Schemas and contracts** | JSON schemas + Pydantic models for data contracts | ✅ Done (completed ahead of schedule in prompt 02) |
| **P5 — Config + fixtures** | BU registry, profiles, policy, synthetic change fixtures | ✅ Done (completed ahead of schedule in prompt 03) |
| **P6 — Skills** | Skill definitions and implementations | ⏳ Prompts 08–10 |
| **P7 — Commands** | Slash command prompts | ✅ Done (prompt 11) |
| **P8 — Hooks** | Hook definitions + policy enforcement | ✅ Done (prompt 12) |
| **P9 — Dryrun + Evals** | First end-to-end dryrun, eval harness | ✅ Done (prompts 13–14) |

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
| 29 | SignalScribe agent | `src/pulsecraft/agents/signalscribe.py` | 05 | Real LLM-backed agent; gates 1/2/3; Protocol-compliant; retry logic |
| 30 | SignalScribe system prompt | `.claude/agents/signalscribe.md` | 05 | 307-line canonical prompt derived from decision criteria |
| 31 | SignalScribe eval script | `scripts/eval_signalscribe.py` | 05 | Runs all 8 fixtures, reports decision chain match status |
| 32 | SignalScribe unit tests | `tests/unit/agents/test_signalscribe_unit.py` | 05 | Mocked-client tests; contract, retry, error handling |
| 33 | SignalScribe integration tests | `tests/integration/agents/test_signalscribe_integration.py` | 05 | Real-API tests; @pytest.mark.llm; skipped by default |
| 34 | BUAtlas agent | `src/pulsecraft/agents/buatlas.py` | 06 | Real LLM-backed agent; gates 4/5; Protocol-compliant; retry + validation retry |
| 35 | BUAtlas fan-out | `src/pulsecraft/agents/buatlas_fanout.py` | 06 | asyncio.gather + asyncio.to_thread; Semaphore; FanoutFailure isolation |
| 36 | BUAtlas system prompt | `.claude/agents/buatlas.md` | 06 | 408-line canonical prompt; default bias ADJACENT; gate-5 self-critique framing |
| 37 | BUAtlas eval script | `scripts/eval_buatlas.py` | 06 | Variance-aware N=3 per fixture; match/close/false_positive/mismatch classification |
| 38 | BUAtlas unit tests | `tests/unit/agents/test_buatlas_unit.py`, `test_buatlas_fanout_unit.py` | 06 | 33 unit tests: protocol, retry, isolation, fanout ordering/failures/concurrency |
| 39 | BUAtlas integration tests | `tests/integration/agents/test_buatlas_integration.py` | 06 | 10 real-API tests; @pytest.mark.llm; skipped by default |
| 40 | PushPilot agent | `src/pulsecraft/agents/pushpilot.py` | 07 | Real LLM-backed agent; gate 6; delivery timing; agent-vs-code policy split |
| 41 | PushPilot system prompt | `.claude/agents/pushpilot.md` | 07 | 236-line canonical prompt; decision table; agent-vs-code split reminder |
| 42 | Orchestrator policy layer | `src/pulsecraft/orchestrator/engine.py` | 07 | `_is_in_quiet_hours`, `_select_channel`, `_enforce_pushpilot_policy` methods |
| 43 | PushPilot eval script | `scripts/eval_pushpilot.py` | 07 | 5 scenarios × N=3 runs; risk/match/mismatch/error classification |
| 44 | PushPilot unit tests | `tests/unit/agents/test_pushpilot_unit.py` | 07 | 20 unit tests: protocol, init, invoke contract, retry/error handling |
| 45 | Policy enforcement tests | `tests/unit/orchestrator/test_policy_enforcement.py` | 07 | 12 tests: quiet-hours detection, SEND_NOW override, channel approval, DIGEST/ESCALATE pass-through |
| 46 | PushPilot integration tests | `tests/integration/agents/test_pushpilot_integration.py` | 07 | 6 real-API tests; @pytest.mark.llm; schema, verb consistency, P1/P2 tendency |
| 47 | Full pipeline tests | `tests/integration/orchestrator/test_full_pipeline.py` | 07 | 10 tests; all 3 real agents; terminal state ranges per fixture |
| 48 | Integration conftest | `tests/integration/conftest.py` | 07 | Shared .env loader for all integration/LLM tests |
| 49 | BU registry expansion | `config/bu_registry.yaml` + `config/bu_profiles.yaml` | 07.7 | bu_alpha owned_product_areas expanded to match SignalScribe's observed vocabulary |
| 50 | Ingest errors | `src/pulsecraft/skills/ingest/errors.py` | 08 | IngestNotFound, IngestUnauthorized, IngestMalformed |
| 51 | Redaction helper | `src/pulsecraft/skills/ingest/redaction.py` | 08 | Belt-and-suspenders regex scrub for PII/credentials at ingest time |
| 52 | Normalizer | `src/pulsecraft/skills/ingest/normalizer.py` | 08 | normalize_to_change_artifact: shared normalization + validation + redaction |
| 53 | Fetch adapters (×5) | `src/pulsecraft/skills/ingest/fetch_*.py` | 08 | fetch_release_note, fetch_work_item (Jira/ADO), fetch_doc, fetch_feature_flag, fetch_incident |
| 54 | Stub source fixtures | `fixtures/sources/` (8 files) | 08 | Dev-mode stubs for all 5 source types |
| 55 | CLI command group | `src/pulsecraft/cli/main.py` | 08 | Restructured to `pulsecraft run-change` + `pulsecraft ingest` command group |
| 56 | Ingest unit tests | `tests/unit/skills/ingest/` (6 files) | 08 | ~110 unit tests: redaction, normalizer, each adapter |
| 57 | Ingest integration tests | `tests/integration/skills/test_ingest_cli.py` | 08 | 8 subprocess-based CLI integration tests |
| 58 | Registry skill | `src/pulsecraft/skills/registry.py` | 09 | lookup_bu_candidates — exact owned_product_areas intersection |
| 59 | Policy skill | `src/pulsecraft/skills/policy.py` | 09 | check_confidence_threshold, check_restricted_terms, evaluate_hitl_triggers; RestrictedTermHit, HITLTrigger dataclasses |
| 60 | Dedupe skill | `src/pulsecraft/skills/dedupe.py` | 09 | compute_dedupe_key (SHA-256), has_recent_duplicate (AuditReader scan) |
| 61 | Audit skill | `src/pulsecraft/skills/audit_skill.py` | 09 | Thin wrapper re-exporting AuditWriter/AuditRecord for use in hooks/commands |
| 62 | Past engagement skill | `src/pulsecraft/skills/past_engagement.py` | 09 | lookup_past_engagement — reconstruct BU history from DELIVERY_ATTEMPT records |
| 63 | AuditReader Protocol | `src/pulsecraft/orchestrator/audit.py` | 09 | Protocol with read_chain + read_recent_events; AuditWriter satisfies it |
| 64 | Skills unit tests | `tests/unit/skills/test_registry.py`, `test_policy.py`, `test_dedupe.py`, `test_past_engagement.py` | 09 | 52 new unit tests across 4 test modules |
| 65 | Delivery payload schemas | `src/pulsecraft/schemas/delivery_payloads.py` | 10 | TeamsCardPayload, EmailPayload, PushPayload, DigestPayload, DeliveryResult, ScheduledDelivery |
| 66 | Jinja2 templates | `templates/` (5 files) | 10 | teams_card.j2, email.txt.j2, email.html.j2, push.j2, portal_digest.md.j2 |
| 67 | Delivery renderer skills (×4) | `src/pulsecraft/skills/delivery/render_*.py` | 10 | render_teams_card, render_email, render_push, render_portal_digest |
| 68 | Send adapter skills (×3) | `src/pulsecraft/skills/delivery/send_*.py` | 10 | send_teams, send_email, send_push — dev-mode file write + injectable transport |
| 69 | Schedule send skill | `src/pulsecraft/skills/delivery/schedule_send.py` | 10 | SEND_NOW/HOLD_UNTIL/DIGEST timing computation |
| 70 | Delivery skill common module | `src/pulsecraft/skills/delivery/common.py` | 10 | get_template_env, validate_length, RenderingError |
| 71 | AuditRecord dedupe_key field | `src/pulsecraft/schemas/audit_record.py`, `schemas/audit_record.schema.json` | 10 | New optional field; populated on DELIVERY_ATTEMPT events |
| 72 | has_recent_duplicate fix | `src/pulsecraft/skills/dedupe.py` | 10 | Now queries r.dedupe_key (was r.input_hash — bug fix) |
| 73 | Orchestrator _execute_delivery refactor | `src/pulsecraft/orchestrator/engine.py` | 10 | Full render→dedupe→send chain; returns (decision_str, is_dedupe_conflict) |
| 74 | New state transition | `src/pulsecraft/orchestrator/states.py` | 10 | (SCHEDULED, "dedupe_conflict") → AWAITING_HITL |
| 75 | Delivery skill tests | `tests/unit/skills/delivery/` (8 test files) | 10 | 53 tests: renderers, send adapters, scheduler |
| 76 | Delivery audit tests | `tests/unit/orchestrator/test_delivery_audit.py` | 10 | 4 end-to-end dedupe correctness tests |
| 77 | CLI commands package | `src/pulsecraft/cli/commands/` (13 modules) | 11 | run_change, ingest, dryrun, approve, reject, edit, answer, replay, pending, digest, audit, metrics, explain |
| 78 | explain_chain skill | `src/pulsecraft/skills/explain_chain.py` | 11 | Builds Explanation dataclass from audit chain; AgentDecisionEvent, HITLEvent, DeliveryEvent, StateTransitionEvent |
| 79 | CLI common utilities | `src/pulsecraft/cli/common.py` | 11 | resolve_change_id, print_json_output, load_audit_writer, load_hitl_queue, format_ts, truncate |
| 80 | CLI unit tests | `tests/unit/cli/` (3 modules) | 11 | test_resolve_change_id (7 tests), test_explain_chain (10 tests), test_metrics (4 tests) |
| 81 | CLI integration tests | `tests/integration/cli/` (3 modules) | 11 | test_commands_smoke (12 tests), test_explain_output (10 tests), test_pending_flow (7 tests) |
| 82 | explain_chain: detect_runs + RunBoundary + RunNotFound | `src/pulsecraft/skills/explain_chain.py` | 11.5 | Run-boundary detection; /explain defaults to latest run; --run/--all/--list-runs |
| 83 | usd_estimate on agent output schemas | `src/pulsecraft/schemas/change_brief.py`, `personalized_brief.py`, `push_pilot_output.py` | 11.5 | Internal cost field (exclude=True, not in JSON schema) |
| 84 | Cost wiring: agents → engine → audit | `agents/*.py`, `orchestrator/engine.py` | 11.5 | Agents set .usd_estimate; engine passes AuditMetrics(cost_usd=...) to audit |
| 85 | detect_runs unit tests | `tests/unit/skills/test_detect_runs.py` | 11.5 | 12 tests for run detection and run-scoped build_explanation |
| 86 | Hook modules | `src/pulsecraft/hooks/pre_ingest.py`, `post_agent.py`, `pre_deliver.py`, `audit_hook.py`, `base.py`, `config.py` | 12 | 4 guardrail hooks + HookContext/HookResult base + settings.json loader |
| 87 | Hook registrations | `.claude/settings.json` | 12 | 4 hooks registered: pre_ingest (closed), post_agent (closed), pre_deliver (closed), audit (open) |
| 88 | Hook engine wiring | `src/pulsecraft/orchestrator/engine.py` | 12 | 5 lifecycle call sites; _invoke_hook; _write_hook_fired; lazy module loading |
| 89 | Hook unit tests | `tests/unit/hooks/` (5 test files) | 12 | 43 new tests: pre_ingest, post_agent, pre_deliver, audit_hook, config loader |
| 90 | Hook integration tests | `tests/integration/hooks/test_hooks_in_pipeline.py` | 12 | 6 pipeline-level hook tests via monkeypatched registrations |
| 91 | post_agent routing-verb fix | `src/pulsecraft/hooks/post_agent.py` | 13 | Skip confidence checks when any decision is a routing verb (ESCALATE, NEED_CLARIFICATION, UNRESOLVABLE, ARCHIVE, HOLD_INDEFINITE) |
| 92 | post_agent routing-verb regression tests | `tests/unit/hooks/test_post_agent.py` | 13 | 5 new tests for routing-verb skip semantics; 1 test for COMMUNICATE+HOLD_INDEFINITE mix |
| 93 | Dryrun report | `design/dryrun/2026-04-23-dryrun-report.md` | 13 | 8-fixture dryrun with real agents; findings, hook summary, /explain outputs, open questions |
| 94 | Eval expectations | `src/pulsecraft/eval/expectations.py` | 14 | 15 ExpectedOutcome entries (8 SS, 4 BA, 3 PP); expected/acceptable/false_positive verb sets |
| 95 | Eval classifier | `src/pulsecraft/eval/classifier.py` | 14 | Asymmetric 5-tier classification: false_positive_risk > mismatch > unstable > acceptable_variance > stable |
| 96 | Eval runner | `src/pulsecraft/eval/runner.py` | 14 | Per-agent isolated runners; BA setup = SS once; PP setup = SS+BA once; candidate-set skip logic |
| 97 | Eval reporter | `src/pulsecraft/eval/reporter.py` | 14 | Per-agent report_{agent}.md + summary_{agent}.json |
| 98 | Eval aggregator | `src/pulsecraft/eval/aggregator.py` | 14 | Grand-total aggregate.md + aggregate.json; pass criteria (0 fp_risk + 0 mismatch) |
| 99 | Eval entry points | `scripts/eval/run_signalscribe.py`, `run_buatlas.py`, `run_pushpilot.py`, `run_all.py` | 14 | Per-agent CLI scripts; exit 0 = pass, exit 1 = attention required |
| 100 | Eval unit tests | `tests/unit/eval/test_classifier.py` | 14 | 13 tests covering all 5 classification tiers + edge cases |
| 101 | Eval pytest integration | `tests/eval/test_agent_evals.py` | 14 | 15 parametrized tests; opt-in via PULSECRAFT_RUN_EVAL_TESTS=1; @pytest.mark.eval |
| 102 | Eval baseline report | `audit/eval/2026-04-23-baseline/` | 14 | 15 cases × 3 runs; stable=10/acceptable=1/unstable=1/skipped=3; PASS ($1.741, 26.9 min) |
| 103 | Enterprise identifier removal | *(25 files touched)* | 14.6 | All org-specific identifiers removed; replaced with neutral terminology; zero behavior changes |
| 104 | Demo sidebar fix | `src/pulsecraft/demo/static/app.js`, `tests/demo/test_server_routes.py` | 15.5 | Fixed JS SyntaxError (missing `)` in escHtml call) that prevented scenario cards from rendering; regression test added |
| 105 | HITLQueue fix | `src/pulsecraft/demo/instrumented_run.py`, `tests/demo/test_server_routes.py` | 15.5.1 | Pass audit_writer to HITLQueue; wrap _run_pipeline in try/except to surface errors via event bus |

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
| ~~O10~~ | ~~Fixture set for first dryrun~~ | ✅ Resolved — prompt 13, all 8 fixtures from prompt 03 used |

---

## Open questions (Track A dependencies)

| ID | Question | Who answers | Blocks |
|---|---|---|---|
| Q1 | "Marketplace" scope — which product surface? | Sponsor org | Pilot definition |
| Q2 | Which BU(s) partner for v1 pilot? | Sponsor | P8 fixtures, pilot |
| Q3 | LLM runtime — Bedrock or Azure AI Foundry or other? | EA / CloudOps | Deployment |
| Q4 | Validation posture — v1 is non-GxP? | Legal / Compliance | ADR-003 (pending) |
| Q5 | Existing internal GenAI reference architecture? | EA / AI Governance | Possible rework |
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
| 05 | `prompts/05-agent-signalscribe.md` | SignalScribe agent — gates 1, 2, 3; real LLM | ✅ Done |
| 06 | `prompts/06-agent-buatlas.md` | BUAtlas prompt | ✅ Done |
| 07 | `prompts/07-agent-pushpilot.md` | PushPilot prompt | ✅ Done |
| 07.7 | `prompts/07.7-demo-reliability-fix.md` | BU pre-filter vocabulary expansion — fixture 001 determinism | ✅ Done |
| 08 | `prompts/08-skills-ingest.md` | Ingest adapter skills | ✅ Done |
| 09 | `prompts/09-skills-registry-policy.md` | Registry, policy, audit skills — extracted from engine.py | ✅ Done |
| 10 | `prompts/10-skills-delivery.md` | Delivery rendering skills | ✅ Done |
| 11 | `prompts/11-commands.md` | Operator slash commands | ✅ Done |
| 12 | `prompts/12-hooks.md` | Guardrail hooks in settings.json | ✅ Done |
| 13 | `prompts/13-dryrun-walkthrough.md` | First end-to-end dryrun | ✅ Done |
| 14 | `prompts/14-eval-harness.md` | Fixture-based evals | ✅ Done |
| 14.5 | `prompts/14.5-readme-overhaul.md` | README overhaul — 625-line publication-quality README with Mermaid diagram | ✅ Done |
| 14.6 | `prompts/14.6-remove-abbvie.md` | Remove org-specific identifiers — repo reads as generic enterprise project | ✅ Done |
| 15 | `prompts/15-demo-ui.md` | Demo UI — FastAPI + SSE + vanilla JS SPA; 5 scenarios; 634 tests; `pulsecraft demo serve` | ✅ Done |

---

## Versioning approach

Prompts, schemas, configs, and decision criteria are versioned together. A change to any of them bumps a version and triggers re-eval. The audit log records which version of each was active for any given change event.
