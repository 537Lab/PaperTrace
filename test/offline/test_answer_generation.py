"""Module D generation proposal: coordinator, port shape and B gateway adapter.

Traceability: FR-D-01, FR-D-02, FR-D-03, INV-01, INV-03, INV-04,
INV-07 (policy/bridge slice only), COST-01. Design record:
``docs/team/designs/module-D/20261123-d-generation-collaborator-plan.md``.

This is an offline, draft-only, opt-in test proposal. ``AnswerService.prepare``
and the approved slice-1 tests are not changed. The proposed coordinator and
adapter modules do not exist yet, so every test resolves them at execution time
and reports a narrow availability failure instead of aborting collection. No
skip/xfail, no stub implementation, no global production-module substitution.

All material is synthetic: the approved ``test/fixtures/answer`` text files,
contract-valid snapshots/evidence and in-file duck-typed test doubles. No
PaperTrace product model, provider, live/network test or real semantic
evaluation is invoked. ``COST-01`` here means zero product LLM calls in these
offline checks; it says nothing about the development assistant's own provider
requests.
"""

from __future__ import annotations

import ast
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
from importlib import import_module
from importlib.util import find_spec
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import ValidationError

from papertrace.contracts import (
    AnswerDraft,
    CorpusSnapshot,
    DocumentVersion,
    EvidenceRecord,
    SourceLocator,
)

QUESTION_ID = "q-synthetic-generation-1"
ANSWER_ID = "ans-synthetic-generation-1"
QUESTION_TEXT = "How much daylight energy does the synthetic resonance cell store?"
REQUESTED_AT = datetime(2026, 11, 23, 0, 0, tzinfo=timezone.utc)
PROVIDER = "synthetic-provider"
MODEL = "synthetic-model"
REVISION_A = 4
REVISION_B = 5
DIGEST_A = sha256(b"papertrace synthetic generation review projection A").hexdigest()
DIGEST_B = sha256(b"papertrace synthetic generation review projection B").hexdigest()
FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "answer"
CORPUS_A = FIXTURE_DIR / "synthetic-corpus-a.txt"
CORPUS_B = FIXTURE_DIR / "synthetic-corpus-b.txt"

_MISSING_SUFFIX = (
    "is absent in this checkout. This is an availability/prerequisite result "
    "for the proposed draft-only API, not a reached behavior result."
)


def _module_ancestors(name: str) -> set[str]:
    """Return dotted prefixes whose absence explains a missing module."""
    parts = name.split(".")
    return {".".join(parts[: index + 1]) for index in range(len(parts))}


def _import_proposed(name: str, label: str) -> Any:
    """Import a proposed module; only its own missing prefix becomes an assertion."""
    try:
        return import_module(name)
    except ModuleNotFoundError as error:
        if error.name not in _module_ancestors(name):
            raise
        raise AssertionError(f"availability RED: {label} {_MISSING_SUFFIX}") from None


def answer_module() -> Any:
    return _import_proposed("papertrace.answer", "module papertrace.answer")


def answer_symbol(name: str) -> Any:
    module = answer_module()
    symbol = getattr(module, name, None)
    if symbol is None:
        raise AssertionError(f"availability RED: papertrace.answer.{name} is absent.")
    return symbol


def generation_module() -> Any:
    return _import_proposed(
        "papertrace.answer.generation", "module papertrace.answer.generation"
    )


def generation_symbol(name: str) -> Any:
    module = generation_module()
    symbol = getattr(module, name, None)
    if symbol is None:
        raise AssertionError(
            f"availability RED: proposed papertrace.answer.generation.{name} is absent."
        )
    return symbol


def adapter_module() -> Any:
    return _import_proposed(
        "papertrace.answer.b_gateway_adapter",
        "module papertrace.answer.b_gateway_adapter",
    )


def adapter_symbol(name: str) -> Any:
    module = adapter_module()
    symbol = getattr(module, name, None)
    if symbol is None:
        raise AssertionError(
            f"availability RED: proposed papertrace.answer.b_gateway_adapter.{name} "
            "is absent."
        )
    return symbol


def retrieval_module() -> Any:
    return _import_proposed(
        "papertrace.retrieval.gateway", "module papertrace.retrieval.gateway"
    )


def retrieval_symbol(name: str) -> Any:
    module = retrieval_module()
    symbol = getattr(module, name, None)
    if symbol is None:
        raise AssertionError(f"availability RED: papertrace.retrieval.gateway.{name} is absent.")
    return symbol


def require_paperqa() -> Any:
    """L2b needs the real ``paperqa.types`` API, not just a discovered package.

    A missing package is a prerequisite assertion. A transitive import failure
    such as ``ModuleNotFoundError(name="lmi")`` is deliberately left uncaught:
    it is a runtime dependency/environment blocker, not a D behavior result or
    an availability success.
    """
    try:
        spec = find_spec("paperqa")
    except (ImportError, ValueError):
        spec = None
    if spec is None:
        raise AssertionError(
            "prerequisite RED: package paperqa is not installed in this interpreter; "
            "the L2b real-bridge slice cannot run."
        )
    module = import_module("paperqa.types")
    required = ("Doc", "Text", "Context", "PQASession")
    missing = [name for name in required if not hasattr(module, name)]
    if missing:
        raise AssertionError(
            "prerequisite RED: paperqa.types lacks the required API "
            f"{', '.join(missing)}; the L2b real-bridge slice cannot run."
        )
    return module


def top_level_imports(source: str) -> list[str]:
    """Return dotted targets imported directly at module scope."""
    names: list[str] = []
    for node in ast.parse(source).body:
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            names.append(node.module)
    return names


def forbidden_imports(source: str, roots: tuple[str, ...]) -> list[str]:
    return [
        name
        for name in top_level_imports(source)
        if any(name == root or name.startswith(f"{root}.") for root in roots)
    ]


def build_document(path: Path, document_id: str, title: str) -> DocumentVersion:
    return DocumentVersion(
        schema_version=1,
        document_id=document_id,
        version_sha256=sha256(path.read_bytes()).hexdigest(),
        title=title,
        source_name=path.name,
        status="ready",
    )


def build_corpus() -> tuple[CorpusSnapshot, DocumentVersion, DocumentVersion]:
    doc_a = build_document(CORPUS_A, "doc-synthetic-a", "Synthetic corpus A")
    doc_b = build_document(CORPUS_B, "doc-synthetic-b", "Synthetic corpus B")
    snapshot = CorpusSnapshot(
        schema_version=1, documents=(doc_a, doc_b), created_at=REQUESTED_AT
    )
    return snapshot, doc_a, doc_b


def excerpt(path: Path, line_number: int = 2) -> str:
    return path.read_text(encoding="utf-8").splitlines()[line_number - 1]


def build_evidence(
    snapshot: CorpusSnapshot,
    document: DocumentVersion,
    path: Path,
    *,
    line_number: int = 2,
) -> EvidenceRecord:
    return EvidenceRecord(
        schema_version=1,
        snapshot_id=snapshot.snapshot_id,
        document_id=document.document_id,
        version_sha256=document.version_sha256,
        locator=SourceLocator(
            schema_version=1,
            line_start=line_number,
            line_end=line_number,
            chunk_id=f"chunk-{document.document_id}-{line_number}",
            parser_name="papertrace-synthetic",
            parser_version="1",
        ),
        excerpt=excerpt(path, line_number),
        retrieved_at=REQUESTED_AT,
    )


@dataclass(frozen=True)
class Projection:
    """Duck-typed stand-in for C's read-only projection; never a ledger write."""

    snapshot_id: str
    question_id: str
    revision: int
    digest: str
    accepted_evidence_ids: tuple[str, ...] = ()
    events: tuple[object, ...] = ()


def build_projection(
    snapshot: CorpusSnapshot,
    *,
    revision: int = REVISION_A,
    accepted: tuple[str, ...] = (),
    events: tuple[object, ...] = (),
    digest: str = DIGEST_A,
    question_id: str = QUESTION_ID,
    snapshot_id: str | None = None,
) -> Projection:
    return Projection(
        snapshot_id=snapshot.snapshot_id if snapshot_id is None else snapshot_id,
        question_id=question_id,
        revision=revision,
        digest=digest,
        accepted_evidence_ids=tuple(accepted),
        events=tuple(events),
    )


class SequenceReader:
    """Read-only projection port double; later reads may raise or change tokens."""

    def __init__(self, *outcomes: object) -> None:
        self._outcomes = tuple(outcomes)
        self.reads: list[str] = []

    def read_projection(self, question_id: str) -> object:
        self.reads.append(question_id)
        index = min(len(self.reads), len(self._outcomes)) - 1
        outcome = self._outcomes[index]
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


class StaticReader:
    """Stable read-only projection double for controls that do not test freshness."""

    def __init__(self, projection: object) -> None:
        self._projection = projection
        self.reads: list[str] = []

    def read_projection(self, question_id: str) -> object:
        self.reads.append(question_id)
        return self._projection


class TokenTrapProjection:
    """Synthetic projection whose revision/digest change after the first read."""

    def __init__(
        self,
        *,
        snapshot_id: str,
        question_id: str,
        revision_values: tuple[int, ...],
        digest_values: tuple[str, ...],
        accepted_evidence_ids: tuple[str, ...] = (),
        events: tuple[object, ...] = (),
    ) -> None:
        self.snapshot_id = snapshot_id
        self.question_id = question_id
        self.revision_values = revision_values
        self.digest_values = digest_values
        self.accepted_evidence_ids = accepted_evidence_ids
        self.events = events
        self.revision_reads = 0
        self.digest_reads = 0

    @property
    def revision(self) -> object:
        self.revision_reads += 1
        index = min(self.revision_reads, len(self.revision_values)) - 1
        return self.revision_values[index]

    @property
    def digest(self) -> object:
        self.digest_reads += 1
        index = min(self.digest_reads, len(self.digest_values)) - 1
        return self.digest_values[index]


class RecordingPort:
    """Generation port double that records calls and returns or raises one outcome."""

    def __init__(self, *, result: object = None, error: BaseException | None = None) -> None:
        self.result = result
        self.error = error
        self.requests: list[Any] = []

    def call(self, request: Any) -> object:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return self.result


def build_policy(**overrides: Any) -> Any:
    policy_type = generation_symbol("GenerationPolicySpec")
    values: dict[str, Any] = {"provider": PROVIDER, "model": MODEL}
    values.update(overrides)
    return policy_type(**values)


def build_answer_request(
    snapshot: CorpusSnapshot, evidence: tuple[EvidenceRecord, ...]
) -> Any:
    request_type = answer_symbol("AnswerRequest")
    return request_type(
        snapshot=snapshot,
        question_id=QUESTION_ID,
        answer_id=ANSWER_ID,
        requested_at=REQUESTED_AT,
        evidence=evidence,
    )


def build_generation_request(
    *,
    snapshot: CorpusSnapshot,
    evidence: tuple[EvidenceRecord, ...],
    selected: tuple[str, ...],
    policy: Any = None,
    question_text: str = QUESTION_TEXT,
) -> Any:
    request_type = generation_symbol("AnswerGenerationRequest")
    return request_type(
        base=build_answer_request(snapshot, evidence),
        question_text=question_text,
        selected_evidence_ids=tuple(selected),
        policy=build_policy() if policy is None else policy,
    )


def build_call_request(
    *,
    snapshot: CorpusSnapshot,
    approved: tuple[EvidenceRecord, ...],
    selected: tuple[str, ...],
    policy: Any = None,
) -> Any:
    request_type = generation_symbol("GenerationCallRequest")
    return request_type(
        snapshot=snapshot,
        question_text=QUESTION_TEXT,
        approved_evidence=approved,
        selected_evidence_ids=tuple(selected),
        review_revision=REVISION_A,
        review_digest=DIGEST_A,
        policy=build_policy() if policy is None else policy,
    )


def build_result(
    *,
    status: str = "SUCCESS",
    raw_output: str = "(b1)",
    sent: tuple[str, ...] = (),
    aliases: tuple[tuple[str, str], ...] = (),
    unknown: tuple[str, ...] = (),
    ambiguous: tuple[str, ...] = (),
    refusal_reason: str | None = None,
    invalid_sent_evidence_ids: tuple[str, ...] = (),
) -> Any:
    result_type = generation_symbol("GenerationCallResult")
    return result_type(
        status=status,
        raw_output=raw_output,
        sent_evidence_ids=sent,
        citation_aliases=aliases,
        unknown_citation_keys=unknown,
        ambiguous_citation_keys=ambiguous,
        refusal_reason=refusal_reason,
        invalid_sent_evidence_ids=invalid_sent_evidence_ids,
    )


def run_controlled(
    *,
    snapshot: CorpusSnapshot,
    evidence: tuple[EvidenceRecord, ...],
    projection: object,
    selected: tuple[str, ...],
    result: object = None,
    error: BaseException | None = None,
    policy: Any = None,
) -> tuple[Any, RecordingPort, StaticReader]:
    service_type = generation_symbol("AnswerGenerationService")
    reader = StaticReader(projection)
    port = RecordingPort(result=result, error=error)
    service = service_type(projections=reader, generation=port)
    request = build_generation_request(
        snapshot=snapshot,
        evidence=evidence,
        selected=selected,
        policy=policy,
    )
    return service.run(request), port, reader


def assert_draft_scope(
    outcome: Any,
    snapshot: CorpusSnapshot,
    *,
    status: str,
    reason: str | None,
    approved: tuple[str, ...],
    sent: tuple[str, ...] = (),
    cited: tuple[str, ...] = (),
    body: str = "",
    revision: int = REVISION_A,
    digest: str = DIGEST_A,
) -> AnswerDraft:
    draft = outcome.draft
    assert isinstance(draft, AnswerDraft)
    assert draft.status == status
    assert draft.answer_id == ANSWER_ID
    assert draft.snapshot_id == snapshot.snapshot_id
    assert draft.question_id == QUESTION_ID
    assert draft.review_revision == revision
    assert draft.review_digest == digest
    assert draft.approved_evidence_ids == approved
    assert draft.sent_evidence_ids == sent
    assert draft.citation_evidence_ids == cited
    assert draft.body == body
    assert draft.refusal_reason == reason
    assert draft.generated_at == REQUESTED_AT
    assert AnswerDraft.model_validate_json(draft.model_dump_json()) == draft
    assert outcome.reason == reason
    return draft


def assert_failed_outcome(
    outcome: Any,
    snapshot: CorpusSnapshot,
    *,
    reason: str,
    approved: tuple[str, ...] = (),
    revision: int = REVISION_A,
    digest: str = DIGEST_A,
) -> AnswerDraft:
    return assert_draft_scope(
        outcome,
        snapshot,
        status="failed",
        reason=reason,
        approved=approved,
        revision=revision,
        digest=digest,
    )


# --------------------------------------------------------------------------- #
# GN-D-01: no approved evidence -> abstained, zero port calls, no body.
# --------------------------------------------------------------------------- #

NO_APPROVED_CASES: tuple[tuple[str, int, tuple[object, ...]], ...] = (
    ("no-review", 0, ()),
    ("all-pending", 5, (object(),)),
    ("all-excluded", 6, (object(),)),
)
NO_APPROVED_IDS = [case[0] for case in NO_APPROVED_CASES]


@pytest.mark.parametrize(("case_id", "revision", "events"), NO_APPROVED_CASES, ids=NO_APPROVED_IDS)
def test_gn_d01_no_approved_evidence_abstains_before_generation(
    case_id: str, revision: int, events: tuple[object, ...]
) -> None:
    """FR-D-01/INV-01: an empty approved projection never reaches the port."""
    snapshot, doc_a, _ = build_corpus()
    record = build_evidence(snapshot, doc_a, CORPUS_A)
    projection = build_projection(snapshot, revision=revision, events=events)

    outcome, port, reader = run_controlled(
        snapshot=snapshot,
        evidence=(record,),
        projection=projection,
        selected=(record.evidence_id,),
    )

    assert port.requests == []
    assert reader.reads == [QUESTION_ID]
    assert outcome.revision_before == revision
    assert outcome.revision_after is None
    assert outcome.digest_before == DIGEST_A
    assert outcome.digest_after is None
    assert outcome.sent_request is None
    assert outcome.result is None
    assert outcome.raw_unknown_keys == ()
    assert outcome.truncation == "unknown"
    draft = assert_draft_scope(
        outcome,
        snapshot,
        status="abstained",
        reason="NO_APPROVED_EVIDENCE",
        approved=(),
        revision=revision,
        digest=DIGEST_A,
    )
    assert draft.body == ""


# --------------------------------------------------------------------------- #
# GN-D-02: approved exists but the caller selected nothing.
# --------------------------------------------------------------------------- #


def test_gn_d02_empty_selection_abstains_without_a_generation_call() -> None:
    """FR-D-01/INV-01: an empty selection is a refusal, not a model prompt."""
    snapshot, doc_a, _ = build_corpus()
    record = build_evidence(snapshot, doc_a, CORPUS_A)
    projection = build_projection(snapshot, accepted=(record.evidence_id,))

    outcome, port, reader = run_controlled(
        snapshot=snapshot,
        evidence=(record,),
        projection=projection,
        selected=(),
    )

    assert port.requests == []
    assert reader.reads == [QUESTION_ID]
    assert outcome.revision_before == REVISION_A
    assert outcome.revision_after is None
    assert outcome.digest_before == DIGEST_A
    assert outcome.digest_after is None
    assert outcome.sent_request is None
    assert outcome.result is None
    draft = assert_draft_scope(
        outcome,
        snapshot,
        status="abstained",
        reason="EMPTY_SELECTION",
        approved=(record.evidence_id,),
    )
    assert draft.body == ""


# --------------------------------------------------------------------------- #
# GN-D-03: selection outside approved is rejected before generation.
# --------------------------------------------------------------------------- #

OUTSIDE_CASES = ("unaccepted-supplied", "foreign-unsupplied")
OUTSIDE_IDS = list(OUTSIDE_CASES)


@pytest.mark.parametrize("case_id", OUTSIDE_CASES, ids=OUTSIDE_IDS)
def test_gn_d03_selection_outside_approved_fails_with_zero_calls(case_id: str) -> None:
    """INV-03: D never intersects a caller selection with the approved set."""
    snapshot, doc_a, doc_b = build_corpus()
    approved_record = build_evidence(snapshot, doc_a, CORPUS_A)
    other_record = build_evidence(snapshot, doc_b, CORPUS_B)
    projection = build_projection(snapshot, accepted=(approved_record.evidence_id,))
    if case_id == "unaccepted-supplied":
        selected = (other_record.evidence_id,)
        evidence = (approved_record, other_record)
    else:
        selected = ("ev-" + "f" * 64,)
        evidence = (approved_record,)

    outcome, port, reader = run_controlled(
        snapshot=snapshot,
        evidence=evidence,
        projection=projection,
        selected=selected,
    )

    assert port.requests == []
    assert reader.reads == [QUESTION_ID]
    assert outcome.revision_before == REVISION_A
    assert outcome.revision_after is None
    assert outcome.digest_before == DIGEST_A
    assert outcome.digest_after is None
    assert outcome.sent_request is None
    assert outcome.result is None
    assert_failed_outcome(
        outcome,
        snapshot,
        reason="SELECTION_OUTSIDE_APPROVED",
        approved=(approved_record.evidence_id,),
    )


# --------------------------------------------------------------------------- #
# GN-D-04: typed policy/request validation happens before any service run.
# --------------------------------------------------------------------------- #

POLICY_INVALID_CASES: tuple[tuple[str, dict[str, Any]], ...] = (
    ("input-zero", {"max_input_tokens": 0}),
    ("input-over-cap", {"max_input_tokens": 12001}),
    ("input-bool", {"max_input_tokens": True}),
    ("output-zero", {"max_output_tokens": 0}),
    ("output-over-cap", {"max_output_tokens": 2001}),
    ("compress-zero", {"compress_at_tokens": 0}),
    ("compress-over-global", {"compress_at_tokens": 9001}),
    ("compress-over-input", {"max_input_tokens": 5000, "compress_at_tokens": 6000}),
    ("sources-zero", {"max_sources": 0}),
    ("sources-bool", {"max_sources": True}),
    ("auto-evidence-true", {"get_evidence_if_no_contexts": True}),
    ("auto-evidence-one", {"get_evidence_if_no_contexts": 1}),
    ("auto-evidence-zero", {"get_evidence_if_no_contexts": 0}),
    ("auto-evidence-string", {"get_evidence_if_no_contexts": "false"}),
    ("pre-prompt", {"pre_prompt": "synthetic pre"}),
    ("post-prompt", {"post_prompt": "synthetic post"}),
    ("autonomous-true", {"autonomous_agent": True}),
    ("autonomous-zero", {"autonomous_agent": 0}),
    ("blank-provider", {"provider": "   "}),
    ("blank-model", {"model": ""}),
    ("non-string-provider", {"provider": b"synthetic-provider"}),
    ("non-string-model", {"model": 7}),
    ("extra-field", {"unexpected": 1}),
)
POLICY_INVALID_IDS = [case[0] for case in POLICY_INVALID_CASES]


@pytest.mark.parametrize(("case_id", "overrides"), POLICY_INVALID_CASES, ids=POLICY_INVALID_IDS)
def test_gn_d04_invalid_policy_raises_before_run(
    case_id: str, overrides: dict[str, Any]
) -> None:
    """INV-07 boundary: invalid typed policy is a ValidationError, not an outcome."""
    snapshot, doc_a, _ = build_corpus()
    record = build_evidence(snapshot, doc_a, CORPUS_A)
    projection = build_projection(snapshot, accepted=(record.evidence_id,))
    service_type = generation_symbol("AnswerGenerationService")
    port = RecordingPort(result=None)
    reader = StaticReader(projection)
    service_type(projections=reader, generation=port)

    with pytest.raises(ValidationError):
        build_policy(**overrides)

    assert port.requests == []
    assert reader.reads == []


POLICY_BOUNDARY_CASES: tuple[tuple[str, dict[str, Any]], ...] = (
    ("defaults", {}),
    ("lower-bounds", {"max_input_tokens": 1, "compress_at_tokens": 1, "max_output_tokens": 1, "max_sources": 1}),
    ("upper-bounds", {"max_input_tokens": 12000, "compress_at_tokens": 9000, "max_output_tokens": 2000, "max_sources": None}),
    ("compress-equals-input", {"max_input_tokens": 5000, "compress_at_tokens": 5000}),
    ("compress-below-global", {"max_input_tokens": 10000, "compress_at_tokens": 9000}),
)
POLICY_BOUNDARY_IDS = [case[0] for case in POLICY_BOUNDARY_CASES]


@pytest.mark.parametrize(("case_id", "overrides"), POLICY_BOUNDARY_CASES, ids=POLICY_BOUNDARY_IDS)
def test_gn_d04_valid_policy_boundaries_and_defaults(
    case_id: str, overrides: dict[str, Any]
) -> None:
    """INV-07 (policy slice): the strict fields accept only the declared range."""
    policy = build_policy(**overrides)

    assert policy.provider == PROVIDER
    assert policy.model == MODEL
    assert 1 <= policy.max_input_tokens <= 12000
    assert 1 <= policy.compress_at_tokens <= min(9000, policy.max_input_tokens)
    assert 1 <= policy.max_output_tokens <= 2000
    assert policy.max_sources is None or policy.max_sources >= 1
    assert policy.get_evidence_if_no_contexts is False
    assert policy.pre_prompt is None
    assert policy.post_prompt is None
    assert policy.autonomous_agent is False
    if case_id == "defaults":
        assert policy.max_input_tokens == 12000
        assert policy.compress_at_tokens == 9000
        assert policy.max_output_tokens == 2000
        assert policy.max_sources is None


REQUEST_INVALID_CASES: tuple[tuple[str, dict[str, Any]], ...] = (
    ("duplicate-selection", {"selected": ("duplicate", "duplicate")}),
    ("non-string-selection", {"selected": (123,)}),
    ("unknown-field", {"extra_field": True}),
    ("blank-question", {"question_text": "   "}),
)
REQUEST_INVALID_IDS = [case[0] for case in REQUEST_INVALID_CASES]


@pytest.mark.parametrize(("case_id", "overrides"), REQUEST_INVALID_CASES, ids=REQUEST_INVALID_IDS)
def test_gn_d04_invalid_generation_request_raises_before_run(
    case_id: str, overrides: dict[str, Any]
) -> None:
    """FR-D-01/INV-01: duplicate or malformed selections never reach the port."""
    snapshot, doc_a, _ = build_corpus()
    record = build_evidence(snapshot, doc_a, CORPUS_A)
    selected: tuple[Any, ...] = (record.evidence_id,)
    if case_id == "duplicate-selection":
        duplicate = "ev-" + "a" * 64
        selected = (duplicate, duplicate)
    elif case_id == "non-string-selection":
        selected = (123,)
    values: dict[str, Any] = {
        "base": build_answer_request(snapshot, (record,)),
        "question_text": QUESTION_TEXT,
        "selected_evidence_ids": selected,
        "policy": build_policy(),
    }
    if case_id == "unknown-field":
        values["extra_field"] = True
    if case_id == "blank-question":
        values["question_text"] = "   "
    request_type = generation_symbol("AnswerGenerationRequest")
    service_type = generation_symbol("AnswerGenerationService")
    port = RecordingPort(result=None)
    reader = StaticReader(build_projection(snapshot, accepted=(record.evidence_id,)))
    service_type(projections=reader, generation=port)

    with pytest.raises(ValidationError):
        request_type(**values)

    assert port.requests == []
    assert reader.reads == []


CALL_REQUEST_INVALID_CASES: tuple[tuple[str, dict[str, Any]], ...] = (
    ("question-id-is-not-part-of-the-b-request", {"question_id": QUESTION_ID}),
    ("bool-revision", {"review_revision": True}),
    ("negative-revision", {"review_revision": -1}),
    ("uppercase-digest", {"review_digest": DIGEST_A.upper()}),
    ("duplicate-selection", {"selected_evidence_ids": ("ev-" + "a" * 64,) * 2}),
    ("non-string-selection", {"selected_evidence_ids": (123,)}),
)
CALL_REQUEST_INVALID_IDS = [case[0] for case in CALL_REQUEST_INVALID_CASES]


@pytest.mark.parametrize(
    ("case_id", "overrides"), CALL_REQUEST_INVALID_CASES, ids=CALL_REQUEST_INVALID_IDS
)
def test_gn_d04_call_request_stays_b_neutral_and_strict(
    case_id: str, overrides: dict[str, Any]
) -> None:
    """FR-D-03: the B-neutral call request has no question_id and strict tokens."""
    snapshot, doc_a, _ = build_corpus()
    record = build_evidence(snapshot, doc_a, CORPUS_A)
    values: dict[str, Any] = {
        "snapshot": snapshot,
        "question_text": QUESTION_TEXT,
        "approved_evidence": (record,),
        "selected_evidence_ids": (record.evidence_id,),
        "review_revision": REVISION_A,
        "review_digest": DIGEST_A,
        "policy": build_policy(),
    }
    values.update(overrides)
    request_type = generation_symbol("GenerationCallRequest")

    with pytest.raises(ValidationError):
        request_type(**values)


def test_gn_d04_sent_call_request_has_no_question_id() -> None:
    """FR-D-03/question binding: question_id stays in D's outer diagnostic record."""
    snapshot, doc_a, _ = build_corpus()
    record = build_evidence(snapshot, doc_a, CORPUS_A)
    call_request = build_call_request(
        snapshot=snapshot, approved=(record,), selected=(record.evidence_id,)
    )

    assert "question_id" not in type(call_request).model_fields
    assert call_request.question_text == QUESTION_TEXT


# --------------------------------------------------------------------------- #
# GN-D-05: positive controls, exact sent set and the proposed parser grammar.
# --------------------------------------------------------------------------- #


def success_result(record: EvidenceRecord, *, raw: str = "The cell stores 12 units (b1).") -> Any:
    return build_result(
        status="SUCCESS",
        raw_output=raw,
        sent=(record.evidence_id,),
        aliases=(("b1", record.evidence_id),),
    )


def test_gn_d05a_single_approved_evidence_makes_one_controlled_call() -> None:
    """FR-D-01/02/03: exactly one call carries the approved selection and tokens."""
    snapshot, doc_a, _ = build_corpus()
    record = build_evidence(snapshot, doc_a, CORPUS_A)
    projection = build_projection(snapshot, accepted=(record.evidence_id,))
    policy = build_policy()
    result = success_result(record)

    outcome, port, reader = run_controlled(
        snapshot=snapshot,
        evidence=(record,),
        projection=projection,
        selected=(record.evidence_id,),
        result=result,
        policy=policy,
    )

    assert len(port.requests) == 1
    call = port.requests[0]
    assert call.snapshot == snapshot
    assert call.question_text == QUESTION_TEXT
    assert call.approved_evidence == (record,)
    assert call.selected_evidence_ids == (record.evidence_id,)
    assert call.review_revision == REVISION_A
    assert call.review_digest == DIGEST_A
    assert call.policy == policy
    assert "question_id" not in type(call).model_fields
    assert reader.reads == [QUESTION_ID, QUESTION_ID]
    assert outcome.question_id == QUESTION_ID
    assert outcome.question_text == QUESTION_TEXT
    assert outcome.sent_request is not None
    assert outcome.sent_request == call
    assert outcome.revision_before == REVISION_A
    assert outcome.revision_after == REVISION_A
    assert outcome.result == result
    assert outcome.raw_unknown_keys == ()
    assert outcome.truncation == "unknown"
    draft = assert_draft_scope(
        outcome,
        snapshot,
        status="draft",
        reason=None,
        approved=(record.evidence_id,),
        sent=(record.evidence_id,),
        cited=(record.evidence_id,),
        body=result.raw_output,
    )
    assert draft.body
    assert not hasattr(outcome, "release_decision")


def test_gn_d05b_multiple_approved_evidence_uses_a_proper_subset_selection() -> None:
    """FR-D-02/INV-04: selected is a nonempty proper subset of approved."""
    snapshot, doc_a, doc_b = build_corpus()
    record_a = build_evidence(snapshot, doc_a, CORPUS_A)
    record_b = build_evidence(snapshot, doc_b, CORPUS_B)
    approved = (record_a.evidence_id, record_b.evidence_id)
    selected = (record_a.evidence_id,)
    projection = build_projection(snapshot, accepted=approved)
    result = success_result(record_a, raw="Only the first source is used (b1).")

    outcome, port, reader = run_controlled(
        snapshot=snapshot,
        evidence=(record_a, record_b),
        projection=projection,
        selected=selected,
        result=result,
    )

    assert set(selected) < set(approved)
    assert selected
    assert len(port.requests) == 1
    call = port.requests[0]
    assert call.approved_evidence == (record_a, record_b)
    assert call.selected_evidence_ids == selected
    draft = assert_draft_scope(
        outcome,
        snapshot,
        status="draft",
        reason=None,
        approved=approved,
        sent=selected,
        cited=(record_a.evidence_id,),
        body=result.raw_output,
    )
    assert set(draft.sent_evidence_ids) <= set(selected)
    assert set(draft.citation_evidence_ids) <= set(draft.sent_evidence_ids)
    assert set(draft.sent_evidence_ids) <= set(draft.approved_evidence_ids)


def test_gn_d05c_two_alias_keys_for_one_evidence_are_preserved_and_deduplicated() -> None:
    """FR-D-02: distinct alias keys may target one sent evidence; cited IDs dedupe."""
    snapshot, doc_a, _ = build_corpus()
    record = build_evidence(snapshot, doc_a, CORPUS_A)
    projection = build_projection(snapshot, accepted=(record.evidence_id,))
    raw = "The same evidence is cited twice (b1) (b2)."
    result = build_result(
        status="SUCCESS",
        raw_output=raw,
        sent=(record.evidence_id,),
        aliases=(
            ("b1", record.evidence_id),
            ("b2", record.evidence_id),
        ),
    )

    outcome, port, _ = run_controlled(
        snapshot=snapshot,
        evidence=(record,),
        projection=projection,
        selected=(record.evidence_id,),
        result=result,
    )

    assert len(port.requests) == 1
    assert outcome.result == result
    assert outcome.result is not None
    assert outcome.result.citation_aliases == (
        ("b1", record.evidence_id),
        ("b2", record.evidence_id),
    )
    assert len(outcome.result.citation_aliases) == 2
    assert outcome.raw_unknown_keys == ()
    draft = assert_draft_scope(
        outcome,
        snapshot,
        status="draft",
        reason=None,
        approved=(record.evidence_id,),
        sent=(record.evidence_id,),
        cited=(record.evidence_id,),
        body=raw,
    )
    assert draft.citation_evidence_ids == (record.evidence_id,)
    assert len(draft.citation_evidence_ids) == 1


PARSER_CASES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("single", "The cell stores 12 units (b1).", ("b1",)),
    ("comma", "Marker (b1, b2).", ("b1", "b2")),
    ("space", "Marker (b1 b2).", ("b1", "b2")),
    ("semicolon", "Marker (b1;b2).", ("b1", "b2")),
    ("adjacent", "Markers (b1)(b2).", ("b1", "b2")),
    ("duplicate", "Again (b1) and (b1).", ("b1",)),
    ("prose", "The value (see Figure 2) is synthetic.", ("see", "Figure", "2")),
    ("empty", "Empty () marker.", ()),
    ("spaces-only", "Blank (   ) marker.", ()),
    ("unclosed", "Malformed (b1 marker.", ()),
    ("plain", "No markers in this sentence.", ()),
    ("nested", "Nested ((b1)).", ("b1",)),
)
PARSER_IDS = [case[0] for case in PARSER_CASES]


@pytest.mark.parametrize(("case_id", "text", "expected"), PARSER_CASES, ids=PARSER_IDS)
def test_gn_d05_parser_grammar_is_the_proposed_parenthesized_convention(
    case_id: str, text: str, expected: tuple[str, ...]
) -> None:
    """FR-D-02: one declared grammar; ordinary prose parentheses are not ignored."""
    parser = generation_symbol("extract_citation_keys")

    assert parser(text) == expected


def test_gn_d05_generation_module_keeps_bridge_imports_lazy() -> None:
    """FR-D-03: D's coordinator must not import B or paperqa at module scope."""
    module = generation_module()
    source = Path(module.__file__).read_text(encoding="utf-8")

    assert forbidden_imports(source, ("paperqa", "papertrace.retrieval")) == []


# --------------------------------------------------------------------------- #
# GN-D-06: malformed or inconsistent result sets fail; nothing is filtered.
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ResultIds:
    accepted: str
    other: str
    foreign: str


RESULT_CASES: tuple[tuple[str, Callable[[ResultIds], dict[str, Any]], str, tuple[str, ...]], ...] = (
    (
        "unknown-key",
        lambda ids: {
            "status": "SUCCESS",
            "raw_output": "(b999)",
            "sent": (ids.accepted,),
            "unknown": ("b999",),
        },
        "UNKNOWN_CITATIONS",
        ("b999",),
    ),
    (
        "ambiguous-key",
        lambda ids: {
            "status": "AMBIGUOUS_CITATIONS",
            "raw_output": "(b7)",
            "sent": (ids.accepted,),
            "ambiguous": ("b7",),
        },
        "AMBIGUOUS_CITATIONS",
        (),
    ),
    (
        "unknown-ambiguous-overlap",
        lambda ids: {
            "status": "AMBIGUOUS_CITATIONS",
            "raw_output": "(b7)",
            "sent": (ids.accepted,),
            "unknown": ("b7",),
            "ambiguous": ("b7",),
        },
        "RESULT_SHAPE_INVALID",
        (),
    ),
    (
        "ambiguous-not-extracted",
        lambda ids: {
            "status": "AMBIGUOUS_CITATIONS",
            "raw_output": "",
            "sent": (ids.accepted,),
            "ambiguous": ("b7",),
        },
        "RESULT_SHAPE_INVALID",
        (),
    ),
    (
        "unreconciled-key",
        lambda ids: {
            "status": "SUCCESS",
            "raw_output": "(b1)",
            "sent": (ids.accepted,),
        },
        "RESULT_SHAPE_INVALID",
        ("b1",),
    ),
    (
        "duplicate-alias-key",
        lambda ids: {
            "status": "SUCCESS",
            "raw_output": "(b1)",
            "sent": (ids.accepted,),
            "aliases": (("b1", ids.accepted), ("b1", ids.accepted)),
        },
        "RESULT_SHAPE_INVALID",
        (),
    ),
    (
        "blank-alias-key",
        lambda ids: {
            "status": "SUCCESS",
            "raw_output": "(b1)",
            "sent": (ids.accepted,),
            "aliases": (("", ids.accepted),),
        },
        "RESULT_SHAPE_INVALID",
        ("b1",),
    ),
    (
        "duplicate-sent",
        lambda ids: {
            "status": "SUCCESS",
            "raw_output": "",
            "sent": (ids.accepted, ids.accepted),
        },
        "RESULT_SHAPE_INVALID",
        (),
    ),
    (
        "approved-but-unselected-in-sent",
        lambda ids: {
            "status": "SUCCESS",
            "raw_output": "",
            "sent": (ids.other,),
        },
        "SENT_OUTSIDE_SELECTED",
        (),
    ),
    (
        "foreign-sent",
        lambda ids: {
            "status": "SUCCESS",
            "raw_output": "",
            "sent": (ids.foreign,),
        },
        "SENT_OUTSIDE_APPROVED",
        (),
    ),
    (
        "alias-target-outside-sent",
        lambda ids: {
            "status": "SUCCESS",
            "raw_output": "(b1)",
            "sent": (ids.accepted,),
            "aliases": (("b1", ids.other),),
        },
        "CITATION_OUTSIDE_SENT",
        (),
    ),
    (
        "refusal-reason-on-success",
        lambda ids: {
            "status": "SUCCESS",
            "raw_output": "(b1)",
            "sent": (ids.accepted,),
            "aliases": (("b1", ids.accepted),),
            "refusal_reason": "WHY",
        },
        "RESULT_SHAPE_INVALID",
        (),
    ),
    (
        "refused-without-reason",
        lambda ids: {"status": "REFUSED", "raw_output": ""},
        "RESULT_SHAPE_INVALID",
        (),
    ),
)
RESULT_CASE_IDS = [case[0] for case in RESULT_CASES]


@pytest.mark.parametrize(
    ("case_id", "build", "expected_reason", "expected_unknown"),
    RESULT_CASES,
    ids=RESULT_CASE_IDS,
)
def test_gn_d06_malformed_or_inconsistent_results_fail_without_filtering(
    case_id: str,
    build: Callable[[ResultIds], dict[str, Any]],
    expected_reason: str,
    expected_unknown: tuple[str, ...],
) -> None:
    """FR-D-02/INV-04: malformed reported sets are failures, never intersected."""
    snapshot, doc_a, doc_b = build_corpus()
    record_a = build_evidence(snapshot, doc_a, CORPUS_A)
    record_b = build_evidence(snapshot, doc_b, CORPUS_B)
    approved = (record_a.evidence_id, record_b.evidence_id)
    selected = (record_a.evidence_id,)
    projection = build_projection(snapshot, accepted=approved)
    ids = ResultIds(
        accepted=record_a.evidence_id,
        other=record_b.evidence_id,
        foreign="ev-" + "f" * 64,
    )
    values = build(ids)
    result = build_result(
        status=str(values.pop("status")),
        raw_output=str(values.pop("raw_output")),
        sent=tuple(values.pop("sent", ())),
        aliases=tuple(values.pop("aliases", ())),
        unknown=tuple(values.pop("unknown", ())),
        ambiguous=tuple(values.pop("ambiguous", ())),
        refusal_reason=values.pop("refusal_reason", None),
    )
    assert values == {}

    outcome, port, _ = run_controlled(
        snapshot=snapshot,
        evidence=(record_a, record_b),
        projection=projection,
        selected=selected,
        result=result,
    )

    assert len(port.requests) == 1
    draft = assert_failed_outcome(
        outcome,
        snapshot,
        reason=expected_reason,
        approved=approved,
    )
    assert draft.body == ""
    assert draft.sent_evidence_ids == ()
    assert draft.citation_evidence_ids == ()
    assert outcome.result == result
    assert outcome.raw_unknown_keys == expected_unknown
    if case_id == "ambiguous-key":
        assert outcome.result is not None
        assert outcome.result.ambiguous_citation_keys == ("b7",)
        assert outcome.raw_unknown_keys == ()
    if case_id == "unknown-ambiguous-overlap":
        assert outcome.result is not None
        assert outcome.result.unknown_citation_keys == ("b7",)
        assert outcome.result.ambiguous_citation_keys == ("b7",)
        assert outcome.raw_unknown_keys == ()


def test_gn_d06_non_result_object_is_shape_invalid() -> None:
    """FR-D-02: a broken collaborator cannot smuggle an object into a draft."""
    snapshot, doc_a, _ = build_corpus()
    record = build_evidence(snapshot, doc_a, CORPUS_A)
    projection = build_projection(snapshot, accepted=(record.evidence_id,))

    outcome, port, _ = run_controlled(
        snapshot=snapshot,
        evidence=(record,),
        projection=projection,
        selected=(record.evidence_id,),
        result=object(),
    )

    assert len(port.requests) == 1
    assert_failed_outcome(
        outcome,
        snapshot,
        reason="RESULT_SHAPE_INVALID",
        approved=(record.evidence_id,),
    )
    assert outcome.result is None


PRE_CALL_ERROR_CASES = (
    "wrong-snapshot",
    "wrong-question",
    "unknown-accepted",
    "foreign-evidence",
    "ledger-unavailable",
)


@pytest.mark.parametrize("case_id", PRE_CALL_ERROR_CASES)
def test_gn_d06_pre_call_assessment_errors_propagate_without_calls(case_id: str) -> None:
    """FR-D-02: scope/provenance/ledger errors are not converted into abstention."""
    snapshot, doc_a, doc_b = build_corpus()
    record = build_evidence(snapshot, doc_a, CORPUS_A)
    evidence: tuple[EvidenceRecord, ...] = (record,)
    selected: tuple[str, ...] = (record.evidence_id,)
    projection: object
    error_type: type[BaseException]
    reader: Any
    if case_id == "wrong-snapshot":
        other = CorpusSnapshot(schema_version=1, documents=(doc_b,), created_at=REQUESTED_AT)
        projection = build_projection(snapshot, snapshot_id=other.snapshot_id)
        error_type = answer_symbol("ProjectionScopeMismatchError")
        reader = StaticReader(projection)
    elif case_id == "wrong-question":
        projection = build_projection(snapshot, question_id="q-synthetic-2")
        error_type = answer_symbol("ProjectionScopeMismatchError")
        reader = StaticReader(projection)
    elif case_id == "unknown-accepted":
        projection = build_projection(snapshot, accepted=("ev-" + "f" * 64,))
        error_type = answer_symbol("UnknownAcceptedEvidenceError")
        reader = StaticReader(projection)
    elif case_id == "foreign-evidence":
        other = CorpusSnapshot(schema_version=1, documents=(doc_b,), created_at=REQUESTED_AT)
        foreign_record = build_evidence(other, doc_b, CORPUS_B)
        evidence = (foreign_record,)
        projection = build_projection(snapshot, accepted=(foreign_record.evidence_id,))
        error_type = answer_symbol("EvidenceProvenanceError")
        reader = StaticReader(projection)
    else:
        error_type = answer_symbol("ReviewStateUnavailableError")
        reader = SequenceReader(error_type("synthetic ledger unavailable"))
    service_type = generation_symbol("AnswerGenerationService")
    port = RecordingPort(result=None)
    service = service_type(projections=reader, generation=port)
    request = build_generation_request(
        snapshot=snapshot, evidence=evidence, selected=selected
    )

    with pytest.raises(error_type):
        service.run(request)

    assert port.requests == []
    assert reader.reads == [QUESTION_ID]


# --------------------------------------------------------------------------- #
# GN-D-07: B statuses and exceptions; no retry and no fallback.
# --------------------------------------------------------------------------- #

STATUS_CASES: tuple[tuple[str, dict[str, Any], str], ...] = (
    (
        "refused",
        {"status": "REFUSED", "raw_output": "", "refusal_reason": "EMPTY_SENT"},
        "GENERATION_REFUSED",
    ),
    (
        "empty-success",
        {"status": "SUCCESS", "raw_output": "", "sent": ("{accepted}",)},
        "EMPTY_OUTPUT",
    ),
    (
        "whitespace-success",
        {"status": "SUCCESS", "raw_output": "  \n\t", "sent": ("{accepted}",)},
        "EMPTY_OUTPUT",
    ),
    (
        "ambiguous",
        {
            "status": "AMBIGUOUS_CITATIONS",
            "raw_output": "(b7)",
            "sent": ("{accepted}",),
            "ambiguous": ("b7",),
        },
        "AMBIGUOUS_CITATIONS",
    ),
)
STATUS_IDS = [case[0] for case in STATUS_CASES]


@pytest.mark.parametrize(("case_id", "values", "expected_reason"), STATUS_CASES, ids=STATUS_IDS)
def test_gn_d07_non_success_results_fail_without_retry(
    case_id: str, values: dict[str, Any], expected_reason: str
) -> None:
    """FR-D-03/COST-01: one call, no retry, no provider/model fallback."""
    snapshot, doc_a, _ = build_corpus()
    record = build_evidence(snapshot, doc_a, CORPUS_A)
    projection = build_projection(snapshot, accepted=(record.evidence_id,))
    resolved = {
        key: tuple(item.format(accepted=record.evidence_id) for item in value)
        if isinstance(value, tuple)
        else value
        for key, value in values.items()
    }
    result = build_result(
        status=str(resolved["status"]),
        raw_output=str(resolved.get("raw_output", "")),
        sent=tuple(resolved.get("sent", ())),
        aliases=tuple(resolved.get("aliases", ())),
        unknown=tuple(resolved.get("unknown", ())),
        ambiguous=tuple(resolved.get("ambiguous", ())),
        refusal_reason=resolved.get("refusal_reason"),
    )

    outcome, port, _ = run_controlled(
        snapshot=snapshot,
        evidence=(record,),
        projection=projection,
        selected=(record.evidence_id,),
        result=result,
    )

    assert len(port.requests) == 1
    assert_failed_outcome(
        outcome,
        snapshot,
        reason=expected_reason,
        approved=(record.evidence_id,),
    )
    assert outcome.result == result
    assert outcome.truncation == "unknown"


def test_gn_d07_invalid_sent_evidence_maps_to_failed_generation_and_retains_diagnostic() -> None:
    """FR-D-02/FR-D-03: confirmed invalid-sent neutral result fails closed.

    D keeps the unauthorized reported ID on the internal result for diagnostics; the
    shared AnswerDraft stays empty and has no invalid-sent field.
    """
    snapshot, doc_a, doc_b = build_corpus()
    selected_record = build_evidence(snapshot, doc_a, CORPUS_A)
    unauthorized_record = build_evidence(snapshot, doc_b, CORPUS_B)
    projection = build_projection(snapshot, accepted=(selected_record.evidence_id,))
    result = build_result(
        status="REFUSED",
        raw_output="",
        sent=(),
        aliases=(),
        refusal_reason="INVALID_SENT_EVIDENCE",
        invalid_sent_evidence_ids=(unauthorized_record.evidence_id,),
    )

    outcome, port, _ = run_controlled(
        snapshot=snapshot,
        evidence=(selected_record, unauthorized_record),
        projection=projection,
        selected=(selected_record.evidence_id,),
        result=result,
    )

    assert len(port.requests) == 1
    assert outcome.result == result
    assert outcome.result is not None
    assert outcome.result.status == "REFUSED"
    assert outcome.result.refusal_reason == "INVALID_SENT_EVIDENCE"
    assert outcome.result.raw_output == ""
    assert outcome.result.sent_evidence_ids == ()
    assert outcome.result.citation_aliases == ()
    assert outcome.result.invalid_sent_evidence_ids == (unauthorized_record.evidence_id,)
    draft = assert_failed_outcome(
        outcome,
        snapshot,
        reason="GENERATION_REFUSED",
        approved=(selected_record.evidence_id,),
    )
    assert draft.body == ""
    assert draft.sent_evidence_ids == ()
    assert draft.citation_evidence_ids == ()
    assert not hasattr(draft, "invalid_sent_evidence_ids")
    assert not hasattr(outcome, "release_decision")


def test_gn_d07_port_exception_propagates_without_fallback() -> None:
    """FR-D-03: a provider-level exception is not converted into an abstention."""
    snapshot, doc_a, _ = build_corpus()
    record = build_evidence(snapshot, doc_a, CORPUS_A)
    projection = build_projection(snapshot, accepted=(record.evidence_id,))
    error = RuntimeError("synthetic upstream failure")
    service_type = generation_symbol("AnswerGenerationService")
    reader = StaticReader(projection)
    port = RecordingPort(error=error)
    service = service_type(projections=reader, generation=port)
    request = build_generation_request(
        snapshot=snapshot, evidence=(record,), selected=(record.evidence_id,)
    )

    with pytest.raises(RuntimeError, match="synthetic upstream failure"):
        service.run(request)

    assert len(port.requests) == 1
    assert reader.reads == [QUESTION_ID]


def test_gn_d07_adapter_shape_error_becomes_a_failed_outcome() -> None:
    """FR-D-02: only D's typed shape error is mapped; other errors still propagate."""
    snapshot, doc_a, _ = build_corpus()
    record = build_evidence(snapshot, doc_a, CORPUS_A)
    projection = build_projection(snapshot, accepted=(record.evidence_id,))
    error_type = generation_symbol("GenerationResultShapeError")

    outcome, port, _ = run_controlled(
        snapshot=snapshot,
        evidence=(record,),
        projection=projection,
        selected=(record.evidence_id,),
        error=error_type("synthetic malformed B result"),
    )

    assert len(port.requests) == 1
    assert_failed_outcome(
        outcome,
        snapshot,
        reason="RESULT_SHAPE_INVALID",
        approved=(record.evidence_id,),
    )
    assert outcome.result is None


# --------------------------------------------------------------------------- #
# GN-D-08: freshness around the one call and validated-token reuse.
# --------------------------------------------------------------------------- #


def test_gn_d08_post_call_review_change_fails_the_outcome() -> None:
    """FR-D-02/INV-04: a changed revision/digest discards the returned answer."""
    snapshot, doc_a, _ = build_corpus()
    record = build_evidence(snapshot, doc_a, CORPUS_A)
    before = build_projection(snapshot, revision=REVISION_A, accepted=(record.evidence_id,))
    after = build_projection(
        snapshot, revision=REVISION_B, digest=DIGEST_B, accepted=(record.evidence_id,)
    )
    result = success_result(record)
    service_type = generation_symbol("AnswerGenerationService")
    reader = SequenceReader(before, after)
    port = RecordingPort(result=result)
    service = service_type(projections=reader, generation=port)
    request = build_generation_request(
        snapshot=snapshot, evidence=(record,), selected=(record.evidence_id,)
    )

    outcome = service.run(request)

    assert len(port.requests) == 1
    assert reader.reads == [QUESTION_ID, QUESTION_ID]
    assert outcome.revision_before == REVISION_A
    assert outcome.revision_after == REVISION_B
    assert outcome.digest_before == DIGEST_A
    assert outcome.digest_after == DIGEST_B
    assert outcome.result == result
    assert outcome.sent_request is not None
    draft = assert_failed_outcome(
        outcome,
        snapshot,
        reason="STALE_REVIEW_DURING_GENERATION",
        approved=(record.evidence_id,),
        revision=REVISION_B,
        digest=DIGEST_B,
    )
    assert draft.body == ""
    assert result.raw_output not in draft.body


POST_CALL_ERROR_NAMES = (
    "ProjectionScopeMismatchError",
    "ReviewStateUnavailableError",
    "EvidenceProvenanceError",
)


@pytest.mark.parametrize("error_name", POST_CALL_ERROR_NAMES)
def test_gn_d08_post_call_assessment_errors_propagate_unchanged(error_name: str) -> None:
    """FR-D-02: scope/provenance/ledger errors are not converted to abstention."""
    snapshot, doc_a, _ = build_corpus()
    record = build_evidence(snapshot, doc_a, CORPUS_A)
    before = build_projection(snapshot, accepted=(record.evidence_id,))
    error_type = answer_symbol(error_name)
    service_type = generation_symbol("AnswerGenerationService")
    reader = SequenceReader(before, error_type("synthetic post-call assessment error"))
    port = RecordingPort(result=success_result(record))
    service = service_type(projections=reader, generation=port)
    request = build_generation_request(
        snapshot=snapshot, evidence=(record,), selected=(record.evidence_id,)
    )

    with pytest.raises(error_type, match="synthetic post-call assessment error"):
        service.run(request)

    assert len(port.requests) == 1
    assert reader.reads == [QUESTION_ID, QUESTION_ID]


def test_gn_d08_run_reuses_the_validated_first_read_tokens() -> None:
    """INV-04 regression: run() must not re-read revision/digest after validation."""
    snapshot, doc_a, _ = build_corpus()
    record = build_evidence(snapshot, doc_a, CORPUS_A)
    trap = TokenTrapProjection(
        snapshot_id=snapshot.snapshot_id,
        question_id=QUESTION_ID,
        revision_values=(REVISION_A, 99),
        digest_values=(DIGEST_A, DIGEST_B),
        accepted_evidence_ids=(record.evidence_id,),
    )
    post = build_projection(snapshot, revision=REVISION_A, accepted=(record.evidence_id,))
    result = success_result(record)
    service_type = generation_symbol("AnswerGenerationService")
    reader = SequenceReader(trap, post)
    port = RecordingPort(result=result)
    service = service_type(projections=reader, generation=port)
    request = build_generation_request(
        snapshot=snapshot, evidence=(record,), selected=(record.evidence_id,)
    )

    outcome = service.run(request)

    assert len(port.requests) == 1
    assert trap.revision_reads == 1
    assert trap.digest_reads == 1
    assert outcome.revision_before == REVISION_A
    assert outcome.digest_before == DIGEST_A
    assert outcome.revision_after == REVISION_A
    assert outcome.digest_after == DIGEST_A
    assert outcome.draft is not None
    assert outcome.draft.review_revision == REVISION_A
    assert outcome.draft.review_digest == DIGEST_A


# --------------------------------------------------------------------------- #
# GN-D-09: the approved legacy prepare() behavior is preserved.
# --------------------------------------------------------------------------- #

LEGACY_CASES = ("no-approved-evidence", "approved-not-generated")


@pytest.mark.parametrize("case_id", LEGACY_CASES)
def test_gn_d09_prepare_preserves_the_approved_no_generation_contract(case_id: str) -> None:
    """The legacy entry point's output/tokens and one projection read are preserved.

    This control observes only ``AnswerService.prepare``. It does not inject or
    observe a generation port, so it cannot prove a zero generation-call count.
    """
    snapshot, doc_a, _ = build_corpus()
    record = build_evidence(snapshot, doc_a, CORPUS_A)
    accepted = (record.evidence_id,) if case_id == "approved-not-generated" else ()
    projection = build_projection(snapshot, revision=REVISION_A, accepted=accepted)
    reader = StaticReader(projection)
    service_type = answer_symbol("AnswerService")
    service = service_type(projections=reader)

    draft = service.prepare(build_answer_request(snapshot, (record,)))

    assert reader.reads == [QUESTION_ID]
    assert isinstance(draft, AnswerDraft)
    assert draft.sent_evidence_ids == ()
    assert draft.citation_evidence_ids == ()
    assert draft.body == ""
    assert draft.review_revision == REVISION_A
    assert draft.review_digest == DIGEST_A
    if case_id == "approved-not-generated":
        assert draft.status == "failed"
        assert draft.approved_evidence_ids == accepted
        assert draft.refusal_reason == answer_module().REFUSAL_GENERATION_PATH_NOT_ENABLED
    else:
        assert draft.status == "abstained"
        assert draft.approved_evidence_ids == ()
        assert draft.refusal_reason == answer_module().REFUSAL_NO_APPROVED_EVIDENCE


# --------------------------------------------------------------------------- #
# GN-D-10 (L2a): real B Gateway plus fake factory/session, not the bridge.
# --------------------------------------------------------------------------- #


class _FakeClaim:
    def __init__(self, key: str, candidates: tuple[str, ...]) -> None:
        self.key = key
        self.candidates = candidates


class _FakeOutput:
    def __init__(self, *, raw: str, evidence_id: str) -> None:
        self.raw_output = raw
        self.citations = (_FakeClaim("b1", (evidence_id,)),)
        self.sent_evidence_ids = (evidence_id,)


class _FakeSession:
    def __init__(self, output: Any) -> None:
        self._output = output
        self.questions: list[str] = []

    def ask(self, question: str) -> Any:
        self.questions.append(question)
        return self._output


class _RecordingFactory:
    def __init__(self, output: Any) -> None:
        self._output = output
        self.policies: list[Any] = []
        self.contexts: list[tuple[Any, ...]] = []
        self.sessions: list[_FakeSession] = []

    def create(self, *, policy: Any = None, contexts: tuple[Any, ...] = ()) -> _FakeSession:
        self.policies.append(policy)
        self.contexts.append(tuple(contexts))
        session = _FakeSession(self._output)
        self.sessions.append(session)
        return session


class _RecordingGateway:
    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self.requests: list[Any] = []

    def generate(self, request: Any) -> Any:
        self.requests.append(request)
        return self._inner.generate(request)


class _UnusedRetrievalAdapter:
    def search(self, request: Any) -> Any:
        raise AssertionError("retrieval must not run during a generation test")


def _unused_source_reader(*, snapshot_id: str, document_id: str, version_sha256: str) -> bytes:
    raise AssertionError("source reading must not run during a generation test")


def test_gn_d10_l2a_real_gateway_converts_the_request_and_calls_the_factory_once() -> None:
    """FR-D-03: D's adapter converts field-by-field and B's public gateway runs."""
    snapshot, doc_a, _ = build_corpus()
    record = build_evidence(snapshot, doc_a, CORPUS_A)
    projection = build_projection(snapshot, accepted=(record.evidence_id,))
    policy = build_policy()
    output = _FakeOutput(raw="The cell stores 12 units (b1).", evidence_id=record.evidence_id)
    factory = _RecordingFactory(output)
    gateway_type = retrieval_symbol("Gateway")
    gateway = gateway_type(
        adapter=_UnusedRetrievalAdapter(),
        source_reader=_unused_source_reader,
        model_factory=factory,
        clock=lambda: REQUESTED_AT,
    )
    recording_gateway = _RecordingGateway(gateway)
    adapter = adapter_symbol("BGatewayGenerationAdapter")(gateway=recording_gateway)
    service_type = generation_symbol("AnswerGenerationService")
    service = service_type(projections=StaticReader(projection), generation=adapter)
    request = build_generation_request(
        snapshot=snapshot,
        evidence=(record,),
        selected=(record.evidence_id,),
        policy=policy,
    )

    outcome = service.run(request)

    assert len(recording_gateway.requests) == 1
    b_request = recording_gateway.requests[0]
    assert b_request.snapshot == snapshot
    assert b_request.question == QUESTION_TEXT
    assert b_request.approved_evidence == (record,)
    assert b_request.selected_evidence_ids == (record.evidence_id,)
    assert b_request.review_revision == REVISION_A
    assert b_request.review_digest == DIGEST_A
    assert b_request.policy.provider == policy.provider
    assert b_request.policy.model == policy.model
    assert b_request.policy.max_input_tokens == policy.max_input_tokens
    assert b_request.policy.compress_at_tokens == policy.compress_at_tokens
    assert b_request.policy.max_output_tokens == policy.max_output_tokens
    assert b_request.policy.max_sources == policy.max_sources
    assert b_request.policy.get_evidence_if_no_contexts is False
    assert b_request.policy.pre_prompt is None
    assert b_request.policy.post_prompt is None
    assert b_request.policy.autonomous_agent is False
    assert len(factory.sessions) == 1
    assert factory.sessions[0].questions == [QUESTION_TEXT]
    assert len(factory.contexts) == 1
    assert tuple(context.evidence_id for context in factory.contexts[0]) == (
        record.evidence_id,
    )
    assert outcome.sent_request is not None
    assert outcome.sent_request.question_text == QUESTION_TEXT
    assert "question_id" not in type(outcome.sent_request).model_fields
    assert outcome.question_id == QUESTION_ID
    assert outcome.result is not None
    assert type(outcome.result.status) is str
    assert outcome.result.status == "SUCCESS"
    assert outcome.result.citation_aliases == (("b1", record.evidence_id),)
    draft = assert_draft_scope(
        outcome,
        snapshot,
        status="draft",
        reason=None,
        approved=(record.evidence_id,),
        sent=(record.evidence_id,),
        cited=(record.evidence_id,),
        body=output.raw_output,
    )
    assert draft.body == output.raw_output


VALID_STATUS_CASES = ("success", "refused", "ambiguous")
VALID_STATUS_IDS = list(VALID_STATUS_CASES)


@pytest.mark.parametrize("case_id", VALID_STATUS_CASES, ids=VALID_STATUS_IDS)
def test_gn_d10_adapter_maps_only_known_b_enum_statuses(case_id: str) -> None:
    """FR-D-02: known B enum members map to D literals; no string comparison."""
    snapshot, doc_a, _ = build_corpus()
    record = build_evidence(snapshot, doc_a, CORPUS_A)
    gateway_module = retrieval_module()
    status_type = gateway_module.GenerationStatus
    result_type = gateway_module.GenerationResult
    if case_id == "success":
        status = status_type.SUCCESS
        result = result_type(
            status=status,
            raw_output="(b1)",
            sent_evidence_ids=(record.evidence_id,),
            citation_aliases=(("b1", record.evidence_id),),
        )
        expected = "SUCCESS"
    elif case_id == "refused":
        status = status_type.REFUSED
        result = result_type(status=status, refusal_reason="EMPTY_SENT")
        expected = "REFUSED"
    else:
        status = status_type.AMBIGUOUS_CITATIONS
        result = result_type(
            status=status,
            raw_output="(b1)",
            sent_evidence_ids=(record.evidence_id,),
            ambiguous_citation_keys=("b1",),
        )
        expected = "AMBIGUOUS_CITATIONS"
    stub = _StubGateway(result)
    adapter = adapter_symbol("BGatewayGenerationAdapter")(gateway=stub)
    call_request = build_call_request(
        snapshot=snapshot, approved=(record,), selected=(record.evidence_id,)
    )

    converted = adapter.call(call_request)

    assert len(stub.requests) == 1
    assert type(converted.status) is str
    assert converted.status == expected
    assert converted.raw_output == result.raw_output
    assert converted.sent_evidence_ids == result.sent_evidence_ids
    assert converted.citation_aliases == result.citation_aliases


def test_gn_d10_adapter_preserves_two_alias_keys_for_one_evidence() -> None:
    """FR-D-02: public-B conversion keeps two distinct keys mapping to one evidence."""
    snapshot, doc_a, _ = build_corpus()
    record = build_evidence(snapshot, doc_a, CORPUS_A)
    gateway_module = retrieval_module()
    result = gateway_module.GenerationResult(
        status=gateway_module.GenerationStatus.SUCCESS,
        raw_output="The same evidence is cited twice (b1) (b2).",
        sent_evidence_ids=(record.evidence_id,),
        citation_aliases=(
            ("b1", record.evidence_id),
            ("b2", record.evidence_id),
        ),
    )
    stub = _StubGateway(result)
    adapter = adapter_symbol("BGatewayGenerationAdapter")(gateway=stub)
    call_request = build_call_request(
        snapshot=snapshot, approved=(record,), selected=(record.evidence_id,)
    )

    converted = adapter.call(call_request)

    assert len(stub.requests) == 1
    assert converted.sent_evidence_ids == (record.evidence_id,)
    assert converted.citation_aliases == (
        ("b1", record.evidence_id),
        ("b2", record.evidence_id),
    )
    assert len(converted.citation_aliases) == 2


class _ForeignStatus(Enum):
    SUCCESS = "SUCCESS"


class _StubGateway:
    def __init__(self, result: object) -> None:
        self.result = result
        self.requests: list[Any] = []

    def generate(self, request: Any) -> object:
        self.requests.append(request)
        return self.result


def test_gn_d10_bridge_boundary_mixed_known_and_unknown_citations_fail_unknown_citations() -> None:
    """B SUCCESS with one resolved and one unknown citation key must fail closed at D.

    The raw mixed output and the unknown key stay as diagnostics. The failed draft has
    empty body/sent/citations and no release decision; no publication gate is claimed.
    """
    snapshot, doc_a, _ = build_corpus()
    record = build_evidence(snapshot, doc_a, CORPUS_A)
    projection = build_projection(snapshot, accepted=(record.evidence_id,))
    gateway_module = retrieval_module()
    raw = "The known claim cites (b1); the unmatched marker is (b999)."
    b_result = gateway_module.GenerationResult(
        status=gateway_module.GenerationStatus.SUCCESS,
        raw_output=raw,
        sent_evidence_ids=(record.evidence_id,),
        citation_aliases=(("b1", record.evidence_id),),
        unknown_citation_keys=("b999",),
    )
    stub = _StubGateway(b_result)
    adapter = adapter_symbol("BGatewayGenerationAdapter")(gateway=stub)
    service_type = generation_symbol("AnswerGenerationService")
    service = service_type(projections=StaticReader(projection), generation=adapter)
    request = build_generation_request(
        snapshot=snapshot,
        evidence=(record,),
        selected=(record.evidence_id,),
    )

    outcome = service.run(request)

    assert len(stub.requests) == 1
    assert outcome.result is not None
    assert outcome.result.status == "SUCCESS"
    assert outcome.result.raw_output == raw
    assert outcome.result.citation_aliases == (("b1", record.evidence_id),)
    assert outcome.result.unknown_citation_keys == ("b999",)
    assert outcome.raw_unknown_keys == ("b999",)
    draft = assert_failed_outcome(
        outcome,
        snapshot,
        reason="UNKNOWN_CITATIONS",
        approved=(record.evidence_id,),
    )
    assert draft.status == "failed"
    assert draft.body == ""
    assert draft.sent_evidence_ids == ()
    assert draft.citation_evidence_ids == ()
    assert not hasattr(outcome, "release_decision")


def test_gn_d10_b_gateway_invalid_sent_evidence_requires_confirmed_contract() -> None:
    """B contract prerequisite: local B16 must expose the confirmed invalid-sent fields.

    This is a B donor/contract checkpoint, not a D behavior result. Actual public B
    types are inspected; no B enum/status fake is introduced.
    """
    gateway_module = retrieval_module()
    status_type = gateway_module.GenerationStatus
    result_type = gateway_module.GenerationResult
    assert hasattr(status_type, "INVALID_SENT_EVIDENCE"), (
        "B contract prerequisite RED: local B donor lacks "
        "GenerationStatus.INVALID_SENT_EVIDENCE"
    )
    result_fields = getattr(result_type, "__dataclass_fields__", None)
    if result_fields is None:
        result_fields = getattr(result_type, "model_fields", {})
    assert "invalid_sent_evidence_ids" in result_fields, (
        "B contract prerequisite RED: local B donor lacks "
        "GenerationResult.invalid_sent_evidence_ids"
    )
    snapshot, doc_a, doc_b = build_corpus()
    selected_record = build_evidence(snapshot, doc_a, CORPUS_A)
    unauthorized_record = build_evidence(snapshot, doc_b, CORPUS_B)
    projection = build_projection(snapshot, accepted=(selected_record.evidence_id,))
    b_result = result_type(
        status=status_type.INVALID_SENT_EVIDENCE,
        raw_output="",
        sent_evidence_ids=(),
        citation_aliases=(),
        invalid_sent_evidence_ids=(unauthorized_record.evidence_id,),
    )
    stub = _StubGateway(b_result)
    adapter = adapter_symbol("BGatewayGenerationAdapter")(gateway=stub)
    service_type = generation_symbol("AnswerGenerationService")
    service = service_type(projections=StaticReader(projection), generation=adapter)
    request = build_generation_request(
        snapshot=snapshot,
        evidence=(selected_record, unauthorized_record),
        selected=(selected_record.evidence_id,),
    )

    outcome = service.run(request)

    assert len(stub.requests) == 1
    assert outcome.result is not None
    assert outcome.result.status == "REFUSED"
    assert outcome.result.refusal_reason == "INVALID_SENT_EVIDENCE"
    assert outcome.result.raw_output == ""
    assert outcome.result.sent_evidence_ids == ()
    assert outcome.result.citation_aliases == ()
    assert outcome.result.invalid_sent_evidence_ids == (unauthorized_record.evidence_id,)
    draft = assert_failed_outcome(
        outcome,
        snapshot,
        reason="GENERATION_REFUSED",
        approved=(selected_record.evidence_id,),
    )
    assert draft.body == ""
    assert draft.sent_evidence_ids == ()
    assert draft.citation_evidence_ids == ()
    assert not hasattr(draft, "invalid_sent_evidence_ids")
    assert not hasattr(outcome, "release_decision")


MALFORMED_RESULT_CASES: tuple[tuple[str, dict[str, Any]], ...] = (
    ("plain-string-status", {"status": "SUCCESS"}),
    ("foreign-enum-status", {"status": _ForeignStatus.SUCCESS}),
    ("bytes-raw", {"raw_output": b"(b1)"}),
    ("string-sent", {"sent_evidence_ids": "ev-not-a-sequence"}),
    ("bytes-sent-item", {"sent_evidence_ids": (b"ev-bytes",)}),
    ("duplicate-sent", {"sent_evidence_ids": ("ev-a", "ev-a")}),
    ("alias-entry-not-pair", {"citation_aliases": (("b1",),)}),
    ("bytes-alias-target", {"citation_aliases": (("b1", b"ev-bytes"),)}),
    (
        "duplicate-alias-key",
        {"citation_aliases": (("b1", "ev-a"), ("b1", "ev-b"))},
    ),
    ("bytes-unknown-key", {"unknown_citation_keys": (b"b9",)}),
    ("int-ambiguous-key", {"ambiguous_citation_keys": (7,)}),
    ("nonstr-refusal-reason", {"refusal_reason": 7}),
)
MALFORMED_RESULT_IDS = [case[0] for case in MALFORMED_RESULT_CASES]


@pytest.mark.parametrize(
    ("case_id", "overrides"), MALFORMED_RESULT_CASES, ids=MALFORMED_RESULT_IDS
)
def test_gn_d10_adapter_rejects_malformed_external_results(
    case_id: str, overrides: dict[str, Any]
) -> None:
    """FR-D-02: external status/tuple/string validation is explicit, not coercion."""
    snapshot, doc_a, _ = build_corpus()
    record = build_evidence(snapshot, doc_a, CORPUS_A)
    gateway_module = retrieval_module()
    status_type = gateway_module.GenerationStatus
    result_type = gateway_module.GenerationResult
    values: dict[str, Any] = {"status": status_type.SUCCESS}
    values.update(overrides)
    result = result_type(**values)
    stub = _StubGateway(result)
    adapter = adapter_symbol("BGatewayGenerationAdapter")(gateway=stub)
    call_request = build_call_request(
        snapshot=snapshot, approved=(record,), selected=(record.evidence_id,)
    )

    with pytest.raises(generation_symbol("GenerationResultShapeError")):
        adapter.call(call_request)

    assert len(stub.requests) == 1


def test_gn_d10_adapter_keeps_bridge_imports_lazy() -> None:
    """FR-D-03: the adapter must import B (and paperqa) inside call, not at import."""
    module = adapter_module()
    source = Path(module.__file__).read_text(encoding="utf-8")

    assert forbidden_imports(source, ("paperqa", "papertrace.retrieval")) == []


# --------------------------------------------------------------------------- #
# GN-D-11 (L2b): the real approved bridge with fake Docs/models/count_tokens.
# --------------------------------------------------------------------------- #


@dataclass
class _BridgeRecorder:
    counted: list[str] = field(default_factory=list)
    serialized: list[dict[str, Any]] = field(default_factory=list)
    queries: list[dict[str, Any]] = field(default_factory=list)
    created_docs: list[Any] = field(default_factory=list)


class _FakeSettings:
    """Minimal settings shape accepted by the approved B bridge; no real model."""

    def __init__(self, recorder: _BridgeRecorder) -> None:
        self._recorder = recorder
        self.answer = SimpleNamespace(
            get_evidence_if_no_contexts=True,
            answer_max_sources=99,
            evidence_relevance_score_cutoff=0.0,
            answer_length="short",
        )
        self.prompts = SimpleNamespace(
            pre="legacy pre", post="legacy post", system="SYSTEM", qa=None
        )
        self.serialized_context_ids: tuple[str, ...] = ()
        self.context_serializer = self._serialize

    async def _serialize(
        self, *, contexts: tuple[Any, ...], question: str, pre_str: str | None
    ) -> str:
        aliases = tuple(f"b{index}" for index in range(1, len(contexts) + 1))
        self.serialized_context_ids = aliases
        self._recorder.serialized.append(
            {
                "aliases": aliases,
                "texts": tuple(context.context for context in contexts),
                "question": question,
            }
        )
        return "\n".join(
            f"({alias}) {context.context}"
            for alias, context in zip(aliases, contexts, strict=True)
        )

    def model_copy(self, *, deep: bool = False) -> "_FakeSettings":
        return _FakeSettings(self._recorder)


class _FakeModel:
    def __init__(
        self, *, provider: str, model: str, token_count: int, recorder: _BridgeRecorder
    ) -> None:
        self.provider = provider
        self.model = model
        self.max_tokens: int | None = None
        self._token_count = token_count
        self._recorder = recorder

    def count_tokens(self, text: str) -> int:
        self._recorder.counted.append(text)
        return self._token_count

    def model_copy(self, *, deep: bool = False) -> "_FakeModel":
        copy = _FakeModel(
            provider=self.provider,
            model=self.model,
            token_count=self._token_count,
            recorder=self._recorder,
        )
        copy.max_tokens = self.max_tokens
        return copy


class _FakeDocs:
    def __init__(self, *, name: str, raw_answer: str, recorder: _BridgeRecorder) -> None:
        self.name = name
        self._raw_answer = raw_answer
        self._recorder = recorder

    async def aadd(self, *args: Any, **kwargs: Any) -> None:
        raise AssertionError("generation must not add documents")

    async def aget_evidence(self, *args: Any, **kwargs: Any) -> Any:
        raise AssertionError("generation must not retrieve evidence")

    async def aquery(self, session: Any, **kwargs: Any) -> Any:
        self._recorder.queries.append(
            {
                "docs_name": self.name,
                "session": session,
                "ids": tuple(context.id for context in session.contexts),
                "texts": tuple(context.context for context in session.contexts),
                "question": session.question,
            }
        )
        return SimpleNamespace(raw_answer=self._raw_answer)


class _FakeDocsFactory:
    def __init__(self, *, raw_answer: str, recorder: _BridgeRecorder) -> None:
        self._raw_answer = raw_answer
        self._recorder = recorder
        self.created: list[_FakeDocs] = []

    def __call__(self, *, name: str) -> _FakeDocs:
        docs = _FakeDocs(name=name, raw_answer=self._raw_answer, recorder=self._recorder)
        self.created.append(docs)
        self._recorder.created_docs.append(docs)
        return docs


class _RecordingModelFactory:
    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self.policies: list[Any] = []
        self.sessions: list[Any] = []

    def create(self, *, policy: Any = None, contexts: tuple[Any, ...] = ()) -> Any:
        self.policies.append(policy)
        session = self._inner.create(policy=policy, contexts=contexts)
        self.sessions.append(session)
        return session


def build_l2b_service(
    *,
    snapshot: CorpusSnapshot,
    projection: object,
    raw_answer: str,
    token_count: int,
    tmp_path: Path,
) -> tuple[Any, _BridgeRecorder, _FakeDocsFactory, _RecordingModelFactory]:
    require_paperqa()
    gateway_module = retrieval_module()
    recorder = _BridgeRecorder()
    docs_factory = _FakeDocsFactory(raw_answer=raw_answer, recorder=recorder)
    model = _FakeModel(
        provider=PROVIDER, model=MODEL, token_count=token_count, recorder=recorder
    )
    settings = _FakeSettings(recorder)
    bridge = gateway_module.PaperQA2Adapter(
        source_reader=_unused_source_reader,
        settings=settings,
        answer_llm_model=model,
        summary_llm_model=model,
        embedding_model=object(),
        docs_factory=docs_factory,
        temporary_directory=tmp_path,
    )
    factory_proxy = _RecordingModelFactory(bridge)
    gateway = gateway_module.Gateway(
        adapter=bridge,
        source_reader=_unused_source_reader,
        model_factory=factory_proxy,
        clock=lambda: REQUESTED_AT,
    )
    adapter = adapter_symbol("BGatewayGenerationAdapter")(gateway=gateway)
    service_type = generation_symbol("AnswerGenerationService")
    service = service_type(
        projections=StaticReader(projection),
        generation=adapter,
    )
    return service, recorder, docs_factory, factory_proxy


L2B_CAP_CASES = ((12000, True), (12001, False))
L2B_CAP_IDS = ["at-cap", "over-cap"]


@pytest.mark.parametrize(("token_count", "allowed"), L2B_CAP_CASES, ids=L2B_CAP_IDS)
def test_gn_d11_l2b_cap_is_checked_on_the_final_prompt(
    token_count: int, allowed: bool, tmp_path: Path
) -> None:
    """INV-07 (bridge slice): over-cap stops before aquery; at-cap reaches it."""
    snapshot, doc_a, doc_b = build_corpus()
    record = build_evidence(snapshot, doc_a, CORPUS_A)
    pending = build_evidence(snapshot, doc_b, CORPUS_B)
    excluded = build_evidence(snapshot, doc_a, CORPUS_A, line_number=1)
    projection = build_projection(snapshot, accepted=(record.evidence_id,))
    raw_answer = "The cell stores 12 units (b1)."
    fixture = build_l2b_service(
        snapshot=snapshot,
        projection=projection,
        raw_answer=raw_answer,
        token_count=token_count,
        tmp_path=tmp_path,
    )
    service, recorder, docs_factory, factory_proxy = fixture
    request = build_generation_request(
        snapshot=snapshot,
        evidence=(record, pending, excluded),
        selected=(record.evidence_id,),
    )

    outcome = service.run(request)

    assert len(recorder.counted) == 1
    prompt = recorder.counted[0]
    assert record.excerpt in prompt
    assert pending.excerpt not in prompt
    assert excluded.excerpt not in prompt
    assert len(recorder.serialized) == 1
    assert record.excerpt in "\n".join(recorder.serialized[0]["texts"])
    assert pending.excerpt not in "\n".join(recorder.serialized[0]["texts"])
    assert excluded.excerpt not in "\n".join(recorder.serialized[0]["texts"])
    assert len(factory_proxy.policies) == 1
    if allowed:
        assert token_count == 12000
        assert len(recorder.queries) == 1
        assert recorder.queries[0]["question"] == QUESTION_TEXT
        assert recorder.queries[0]["texts"] == (record.excerpt,)
        assert outcome.draft is not None
        assert outcome.draft.status == "draft"
        assert outcome.draft.sent_evidence_ids == (record.evidence_id,)
        assert outcome.draft.citation_evidence_ids == (record.evidence_id,)
        assert outcome.draft.body == raw_answer
        assert outcome.reason is None
        assert len(docs_factory.created) == 1
    else:
        assert token_count > 12000
        assert recorder.queries == []
        assert len(docs_factory.created) == 1
        assert outcome.result is not None
        assert outcome.result.status == "REFUSED"
        assert outcome.result.refusal_reason == "INPUT_BUDGET_EXCEEDED"
        assert outcome.draft is not None
        assert outcome.draft.status == "failed"
        assert outcome.draft.body == ""
        assert outcome.draft.sent_evidence_ids == ()
        assert outcome.reason == "GENERATION_REFUSED"


def test_gn_d11_l2b_repeated_runs_use_fresh_sessions_and_fresh_docs(tmp_path: Path) -> None:
    """FR-D-03: every run asks B for a new session; no Docs/session is reused."""
    snapshot, doc_a, doc_b = build_corpus()
    record = build_evidence(snapshot, doc_a, CORPUS_A)
    pending = build_evidence(snapshot, doc_b, CORPUS_B)
    projection = build_projection(snapshot, accepted=(record.evidence_id,))
    fixture = build_l2b_service(
        snapshot=snapshot,
        projection=projection,
        raw_answer="The cell stores 12 units (b1).",
        token_count=12000,
        tmp_path=tmp_path,
    )
    service, recorder, docs_factory, factory_proxy = fixture
    request = build_generation_request(
        snapshot=snapshot,
        evidence=(record, pending),
        selected=(record.evidence_id,),
    )

    first = service.run(request)
    second = service.run(request)

    assert first.draft is not None and first.draft.status == "draft"
    assert second.draft is not None and second.draft.status == "draft"
    assert len(factory_proxy.policies) == 2
    assert len(factory_proxy.sessions) == 2
    assert factory_proxy.sessions[0] is not factory_proxy.sessions[1]
    assert len(docs_factory.created) == 2
    assert docs_factory.created[0] is not docs_factory.created[1]
    assert len(recorder.queries) == 2
    assert recorder.queries[0]["session"] is not recorder.queries[1]["session"]
    assert recorder.queries[0]["session"].question == QUESTION_TEXT
    assert recorder.queries[1]["session"].question == QUESTION_TEXT
    assert recorder.queries[0]["docs_name"] == recorder.queries[1]["docs_name"]
    assert recorder.queries[0]["texts"] == (record.excerpt,)
    assert recorder.queries[1]["texts"] == (record.excerpt,)
    assert pending.excerpt not in recorder.queries[0]["texts"]
    assert pending.excerpt not in recorder.queries[1]["texts"]


# --------------------------------------------------------------------------- #
# GN-D-12: source-free collectability and no skip/xfail/global substitution.
# --------------------------------------------------------------------------- #


def test_gn_d12_test_module_collects_without_the_proposed_modules() -> None:
    """The test file itself must not import D/B proposals at module scope."""
    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_roots = (
        "paperqa",
        "papertrace.answer.generation",
        "papertrace.answer.b_gateway_adapter",
        "papertrace.retrieval",
    )
    offenders: list[str] = []
    for node in tree.body:
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            names = [node.module]
        offenders.extend(
            name
            for name in names
            if any(name == root or name.startswith(f"{root}.") for root in forbidden_roots)
        )
    assert offenders == []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute):
            continue
        if isinstance(node.value, ast.Name) and node.value.id == "pytest":
            assert node.attr not in {"skip", "xfail", "importorskip"}
        if (
            isinstance(node.value, ast.Attribute)
            and isinstance(node.value.value, ast.Name)
            and node.value.value.id == "pytest"
            and node.value.attr == "mark"
        ):
            assert node.attr not in {"skip", "xfail", "skipif"}

    proposed_names = {
        "AnswerGenerationService",
        "AnswerGenerationOutcome",
        "AnswerGenerationRequest",
        "BGatewayGenerationAdapter",
        "GenerationCallRequest",
        "GenerationCallResult",
        "GenerationPolicySpec",
        "GenerationPort",
        "GenerationResultShapeError",
        "extract_citation_keys",
    }
    defined = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.ClassDef, ast.FunctionDef))
    }
    assert defined.isdisjoint(proposed_names)
