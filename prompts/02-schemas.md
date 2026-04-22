# Prompt 02 — JSON Schemas + Pydantic Models for Data Contracts

> **How to use this prompt.**
> 1. Copy everything below the `---` line into Claude Code, running inside your `pulsecraft-change-intelligence` repo.
> 2. Claude Code will author six JSON schemas + matching Pydantic models, verify, and commit.
> 3. When done, Claude Code will offer to also save **this prompt file itself** into `prompts/02-schemas.md` — if you choose yes, one extra commit lands it in the repo as an archive.
>
> **Expected duration:** 60–90 minutes.
>
> **Prerequisite:** Prompts 00 and 01 completed. Repo has scaffold + design docs committed.
>
> **What this prompt does NOT do:** author agent prompts, skill code, commands, or business logic. Just the data contracts. Everything downstream depends on these contracts, which is why they come before agents.

---

# Instructions for Claude Code

You are authoring the **data contracts** that flow between the orchestrator, the three agents (SignalScribe, BUAtlas, PushPilot), the skills, and the audit system in PulseCraft. These contracts are load-bearing: if they're wrong or under-specified, every downstream prompt has to work around the flaws. If they're right, the agents, skills, and orchestrator almost write themselves.

Your job in **this session** is to produce:

1. **Six JSON Schema files** in `schemas/` — the canonical wire-format contract for each data type.
2. **Six matching Pydantic v2 models** in `src/pulsecraft/schemas/` — the Python counterpart used by orchestrator and skills.
3. **A schema-level test** that validates the Pydantic models and JSON schemas agree with each other.
4. **A short schemas README** documenting each contract, what produces it, what consumes it.
5. **One commit** with a clear message.

Do **not** author agent prompts, orchestrator code, or skill implementations. Those come later.

## Source of truth

Before authoring the schemas, read these files in the repo for context (in this order):

1. `design/00-problem-statement.md` — understand the flow end-to-end
2. `design/adr/ADR-002-subagent-topology.md` — component-to-primitive map, subagent I/O contracts
3. `design/planning/01-decision-criteria.md` — decision verbs for each gate (this determines the `decisions[]` structure on every contract)
4. `design/README.md` — architecture overview

The decision criteria document in particular is the source of truth for every decision verb that appears in the `decisions[]` array on `ChangeBrief`, `PersonalizedBrief`, `DeliveryPlan`. If there's any conflict between what this prompt says and what the decision criteria say, the decision criteria win.

## Design principles (apply to every schema)

1. **Every contract carries a `decisions[]` trail.** Agent decisions are first-class data, not side logs. Each decision entry includes: gate number, verb, reason (free-text), confidence, timestamp, agent version.
2. **Every contract has identifiers suitable for idempotency and audit replay.** `change_id`, `brief_id`, `bu_id`, `recipient_id`, `delivery_id`, with clear generation rules.
3. **Every contract is versioned.** Include a `schema_version` field on every top-level object (start at `"1.0"`).
4. **Optional fields are explicitly optional** (not implicitly by omission). Required fields are marked required.
5. **Timestamps are ISO-8601 UTC** (`2026-04-22T12:34:56Z`). Never epoch seconds. Never local-time.
6. **No free-form `metadata: {}` escape hatches.** If a field is needed, name it. If it's not clear what's needed, use a structured `extensions` sub-object with documented sub-keys and leave the exact keys as TODO.
7. **Decision verbs are enums**, not free strings. This is critical — typos in verbs would be silent bugs.
8. **Confidence is a float in [0, 1]**, with defined semantics (see decision criteria doc). Never percentages.
9. **No PII, PHI, or secrets** anywhere in any schema. The ingest layer redacts before data hits these contracts. Schemas should have field-level notes calling this out where tempting (e.g., `reason` strings on audit records).
10. **Forward-compatibility.** It's OK to leave fields with `additionalProperties: false` at the top level but allow structured extension points (see point 6).

## Step-by-step work

### Step 1 — Review and confirm context

Read the four files listed above. Confirm you can locate the decision verbs in the decision criteria doc. If any are unclear, stop and ask.

### Step 2 — Create six JSON Schema files

All schemas go in the `schemas/` folder at the repo root. Use JSON Schema draft 2020-12. Include `$schema`, `$id`, `title`, and `description` on each.

#### Schema 1 — `schemas/change_artifact.schema.json`

Represents a **normalized change artifact** — the output of the ingest adapters, input to SignalScribe. Same shape regardless of source (release note, Jira ticket, doc, feature flag, incident).

Required fields:
- `schema_version` (string, const `"1.0"`)
- `change_id` (string, ULID or UUID format recommended — pick one and document it)
- `source_type` (enum: `release_note`, `jira_work_item`, `ado_work_item`, `doc`, `feature_flag`, `incident`)
- `source_ref` (string — opaque identifier from the source system; do not include URLs with credentials)
- `ingested_at` (ISO-8601 UTC timestamp)
- `title` (string, max 500 chars)
- `raw_text` (string — redacted content, no PII/PHI/secrets — document the redaction contract in a `description`)
- `author` (optional object: `{ name: string, role?: string }` — name should be a display name, not email/ID)

Optional fields:
- `related_refs` (array of objects: `{ type: source_type, ref: string, relation: "parent"|"child"|"referenced-by"|"references" }`)
- `links` (array of strings — opaque internal URIs, no query-string secrets)
- `labels` (array of strings — e.g., `customer-impacting`, `gxp-adjacent`, `experiment`)
- `rollout_hints` (optional object: `{ start_date?: date, ramp?: string, target_population?: string }`)

Do not include a `decisions[]` on this contract — decisions don't exist until an agent has processed it.

#### Schema 2 — `schemas/change_brief.schema.json`

SignalScribe's output. Carries interpretation + decisions from gates 1, 2, 3.

Required fields:
- `schema_version` (string, const `"1.0"`)
- `brief_id` (string — ULID/UUID)
- `change_id` (string — matches the ChangeArtifact's change_id)
- `produced_at` (ISO-8601 UTC)
- `produced_by` (object: `{ agent: "signalscribe", version: string }`)
- `summary` (string, max 500 chars — 1–2 sentence plain-English summary)
- `before` (string — prior state, use `"unknown"` if genuinely unknown)
- `after` (string — new state)
- `change_type` (enum: `bugfix`, `behavior_change`, `new_feature`, `deprecation`, `rollback`, `configuration_change`)
- `impact_areas` (array of strings — taxonomy is freeform in v1; will align with BU registry later)
- `affected_segments` (array of strings — e.g., `internal_users`, `hcp_portal`, `specialty_pharmacy`)
- `timeline` (object: `{ status: enum["ripe", "held_until", "held_indefinite", "already_shipped"], start_date?: date, ramp?: string, reevaluate_at?: date, reevaluate_trigger?: string }`)
- `required_actions` (array of strings — empty array if none)
- `risks` (array of strings — empty array if none)
- `mitigations` (array of strings — empty array if none)
- `faq` (array of `{ q: string, a: string }` pairs — empty array if none)
- `sources` (array of citation objects: `{ type: source_type, ref: string, quote: string }` — `quote` is a short snippet <200 chars from the source supporting the claim)
- `confidence_score` (float 0..1)
- `decisions` (array of decision objects — see "Decision object structure" below)

Optional fields:
- `open_questions` (array of strings — populated when gate 3 returns `NEED_CLARIFICATION`)
- `escalation_reason` (string — populated when any gate returns `ESCALATE`)

#### Schema 3 — `schemas/personalized_brief.schema.json`

BUAtlas's output for one BU. Carries decisions from gates 4, 5.

Required fields:
- `schema_version` (string, const `"1.0"`)
- `personalized_brief_id` (string — ULID/UUID)
- `change_id` (string — traces back to ChangeArtifact)
- `brief_id` (string — traces back to ChangeBrief)
- `bu_id` (string — matches BU registry ID)
- `produced_at` (ISO-8601 UTC)
- `produced_by` (object: `{ agent: "buatlas", version: string, invocation_id: string }` — invocation_id disambiguates parallel per-BU invocations)
- `relevance` (enum: `affected`, `adjacent`, `not_affected`)
- `priority` (enum: `P0`, `P1`, `P2`, `null_if_not_affected`) — define the nullable case clearly
- `why_relevant` (string — concrete, BU-specific. Populated only when `relevance = affected`.)
- `recommended_actions` (array of objects: `{ owner: string, action: string, by_when?: string }` — empty array if none)
- `assumptions` (array of strings — explicit assumptions BUAtlas made; empty array if none)
- `message_variants` (object: `{ push_short?: string (max 240 chars), teams_medium?: string (max 6 lines / ~600 chars), email_long?: string (max 200 words) }` — required when `relevance = affected` AND `message_quality != not_worth`)
- `message_quality` (enum: `worth_sending`, `weak`, `not_worth`, `null_if_not_affected`)
- `confidence_score` (float 0..1)
- `decisions` (array of decision objects)

Optional:
- `regeneration_attempts` (integer — incremented when BUAtlas regenerates after a `WEAK` self-assessment)

#### Schema 4 — `schemas/delivery_plan.schema.json`

PushPilot's output + deterministic delivery planning. Carries decision from gate 6.

Required fields:
- `schema_version` (string, const `"1.0"`)
- `delivery_id` (string — ULID/UUID)
- `personalized_brief_id` (string — traces back)
- `change_id` (string)
- `bu_id` (string)
- `recipient_id` (string — identifies the BU head or delegate)
- `recipient_display` (object: `{ name: string, role: string }` — no email/phone; channel adapter resolves those separately)
- `produced_at` (ISO-8601 UTC)
- `produced_by` (object: `{ agent: "pushpilot", version: string }`)
- `decision` (enum: `send_now`, `hold_until`, `digest`, `escalate`)
- `channel` (enum: `teams`, `email`, `push`, `portal_digest`, `servicenow`, `null_if_escalated_or_held`)
- `scheduled_time` (ISO-8601 UTC or null)
- `reason` (string — required; explains the decision)
- `dedupe_key` (string — deterministic, see dedupe-key generation note below)
- `policy_check` (object: `{ passed: bool, violations?: array of enum["quiet_hours", "rate_limit", "unapproved_channel", "restricted_terms", "mlr_sensitive", "dedupe_conflict"], reasons?: array of strings }`)
- `retry_policy` (object: `{ max_attempts: integer, backoff: enum["exponential", "fixed", "none"], retry_on: array of enum["transient_error", "rate_limit", "timeout"] }`)
- `confidence_score` (float 0..1)
- `decisions` (array of decision objects)

Dedupe-key generation rule (document in the `description` of `dedupe_key`): hash of `(change_id, bu_id, recipient_id, message_variant_id)` where `message_variant_id` is a stable hash of the chosen message variant content. Keys are stable across replays.

#### Schema 5 — `schemas/bu_profile.schema.json`

BU configuration — read-only input to BUAtlas. Versioned YAML in config/ but validated against this JSON schema.

Required fields:
- `schema_version` (string, const `"1.0"`)
- `bu_id` (string — stable identifier, e.g., `immunology`, `oncology`)
- `name` (string — display name)
- `head` (object: `{ name: string, role: string, delegate_ids?: array of string }`)
- `therapeutic_area` (optional string — e.g., `immunology`, `neuroscience`. Placeholder until real AbbVie BU taxonomy is loaded.)
- `owned_product_areas` (array of strings — matches `impact_areas` vocabulary in ChangeBriefs)
- `preferences` (object: `{ channels: array of enum[...], quiet_hours: { timezone: string, start: "HH:MM", end: "HH:MM" }, digest_opt_in: bool, max_notifications_per_week?: integer }`)
- `active_initiatives` (array of strings — freeform; used by BUAtlas to assess "BU currently cares about X")
- `escalation_contact` (object: `{ name: string, role: string }`)

Optional:
- `okrs_current_quarter` (array of strings — summarized, sanitized)
- `historical_notification_feedback_summary` (object — aggregate stats only, no PII; exact shape TODO in a later prompt)

Document in the schema `description`: this file contains no PII by contract; all `name` values are display names only.

#### Schema 6 — `schemas/audit_record.schema.json`

Append-only audit log entry. Every LLM call, every tool call, every HITL action, every delivery attempt gets one.

Required fields:
- `schema_version` (string, const `"1.0"`)
- `audit_id` (string — ULID/UUID)
- `timestamp` (ISO-8601 UTC)
- `event_type` (enum: `agent_invocation`, `tool_call`, `hook_fired`, `hitl_action`, `delivery_attempt`, `state_transition`, `policy_check`, `error`)
- `change_id` (string — always populated; the unit of traceability)
- `correlation_ids` (optional object: `{ brief_id?: string, personalized_brief_id?: string, delivery_id?: string, invocation_id?: string }`)
- `actor` (object: `{ type: enum["agent", "orchestrator", "skill", "hook", "human"], id: string, version?: string }`)
- `action` (string — short verb: `"invoked"`, `"completed"`, `"redacted"`, `"approved"`, `"rejected"`, `"sent"`, etc.)
- `input_hash` (string — sha256 of the serialized input; never raw input with PII)
- `output_summary` (string — max 500 chars, structured summary; never dumps full LLM output)
- `decision` (optional object: `{ gate: integer, verb: string, reason: string }` — populated for agent invocations that emit a gate decision)
- `metrics` (optional object: `{ token_count_input?: integer, token_count_output?: integer, cost_usd?: float, latency_ms?: integer }`)
- `outcome` (enum: `success`, `failure`, `retry_scheduled`, `escalated`)
- `error` (optional object: `{ code: string, message: string }` — populated on failure)

No PII anywhere in an audit record. `output_summary` is a structured summary, not the raw LLM response.

### Step 3 — Decision object structure (shared across contracts)

Each of `ChangeBrief`, `PersonalizedBrief`, `DeliveryPlan` carries a `decisions[]` array. Define a shared sub-schema `schemas/decision.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://pulsecraft.abbvie.internal/schemas/decision.schema.json",
  "title": "Decision",
  "description": "A single gate decision made by an agent, carried in the contract's decisions[] array. Enables full decision-chain replay.",
  "type": "object",
  "required": ["gate", "verb", "reason", "confidence", "decided_at", "agent"],
  "additionalProperties": false,
  "properties": {
    "gate": { "type": "integer", "minimum": 1, "maximum": 6 },
    "verb": {
      "type": "string",
      "enum": [
        "COMMUNICATE", "ARCHIVE", "ESCALATE",
        "RIPE", "HOLD_UNTIL", "HOLD_INDEFINITE",
        "READY", "NEED_CLARIFICATION", "UNRESOLVABLE",
        "AFFECTED", "ADJACENT", "NOT_AFFECTED",
        "WORTH_SENDING", "WEAK", "NOT_WORTH",
        "SEND_NOW", "DIGEST"
      ]
    },
    "reason": { "type": "string", "maxLength": 1000 },
    "confidence": { "type": "number", "minimum": 0, "maximum": 1 },
    "decided_at": { "type": "string", "format": "date-time" },
    "agent": {
      "type": "object",
      "required": ["name", "version"],
      "properties": {
        "name": { "enum": ["signalscribe", "buatlas", "pushpilot"] },
        "version": { "type": "string" }
      }
    },
    "payload": {
      "type": "object",
      "description": "Verb-specific extra data (e.g., HOLD_UNTIL carries a date + trigger; NEED_CLARIFICATION carries a questions array).",
      "additionalProperties": true
    }
  }
}
```

Note: the enum combines all decision verbs from all gates. This is intentional — one shared enum makes validation simpler and keeps gates cross-referenceable.

Each of `ChangeBrief`, `PersonalizedBrief`, `DeliveryPlan` references this via `$ref` in their `decisions[]` array items.

### Step 4 — Author Pydantic v2 models in `src/pulsecraft/schemas/`

For each JSON schema, author a matching Pydantic v2 model:

- `src/pulsecraft/schemas/change_artifact.py` → `ChangeArtifact`
- `src/pulsecraft/schemas/change_brief.py` → `ChangeBrief`
- `src/pulsecraft/schemas/personalized_brief.py` → `PersonalizedBrief`
- `src/pulsecraft/schemas/delivery_plan.py` → `DeliveryPlan`
- `src/pulsecraft/schemas/bu_profile.py` → `BUProfile`
- `src/pulsecraft/schemas/audit_record.py` → `AuditRecord`
- `src/pulsecraft/schemas/decision.py` → `Decision`, `DecisionVerb` (StrEnum of all verbs)
- `src/pulsecraft/schemas/__init__.py` → re-exports all public symbols

Pydantic conventions:
- Use `BaseModel` with `model_config = ConfigDict(extra="forbid", frozen=False, str_strip_whitespace=True)`
- Use `Annotated[…, Field(...)]` for constrained fields (min/max length, ranges)
- Use `StrEnum` (Python 3.11+) for enum types
- Use `datetime` (UTC-aware) for timestamps, with a validator that rejects naive datetimes
- Use `str` for IDs — wrap in a `NewType` or `Annotated[str, Field(pattern=...)]` for ULID/UUID pattern validation
- Add brief docstrings to each model and non-obvious field
- Do not add any example values with placeholder PII (no `"name": "John Doe"` etc.). Use `"name": "<display-name>"` style placeholders if examples are needed.

Each Pydantic model must be able to round-trip through its JSON schema: serialize a model → validate against the JSON schema → parse back to a model → equal to original.

### Step 5 — Author `schemas/README.md`

A short doc explaining:
- What each schema is
- Which agent/component produces it
- Which agent/component consumes it
- Where the Pydantic counterpart lives
- How to regenerate validation tests when a schema changes
- The decisions[] invariant: every agent output schema has a decisions[] carrying the decision trail

Include a small table:

| Schema | Producer | Consumer | Pydantic model |
|---|---|---|---|
| ChangeArtifact | Ingest adapters | SignalScribe | `src/pulsecraft/schemas/change_artifact.py` |
| ChangeBrief | SignalScribe | Orchestrator → BUAtlas | `src/pulsecraft/schemas/change_brief.py` |
| PersonalizedBrief | BUAtlas (per BU) | Orchestrator → PushPilot / HITL | `src/pulsecraft/schemas/personalized_brief.py` |
| DeliveryPlan | PushPilot + code | Delivery adapters | `src/pulsecraft/schemas/delivery_plan.py` |
| BUProfile | BU registry config | BUAtlas (read-only) | `src/pulsecraft/schemas/bu_profile.py` |
| AuditRecord | Every hook + agent | Audit log | `src/pulsecraft/schemas/audit_record.py` |

### Step 6 — Tests

In `tests/unit/schemas/` (create folder):

1. `test_pydantic_roundtrip.py` — for each model, build a minimal valid instance, serialize to JSON, validate against the matching JSON schema (using `jsonschema` package), parse back, assert equality.
2. `test_schema_enums.py` — assert that `DecisionVerb` Python enum and the JSON schema enum on `decision.schema.json` list exactly the same verbs, no drift.
3. `test_schema_required_fields.py` — assert each schema's required-fields list is complete (i.e., removing any required field fails validation).
4. `test_decision_verb_per_gate.py` — assert that each gate (1-6) only emits verbs that match the decision criteria doc (hardcode the mapping in the test).

Fixture data for tests lives in `tests/fixtures/schemas/minimal_valid/`:
- `change_artifact.json`, `change_brief.json`, `personalized_brief.json`, `delivery_plan.json`, `bu_profile.json`, `audit_record.json`

These fixtures use only synthetic data. No AbbVie-internal system names, no real people, no real product names. Use placeholder values like `"bu_id": "bu_alpha"`, `"name": "<display-name>"`.

### Step 7 — Verify

Run these in order:

1. `ruff check .` → passes
2. `ruff format --check .` → passes (format if not)
3. `mypy src/pulsecraft/schemas/` → passes (fix any type issues)
4. `pytest tests/unit/schemas/ -v` → all tests pass
5. `python -c "from pulsecraft.schemas import ChangeArtifact, ChangeBrief, PersonalizedBrief, DeliveryPlan, BUProfile, AuditRecord, Decision, DecisionVerb; print('all imports ok')"` → prints success
6. Validate every JSON schema itself: `python -c "import json, jsonschema; [jsonschema.Draft202012Validator.check_schema(json.load(open(f))) for f in ['schemas/change_artifact.schema.json', 'schemas/change_brief.schema.json', 'schemas/personalized_brief.schema.json', 'schemas/delivery_plan.schema.json', 'schemas/bu_profile.schema.json', 'schemas/audit_record.schema.json', 'schemas/decision.schema.json']]; print('all schemas valid')"` → prints success

If any verification fails, fix before committing. If a schema design issue surfaces that requires judgment (not just a bug), stop and ask the user.

### Step 8 — Commit

```
feat(schemas): add data contracts + Pydantic models (prompt 02 output)

Six JSON Schemas (draft 2020-12) + matching Pydantic v2 models:
- ChangeArtifact — normalized ingest output (SignalScribe input)
- ChangeBrief — SignalScribe output (gates 1-3 decisions)
- PersonalizedBrief — BUAtlas per-BU output (gates 4-5 decisions)
- DeliveryPlan — PushPilot output + delivery planning (gate 6 decision)
- BUProfile — BU registry config (BUAtlas input)
- AuditRecord — append-only log entry

Plus:
- Decision sub-schema (shared decisions[] trail across agent contracts)
- Pydantic round-trip tests, enum-parity tests, required-field tests
- schemas/README.md explaining producer/consumer per contract
- Minimal-valid fixtures in tests/fixtures/schemas/

These contracts are invariant across agent prompt iterations. Agent prompts
(prompts 05-07) will consume these schemas as their I/O contracts.

Next: prompt 03 — config (BU registry, BU profiles, policy) + synthetic
change artifact fixtures for dev/eval.
```

Do not push to remote unless the user asks.

## Rules for this session

- **Do not invent decision verbs.** Use exactly what's in the decision criteria doc and what's listed in Step 3.
- **Do not add "AI-assistant" example values.** No `"assistant": "Claude"`, no real email addresses, no real names. Synthetic placeholders only.
- **Do not couple Pydantic models to the Anthropic SDK or any agent framework.** These are pure data contracts. The orchestrator and skills will adapt between them and the SDK as needed.
- **Do not add `metadata: {}` fields.** If a shape is unknown, use a named sub-object with a TODO comment.
- **If the decision criteria doc lists a verb I didn't include in the enum, flag it** in the final report rather than silently add or silently omit.

## Final report

1. Files created — full list with line counts.
2. Verification results — each step pass/fail.
3. Any TODOs or schema-design questions flagged for follow-up.
4. Commit hash.
5. "Ready for prompt 03: config + fixtures."

---

## [Post-commit] Save this prompt file to the repo

After the main commit lands, ask the user: **"Save this prompt file (prompt 02) to `prompts/02-schemas.md` as a commit archive? (yes/no)"**

If yes:
- The user will paste the full content of this prompt into the clipboard, or provide a local path to the downloaded prompt file.
- Write it to `prompts/02-schemas.md` verbatim.
- Commit with: `chore(prompts): archive prompt 02 (schemas) in repo`.

If no: skip and proceed.

This keeps prompts versioned alongside the code they generated.
