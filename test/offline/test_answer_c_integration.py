"""Module D: C review-ledger projection through a thin D-local adapter (proposal).

Traceability: FR-D-01, FR-D-02 (partial), FR-D-03 (partial), INV-01, INV-03,
INV-04, QA-01, COST-01.

This file belongs to the local publication-preparation stage that the supervising
side reports as authorized for tests/design only (2026-11-21, continued
2026-11-22 HKT); it is not itself an approval record. It fixes the proposed
D-local interface
``papertrace.answer.c_adapter.CReviewProjectionAdapter(*, ledger=ReviewLedger)``
with ``read_projection(question_id)`` returning C's own ``ReviewProjection`` for
that question. That name is a testable D-local interface proposal, not an
implementation and not a new shared contract; there is no fallback stub.

The real D package is resolved only during test/helper execution, never at
collection. A source-free checkout therefore collects normally and fails each
test with an ordinary missing-prerequisite assertion; an approved-D checkout
without ``papertrace.answer.c_adapter`` instead fails its behavior tests at the
explicit adapter-availability assertion. Only an exact
``ModuleNotFoundError.name`` of ``papertrace.answer`` (missing D) or
``papertrace.answer.c_adapter`` (missing adapter, after real C/D origin checks)
is classified; every other import error is re-raised unchanged.

Every ledger here is synthetic and created at runtime under ``tmp_path`` through
C's real ``prepare_decision``/``commit_decision`` path. Revision and digest values
are always compared with C's own projection, never recomputed or invented.
Synthetic reviewer references are runtime test data, never GitHub approval. These
tests make no PaperTrace product-model, live-retrieval or real semantic
invocation and no product SDK/network call; the coding-assistant session that
edited them is a separate development-tool concern.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from papertrace.contracts import (
    AnswerDraft,
    ContractModel,
    CorpusSnapshot,
    DocumentVersion,
    EvidenceRecord,
    SourceLocator,
)
from papertrace.review import ReviewLedger, ReviewLedgerCorrupted, ReviewProjection

QUESTION_ONE = "q-c-integration-1"
QUESTION_TWO = "q-c-integration-2"
ANSWER_ID_ONE = "ans-c-integration-1"
ANSWER_ID_TWO = "ans-c-integration-2"
REQUESTED_AT = datetime(2026, 11, 21, 0, 0, tzinfo=timezone.utc)
# Synthetic runtime reviewer reference; it is not a GitHub account or an approval.
SYNTHETIC_REVIEWER = "reviewer-SYNTHETIC-C"
EVIDENCE_LINE_NUMBERS = (2, 3)

EXPECTED_ADAPTER_RED = (
    "expected RED: papertrace.answer.c_adapter is not implemented yet; the import "
    "failure was ModuleNotFoundError with name exactly 'papertrace.answer.c_adapter'"
)

MISSING_D_PREREQUISITE = (
    "prerequisite missing: the real module 'papertrace.answer' (Module D) is not "
    "present in this checkout; this is the missing-D prerequisite, distinct from "
    "the missing 'papertrace.answer.c_adapter' expected RED, and no C-to-D "
    "integration behavior was executed"
)


def expected_module_paths() -> dict[str, Path]:
    """Resolve this checkout's expected C/D module files from the test file itself."""
    root = Path(__file__).resolve().parents[2]
    source = root / "src" / "papertrace"
    return {
        "papertrace.answer": source / "answer" / "__init__.py",
        "papertrace.answer.service": source / "answer" / "service.py",
        "papertrace.review": source / "review" / "__init__.py",
        "papertrace.review.service": source / "review" / "service.py",
    }


def module_path(module: ModuleType) -> Path:
    """Return an imported module's real file; a missing ``__file__`` fails visibly."""
    module_file = module.__file__
    assert module_file is not None, f"{module.__name__} has no __file__"
    return Path(module_file).resolve()


def load_answer_package() -> ModuleType:
    """Load real module D at execution time; only the exact missing package is RED.

    Collection stays safe on a source-free checkout because this import never runs
    at module import time. A missing submodule or third-party dependency is a real
    import failure and propagates unchanged.
    """
    try:
        return import_module("papertrace.answer")
    except ModuleNotFoundError as error:
        if error.name != "papertrace.answer":
            raise
        raise AssertionError(MISSING_D_PREREQUISITE) from error


def verified_project_modules() -> dict[str, ModuleType]:
    """Import real C/D and prove all four files resolve inside this checkout.

    This runs during test/helper execution, after D is loaded and before any
    adapter probe, so a source-free checkout reaches the missing-D assertion
    rather than a collection-time error or an origin check mistaken for adapter RED.
    """
    answer_package = load_answer_package()
    modules: dict[str, ModuleType] = {
        "papertrace.answer": answer_package,
        "papertrace.answer.service": import_module("papertrace.answer.service"),
        "papertrace.review": import_module("papertrace.review"),
        "papertrace.review.service": import_module("papertrace.review.service"),
    }
    expected = expected_module_paths()
    for name, path in expected.items():
        actual = module_path(modules[name])
        assert actual == path.resolve(), f"{name} resolved to {actual}, not {path}"
    return modules


@dataclass(frozen=True)
class AnswerSymbols:
    """Real D exports resolved during execution, after the C/D origin preflight.

    Every field is the actual object exported by ``papertrace.answer``; this is a
    test-local resolution record, not a fallback module or substitute contract.
    """

    answer_service: type[Any]
    answer_request: type[Any]
    preparation_error: type[BaseException]
    scope_mismatch_error: type[BaseException]
    refusal_no_approved_evidence: str
    refusal_generation_path_not_enabled: str


def exported_symbol(package: ModuleType, name: str) -> Any:
    """Resolve one real D export or fail visibly as an interface problem."""
    value = getattr(package, name, None)
    assert value is not None, f"real papertrace.answer does not export {name}"
    return value


def require_answer_api() -> AnswerSymbols:
    """Resolve real D exports only during execution, after verifying C/D origin."""
    modules = verified_project_modules()
    package = modules["papertrace.answer"]
    refusal_no_approved = exported_symbol(package, "REFUSAL_NO_APPROVED_EVIDENCE")
    refusal_generation = exported_symbol(package, "REFUSAL_GENERATION_PATH_NOT_ENABLED")
    assert isinstance(refusal_no_approved, str)
    assert isinstance(refusal_generation, str)
    return AnswerSymbols(
        answer_service=exported_symbol(package, "AnswerService"),
        answer_request=exported_symbol(package, "AnswerRequest"),
        preparation_error=exported_symbol(package, "AnswerPreparationError"),
        scope_mismatch_error=exported_symbol(package, "ProjectionScopeMismatchError"),
        refusal_no_approved_evidence=refusal_no_approved,
        refusal_generation_path_not_enabled=refusal_generation,
    )


@dataclass(frozen=True)
class AdapterProbe:
    """Result of the post-preflight adapter import; absence is never a skip."""

    module: ModuleType | None
    import_error: ModuleNotFoundError | None


def probe_adapter() -> AdapterProbe:
    """Probe the proposed adapter only after the real C/D origin preflight."""
    verified_project_modules()
    try:
        module = import_module("papertrace.answer.c_adapter")
    except ModuleNotFoundError as error:
        if error.name != "papertrace.answer.c_adapter":
            raise
        return AdapterProbe(module=None, import_error=error)
    return AdapterProbe(module=module, import_error=None)


def adapter_module() -> ModuleType:
    """Return the proposed D-local adapter module, or fail as expected product RED."""
    probe = probe_adapter()
    assert probe.module is not None, EXPECTED_ADAPTER_RED
    return probe.module


def build_adapter(ledger: ReviewLedger) -> Any:
    """Instantiate the planned interface; a missing class is a real interface failure."""
    factory = getattr(adapter_module(), "CReviewProjectionAdapter", None)
    assert factory is not None, (
        "planned interface papertrace.answer.c_adapter.CReviewProjectionAdapter is missing"
    )
    return factory(ledger=ledger)


@dataclass(frozen=True)
class SyntheticCorpus:
    """One synthetic snapshot plus its contract-valid evidence candidates."""

    snapshot: CorpusSnapshot
    evidence: tuple[EvidenceRecord, ...]


def assert_contract_roundtrip(*models: ContractModel) -> None:
    """QA-01: fixture objects must survive the shared JSON contract unchanged."""
    for model in models:
        assert type(model).model_validate_json(model.model_dump_json()) == model


def document_specs(label: str) -> tuple[tuple[str, str, tuple[str, ...]], ...]:
    """Two synthetic documents, two excerpt lines each, per corpus label."""
    tag = label.upper()
    return (
        (
            f"doc-synthetic-{label}-primary",
            f"synthetic-{label}-primary.txt",
            (
                f"Synthetic corpus {tag} primary - header line.",
                f"Claim {tag} P1: only a synthetic human command may accept this excerpt.",
                f"Claim {tag} P2: synthetic excerpt left pending in the mixed case.",
                f"Synthetic corpus {tag} primary - footer line.",
            ),
        ),
        (
            f"doc-synthetic-{label}-secondary",
            f"synthetic-{label}-secondary.txt",
            (
                f"Synthetic corpus {tag} secondary - header line.",
                f"Claim {tag} S1: second document in the same synthetic snapshot.",
                f"Claim {tag} S2: fourth synthetic excerpt for scope and reset cases.",
                f"Synthetic corpus {tag} secondary - footer line.",
            ),
        ),
    )


def build_corpus(tmp_path: Path, label: str) -> SyntheticCorpus:
    """Create a real synthetic corpus and evidence, validated by real contracts."""
    root = tmp_path / f"corpus-{label}"
    root.mkdir(parents=True, exist_ok=True)
    prepared: list[tuple[DocumentVersion, tuple[str, ...]]] = []
    for document_id, filename, lines in document_specs(label):
        path = root / filename
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        document = DocumentVersion(
            schema_version=1,
            document_id=document_id,
            version_sha256=sha256(path.read_bytes()).hexdigest(),
            title=f"Synthetic {label} document {document_id}",
            source_name=path.name,
            status="ready",
        )
        prepared.append((document, lines))

    snapshot = CorpusSnapshot(
        schema_version=1,
        documents=tuple(document for document, _ in prepared),
        created_at=REQUESTED_AT,
    )
    evidence: list[EvidenceRecord] = []
    for document, lines in prepared:
        for line_number in EVIDENCE_LINE_NUMBERS:
            evidence.append(
                EvidenceRecord(
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
                    excerpt=lines[line_number - 1],
                    retrieved_at=REQUESTED_AT,
                )
            )
    corpus = SyntheticCorpus(snapshot=snapshot, evidence=tuple(evidence))
    assert_contract_roundtrip(snapshot)
    assert_contract_roundtrip(*corpus.evidence)
    return corpus


def build_ledger(tmp_path: Path, corpus: SyntheticCorpus) -> ReviewLedger:
    """Bind a real C ledger to the synthetic snapshot and its candidates."""
    return ReviewLedger(
        ledger_root=tmp_path / "ledger",
        snapshot=corpus.snapshot,
        candidates=corpus.evidence,
        clock=lambda: REQUESTED_AT,
    )


def ledger_files(tmp_path: Path) -> tuple[Path, ...]:
    """Discover the actual ledger files C wrote; never reconstruct C's path logic."""
    return tuple(sorted(tmp_path.rglob("*.jsonl")))


def append_decision(
    ledger: ReviewLedger,
    *,
    question_id: str,
    evidence_id: str,
    action: str,
    revision: int,
    reason: str,
) -> ReviewProjection:
    """Real C path: validate a human command, then append exactly one event."""
    intent = ledger.prepare_decision(
        question_id=question_id,
        evidence_id=evidence_id,
        action=action,
        reviewer_ref=SYNTHETIC_REVIEWER,
        reason=reason,
        expected_revision=revision,
        command_id=f"cmd-{question_id}-{revision + 1}",
    )
    return ledger.commit_decision(intent)


def accept_one(
    ledger: ReviewLedger, corpus: SyntheticCorpus, *, reason: str
) -> ReviewProjection:
    """Append one accepted synthetic decision for the first candidate of question one."""
    return append_decision(
        ledger,
        question_id=QUESTION_ONE,
        evidence_id=corpus.evidence[0].evidence_id,
        action="accept",
        revision=ledger.projection(QUESTION_ONE).revision,
        reason=reason,
    )


def build_request(
    corpus: SyntheticCorpus,
    *,
    question_id: str = QUESTION_ONE,
    answer_id: str = ANSWER_ID_ONE,
) -> Any:
    api = require_answer_api()
    return api.answer_request(
        snapshot=corpus.snapshot,
        question_id=question_id,
        answer_id=answer_id,
        requested_at=REQUESTED_AT,
        evidence=corpus.evidence,
    )


def prepare(
    ledger: ReviewLedger,
    corpus: SyntheticCorpus,
    *,
    question_id: str = QUESTION_ONE,
    answer_id: str = ANSWER_ID_ONE,
) -> AnswerDraft:
    """Run the existing D service against the proposed adapter, no model involved."""
    api = require_answer_api()
    service = api.answer_service(projections=build_adapter(ledger))
    return service.prepare(
        build_request(corpus, question_id=question_id, answer_id=answer_id)
    )


def test_real_c_and_d_preflight_imports_resolve_to_this_checkout() -> None:
    """Dependency preflight: imports resolve to this checkout's real C/D files."""
    modules = verified_project_modules()
    expected = expected_module_paths()
    assert set(modules) == {
        "papertrace.answer",
        "papertrace.answer.service",
        "papertrace.review",
        "papertrace.review.service",
    }
    assert module_path(modules["papertrace.review"]) == expected["papertrace.review"].resolve()
    assert module_path(modules["papertrace.answer"]) == expected["papertrace.answer"].resolve()
    assert module_path(modules["papertrace.review.service"]) == expected[
        "papertrace.review.service"
    ].resolve()
    assert module_path(modules["papertrace.answer.service"]) == expected[
        "papertrace.answer.service"
    ].resolve()
    assert ReviewLedger.__module__ == "papertrace.review.service"
    answer_service = exported_symbol(modules["papertrace.answer"], "AnswerService")
    assert answer_service.__module__ == "papertrace.answer.service"


def test_missing_adapter_is_classified_by_exact_module_name() -> None:
    """Correction: only the exact missing module name may be called expected RED."""
    probe = probe_adapter()
    if probe.module is None:
        assert probe.import_error is not None
        assert isinstance(probe.import_error, ModuleNotFoundError)
        assert probe.import_error.name == "papertrace.answer.c_adapter"
    else:
        assert getattr(probe.module, "CReviewProjectionAdapter", None) is not None


def test_adapter_returns_c_projection_for_the_requested_question(tmp_path: Path) -> None:
    """Proposed interface: return C's own projection object for that question only."""
    corpus = build_corpus(tmp_path, "a")
    ledger = build_ledger(tmp_path, corpus)
    accepted = corpus.evidence[0]
    append_decision(
        ledger,
        question_id=QUESTION_ONE,
        evidence_id=accepted.evidence_id,
        action="accept",
        revision=0,
        reason="Synthetic human acceptance for the adapter interface test.",
    )

    adapter = build_adapter(ledger)
    returned = adapter.read_projection(QUESTION_ONE)
    expected = ledger.projection(QUESTION_ONE)

    assert isinstance(returned, ReviewProjection)
    assert not isinstance(returned, dict)
    assert returned.snapshot_id == expected.snapshot_id == corpus.snapshot.snapshot_id
    assert returned.question_id == expected.question_id == QUESTION_ONE
    assert expected.revision == 1
    assert returned.revision == expected.revision
    assert returned.digest == expected.digest
    assert returned.accepted_evidence_ids == expected.accepted_evidence_ids
    assert returned.accepted_evidence_ids == (accepted.evidence_id,)
    assert returned.events == expected.events

    expected_other = ledger.projection(QUESTION_TWO)
    other = adapter.read_projection(QUESTION_TWO)
    assert other.question_id == expected_other.question_id == QUESTION_TWO
    assert other.snapshot_id == expected_other.snapshot_id == corpus.snapshot.snapshot_id
    assert other.revision == expected_other.revision
    assert other.digest == expected_other.digest
    assert other.accepted_evidence_ids == expected_other.accepted_evidence_ids == ()


@pytest.mark.parametrize("ledger_state", ["absent-file", "empty-existing-file"])
def test_empty_or_absent_ledger_abstains_with_real_projection_token(
    tmp_path: Path, ledger_state: str
) -> None:
    """CT-D-01 / FR-D-01, INV-01, INV-04: no review state abstains; absence is no error."""
    corpus = build_corpus(tmp_path, "a")
    ledger = build_ledger(tmp_path, corpus)
    if ledger_state == "empty-existing-file":
        accept_one(ledger, corpus, reason="Synthetic acceptance used to create the file.")
        files = ledger_files(tmp_path)
        assert len(files) == 1
        files[0].write_bytes(b"")
        assert files[0].exists()
        assert files[0].read_bytes() == b""
    else:
        assert ledger_files(tmp_path) == ()

    projection = ledger.projection(QUESTION_ONE)
    assert projection.revision == 0
    assert projection.accepted_evidence_ids == ()

    api = require_answer_api()
    draft = prepare(ledger, corpus)

    assert_contract_roundtrip(draft)
    assert draft.status == "abstained"
    assert draft.refusal_reason == api.refusal_no_approved_evidence
    assert draft.approved_evidence_ids == ()
    assert draft.sent_evidence_ids == ()
    assert draft.citation_evidence_ids == ()
    assert draft.body == ""
    assert draft.review_revision == projection.revision
    assert draft.review_digest == projection.digest


def test_one_accepted_decision_fails_closed_without_generation(tmp_path: Path) -> None:
    """CT-D-02 / FR-D-01, FR-D-03 (partial), INV-04: generation stays disabled."""
    corpus = build_corpus(tmp_path, "a")
    ledger = build_ledger(tmp_path, corpus)
    accepted = corpus.evidence[0]
    projection = append_decision(
        ledger,
        question_id=QUESTION_ONE,
        evidence_id=accepted.evidence_id,
        action="accept",
        revision=0,
        reason="Synthetic human acceptance of exactly one candidate.",
    )
    assert projection.revision == 1
    assert projection.accepted_evidence_ids == (accepted.evidence_id,)

    api = require_answer_api()
    draft = prepare(ledger, corpus)

    assert_contract_roundtrip(draft)
    assert draft.status == "failed"
    assert draft.refusal_reason == api.refusal_generation_path_not_enabled
    assert draft.approved_evidence_ids == projection.accepted_evidence_ids
    assert draft.approved_evidence_ids == (accepted.evidence_id,)
    assert draft.sent_evidence_ids == ()
    assert draft.citation_evidence_ids == ()
    assert draft.body == ""
    assert draft.review_revision == projection.revision
    assert draft.review_digest == projection.digest


def _all_pending_case(ledger: ReviewLedger, corpus: SyntheticCorpus) -> ReviewProjection:
    return ledger.projection(QUESTION_ONE)


def _all_excluded_case(ledger: ReviewLedger, corpus: SyntheticCorpus) -> ReviewProjection:
    projection = ledger.projection(QUESTION_ONE)
    for index, record in enumerate(corpus.evidence):
        projection = append_decision(
            ledger,
            question_id=QUESTION_ONE,
            evidence_id=record.evidence_id,
            action="exclude",
            revision=projection.revision,
            reason=f"Synthetic exclusion number {index + 1} for the all-excluded case.",
        )
    return projection


def _mixed_case(ledger: ReviewLedger, corpus: SyntheticCorpus) -> ReviewProjection:
    projection = ledger.projection(QUESTION_ONE)
    for evidence_id, action in (
        (corpus.evidence[0].evidence_id, "accept"),
        (corpus.evidence[1].evidence_id, "exclude"),
    ):
        projection = append_decision(
            ledger,
            question_id=QUESTION_ONE,
            evidence_id=evidence_id,
            action=action,
            revision=projection.revision,
            reason=f"Synthetic {action} for the mixed accepted/excluded/pending case.",
        )
    return projection


CASE_BUILDERS = {
    "all-pending": (_all_pending_case, "abstained"),
    "all-excluded": (_all_excluded_case, "abstained"),
    "mixed": (_mixed_case, "failed"),
}


@pytest.mark.parametrize("case_id", sorted(CASE_BUILDERS))
def test_only_accepted_evidence_enters_approved(tmp_path: Path, case_id: str) -> None:
    """CT-D-03 / INV-03, INV-04: excluded and pending evidence never enter approved."""
    build_case, expected_status = CASE_BUILDERS[case_id]
    corpus = build_corpus(tmp_path, "a")
    ledger = build_ledger(tmp_path, corpus)
    projection = build_case(ledger, corpus)
    statuses = {
        record.evidence_id: projection.status_by_evidence[record.evidence_id]
        for record in corpus.evidence
    }

    if case_id == "all-pending":
        assert set(statuses.values()) == {"pending"}
    elif case_id == "all-excluded":
        assert set(statuses.values()) == {"excluded"}
    else:
        assert statuses[corpus.evidence[0].evidence_id] == "accepted"
        assert statuses[corpus.evidence[1].evidence_id] == "excluded"
        assert statuses[corpus.evidence[2].evidence_id] == "pending"

    draft = prepare(ledger, corpus)

    assert draft.status == expected_status
    assert draft.approved_evidence_ids == projection.accepted_evidence_ids
    assert draft.sent_evidence_ids == ()
    assert draft.citation_evidence_ids == ()
    assert draft.body == ""
    assert draft.review_revision == projection.revision
    assert draft.review_digest == projection.digest
    for record in corpus.evidence:
        if statuses[record.evidence_id] != "accepted":
            assert record.evidence_id not in draft.approved_evidence_ids


def test_reset_accepted_evidence_is_not_reused(tmp_path: Path) -> None:
    """CT-D-03 reset / INV-03, INV-04: withdrawn acceptance is never reused.

    One adapter and one AnswerService instance are reused across the real C reset,
    so a projection cached inside either instance would surface here. This is
    sequential-reuse coverage only; it does not establish concurrency or
    verify_current/release race safety.
    """
    corpus = build_corpus(tmp_path, "a")
    ledger = build_ledger(tmp_path, corpus)
    accepted = corpus.evidence[0]
    first = accept_one(ledger, corpus, reason="Synthetic acceptance before the reset.")
    assert first.accepted_evidence_ids == (accepted.evidence_id,)

    api = require_answer_api()
    service = api.answer_service(projections=build_adapter(ledger))
    before = service.prepare(build_request(corpus))
    assert before.status == "failed"
    assert before.approved_evidence_ids == (accepted.evidence_id,)

    reset = append_decision(
        ledger,
        question_id=QUESTION_ONE,
        evidence_id=accepted.evidence_id,
        action="reset",
        revision=first.revision,
        reason="Synthetic human reset that withdraws the earlier acceptance.",
    )
    assert reset.accepted_evidence_ids == ()
    assert reset.status_by_evidence[accepted.evidence_id] == "pending"
    current = ledger.projection(QUESTION_ONE)
    assert (current.revision, current.digest) == (reset.revision, reset.digest)

    after = service.prepare(build_request(corpus))

    assert after.status == "abstained"
    assert after.refusal_reason == api.refusal_no_approved_evidence
    assert after.approved_evidence_ids == ()
    assert after.sent_evidence_ids == ()
    assert after.citation_evidence_ids == ()
    assert after.body == ""
    assert after.review_revision == reset.revision
    assert after.review_digest == reset.digest


def test_acceptance_for_one_question_does_not_authorise_another(tmp_path: Path) -> None:
    """CT-D-04 / INV-03, INV-04: each question is read under its own projection token."""
    corpus = build_corpus(tmp_path, "a")
    ledger = build_ledger(tmp_path, corpus)
    first = accept_one(ledger, corpus, reason="Synthetic acceptance scoped to question one.")
    assert first.accepted_evidence_ids == (corpus.evidence[0].evidence_id,)

    adapter = build_adapter(ledger)
    other_projection = ledger.projection(QUESTION_TWO)
    returned = adapter.read_projection(QUESTION_TWO)
    assert returned.question_id == other_projection.question_id == QUESTION_TWO
    assert returned.snapshot_id == other_projection.snapshot_id == corpus.snapshot.snapshot_id
    assert returned.revision == other_projection.revision
    assert returned.digest == other_projection.digest
    assert returned.accepted_evidence_ids == other_projection.accepted_evidence_ids == ()

    api = require_answer_api()
    service = api.answer_service(projections=adapter)
    draft = service.prepare(
        build_request(corpus, question_id=QUESTION_TWO, answer_id=ANSWER_ID_TWO)
    )

    assert draft.question_id == QUESTION_TWO
    assert draft.status == "abstained"
    assert draft.refusal_reason == api.refusal_no_approved_evidence
    assert draft.approved_evidence_ids == ()
    assert draft.sent_evidence_ids == ()
    assert draft.citation_evidence_ids == ()
    assert draft.body == ""
    assert draft.review_revision == other_projection.revision
    assert draft.review_digest == other_projection.digest


def test_foreign_snapshot_request_raises_scope_mismatch_and_returns_no_draft(
    tmp_path: Path,
) -> None:
    """CT-D-05 / INV-04, FR-D-02 (partial): a ledger for snapshot A cannot answer B."""
    corpus_a = build_corpus(tmp_path, "a")
    corpus_b = build_corpus(tmp_path, "b")
    assert_contract_roundtrip(
        corpus_a.snapshot,
        corpus_b.snapshot,
        *corpus_a.evidence,
        *corpus_b.evidence,
    )
    assert corpus_a.snapshot.snapshot_id != corpus_b.snapshot.snapshot_id
    ledger = build_ledger(tmp_path, corpus_a)
    accept_one(ledger, corpus_a, reason="Synthetic acceptance bound to snapshot A.")

    control = prepare(ledger, corpus_a)
    assert control.snapshot_id == corpus_a.snapshot.snapshot_id
    assert control.status == "failed"

    api = require_answer_api()
    service = api.answer_service(projections=build_adapter(ledger))
    with pytest.raises(api.scope_mismatch_error):
        service.prepare(build_request(corpus_b))


def test_corrupt_ledger_propagates_review_ledger_corrupted_without_fallback(
    tmp_path: Path,
) -> None:
    """CT-D-06 / QA-01, INV-01: a truncated ledger fails closed; no abstained fallback."""
    corpus = build_corpus(tmp_path, "a")
    ledger = build_ledger(tmp_path, corpus)
    accept_one(ledger, corpus, reason="Synthetic acceptance before corrupting the file.")

    files = ledger_files(tmp_path)
    assert len(files) == 1
    ledger_path = files[0]
    payload = ledger_path.read_bytes()
    assert payload.endswith(b"\n")
    ledger_path.write_bytes(payload[:-1])

    api = require_answer_api()
    assert not issubclass(ReviewLedgerCorrupted, api.preparation_error)

    adapter = build_adapter(ledger)
    with pytest.raises(ReviewLedgerCorrupted):
        adapter.read_projection(QUESTION_ONE)

    service = api.answer_service(projections=adapter)
    with pytest.raises(ReviewLedgerCorrupted):
        service.prepare(build_request(corpus))


@pytest.mark.parametrize("error_name", ["PermissionError", "OSError"])
def test_ledger_read_fault_propagates_the_same_exception_instance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error_name: str
) -> None:
    """CT-D-07 / FR-D-02, INV-01: a read fault is not an empty review state.

    The fault is injected only at the actual ledger path's ``Path.read_bytes``
    boundary; every other path is delegated to the original method.
    """
    corpus = build_corpus(tmp_path, "a")
    ledger = build_ledger(tmp_path, corpus)
    accept_one(ledger, corpus, reason="Synthetic acceptance read normally before injection.")

    files = ledger_files(tmp_path)
    assert len(files) == 1
    ledger_path = files[0]

    control = prepare(ledger, corpus)
    assert control.status == "failed"

    injected = (
        PermissionError("synthetic permission fault at the ledger read boundary")
        if error_name == "PermissionError"
        else OSError("synthetic I/O fault at the ledger read boundary")
    )
    original_read_bytes = Path.read_bytes
    intercepted: list[Path] = []

    def guarded_read_bytes(self: Path) -> bytes:
        if Path(self) == ledger_path:
            intercepted.append(Path(self))
            raise injected
        return original_read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)

    api = require_answer_api()
    service = api.answer_service(projections=build_adapter(ledger))
    with pytest.raises(type(injected)) as excinfo:
        service.prepare(build_request(corpus))

    assert intercepted == [ledger_path]
    assert excinfo.value is injected
