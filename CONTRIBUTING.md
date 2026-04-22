# Contributing to PulseCraft

PulseCraft is in its planning and early-build phase. It is an AbbVie-internal project; contributions are coordinated via the sponsor (Head of AI, AbbVie).

## How changes are made

PulseCraft follows a **prompt-driven build process**:

1. Author or update the relevant design document in `design/` (problem statement, ADR, agent contract, etc.).
2. Reflect the design change in the relevant prompt file under `prompts/`.
3. Run the updated prompt in a Claude Code session to generate or modify code.
4. Review the output, run verification steps, and commit.

This process ensures every implementation decision has a traceable design rationale, and that the entire codebase can be regenerated or audited from the prompt sequence.

## Getting help

Contact the AbbVie AI sponsor or team lead before opening any issue or making any change outside the planned prompt sequence.

## Code style

- Formatting and linting: `ruff` (configured in `pyproject.toml`).
- Type checking: `mypy`.
- Tests: `pytest` with `pytest-asyncio` for async code.
- Pre-commit hooks: run `pre-commit install` after setting up the environment.
