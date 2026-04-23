"""SignalScribe — real LLM-backed agent for gates 1, 2, 3.

Loads its system prompt from .claude/agents/signalscribe.md at init time.
Calls Claude via the Anthropic API, validates the response as a ChangeBrief,
and retries once with corrective feedback if validation fails.
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

import anthropic
import structlog
from anthropic.types import MessageParam, TextBlock
from pydantic import ValidationError
from tenacity import (
    retry,
    retry_if_exception_type,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from pulsecraft.schemas.change_artifact import ChangeArtifact
from pulsecraft.schemas.change_brief import ChangeBrief

logger = structlog.get_logger(__name__)

# Anthropic Sonnet 4.6 pricing (USD per million tokens, as of April 2026)
_INPUT_PRICE_PER_MTK = 3.00
_OUTPUT_PRICE_PER_MTK = 15.00

_DEFAULT_PROMPT_PATH = (
    Path(__file__).parent.parent.parent.parent / ".claude" / "agents" / "signalscribe.md"
)


class AgentInvocationError(Exception):
    """Raised after all API retry attempts are exhausted."""


class AgentOutputValidationError(Exception):
    """Raised when response fails ChangeBrief validation after max retries."""


def _estimate_cost(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens * _INPUT_PRICE_PER_MTK + output_tokens * _OUTPUT_PRICE_PER_MTK) / 1_000_000


def _build_user_message(artifact: ChangeArtifact) -> str:
    return (
        "Interpret the following change artifact and produce a ChangeBrief JSON object.\n\n"
        f"CHANGE ARTIFACT:\n{artifact.model_dump_json(indent=2)}\n\n"
        "REMINDER: Respond with ONLY a valid JSON object. No prose, no code fences. "
        f"The change_id in your output MUST be exactly: {artifact.change_id}\n"
        "Generate a new UUID v4 for brief_id."
    )


def _build_correction_message(validation_error: str) -> str:
    return (
        "Your previous response failed JSON schema validation. Fix it and return ONLY valid JSON.\n\n"
        f"VALIDATION ERROR:\n{validation_error}\n\n"
        "Return the corrected JSON object only. No prose. No code fences."
    )


class SignalScribe:
    """Real SignalScribe implementation using Claude Sonnet 4.6.

    Satisfies SignalScribeProtocol. Loads system prompt from disk.
    Uses retry logic for API errors and validation failures.
    """

    agent_name = "signalscribe"
    version = "1.0"

    def __init__(
        self,
        anthropic_client: anthropic.Anthropic | None = None,
        model: str = "claude-sonnet-4-6",
        max_validation_retries: int = 1,
        prompt_path: Path | None = None,
    ) -> None:
        self._model = model
        self._max_validation_retries = max_validation_retries
        self._client = anthropic_client or anthropic.Anthropic()

        path = prompt_path or _DEFAULT_PROMPT_PATH
        if not path.exists():
            raise FileNotFoundError(f"SignalScribe prompt not found: {path}")
        self._system_prompt = path.read_text(encoding="utf-8")

        logger.debug(
            "signalscribe_initialized",
            model=self._model,
            prompt_lines=self._system_prompt.count("\n"),
        )

    def invoke(self, artifact: ChangeArtifact) -> ChangeBrief:
        """Run gates 1 → 2 → 3. Returns a validated ChangeBrief.

        Raises AgentInvocationError on API failure after retries.
        Raises AgentOutputValidationError on persistent validation failure.
        """
        start = time.monotonic()
        log = logger.bind(change_id=artifact.change_id, agent=self.agent_name)
        log.info("signalscribe_invoke_start", title=artifact.title[:80])

        messages: list[MessageParam] = [{"role": "user", "content": _build_user_message(artifact)}]

        response_text, usage = self._call_api(messages)
        cost = _estimate_cost(usage.input_tokens, usage.output_tokens)

        # Attempt to parse and validate
        brief, error = self._parse_and_validate(response_text, artifact.change_id)
        if brief is None and self._max_validation_retries > 0:
            log.info(
                "signalscribe_validation_retry",
                error=error[:200] if error else "unknown",
            )
            messages.append({"role": "assistant", "content": response_text})
            messages.append({"role": "user", "content": _build_correction_message(error or "")})
            response_text2, usage2 = self._call_api(messages)
            cost += _estimate_cost(usage2.input_tokens, usage2.output_tokens)
            brief, error2 = self._parse_and_validate(response_text2, artifact.change_id)
            if brief is None:
                log.error(
                    "signalscribe_validation_failed", error=error2[:200] if error2 else "unknown"
                )
                raise AgentOutputValidationError(
                    f"ChangeBrief validation failed after {self._max_validation_retries + 1} attempts: {error2}"
                )

        elapsed = time.monotonic() - start
        log.info(
            "signalscribe_invoke_complete",
            elapsed_s=round(elapsed, 2),
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            usd_estimate=round(cost, 4),
            terminal_gate=brief.decisions[-1].gate if brief and brief.decisions else None,
            terminal_verb=brief.decisions[-1].verb if brief and brief.decisions else None,
        )

        assert brief is not None
        brief.usd_estimate = round(cost, 4)
        return brief

    @retry(
        # Only retry transient server errors, not permanent auth/permission failures
        retry=(
            retry_if_exception_type(anthropic.APIStatusError)
            & retry_if_not_exception_type(anthropic.AuthenticationError)
            & retry_if_not_exception_type(anthropic.PermissionDeniedError)
        ),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def _api_call_with_retry(self, messages: list[MessageParam]) -> anthropic.types.Message:
        return self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=self._system_prompt,
            messages=messages,
        )

    def _call_api(self, messages: list[MessageParam]) -> tuple[str, anthropic.types.Usage]:
        try:
            response = self._api_call_with_retry(messages)
            first_block = response.content[0] if response.content else None
            text = first_block.text if isinstance(first_block, TextBlock) else ""
            return text, response.usage
        except anthropic.AuthenticationError as exc:
            raise AgentInvocationError(f"Anthropic authentication failed: {exc}") from exc
        except anthropic.PermissionDeniedError as exc:
            raise AgentInvocationError(f"Anthropic permission denied: {exc}") from exc
        except anthropic.APIStatusError as exc:
            raise AgentInvocationError(f"Anthropic API error after retries: {exc}") from exc
        except anthropic.APIConnectionError as exc:
            raise AgentInvocationError(f"Anthropic connection error: {exc}") from exc

    def _parse_and_validate(
        self, text: str, expected_change_id: str
    ) -> tuple[ChangeBrief | None, str | None]:
        """Try to parse text as JSON and validate as ChangeBrief.

        Returns (brief, None) on success, (None, error_message) on failure.
        """
        # Strip accidental markdown fences if the model added them
        stripped = text.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            stripped = (
                "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
            )

        try:
            raw = json.loads(stripped)
        except json.JSONDecodeError as exc:
            return None, f"Response is not valid JSON: {exc}"

        # Ensure change_id matches (prevent hallucinated IDs)
        if isinstance(raw, dict) and raw.get("change_id") != expected_change_id:
            raw["change_id"] = expected_change_id

        # Ensure brief_id is present and valid
        if isinstance(raw, dict) and not raw.get("brief_id"):
            raw["brief_id"] = str(uuid.uuid4())

        # Truncate oversized string fields the model routinely exceeds
        if isinstance(raw, dict):
            for src in raw.get("sources") or []:
                if isinstance(src, dict) and isinstance(src.get("quote"), str):
                    src["quote"] = src["quote"][:200]
            for dec in raw.get("decisions") or []:
                if isinstance(dec, dict) and isinstance(dec.get("reason"), str):
                    dec["reason"] = dec["reason"][:1000]

        try:
            brief = ChangeBrief.model_validate(raw)
            return brief, None
        except ValidationError as exc:
            return None, str(exc)
