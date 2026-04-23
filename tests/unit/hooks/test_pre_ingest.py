"""Unit tests for pre_ingest hook."""

from pulsecraft.hooks.base import HookContext
from pulsecraft.hooks.pre_ingest import run


def _ctx(raw_text: object) -> HookContext:
    return HookContext(stage="pre_ingest", change_id="change-001", payload={"raw_text": raw_text})


def test_passes_clean_text():
    result = run(_ctx("No sensitive content here."))
    assert result.outcome == "pass"
    assert result.details["redacted_text"] == "No sensitive content here."
    assert result.audit_payload["redaction_applied"] is False


def test_redacts_email():
    result = run(_ctx("Contact user@example.com about the ticket."))
    assert result.outcome == "pass"
    redacted = result.details["redacted_text"]
    assert "user@example.com" not in redacted
    assert result.audit_payload["redaction_applied"] is True


def test_redacts_ssn():
    result = run(_ctx("SSN: 123-45-6789 for the patient."))
    assert result.outcome == "pass"
    assert "123-45-6789" not in result.details["redacted_text"]
    assert result.audit_payload["redaction_applied"] is True


def test_fails_when_raw_text_not_string():
    result = run(_ctx(None))
    assert result.outcome == "fail"
    assert "raw_text" in result.reason.lower() or "string" in result.reason.lower()


def test_fails_when_raw_text_is_int():
    result = run(_ctx(42))
    assert result.outcome == "fail"
    assert result.details.get("raw_text_type") == "int"


def test_fails_when_raw_text_missing():
    ctx = HookContext(stage="pre_ingest", change_id="c1", payload={})
    result = run(ctx)
    assert result.outcome == "fail"


def test_chars_in_out_tracked():
    text = "hello world"
    result = run(_ctx(text))
    assert result.audit_payload["chars_in"] == len(text)
    assert result.audit_payload["chars_out"] >= 0


def test_empty_string_passes():
    result = run(_ctx(""))
    assert result.outcome == "pass"
    assert result.details["redacted_text"] == ""
    assert result.audit_payload["redaction_applied"] is False
