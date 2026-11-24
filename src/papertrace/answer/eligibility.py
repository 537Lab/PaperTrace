"""Pure approved-evidence gate: shape, scope, membership and provenance checks.

Traceability: FR-D-02, INV-01, INV-04. C owns ledger replay, digest algorithms and
human authority; this module only checks the read-only projection it is handed.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass

from papertrace.answer.errors import (
    EvidenceProvenanceError,
    ProjectionScopeMismatchError,
    ProjectionShapeError,
    UnknownAcceptedEvidenceError,
)
from papertrace.answer.model import (
    REFUSAL_NO_APPROVED_EVIDENCE,
    AnswerRequest,
    EligibilityDecision,
)
from papertrace.contracts import EvidenceRecord

_EVIDENCE_ID = re.compile(r"ev-[0-9a-f]{64}")
_QUESTION_ID = re.compile(r"q-[a-z0-9][a-z0-9_-]{0,63}")
_SNAPSHOT_ID = re.compile(r"snap-[0-9a-f]{64}")
_DIGEST = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True)
class _ValidatedProjection:
    """Shape-checked view; values are still C's, not recomputed here."""

    snapshot_id: str
    question_id: str
    revision: int
    digest: str
    accepted_evidence_ids: tuple[str, ...]
    events: tuple[object, ...]


@dataclass(frozen=True)
class EligibilityAssessment:
    """D-internal result: the decision plus the revision/digest it validated.

    Deliberately not exported from ``papertrace.answer``. It exists so the service
    can build a draft from the tokens validation accepted instead of reading them
    from the projection a second time (FR-D-02, INV-04). The values are copied at
    validation time; this type neither recomputes nor re-authenticates them.
    """

    decision: EligibilityDecision
    revision: int
    digest: str


def _attribute(projection: object, name: str) -> object:
    try:
        value: object = getattr(projection, name)
    except AttributeError as error:
        raise ProjectionShapeError(f"projection is missing attribute {name}") from error
    if value is None:
        raise ProjectionShapeError(f"projection attribute {name} is null")
    return value


def _text(value: object, *, name: str, pattern: re.Pattern[str]) -> str:
    if not isinstance(value, str):
        raise ProjectionShapeError(f"{name} must be a string")
    if pattern.fullmatch(value) is None:
        raise ProjectionShapeError(f"{name} has an invalid format")
    return value


def _revision(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProjectionShapeError("revision must be an integer")
    if value < 0:
        raise ProjectionShapeError("revision must be non-negative")
    return value


def _sequence(value: object, *, name: str) -> tuple[object, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ProjectionShapeError(f"{name} must be a sequence")
    return tuple(value)


def _validate_shape(projection: object) -> _ValidatedProjection:
    revision = _revision(_attribute(projection, "revision"))
    digest = _text(
        _attribute(projection, "digest"), name="digest", pattern=_DIGEST
    )
    accepted_items = _sequence(
        _attribute(projection, "accepted_evidence_ids"),
        name="accepted_evidence_ids",
    )
    accepted = tuple(
        _text(item, name=f"accepted_evidence_ids[{index}]", pattern=_EVIDENCE_ID)
        for index, item in enumerate(accepted_items)
    )
    if len(set(accepted)) != len(accepted):
        raise ProjectionShapeError("accepted_evidence_ids contains duplicate identity")
    snapshot_id = _text(
        _attribute(projection, "snapshot_id"), name="snapshot_id", pattern=_SNAPSHOT_ID
    )
    question_id = _text(
        _attribute(projection, "question_id"), name="question_id", pattern=_QUESTION_ID
    )
    events = _sequence(_attribute(projection, "events"), name="events")
    if revision == 0 and (accepted or events):
        raise ProjectionShapeError("revision 0 requires an empty ledger view")
    return _ValidatedProjection(
        snapshot_id=snapshot_id,
        question_id=question_id,
        revision=revision,
        digest=digest,
        accepted_evidence_ids=accepted,
        events=events,
    )


def assess_eligibility(*, projection: object, request: AnswerRequest) -> EligibilityAssessment:
    """FR-D-02/INV-04: the single validation path, returning decision and tokens.

    Every check happens exactly once and only the first read of each token is used,
    so an invalid first read can never be replaced by a later, valid one.
    """
    shape = _validate_shape(projection)
    if shape.snapshot_id != request.snapshot.snapshot_id:
        raise ProjectionScopeMismatchError(
            "projection snapshot does not match the requested snapshot"
        )
    if shape.question_id != request.question_id:
        raise ProjectionScopeMismatchError(
            "projection question does not match the requested question"
        )

    supplied = {record.evidence_id: record for record in request.evidence}
    accepted: list[EvidenceRecord] = []
    for evidence_id in shape.accepted_evidence_ids:
        record = supplied.get(evidence_id)
        if record is None:
            raise UnknownAcceptedEvidenceError(
                f"accepted evidence {evidence_id} was not supplied for this request"
            )
        accepted.append(record)

    documents = {document.document_id: document for document in request.snapshot.documents}
    for record in accepted:
        if record.snapshot_id != request.snapshot.snapshot_id:
            raise EvidenceProvenanceError(
                f"evidence {record.evidence_id} belongs to another snapshot"
            )
        document = documents.get(record.document_id)
        if document is None:
            raise EvidenceProvenanceError(
                f"evidence {record.evidence_id} names a document outside the snapshot"
            )
        if document.version_sha256 != record.version_sha256:
            raise EvidenceProvenanceError(
                f"evidence {record.evidence_id} has a mismatched document version"
            )

    if shape.accepted_evidence_ids:
        decision = EligibilityDecision(
            eligible=True,
            approved_evidence_ids=shape.accepted_evidence_ids,
            reason=None,
        )
    else:
        decision = EligibilityDecision(
            eligible=False,
            approved_evidence_ids=(),
            reason=REFUSAL_NO_APPROVED_EVIDENCE,
        )
    return EligibilityAssessment(
        decision=decision, revision=shape.revision, digest=shape.digest
    )


def evaluate_eligibility(*, projection: object, request: AnswerRequest) -> EligibilityDecision:
    """FR-D-02/INV-04: check scope, membership and provenance, then decide.

    Thin compatibility wrapper: the public API and return type are unchanged and
    the checks run through the same single path as ``assess_eligibility``.
    """
    return assess_eligibility(projection=projection, request=request).decision
