"""Module D slice 1: approved-eligibility gate and refusal before generation.

Traceability: FR-D-01, FR-D-02, FR-D-03 (partial), INV-01, INV-04, COST-01.
The proposed D-local interfaces exercised here are fixed in
``docs/team/designs/module-D/20261117-d-abstain-pre-generation-gate.md``.
No generation collaborator, model, network or human approval is involved.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from importlib import import_module
from importlib.util import find_spec
from pathlib import Path
from typing import Any, Callable

import pytest

from papertrace.contracts import (
    AnswerDraft,
    CorpusSnapshot,
    DocumentVersion,
    EvidenceRecord,
    SourceLocator,
)

QUESTION_ID = "q-synthetic-1"
ANSWER_ID = "ans-synthetic-1"
REQUESTED_AT = datetime(2026, 11, 17, 0, 0, tzinfo=timezone.utc)
FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "answer"
CORPUS_A = FIXTURE_DIR / "synthetic-corpus-a.txt"
CORPUS_B = FIXTURE_DIR / "synthetic-corpus-b.txt"
# Provisional fixture digest: D checks only its shape and never replays C's ledger.
PROJECTION_DIGEST = sha256(b"papertrace synthetic review projection v1").hexdigest()


def answer(name: str) -> Any:
    """Resolve a proposed D-local public symbol; absence is an assertion, not ImportError."""
    try:
        spec = find_spec("papertrace.answer")
    except ModuleNotFoundError:
        spec = None
    assert spec is not None, (
        "FR-D-01/INV-01: proposed module papertrace.answer is not implemented "
        "(expected RED during the approved test-preparation stage)"
    )
    module = import_module("papertrace.answer")
    symbol = getattr(module, name, None)
    assert symbol is not None, f"proposed Module D public interface {name!r} is missing"
    return symbol


def build_document(path: Path, document_id: str, title: str) -> DocumentVersion:
    """QA-01/INV-02: the content version is the SHA-256 of the fixture bytes."""
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


def build_unverified_evidence(
    snapshot: CorpusSnapshot,
    *,
    document_id: str,
    version_sha256: str,
    path: Path = CORPUS_A,
) -> EvidenceRecord:
    """Deliberately inconsistent provenance for negative tests, still contract-shaped."""
    return EvidenceRecord(
        schema_version=1,
        snapshot_id=snapshot.snapshot_id,
        document_id=document_id,
        version_sha256=version_sha256,
        locator=SourceLocator(
            schema_version=1,
            line_start=2,
            line_end=2,
            chunk_id="chunk-unverified",
            parser_name="papertrace-synthetic",
            parser_version="1",
        ),
        excerpt=excerpt(path),
        retrieved_at=REQUESTED_AT,
    )


@dataclass(frozen=True)
class FakeProjection:
    """Provisional stand-in for C's proposal; never an approved interface."""

    snapshot_id: str
    question_id: str
    revision: int
    digest: str
    accepted_evidence_ids: tuple[str, ...] = ()
    events: tuple[object, ...] = ()


def build_projection(
    snapshot: CorpusSnapshot,
    *,
    revision: int = 0,
    accepted: tuple[str, ...] = (),
    events: tuple[object, ...] = (),
    question_id: str = QUESTION_ID,
    digest: str = PROJECTION_DIGEST,
    snapshot_id: str | None = None,
) -> FakeProjection:
    return FakeProjection(
        snapshot_id=snapshot.snapshot_id if snapshot_id is None else snapshot_id,
        question_id=question_id,
        revision=revision,
        digest=digest,
        accepted_evidence_ids=tuple(accepted),
        events=tuple(events),
    )


class StubProjectionReader:
    """Read-only projection collaborator stand-in; it never writes a ledger."""

    def __init__(self, outcome: object) -> None:
        self.outcome = outcome
        self.reads: list[str] = []

    def read_projection(self, question_id: str) -> object:
        self.reads.append(question_id)
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


def build_request(snapshot: CorpusSnapshot, evidence: tuple[EvidenceRecord, ...]) -> Any:
    request_type = answer("AnswerRequest")
    return request_type(
        snapshot=snapshot,
        question_id=QUESTION_ID,
        answer_id=ANSWER_ID,
        requested_at=REQUESTED_AT,
        evidence=evidence,
    )


def prepare(
    snapshot: CorpusSnapshot,
    outcome: object,
    evidence: tuple[EvidenceRecord, ...],
) -> Any:
    service = answer("AnswerService")(projections=StubProjectionReader(outcome))
    return service.prepare(build_request(snapshot, evidence))


def shape_cases() -> list[tuple[str, Callable[[CorpusSnapshot, EvidenceRecord], object]]]:
    return [
        (
            "not-a-projection",
            lambda snapshot, record: object(),
        ),
        (
            "negative-revision",
            lambda snapshot, record: build_projection(snapshot, revision=-1),
        ),
        (
            "boolean-revision",
            lambda snapshot, record: build_projection(snapshot, revision=True),
        ),
        (
            "string-revision",
            lambda snapshot, record: build_projection(snapshot, revision="1"),
        ),
        (
            "malformed-digest",
            lambda snapshot, record: build_projection(snapshot, digest="not-a-sha256"),
        ),
        (
            "missing-digest",
            lambda snapshot, record: build_projection(snapshot, digest=None),
        ),
        (
            "malformed-question-id",
            lambda snapshot, record: build_projection(snapshot, question_id="question-1"),
        ),
        (
            "malformed-snapshot-id",
            lambda snapshot, record: build_projection(snapshot, snapshot_id="snap-nope"),
        ),
        (
            "malformed-accepted-id",
            lambda snapshot, record: build_projection(snapshot, accepted=("not-an-evidence",)),
        ),
        (
            "duplicate-accepted-id",
            lambda snapshot, record: build_projection(
                snapshot, revision=1, accepted=(record.evidence_id, record.evidence_id)
            ),
        ),
        (
            "accepted-with-zero-revision",
            lambda snapshot, record: build_projection(
                snapshot, revision=0, accepted=(record.evidence_id,)
            ),
        ),
    ]


SHAPE_CASES = shape_cases()
SHAPE_CASE_IDS = [case_id for case_id, _ in SHAPE_CASES]


def scope_cases() -> list[tuple[str, Callable[..., object]]]:
    return [
        (
            "wrong-question",
            lambda snapshot, record, other: build_projection(
                snapshot, question_id="q-synthetic-2"
            ),
        ),
        (
            "wrong-snapshot",
            lambda snapshot, record, other: build_projection(
                snapshot, snapshot_id=other.snapshot_id
            ),
        ),
    ]


SCOPE_CASES = scope_cases()
SCOPE_CASE_IDS = [case_id for case_id, _ in SCOPE_CASES]


def foreign_snapshot_case(
    snapshot: CorpusSnapshot,
    doc_a: DocumentVersion,
    doc_b: DocumentVersion,
) -> tuple[tuple[EvidenceRecord, ...], tuple[str, ...]]:
    other = CorpusSnapshot(schema_version=1, documents=(doc_b,), created_at=REQUESTED_AT)
    record = build_evidence(other, doc_b, CORPUS_B)
    return (record,), (record.evidence_id,)


def unknown_document_case(
    snapshot: CorpusSnapshot,
    doc_a: DocumentVersion,
    doc_b: DocumentVersion,
) -> tuple[tuple[EvidenceRecord, ...], tuple[str, ...]]:
    record = build_unverified_evidence(
        snapshot, document_id="doc-synthetic-z", version_sha256="c" * 64
    )
    return (record,), (record.evidence_id,)


def wrong_version_case(
    snapshot: CorpusSnapshot,
    doc_a: DocumentVersion,
    doc_b: DocumentVersion,
) -> tuple[tuple[EvidenceRecord, ...], tuple[str, ...]]:
    record = build_unverified_evidence(
        snapshot, document_id=doc_a.document_id, version_sha256=doc_b.version_sha256
    )
    return (record,), (record.evidence_id,)


PROVENANCE_CASES: dict[
    str,
    Callable[
        [CorpusSnapshot, DocumentVersion, DocumentVersion],
        tuple[tuple[EvidenceRecord, ...], tuple[str, ...]],
    ],
] = {
    "foreign-snapshot": foreign_snapshot_case,
    "unknown-document": unknown_document_case,
    "wrong-version": wrong_version_case,
}


@pytest.mark.parametrize(("revision", "events"), [(0, ()), (3, (object(),))])
def test_projection_without_accepted_evidence_abstains(
    revision: int, events: tuple[object, ...]
) -> None:
    """FR-D-01/INV-01: no accepted evidence yields a refusal, not a generation attempt."""
    snapshot, doc_a, _ = build_corpus()
    record = build_evidence(snapshot, doc_a, CORPUS_A)
    current = build_projection(snapshot, revision=revision, events=events)

    draft = prepare(snapshot, current, (record,))

    assert draft.status == "abstained"
    assert draft.approved_evidence_ids == ()
    assert draft.sent_evidence_ids == ()
    assert draft.citation_evidence_ids == ()
    assert draft.body == ""
    assert draft.refusal_reason == answer("REFUSAL_NO_APPROVED_EVIDENCE")
    assert draft.review_revision == revision
    assert draft.review_digest == current.digest
    assert draft.generated_at == REQUESTED_AT
    assert draft.answer_id == ANSWER_ID
    assert draft.snapshot_id == snapshot.snapshot_id
    assert draft.question_id == QUESTION_ID


def test_pure_gate_marks_accepted_evidence_eligible() -> None:
    """FR-D-02/INV-04: eligibility is a pure decision over the current projection."""
    snapshot, doc_a, _ = build_corpus()
    record = build_evidence(snapshot, doc_a, CORPUS_A)
    current = build_projection(snapshot, revision=1, accepted=(record.evidence_id,))

    decision = answer("evaluate_eligibility")(
        projection=current, request=build_request(snapshot, (record,))
    )

    assert isinstance(decision, answer("EligibilityDecision"))
    assert decision.eligible is True
    assert decision.approved_evidence_ids == (record.evidence_id,)
    assert decision.reason is None
    assert not hasattr(decision, "sent_evidence_ids")


def gate_mismatch_cases() -> list[
    tuple[
        str,
        Callable[
            [CorpusSnapshot, DocumentVersion, DocumentVersion],
            tuple[object, tuple[EvidenceRecord, ...]],
        ],
        str,
    ]
]:
    """Direct gate inputs for scope, membership and provenance negatives."""

    def wrong_question(snapshot, doc_a, doc_b):
        record = build_evidence(snapshot, doc_a, CORPUS_A)
        return build_projection(snapshot, question_id="q-synthetic-2"), (record,)

    def wrong_snapshot(snapshot, doc_a, doc_b):
        record = build_evidence(snapshot, doc_a, CORPUS_A)
        other = CorpusSnapshot(schema_version=1, documents=(doc_a,), created_at=REQUESTED_AT)
        return build_projection(snapshot, snapshot_id=other.snapshot_id), (record,)

    def unknown_accepted(snapshot, doc_a, doc_b):
        record = build_evidence(snapshot, doc_a, CORPUS_A)
        stranger = "ev-" + "f" * 64
        return build_projection(snapshot, revision=1, accepted=(stranger,)), (record,)

    def foreign_snapshot(snapshot, doc_a, doc_b):
        other = CorpusSnapshot(schema_version=1, documents=(doc_b,), created_at=REQUESTED_AT)
        record = build_evidence(other, doc_b, CORPUS_B)
        accepted = (record.evidence_id,)
        return build_projection(snapshot, revision=1, accepted=accepted), (record,)

    def unknown_document(snapshot, doc_a, doc_b):
        record = build_unverified_evidence(
            snapshot, document_id="doc-synthetic-z", version_sha256="c" * 64
        )
        accepted = (record.evidence_id,)
        return build_projection(snapshot, revision=1, accepted=accepted), (record,)

    def wrong_version(snapshot, doc_a, doc_b):
        record = build_unverified_evidence(
            snapshot, document_id=doc_a.document_id, version_sha256=doc_b.version_sha256
        )
        accepted = (record.evidence_id,)
        return build_projection(snapshot, revision=1, accepted=accepted), (record,)

    return [
        ("scope-question", wrong_question, "ProjectionScopeMismatchError"),
        ("scope-snapshot", wrong_snapshot, "ProjectionScopeMismatchError"),
        ("unknown-accepted", unknown_accepted, "UnknownAcceptedEvidenceError"),
        ("foreign-snapshot", foreign_snapshot, "EvidenceProvenanceError"),
        ("unknown-document", unknown_document, "EvidenceProvenanceError"),
        ("wrong-version", wrong_version, "EvidenceProvenanceError"),
    ]


GATE_MISMATCH_CASES = gate_mismatch_cases()
GATE_MISMATCH_IDS = [case_id for case_id, _, _ in GATE_MISMATCH_CASES]


@pytest.mark.parametrize(
    ("case_id", "build", "error_name"), GATE_MISMATCH_CASES, ids=GATE_MISMATCH_IDS
)
def test_pure_gate_rejects_mismatched_scope_membership_and_provenance(
    case_id: str,
    build: Callable[
        [CorpusSnapshot, DocumentVersion, DocumentVersion],
        tuple[object, tuple[EvidenceRecord, ...]],
    ],
    error_name: str,
) -> None:
    """Checks 2-4 must hold in the gate itself, independently of any service wiring."""
    snapshot, doc_a, doc_b = build_corpus()
    record = build_evidence(snapshot, doc_a, CORPUS_A)
    control = answer("evaluate_eligibility")(
        projection=build_projection(snapshot, revision=1, accepted=(record.evidence_id,)),
        request=build_request(snapshot, (record,)),
    )
    assert control.eligible is True
    current, evidence = build(snapshot, doc_a, doc_b)

    with pytest.raises(answer(error_name)):
        answer("evaluate_eligibility")(
            projection=current, request=build_request(snapshot, evidence)
        )


def test_eligible_evidence_is_not_generated_in_this_slice() -> None:
    """FR-D-03 (partial): without a generation path the service fails closed."""
    snapshot, doc_a, _ = build_corpus()
    record = build_evidence(snapshot, doc_a, CORPUS_A)
    current = build_projection(snapshot, revision=1, accepted=(record.evidence_id,))

    draft = prepare(snapshot, current, (record,))

    assert draft.status == "failed"
    assert draft.approved_evidence_ids == (record.evidence_id,)
    assert draft.sent_evidence_ids == ()
    assert draft.citation_evidence_ids == ()
    assert draft.body == ""
    assert draft.refusal_reason == answer("REFUSAL_GENERATION_PATH_NOT_ENABLED")
    assert draft.review_revision == 1
    assert draft.review_digest == current.digest


def test_service_reads_the_projection_once_for_the_requested_question() -> None:
    """FR-D-01: the only collaborator is consulted once, for this question."""
    snapshot, doc_a, _ = build_corpus()
    record = build_evidence(snapshot, doc_a, CORPUS_A)
    reader = StubProjectionReader(build_projection(snapshot))
    service = answer("AnswerService")(projections=reader)

    service.prepare(build_request(snapshot, (record,)))

    assert reader.reads == [QUESTION_ID]


def test_proposed_refusal_reasons_are_stable_strings() -> None:
    """The design record fixes these policy strings; tests must not drift from it."""
    assert answer("REFUSAL_NO_APPROVED_EVIDENCE") == "NO_APPROVED_EVIDENCE"
    assert answer("REFUSAL_GENERATION_PATH_NOT_ENABLED") == "GENERATION_PATH_NOT_ENABLED"


def test_unavailable_review_state_raises_without_returning_a_draft() -> None:
    """FR-D-01/INV-01: an unreadable review state surfaces as a typed error, not a draft."""
    snapshot, doc_a, _ = build_corpus()
    record = build_evidence(snapshot, doc_a, CORPUS_A)
    error_type = answer("ReviewStateUnavailableError")

    with pytest.raises(error_type) as excinfo:
        prepare(snapshot, error_type("review state unavailable"), (record,))

    assert str(excinfo.value) == "review state unavailable"


@pytest.mark.parametrize(("case_id", "build"), SHAPE_CASES, ids=SHAPE_CASE_IDS)
def test_malformed_projection_raises_shape_error(
    case_id: str,
    build: Callable[[CorpusSnapshot, EvidenceRecord], object],
) -> None:
    """Checks 1/4: shape, revision, digest, accepted-ID pattern and uniqueness."""
    snapshot, doc_a, _ = build_corpus()
    record = build_evidence(snapshot, doc_a, CORPUS_A)
    control = prepare(snapshot, build_projection(snapshot), (record,))
    assert control.status == "abstained"

    with pytest.raises(answer("ProjectionShapeError")):
        prepare(snapshot, build(snapshot, record), (record,))


@pytest.mark.parametrize(("case_id", "build"), SCOPE_CASES, ids=SCOPE_CASE_IDS)
def test_projection_header_scope_mismatch_raises(
    case_id: str,
    build: Callable[[CorpusSnapshot, EvidenceRecord, CorpusSnapshot], object],
) -> None:
    """Check 2: projection header must match the requested snapshot and question."""
    snapshot, doc_a, _ = build_corpus()
    other = CorpusSnapshot(schema_version=1, documents=(doc_a,), created_at=REQUESTED_AT)
    record = build_evidence(snapshot, doc_a, CORPUS_A)
    control = prepare(
        snapshot,
        build_projection(snapshot, revision=1, accepted=(record.evidence_id,)),
        (record,),
    )
    assert control.status == "failed"

    with pytest.raises(answer("ProjectionScopeMismatchError")):
        prepare(snapshot, build(snapshot, record, other), (record,))


def test_unknown_accepted_evidence_raises() -> None:
    """Check 4: an accepted ID absent from the supplied evidence is never guessed."""
    snapshot, doc_a, _ = build_corpus()
    record = build_evidence(snapshot, doc_a, CORPUS_A)
    stranger = "ev-" + "f" * 64
    control = prepare(
        snapshot,
        build_projection(snapshot, revision=1, accepted=(record.evidence_id,)),
        (record,),
    )
    assert control.status == "failed"

    with pytest.raises(answer("UnknownAcceptedEvidenceError")):
        prepare(
            snapshot,
            build_projection(snapshot, revision=1, accepted=(stranger,)),
            (record,),
        )


@pytest.mark.parametrize("case_id", sorted(PROVENANCE_CASES))
def test_evidence_provenance_mismatch_raises(case_id: str) -> None:
    """Checks 3/4: snapshot, document and version of accepted evidence must match."""
    snapshot, doc_a, doc_b = build_corpus()
    record = build_evidence(snapshot, doc_a, CORPUS_A)
    control = prepare(
        snapshot,
        build_projection(snapshot, revision=1, accepted=(record.evidence_id,)),
        (record,),
    )
    assert control.status == "failed"
    evidence, accepted = PROVENANCE_CASES[case_id](snapshot, doc_a, doc_b)

    with pytest.raises(answer("EvidenceProvenanceError")):
        prepare(snapshot, build_projection(snapshot, revision=1, accepted=accepted), evidence)


def test_returned_drafts_round_trip_through_shared_contracts() -> None:
    """QA-01/INV-04: both refusal shapes survive the shared JSON contract unchanged."""
    snapshot, doc_a, _ = build_corpus()
    record = build_evidence(snapshot, doc_a, CORPUS_A)
    abstained = prepare(snapshot, build_projection(snapshot), (record,))
    failed = prepare(
        snapshot,
        build_projection(snapshot, revision=1, accepted=(record.evidence_id,)),
        (record,),
    )

    for draft in (abstained, failed):
        assert AnswerDraft.model_validate_json(draft.model_dump_json()) == draft
    assert abstained.status == "abstained"
    assert failed.status == "failed"


# Direct provider SDKs and HTTP/network stacks that could open an outbound attempt.
# `google` covers google.genai / google.generativeai; `http.client` and
# `urllib.request` are matched as exact module paths, not the whole stdlib package.
PROVIDER_AND_NETWORK_ROOTS = (
    "paperqa",
    "openai",
    "anthropic",
    "cohere",
    "mistralai",
    "litellm",
    "fhlmi",
    "google",
    "httpx",
    "requests",
    "aiohttp",
    "urllib3",
    "socket",
)
PROVIDER_AND_NETWORK_MODULES = ("http.client", "urllib.request")


def forbidden_imports(source: str) -> list[str]:
    """Return forbidden dotted import targets found in one module source string."""
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                continue
            names = [f"{node.module}.{alias.name}" for alias in node.names]
        else:
            continue
        for name in names:
            root_match = any(
                name == root or name.startswith(f"{root}.")
                for root in PROVIDER_AND_NETWORK_ROOTS
            )
            if root_match:
                found.append(name)
            elif any(
                name == module or name.startswith(f"{module}.")
                for module in PROVIDER_AND_NETWORK_MODULES
            ):
                found.append(name)
    return found


def test_static_import_scanner_flags_provider_and_network_imports() -> None:
    """The scanner must not pass vacuously; check it against known-bad imports."""
    sample = "\n".join(
        [
            "import httpx",
            "from openai import OpenAI",
            "from google import genai",
            "import socket",
            "from urllib import request",
            "import http.client",
            "from papertrace.contracts import AnswerDraft",
        ]
    )

    assert forbidden_imports(sample) == [
        "httpx",
        "openai.OpenAI",
        "google.genai",
        "socket",
        "urllib.request",
        "http.client",
    ]


def test_answer_package_has_no_direct_upstream_provider_or_network_imports() -> None:
    """Supplementary static observation; not proof of zero outbound attempts."""
    try:
        package = import_module("papertrace.answer")
    except ModuleNotFoundError:
        pytest.fail(
            "FR-D-01/INV-01: proposed module papertrace.answer is not implemented "
            "(expected RED during the approved test-preparation stage)"
        )
    root = Path(package.__file__).parent
    offenders = [
        f"{path.relative_to(root).as_posix()}:{name}"
        for path in sorted(root.rglob("*.py"))
        for name in forbidden_imports(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []
