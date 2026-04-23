"""Unit tests for audit_hook."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from pulsecraft.hooks.audit_hook import run
from pulsecraft.hooks.base import HookContext

_UUID = str(uuid.uuid4())
_UUID2 = str(uuid.uuid4())


def _make_writer() -> MagicMock:
    writer = MagicMock()
    writer.log_event = MagicMock()
    return writer


def _ctx(
    audit_writer: object | None = None,
    hook_name: str = "pre_ingest",
    hook_outcome: str = "pass",
    hook_reason: str = "all clear",
    change_id: str | None = _UUID,
) -> HookContext:
    return HookContext(
        stage="audit",
        change_id=change_id,
        payload={
            "audit_writer": audit_writer,
            "hook_name": hook_name,
            "hook_outcome": hook_outcome,
            "hook_reason": hook_reason,
        },
    )


def test_writes_audit_record_on_pass():
    writer = _make_writer()
    result = run(_ctx(audit_writer=writer, hook_outcome="pass"))
    assert result.outcome == "pass"
    writer.log_event.assert_called_once()
    record = writer.log_event.call_args[0][0]
    assert record.event_type == "hook_fired"
    assert record.outcome == "success"


def test_writes_audit_record_on_fail():
    writer = _make_writer()
    result = run(_ctx(audit_writer=writer, hook_outcome="fail", hook_reason="blocked"))
    assert result.outcome == "pass"
    record = writer.log_event.call_args[0][0]
    assert record.outcome == "failure"
    assert "FAIL" in record.output_summary


def test_skips_when_no_audit_writer():
    result = run(_ctx(audit_writer=None))
    assert result.outcome == "pass"
    assert "skipped" in result.reason.lower()


def test_skips_when_no_change_id():
    writer = _make_writer()
    result = run(_ctx(audit_writer=writer, change_id=None))
    assert result.outcome == "pass"
    writer.log_event.assert_not_called()


def test_fail_open_on_write_error():
    writer = _make_writer()
    writer.log_event.side_effect = RuntimeError("disk full")
    result = run(_ctx(audit_writer=writer))
    assert result.outcome == "pass"


def test_hook_name_in_audit_record():
    writer = _make_writer()
    run(_ctx(audit_writer=writer, hook_name="post_agent"))
    record = writer.log_event.call_args[0][0]
    assert record.actor.id == "post_agent"


def test_change_id_in_audit_record():
    writer = _make_writer()
    run(_ctx(audit_writer=writer, change_id=_UUID2))
    record = writer.log_event.call_args[0][0]
    assert record.change_id == _UUID2
