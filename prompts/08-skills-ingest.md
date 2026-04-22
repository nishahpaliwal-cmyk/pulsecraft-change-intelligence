# Prompt 08 — Ingest Skills (Fetch Adapters + Normalizer)

> **Character.** Pure engineering work. No LLM calls, no real credentials needed. Five source-type adapters + a normalizer that produces `ChangeArtifact`. This turns "we have hand-authored fixtures" into "we can point at a real source and receive an artifact."
>
> **Also fixes the CLI structure.** The current CLI is a single Typer command (`pulsecraft <fixture_path>`). Prompt 11 (operator commands) needs it to be a command group with subcommands. This prompt does the conversion: `pulsecraft run-change <fixture>` and `pulsecraft ingest <source>` both work.
>
> **How to use.** Paste below the `---` line into Claude Code. Claude Code builds adapters, normalizer, ingest command, tests, commits. Self-save at end.
>
> **Expected duration:** 2–3 hours.
>
> **Prerequisite:** Prompts 00–07.7 done. 270 tests passing. `origin/main` up to date.
>
> **Budget:** Zero API cost. All adapters use local fixtures or mocked HTTP; no real LLM or external service calls.

---

# Instructions for Claude Code

You are authoring the **ingest layer** for PulseCraft — the code that fetches change artifacts from source systems and normalizes them into the `ChangeArtifact` schema that SignalScribe consumes. This prompt builds five adapters, one normalizer, and restructures the CLI to accept subcommands.

No LLM calls. No real external systems. No credentials required at runtime. Stub endpoints and mockable transports only.

## Environment discipline

`.venv/bin/python`, `.venv/bin/pytest`, `.venv/bin/ruff`, `.venv/bin/mypy`. `uv run <cmd>` acceptable.

## Context to read before starting

1. **`src/pulsecraft/schemas/change_artifact.py`** — the output contract every adapter must produce
2. **`schemas/change_artifact.schema.json`** — JSON schema for validation
3. **`fixtures/changes/`** — look at the shape of each existing fixture; new adapters must produce artifacts that match this shape
4. **`src/pulsecraft/cli/main.py`** — current CLI structure (single Typer command); needs restructuring
5. **`CLAUDE.md`** — standing orders; pay attention to the no-real-AbbVie-data rule (applies to adapters too — use stub URLs like `https://example.invalid/rn/<id>`, not real endpoints)
6. **`design/planning/01-decision-criteria.md`** — just skim; not critical for this prompt but worth re-acquainting

## What "done" looks like

When you finish:

1. **Five adapter modules** in `src/pulsecraft/skills/ingest/`:
   - `fetch_release_note.py`
   - `fetch_work_item.py` (Jira/ADO — handles both with a `source` discriminator)
   - `fetch_doc.py`
   - `fetch_feature_flag.py`
   - `fetch_incident.py`
2. **One normalizer module** (`src/pulsecraft/skills/ingest/normalizer.py`) that takes raw source-specific payloads and produces validated `ChangeArtifact` objects.
3. **Six stub "source server" fixtures** (JSON files) in `fixtures/sources/<source_type>/` that mimic what each source system would return. Adapters read from these by default in dev mode.
4. **CLI restructured to command group** — `pulsecraft run-change <fixture>` (existing behavior) and `pulsecraft ingest <source_type> <source_ref> [options]` (new) both work.
5. **Tests** in `tests/unit/skills/ingest/`:
   - One test file per adapter + one for the normalizer
   - Mock HTTP with `respx` (add as dev dep if not present) or `unittest.mock`
   - Fixture coverage: each adapter normalizes its sample payload into a schema-valid `ChangeArtifact`
6. **Integration smoke test** — `tests/integration/skills/test_ingest_cli.py` — invokes the `pulsecraft ingest` CLI against the stub fixtures and asserts the produced `ChangeArtifact` round-trips through the schema.
7. **CLAUDE.md** — "Skills authored so far" section now lists the five ingest skills. "Current phase" marks prompt 08 done. Last-updated footer updated.
8. **Planning index** updated.
9. **One feature commit** + optional archive commit.
10. All prior 270 unit tests still pass. New tests pass. No new LLM integration tests (ingest is non-LLM).

## Design principles

1. **No real external calls at runtime.** Each adapter accepts an optional `transport` parameter (a callable or `httpx.Client`). Default in dev mode: read from stub fixtures in `fixtures/sources/`. Future real integrations inject a real transport.
2. **Source-agnostic normalization.** The normalizer doesn't know about Jira vs. ADO vs. release notes. It takes a dict with well-defined input keys (`raw_text`, `title`, `source_type`, `source_ref`, etc.) and produces a `ChangeArtifact`. All source-specific shape-fixing happens inside the adapter, before calling the normalizer.
3. **Adapters are pure functions where possible.** `fetch(source_ref: str, transport=None) -> ChangeArtifact`. No side effects beyond HTTP (or stub read). No global state.
4. **Errors are typed.** Three exception classes: `IngestNotFound` (404-equivalent), `IngestUnauthorized` (401/403 — flag for credentials later), `IngestMalformed` (response didn't match expected shape). Orchestrator will eventually handle these; for now just raise cleanly.
5. **Redaction at the boundary.** Every adapter passes its raw content through a redaction function before building the `raw_text`. V1 redactor is simple — regex-based scrub of patterns like `DOB:`, `MRN:`, `SSN:`, `API_KEY`, `password=`. Same list as `policy.yaml` → `restricted_terms.sensitive_data_markers`. Reuse if possible.
6. **No AbbVie-specific identifiers.** All stub fixtures use generic IDs (`RN-2026-042`, `JIRA-ALPHA-1234`, `DOC-42`, `FLAG-99`, `INC-2026-001`). Stub URLs use `https://example.invalid/`.
7. **CLI conversion is surgical.** Don't rewrite the CLI. Restructure the existing command to be `run-change`, add `ingest` as a sibling, keep all existing `--real-signalscribe` etc. flags working on `run-change`. Tests that shell out to the CLI must be updated.

## Step-by-step work

### Step 1 — Pre-flight and context

1. `git status` clean. `git log -1` shows the latest 07.7 commit.
2. `.venv/bin/pytest tests/ -q -m "not llm"` shows 270 passing.
3. Read the 6 context files.
4. Check whether `respx` is in pyproject.toml dev deps. If not, add it: `uv pip install respx` (and declare in `pyproject.toml` under `[project.optional-dependencies].dev`).

### Step 2 — Schemas used

Use the existing `ChangeArtifact` schema. If you find fields that don't fit your stub payloads cleanly, **don't modify the schema** — adjust the adapter's normalization logic. If a genuine gap exists, flag it in the final report rather than editing the schema.

### Step 3 — Author the redaction helper

`src/pulsecraft/skills/ingest/redaction.py`:

```python
def redact(text: str) -> str:
    """Remove sensitive data markers from raw text before it enters the pipeline."""
    ...
```

Patterns to scrub (case-insensitive):
- `SSN:\s*\d{3}-?\d{2}-?\d{4}`
- `DOB:\s*\d{1,2}/\d{1,2}/\d{2,4}`
- `MRN:\s*\d+`
- `password\s*=\s*\S+`
- `API[_-]?KEY\s*[:=]\s*\S+`
- Email addresses: `[\w.+-]+@[\w-]+\.[\w.-]+`
- Phone numbers (US-ish): `\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b`

Replacement: `[REDACTED]`. Not perfect redaction — this is belt-and-suspenders around upstream controls; proper redaction is a policy-hook concern handled in prompt 12. Note this in the module docstring.

Unit test: `tests/unit/skills/ingest/test_redaction.py` — each pattern redacts, benign text passes through, output is always a string.

### Step 4 — Author the normalizer

`src/pulsecraft/skills/ingest/normalizer.py`:

```python
def normalize_to_change_artifact(
    *,
    source_type: Literal["release_note", "jira_work_item", "ado_work_item", "doc", "feature_flag", "incident"],
    source_ref: str,
    title: str,
    raw_text: str,
    author: dict | None = None,
    related_refs: list[dict] | None = None,
    links: list[str] | None = None,
    labels: list[str] | None = None,
    rollout_hints: dict | None = None,
    ingested_at: datetime | None = None,
    change_id: str | None = None,
) -> ChangeArtifact:
    """Produce a validated ChangeArtifact. Generates change_id (ULID or UUID) and ingested_at if not provided. Applies redaction to raw_text."""
    ...
```

- `change_id`: if not provided, generate as UUID4 (or keep consistent with existing fixture format — check fixtures/changes/ for the format)
- `ingested_at`: if not provided, use `datetime.now(timezone.utc)`
- `raw_text`: always redacted via `redact()` before returning
- Returns a Pydantic-validated `ChangeArtifact`
- Raises `IngestMalformed` if required fields are invalid/missing

Unit test: `tests/unit/skills/ingest/test_normalizer.py` — happy path, field defaults, redaction applied, invalid input raises `IngestMalformed`.

### Step 5 — Author the five adapters

Each adapter has the same shape:

```python
def fetch_release_note(
    source_ref: str,
    *,
    transport: Callable[[str], dict] | None = None,
) -> ChangeArtifact:
    """Fetch a release note by ref. In dev mode (no transport), reads from fixtures/sources/release_notes/<ref>.json."""
    ...
```

For each adapter:

1. Define a simple input payload schema (as a `TypedDict` or plain dict spec in docstring) — what the source system returns for this type.
2. Call the transport (or read the stub fixture in dev mode).
3. Validate the payload shape. On malformed → raise `IngestMalformed`.
4. Extract fields appropriate to the source type and pass to `normalize_to_change_artifact`.
5. Return the resulting `ChangeArtifact`.

Specifics:

#### `fetch_release_note.py`
- Stub payload shape: `{release_id, title, body, author_name, published_at, tags, rollout?}`
- `source_ref` format: `RN-YYYY-NNN` (e.g., `RN-2026-042`)
- Stub fixtures at `fixtures/sources/release_notes/RN-2026-042.json` (create at least 2 samples)

#### `fetch_work_item.py`
- Handles both Jira and ADO. Discriminator: `source_type` parameter to the fetch function
- Stub payload shape: `{key, fields: {summary, description, status, priority, assignee, labels, linked_items}}`
- `source_ref` format: `JIRA-PROJ-NNNN` or `ADO-NNNN`
- Stub fixtures at `fixtures/sources/work_items/<ref>.json` (create 2 samples — one Jira, one ADO)

#### `fetch_doc.py`
- Stub payload shape: `{doc_id, title, markdown_content, author, last_modified, folder_path}`
- `source_ref` format: `DOC-NNN`
- Stub fixtures at `fixtures/sources/docs/DOC-42.json` (create 1 sample)

#### `fetch_feature_flag.py`
- Stub payload shape: `{flag_id, name, description, state: "experiment"|"ramping"|"ga"|"sunset", rollout_percentage, target_audiences, owner_team}`
- `source_ref` format: `FLAG-NNN`
- Stub fixtures at `fixtures/sources/feature_flags/FLAG-99.json` (create 2 samples — one early-stage, one ramping)

#### `fetch_incident.py`
- Stub payload shape: `{incident_id, title, summary, severity, status, affected_components, created_at, resolved_at?}`
- `source_ref` format: `INC-YYYY-NNN`
- Stub fixtures at `fixtures/sources/incidents/INC-2026-001.json` (create 1 sample)

Each adapter:
- Has a module docstring explaining source type + shape
- Has a unit test in `tests/unit/skills/ingest/test_fetch_<source>.py`
- Test uses mocked transport or reads from fixture directly
- Test verifies: happy path produces valid `ChangeArtifact`, missing fields raise `IngestMalformed`, unauthorized transport raises `IngestUnauthorized`, 404 raises `IngestNotFound`

### Step 6 — Package init and exports

`src/pulsecraft/skills/ingest/__init__.py` — re-export:

```python
from pulsecraft.skills.ingest.fetch_release_note import fetch_release_note
from pulsecraft.skills.ingest.fetch_work_item import fetch_work_item
from pulsecraft.skills.ingest.fetch_doc import fetch_doc
from pulsecraft.skills.ingest.fetch_feature_flag import fetch_feature_flag
from pulsecraft.skills.ingest.fetch_incident import fetch_incident
from pulsecraft.skills.ingest.normalizer import normalize_to_change_artifact
from pulsecraft.skills.ingest.redaction import redact
from pulsecraft.skills.ingest.errors import IngestNotFound, IngestUnauthorized, IngestMalformed
```

`src/pulsecraft/skills/ingest/errors.py` — the three exception classes.

### Step 7 — Restructure the CLI (surgical)

Current: `src/pulsecraft/cli/main.py` has a single Typer command.

Convert to a command group:

```python
app = typer.Typer(help="PulseCraft CLI")

@app.command("run-change")
def run_change(fixture_path: Path, ...): ...  # existing logic

@app.command("ingest")
def ingest(
    source_type: str = typer.Argument(..., help="One of: release_note, jira_work_item, ado_work_item, doc, feature_flag, incident"),
    source_ref: str = typer.Argument(...),
    run_after_ingest: bool = typer.Option(False, "--run", help="After ingesting, hand off to run-change pipeline"),
    ...
): ...
```

The `ingest` command:
1. Dispatches to the right adapter based on `source_type`
2. Prints a summary of the produced `ChangeArtifact` (id, title, source, size)
3. If `--run` flag is passed, writes the artifact to `fixtures/changes/generated/<change_id>.json` and invokes the same orchestration logic as `run-change`
4. Otherwise, writes to the generated folder and exits with the path printed

Tests that invoke the CLI (existing integration tests) must be updated to use `pulsecraft run-change <fixture>` instead of `pulsecraft <fixture>`. Use `grep -r "pulsecraft fixtures" tests/` to find them.

### Step 8 — Integration test

`tests/integration/skills/test_ingest_cli.py`:

- Runs `.venv/bin/pulsecraft ingest release_note RN-2026-042` against the stub fixture
- Asserts the produced artifact file exists in `fixtures/changes/generated/`
- Asserts the artifact validates against the schema
- One test per source type (5 tests)

### Step 9 — Verify

1. `.venv/bin/ruff check .` passes
2. `.venv/bin/ruff format --check .` passes
3. `.venv/bin/mypy src/pulsecraft/skills/ingest/ src/pulsecraft/cli/` passes
4. `.venv/bin/pytest tests/ -v -m "not llm"` — 270 prior + ~25-30 new tests pass
5. CLI smoke tests:
   - `.venv/bin/pulsecraft --help` shows `run-change` and `ingest` as subcommands
   - `.venv/bin/pulsecraft run-change fixtures/changes/change_001_clearcut_communicate.json` still works (existing behavior)
   - `.venv/bin/pulsecraft ingest release_note RN-2026-042` produces a generated artifact
   - `.venv/bin/pulsecraft ingest release_note RN-2026-042 --run` produces artifact and runs it through the pipeline with mock agents (no LLM needed for this smoke test)

If CLI smoke tests fail, stop and diagnose. CLI regressions break everything downstream.

### Step 10 — Update CLAUDE.md

In the **"Skills authored so far"** section, add:

```markdown
### Ingest skills (prompt 08)
Location: `src/pulsecraft/skills/ingest/`

| Skill | Purpose | Source-ref format |
|---|---|---|
| fetch_release_note | Fetch release notes | `RN-YYYY-NNN` |
| fetch_work_item | Fetch Jira or ADO work items | `JIRA-PROJ-NNNN` / `ADO-NNNN` |
| fetch_doc | Fetch documents | `DOC-NNN` |
| fetch_feature_flag | Fetch feature flag state | `FLAG-NNN` |
| fetch_incident | Fetch incidents | `INC-YYYY-NNN` |
| normalize_to_change_artifact | Normalize source-specific payload into ChangeArtifact | — |
| redact | Scrub sensitive data markers from raw_text | — |

All adapters read from `fixtures/sources/<type>/<ref>.json` in dev mode. Production transports injected via `transport` parameter. No real external systems. CLI: `pulsecraft ingest <source_type> <source_ref> [--run]`.
```

Update **"Current phase"**:
- Add `✅ 08 — Ingest skills (5 adapters + normalizer + CLI)`
- Mark next as ⏳ 09 — Registry, policy, audit skills

Update last-updated footer:
```
*Last updated: prompt 08 (ingest skills).*
*Next prompt: 09 — Registry, policy, audit skills.*
```

Also update the **CLI section** (if it exists; if not, add one) to document the new command-group structure.

### Step 11 — Update planning index

Add row to the prompt-driven build workflow table:
```
| 08 | prompts/08-skills-ingest.md | Ingest skills: 5 adapters + normalizer + CLI restructure | ✅ Done |
```

Add entry to Completed Artifacts referring to `src/pulsecraft/skills/ingest/` as the ingest layer.

### Step 12 — Commit

```
feat(skills): add ingest layer (5 adapters + normalizer + CLI restructure) — prompt 08

Ingest skills (src/pulsecraft/skills/ingest/):
- fetch_release_note, fetch_work_item (Jira/ADO), fetch_doc,
  fetch_feature_flag, fetch_incident — source-specific adapters
- normalize_to_change_artifact — shared normalization to ChangeArtifact
- redact — regex-based scrub of sensitive data markers
- errors — IngestNotFound, IngestUnauthorized, IngestMalformed

Each adapter accepts an optional transport callable; defaults to reading
from fixtures/sources/<type>/ in dev mode. No real external systems
touched. Production transports injected by orchestrator in prompt 09+.

CLI restructured from single command to command group:
- `pulsecraft run-change <fixture>` — existing behavior
- `pulsecraft ingest <source_type> <source_ref> [--run]` — new

Stub source fixtures in fixtures/sources/ (release_notes/, work_items/,
docs/, feature_flags/, incidents/).

Tests:
- tests/unit/skills/ingest/ — per-adapter + normalizer + redaction
- tests/integration/skills/test_ingest_cli.py — CLI smoke tests

All prior 270 unit tests still pass. ~25-30 new unit tests added.
No LLM calls in this prompt; zero API cost.

Next: prompt 09 — registry/policy/audit skills.
```

Do not push to remote unless the user asks.

## Rules for this session

- **No LLM calls. No real external services.** If tempted to call an API, stop — this is pure plumbing.
- **No real AbbVie identifiers.** All stubs use generic IDs and `example.invalid` hostnames.
- **No schema changes.** If a field seems missing from `ChangeArtifact`, adjust adapter logic, not the schema.
- **Surgical CLI changes.** Don't rewrite; convert to command group. Existing behavior of `run-change` preserved exactly.
- **Update all tests that shell out to `pulsecraft <fixture>`.** They need the new `run-change` subcommand.
- **Redaction is belt-and-suspenders.** V1 redactor is simple regex. Proper redaction is a prompt-12 concern. Note the limitation in module docstring.
- **Don't commit partial work.** If the CLI restructure surfaces unexpected issues, revert and ask before committing.

## Final report

1. **Files created/modified** — full tree with line counts.
2. **Verification results** — each step pass/fail.
3. **Pre-restructure vs. post-restructure CLI smoke test output** — show that `pulsecraft run-change` still works as before, and `pulsecraft ingest` works as new.
4. **Test count before/after.**
5. **Any schema gaps flagged** (if adapters couldn't cleanly fit — though this shouldn't happen).
6. **Commit hashes** — both commits.
7. **Next:** "Ready for prompt 09: registry, policy, audit skills."

---

## [Post-commit] Save this prompt file to the repo

After the main commit lands: **"Save prompt 08 to `prompts/08-skills-ingest.md`? (yes/no)"**

If yes: write verbatim, commit with `chore(prompts): archive prompt 08 (ingest skills) in repo`.

If no: skip.
