"""Offline D accounting tests for the public B34 result boundary."""

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from hashlib import sha256
from importlib import import_module
from types import SimpleNamespace
from typing import Any

import pytest

from papertrace.contracts import CorpusSnapshot, DocumentVersion, EvidenceRecord, SourceLocator

NOW = datetime(2026, 11, 23, tzinfo=timezone.utc)
QUESTION_ID = "q-synthetic-accounting"
QUESTION = "What does the synthetic source say?"


def _module(name: str) -> Any:
    try:
        return import_module(name)
    except ModuleNotFoundError as error:
        if error.name is not None and (name == error.name or name.startswith(error.name + ".")):
            pytest.fail(f"Missing product prerequisite {error.name} for D accounting tests")
        raise


@dataclass(frozen=True)
class _Projection:
    snapshot_id: str
    question_id: str
    revision: int
    digest: str
    accepted_evidence_ids: tuple[str, ...]
    events: tuple[object, ...] = ()

    def read_projection(self, question_id: str) -> "_Projection":
        assert question_id == self.question_id
        return self


class _GatewaySpy:
    def __init__(self, response: object) -> None:
        self.response = response
        self.requests: list[object] = []

    def generate(self, request: object) -> object:
        self.requests.append(request)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class _NeverCreate:
    def create(self, **kwargs: object) -> None:
        pytest.fail("The empty-approved B fixture must never construct a model")


@pytest.fixture
def scenario():
    answer = _module("papertrace.answer")
    generation = _module("papertrace.answer.generation")
    adapter = _module("papertrace.answer.b_gateway_adapter")
    text = "The synthetic source contains a single observation."
    doc = DocumentVersion(
        schema_version=1,
        document_id="doc-synthetic-accounting",
        version_sha256=sha256(text.encode()).hexdigest(),
        title="Synthetic accounting source",
        source_name="synthetic-accounting.txt",
        status="ready",
    )
    snapshot = CorpusSnapshot(schema_version=1, documents=(doc,), created_at=NOW)
    evidence = EvidenceRecord(
        schema_version=1,
        snapshot_id=snapshot.snapshot_id,
        document_id=doc.document_id,
        version_sha256=doc.version_sha256,
        locator=SourceLocator(
            schema_version=1,
            line_start=1,
            line_end=1,
            chunk_id="synthetic-accounting-line-1",
            parser_name="synthetic",
            parser_version="1",
        ),
        excerpt=text,
        retrieved_at=NOW,
    )
    request = generation.AnswerGenerationRequest(
        base=answer.AnswerRequest(
            snapshot=snapshot,
            question_id=QUESTION_ID,
            answer_id="ans-synthetic-accounting",
            requested_at=NOW,
            evidence=(evidence,),
        ),
        question_text=QUESTION,
        selected_evidence_ids=(evidence.evidence_id,),
        policy=generation.GenerationPolicySpec(provider="request-provider", model="request-model"),
    )

    def run(gateway: _GatewaySpy, *, approved: bool = True):
        projection = _Projection(
            snapshot_id=snapshot.snapshot_id,
            question_id=QUESTION_ID,
            revision=1 if approved else 0,
            digest=sha256(b"approved" if approved else b"empty").hexdigest(),
            accepted_evidence_ids=(evidence.evidence_id,) if approved else (),
        )
        service = generation.AnswerGenerationService(
            projections=projection,
            generation=adapter.BGatewayGenerationAdapter(gateway=gateway),
        )
        return service.run(request)

    return SimpleNamespace(run=run, snapshot=snapshot, evidence_id=evidence.evidence_id)


@pytest.fixture
def b_result(scenario):
    b = _module("papertrace.retrieval.gateway")
    policy = b.GenerationPolicy(
        provider="reported-provider",
        model="reported-model",
        max_input_tokens=4096,
        compress_at_tokens=3072,
        max_output_tokens=512,
        max_sources=2,
        get_evidence_if_no_contexts=False,
        pre_prompt=None,
        post_prompt=None,
        autonomous_agent=False,
    )
    template = b.Gateway(
        adapter=None, source_reader=None, model_factory=_NeverCreate(), clock=lambda: NOW
    ).generate(
        b.GenerationRequest(
            snapshot=scenario.snapshot,
            question=QUESTION,
            approved_evidence=(),
            selected_evidence_ids=(),
            policy=policy,
        )
    )
    assert isinstance(template, b.GenerationResult)
    assert template.status is b.GenerationStatus.REFUSED
    assert hasattr(template, "accounting"), "Missing B34 prerequisite: public result accounting"
    assert template.accounting is not None
    assert template.accounting.answer_model_attempts == 0
    return template


def _success(scenario, b_result, *, unknown: bool = False):
    return replace(
        b_result,
        status=type(b_result.status).SUCCESS,
        raw_output="Synthetic answer (b1) (b999)." if unknown else "Synthetic answer (b1).",
        sent_evidence_ids=(scenario.evidence_id,),
        citation_aliases=(("b1", scenario.evidence_id),),
        unknown_citation_keys=("b999",) if unknown else (),
        refusal_reason=None,
    )


def _invalid_sent(b_result):
    return replace(
        b_result,
        status=type(b_result.status).INVALID_SENT_EVIDENCE,
        refusal_reason=None,
        invalid_sent_evidence_ids=("unselected-synthetic-id",),
    )


def _assert_one_call(gateway, scenario):
    assert len(gateway.requests) == 1
    request = gateway.requests[0]
    assert request.selected_evidence_ids == (scenario.evidence_id,)
    assert request.policy.provider == "request-provider"
    assert request.policy.model == "request-model"


def _assert_accounting(result, expected):
    assert result is not None
    assert hasattr(result, "accounting"), "D adapter must expose the B call's accounting"
    if expected is None:
        assert result.accounting is None
        return
    assert result.accounting is not None
    assert result.accounting.provider == expected.provider
    assert result.accounting.model == expected.model
    assert result.accounting.answer_model_attempts == expected.answer_model_attempts


@pytest.mark.parametrize("attempts", (1, 2, None), ids=("one", "two", "unknown"))
def test_d_preserves_accounting_from_one_gateway_call(scenario, b_result, attempts):
    accounting = replace(b_result.accounting, answer_model_attempts=attempts)
    response = replace(_success(scenario, b_result), accounting=accounting)
    gateway = _GatewaySpy(response)
    outcome = scenario.run(gateway)
    _assert_one_call(gateway, scenario)
    assert outcome.draft.status == "draft"
    assert outcome.draft.citation_evidence_ids == (scenario.evidence_id,)
    _assert_accounting(outcome.result, accounting)


def test_d_preserves_absence_of_post_call_accounting(scenario, b_result):
    response = replace(_success(scenario, b_result), accounting=None)
    gateway = _GatewaySpy(response)
    outcome = scenario.run(gateway)
    _assert_one_call(gateway, scenario)
    assert outcome.draft.status == "draft"
    assert outcome.result is not None
    _assert_accounting(outcome.result, None)


def test_d_preserves_explicit_zero_from_a_gateway_refusal(scenario, b_result):
    gateway = _GatewaySpy(b_result)
    outcome = scenario.run(gateway)
    _assert_one_call(gateway, scenario)
    assert outcome.draft.status == "failed"
    assert outcome.reason == "GENERATION_REFUSED"
    _assert_accounting(outcome.result, b_result.accounting)


@pytest.mark.parametrize("guard", ("unknown-citation", "invalid-sent"))
@pytest.mark.parametrize("check_accounting", (False, True), ids=("guard", "accounting"))
def test_d_keeps_failure_with_post_call_accounting(scenario, b_result, guard, check_accounting):
    if guard == "unknown-citation":
        response = _success(scenario, b_result, unknown=True)
        attempts = 2
    else:
        response = _invalid_sent(b_result)
        attempts = None
    accounting = replace(b_result.accounting, answer_model_attempts=attempts)
    gateway = _GatewaySpy(replace(response, accounting=accounting))
    outcome = scenario.run(gateway)
    _assert_one_call(gateway, scenario)
    assert outcome.draft.status == "failed"
    assert not outcome.draft.body
    assert outcome.draft.citation_evidence_ids == ()
    assert outcome.result is not None
    if guard == "unknown-citation":
        assert outcome.reason == "UNKNOWN_CITATIONS"
        assert outcome.raw_unknown_keys == ("b999",)
    else:
        assert outcome.reason == "GENERATION_REFUSED"
        assert outcome.result.status == "REFUSED"
        assert outcome.result.refusal_reason == "INVALID_SENT_EVIDENCE"
        assert outcome.result.sent_evidence_ids == ()
        assert outcome.result.citation_aliases == ()
        assert outcome.result.invalid_sent_evidence_ids == ("unselected-synthetic-id",)
    if check_accounting:
        _assert_accounting(outcome.result, accounting)


def test_d_pre_call_abstention_has_no_generation_record(scenario):
    gateway = _GatewaySpy(AssertionError("Gateway called without approved evidence"))
    outcome = scenario.run(gateway, approved=False)
    assert gateway.requests == []
    assert outcome.draft.status == "abstained"
    assert outcome.reason == "NO_APPROVED_EVIDENCE"
    assert outcome.sent_request is None
    assert outcome.result is None


def test_d_propagates_gateway_exception_and_cause_without_retry(scenario):
    cause = ValueError("synthetic original error")
    error = RuntimeError("synthetic gateway failure")
    error.__cause__ = cause
    gateway = _GatewaySpy(error)
    with pytest.raises(RuntimeError) as caught:
        scenario.run(gateway)
    _assert_one_call(gateway, scenario)
    assert caught.value is error
    assert caught.value.__cause__ is cause
