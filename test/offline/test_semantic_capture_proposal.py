"""Contract tests for evaluator intake from B's pre-dispatch request observer."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from runpy import run_path

import pytest

from papertrace.answer.generation import (
    AnswerGenerationOutcome,
    GenerationAccounting,
    GenerationCallResult,
)
from papertrace.contracts import AnswerDraft

ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = ROOT / "test/evaluation/cases.json"
SYSTEM_PATH = ROOT / "prompts/answer-system-v1.0.txt"
EVALUATOR_PATH = ROOT / "test/evaluation/evaluator.py"
CASE_ID = "QUAL-02"
RUNTIME_A = "ev-" + "a" * 64
RUNTIME_B = "ev-" + "b" * 64
FIXED_TO_RUNTIME = {"ev-a": RUNTIME_A, "ev-b": RUNTIME_B}


def digest(value):
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return sha256(encoded).hexdigest()


@pytest.fixture
def fixed_case():
    raw = DATASET_PATH.read_bytes()
    case = next(case for case in json.loads(raw)["cases"] if case["id"] == CASE_ID)
    return sha256(raw).hexdigest(), case, SYSTEM_PATH.read_bytes().decode("utf-8")


@pytest.fixture
def collect_attempt():
    def invoke(**kwargs):
        if not EVALUATOR_PATH.is_file():
            pytest.fail("Evaluator capture entry point is pending: evaluator.py is absent")
        implementation = run_path(str(EVALUATOR_PATH)).get("collect_attempt")
        if not callable(implementation):
            pytest.fail("Evaluator capture entry point is pending: collect_attempt is absent")
        return implementation(**kwargs)

    return invoke


def request_messages(case, system, sent, *, indent=2):
    evidence = {item["id"]: item for item in case["input"]["approved_evidence"]}
    body = {
        "question": case["input"]["question"],
        "approved_evidence": [evidence[identifier] for identifier in sent],
    }
    return (("system", system), ("user", json.dumps(body, indent=indent, ensure_ascii=False)))


SNAPSHOT_ID = 'snap-' + 'c' * 64
REVIEW_DIGEST = 'd' * 64
GENERATED_AT = datetime(2026, 11, 25, tzinfo=timezone.utc)
QUESTION_ID = 'q-eval-1'
QUESTION_TEXT = 'What does the synthetic resonance cell store?'
UNKNOWN_ALIAS = 'b-unknown'


def _accounting(attempts):
    """Build D's validated accounting model rather than a bare namespace."""
    return GenerationAccounting(
        provider='synthetic-provider',
        model='synthetic-model',
        answer_model_attempts=attempts,
    )


def _draft(*, sent, citations, status='draft'):
    """Build the real AnswerDraft with an explicit schema version.

    sent_evidence_ids records what B actually sent and citation_evidence_ids
    records only what the draft cites, so the two sets stay distinguishable.
    """
    accepted = status == 'draft'
    return AnswerDraft(
        schema_version=1,
        answer_id='ans-eval-1',
        snapshot_id=SNAPSHOT_ID,
        question_id=QUESTION_ID,
        review_revision=1,
        review_digest=REVIEW_DIGEST,
        approved_evidence_ids=(RUNTIME_A, RUNTIME_B),
        sent_evidence_ids=tuple(sent),
        citation_evidence_ids=tuple(citations) if accepted else (),
        status=status,
        body='Synthetic answer (b1).' if accepted else '',
        refusal_reason=None if accepted else 'STALE_REVIEW_DURING_GENERATION',
        generated_at=GENERATED_AT,
    )


def _result(*, sent, citations=(), unknown_keys=()):
    """Build the real GenerationCallResult, which carries alias mappings only."""
    return GenerationCallResult(
        status='SUCCESS' if not unknown_keys else 'AMBIGUOUS_CITATIONS',
        raw_output='Synthetic answer (b1).',
        sent_evidence_ids=tuple(sent),
        citation_aliases=(('b1', citations[0]),) if citations else (),
        unknown_citation_keys=tuple(unknown_keys),
        ambiguous_citation_keys=(),
        refusal_reason=None,
    )


def _outcome(*, draft=None, result=None, accounting=None):
    """Build the real AnswerGenerationOutcome with every required field."""
    return AnswerGenerationOutcome(
        draft=draft,
        reason=None,
        revision_before=1,
        revision_after=1,
        digest_before=REVIEW_DIGEST,
        digest_after=REVIEW_DIGEST,
        sent_request=None,
        result=result,
        raw_unknown_keys=(),
        accounting=accounting,
        question_id=QUESTION_ID,
        question_text=QUESTION_TEXT,
    )


class OfflineBoundary:
    """Contract-real stand-in for D's generation boundary.

    It returns the actual AnswerGenerationOutcome, AnswerDraft and
    GenerationCallResult models, so a collector cannot pass on a synthetic-only
    shape. sent_evidence_ids always carries the pinned send set; citations only
    ever appear on an accepted draft, and an out-of-scope or unknown citation is
    expressed as a failed draft plus a result that reports the rejected key.

    Modes: success, dropped (D keeps accounting, discards result), stale
    (post-call review change), out-of-scope-citation and unknown-citation.
    """

    def __init__(
        self,
        messages,
        citations=(),
        *,
        sent=None,
        attempts=1,
        rejected=False,
        mode='success',
        repeat=1,
    ):
        self.messages = messages
        self.events = []
        self.attempts = attempts
        self.mode = 'dropped' if rejected else mode
        self.citations = tuple(citations)
        self.sent = tuple(sent) if sent is not None else self.citations
        self.response = {
            'request_id': f'offline-{repeat}',
            'model': 'offline-model',
            'model_version': 'synthetic',
            'content': f'Synthetic answer {repeat}',
            'finish_reason': 'stop',
            'usage': {'input_tokens': 8, 'output_tokens': 2, 'total_tokens': 10},
        }

    def generate(self, *, request_observer):
        self.events.append('driver')
        if self.messages is None:
            # Empty approved set: D never reaches the boundary and has no accounting.
            return _outcome(), None
        self.events.append('capture')
        try:
            request_observer(self.messages)
        except ValueError:
            # B refuses before call_single; D still exposes validated zero attempts.
            return _outcome(accounting=_accounting(0)), None
        self.events.append('model')
        if self.mode == "no-accounting":
            draft = _draft(sent=self.sent, citations=self.citations)
            return _outcome(
                draft=draft,
                result=_result(sent=self.sent, citations=self.citations),
                accounting=None,
            ), self.response
        if self.mode == "dropped":
            return _outcome(accounting=_accounting(self.attempts)), None
        if self.mode == 'unknown-citation':
            result = _result(sent=self.sent, unknown_keys=(UNKNOWN_ALIAS,))
            draft = _draft(sent=self.sent, citations=(), status='failed')
            return _outcome(
                draft=draft, result=result, accounting=_accounting(self.attempts)
            ), self.response
        if self.mode == 'out-of-scope-citation':
            # A real citation that was never sent: the draft fails, the result records it.
            result = _result(sent=self.sent, citations=self.citations)
            draft = _draft(sent=self.sent, citations=(), status='failed')
            return _outcome(
                draft=draft, result=result, accounting=_accounting(self.attempts)
            ), self.response
        draft = _draft(
            sent=self.sent,
            citations=self.citations,
            status='failed' if self.mode == 'stale' else 'draft',
        )
        outcome = _outcome(
            draft=draft,
            result=_result(sent=self.sent, citations=self.citations),
            accounting=_accounting(self.attempts),
        )
        return outcome, self.response


def run(collect_attempt, fixed_case, driver, *, repeat=1, bindings=None):
    dataset_sha256, case, system = fixed_case
    if bindings is None:
        bindings = {(dataset_sha256, CASE_ID): {"ev-a": RUNTIME_A, "ev-b": RUNTIME_B}}
    return collect_attempt(
        dataset_sha256=dataset_sha256,
        case=case,
        repeat=repeat,
        system_prompt=system,
        bindings=bindings,
        drive=driver.generate,
    )


def test_boundary_fixture_builds_real_contract_models(fixed_case):
    """Control: the double must construct the real contracts directly."""
    _, case, system = fixed_case
    messages = request_messages(case, system, ("ev-a", "ev-b"))
    sent_ids = (RUNTIME_A, RUNTIME_B)
    driver = OfflineBoundary(messages, (RUNTIME_A,), **{"sent": sent_ids})
    outcome, response = driver.generate(request_observer=lambda _: None)
    assert driver.events == ["driver", "capture", "model"]
    assert isinstance(outcome, AnswerGenerationOutcome)
    draft = outcome.draft
    assert draft is not None and draft.schema_version == 1
    assert draft.sent_evidence_ids == (RUNTIME_A, RUNTIME_B)
    assert draft.citation_evidence_ids == (RUNTIME_A,)
    result = outcome.result
    assert result is not None
    assert result.sent_evidence_ids == (RUNTIME_A, RUNTIME_B)
    assert result.citation_aliases == (("b1", RUNTIME_A),)
    assert outcome.accounting is not None
    assert outcome.accounting.answer_model_attempts == 1
    assert response == driver.response


def test_boundary_rejection_keeps_zero_attempts(fixed_case):
    """Control: observer rejection yields validated zero-attempt accounting."""
    _, case, system = fixed_case
    driver = OfflineBoundary(request_messages(case, system, ("ev-b",)))

    def reject(_messages):
        raise ValueError("capture rejected")

    outcome, response = driver.generate(request_observer=reject)
    assert driver.events == ["driver", "capture"]
    assert outcome.draft is None and outcome.result is None and response is None
    assert outcome.accounting is not None
    assert outcome.accounting.answer_model_attempts == 0

def test_boundary_repeat_fixtures_pin_the_send_set(fixed_case):
    """P1: both repeat calls must pin the real send set, not an empty one."""
    _, case, system = fixed_case
    for indent, repeat in ((2, 1), (None, 2)):
        driver = OfflineBoundary(
            request_messages(case, system, ("ev-b",), indent=indent),
            sent=(RUNTIME_B,),
            repeat=repeat,
        )
        outcome, _ = driver.generate(request_observer=lambda _: None)
        assert outcome.draft is not None
        assert outcome.draft.sent_evidence_ids == (RUNTIME_B,)
        assert outcome.draft.citation_evidence_ids == ()


@pytest.mark.parametrize("mode", ["out-of-scope-citation", "unknown-citation"])
def test_boundary_rejected_citation_keeps_accounting_without_report(fixed_case, mode):
    """P1: out-of-scope and unknown citations fail the draft, not the contract."""
    _, case, system = fixed_case
    driver = OfflineBoundary(
        request_messages(case, system, ("ev-b",)),
        (RUNTIME_A,),
        sent=(RUNTIME_B,),
        mode=mode,
    )
    outcome, _ = driver.generate(request_observer=lambda _: None)
    assert outcome.draft is not None and outcome.draft.status == "failed"
    assert outcome.draft.sent_evidence_ids == (RUNTIME_B,)
    assert outcome.draft.citation_evidence_ids == ()
    assert outcome.result is not None
    assert outcome.accounting is not None
    assert outcome.accounting.answer_model_attempts == 1

@pytest.mark.parametrize("sent", [("ev-a", "ev-b"), ("ev-b", "ev-a"), ("ev-b",)])
def test_qual02_fixture_passes_existing_request_gate(fixed_case, sent):
    _, case, system = fixed_case
    boundary = run_path(str(ROOT / "scripts/semantic_evidence.py"))
    request = [
        {"role": role, "content": content}
        for role, content in request_messages(case, system, sent)
    ]
    boundary["_check_request"]({"request": request, "sent_ids": sent}, case, system)


@pytest.mark.parametrize(
    ("sent", "runtime_citation", "fixed_citation"),
    [
        (("ev-a", "ev-b"), RUNTIME_A, "ev-a"),
        (("ev-b", "ev-a"), RUNTIME_B, "ev-b"),
        (("ev-b",), RUNTIME_B, "ev-b"),
    ],
    ids=("forward", "reverse", "cropped"),
)
def test_record_uses_actual_request_and_mapped_citations(
    collect_attempt, fixed_case, sent, runtime_citation, fixed_citation,
):
    _, case, system = fixed_case
    messages = request_messages(case, system, sent)
    driver = OfflineBoundary(
        messages,
        (runtime_citation,),
        sent=tuple(FIXED_TO_RUNTIME[item] for item in sent),
    )
    outcome = run(collect_attempt, fixed_case, driver)
    assert driver.events == ["driver", "capture", "model"]
    row = outcome["record"]
    expected = [{"role": role, "content": content} for role, content in messages]
    assert row["request"] == expected
    assert row["sent_ids"] == list(sent)
    assert row["cited_ids"] == [fixed_citation]
    assert row["input_sha256"] == digest(case["input"])
    assert row["prompt_sha256"] == digest(expected)
    assert row["response"] == driver.response
    assert row["response_sha256"] == digest(driver.response)
    assert outcome["accounting_present"] is True
    assert outcome["answer_model_attempts"] == 1


def test_empty_approved_set_has_no_report_or_model_call(collect_attempt, fixed_case):
    driver = OfflineBoundary(None)
    outcome = run(collect_attempt, fixed_case, driver)
    assert driver.events == ["driver"]
    assert outcome["record"] is None
    assert outcome["accounting_present"] is False
    assert outcome["answer_model_attempts"] is None


@pytest.mark.parametrize(
    "fault",
    [
        "system",
        "malformed-user",
        "unknown-fixed-id",
        "evidence-text",
        "extra-field",
    ],
)
def test_rejected_capture_prevents_model_call(collect_attempt, fixed_case, fault):
    _, case, system = fixed_case
    system_entry, user_entry = request_messages(case, system, ("ev-b",))
    if fault == "system":
        system_entry = ("system", system + "\n")
    if fault == "malformed-user":
        user_entry = ("user", "unexpected question template")
    if fault == "extra-field":
        payload = json.loads(user_entry[1])
        payload["unapproved_note"] = "extra"
        user_entry = ("user", json.dumps(payload))
    if fault == "evidence-text":
        payload = json.loads(user_entry[1])
        payload["approved_evidence"][0]["text"] = (
            payload["approved_evidence"][0]["text"] + " amended"
        )
        user_entry = ("user", json.dumps(payload))
    if fault == "unknown-fixed-id":
        payload = json.loads(user_entry[1])
        payload["approved_evidence"][0]["id"] = "ev-pending"
        user_entry = ("user", json.dumps(payload))
    driver = OfflineBoundary((system_entry, user_entry))
    outcome = run(collect_attempt, fixed_case, driver)
    assert driver.events == ["driver", "capture"]
    assert outcome["record"] is None
    # P1: observer rejection keeps D's validated accounting with zero attempts.
    assert outcome["accounting_present"] is True
    assert outcome["answer_model_attempts"] == 0


def test_post_call_stale_review_keeps_result_but_never_yields_a_report_row(
    collect_attempt, fixed_case
):
    """P1: a post-call review change keeps result while the draft fails."""
    _, case, system = fixed_case
    driver = OfflineBoundary(
        request_messages(case, system, ("ev-b",)), (RUNTIME_B,), mode="stale"
    )
    outcome = run(collect_attempt, fixed_case, driver)
    assert driver.events == ["driver", "capture", "model"]
    assert outcome["record"] is None
    assert outcome["accounting_present"] is True
    assert outcome["answer_model_attempts"] == 1


def test_capture_send_set_must_match_draft_send_set(collect_attempt, fixed_case):
    """P1: the row send set comes from the capture, not from the draft."""
    _, case, system = fixed_case
    driver = OfflineBoundary(
        request_messages(case, system, ("ev-b",)),
        (RUNTIME_A,),
        sent=(RUNTIME_A,),
    )
    outcome = run(collect_attempt, fixed_case, driver)
    assert driver.events == ["driver", "capture", "model"]
    assert outcome["record"] is None
    assert outcome["accounting_present"] is True
    assert outcome["answer_model_attempts"] == 1


def test_missing_accounting_never_yields_a_report_row(collect_attempt, fixed_case):
    """P2: no accounting means no row, and absence is not invented as zero."""
    _, case, system = fixed_case
    driver = OfflineBoundary(
        request_messages(case, system, ("ev-b",)),
        (RUNTIME_B,),
        sent=(RUNTIME_B,),
        mode="no-accounting",
    )
    outcome = run(collect_attempt, fixed_case, driver)
    assert driver.events == ["driver", "capture", "model"]
    assert outcome["record"] is None
    assert outcome["accounting_present"] is False
    assert outcome["answer_model_attempts"] is None


@pytest.mark.parametrize("fault", ["different-case", "different-dataset", "non-bijective"])

def test_invalid_binding_fails_before_driver(collect_attempt, fixed_case, fault):
    dataset_sha256, case, system = fixed_case
    wrong_bindings = {
        "different-case": {(dataset_sha256, "QUAL-01"): {"ev-a": RUNTIME_A, "ev-b": RUNTIME_B}},
        "different-dataset": {("0" * 64, CASE_ID): {"ev-a": RUNTIME_A, "ev-b": RUNTIME_B}},
        "non-bijective": {(dataset_sha256, CASE_ID): {"ev-a": RUNTIME_A, "ev-b": RUNTIME_A}},
    }
    driver = OfflineBoundary(request_messages(case, system, ("ev-a",)))
    with pytest.raises(ValueError):
        run(collect_attempt, fixed_case, driver, bindings=wrong_bindings[fault])
    assert driver.events == []


@pytest.mark.parametrize(
    ("citation", "mode"),
    [(RUNTIME_A, "out-of-scope-citation"), ("ev-" + "c" * 64, "unknown-citation")],
    ids=("cropped", "unknown"),
)
def test_out_of_scope_citation_cannot_produce_report_row(
    collect_attempt, fixed_case, citation, mode
):
    _, case, system = fixed_case
    driver = OfflineBoundary(
        request_messages(case, system, ("ev-b",)),
        (citation,),
        sent=(RUNTIME_B,),
        mode=mode,
    )
    outcome = run(collect_attempt, fixed_case, driver)
    assert driver.events == ["driver", "capture", "model"]
    assert outcome["record"] is None
    assert outcome["accounting_present"] is True
    assert outcome["answer_model_attempts"] == 1


@pytest.mark.parametrize("attempts", [0, None, 1], ids=("zero", "unknown", "one"))
def test_preserves_d_outcome_accounting_when_drops_result(
    collect_attempt, fixed_case, attempts,
):
    _, case, system = fixed_case
    driver = OfflineBoundary(request_messages(case, system, ("ev-b",)), attempts=attempts, rejected=True)
    outcome = run(collect_attempt, fixed_case, driver)
    assert outcome["record"] is None
    assert outcome["accounting_present"] is True
    assert outcome["answer_model_attempts"] == attempts


def test_repeat_never_reuses_prior_capture(collect_attempt, fixed_case):
    _, case, system = fixed_case
    first = OfflineBoundary(
        request_messages(case, system, ("ev-b",), indent=2),
        sent=(RUNTIME_B,),
        repeat=1,
    )
    second = OfflineBoundary(
        request_messages(case, system, ("ev-b",), indent=None),
        sent=(RUNTIME_B,),
        repeat=2,
    )
    empty = OfflineBoundary(None)
    first_row = run(collect_attempt, fixed_case, first, repeat=1)["record"]
    second_row = run(collect_attempt, fixed_case, second, repeat=2)["record"]
    third = run(collect_attempt, fixed_case, empty, repeat=3)
    assert (first_row["case_id"], first_row["repeat"]) == (CASE_ID, 1)
    assert (second_row["case_id"], second_row["repeat"]) == (CASE_ID, 2)
    assert first_row["request"][1]["content"] != second_row["request"][1]["content"]
    assert first_row["prompt_sha256"] != second_row["prompt_sha256"]
    assert first_row["response_sha256"] != second_row["response_sha256"]
    assert third["record"] is None
    assert empty.events == ["driver"]
