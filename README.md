# PulseCraft

> **PulseCraft — from release notes to BU-ready actions, via a team of AI agents.**

PulseCraft is an internal AI service that monitors marketplace product and feature changes, reasons about their business impact, and delivers personalized, actionable notifications to Business Unit heads — without requiring them to read vendor release notes. It is implemented as a team of three specialist AI agents (SignalScribe, BUAtlas, PushPilot) orchestrated by a deterministic Python service built on the Claude Agent SDK.

The service turns unstructured change artifacts (release notes, changelogs, announcements) into structured signals, maps each signal to the BUs most likely to care, drafts concise BU-tailored messages, and routes them through a human-in-the-loop approval gate before delivery.

**Status:** P3 build sequence complete. All three agents live — orchestrator (prompt 04), SignalScribe (prompt 05), BUAtlas (prompt 06), PushPilot (prompt 07). Ingest skills (prompt 08), registry/policy/audit skills (prompt 09), delivery rendering skills (prompt 10), operator slash commands (prompt 11/11.5), guardrail hooks (prompt 12). First end-to-end dryrun (prompt 13): all 8 fixtures with real agents, 2 bugs fixed. Eval harness (prompt 14): per-agent variance-aware eval, baseline PASS stable=10/acceptable=1/unstable=1 ($1.74), 619 tests.

> **For Claude Code sessions:** read [`CLAUDE.md`](CLAUDE.md) for standing instructions before taking any action in this repo.

---

## Repository structure

```
pulsecraft-change-intelligence/
├── .claude/          # Claude Code config: agents, skills, commands, hooks
├── src/pulsecraft/   # Python package — orchestrator, agents, CLI, schemas
├── tests/            # Unit, integration, and fixture tests
├── schemas/          # JSON schema files for data contracts
├── config/           # BU registry, BU profiles, policy YAML
├── templates/        # Message templates (short / Teams / email)
├── fixtures/         # Synthetic change artifacts for development
├── audit/            # Runtime audit log output (gitignored)
├── queue/            # HITL queues: pending, held, digest (gitignored)
├── design/           # Architecture docs, ADRs, decision criteria
├── prompts/          # Prompt files used to build this repo
├── docs/             # GitHub Pages site (deferred)
└── scripts/          # Dev utilities and sanity checks
```

For the detailed architecture, ADRs, and decision criteria, see [`design/`](design/).
Architecture diagram: `design/architecture.png` *(populated in prompt 01)*.

---

## Quick start

```bash
# 1. Clone the repo
git clone <repo-url> pulsecraft-change-intelligence
cd pulsecraft-change-intelligence

# 2. Set up Python environment (Python 3.11+ required)
uv venv && uv pip install -e ".[dev]"
# or without uv:
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 3. Run the sanity check
python scripts/hello.py

# 4. Run tests
pytest
```

---

## Design and planning

Full planning docs, problem statement, ADRs, agent contracts, and the build prompt index live in [`design/planning/00-planning-index.md`](design/planning/00-planning-index.md) *(populated in prompt 01)*.

---

## License

Proprietary — see [`LICENSE`](LICENSE).
