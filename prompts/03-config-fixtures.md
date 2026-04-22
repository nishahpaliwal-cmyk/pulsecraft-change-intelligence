# Prompt 03 — Config Files + Synthetic Change Fixtures

> **How to use this prompt.**
> 1. Copy everything below the `---` line into Claude Code, running inside your `pulsecraft-change-intelligence` repo.
> 2. Claude Code will author config YAML files, synthetic change fixtures, a config loader module, and tests. Then commit.
> 3. At the end, Claude Code offers to also save **this prompt file itself** into `prompts/03-config-fixtures.md` as an archive commit.
>
> **Expected duration:** 90–120 minutes. Mostly content authoring + tests, no heavy reasoning.
>
> **Prerequisite:** Prompts 00, 01, 02 completed. Venv healthy, 37 schema tests passing.
>
> **What this prompt does NOT do:** author agents, orchestrator, skills, or commands. Those depend on these configs + fixtures, which is why this comes before them.

---

# Instructions for Claude Code

You are authoring the **configuration files** and **synthetic change fixtures** for PulseCraft. These are foundational: every agent prompt, skill, and eval will read from these files. Getting them right means downstream prompts can run end-to-end tests against realistic inputs without waiting for real AbbVie data.

Your job in **this session** is to produce:

1. **Four config YAML files** in `config/` — BU registry, BU profiles, policy, channel policy
2. **Eight synthetic `ChangeArtifact` fixtures** in `fixtures/changes/` — one per realistic decision-pattern scenario
3. **A config loader module** in `src/pulsecraft/config/` — typed API for orchestrator/skills to read config
4. **Tests** that every config file and fixture validates against its schema
5. **A short config README** explaining each file and its versioning contract
6. **One commit** with a clear message, plus optional archive commit at the end

## Environment discipline (applies to every prompt)

Always invoke Python tools via the venv binary, never the system one. Use `.venv/bin/python`, `.venv/bin/pytest`, `.venv/bin/ruff`, `.venv/bin/mypy` explicitly. If `uv` is available, `uv run <cmd>` is acceptable (it handles activation automatically). Never rely on `source .venv/bin/activate` persisting between tool calls — the shell state may reset. If a required tool is missing, install via `uv pip install <pkg>` (preferred) or `.venv/bin/python -m pip install <pkg>` (fallback). If neither works, stop and ask the user.

## Source of truth

Before authoring, read these files for context:

1. `design/planning/01-decision-criteria.md` — the six-gate decision criteria. **This drives fixture design.** Every decision verb should be exercisable by at least one fixture.
2. `design/00-problem-statement.md` — scale envelope, scope, constraints
3. `schemas/bu_profile.schema.json` — BU profile shape
4. `schemas/change_artifact.schema.json` — change artifact shape
5. `src/pulsecraft/schemas/` — Pydantic counterparts (use these for validation in tests)

If something in this prompt conflicts with the decision criteria document, the decision criteria wins.

## Design principles

1. **Synthetic, not real.** No AbbVie internal system names, no real people, no real product names, no real therapeutic-area-specific terminology except where generic (e.g., "immunology" as a BU label is fine — it's industry-standard — but no real AbbVie product brand names).
2. **Placeholder BU IDs.** Use `bu_alpha`, `bu_beta`, `bu_gamma`, etc. These are stand-ins until real AbbVie BU taxonomy is loaded via Track A discovery. Keep BU IDs lowercase snake_case for consistency.
3. **Realistic shapes, synthetic content.** The fixtures must feel like actual release notes / work items / feature flag events — not toy examples. Multi-paragraph, ambiguity where ambiguity is typical, implicit references, uneven quality. If they're all pristine, they won't surface real agent failure modes.
4. **Fixture diversity is the whole point.** Every decision verb (`COMMUNICATE`, `ARCHIVE`, `ESCALATE`, `RIPE`, `HOLD_UNTIL`, `HOLD_INDEFINITE`, `READY`, `NEED_CLARIFICATION`, `UNRESOLVABLE`, `AFFECTED`, `ADJACENT`, `NOT_AFFECTED`, `WORTH_SENDING`, `WEAK`, `NOT_WORTH`, `SEND_NOW`, `DIGEST`) should be the "correct answer" for at least one fixture scenario. The fixtures *don't* declare which verb they should trigger — that's what the agents decide. But the fixture set *as a whole* should provide coverage.
5. **Versioned YAML.** Every config file has a `schema_version` at the top (`"1.0"`). Every config file has a header comment explaining its purpose and ownership.
6. **Loader is strict.** Config loading validates against schemas and fails loudly on malformed data. No silent defaults, no best-effort fallbacks. Config bugs should surface at startup, not mid-run.

## Step-by-step work

### Step 1 — Review context

Read the five source files. Confirm you understand the BU profile shape and the change artifact shape. List in your head: which decision verbs should the fixture set exercise? (Target: all 17 verbs from the `Decision` enum across 8 fixtures.)

### Step 2 — Author `config/bu_registry.yaml`

The BU registry is the **deterministic pre-filter** between SignalScribe and BUAtlas. It maps product-area keywords/tags to BU IDs. Intentionally **recall-biased** — let BUAtlas (gate 4) filter false positives.

Structure:

```yaml
schema_version: "1.0"
# BU Registry — product-area → BU mapping for deterministic pre-filter.
# Recall-biased: prefer over-matching; BUAtlas (gate 4) applies precision.
# Owner: (TBD — Track A discovery item Q7)
# Last updated: <date>

bus:
  - bu_id: bu_alpha
    name: "Alpha BU"
    owned_product_areas:
      - specialty_pharmacy
      - hcp_portal_ordering
      - prior_authorization
    keywords:
      - specialty
      - pharmacy
      - prior auth
      - PA
    therapeutic_area: immunology
  - bu_id: bu_beta
    name: "Beta BU"
    owned_product_areas:
      - patient_support_services
      - co_pay_programs
      - patient_portal
    keywords:
      - patient support
      - co-pay
      - patient portal
    therapeutic_area: oncology
  # ... at least 6 BUs total
```

Create **at least 6 BUs** (`bu_alpha` through `bu_zeta`), spanning:
- A specialty pharmacy / distribution BU
- A patient support / access BU
- A field medical / medical affairs BU
- A clinical operations BU
- A commercial / field force BU
- A data / analytics / reporting BU

Each BU has 2–4 `owned_product_areas` (snake_case terms) and 3–6 `keywords` (natural-language phrases for fuzzy matching). Some product areas should overlap between BUs intentionally (e.g., `patient_portal` might be listed by both a support BU and a commercial BU) so we can test multi-BU impact fixtures.

### Step 3 — Author `config/bu_profiles.yaml`

One profile per BU from the registry. Matches the `BUProfile` schema from prompt 02.

Structure:

```yaml
schema_version: "1.0"
# BU Profiles — configuration for BUAtlas personalization.
# Contains display names only (no PII). Heads and delegates are placeholder
# synthetic names. Real names loaded via Track A onboarding (item Q2, Q7).

profiles:
  - bu_id: bu_alpha
    name: "Alpha BU"
    head:
      name: "<head-alpha>"
      role: "Head of Alpha BU"
      delegate_ids: ["<delegate-alpha-1>"]
    therapeutic_area: immunology
    owned_product_areas: [specialty_pharmacy, hcp_portal_ordering, prior_authorization]
    preferences:
      channels: [teams, email]
      quiet_hours:
        timezone: "America/Chicago"
        start: "18:00"
        end: "08:00"
      digest_opt_in: true
      max_notifications_per_week: 10
    active_initiatives:
      - "Q2 specialty pharmacy network expansion"
      - "PA turnaround time reduction"
    escalation_contact:
      name: "<escalation-alpha>"
      role: "Director of Operations, Alpha BU"
  # ... one profile per BU in the registry
```

Create one profile per BU from step 2. Vary the profiles meaningfully:
- Different timezones (America/Chicago, America/New_York, America/Los_Angeles, Europe/London, Asia/Tokyo — pick a plausible mix)
- Different quiet hours ranges
- Different `max_notifications_per_week` (5, 8, 10, 15 — so rate-limit scenarios can be tested)
- Different channel preferences (some email-only, some Teams+email, one with portal_digest)
- Some with `digest_opt_in: true`, some `false`
- 2–4 `active_initiatives` per BU — these are what BUAtlas uses for "BU currently cares about X" reasoning. Keep them synthetic and generic.

Use `<head-alpha>`, `<head-beta>` etc. as placeholder names. Do NOT invent realistic-sounding fake names — the explicit placeholder pattern makes it obvious that real names need to be filled in during onboarding.

### Step 4 — Author `config/policy.yaml`

Confidence thresholds, restricted terms, HITL triggers, rate limits.

```yaml
schema_version: "1.0"
# Policy Config — thresholds, restricted terms, rate limits, HITL triggers.
# Enforced in code (hooks). Agents cannot reason around these values.
# Owner: Head of AI (sponsor) + InfoSec (Track A item Q6)

confidence_thresholds:
  # Below these, route to HITL instead of proceeding
  signalscribe:
    gate_1_communicate: 0.75        # below → ESCALATE
    gate_1_archive: 0.6             # below → ESCALATE
    gate_2_ripe: 0.7
    gate_3_ready: 0.75
  buatlas:
    gate_4_affected: 0.6            # below → downgrade to ADJACENT
    gate_4_any: 0.5                 # below → ESCALATE
    gate_5_worth_sending: 0.6
  pushpilot:
    gate_6_any: 0.6

hitl_triggers:
  # Any match routes to HITL before delivery
  - any_agent_escalate
  - gate_3_need_clarification
  - gate_3_unresolvable
  - confidence_below_threshold
  - priority_p0
  - draft_contains_commitment_or_date
  - restricted_term_detected
  - mlr_sensitive_content_detected
  - second_weak_from_gate_5
  - dedupe_or_rate_limit_conflict_requiring_judgment

restricted_terms:
  # Categorized; hook matches case-insensitively
  commitments_and_dates:
    # Phrases that imply commitments; require HITL review
    - "we will deliver"
    - "guaranteed by"
    - "commitment to ship"
    - "promise that"
  scientific_communication:
    # Phrases that may constitute scientific communication; require MLR review
    - "efficacy"
    - "safety profile"
    - "clinical outcomes"
    - "indicated for"
    - "contraindicated"
    - "adverse event"
  sensitive_data_markers:
    # Indicators that redaction failed upstream; hard-block delivery
    - "patient name:"
    - "DOB:"
    - "MRN:"
    - "SSN:"
    - "API_KEY"
    - "password="

rate_limits:
  per_recipient:
    max_per_day: 5
    max_per_week: 15    # overridden by BU profile if BU profile sets lower
  per_bu:
    max_per_day: 20
  global:
    max_per_hour: 50

quiet_hours_default:
  # Used if BU profile doesn't specify
  timezone: "America/Chicago"
  start: "19:00"
  end: "07:00"

mlr_review_required_when:
  # Any match routes to MLR queue in addition to (not instead of) HITL
  - scientific_communication_term_present
  - change_type_indicates_label_or_indication
  - explicit_mlr_flag_in_source_artifact
```

### Step 5 — Author `config/channel_policy.yaml`

Approved channels per BU, priority-based channel selection rules.

```yaml
schema_version: "1.0"
# Channel Policy — approved channels, priority-based routing, dedupe.
# Enforced in code (pre-delivery hook).

approved_channels:
  global:
    # Channels approved for any BU unless overridden
    - teams
    - email
  restricted:
    # Channels only approved for specific BUs
    push: [bu_beta]           # only Beta BU uses push in v1
    portal_digest: []         # not approved in v1 for any BU
    servicenow: []            # not approved in v1

channel_selection_rules:
  # Applied in order; first match wins
  - when: { priority: P0 }
    channel: teams
    also_send_to: [email]        # dual-channel for P0
  - when: { priority: P1 }
    channel: teams
  - when: { priority: P2, recipient_digest_opt_in: true }
    channel: digest_bundle
  - when: { priority: P2, recipient_digest_opt_in: false }
    channel: email
  - when: { priority: any, recipient_preference: email_only }
    channel: email
  default:
    channel: email

dedupe:
  window_hours: 24
  key_components:
    - change_id
    - bu_id
    - recipient_id
    - message_variant_id

digest:
  cadence: daily
  send_time_recipient_local: "09:00"
  max_items_per_digest: 8
  priority_filter: [P2]    # digests are P2-only; P0/P1 are always immediate
```

### Step 6 — Author the config loader

`src/pulsecraft/config/__init__.py` — re-exports public API
`src/pulsecraft/config/loader.py` — the actual loader logic

API:

```python
from pulsecraft.config import (
    get_bu_registry,      # returns BURegistry (Pydantic)
    get_bu_profile,       # takes bu_id: str, returns BUProfile
    get_policy,           # returns Policy (Pydantic)
    get_channel_policy,   # returns ChannelPolicy (Pydantic)
    reload_config,        # forces reload (for tests / hot-reload)
)
```

Implementation requirements:

- Pydantic v2 models for each config type, living alongside the schemas work from prompt 02 (e.g., `src/pulsecraft/schemas/bu_registry.py`, `src/pulsecraft/schemas/policy.py`, `src/pulsecraft/schemas/channel_policy.py`). Add to `__init__.py` re-exports.
- Loader reads YAML, validates via Pydantic, caches in-memory.
- Config path is resolvable from env var `PULSECRAFT_CONFIG_DIR` (defaults to `./config`). Tests use a temp dir via fixture.
- On validation failure, raise a custom `ConfigValidationError` with a clear message pointing to the file + field.
- Do not use global singletons that persist across test runs — use a module-level cache with a `reload_config()` function for testability.
- Every loader function has a type annotation and a 1–2 line docstring.

### Step 7 — Author 8 synthetic change fixtures

Location: `fixtures/changes/`. Naming: `change_001_<short_slug>.json` through `change_008_<short_slug>.json`.

Each fixture is a valid `ChangeArtifact` per the JSON schema from prompt 02. Each has realistic `raw_text` (multi-paragraph where appropriate), plausible `title`, `source_type`, `source_ref` (use placeholder refs like `"RN-2026-042"` for release notes, `"JIRA-ALPHA-1234"` for Jira tickets, etc.), `author` (placeholder names), and `rollout_hints`.

**Each fixture is designed to provoke a specific decision pattern when run through the agents.** The fixture itself does not declare the expected verb — the eval harness in prompt 14 will encode expectations separately. But when you author each fixture, you're targeting a scenario. Below are the eight scenarios and what they should contain:

#### Fixture 1 — `change_001_clearcut_communicate.json`

**Scenario:** Clean release note for a feature with imminent rollout. Named product area matches one BU's owned area concretely. Should provoke `COMMUNICATE` (gate 1) → `RIPE` (gate 2) → `READY` (gate 3) → `AFFECTED` (gate 4 for one BU, `NOT_AFFECTED` for others) → `WORTH_SENDING` (gate 5) → `SEND_NOW` (gate 6, assuming not in quiet hours).

Content sketch: A clearly-written release note announcing a UI change to the prior authorization submission form, affecting the `hcp_portal_ordering` area owned by `bu_alpha`. Rolling out over the next two weeks starting in ~10 days. Support team has prepared FAQs. Timeline explicit.

#### Fixture 2 — `change_002_pure_internal_refactor.json`

**Scenario:** Internal refactor with no behavior change. Should provoke `ARCHIVE` at gate 1. Pipeline terminates there.

Content sketch: A Jira ticket describing a migration from one internal queue library to another. No user-visible change. No workflow change. Engineer-written, technical.

#### Fixture 3 — `change_003_ambiguous_escalate.json`

**Scenario:** Vague release note with unclear scope. "Various improvements to the portal." Should provoke `ESCALATE` at gate 1 or `NEED_CLARIFICATION` at gate 3.

Content sketch: A release note that mentions "various improvements" and "performance enhancements" without specifying what changed or who's affected. Title is generic. Body is marketing-speak.

#### Fixture 4 — `change_004_early_flag_hold_until.json`

**Scenario:** Feature flag announcement for a new capability at 2% internal rollout, no ramp scheduled. Should provoke `COMMUNICATE` at gate 1 (new capability warrants future communication) but `HOLD_UNTIL` at gate 2 (too early).

Content sketch: A feature-flag event notification showing a new capability enabled for 2% of internal users, with a note that ramp timing is "TBD pending metrics review." The capability is genuinely new and affects `bu_gamma`'s area, but it's premature to announce.

#### Fixture 5 — `change_005_muddled_need_clarification.json`

**Scenario:** Release note that passes gate 1 (clearly worth communicating) and gate 2 (timing ripe) but is muddled enough that gate 3 should return `NEED_CLARIFICATION`.

Content sketch: A release note that mentions a change affecting "order submissions" but doesn't specify whether it's all regions, all product classes, or a subset. Timeline says "Q3" without specifics. Actor isn't named. Impact is gestured at ("should improve things").

#### Fixture 6 — `change_006_multi_bu_affected_vs_adjacent.json`

**Scenario:** A substantive change that clearly affects one BU (gate 4 returns `AFFECTED`) and is topically proximate to another (gate 4 should return `ADJACENT`, not `AFFECTED`). Registry pre-filter surfaces both; BUAtlas applies precision.

Content sketch: A release note about changes to a reporting dashboard used by `bu_zeta` (data/analytics BU — clearly affected — they own the surface). The change also touches a report type used occasionally by `bu_delta` (clinical ops BU) for one corner case. Registry matches both BUs because "reporting" is in both their keywords. BUAtlas should distinguish.

#### Fixture 7 — `change_007_mlr_sensitive.json`

**Scenario:** A release note that mentions a change to outbound communication content referencing "safety profile" or "efficacy" language. Should trigger MLR-sensitive-content detection (restricted term in policy.yaml) and route to HITL with MLR review flag.

Content sketch: A release note about a new HCP-facing educational module. The description mentions updates to "safety profile" messaging and "efficacy" data presentation. Even though the change may be benign, the presence of those terms should trigger MLR review per policy.

#### Fixture 8 — `change_008_post_hoc_already_shipped.json`

**Scenario:** A post-hoc awareness case. Change already shipped without communication. Should provoke `COMMUNICATE` + `RIPE` (post-hoc awareness is still ripe) + `READY`, eventually hitting gate 6 where it might be `DIGEST` (since it's awareness-only, P2) rather than `SEND_NOW`.

Content sketch: A Jira ticket marked "DONE" describing a behavior change in notification wording that shipped two weeks ago. No announcement was made. Several support tickets have asked about it. Clearly affects `bu_epsilon`'s workflow.

### Step 8 — Author a fixtures README

`fixtures/changes/README.md`:

A short table:

```markdown
# Synthetic Change Fixtures

Used for dev and eval. No real data.

| Fixture | Scenario | Decision pattern target |
|---|---|---|
| 001 | Clear-cut communicate | COMMUNICATE → RIPE → READY → AFFECTED → WORTH_SENDING → SEND_NOW |
| 002 | Pure internal refactor | ARCHIVE (gate 1) |
| 003 | Ambiguous scope | ESCALATE or NEED_CLARIFICATION |
| 004 | Early flag, no ramp | COMMUNICATE → HOLD_UNTIL |
| 005 | Muddled release note | COMMUNICATE → RIPE → NEED_CLARIFICATION |
| 006 | Multi-BU (affected vs adjacent) | AFFECTED for one BU, ADJACENT for another |
| 007 | MLR-sensitive content | Triggers MLR review flag in HITL |
| 008 | Post-hoc already shipped | RIPE → DIGEST (P2 awareness) |

These scenarios cover the decision-verb space. The eval harness (prompt 14)
encodes expected outcomes as assertions; these fixtures are the inputs.
```

### Step 9 — Tests

In `tests/unit/config/` (new folder):

1. `test_config_loads.py` — each config file loads and validates via the loader without error.
2. `test_config_cross_references.py`:
   - Every BU in `bu_profiles.yaml` has a matching entry in `bu_registry.yaml` (by `bu_id`)
   - Every BU in `bu_registry.yaml` has a matching profile (or explicit TODO for not-yet-onboarded BUs)
   - Every therapeutic area referenced exists in a predefined list
3. `test_policy_sanity.py`:
   - All confidence thresholds are in [0, 1]
   - No restricted term is empty string
   - HITL trigger names match a known set
4. `test_channel_policy_sanity.py`:
   - Every channel referenced in rules is either in `approved_channels.global` or `approved_channels.restricted`
   - Rate-limit numbers are positive integers

In `tests/unit/fixtures/` (new folder):

5. `test_change_fixtures_valid.py` — every fixture file in `fixtures/changes/` parses as `ChangeArtifact` without error.
6. `test_change_fixtures_coverage.py` — assertions about the fixture set:
   - Exactly 8 fixtures (no more, no less — guards against accidental additions)
   - All `source_type` enum values covered across the fixture set (except those explicitly documented as out-of-scope for v1 fixtures)
   - Fixture filenames match the pattern `change_\d{3}_[a-z_]+\.json`

All tests run under `.venv/bin/pytest`.

### Step 10 — Verify

Run in order using venv binaries explicitly:

1. `.venv/bin/ruff check .`
2. `.venv/bin/ruff format --check .` (apply format if needed)
3. `.venv/bin/mypy src/pulsecraft/config/ src/pulsecraft/schemas/`
4. `.venv/bin/pytest tests/unit/config/ tests/unit/fixtures/ tests/unit/schemas/ -v` — all pass (prior schemas tests still pass, new ones pass)
5. `.venv/bin/python -c "from pulsecraft.config import get_bu_registry, get_bu_profile, get_policy, get_channel_policy; print(get_bu_registry().bus[0].bu_id)"` — prints `bu_alpha`

Fix failures before committing. Don't silently weaken a test to make it pass — if something's genuinely wrong, stop and ask.

### Step 11 — Commit

```
feat(config): add configs + synthetic change fixtures (prompt 03 output)

Config (config/):
- bu_registry.yaml — 6 synthetic BUs with product areas and keywords
- bu_profiles.yaml — matching profiles with timezones, quiet hours, preferences
- policy.yaml — confidence thresholds, restricted terms, HITL triggers, rate limits
- channel_policy.yaml — approved channels, priority routing, dedupe, digest cadence

Loader (src/pulsecraft/config/):
- Typed API: get_bu_registry, get_bu_profile, get_policy, get_channel_policy
- Strict Pydantic validation; raises ConfigValidationError on malformed data
- Env var PULSECRAFT_CONFIG_DIR for path override; test-friendly

Fixtures (fixtures/changes/):
- 8 synthetic change artifacts covering decision-verb scenarios:
  001 clearcut communicate, 002 internal refactor, 003 ambiguous escalate,
  004 early flag hold, 005 muddled clarification, 006 multi-BU affected/adjacent,
  007 MLR-sensitive, 008 post-hoc already shipped

Tests (tests/unit/config/, tests/unit/fixtures/):
- Config validation, cross-reference integrity, policy/channel sanity
- Fixture schema validation, coverage guards

All synthetic — no real AbbVie data. Real data loaded via Track A onboarding.

Next: prompt 04 — CLAUDE.md orchestrator spec.
```

Do not push to remote unless the user asks.

## Rules for this session

- **No real AbbVie system names.** If tempted to write something like "Veeva CRM integration," use `"<crm-system>"` or `"internal CRM"` instead.
- **No real drug/product names.** Not even close-sounding ones.
- **No real people.** Placeholder `<head-alpha>` style.
- **No free-form text in fixtures that happens to contain real PHI patterns.** The `raw_text` of each fixture should represent *what would appear after upstream redaction* — i.e., already-clean text.
- **Don't weaken schemas to make a fixture fit.** If a fixture can't be expressed in the current schema, the schema has a gap — flag it and ask before changing either.
- **Don't add fixtures beyond the 8 specified.** If a ninth scenario occurs to you, add it to the final report as a suggestion for a future prompt.

## Final report

1. **Files created** — full list with byte sizes or line counts.
2. **Verification results** — each step pass/fail.
3. **Fixture decision-verb coverage** — quick table showing which verbs each fixture targets. Helps the user confirm coverage.
4. **Any TODOs or schema gaps flagged** for follow-up.
5. **Commit hash** — `git log -1 --format="%h %s"`.
6. **Next prompt** — "Ready for prompt 04: CLAUDE.md orchestrator."

---

## [Post-commit] Save this prompt file to the repo

After the main commit lands, ask the user: **"Save this prompt file (prompt 03) to `prompts/03-config-fixtures.md` as a commit archive? (yes/no)"**

If yes:
- The user will provide the prompt file content or path.
- Write it verbatim to `prompts/03-config-fixtures.md`.
- Commit with: `chore(prompts): archive prompt 03 (config + fixtures) in repo`.

If no: skip.

This keeps prompts versioned alongside the code they generated.
