"""Unit tests for HookContext and HookResult."""

from pulsecraft.hooks.base import HookContext, HookResult


def test_hook_result_passed_default():
    r = HookResult.passed()
    assert r.outcome == "pass"
    assert r.reason == ""
    assert r.details == {}


def test_hook_result_passed_with_kwargs():
    r = HookResult.passed(reason="ok", redacted_text="x")
    assert r.outcome == "pass"
    assert r.reason == "ok"
    assert r.details == {"redacted_text": "x"}


def test_hook_result_failed():
    r = HookResult.failed("bad input", field="raw_text")
    assert r.outcome == "fail"
    assert r.reason == "bad input"
    assert r.details == {"field": "raw_text"}


def test_hook_result_skipped():
    r = HookResult.skipped("no hook registered")
    assert r.outcome == "skip"
    assert r.reason == "no hook registered"


def test_hook_context_defaults():
    ctx = HookContext(stage="pre_ingest")
    assert ctx.stage == "pre_ingest"
    assert ctx.change_id is None
    assert ctx.payload == {}


def test_hook_context_with_payload():
    ctx = HookContext(stage="post_agent", change_id="abc-123", payload={"key": "val"})
    assert ctx.change_id == "abc-123"
    assert ctx.payload["key"] == "val"
