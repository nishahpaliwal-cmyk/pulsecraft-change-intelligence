"""Tests for HITLQueue — file-based pending/approved/rejected queue."""

import uuid
from pathlib import Path

import pytest

from pulsecraft.orchestrator.audit import AuditWriter
from pulsecraft.orchestrator.hitl import HITLQueue, HITLReason, HITLStatus


@pytest.fixture()
def queue(tmp_path: Path) -> HITLQueue:
    audit = AuditWriter(root=tmp_path / "audit")
    return HITLQueue(audit_writer=audit, root=tmp_path / "queue")


class TestEnqueue:
    def test_enqueue_creates_pending_file(self, queue: HITLQueue) -> None:
        cid = str(uuid.uuid4())
        queue.enqueue(cid, HITLReason.AGENT_ESCALATE)
        assert queue.is_pending(cid)

    def test_enqueue_with_payload(self, queue: HITLQueue) -> None:
        cid = str(uuid.uuid4())
        payload = {"brief_id": str(uuid.uuid4()), "reason": "test"}
        queue.enqueue(cid, HITLReason.NEED_CLARIFICATION, payload=payload)
        items = queue.list_pending()
        assert len(items) == 1
        assert items[0].payload["brief_id"] == payload["brief_id"]

    def test_enqueue_writes_audit_record(self, tmp_path: Path) -> None:
        audit = AuditWriter(root=tmp_path / "audit")
        q = HITLQueue(audit_writer=audit, root=tmp_path / "queue")
        cid = str(uuid.uuid4())
        q.enqueue(cid, HITLReason.PRIORITY_P0)
        chain = audit.read_chain(cid)
        assert len(chain) == 1
        assert chain[0].action == "enqueued"

    def test_list_pending_empty_initially(self, queue: HITLQueue) -> None:
        assert queue.list_pending() == []

    def test_list_pending_returns_all_items(self, queue: HITLQueue) -> None:
        cids = [str(uuid.uuid4()) for _ in range(3)]
        for cid in cids:
            queue.enqueue(cid, HITLReason.CONFIDENCE_BELOW_THRESHOLD)
        pending = queue.list_pending()
        assert len(pending) == 3


class TestApprove:
    def test_approve_moves_to_approved(self, queue: HITLQueue) -> None:
        cid = str(uuid.uuid4())
        queue.enqueue(cid, HITLReason.AGENT_ESCALATE)
        queue.approve(cid, reviewer="reviewer_a", notes="looks good")
        assert not queue.is_pending(cid)
        approved_file = queue._path("approved", cid)
        assert approved_file.exists()

    def test_approve_writes_reviewer_and_notes(self, queue: HITLQueue) -> None:
        cid = str(uuid.uuid4())
        queue.enqueue(cid, HITLReason.PRIORITY_P0)
        queue.approve(cid, reviewer="reviewer_b", notes="all clear")
        import json

        data = json.loads(queue._path("approved", cid).read_text())
        assert data["reviewer"] == "reviewer_b"
        assert data["reviewer_notes"] == "all clear"
        assert data["status"] == HITLStatus.APPROVED

    def test_approve_nonexistent_raises(self, queue: HITLQueue) -> None:
        with pytest.raises(KeyError):
            queue.approve("nonexistent-id", reviewer="someone")


class TestReject:
    def test_reject_moves_to_rejected(self, queue: HITLQueue) -> None:
        cid = str(uuid.uuid4())
        queue.enqueue(cid, HITLReason.MLR_SENSITIVE)
        queue.reject(cid, reviewer="reviewer_c", reason="contains restricted term")
        assert not queue.is_pending(cid)
        rejected_file = queue._path("rejected", cid)
        assert rejected_file.exists()

    def test_reject_preserves_reason(self, queue: HITLQueue) -> None:
        cid = str(uuid.uuid4())
        queue.enqueue(cid, HITLReason.RESTRICTED_TERM_DETECTED)
        queue.reject(cid, reviewer="reviewer_d", reason="sensitive content")
        import json

        data = json.loads(queue._path("rejected", cid).read_text())
        assert data["reviewer_notes"] == "sensitive content"
        assert data["status"] == HITLStatus.REJECTED


class TestEdit:
    def test_edit_records_change(self, queue: HITLQueue) -> None:
        cid = str(uuid.uuid4())
        queue.enqueue(cid, HITLReason.DRAFT_HAS_COMMITMENT)
        queue.edit(cid, "message_variants.push_short", "Updated message", reviewer="editor_a")
        import json

        data = json.loads(queue._path("pending", cid).read_text())
        assert len(data["edits"]) == 1
        assert data["edits"][0]["field_path"] == "message_variants.push_short"
        assert data["edits"][0]["new_value"] == "Updated message"

    def test_edit_nonexistent_raises(self, queue: HITLQueue) -> None:
        with pytest.raises(KeyError):
            queue.edit("nonexistent-id", "field", "value", reviewer="r")


class TestAnswerClarification:
    def test_answer_saves_answers(self, queue: HITLQueue) -> None:
        cid = str(uuid.uuid4())
        queue.enqueue(cid, HITLReason.NEED_CLARIFICATION)
        answers = {"q1": "US only", "q2": "GA rollout May 1"}
        queue.answer_clarification(cid, answers=answers, reviewer="sme_a")
        import json

        data = json.loads(queue._path("pending", cid).read_text())
        assert data["clarification_answers"] == answers
        assert data["status"] == HITLStatus.ANSWERED


class TestHITLReasonEnum:
    def test_all_reasons_are_strings(self) -> None:
        for reason in HITLReason:
            assert isinstance(reason, str)

    def test_expected_reasons_exist(self) -> None:
        assert HITLReason.AGENT_ESCALATE == "agent_escalate"
        assert HITLReason.NEED_CLARIFICATION == "need_clarification"
        assert HITLReason.CONFIDENCE_BELOW_THRESHOLD == "confidence_below_threshold"
        assert HITLReason.MLR_SENSITIVE == "mlr_sensitive"
