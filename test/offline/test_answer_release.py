"""Module D release gate: deterministic freshness and traceability checks.

Traceability: FR-D-01, FR-D-02, INV-01, INV-02, INV-03, INV-04, QA-01,
offline COST-01. The proposed D-local interface is fixed in
``docs/team/designs/module-D/20261123-d-release-gate-plan.md``.

This is a test-preparation artifact. ``papertrace.answer.release`` does not
exist yet, so every case fails through ``release_module()`` with the explicit
prerequisite assertion instead of a collection error. No product model, network,
human approval, B generation, pagination or E publishing is exercised.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from hashlib import sha256
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import ValidationError

QUESTION_ID = "q-synthetic-release"
OTHER_QUESTION_ID = "q-synthetic-release-other"
ANSWER_ID = "ans-synthetic-release"
REVIEWER = "reviewer-SYNTHETIC"
REASON = "synthetic offline release-gate fixture; not a real human approval"
CORPUS_TIME = datetime(2026, 11, 23, 0, 0, tzinfo=timezone.utc)
GENERATED_AT = datetime(2026, 11, 23, 11, 0, tzinfo=timezone.utc)
CHECK_TIME = datetime(2026, 11, 23, 12, 0, tzinfo=timezone.utc)
DIGEST_ONE = "a" * 64
DIGEST_TWO = "b" * 64
PROJECT_ROOT = Path(__file__).resolve().parents[2]

_DOC_A_TEXT = (
    "Synthetic release fixture A.\n"
    "The synthetic resonance cell stores 12 units of daylight energy.\n"
    "Only synthetic text is used in this offline test.\n"
)
_DOC_B_TEXT = (
    "Synthetic release fixture B.\n"
    "The synthetic resonance cell releases 3 units of daylight energy per cycle.\n"
    "Only synthetic text is used in this offline test.\n"
)
_DOC_C_TEXT = (
    "Synthetic release fixture C.\n"
    "The synthetic control cell records no daylight energy transfer.\n"
    "Only synthetic text is used in this offline test.\n"
)

_EXPECTED_MISSING = ("papertrace.answer", "papertrace.answer.release")


# --------------------------------------------------------------------------- #
# Lazy imports: collection is safe before D's release module exists.
# --------------------------------------------------------------------------- #
def release_module() -> Any:
    """Resolve the future release module; only its exact absence is a RED assert."""
    try:
        module = import_module("papertrace.answer.release")
    except ModuleNotFoundError as error:
        if error.name in _EXPECTED_MISSING:
            pytest.fail(
                "expected RED: proposed module papertrace.answer.release is not "
                "implemented (approved test-preparation stage); no fallback is used"
            )
        raise
    return module


def release_symbol(name: str) -> Any:
    value = getattr(release_module(), name, None)
    assert value is not None, f"proposed Module D release interface {name!r} is missing"
    return value


def contract_symbol(name: str) -> Any:
    return getattr(import_module("papertrace.contracts"), name)


def answer_symbol(name: str) -> Any:
    return getattr(import_module("papertrace.answer"), name)


def review_symbol(name: str) -> Any:
    return getattr(import_module("papertrace.review"), name)


# --------------------------------------------------------------------------- #
# Inline synthetic contracts and a real C ledger.
# --------------------------------------------------------------------------- #
def make_document(
    text: str, *, document_id: str, title: str, source_name: str
) -> Any:
    return contract_symbol("DocumentVersion")(
        schema_version=1,
        document_id=document_id,
        version_sha256=sha256(text.encode("utf-8")).hexdigest(),
        title=title,
        source_name=source_name,
        status="ready",
    )


def make_evidence(
    snapshot: Any,
    document: Any,
    text: str,
    *,
    chunk_id: str,
    line_number: int = 2,
) -> Any:
    return contract_symbol("EvidenceRecord")(
        schema_version=1,
        snapshot_id=snapshot.snapshot_id,
        document_id=document.document_id,
        version_sha256=document.version_sha256,
        locator=contract_symbol("SourceLocator")(
            schema_version=1,
            line_start=line_number,
            line_end=line_number,
            chunk_id=chunk_id,
            parser_name="papertrace-synthetic",
            parser_version="1",
        ),
        excerpt=text.splitlines()[line_number - 1],
        retrieved_at=CORPUS_TIME,
    )


@lru_cache(maxsize=1)
def synthetic_corpus() -> tuple[Any, Any, Any, Any, Any]:
    doc_a = make_document(
        _DOC_A_TEXT,
        document_id="doc-synthetic-release-a",
        title="Synthetic release corpus A",
        source_name="synthetic-release-a.txt",
    )
    doc_b = make_document(
        _DOC_B_TEXT,
        document_id="doc-synthetic-release-b",
        title="Synthetic release corpus B",
        source_name="synthetic-release-b.txt",
    )
    snapshot = contract_symbol("CorpusSnapshot")(
        schema_version=1, documents=(doc_a, doc_b), created_at=CORPUS_TIME
    )
    evidence_a = make_evidence(
        snapshot, doc_a, _DOC_A_TEXT, chunk_id="chunk-release-a-2"
    )
    evidence_b = make_evidence(
        snapshot, doc_b, _DOC_B_TEXT, chunk_id="chunk-release-b-2"
    )
    return snapshot, doc_a, doc_b, evidence_a, evidence_b


@lru_cache(maxsize=1)
def foreign_snapshot() -> tuple[Any, Any]:
    doc_c = make_document(
        _DOC_C_TEXT,
        document_id="doc-synthetic-release-c",
        title="Synthetic release corpus C",
        source_name="synthetic-release-c.txt",
    )
    snapshot = contract_symbol("CorpusSnapshot")(
        schema_version=1, documents=(doc_c,), created_at=CORPUS_TIME
    )
    evidence_c = make_evidence(
        snapshot, doc_c, _DOC_C_TEXT, chunk_id="chunk-release-c-2"
    )
    return snapshot, evidence_c


def make_draft(
    *,
    snapshot: Any,
    approved: Sequence[str],
    sent: Sequence[str],
    citation: Sequence[str],
    review_revision: int,
    review_digest: str,
    status: str = "draft",
    body: str = "Synthetic answer body for the offline release gate.",
    refusal_reason: str | None = None,
    question_id: str = QUESTION_ID,
    answer_id: str = ANSWER_ID,
) -> Any:
    return contract_symbol("AnswerDraft")(
        schema_version=1,
        answer_id=answer_id,
        snapshot_id=snapshot.snapshot_id,
        question_id=question_id,
        review_revision=review_revision,
        review_digest=review_digest,
        approved_evidence_ids=tuple(approved),
        sent_evidence_ids=tuple(sent),
        citation_evidence_ids=tuple(citation),
        status=status,
        body=body,
        refusal_reason=refusal_reason,
        generated_at=GENERATED_AT,
    )


@dataclass(frozen=True)
class Projection:
    """Structurally valid stand-in for C's read-only projection."""

    snapshot_id: str
    question_id: str
    revision: int
    digest: str
    accepted_evidence_ids: tuple[str, ...]
    events: tuple[object, ...] = ()


def projection_for(
    snapshot: Any,
    *,
    revision: int = 1,
    digest: str = DIGEST_ONE,
    accepted: Sequence[str] = (),
    question_id: str = QUESTION_ID,
    snapshot_id: str | None = None,
) -> Projection:
    return Projection(
        snapshot_id=snapshot.snapshot_id if snapshot_id is None else snapshot_id,
        question_id=question_id,
        revision=revision,
        digest=digest,
        accepted_evidence_ids=tuple(accepted),
        events=(object(),) if revision > 0 else (),
    )


class FixedClock:
    """Deterministic check clock; counts calls for the one-time-per-check claim."""

    def __init__(self, value: datetime = CHECK_TIME) -> None:
        self.value = value
        self.calls = 0

    def __call__(self) -> datetime:
        self.calls += 1
        return self.value


def make_gate(current: object, clock: Any | None = None) -> Any:
    return release_symbol("ReleaseGate")(
        current=current,
        clock=FixedClock() if clock is None else clock,
    )


def make_real_ledger(root: Path, snapshot: Any, evidence: Sequence[Any]) -> Any:
    return review_symbol("ReviewLedger")(
        ledger_root=root,
        snapshot=snapshot,
        candidates=tuple(evidence),
        clock=FixedClock(GENERATED_AT),
    )


def commit(
    ledger: Any,
    evidence_id: str,
    *,
    action: str,
    expected_revision: int,
    question_id: str = QUESTION_ID,
) -> Any:
    intent = ledger.prepare_decision(
        question_id=question_id,
        evidence_id=evidence_id,
        action=action,
        reviewer_ref=REVIEWER,
        reason=REASON,
        expected_revision=expected_revision,
        command_id=f"cmd-{action}-{expected_revision:04d}",
    )
    return ledger.commit_decision(intent)


@dataclass
class LedgerProjectionPort:
    ledger: Any

    def read_projection(self, question_id: str) -> Any:
        return self.ledger.projection(question_id)


# --------------------------------------------------------------------------- #
# Current ports and projection traps.
# --------------------------------------------------------------------------- #
@dataclass
class FixedCurrent:
    bundle: object
    reads: list[str] = field(default_factory=list)

    def read_current(self, question_id: str) -> object:
        self.reads.append(question_id)
        if isinstance(self.bundle, BaseException):
            raise self.bundle
        return self.bundle


@dataclass
class SequenceCurrent:
    bundles: Sequence[object]
    reads: list[str] = field(default_factory=list)

    def read_current(self, question_id: str) -> object:
        self.reads.append(question_id)
        index = min(len(self.reads) - 1, len(self.bundles) - 1)
        bundle = self.bundles[index]
        if isinstance(bundle, BaseException):
            raise bundle
        return bundle


@dataclass
class LedgerCurrent:
    ledger: Any
    snapshot: Any
    evidence: tuple[Any, ...]
    reads: list[str] = field(default_factory=list)

    def read_current(self, question_id: str) -> object:
        self.reads.append(question_id)
        return (self.snapshot, self.ledger.projection(question_id), self.evidence)


@dataclass
class NeverReadCurrent:
    reads: list[str] = field(default_factory=list)

    def read_current(self, question_id: str) -> object:
        self.reads.append(question_id)
        raise AssertionError("current must not be read before the draft is releasable")


class ExplodingProjection:
    """Fails if the gate touches the projection before the snapshot check."""

    def __getattr__(self, name: str) -> object:
        raise AssertionError(
            f"projection attribute {name!r} read before snapshot scope check"
        )


class TrapProjection:
    """Returns a different value on every read to expose duplicate reads."""

    def __init__(
        self,
        *,
        snapshot_id: str,
        question_id: str,
        revisions: Sequence[int],
        digests: Sequence[str],
        accepted: Sequence[Sequence[str]],
        events: Sequence[Sequence[object]],
    ) -> None:
        self._snapshot_ids = (snapshot_id,)
        self._question_ids = (question_id,)
        self._revisions = tuple(revisions)
        self._digests = tuple(digests)
        self._accepted = tuple(tuple(item) for item in accepted)
        self._events = tuple(tuple(item) for item in events)
        self.read_counts = {
            name: 0
            for name in (
                "revision",
                "digest",
                "accepted_evidence_ids",
                "snapshot_id",
                "question_id",
                "events",
            )
        }
        self.verify_calls = 0

    def _next(self, name: str, values: Sequence[Any]) -> Any:
        index = min(self.read_counts[name], len(values) - 1)
        self.read_counts[name] += 1
        return values[index]

    @property
    def snapshot_id(self) -> str:
        return self._next("snapshot_id", self._snapshot_ids)

    @property
    def question_id(self) -> str:
        return self._next("question_id", self._question_ids)

    @property
    def revision(self) -> int:
        return self._next("revision", self._revisions)

    @property
    def digest(self) -> str:
        return self._next("digest", self._digests)

    @property
    def accepted_evidence_ids(self) -> tuple[str, ...]:
        return self._next("accepted_evidence_ids", self._accepted)

    @property
    def events(self) -> tuple[object, ...]:
        return self._next("events", self._events)

    def verify_current(self, *args: object, **kwargs: object) -> None:
        self.verify_calls += 1
        raise AssertionError("release gate must not call verify_current")


# --------------------------------------------------------------------------- #
# Assertion helpers.
# --------------------------------------------------------------------------- #
def assert_blocked(
    decision: Any,
    *,
    reason: str,
    flags: tuple[bool, bool, bool, bool, bool],
) -> None:
    assert decision.status == "blocked"
    assert decision.status != "released"
    assert decision.reason_codes == (reason,)
    actual = (
        decision.snapshot_check_passed,
        decision.review_check_passed,
        decision.evidence_check_passed,
        decision.citation_check_passed,
        decision.answer_check_passed,
    )
    assert actual == flags, f"unexpected check flags for {reason}: {actual!r}"
    assert decision.decided_at == CHECK_TIME


def chained_cause(error: BaseException) -> BaseException | None:
    return error.__cause__ or error.__context__


def assert_input_error(
    call: Callable[[], Any], *, cause: type[BaseException] | None = None
) -> Any:
    with pytest.raises(release_symbol("ReleaseInputError")) as excinfo:
        call()
    if cause is not None:
        assert isinstance(chained_cause(excinfo.value), cause)
    return excinfo.value


def valid_draft_for(projection: Any, snapshot: Any, evidence_id: str) -> Any:
    return make_draft(
        snapshot=snapshot,
        approved=(evidence_id,),
        sent=(evidence_id,),
        citation=(evidence_id,),
        review_revision=projection.revision,
        review_digest=projection.digest,
    )


# --------------------------------------------------------------------------- #
# Prerequisite: the future module and its two public names.
# --------------------------------------------------------------------------- #
def test_release_gate_module_prerequisite() -> None:
    """The only explicit prerequisite assertion: exact module absence is RED."""
    module = release_module()
    assert getattr(module, "ReleaseGate", None) is not None
    assert getattr(module, "ReleaseInputError", None) is not None


# --------------------------------------------------------------------------- #
# 1. Contract revalidation and non-draft gate.
# --------------------------------------------------------------------------- #
def test_malformed_instantiated_draft_raises_contract_validation_error() -> None:
    """FR-D-02/QA-01: revalidate before any trusted read, even for instances."""
    release_module()
    snapshot, _, _, evidence_a, _ = synthetic_corpus()
    draft_type = contract_symbol("AnswerDraft")
    malformed = draft_type.model_construct(
        schema_version=1,
        answer_id=ANSWER_ID,
        snapshot_id=snapshot.snapshot_id,
        question_id=QUESTION_ID,
        review_revision=0,
        review_digest=DIGEST_ONE,
        approved_evidence_ids=(evidence_a.evidence_id,),
        sent_evidence_ids=(evidence_a.evidence_id,),
        citation_evidence_ids=(evidence_a.evidence_id,),
        status="draft",
        body="Synthetic body.",
        refusal_reason=None,
        generated_at=GENERATED_AT,
    )
    assert isinstance(malformed, draft_type)
    with pytest.raises(ValidationError):
        draft_type.model_validate(malformed)

    current = NeverReadCurrent()
    with pytest.raises(ValidationError) as excinfo:
        make_gate(current).check(draft=malformed)
    assert not isinstance(excinfo.value, release_symbol("ReleaseInputError"))
    assert current.reads == []


@pytest.mark.parametrize("legacy_status", ["abstained", "failed"])
def test_legacy_answer_service_result_blocks_without_reading_current(
    tmp_path: Path, legacy_status: str
) -> None:
    """FR-D-01/INV-01: a real legacy non-draft is not releasable; zero reads."""
    release_module()
    snapshot, _, _, evidence_a, evidence_b = synthetic_corpus()
    ledger = make_real_ledger(tmp_path, snapshot, (evidence_a, evidence_b))
    request = answer_symbol("AnswerRequest")(
        snapshot=snapshot,
        question_id=QUESTION_ID,
        answer_id=ANSWER_ID,
        requested_at=GENERATED_AT,
        evidence=(evidence_a, evidence_b),
    )
    if legacy_status == "failed":
        projection = commit(
            ledger, evidence_a.evidence_id, action="accept", expected_revision=0
        )
        assert projection.accepted_evidence_ids == (evidence_a.evidence_id,)
    service = answer_symbol("AnswerService")(
        projections=LedgerProjectionPort(ledger)
    )
    draft = service.prepare(request)
    assert draft.status == legacy_status

    current = NeverReadCurrent()
    decision = make_gate(current).check(draft=draft)
    assert_blocked(
        decision, reason="DRAFT_NOT_RELEASABLE", flags=(False, False, False, False, False)
    )
    assert decision.answer_id == draft.answer_id
    assert decision.snapshot_id == draft.snapshot_id
    assert decision.question_id == draft.question_id
    assert decision.review_revision == draft.review_revision
    assert decision.review_digest == draft.review_digest
    assert current.reads == []


# --------------------------------------------------------------------------- #
# 2. All checks pass: D still does not release; E owns persistence.
# --------------------------------------------------------------------------- #
def test_all_checks_pass_blocks_with_publication_commit_unavailable(
    tmp_path: Path,
) -> None:
    """FR-D-02/INV-04: all five checks pass but D never returns released."""
    release_module()
    snapshot, _, _, evidence_a, evidence_b = synthetic_corpus()
    ledger = make_real_ledger(tmp_path, snapshot, (evidence_a, evidence_b))
    projection = commit(
        ledger, evidence_a.evidence_id, action="accept", expected_revision=0
    )
    draft = valid_draft_for(projection, snapshot, evidence_a.evidence_id)
    current = FixedCurrent((snapshot, projection, (evidence_a, evidence_b)))
    clock = FixedClock()
    gate = make_gate(current, clock)
    ledger_bytes = {path.name: path.read_bytes() for path in tmp_path.glob("*.jsonl")}
    files_before = sorted(path.name for path in tmp_path.iterdir())
    draft_before = draft.model_dump()

    decision = gate.check(draft=draft)

    assert_blocked(
        decision,
        reason="PUBLICATION_COMMIT_UNAVAILABLE",
        flags=(True, True, True, True, True),
    )
    release_decision_type = contract_symbol("ReleaseDecision")
    assert isinstance(decision, release_decision_type)
    assert release_decision_type.model_validate_json(decision.model_dump_json()) == decision
    assert decision.answer_id == draft.answer_id
    assert decision.snapshot_id == draft.snapshot_id
    assert decision.question_id == draft.question_id
    assert decision.review_revision == draft.review_revision
    assert decision.review_digest == draft.review_digest
    assert decision.decided_at == CHECK_TIME
    assert clock.calls == 1
    assert current.reads == [QUESTION_ID]
    assert draft.model_dump() == draft_before
    assert {path.name: path.read_bytes() for path in tmp_path.glob("*.jsonl")} == ledger_bytes
    assert sorted(path.name for path in tmp_path.iterdir()) == files_before


# --------------------------------------------------------------------------- #
# 3. Snapshot, review, evidence and citation stage negatives.
# --------------------------------------------------------------------------- #
def test_snapshot_scope_mismatch_blocks_before_projection_assessment() -> None:
    """FR-D-02/INV-04: snapshot identity is compared before trusted projection reads."""
    release_module()
    snapshot, _, _, evidence_a, _ = synthetic_corpus()
    foreign, foreign_evidence = foreign_snapshot()
    draft = make_draft(
        snapshot=snapshot,
        approved=(evidence_a.evidence_id,),
        sent=(evidence_a.evidence_id,),
        citation=(evidence_a.evidence_id,),
        review_revision=1,
        review_digest=DIGEST_ONE,
    )
    current = FixedCurrent((foreign, ExplodingProjection(), (foreign_evidence,)))

    decision = make_gate(current).check(draft=draft)

    assert_blocked(
        decision,
        reason="SNAPSHOT_SCOPE_MISMATCH",
        flags=(False, False, False, False, True),
    )
    assert decision.snapshot_id == draft.snapshot_id
    assert decision.review_revision == draft.review_revision
    assert decision.review_digest == draft.review_digest
    assert current.reads == [QUESTION_ID]


@pytest.mark.parametrize("scope_case", ["snapshot", "question"])
def test_projection_scope_mismatch_maps_to_review_scope_mismatch(
    scope_case: str,
) -> None:
    """FR-D-02/INV-04: ProjectionScopeMismatchError becomes the blocked outcome."""
    release_module()
    snapshot, _, _, evidence_a, _ = synthetic_corpus()
    foreign, _ = foreign_snapshot()
    if scope_case == "snapshot":
        projection = projection_for(snapshot, snapshot_id=foreign.snapshot_id)
    else:
        projection = projection_for(snapshot, question_id=OTHER_QUESTION_ID)
    draft = make_draft(
        snapshot=snapshot,
        approved=(evidence_a.evidence_id,),
        sent=(evidence_a.evidence_id,),
        citation=(evidence_a.evidence_id,),
        review_revision=projection.revision,
        review_digest=projection.digest,
    )
    current = FixedCurrent((snapshot, projection, (evidence_a,)))

    decision = make_gate(current).check(draft=draft)

    assert_blocked(
        decision,
        reason="REVIEW_SCOPE_MISMATCH",
        flags=(True, False, False, False, True),
    )
    assert current.reads == [QUESTION_ID]


def test_review_revision_is_checked_before_digest(tmp_path: Path) -> None:
    """FR-D-02/INV-04: revision first, then digest; both use validated tokens."""
    release_module()
    snapshot, _, _, evidence_a, evidence_b = synthetic_corpus()
    ledger = make_real_ledger(tmp_path, snapshot, (evidence_a, evidence_b))
    first = commit(ledger, evidence_a.evidence_id, action="accept", expected_revision=0)
    draft_one = valid_draft_for(first, snapshot, evidence_a.evidence_id)
    second = commit(ledger, evidence_a.evidence_id, action="exclude", expected_revision=1)
    assert second.revision == 2
    assert second.accepted_evidence_ids == ()
    current = LedgerCurrent(ledger, snapshot, (evidence_a, evidence_b))
    gate = make_gate(current)

    stale = gate.check(draft=draft_one)
    assert_blocked(
        stale,
        reason="REVIEW_REVISION_STALE",
        flags=(True, False, False, False, True),
    )
    assert stale.review_revision == draft_one.review_revision
    assert stale.review_digest == draft_one.review_digest

    digest_only = make_draft(
        snapshot=snapshot,
        approved=(evidence_a.evidence_id,),
        sent=(evidence_a.evidence_id,),
        citation=(evidence_a.evidence_id,),
        review_revision=second.revision,
        review_digest=first.digest,
    )
    mismatched = gate.check(draft=digest_only)
    assert_blocked(
        mismatched,
        reason="REVIEW_DIGEST_MISMATCH",
        flags=(True, False, False, False, True),
    )
    assert mismatched.review_revision == digest_only.review_revision
    assert mismatched.review_digest == digest_only.review_digest
    assert current.reads == [QUESTION_ID, QUESTION_ID]


@pytest.mark.parametrize(
    ("action", "with_citation"),
    [("reset", False), ("exclude", True)],
    ids=["reset-with-empty-citation", "exclude-with-citation"],
)
def test_historical_approved_id_outside_new_trusted_set_is_evidence_scope(
    tmp_path: Path, action: str, with_citation: bool
) -> None:
    """FR-D-02/INV-04: a structurally valid stale approved set fails evidence scope."""
    release_module()
    snapshot, _, _, evidence_a, evidence_b = synthetic_corpus()
    ledger = make_real_ledger(tmp_path, snapshot, (evidence_a, evidence_b))
    commit(ledger, evidence_a.evidence_id, action="accept", expected_revision=0)
    projection = commit(
        ledger, evidence_a.evidence_id, action=action, expected_revision=1
    )
    assert projection.accepted_evidence_ids == ()
    citation = (evidence_a.evidence_id,) if with_citation else ()
    draft = make_draft(
        snapshot=snapshot,
        approved=(evidence_a.evidence_id,),
        sent=(evidence_a.evidence_id,),
        citation=citation,
        review_revision=projection.revision,
        review_digest=projection.digest,
    )
    current = FixedCurrent((snapshot, projection, (evidence_a, evidence_b)))

    decision = make_gate(current).check(draft=draft)

    assert_blocked(
        decision,
        reason="EVIDENCE_SCOPE_MISMATCH",
        flags=(True, True, False, False, True),
    )
    assert decision.review_revision == projection.revision
    assert decision.review_digest == projection.digest
    assert current.reads == [QUESTION_ID]


def test_draft_claimed_foreign_provenance_is_evidence_provenance_invalid(
    tmp_path: Path,
) -> None:
    """FR-D-02/INV-02: claimed evidence with foreign provenance is not traceable."""
    release_module()
    snapshot, _, _, evidence_a, evidence_b = synthetic_corpus()
    foreign, foreign_evidence = foreign_snapshot()
    assert foreign.snapshot_id != snapshot.snapshot_id
    ledger = make_real_ledger(tmp_path, snapshot, (evidence_a, evidence_b))
    projection = commit(
        ledger, evidence_a.evidence_id, action="accept", expected_revision=0
    )
    draft = make_draft(
        snapshot=snapshot,
        approved=(foreign_evidence.evidence_id,),
        sent=(foreign_evidence.evidence_id,),
        citation=(foreign_evidence.evidence_id,),
        review_revision=projection.revision,
        review_digest=projection.digest,
    )
    current = FixedCurrent(
        (snapshot, projection, (evidence_a, evidence_b, foreign_evidence))
    )

    decision = make_gate(current).check(draft=draft)

    assert_blocked(
        decision,
        reason="EVIDENCE_PROVENANCE_INVALID",
        flags=(True, True, False, False, True),
    )
    assert current.reads == [QUESTION_ID]


def test_empty_citation_is_not_traceable(tmp_path: Path) -> None:
    """FR-D-02/INV-04: an explicit empty-citation draft is blocked, not released."""
    release_module()
    snapshot, _, _, evidence_a, evidence_b = synthetic_corpus()
    ledger = make_real_ledger(tmp_path, snapshot, (evidence_a, evidence_b))
    projection = commit(
        ledger, evidence_a.evidence_id, action="accept", expected_revision=0
    )
    draft = make_draft(
        snapshot=snapshot,
        approved=(evidence_a.evidence_id,),
        sent=(evidence_a.evidence_id,),
        citation=(),
        review_revision=projection.revision,
        review_digest=projection.digest,
    )
    current = FixedCurrent((snapshot, projection, (evidence_a, evidence_b)))

    decision = make_gate(current).check(draft=draft)

    assert_blocked(
        decision,
        reason="NO_TRACEABLE_CITATION",
        flags=(True, True, True, False, True),
    )
    assert current.reads == [QUESTION_ID]


# --------------------------------------------------------------------------- #
# 4. Input errors: malformed bundle, projection shape, membership, provenance.
# --------------------------------------------------------------------------- #
def test_projection_shape_error_becomes_release_input_error() -> None:
    """FR-D-02: assess_eligibility shape failure is an input error, not a decision."""
    release_module()
    snapshot, _, _, evidence_a, _ = synthetic_corpus()
    projection = SimpleNamespace(
        snapshot_id=snapshot.snapshot_id,
        question_id=QUESTION_ID,
        digest=DIGEST_ONE,
        accepted_evidence_ids=(),
        events=(),
    )
    draft = make_draft(
        snapshot=snapshot,
        approved=(evidence_a.evidence_id,),
        sent=(evidence_a.evidence_id,),
        citation=(evidence_a.evidence_id,),
        review_revision=1,
        review_digest=DIGEST_ONE,
    )
    current = FixedCurrent((snapshot, projection, (evidence_a,)))

    assert_input_error(
        lambda: make_gate(current).check(draft=draft),
        cause=answer_symbol("ProjectionShapeError"),
    )

    assert current.reads == [QUESTION_ID]


def test_unknown_current_accepted_id_becomes_release_input_error() -> None:
    """FR-D-02: a trusted accepted ID absent from the captured evidence is input error."""
    release_module()
    snapshot, _, _, evidence_a, _ = synthetic_corpus()
    stranger = "ev-" + "f" * 64
    projection = projection_for(snapshot, accepted=(stranger,))
    draft = make_draft(
        snapshot=snapshot,
        approved=(evidence_a.evidence_id,),
        sent=(evidence_a.evidence_id,),
        citation=(evidence_a.evidence_id,),
        review_revision=projection.revision,
        review_digest=projection.digest,
    )
    current = FixedCurrent((snapshot, projection, (evidence_a,)))

    assert_input_error(
        lambda: make_gate(current).check(draft=draft),
        cause=answer_symbol("UnknownAcceptedEvidenceError"),
    )
    assert current.reads == [QUESTION_ID]


def test_trusted_accepted_foreign_provenance_becomes_release_input_error() -> None:
    """FR-D-02/INV-02: invalid provenance of current trusted evidence is input error."""
    release_module()
    snapshot, _, _, evidence_a, _ = synthetic_corpus()
    _, foreign_evidence = foreign_snapshot()
    projection = projection_for(
        snapshot, accepted=(foreign_evidence.evidence_id,)
    )
    draft = make_draft(
        snapshot=snapshot,
        approved=(evidence_a.evidence_id,),
        sent=(evidence_a.evidence_id,),
        citation=(evidence_a.evidence_id,),
        review_revision=projection.revision,
        review_digest=projection.digest,
    )
    current = FixedCurrent((snapshot, projection, (evidence_a, foreign_evidence)))

    assert_input_error(
        lambda: make_gate(current).check(draft=draft),
        cause=answer_symbol("EvidenceProvenanceError"),
    )
    assert current.reads == [QUESTION_ID]


@pytest.mark.parametrize(
    "case",
    ["two-tuple", "none-evidence", "none-snapshot"],
)
def test_malformed_bundle_becomes_release_input_error(case: str) -> None:
    """FR-D-02: a malformed captured bundle is a typed input error, not a decision."""
    release_module()
    snapshot, _, _, evidence_a, _ = synthetic_corpus()
    projection = projection_for(snapshot, accepted=(evidence_a.evidence_id,))
    draft = valid_draft_for(projection, snapshot, evidence_a.evidence_id)
    if case == "two-tuple":
        captured: object = (snapshot, projection)
    elif case == "none-evidence":
        captured = (snapshot, projection, None)
    else:
        captured = (None, projection, (evidence_a,))
    current = FixedCurrent(captured)

    assert_input_error(lambda: make_gate(current).check(draft=draft))
    assert current.reads == [QUESTION_ID]


# --------------------------------------------------------------------------- #
# 5. Propagation and no fallback.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "error",
    [PermissionError("synthetic permission denied"), OSError("synthetic io failure")],
    ids=["permission", "oserror"],
)
def test_port_errors_propagate_unchanged(error: OSError) -> None:
    """FR-D-02: port I/O failures propagate as the same object; no draft or fallback."""
    release_module()
    snapshot, _, _, evidence_a, _ = synthetic_corpus()
    draft = make_draft(
        snapshot=snapshot,
        approved=(evidence_a.evidence_id,),
        sent=(evidence_a.evidence_id,),
        citation=(evidence_a.evidence_id,),
        review_revision=1,
        review_digest=DIGEST_ONE,
    )
    current = FixedCurrent(error)

    with pytest.raises(type(error)) as excinfo:
        make_gate(current).check(draft=draft)

    assert excinfo.value is error
    assert current.reads == [QUESTION_ID]


def test_real_corrupted_ledger_propagates_without_repair(tmp_path: Path) -> None:
    """FR-D-02/INV-04: a real corrupted C ledger propagates; D does not repair it."""
    release_module()
    snapshot, _, _, evidence_a, evidence_b = synthetic_corpus()
    ledger = make_real_ledger(tmp_path, snapshot, (evidence_a, evidence_b))
    projection = commit(
        ledger, evidence_a.evidence_id, action="accept", expected_revision=0
    )
    draft = valid_draft_for(projection, snapshot, evidence_a.evidence_id)
    files = sorted(tmp_path.glob("*.jsonl"))
    assert len(files) == 1
    path = files[0]
    path.write_bytes(path.read_bytes()[:-10])
    before = path.read_bytes()
    current = LedgerCurrent(ledger, snapshot, (evidence_a, evidence_b))

    with pytest.raises(review_symbol("ReviewLedgerCorrupted")):
        make_gate(current).check(draft=draft)

    assert current.reads == [QUESTION_ID]
    assert path.read_bytes() == before


def test_gate_does_not_retry_a_malformed_bundle() -> None:
    """FR-D-02: one captured read; a malformed bundle is not retried or replaced."""
    release_module()
    snapshot, _, _, evidence_a, _ = synthetic_corpus()
    projection = projection_for(snapshot, accepted=(evidence_a.evidence_id,))
    draft = valid_draft_for(projection, snapshot, evidence_a.evidence_id)
    current = SequenceCurrent(
        [
            (snapshot, projection),
            (snapshot, projection, (evidence_a,)),
        ]
    )

    assert_input_error(lambda: make_gate(current).check(draft=draft))
    assert current.reads == [QUESTION_ID]


def test_gate_uses_only_the_first_captured_bundle() -> None:
    """FR-D-02/INV-04: no second read for freshness; the captured bundle is final."""
    release_module()
    snapshot, _, _, evidence_a, _ = synthetic_corpus()
    first = projection_for(snapshot, accepted=(evidence_a.evidence_id,))
    second = projection_for(
        snapshot,
        revision=2,
        digest=DIGEST_TWO,
        accepted=(),
    )
    draft = valid_draft_for(first, snapshot, evidence_a.evidence_id)
    current = SequenceCurrent(
        [
            (snapshot, first, (evidence_a,)),
            (snapshot, second, (evidence_a,)),
        ]
    )

    decision = make_gate(current).check(draft=draft)

    assert_blocked(
        decision,
        reason="PUBLICATION_COMMIT_UNAVAILABLE",
        flags=(True, True, True, True, True),
    )
    assert decision.review_revision == first.revision
    assert decision.review_digest == first.digest
    assert current.reads == [QUESTION_ID]


def test_changing_projection_exposes_duplicate_reads() -> None:
    """FR-D-02/INV-04: revision, digest and accepted membership are read once."""
    release_module()
    snapshot, _, _, evidence_a, _ = synthetic_corpus()
    trap = TrapProjection(
        snapshot_id=snapshot.snapshot_id,
        question_id=QUESTION_ID,
        revisions=(1, 2),
        digests=(DIGEST_ONE, DIGEST_TWO),
        accepted=((evidence_a.evidence_id,), ()),
        events=((object(),), ()),
    )
    draft = make_draft(
        snapshot=snapshot,
        approved=(evidence_a.evidence_id,),
        sent=(evidence_a.evidence_id,),
        citation=(evidence_a.evidence_id,),
        review_revision=1,
        review_digest=DIGEST_ONE,
    )
    current = FixedCurrent((snapshot, trap, (evidence_a,)))

    decision = make_gate(current).check(draft=draft)

    assert_blocked(
        decision,
        reason="PUBLICATION_COMMIT_UNAVAILABLE",
        flags=(True, True, True, True, True),
    )
    assert decision.review_revision == 1
    assert decision.review_digest == DIGEST_ONE
    assert trap.read_counts == {
        "revision": 1,
        "digest": 1,
        "accepted_evidence_ids": 1,
        "snapshot_id": 1,
        "question_id": 1,
        "events": 1,
    }
    assert trap.verify_calls == 0
    assert current.reads == [QUESTION_ID]


# --------------------------------------------------------------------------- #
# 6. Sequential state and immutability of a returned decision.
# --------------------------------------------------------------------------- #
def test_sequential_ledger_changes_do_not_mutate_returned_decision(
    tmp_path: Path,
) -> None:
    """INV-04: two checks on one gate see state changes; old decision is immutable."""
    release_module()
    snapshot, _, _, evidence_a, evidence_b = synthetic_corpus()
    ledger = make_real_ledger(tmp_path, snapshot, (evidence_a, evidence_b))
    first = commit(ledger, evidence_a.evidence_id, action="accept", expected_revision=0)
    draft_one = valid_draft_for(first, snapshot, evidence_a.evidence_id)
    current = LedgerCurrent(ledger, snapshot, (evidence_a, evidence_b))
    clock = FixedClock()
    gate = make_gate(current, clock)

    decision_one = gate.check(draft=draft_one)
    assert_blocked(
        decision_one,
        reason="PUBLICATION_COMMIT_UNAVAILABLE",
        flags=(True, True, True, True, True),
    )
    decision_one_snapshot = decision_one.model_dump()
    assert current.reads == [QUESTION_ID]

    second = commit(ledger, evidence_a.evidence_id, action="reset", expected_revision=1)
    assert second.revision == 2
    assert second.accepted_evidence_ids == ()

    decision_two = gate.check(draft=draft_one)
    assert_blocked(
        decision_two,
        reason="REVIEW_REVISION_STALE",
        flags=(True, False, False, False, True),
    )
    assert decision_two.review_revision == draft_one.review_revision
    assert decision_two.review_digest == draft_one.review_digest
    assert current.reads == [QUESTION_ID, QUESTION_ID]
    assert decision_one.model_dump() == decision_one_snapshot
    assert decision_one.status == "blocked"
    assert decision_one.reason_codes == ("PUBLICATION_COMMIT_UNAVAILABLE",)

    draft_after_reset = make_draft(
        snapshot=snapshot,
        approved=(evidence_a.evidence_id,),
        sent=(evidence_a.evidence_id,),
        citation=(evidence_a.evidence_id,),
        review_revision=second.revision,
        review_digest=second.digest,
    )
    decision_three = gate.check(draft=draft_after_reset)
    assert_blocked(
        decision_three,
        reason="EVIDENCE_SCOPE_MISMATCH",
        flags=(True, True, False, False, True),
    )
    assert decision_three.review_revision == draft_after_reset.review_revision
    assert decision_three.review_digest == draft_after_reset.review_digest
    assert current.reads == [QUESTION_ID, QUESTION_ID, QUESTION_ID]
    assert clock.calls == 3
    assert decision_one.model_dump() == decision_one_snapshot


# --------------------------------------------------------------------------- #
# 7. Contract-revalidation cases that cannot be runtime negatives.
# --------------------------------------------------------------------------- #
def test_impossible_sent_and_citation_relations_are_contract_errors() -> None:
    """QA-01/INV-04: sent outside approved and cited outside sent never reach D."""
    release_module()
    snapshot, _, _, evidence_a, evidence_b = synthetic_corpus()
    draft_type = contract_symbol("AnswerDraft")
    common = {
        "schema_version": 1,
        "answer_id": ANSWER_ID,
        "snapshot_id": snapshot.snapshot_id,
        "question_id": QUESTION_ID,
        "review_revision": 1,
        "review_digest": DIGEST_ONE,
        "status": "draft",
        "body": "Synthetic body.",
        "generated_at": GENERATED_AT,
    }
    with pytest.raises(ValidationError):
        draft_type(
            **common,
            approved_evidence_ids=(evidence_a.evidence_id,),
            sent_evidence_ids=(evidence_b.evidence_id,),
            citation_evidence_ids=(),
        )
    with pytest.raises(ValidationError):
        draft_type(
            **common,
            approved_evidence_ids=(evidence_a.evidence_id,),
            sent_evidence_ids=(evidence_a.evidence_id,),
            citation_evidence_ids=(evidence_b.evidence_id,),
        )

    malformed = draft_type.model_construct(
        **common,
        approved_evidence_ids=(evidence_a.evidence_id,),
        sent_evidence_ids=(evidence_b.evidence_id,),
        citation_evidence_ids=(),
        refusal_reason=None,
    )
    current = NeverReadCurrent()
    with pytest.raises(ValidationError):
        make_gate(current).check(draft=malformed)
    assert current.reads == []


# --------------------------------------------------------------------------- #
# 8. Import isolation: a fresh interpreter, not the rest of this test process.
# --------------------------------------------------------------------------- #
def test_release_module_source_does_not_import_paperqa() -> None:
    """FR-D-03 (structural supplement): D's release module has no paperqa import."""
    module = release_module()
    source = Path(module.__file__).read_text(encoding="utf-8")
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                continue
            names = [node.module]
        else:
            continue
        found.extend(
            name for name in names if name == "paperqa" or name.startswith("paperqa.")
        )
    assert found == []


def test_release_import_is_isolated_from_paperqa_in_a_fresh_interpreter() -> None:
    """COST-01/FR-D-03: a child interpreter imports D without importing PaperQA."""
    release_module()
    code = (
        "import sys\n"
        "import papertrace.answer.release\n"
        "print('paperqa' in sys.modules)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_ROOT / "src",
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "False"
