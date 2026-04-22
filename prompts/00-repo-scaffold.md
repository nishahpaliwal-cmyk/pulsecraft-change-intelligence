# Prompt 00 — Repo Scaffold & Python Project Setup

> **How to use this prompt.** Copy the content below the `---` line into Claude Code, running inside your cloned repo (`pulsecraft-change-intelligence`). Claude Code will create the folder structure, Python project files, Claude Code config, and make an initial commit.
>
> **Expected duration:** 30–60 minutes, mostly automated.
>
> **Prerequisite:** You have cloned `https://github.com/sunilpradhansharma/pulsecraft-change-intelligence` locally, and `claude` CLI (Claude Code) is installed and authenticated.
>
> **What this prompt does NOT do:** author agents, skills, commands, or orchestrator logic. Those come in later prompts. This prompt *only* scaffolds the empty structure so all subsequent prompts have a place to write into.

---

# Instructions for Claude Code

You are setting up the PulseCraft repository — an AbbVie-internal AI service that turns marketplace product/feature changes into personalized notifications for BU heads. PulseCraft is implemented as a team of three specialist AI agents (SignalScribe, BUAtlas, PushPilot) each acting as decision-makers at six judgment gates, orchestrated by a deterministic Python service built on the Claude Agent SDK.

Your job in **this session** is to scaffold the repository — nothing more. You are **not** authoring agents, skills, commands, or orchestrator logic. Those are separate sessions.

## What "done" looks like for this session

When you finish, the repo will have:

1. A complete directory structure matching the plan below — all folders created, placeholder README files in each major folder explaining its purpose.
2. A working Python project: `pyproject.toml`, a virtual environment, installed dependencies, passing basic sanity checks.
3. Claude Code configuration: `.claude/settings.json` (empty hooks for now), placeholder agent / skill / command folders.
4. A proper `.gitignore`, a root `README.md`, a `LICENSE` placeholder, and a `CONTRIBUTING.md`.
5. An initial commit with a clear message: `"chore: scaffold PulseCraft repo + Python project (P0 output)"`.
6. A verification step you run at the end to confirm the scaffolding works.

## Step-by-step work

### Step 1 — Confirm the working environment

- Confirm the current working directory is the cloned `pulsecraft-change-intelligence` repo.
- Confirm `git` is clean (or warn the user if there are uncommitted changes).
- Confirm Python 3.11+ is available. If not, stop and ask the user to install it.
- Prefer `uv` if available (faster, modern Python package manager). Fall back to `pip` + `venv` if `uv` is not available.

### Step 2 — Create the directory structure

Create this exact tree (create empty folders where no files are listed; files will be authored in later prompts):

```
pulsecraft-change-intelligence/
├── .claude/
│   ├── agents/               # Subagent prompts (authored in later prompts)
│   ├── skills/               # Skill definitions (authored in later prompts)
│   ├── commands/             # Slash commands (authored in later prompts)
│   └── settings.json         # Hooks and Claude Code config (stub in this prompt)
├── src/
│   └── pulsecraft/
│       ├── __init__.py
│       ├── orchestrator/     # Orchestrator service code (authored later)
│       │   └── __init__.py
│       ├── agents/           # Agent invocation wrappers (authored later)
│       │   └── __init__.py
│       ├── skills/           # Skill implementations in Python (authored later)
│       │   └── __init__.py
│       ├── schemas/          # Pydantic models for data contracts (authored in prompt 02)
│       │   └── __init__.py
│       ├── cli/              # CLI entry points for /ingest, /approve, etc. (authored later)
│       │   └── __init__.py
│       └── observability/    # Audit log, metrics (authored later)
│           └── __init__.py
├── tests/
│   ├── __init__.py
│   ├── unit/
│   │   └── __init__.py
│   ├── integration/
│   │   └── __init__.py
│   └── fixtures/             # Test fixtures (authored in prompt 03)
├── schemas/                  # JSON schema files (authored in prompt 02)
├── config/                   # bu_registry.yaml, bu_profiles.yaml, policy.yaml (authored in prompt 03)
├── templates/                # Message templates short/Teams/email (authored in prompt 03)
├── fixtures/                 # Synthetic change artifacts for dev (authored in prompt 03)
├── audit/                    # Runtime audit log output (gitignored, .gitkeep inside)
├── queue/                    # HITL pending, held, digest queues (gitignored, .gitkeep inside)
├── design/                   # Design docs — populated by prompt 01
├── prompts/                  # These prompt files — populated by user
├── docs/                     # GitHub Pages site — deferred, create empty for now
└── scripts/                  # Dev scripts (hello-world sanity check in this prompt)
```

In each major folder (`src/pulsecraft/`, `tests/`, `schemas/`, `config/`, `templates/`, `fixtures/`, `audit/`, `queue/`, `design/`, `docs/`, `scripts/`, and each `.claude/` subfolder), add a short `README.md` explaining the folder's purpose in 1–2 sentences. These are placeholders; later prompts will either replace or append to them.

### Step 3 — Author `pyproject.toml`

Create a `pyproject.toml` at the repo root using modern PEP 621 conventions. Use `hatchling` as the build backend for simplicity.

Required metadata:

- Project name: `pulsecraft`
- Version: `0.1.0`
- Description: "AbbVie-internal AI service: marketplace change → BU-ready notifications via a team of three specialist AI agents."
- Requires Python: `>=3.11`
- License: `Proprietary` (or leave a placeholder; the user will adjust)

Dependencies (add with sensible recent version constraints — you pick the pinning style, but be conservative; prefer `~=` for minor-version compatibility):

- `claude-agent-sdk` — Anthropic's Agent SDK for building the orchestrator
- `anthropic` — Anthropic SDK (for direct LLM calls in skills where needed)
- `pydantic>=2.6` — data validation for schemas
- `pyyaml` — for BU registry, BU profiles, policy config
- `typer` — for the CLI (`/ingest`, `/approve`, etc.)
- `rich` — nice terminal output for CLI
- `structlog` — structured logging for the audit trail
- `jsonschema` — JSON schema validation at hook boundaries
- `httpx` — for delivery adapters (Teams, email relay, etc.) — async-capable
- `python-dateutil` — for HOLD_UNTIL date math and timezone handling
- `tenacity` — retry logic for delivery

Dev dependencies (under `[project.optional-dependencies]` as `dev`):

- `pytest`
- `pytest-asyncio`
- `pytest-cov`
- `ruff` — linter + formatter, replaces black + flake8 + isort
- `mypy` — type checking
- `pre-commit` — git hook runner

Also define a `[project.scripts]` entry point: `pulsecraft = "pulsecraft.cli.main:app"` (the CLI module is stubbed in this prompt, authored later).

### Step 4 — Author `.gitignore`

Use a standard Python `.gitignore` as the base. Additions specific to PulseCraft:

- `audit/*` (except `.gitkeep`)
- `queue/*` (except `.gitkeep`)
- `.venv/`, `venv/`, `.python-version`
- `.env`, `.env.*` (never commit environment files)
- `*.db`, `*.sqlite`
- `.claude/local-settings.json` (if Claude Code ever creates local overrides)
- `.DS_Store`, `Thumbs.db`
- `node_modules/` (in case docs/ uses any tooling later)
- `.ruff_cache/`, `.mypy_cache/`, `.pytest_cache/`, `__pycache__/`

Add `.gitkeep` files inside `audit/` and `queue/` so the folders are tracked but their contents are not.

### Step 5 — Author `.claude/settings.json` stub

This file configures Claude Code's behavior for this repo. For now, create a minimal stub:

```json
{
  "$schema": "https://raw.githubusercontent.com/anthropics/claude-code/main/schemas/settings.schema.json",
  "hooks": {
    "PreToolUse": [],
    "PostToolUse": []
  },
  "description": "PulseCraft — hooks will be populated in prompt 12."
}
```

If the `$schema` URL above is incorrect or outdated, use a comment (`// …`) or omit the `$schema` key and add a TODO. Do not fabricate a schema URL.

### Step 6 — Author the root `README.md`

Create a root `README.md` that serves as the repo's front door. It should:

- Open with the tagline: *"PulseCraft — from release notes to BU-ready actions, via a team of AI agents."*
- Give a 3–4 sentence elevator pitch of what PulseCraft is.
- Show the status clearly: "Planning phase complete. Implementation in progress (phase P3)."
- Link to the design docs folder (`design/`) with a note that the detailed architecture, ADRs, and decision criteria live there.
- Include a "Quick start" section that lists:
  - Clone the repo.
  - Set up Python environment (`uv sync` or `pip install -e ".[dev]"`).
  - Run the sanity check: `python scripts/hello.py`.
  - Run tests: `pytest`.
- Include a "Repository structure" section with a brief tree.
- Link to the planning index at `design/planning/00-planning-index.md` for current status.

Do **not** embed the architecture diagram yet — that's committed in prompt 01. Link to it as `design/architecture.png` with a note "(populated in prompt 01)".

### Step 7 — Author `LICENSE` placeholder and `CONTRIBUTING.md`

- `LICENSE`: Create a file containing the text `TBD — proprietary AbbVie-internal. License to be confirmed with Legal in Track A discovery.`
- `CONTRIBUTING.md`: Create a short file explaining that PulseCraft is in planning/early-build phase, contributions are coordinated via the sponsor (Head of AI), and changes should follow the prompt-driven build process (author a design change in `design/`, update `prompts/` to reflect it, run the prompt in Claude Code).

### Step 8 — Author `scripts/hello.py`

A tiny sanity-check script that:

- Imports `pulsecraft` (verifying the package installs).
- Prints `"PulseCraft scaffolding OK — ready for prompt 01."` with some basic environment info (Python version, package version).

Make it runnable as `python scripts/hello.py`.

### Step 9 — Set up the Python virtual environment and install dependencies

- Create a virtual environment (`.venv/` using `uv venv` or `python -m venv .venv`).
- Activate it (note: within the Claude Code session, use the venv's Python directly rather than relying on shell activation).
- Install dependencies in editable mode: `uv pip install -e ".[dev]"` or `pip install -e ".[dev]"`.
- If any dependency fails to install, stop and report the error to the user clearly. Do not try to work around dependency issues silently.

### Step 10 — Verification

Run these commands in order and verify each passes before committing:

1. `python scripts/hello.py` → should print the success message.
2. `python -c "import pulsecraft; print(pulsecraft.__name__)"` → should print `pulsecraft`.
3. `ruff check .` → should pass (or report only trivial issues; fix them).
4. `python -c "from pydantic import BaseModel; print('pydantic ok')"` → confirms core dep works.
5. `pytest --collect-only` → should report 0 tests collected without errors.

If any verification step fails, stop and fix before proceeding to the commit.

### Step 11 — Commit

Stage all new files and commit with:

```
chore: scaffold PulseCraft repo + Python project (P0 output)

- Full directory structure for .claude/, src/, schemas/, config/, templates/, fixtures/, design/, docs/, prompts/
- pyproject.toml with runtime + dev dependencies (Agent SDK, pydantic, typer, pytest, ruff)
- .gitignore, LICENSE placeholder, CONTRIBUTING.md
- Root README with elevator pitch and quick-start
- scripts/hello.py sanity check (passing)
- .claude/settings.json stub (hooks to be populated in prompt 12)

Next: prompt 01 — commit planning documents (problem statement, ADRs, decision criteria, architecture).
```

Do **not** push to remote unless the user explicitly asks. Leave the commit on the local branch.

## Rules for this session

- **Do not author agent prompts, skill prompts, or command prompts.** Those are later sessions. If you feel tempted, resist — leave placeholder READMEs and move on.
- **Do not invent design decisions.** If something isn't specified here, leave a `TODO(prompt-XX)` comment and flag it in your final report.
- **Do not create branches.** Work on the current branch (`main` or whatever the user has checked out).
- **Do not make assumptions about AbbVie-internal systems.** Integrations (Jira, Veeva, Teams, etc.) are stubs only — no real URLs, no real credentials, no real tenant IDs.
- **If Claude Agent SDK is not installable** (e.g., package name changed, version conflict, auth required), stop and ask the user rather than guess. The SDK is a real package at `claude-agent-sdk` on PyPI, but verify before pinning a version.
- **Ask the user before any destructive action** (force-push, rm -rf, etc.). None should be needed in this prompt.

## Final report

At the end of the session, produce a short report covering:

1. **What was created** — summary tree of new files and folders.
2. **Verification results** — each verification command and its pass/fail status.
3. **Any TODOs or questions** — things you flagged for later attention.
4. **Next prompt** — "Ready for prompt 01: commit planning documents."

If anything went wrong that you couldn't resolve, state it clearly and do not commit partial work.
