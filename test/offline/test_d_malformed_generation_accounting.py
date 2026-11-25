"""D preserves validated accounting when a gateway response is rejected."""

from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
from importlib import import_module
from types import SimpleNamespace

import pytest

from papertrace.contracts import CorpusSnapshot, DocumentVersion, EvidenceRecord, SourceLocator


@pytest.fixture
def scenario():
    answer = import_module("papertrace.answer")
    generation = import_module("papertrace.answer.generation")
    adapter = import_module("papertrace.answer.b_gateway_adapter")
    gateway_api = import_module("papertrace.retrieval.gateway")
    now = datetime(2026, 11, 24, tzinfo=timezone.utc)
    text = "The synthetic source reports a single observation."
    doc = DocumentVersion(
        schema_version=1,
        document_id="doc-synthetic-diagnostics",
        version_sha256=sha256(text.encode()).hexdigest(),
        title="Synthetic diagnostic source",
        source_name="synthetic.txt",
        status="ready",
    )
    snapshot = CorpusSnapshot(schema_version=1, documents=(doc,), created_at=now)
    evidence = EvidenceRecord(
        schema_version=1,
        snapshot_id=snapshot.snapshot_id,
        document_id=doc.document_id,
        version_sha256=doc.version_sha256,
        locator=SourceLocator(
            schema_version=1,
            line_start=1,
            line_end=1,
            chunk_id="synthetic-diagnostics-line-1",
            parser_name="synthetic",
            parser_version="1",
        ),
        excerpt=text,
        retrieved_at=now,
    )
    question_id = "q-synthetic-diagnostics"
    digest = sha256(b"synthetic reviewed evidence").hexdigest()
    projection = SimpleNamespace(
        snapshot_id=snapshot.snapshot_id,
        question_id=question_id,
        revision=1,
        digest=digest,
        accepted_evidence_ids=(evidence.evidence_id,),
        events=(),
    )
    request = generation.AnswerGenerationRequest(
        base=answer.AnswerRequest(
            snapshot=snapshot,
            question_id=question_id,
            answer_id="ans-synthetic-diagnostics",
            requested_at=now,
            evidence=(evidence,),
        ),
        question_text="What does the source report?",
        selected_evidence_ids=(evidence.evidence_id,),
        policy=generation.GenerationPolicySpec(
            provider="requested-provider", model="requested-model"
        ),
    )

    def read_projection(requested_question_id):
        assert requested_question_id == question_id
        return projection

    def run(accounting):
        response = gateway_api.GenerationResult(
            status=gateway_api.GenerationStatus.SUCCESS,
            raw_output="Rejected synthetic output (b1).",
            sent_evidence_ids=(evidence.evidence_id, evidence.evidence_id),
            citation_aliases=(("b1", evidence.evidence_id),),
            accounting=accounting,
        )
        calls = []

        def generate(call_request):
            calls.append(call_request)
            return response

        service = generation.AnswerGenerationService(
            projections=SimpleNamespace(read_projection=read_projection),
            generation=adapter.BGatewayGenerationAdapter(
                gateway=SimpleNamespace(generate=generate)
            ),
        )
        outcome = service.run(request)
        assert len(calls) == 1
        assert calls[0].selected_evidence_ids == (evidence.evidence_id,)
        assert outcome.reason == "RESULT_SHAPE_INVALID"
        assert outcome.result is None
        assert outcome.draft is not None
        assert outcome.draft.status == "failed"
        assert outcome.draft.body == ""
        assert outcome.draft.sent_evidence_ids == ()
        assert outcome.draft.citation_evidence_ids == ()
        assert outcome.draft.approved_evidence_ids == (evidence.evidence_id,)
        assert outcome.draft.review_revision == 1
        assert outcome.draft.review_digest == digest
        return outcome

    def no_model(**kwargs):
        pytest.fail("Empty-evidence accounting fixture entered the model boundary")

    seed_result = gateway_api.Gateway(
        adapter=None,
        source_reader=None,
        model_factory=SimpleNamespace(create=no_model),
        clock=lambda: now,
    ).generate(
        gateway_api.GenerationRequest(
            snapshot=snapshot,
            question=request.question_text,
            approved_evidence=(),
            selected_evidence_ids=(),
            policy=gateway_api.GenerationPolicy(
                provider="reported-provider", model="reported-model"
            ),
        )
    )
    assert seed_result.status is gateway_api.GenerationStatus.REFUSED
    assert seed_result.accounting is not None
    assert seed_result.accounting.answer_model_attempts == 0
    return run, seed_result.accounting


@pytest.mark.parametrize("attempts", (1, 0, None), ids=("observed", "zero", "unknown"))
def test_rejected_gateway_result_retains_valid_accounting(scenario, attempts):
    run, accounting_template = scenario
    outcome = run(replace(accounting_template, answer_model_attempts=attempts))
    accounting = getattr(outcome, "accounting", None)
    assert accounting is not None, "Validated B accounting must survive outside the rejected result"
    assert (accounting.provider, accounting.model) == ("reported-provider", "reported-model")
    assert accounting.answer_model_attempts == attempts
    if attempts is not None:
        assert type(accounting.answer_model_attempts) is int


@pytest.mark.parametrize(
    "overrides",
    (None, {"answer_model_attempts": True}, {"provider": " "}),
    ids=("absent", "boolean-count", "blank-provider"),
)
def test_rejected_gateway_result_does_not_invent_accounting(scenario, overrides):
    run, accounting_template = scenario
    accounting = None if overrides is None else replace(accounting_template, **overrides)
    assert getattr(run(accounting), "accounting", None) is None
