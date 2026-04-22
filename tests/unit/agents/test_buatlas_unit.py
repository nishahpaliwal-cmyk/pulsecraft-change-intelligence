"""Unit tests for BUAtlas — mocked Anthropic client, no real API calls."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from anthropic.types import TextBlock, Usage

from pulsecraft.agents.buatlas import (
    AgentInvocationError,
    AgentOutputValidationError,
    BUAtlas,
)
from pulsecraft.orchestrator.agent_protocol import BUAtlasProtocol
from pulsecraft.schemas.bu_profile import BUProfile
from pulsecraft.schemas.change_brief import ChangeBrief
from pulsecraft.schemas.personalized_brief import PersonalizedBrief

FIXTURES_DIR = Path(__file__).parent.parent.parent.parent / "fixtures" / "changes"
CONFIG_DIR = Path(__file__).parent.parent.parent.parent / "config"


def _make_change_brief() -> ChangeBrief:

    from pulsecraft.schemas.change_artifact import ChangeArtifact

    artifact = ChangeArtifact.model_validate(
        json.loads((FIXTURES_DIR / "change_001_clearcut_communicate.json").read_text())
    )
    # Build a minimal synthetic ChangeBrief instead of calling the real SignalScribe
    from pulsecraft.schemas.change_brief import (
        ChangeType,
        SourceCitation,
        Timeline,
        TimelineStatus,
    )
    from pulsecraft.schemas.change_brief import (
        ProducedBy as CBProducedBy,
    )
    from pulsecraft.schemas.decision import Decision, DecisionAgent, DecisionVerb

    now = datetime.now(tz=UTC)
    agent = DecisionAgent(name="signalscribe", version="1.0")
    return ChangeBrief(
        brief_id=str(uuid.uuid4()),
        change_id=artifact.change_id,
        produced_at=now,
        produced_by=CBProducedBy(version="1.0"),
        summary="PA form validation UI redesigned.",
        before="Single-page form with inline errors.",
        after="Multi-step wizard with real-time field validation.",
        change_type=ChangeType.BEHAVIOR_CHANGE,
        impact_areas=["specialty_pharmacy", "hcp_portal_ordering"],
        affected_segments=["hcp_users"],
        timeline=Timeline(status=TimelineStatus.RIPE),
        required_actions=["Notify field teams of new UI flow."],
        risks=[],
        mitigations=[],
        faq=[],
        sources=[
            SourceCitation(
                type="release_note",
                ref=artifact.source_ref,
                quote="redesigned validation interface",
            )
        ],
        confidence_score=0.92,
        decisions=[
            Decision(
                gate=1,
                verb=DecisionVerb.COMMUNICATE,
                reason="Visible UI change.",
                confidence=0.92,
                decided_at=now,
                agent=agent,
            ),
            Decision(
                gate=2,
                verb=DecisionVerb.RIPE,
                reason="GA rollout imminent.",
                confidence=0.90,
                decided_at=now,
                agent=agent,
            ),
            Decision(
                gate=3,
                verb=DecisionVerb.READY,
                reason="Before/after clearly described.",
                confidence=0.92,
                decided_at=now,
                agent=agent,
            ),
        ],
    )


def _make_bu_profile() -> BUProfile:
    from pulsecraft.config.loader import get_bu_profile

    return get_bu_profile("bu_alpha")


def _valid_personalized_brief_dict(change_brief: ChangeBrief, bu_id: str) -> dict:
    now = datetime.now(tz=UTC).isoformat()
    return {
        "schema_version": "1.0",
        "personalized_brief_id": str(uuid.uuid4()),
        "change_id": change_brief.change_id,
        "brief_id": change_brief.brief_id,
        "bu_id": bu_id,
        "produced_at": now,
        "produced_by": {
            "agent": "buatlas",
            "version": "1.0",
            "invocation_id": str(uuid.uuid4()),
        },
        "relevance": "affected",
        "priority": "P1",
        "why_relevant": "BU owns hcp_portal_ordering; field coordinators submit PAs through this workflow.",
        "recommended_actions": [
            {
                "owner": "Field training coordinator",
                "action": "Brief field staff on new UI steps",
                "by_when": "2026-05-03",
            }
        ],
        "assumptions": ["Assumed rollout timeline applies to this BU's users."],
        "message_variants": {
            "push_short": "HCP portal PA form redesigned to multi-step — West rollout May 5. Prep teams now.",
            "teams_medium": "The prior authorization submission form in the HCP portal has been updated to a multi-step wizard layout. Your field coordinators will see the new UI starting May 5 (West region). Brief them before rollout.",
            "email_long": "The HCP portal PA submission form has been redesigned. The new multi-step wizard replaces the single-page form. West region rollout begins May 5. Action: brief field coordinators this week on the new step order.",
        },
        "message_quality": "worth_sending",
        "confidence_score": 0.91,
        "decisions": [
            {
                "gate": 4,
                "verb": "AFFECTED",
                "reason": "BU owns hcp_portal_ordering; field coordinators submit PAs through the changed workflow.",
                "confidence": 0.91,
                "decided_at": now,
                "agent": {"name": "buatlas", "version": "1.0"},
                "payload": None,
            },
            {
                "gate": 5,
                "verb": "WORTH_SENDING",
                "reason": "Message names specific BU consequence (field coordinator prep) and concrete deadline.",
                "confidence": 0.90,
                "decided_at": now,
                "agent": {"name": "buatlas", "version": "1.0"},
                "payload": None,
            },
        ],
        "regeneration_attempts": 0,
    }


def _valid_not_affected_dict(change_brief: ChangeBrief, bu_id: str) -> dict:
    now = datetime.now(tz=UTC).isoformat()
    return {
        "schema_version": "1.0",
        "personalized_brief_id": str(uuid.uuid4()),
        "change_id": change_brief.change_id,
        "brief_id": change_brief.brief_id,
        "bu_id": bu_id,
        "produced_at": now,
        "produced_by": {
            "agent": "buatlas",
            "version": "1.0",
            "invocation_id": str(uuid.uuid4()),
        },
        "relevance": "not_affected",
        "priority": None,
        "why_relevant": "",
        "recommended_actions": [],
        "assumptions": ["PA form is not in this BU's product area."],
        "message_variants": None,
        "message_quality": None,
        "confidence_score": 0.88,
        "decisions": [
            {
                "gate": 4,
                "verb": "NOT_AFFECTED",
                "reason": "BU does not own or operate hcp_portal_ordering or specialty_pharmacy.",
                "confidence": 0.88,
                "decided_at": now,
                "agent": {"name": "buatlas", "version": "1.0"},
                "payload": None,
            }
        ],
        "regeneration_attempts": 0,
    }


def _mock_message(text: str, input_tokens: int = 600, output_tokens: int = 900) -> MagicMock:
    usage = MagicMock(spec=Usage)
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens
    content_block = TextBlock(type="text", text=text)
    msg = MagicMock()
    msg.content = [content_block]
    msg.usage = usage
    return msg


class TestBUAtlasProtocolCompliance:
    def test_satisfies_protocol(self) -> None:
        ba = BUAtlas.__new__(BUAtlas)
        ba._model = "claude-sonnet-4-6"
        ba._max_validation_retries = 1
        ba._client = MagicMock()
        ba._system_prompt = "test"
        assert isinstance(ba, BUAtlasProtocol)

    def test_agent_name_is_canonical(self) -> None:
        assert BUAtlas.agent_name == "buatlas"

    def test_version_is_string(self) -> None:
        assert isinstance(BUAtlas.version, str)


class TestBUAtlasInit:
    def test_loads_prompt_from_default_path(self) -> None:
        with patch("anthropic.Anthropic"):
            ba = BUAtlas()
        assert len(ba._system_prompt) > 100

    def test_raises_if_prompt_file_missing(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            BUAtlas(prompt_path=tmp_path / "nonexistent.md")

    def test_loads_prompt_from_custom_path(self, tmp_path: Path) -> None:
        prompt_file = tmp_path / "prompt.md"
        prompt_file.write_text("# Test BUAtlas prompt", encoding="utf-8")
        with patch("anthropic.Anthropic"):
            ba = BUAtlas(prompt_path=prompt_file)
        assert ba._system_prompt == "# Test BUAtlas prompt"

    def test_uses_provided_client(self) -> None:
        mock_client = MagicMock()
        ba = BUAtlas(anthropic_client=mock_client)
        assert ba._client is mock_client


class TestBUAtlasInvoke:
    def test_returns_valid_personalized_brief_affected(self) -> None:
        cb = _make_change_brief()
        bu = _make_bu_profile()
        valid_json = json.dumps(_valid_personalized_brief_dict(cb, bu.bu_id))
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_message(valid_json)
        ba = BUAtlas(anthropic_client=mock_client)
        result = ba.invoke(cb, bu)
        assert isinstance(result, PersonalizedBrief)
        assert result.change_id == cb.change_id
        assert result.brief_id == cb.brief_id
        assert result.bu_id == bu.bu_id

    def test_decisions_array_has_two_entries_when_affected(self) -> None:
        cb = _make_change_brief()
        bu = _make_bu_profile()
        valid_json = json.dumps(_valid_personalized_brief_dict(cb, bu.bu_id))
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_message(valid_json)
        ba = BUAtlas(anthropic_client=mock_client)
        result = ba.invoke(cb, bu)
        assert len(result.decisions) == 2
        assert result.decisions[0].gate == 4
        assert result.decisions[1].gate == 5

    def test_decisions_array_has_one_entry_when_not_affected(self) -> None:
        cb = _make_change_brief()
        bu = _make_bu_profile()
        valid_json = json.dumps(_valid_not_affected_dict(cb, bu.bu_id))
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_message(valid_json)
        ba = BUAtlas(anthropic_client=mock_client)
        result = ba.invoke(cb, bu)
        assert len(result.decisions) == 1
        assert result.decisions[0].gate == 4

    def test_decisions_agent_name_is_canonical(self) -> None:
        cb = _make_change_brief()
        bu = _make_bu_profile()
        valid_json = json.dumps(_valid_personalized_brief_dict(cb, bu.bu_id))
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_message(valid_json)
        ba = BUAtlas(anthropic_client=mock_client)
        result = ba.invoke(cb, bu)
        for decision in result.decisions:
            assert decision.agent.name == "buatlas"

    def test_fixes_wrong_change_id(self) -> None:
        cb = _make_change_brief()
        bu = _make_bu_profile()
        brief_dict = _valid_personalized_brief_dict(cb, bu.bu_id)
        brief_dict["change_id"] = "00000000-0000-0000-0000-000000000000"
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_message(json.dumps(brief_dict))
        ba = BUAtlas(anthropic_client=mock_client)
        result = ba.invoke(cb, bu)
        assert result.change_id == cb.change_id

    def test_fixes_wrong_brief_id(self) -> None:
        cb = _make_change_brief()
        bu = _make_bu_profile()
        brief_dict = _valid_personalized_brief_dict(cb, bu.bu_id)
        brief_dict["brief_id"] = "00000000-0000-0000-0000-000000000000"
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_message(json.dumps(brief_dict))
        ba = BUAtlas(anthropic_client=mock_client)
        result = ba.invoke(cb, bu)
        assert result.brief_id == cb.brief_id

    def test_fixes_wrong_bu_id(self) -> None:
        cb = _make_change_brief()
        bu = _make_bu_profile()
        brief_dict = _valid_personalized_brief_dict(cb, bu.bu_id)
        brief_dict["bu_id"] = "wrong_bu"
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_message(json.dumps(brief_dict))
        ba = BUAtlas(anthropic_client=mock_client)
        result = ba.invoke(cb, bu)
        assert result.bu_id == bu.bu_id

    def test_strips_markdown_fences(self) -> None:
        cb = _make_change_brief()
        bu = _make_bu_profile()
        valid_dict = _valid_personalized_brief_dict(cb, bu.bu_id)
        fenced = "```json\n" + json.dumps(valid_dict) + "\n```"
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_message(fenced)
        ba = BUAtlas(anthropic_client=mock_client)
        result = ba.invoke(cb, bu)
        assert isinstance(result, PersonalizedBrief)

    def test_truncates_message_variants(self) -> None:
        cb = _make_change_brief()
        bu = _make_bu_profile()
        brief_dict = _valid_personalized_brief_dict(cb, bu.bu_id)
        brief_dict["message_variants"]["push_short"] = "X" * 300
        brief_dict["message_variants"]["teams_medium"] = "Y" * 700
        brief_dict["message_variants"]["email_long"] = "Z" * 1500
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_message(json.dumps(brief_dict))
        ba = BUAtlas(anthropic_client=mock_client)
        result = ba.invoke(cb, bu)
        assert len(result.message_variants.push_short) <= 240
        assert len(result.message_variants.teams_medium) <= 600
        assert len(result.message_variants.email_long) <= 1200

    def test_isolation_between_calls(self) -> None:
        """Same BUAtlas instance can be called twice with different BU profiles."""
        cb = _make_change_brief()
        bu_alpha = _make_bu_profile()
        from pulsecraft.config.loader import get_bu_profile

        bu_beta = get_bu_profile("bu_beta")

        alpha_dict = _valid_personalized_brief_dict(cb, bu_alpha.bu_id)
        beta_dict = _valid_not_affected_dict(cb, bu_beta.bu_id)

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = [
            _mock_message(json.dumps(alpha_dict)),
            _mock_message(json.dumps(beta_dict)),
        ]
        ba = BUAtlas(anthropic_client=mock_client)

        result_alpha = ba.invoke(cb, bu_alpha)
        result_beta = ba.invoke(cb, bu_beta)

        assert result_alpha.bu_id == bu_alpha.bu_id
        assert result_beta.bu_id == bu_beta.bu_id
        assert result_alpha.relevance != result_beta.relevance


class TestBUAtlasRetry:
    def test_retries_once_on_invalid_json(self) -> None:
        cb = _make_change_brief()
        bu = _make_bu_profile()
        valid_json = json.dumps(_valid_personalized_brief_dict(cb, bu.bu_id))
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = [
            _mock_message("not valid json at all"),
            _mock_message(valid_json),
        ]
        ba = BUAtlas(anthropic_client=mock_client, max_validation_retries=1)
        result = ba.invoke(cb, bu)
        assert isinstance(result, PersonalizedBrief)
        assert mock_client.messages.create.call_count == 2

    def test_retries_once_on_schema_validation_failure(self) -> None:
        cb = _make_change_brief()
        bu = _make_bu_profile()
        invalid_dict = _valid_personalized_brief_dict(cb, bu.bu_id)
        invalid_dict["confidence_score"] = 999.9
        valid_json = json.dumps(_valid_personalized_brief_dict(cb, bu.bu_id))
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = [
            _mock_message(json.dumps(invalid_dict)),
            _mock_message(valid_json),
        ]
        ba = BUAtlas(anthropic_client=mock_client, max_validation_retries=1)
        result = ba.invoke(cb, bu)
        assert isinstance(result, PersonalizedBrief)

    def test_raises_validation_error_after_max_retries(self) -> None:
        cb = _make_change_brief()
        bu = _make_bu_profile()
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_message("not json")
        ba = BUAtlas(anthropic_client=mock_client, max_validation_retries=1)
        with pytest.raises(AgentOutputValidationError):
            ba.invoke(cb, bu)

    def test_raises_invocation_error_on_auth_failure(self) -> None:
        import anthropic as anthropic_lib

        cb = _make_change_brief()
        bu = _make_bu_profile()
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = anthropic_lib.AuthenticationError(
            message="Invalid API key", response=MagicMock(), body={}
        )
        ba = BUAtlas(anthropic_client=mock_client)
        with pytest.raises(AgentInvocationError):
            ba.invoke(cb, bu)


class TestBUAtlasOutputContract:
    def test_confidence_score_in_range(self) -> None:
        cb = _make_change_brief()
        bu = _make_bu_profile()
        valid_json = json.dumps(_valid_personalized_brief_dict(cb, bu.bu_id))
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_message(valid_json)
        ba = BUAtlas(anthropic_client=mock_client)
        result = ba.invoke(cb, bu)
        assert 0.0 <= result.confidence_score <= 1.0

    def test_produced_by_agent_name_is_buatlas(self) -> None:
        cb = _make_change_brief()
        bu = _make_bu_profile()
        valid_json = json.dumps(_valid_personalized_brief_dict(cb, bu.bu_id))
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_message(valid_json)
        ba = BUAtlas(anthropic_client=mock_client)
        result = ba.invoke(cb, bu)
        assert result.produced_by.agent == "buatlas"

    def test_invocation_id_is_uuid(self) -> None:
        cb = _make_change_brief()
        bu = _make_bu_profile()
        valid_json = json.dumps(_valid_personalized_brief_dict(cb, bu.bu_id))
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_message(valid_json)
        ba = BUAtlas(anthropic_client=mock_client)
        result = ba.invoke(cb, bu)
        # Validate format
        uuid.UUID(result.produced_by.invocation_id)
