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


# --- Standalone answer panel: test-preparation proposal ----------------------
#
# Traceability: FR-D-01, FR-D-02, FR-D-03, INV-01, INV-03, INV-04. The proposed
# panel contract is fixed in
# ``docs/team/designs/module-D/20261125-d-answer-panel-test-plan.md``.
# These tests drive the future renderer through a recording UI and the real D
# generation/release services. They import no Streamlit runtime and make no
# product model or network call.


def generation_symbol(name: str) -> Any:
    """Resolve an already implemented D generation symbol from its submodule."""
    module = import_module("papertrace.answer.generation")
    symbol = getattr(module, name, None)
    assert symbol is not None, f"proposed Module D generation symbol {name!r} is missing"
    return symbol


def release_symbol(name: str) -> Any:
    """Resolve an already implemented D release symbol from its submodule."""
    module = import_module("papertrace.answer.release")
    symbol = getattr(module, name, None)
    assert symbol is not None, f"proposed Module D release symbol {name!r} is missing"
    return symbol


def panel_module(name: str) -> Any:
    """Lazily import a future panel entrypoint so pytest collection stays clean."""
    qualified = f"papertrace.answer.{name}"
    try:
        spec = find_spec(qualified)
    except ModuleNotFoundError:
        spec = None
    assert spec is not None, (
        f"FR-D-03/INV-04: proposed panel module {qualified} is not implemented "
        "(expected RED during the approved test-preparation stage)"
    )
    return import_module(qualified)


def panel_symbol(module_name: str, name: str) -> Any:
    """Resolve one proposed panel symbol, failing as a test assertion when absent."""
    module = panel_module(module_name)
    symbol = getattr(module, name, None)
    assert symbol is not None, (
        f"proposed Module D panel symbol {module_name}.{name} is missing"
    )
    return symbol


class RecordingProjectionReader:
    """Read-only projection port with a write spy the panel must never use."""

    def __init__(self, projection: object) -> None:
        self.projection = projection
        self.reads: list[str] = []
        self.writes: list[object] = []

    def read_projection(self, question_id: str) -> object:
        self.reads.append(question_id)
        return self.projection

    def write_projection(self, event: object) -> None:
        self.writes.append(event)


class RecordingCurrentPort:
    """Read-only release-input port with a write spy the panel must never use."""

    def __init__(self, bundle: object) -> None:
        self.bundle = bundle
        self.reads: list[str] = []
        self.writes: list[object] = []

    def read_current(self, question_id: str) -> object:
        self.reads.append(question_id)
        return self.bundle

    def write_current(self, event: object) -> None:
        self.writes.append(event)


class RecordingGenerationPort:
    """Counting double at D's B-generation boundary; it records exact calls."""

    def __init__(self, outcome: object) -> None:
        self.outcome = outcome
        self.calls: list[object] = []

    def call(self, request: object) -> object:
        self.calls.append(request)
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


class RecordingPanelUI:
    """Minimal display double; it deliberately exposes no publication command."""

    def __init__(self, generate_requests: tuple[bool, ...] = ()) -> None:
        self._requests = list(generate_requests)
        self.views: list[object | None] = []
        self.publication_requests = 0

    def render(self, view: object | None) -> None:
        self.views.append(view)

    def take_generate_request(self) -> bool:
        if not self._requests:
            return False
        return self._requests.pop(0)

    def request_publication(self) -> None:
        self.publication_requests += 1
        raise AssertionError("the answer panel must not expose a publication control")


def generation_policy() -> Any:
    return generation_symbol("GenerationPolicySpec")(
        provider="synthetic-provider", model="synthetic-model"
    )


def generation_request(
    snapshot: CorpusSnapshot,
    evidence: tuple[EvidenceRecord, ...],
    *,
    selected: tuple[str, ...] | None = None,
    question_text: str = "What does the synthetic resonance cell store?",
) -> Any:
    selected_ids = (evidence[0].evidence_id,) if selected is None else selected
    return generation_symbol("AnswerGenerationRequest")(
        base=build_request(snapshot, evidence),
        question_text=question_text,
        selected_evidence_ids=selected_ids,
        policy=generation_policy(),
    )


def successful_generation_result(
    evidence_id: str, *, accounting: object | None = None
) -> Any:
    return generation_symbol("GenerationCallResult")(
        status="SUCCESS",
        raw_output="The synthetic resonance cell stores 12 units of daylight energy (b1).",
        sent_evidence_ids=(evidence_id,),
        citation_aliases=(("b1", evidence_id),),
        unknown_citation_keys=(),
        ambiguous_citation_keys=(),
        refusal_reason=None,
        accounting=accounting,
    )


def repeated_sent_generation_result(
    evidence_id: str, *, accounting: object | None = None
) -> Any:
    return generation_symbol("GenerationCallResult")(
        status="SUCCESS",
        raw_output="Repeated synthetic sent metadata must be rejected (b1).",
        sent_evidence_ids=(evidence_id, evidence_id),
        citation_aliases=(("b1", evidence_id),),
        unknown_citation_keys=(),
        ambiguous_citation_keys=(),
        refusal_reason=None,
        accounting=accounting,
    )


def generation_accounting(attempts: int | None) -> Any:
    return generation_symbol("GenerationAccounting")(
        provider="synthetic-provider",
        model="synthetic-model",
        answer_model_attempts=attempts,
    )


def panel_scope(
    snapshot: CorpusSnapshot,
    projection: Any,
    *,
    question_id: str = QUESTION_ID,
    revision: int | None = None,
    digest: str | None = None,
    snapshot_id: str | None = None,
) -> Any:
    return panel_symbol("view", "PanelScope")(
        question_id=question_id,
        snapshot_id=snapshot.snapshot_id if snapshot_id is None else snapshot_id,
        review_revision=projection.revision if revision is None else revision,
        review_digest=projection.digest if digest is None else digest,
    )


def build_panel(
    *,
    projection: Any,
    generation_outcome: object,
    snapshot: CorpusSnapshot,
    evidence: tuple[EvidenceRecord, ...],
    ui: RecordingPanelUI,
    current_projection: Any | None = None,
) -> tuple[Any, RecordingProjectionReader, RecordingCurrentPort, RecordingGenerationPort]:
    projection_reader = RecordingProjectionReader(projection)
    current_reader = RecordingCurrentPort(
        (
            snapshot,
            projection if current_projection is None else current_projection,
            evidence,
        )
    )
    generation_port = RecordingGenerationPort(generation_outcome)
    panel = panel_symbol("view", "AnswerPanel")(
        generation=generation_symbol("AnswerGenerationService")(
            projections=projection_reader, generation=generation_port
        ),
        release_gate=release_symbol("ReleaseGate")(
            current=current_reader, clock=lambda: REQUESTED_AT
        ),
        ui=ui,
    )
    return panel, projection_reader, current_reader, generation_port


def top_level_import_names(source: str) -> list[str]:
    """Return module-scope import targets, used to keep Streamlit out of import time."""
    names: list[str] = []
    for node in ast.parse(source).body:
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            names.append(node.module)
    return names


def test_panel_open_and_rerun_do_not_generate_or_write() -> None:
    """FR-D-01/INV-01: opening and rerunning only render; no boundary call or write."""
    snapshot, doc_a, _ = build_corpus()
    record = build_evidence(snapshot, doc_a, CORPUS_A)
    projection = build_projection(snapshot)
    request = generation_request(snapshot, (record,))
    ui = RecordingPanelUI()
    panel, projections, current, generation = build_panel(
        projection=projection,
        generation_outcome=successful_generation_result(record.evidence_id),
        snapshot=snapshot,
        evidence=(record,),
        ui=ui,
    )
    scope = panel_scope(snapshot, projection)

    assert panel.render(request=request, scope=scope) is None
    assert panel.render(request=request, scope=scope) is None

    assert ui.views == [None, None]
    assert generation.calls == []
    assert projections.reads == []
    assert current.reads == []
    assert projections.writes == []
    assert current.writes == []
    assert ui.publication_requests == 0


def test_explicit_generate_calls_boundary_once_and_rerun_reuses_display() -> None:
    """FR-D-03/INV-04: one click, one port call, one displayed validated draft."""
    snapshot, doc_a, _ = build_corpus()
    record = build_evidence(snapshot, doc_a, CORPUS_A)
    projection = build_projection(snapshot, revision=1, accepted=(record.evidence_id,))
    result = successful_generation_result(record.evidence_id)
    request = generation_request(snapshot, (record,))
    ui = RecordingPanelUI((True, False))
    panel, projections, current, generation = build_panel(
        projection=projection,
        generation_outcome=result,
        snapshot=snapshot,
        evidence=(record,),
        ui=ui,
    )
    scope = panel_scope(snapshot, projection)

    first = panel.render(request=request, scope=scope)
    second = panel.render(request=request, scope=scope)

    assert len(generation.calls) == 1
    assert first is not None
    assert first.draft_status == "draft"
    assert first.body == result.raw_output
    assert first.citation_evidence_ids == (record.evidence_id,)
    assert first.refusal_reason is None
    assert second == first
    assert ui.views == [first, first]
    assert projections.reads == [QUESTION_ID, QUESTION_ID]
    assert current.reads == [QUESTION_ID]


def test_generate_without_approved_evidence_shows_refusal_and_skips_boundary() -> None:
    """FR-D-01/INV-01: an empty accepted projection is refused before generation."""
    snapshot, doc_a, _ = build_corpus()
    record = build_evidence(snapshot, doc_a, CORPUS_A)
    projection = build_projection(snapshot)
    request = generation_request(snapshot, (record,))
    ui = RecordingPanelUI((True,))
    panel, projections, current, generation = build_panel(
        projection=projection,
        generation_outcome=successful_generation_result(record.evidence_id),
        snapshot=snapshot,
        evidence=(record,),
        ui=ui,
    )

    view = panel.render(request=request, scope=panel_scope(snapshot, projection))

    assert view is not None
    assert view.draft_status == "abstained"
    assert view.refusal_reason == answer("REFUSAL_NO_APPROVED_EVIDENCE")
    assert view.body == ""
    assert view.citation_evidence_ids == ()
    assert view.release_decision is None
    assert generation.calls == []
    assert projections.reads == [QUESTION_ID]
    assert current.reads == []
    assert projections.writes == []
    assert current.writes == []


def test_blocked_release_keeps_draft_visible_and_offers_no_publication_control() -> None:
    """FR-D-02/INV-04: a real blocked gate does not hide the draft or citations."""
    snapshot, doc_a, _ = build_corpus()
    record = build_evidence(snapshot, doc_a, CORPUS_A)
    projection = build_projection(snapshot, revision=1, accepted=(record.evidence_id,))
    result = successful_generation_result(
        record.evidence_id, accounting=generation_accounting(1)
    )
    request = generation_request(snapshot, (record,))
    ui = RecordingPanelUI((True,))
    panel, projections, current, generation = build_panel(
        projection=projection,
        generation_outcome=result,
        snapshot=snapshot,
        evidence=(record,),
        ui=ui,
    )

    view = panel.render(request=request, scope=panel_scope(snapshot, projection))

    assert view is not None
    assert view.draft_status == "draft"
    assert view.body == result.raw_output
    assert view.citation_evidence_ids == (record.evidence_id,)
    assert view.release_decision is not None
    assert view.release_decision.status == "blocked"
    assert view.release_decision.reason_codes == (
        release_symbol("PUBLICATION_COMMIT_UNAVAILABLE"),
    )
    assert ui.publication_requests == 0
    assert "request_publication" not in dir(panel_symbol("view", "PanelUI"))
    assert len(generation.calls) == 1
    assert current.reads == [QUESTION_ID]
    assert projections.writes == []
    assert current.writes == []


@pytest.mark.parametrize(
    ("case_id", "attempts", "accounting_present"),
    [
        ("observed-one", 1, True),
        ("observed-zero", 0, True),
        ("unknown-count", None, True),
        ("absent-accounting", None, False),
    ],
    ids=["observed-one", "observed-zero", "unknown-count", "absent-accounting"],
)
def test_repeated_sent_ids_suppress_output_and_show_validated_accounting(
    case_id: str, attempts: int | None, accounting_present: bool
) -> None:
    """FR-D-02/INV-04: a rejected duplicate-sent result keeps only validated accounting."""
    snapshot, doc_a, _ = build_corpus()
    record = build_evidence(snapshot, doc_a, CORPUS_A)
    projection = build_projection(snapshot, revision=1, accepted=(record.evidence_id,))
    accounting = generation_accounting(attempts) if accounting_present else None
    result = repeated_sent_generation_result(
        record.evidence_id, accounting=accounting
    )
    request = generation_request(snapshot, (record,))
    ui = RecordingPanelUI((True,))
    panel, _, _, generation = build_panel(
        projection=projection,
        generation_outcome=result,
        snapshot=snapshot,
        evidence=(record,),
        ui=ui,
    )

    view = panel.render(request=request, scope=panel_scope(snapshot, projection))

    assert view is not None
    assert view.draft_status == "failed"
    assert view.refusal_reason == generation_symbol("REASON_RESULT_SHAPE_INVALID")
    assert view.body == ""
    assert result.raw_output not in view.body
    assert view.citation_evidence_ids == ()
    assert view.accounting_observed is accounting_present
    assert view.observed_answer_model_attempts == (
        attempts if accounting_present else None
    )
    assert len(generation.calls) == 1


SCOPE_CHANGES = [
    ("question", {"question_id": "q-synthetic-2"}),
    ("snapshot", {"snapshot_id": "snap-" + "a" * 64}),
    ("revision", {"revision": 2}),
    ("digest", {"digest": "b" * 64}),
]
SCOPE_CHANGE_IDS = [case_id for case_id, _ in SCOPE_CHANGES]


@pytest.mark.parametrize(
    ("case_id", "changes"), SCOPE_CHANGES, ids=SCOPE_CHANGE_IDS
)
def test_scope_change_clears_previous_result_without_generation(
    case_id: str, changes: dict[str, object]
) -> None:
    """FR-D-02/INV-04: a display-scope change discards the old view and never generates."""
    snapshot, doc_a, _ = build_corpus()
    record = build_evidence(snapshot, doc_a, CORPUS_A)
    projection = build_projection(snapshot, revision=1, accepted=(record.evidence_id,))
    result = successful_generation_result(record.evidence_id)
    request = generation_request(snapshot, (record,))
    ui = RecordingPanelUI((True, True))
    panel, projections, _, generation = build_panel(
        projection=projection,
        generation_outcome=result,
        snapshot=snapshot,
        evidence=(record,),
        ui=ui,
    )
    scope = panel_scope(snapshot, projection)

    first = panel.render(request=request, scope=scope)
    assert first is not None
    assert first.draft_status == "draft"
    calls_after_first = len(generation.calls)
    reads_after_first = list(projections.reads)

    cleared = panel.render(
        request=request, scope=panel_scope(snapshot, projection, **changes)
    )

    assert cleared is None
    assert ui.views[-1] is None
    assert calls_after_first == 1
    assert len(generation.calls) == calls_after_first
    assert projections.reads == reads_after_first


def test_preview_entrypoint_keeps_streamlit_out_of_module_scope() -> None:
    """FR-D-03: the preview module imports without an installed Streamlit runtime."""
    from inspect import getsource

    module = panel_module("preview")

    assert callable(getattr(module, "render_preview", None))
    assert callable(getattr(module, "main", None))
    names = top_level_import_names(getsource(module))
    assert not any(
        name == "streamlit" or name.startswith("streamlit.") for name in names
    )
