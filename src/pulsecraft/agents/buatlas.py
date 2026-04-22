"""BUAtlas — real LLM-backed per-BU personalization agent (gates 4, 5).

Loads its system prompt from .claude/agents/buatlas.md at init time.
Single-BU invocation: one change_brief + one bu_profile → one PersonalizedBrief.
Parallelism happens at the fan-out layer (buatlas_fanout.py), not here.
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

from pulsecraft.schemas.bu_profile import BUProfile
from pulsecraft.schemas.change_brief import ChangeBrief
from pulsecraft.schemas.past_engagement import PastEngagement
from pulsecraft.schemas.personalized_brief import PersonalizedBrief

logger = structlog.get_logger(__name__)

_INPUT_PRICE_PER_MTK = 3.00
_OUTPUT_PRICE_PER_MTK = 15.00

_DEFAULT_PROMPT_PATH = (
    Path(__file__).parent.parent.parent.parent / ".claude" / "agents" / "buatlas.md"
)


class AgentInvocationError(Exception):
    """Raised after all API retry attempts are exhausted."""


class AgentOutputValidationError(Exception):
    """Raised when response fails PersonalizedBrief validation after max retries."""


def _estimate_cost(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens * _INPUT_PRICE_PER_MTK + output_tokens * _OUTPUT_PRICE_PER_MTK) / 1_000_000


def _build_user_message(
    change_brief: ChangeBrief,
    bu_profile: BUProfile,
    past_engagement: PastEngagement | None,
) -> str:
    input_obj: dict = {
        "change_brief": json.loads(change_brief.model_dump_json()),
        "bu_profile": json.loads(bu_profile.model_dump_json()),
    }
    if past_engagement is not None:
        input_obj["past_engagement"] = json.loads(past_engagement.model_dump_json())

    return (
        "Evaluate the following input and produce a PersonalizedBrief JSON object.\n\n"
        f"INPUT:\n{json.dumps(input_obj, indent=2)}\n\n"
        "REMINDER: Respond with ONLY a valid JSON object. No prose, no code fences.\n"
        f"The change_id in your output MUST be exactly: {change_brief.change_id}\n"
        f"The brief_id in your output MUST be exactly: {change_brief.brief_id}\n"
        f"The bu_id in your output MUST be exactly: {bu_profile.bu_id}\n"
        "Generate a new UUID v4 for personalized_brief_id and produced_by.invocation_id."
    )


def _build_correction_message(validation_error: str) -> str:
    return (
        "Your previous response failed JSON schema validation. Fix it and return ONLY valid JSON.\n\n"
        f"VALIDATION ERROR:\n{validation_error}\n\n"
        "Return the corrected JSON object only. No prose. No code fences."
    )


class BUAtlas:
    """Real BUAtlas implementation using Claude Sonnet 4.6. Single-BU invocation.

    Satisfies BUAtlasProtocol. Loads system prompt from disk.
    Parallelism over multiple BUs is handled by buatlas_fanout.py.
    """

    agent_name = "buatlas"
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
            raise FileNotFoundError(f"BUAtlas prompt not found: {path}")
        self._system_prompt = path.read_text(encoding="utf-8")

        logger.debug(
            "buatlas_initialized",
            model=self._model,
            prompt_lines=self._system_prompt.count("\n"),
        )

    def invoke(
        self,
        change_brief: ChangeBrief,
        bu_profile: BUProfile,
        past_engagement: PastEngagement | None = None,
    ) -> PersonalizedBrief:
        """Run gate 4, then gate 5 if affected. Returns a validated PersonalizedBrief.

        Raises AgentInvocationError on API failure after retries.
        Raises AgentOutputValidationError on persistent validation failure.
        """
        start = time.monotonic()
        log = logger.bind(
            change_id=change_brief.change_id,
            bu_id=bu_profile.bu_id,
            agent=self.agent_name,
        )
        log.info("buatlas_invoke_start", brief_id=change_brief.brief_id)

        messages: list[MessageParam] = [
            {
                "role": "user",
                "content": _build_user_message(change_brief, bu_profile, past_engagement),
            }
        ]

        response_text, usage = self._call_api(messages)
        cost = _estimate_cost(usage.input_tokens, usage.output_tokens)

        brief, error = self._parse_and_validate(
            response_text, change_brief.change_id, change_brief.brief_id, bu_profile.bu_id
        )

        if brief is None and self._max_validation_retries > 0:
            log.info(
                "buatlas_validation_retry",
                error=error[:200] if error else "unknown",
            )
            messages.append({"role": "assistant", "content": response_text})
            messages.append({"role": "user", "content": _build_correction_message(error or "")})
            response_text2, usage2 = self._call_api(messages)
            cost += _estimate_cost(usage2.input_tokens, usage2.output_tokens)
            brief, error2 = self._parse_and_validate(
                response_text2, change_brief.change_id, change_brief.brief_id, bu_profile.bu_id
            )
            if brief is None:
                log.error(
                    "buatlas_validation_failed",
                    error=error2[:200] if error2 else "unknown",
                )
                raise AgentOutputValidationError(
                    f"PersonalizedBrief validation failed after "
                    f"{self._max_validation_retries + 1} attempts: {error2}"
                )

        elapsed = time.monotonic() - start
        log.info(
            "buatlas_invoke_complete",
            elapsed_s=round(elapsed, 2),
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            usd_estimate=round(cost, 4),
            relevance=str(brief.relevance) if brief else None,
            message_quality=str(brief.message_quality) if brief else None,
        )

        assert brief is not None
        return brief

    @retry(
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
        self,
        text: str,
        expected_change_id: str,
        expected_brief_id: str,
        expected_bu_id: str,
    ) -> tuple[PersonalizedBrief | None, str | None]:
        """Try to parse text as JSON and validate as PersonalizedBrief.

        Returns (brief, None) on success, (None, error_message) on failure.
        """
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

        if not isinstance(raw, dict):
            return None, "Response is not a JSON object"

        # Ensure key IDs match (prevent hallucination)
        if raw.get("change_id") != expected_change_id:
            raw["change_id"] = expected_change_id
        if raw.get("brief_id") != expected_brief_id:
            raw["brief_id"] = expected_brief_id
        if raw.get("bu_id") != expected_bu_id:
            raw["bu_id"] = expected_bu_id

        # Ensure generated IDs are present
        if not raw.get("personalized_brief_id"):
            raw["personalized_brief_id"] = str(uuid.uuid4())
        if isinstance(raw.get("produced_by"), dict) and not raw["produced_by"].get("invocation_id"):
            raw["produced_by"]["invocation_id"] = str(uuid.uuid4())

        # Truncate oversized string fields
        if isinstance(raw.get("message_variants"), dict):
            mv = raw["message_variants"]
            if isinstance(mv.get("push_short"), str):
                mv["push_short"] = mv["push_short"][:240]
            if isinstance(mv.get("teams_medium"), str):
                mv["teams_medium"] = mv["teams_medium"][:600]
            if isinstance(mv.get("email_long"), str):
                mv["email_long"] = mv["email_long"][:1200]
        for dec in raw.get("decisions") or []:
            if isinstance(dec, dict) and isinstance(dec.get("reason"), str):
                dec["reason"] = dec["reason"][:1000]

        try:
            brief = PersonalizedBrief.model_validate(raw)
            return brief, None
        except ValidationError as exc:
            return None, str(exc)
