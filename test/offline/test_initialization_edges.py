"""Initialization edge cases: ADR-001; QA-01, INV-01/03/04, COST-01."""

import json
import socket
from pathlib import Path

import pytest
from pydantic import ValidationError
from pytest_socket import SocketBlockedError

from papertrace.contracts import AnswerDraft, ReleaseDecision

FIXTURES = Path(__file__).parents[1] / "fixtures" / "contracts"


def fixture_payload(name):
    """QA-01: use the published handwritten synthetic records, never a provider."""
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))["data"]


def test_initial_review_revision_zero_can_record_abstention():
    """INV-01/03: a question with no human events has revision zero, not a fake event."""
    payload = fixture_payload("AnswerDraft") | {
        "review_revision": 0,
        "approved_evidence_ids": [],
        "sent_evidence_ids": [],
        "citation_evidence_ids": [],
        "status": "abstained",
        "body": "",
        "refusal_reason": "NO_APPROVED_EVIDENCE",
    }
    answer = AnswerDraft.model_validate(payload)
    assert answer.review_revision == 0
    assert AnswerDraft.model_validate_json(answer.model_dump_json()) == answer


def test_initial_review_revision_zero_can_record_blocked_release():
    """INV-01/04: a blocked decision may describe the initial unreviewed state."""
    payload = fixture_payload("ReleaseDecision") | {
        "review_revision": 0,
        "status": "blocked",
        "review_check_passed": False,
        "reason_codes": ["NO_REVIEW_EVENTS"],
    }
    decision = ReleaseDecision.model_validate(payload)
    assert decision.review_revision == 0


@pytest.mark.parametrize("name,model", [("AnswerDraft", AnswerDraft), ("ReleaseDecision", ReleaseDecision)])
def test_revision_zero_cannot_claim_approved_draft_or_release(name, model):
    """INV-03/04: revision zero never substantiates an approved draft or release."""
    payload = fixture_payload(name) | {"review_revision": 0}
    if name == "ReleaseDecision":
        payload |= {
            "status": "released", "reason_codes": [],
            "snapshot_check_passed": True, "review_check_passed": True,
            "evidence_check_passed": True, "citation_check_passed": True,
            "answer_check_passed": True,
        }
    with pytest.raises(ValidationError):
        model.model_validate(payload)


def test_offline_socket_creation_is_blocked():
    """COST-01: an ordinary new test socket is actually blocked by pytest-socket."""
    with pytest.warns(UserWarning, match="socket.socket"), pytest.raises(SocketBlockedError):
        socket.socket()
