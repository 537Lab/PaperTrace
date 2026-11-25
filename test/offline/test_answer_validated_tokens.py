"""Module D regression: reuse validation-time revision/digest for the draft.

Traceability: FR-D-02, INV-04. Proposed design record:
``docs/team/designs/module-D/20261122-d-validated-token-reuse.md``.

The projection handed to ``AnswerService.prepare`` changes its ``revision`` and
``digest`` properties after the first read of each. Validation must accept those
first (valid) values once, and the draft must be built from the same values; a
draft that re-reads either property is the defect under test.

All material is synthetic: two local corpus fixtures, contract-valid objects and a
duck-typed projection double. No PaperTrace product model, live/network test or real
semantic evaluation is used. D's public surface is resolved at execution time, so a
checkout without ``papertrace.answer`` still collects and reports ordinary failures.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from importlib import import_module
from pathlib import Path
from typing import Any

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
REQUESTED_AT = datetime(2026, 11, 22, 0, 0, tzinfo=timezone.utc)
FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "answer"
CORPUS_A = FIXTURE_DIR / "synthetic-corpus-a.txt"

# First-read ("A") and later-read ("B") tokens. They are distinct constants so a
# draft assertion compares against immutable expected values and never touches the
# stateful projection a second time.
REVISION_A = 7
REVISION_B = 9
EMPTY_REVISION_A = 3
EMPTY_REVISION_B = 8
REVISION_ONLY_A = 4
REVISION_ONLY_B = 6
DIGEST_A = sha256(b"papertrace validated-token synthetic projection A").hexdigest()
DIGEST_B = sha256(b"papertrace validated-token synthetic projection B").hexdigest()

ELIGIBLE = "eligible"
ABSTAINED = "abstained"

MISSING_IMPLEMENTATION = (
    "FR-D-01/INV-01: module papertrace.answer is not implemented "
    "(expected RED during the approved test-preparation stage)"
)


def answer_module() -> Any:
    """Resolve D at execution time; only the exact absent module becomes an assertion."""
    try:
        return import_module("papertrace.answer")
    except ModuleNotFoundError as error:
        if error.name != "papertrace.answer":
            raise
        raise AssertionError(MISSING_IMPLEMENTATION) from None


def d_symbol(name: str) -> Any:
    """Resolve one proposed D public attribute at execution time; absence fails clearly."""
    module = answer_module()
    symbol = getattr(module, name, None)
    if symbol is None:
        raise AssertionError(f"proposed Module D public attribute {name!r} is missing")
    return symbol


@dataclass(frozen=True)
class StaticProjection:
    """Stable synthetic stand-in for C's read-only projection (control cases only)."""

    snapshot_id: str
    question_id: str
    revision: int
    digest: str
    accepted_evidence_ids: tuple[str, ...] = ()
    events: tuple[object, ...] = ()


class TokenTrapProjection:
    """Synthetic projection whose revision/digest change after the first read.

    Revision and digest keep separate counters so a revision trap cannot hide a
    missing or repeated digest read. Reads beyond the supplied values repeat the
    last one; the tests never read these properties themselves.
    """

    def __init__(
        self,
        *,
        snapshot_id: str,
        question_id: str,
        revision_values: tuple[object, ...],
        digest_values: tuple[object, ...],
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


class ProjectionReader:
    """Read-only projection port double; it records reads and never writes."""

    def __init__(self, projection: object) -> None:
        self.projection = projection
        self.reads: list[str] = []

    def read_projection(self, question_id: str) -> object:
        self.reads.append(question_id)
        return self.projection


def corpus_snapshot() -> tuple[CorpusSnapshot, EvidenceRecord]:
    """Build the approved synthetic corpus and one accepted candidate from its bytes."""
    assert CORPUS_A.is_file(), f"approved synthetic fixture is missing: {CORPUS_A.name}"
    document = DocumentVersion(
        schema_version=1,
        document_id="doc-synthetic-a",
        version_sha256=sha256(CORPUS_A.read_bytes()).hexdigest(),
        title="Synthetic corpus A",
        source_name=CORPUS_A.name,
        status="ready",
    )
    snapshot = CorpusSnapshot(
        schema_version=1, documents=(document,), created_at=REQUESTED_AT
    )
    lines = CORPUS_A.read_text(encoding="utf-8").splitlines()
    record = EvidenceRecord(
        schema_version=1,
        snapshot_id=snapshot.snapshot_id,
        document_id=document.document_id,
        version_sha256=document.version_sha256,
        locator=SourceLocator(
            schema_version=1,
            line_start=2,
            line_end=2,
            chunk_id=f"chunk-{document.document_id}-2",
            parser_name="papertrace-synthetic",
            parser_version="1",
        ),
        excerpt=lines[1],
        retrieved_at=REQUESTED_AT,
    )
    return snapshot, record


def answer_request(
    snapshot: CorpusSnapshot, evidence: tuple[EvidenceRecord, ...]
) -> Any:
    request_type = d_symbol("AnswerRequest")
    return request_type(
        snapshot=snapshot,
        question_id=QUESTION_ID,
        answer_id=ANSWER_ID,
        requested_at=REQUESTED_AT,
        evidence=evidence,
    )


def prepare_with(
    snapshot: CorpusSnapshot,
    projection: object,
    evidence: tuple[EvidenceRecord, ...],
) -> tuple[AnswerDraft, ProjectionReader]:
    """Run one prepare call and return the draft with the reader that served it."""
    reader = ProjectionReader(projection)
    service_type = d_symbol("AnswerService")
    service = service_type(projections=reader)
    return service.prepare(answer_request(snapshot, evidence)), reader


def assert_draft_identity(draft: AnswerDraft, snapshot: CorpusSnapshot) -> None:
    """INV-04/QA-01: scope, empty sent/cited/body and the shared contract round-trip."""
    assert draft.answer_id == ANSWER_ID
    assert draft.snapshot_id == snapshot.snapshot_id
    assert draft.question_id == QUESTION_ID
    assert draft.generated_at == REQUESTED_AT
    assert draft.sent_evidence_ids == ()
    assert draft.citation_evidence_ids == ()
    assert draft.body == ""
    assert AnswerDraft.model_validate_json(draft.model_dump_json()) == draft


# VT-D-01 / VT-D-07: stable accepted and empty-approved controls.
@pytest.mark.parametrize(
    ("revision", "accepted"),
    [(REVISION_A, True), (0, False), (REVISION_ONLY_A, False)],
    ids=["accepted-evidence", "unreviewed-empty", "reviewed-empty"],
)
def test_static_projection_controls_preserve_the_draft_contract(
    revision: int, accepted: bool
) -> None:
    """A valid projection still produces the approved refusal draft shape."""
    snapshot, record = corpus_snapshot()
    approved = (record.evidence_id,) if accepted else ()
    projection = StaticProjection(
        snapshot_id=snapshot.snapshot_id,
        question_id=QUESTION_ID,
        revision=revision,
        digest=DIGEST_A,
        accepted_evidence_ids=approved,
    )

    draft, reader = prepare_with(snapshot, projection, (record,))

    assert_draft_identity(draft, snapshot)
    assert reader.reads == [QUESTION_ID]
    assert draft.review_revision == revision
    assert draft.review_digest == DIGEST_A
    if accepted:
        assert draft.status == "failed"
        assert draft.approved_evidence_ids == (record.evidence_id,)
        assert draft.refusal_reason == d_symbol("REFUSAL_GENERATION_PATH_NOT_ENABLED")
    else:
        assert draft.status == "abstained"
        assert draft.approved_evidence_ids == ()
        assert draft.refusal_reason == d_symbol("REFUSAL_NO_APPROVED_EVIDENCE")


# Both fields varying, revision-only and digest-only, for both decision outcomes.
TOKEN_CASES = (
    ("eligible-both-vary", ELIGIBLE, (REVISION_A, REVISION_B), (DIGEST_A, DIGEST_B)),
    (
        "eligible-revision-only",
        ELIGIBLE,
        (REVISION_ONLY_A, REVISION_ONLY_B),
        (DIGEST_A, DIGEST_A),
    ),
    ("eligible-digest-only", ELIGIBLE, (REVISION_ONLY_A, REVISION_ONLY_A), (DIGEST_A, DIGEST_B)),
    (
        "abstained-both-vary",
        ABSTAINED,
        (EMPTY_REVISION_A, EMPTY_REVISION_B),
        (DIGEST_A, DIGEST_B),
    ),
    (
        "abstained-revision-only",
        ABSTAINED,
        (REVISION_ONLY_A, REVISION_ONLY_B),
        (DIGEST_A, DIGEST_A),
    ),
    (
        "abstained-digest-only",
        ABSTAINED,
        (REVISION_ONLY_A, REVISION_ONLY_A),
        (DIGEST_A, DIGEST_B),
    ),
)
TOKEN_CASE_IDS = [case[0] for case in TOKEN_CASES]
TOKEN_PARAM_NAMES = ("case_id", "path", "revision_values", "digest_values")


def trapped_case(
    case: tuple[str, str, tuple[int, ...], tuple[str, ...]],
) -> tuple[CorpusSnapshot, EvidenceRecord, TokenTrapProjection]:
    case_id, path, revision_values, digest_values = case
    snapshot, record = corpus_snapshot()
    approved = (record.evidence_id,) if path == ELIGIBLE else ()
    trap = TokenTrapProjection(
        snapshot_id=snapshot.snapshot_id,
        question_id=QUESTION_ID,
        revision_values=revision_values,
        digest_values=digest_values,
        accepted_evidence_ids=approved,
    )
    return snapshot, record, trap


@pytest.mark.parametrize(TOKEN_PARAM_NAMES, TOKEN_CASES, ids=TOKEN_CASE_IDS)
def test_draft_uses_the_validated_first_token_values(
    case_id: str,
    path: str,
    revision_values: tuple[int, ...],
    digest_values: tuple[str, ...],
) -> None:
    """VT-D-02..04: the draft must carry the first-read revision and digest."""
    snapshot, record, trap = trapped_case((case_id, path, revision_values, digest_values))

    draft, _ = prepare_with(snapshot, trap, (record,))

    assert_draft_identity(draft, snapshot)
    assert draft.review_revision == revision_values[0]
    assert draft.review_digest == digest_values[0]
    if path == ELIGIBLE:
        assert draft.status == "failed"
        assert draft.approved_evidence_ids == (record.evidence_id,)
        assert draft.refusal_reason == d_symbol("REFUSAL_GENERATION_PATH_NOT_ENABLED")
    else:
        assert draft.status == "abstained"
        assert draft.approved_evidence_ids == ()
        assert draft.refusal_reason == d_symbol("REFUSAL_NO_APPROVED_EVIDENCE")


@pytest.mark.parametrize(TOKEN_PARAM_NAMES, TOKEN_CASES, ids=TOKEN_CASE_IDS)
def test_successful_prepare_reads_each_token_exactly_once(
    case_id: str,
    path: str,
    revision_values: tuple[int, ...],
    digest_values: tuple[str, ...],
) -> None:
    """VT-D-05: validation and the draft share one read of each token."""
    snapshot, record, trap = trapped_case((case_id, path, revision_values, digest_values))

    draft, _ = prepare_with(snapshot, trap, (record,))

    assert trap.revision_reads == 1
    assert trap.digest_reads == 1
    assert draft.review_revision == revision_values[0]
    assert draft.review_digest == digest_values[0]


# A first invalid token followed by valid values must still fail validation.
INVALID_FIRST_CASES = (
    ("negative-revision-first", (-1, REVISION_A), (DIGEST_A, DIGEST_A)),
    ("malformed-digest-first", (REVISION_A, REVISION_A), ("not-a-sha256", DIGEST_B)),
)
INVALID_FIRST_IDS = [case[0] for case in INVALID_FIRST_CASES]


@pytest.mark.parametrize(
    ("case_id", "revision_values", "digest_values"),
    INVALID_FIRST_CASES,
    ids=INVALID_FIRST_IDS,
)
def test_invalid_first_token_raises_without_using_later_valid_values(
    case_id: str,
    revision_values: tuple[int, ...],
    digest_values: tuple[str, ...],
) -> None:
    """VT-D-06: an invalid first read is a shape failure, never a draft."""
    snapshot, record = corpus_snapshot()
    trap = TokenTrapProjection(
        snapshot_id=snapshot.snapshot_id,
        question_id=QUESTION_ID,
        revision_values=revision_values,
        digest_values=digest_values,
        accepted_evidence_ids=(record.evidence_id,),
    )

    with pytest.raises(d_symbol("ProjectionShapeError")):
        prepare_with(snapshot, trap, (record,))

    # The failing token is read once; a later getter is not required to run.
    assert trap.revision_reads == 1
    assert trap.digest_reads <= 1


@pytest.mark.parametrize(TOKEN_PARAM_NAMES, TOKEN_CASES, ids=TOKEN_CASE_IDS)
def test_token_cases_change_only_the_declared_field(
    case_id: str,
    path: str,
    revision_values: tuple[int, ...],
    digest_values: tuple[str, ...],
) -> None:
    """Instrument control: no case is vacuous because A and B happen to be equal."""
    if case_id.endswith("both-vary"):
        assert revision_values[0] != revision_values[1]
        assert digest_values[0] != digest_values[1]
    elif case_id.endswith("revision-only"):
        assert revision_values[0] != revision_values[1]
        assert digest_values[0] == digest_values[1]
    else:
        assert revision_values[0] == revision_values[1]
        assert digest_values[0] != digest_values[1]
