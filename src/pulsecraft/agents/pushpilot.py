"""PushPilot — real LLM-backed delivery timing agent (gate 6).

Loads its system prompt from .claude/agents/pushpilot.md at init time.
One invocation per WORTH_SENDING PersonalizedBrief. Sequential — no fan-out.

Agent's job: express a delivery preference (SEND_NOW / HOLD_UNTIL / DIGEST / ESCALATE).
Orchestrator's job: enforce policy invariants (quiet hours, rate limits, channel approval).
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
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
from pulsecraft.schemas.personalized_brief import PersonalizedBrief
from pulsecraft.schemas.push_pilot_output import PushPilotOutput

logger = structlog.get_logger(__name__)

_INPUT_PRICE_PER_MTK = 3.00
_OUTPUT_PRICE_PER_MTK = 15.00

_DEFAULT_PROMPT_PATH = (
    Path(__file__).parent.parent.parent.parent / ".claude" / "agents" / "pushpilot.md"
)


class AgentInvocationError(Exception):
    """Raised after all API retry attempts are exhausted."""


class AgentOutputValidationError(Exception):
    """Raised when response fails PushPilotOutput validation after max retries."""


def _estimate_cost(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens * _INPUT_PRICE_PER_MTK + output_tokens * _OUTPUT_PRICE_PER_MTK) / 1_000_000


def _build_user_message(
    personalized_brief: PersonalizedBrief,
    bu_profile: BUProfile,
    recent_volume: dict,
    current_utc: datetime,
) -> str:
    input_obj = {
        "personalized_brief": json.loads(personalized_brief.model_dump_json()),
        "bu_profile": json.loads(bu_profile.model_dump_json()),
        "current_utc_time": current_utc.isoformat(),
        "recent_notification_volume": recent_volume,
    }
    return (
        "Evaluate the following input and produce a PushPilotOutput JSON object.\n\n"
        f"INPUT:\n{json.dumps(input_obj, indent=2)}\n\n"
        "REMINDER: Respond with ONLY a valid JSON object. No prose, no code fences.\n"
        'Set gate_decision.gate = 6 and gate_decision.agent.name = "pushpilot".\n'
        "decision and gate_decision.verb must match (send_now ↔ SEND_NOW, etc.)."
    )


def _build_correction_message(validation_error: str) -> str:
    return (
        "Your previous response failed JSON schema validation. Fix it and return ONLY valid JSON.\n\n"
        f"VALIDATION ERROR:\n{validation_error}\n\n"
        "Return the corrected JSON object only. No prose. No code fences."
    )


def _verb_for_decision(decision: str) -> str:
    """Map decision lowercase to gate_decision verb uppercase form."""
    return decision.upper()


class PushPilot:
    """Real PushPilot implementation using Claude Sonnet 4.6.

    Satisfies PushPilotProtocol. Agent expresses a delivery preference; the
    orchestrator enforces policy invariants (quiet hours, rate limits, channels).
    """

    agent_name = "pushpilot"
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
            raise FileNotFoundError(f"PushPilot prompt not found: {path}")
        self._system_prompt = path.read_text(encoding="utf-8")

        logger.debug(
            "pushpilot_initialized",
            model=self._model,
            prompt_lines=self._system_prompt.count("\n"),
        )

    def invoke(
        self,
        personalized_brief: PersonalizedBrief,
        bu_profile: BUProfile,
    ) -> PushPilotOutput:
        """Gate 6. Returns agent's preference + reason.

        The orchestrator applies policy overrides (quiet hours, rate limits,
        channel approval) after this call. This method expresses the preference only.

        Raises AgentInvocationError on API failure after retries.
        Raises AgentOutputValidationError on persistent validation failure.
        """
        start = time.monotonic()
        current_utc = datetime.now(UTC)
        recent_volume = {"last_24h": 0, "last_7d": 0}  # v1: no tracking yet

        log = logger.bind(
            change_id=personalized_brief.change_id,
            bu_id=bu_profile.bu_id,
            agent=self.agent_name,
        )
        log.info(
            "pushpilot_invoke_start",
            brief_id=personalized_brief.brief_id,
            priority=str(personalized_brief.priority),
        )

        messages: list[MessageParam] = [
            {
                "role": "user",
                "content": _build_user_message(
                    personalized_brief, bu_profile, recent_volume, current_utc
                ),
            }
        ]

        response_text, usage = self._call_api(messages)
        cost = _estimate_cost(usage.input_tokens, usage.output_tokens)

        output, error = self._parse_and_validate(response_text, current_utc)

        if output is None and self._max_validation_retries > 0:
            log.info("pushpilot_validation_retry", error=error[:200] if error else "unknown")
            messages.append({"role": "assistant", "content": response_text})
            messages.append({"role": "user", "content": _build_correction_message(error or "")})
            response_text2, usage2 = self._call_api(messages)
            cost += _estimate_cost(usage2.input_tokens, usage2.output_tokens)
            output, error2 = self._parse_and_validate(response_text2, current_utc)
            if output is None:
                log.error(
                    "pushpilot_validation_failed", error=error2[:200] if error2 else "unknown"
                )
                raise AgentOutputValidationError(
                    f"PushPilotOutput validation failed after "
                    f"{self._max_validation_retries + 1} attempts: {error2}"
                )

        elapsed = time.monotonic() - start
        log.info(
            "pushpilot_invoke_complete",
            elapsed_s=round(elapsed, 2),
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            usd_estimate=round(cost, 4),
            decision=str(output.decision) if output else None,
            channel=str(output.channel) if output and output.channel else None,
        )

        assert output is not None
        output.usd_estimate = round(cost, 4)
        return output

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
            max_tokens=2048,
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
        current_utc: datetime,
    ) -> tuple[PushPilotOutput | None, str | None]:
        """Try to parse text as JSON and validate as PushPilotOutput.

        Returns (output, None) on success, (None, error_message) on failure.
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

        # Normalise gate_decision to ensure invariants
        gate_dec = raw.get("gate_decision")
        if isinstance(gate_dec, dict):
            gate_dec["gate"] = 6
            if not isinstance(gate_dec.get("agent"), dict):
                gate_dec["agent"] = {"name": "pushpilot", "version": "1.0"}
            else:
                gate_dec["agent"]["name"] = "pushpilot"
            if not gate_dec.get("decided_at"):
                gate_dec["decided_at"] = current_utc.isoformat()
            # Sync verb with top-level decision
            decision_str = raw.get("decision", "")
            if decision_str:
                gate_dec["verb"] = _verb_for_decision(decision_str)
            # Truncate reason
            if isinstance(gate_dec.get("reason"), str):
                gate_dec["reason"] = gate_dec["reason"][:1000]

        if isinstance(raw.get("reason"), str):
            raw["reason"] = raw["reason"][:1000]

        # scheduled_time must be present for hold_until
        if raw.get("decision") == "hold_until" and not raw.get("scheduled_time"):
            # Provide a 09:00 next-business-day UTC placeholder rather than failing
            from datetime import timedelta

            next_day = current_utc.replace(hour=9, minute=0, second=0, microsecond=0)
            if next_day <= current_utc:
                next_day += timedelta(days=1)
            raw["scheduled_time"] = next_day.isoformat()

        try:
            output = PushPilotOutput.model_validate(raw)
            return output, None
        except ValidationError as exc:
            return None, str(exc)
