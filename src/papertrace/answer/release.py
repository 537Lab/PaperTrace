"""Deterministic Module D release gate over one captured review/corpus bundle.

Traceability: FR-D-02, INV-01, INV-02, INV-04, QA-01, offline COST-01. The gate
revalidates one ``AnswerDraft`` against the shared contract, reads exactly one
captured ``(CorpusSnapshot, ReviewProjectionView, evidence)`` bundle, reuses
``assess_eligibility``'s validated revision, digest and accepted membership, and
returns a blocked ``ReleaseDecision``. It never returns ``released``:
persistence and the final consistency boundary belong to E and application
orchestration. This module does not import PaperQA2, C's ledger, provider SDKs
or any network stack, and it never re-reads projection fields.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Protocol

from papertrace.answer.eligibility import assess_eligibility
from papertrace.answer.errors import (
    EvidenceProvenanceError,
    ProjectionScopeMismatchError,
    ProjectionShapeError,
    UnknownAcceptedEvidenceError,
)
from papertrace.answer.model import AnswerRequest, ReviewProjectionView
from papertrace.contracts import (
    AnswerDraft,
    CorpusSnapshot,
    DocumentVersion,
    EvidenceRecord,
    ReleaseDecision,
)

DRAFT_NOT_RELEASABLE = "DRAFT_NOT_RELEASABLE"
SNAPSHOT_SCOPE_MISMATCH = "SNAPSHOT_SCOPE_MISMATCH"
REVIEW_SCOPE_MISMATCH = "REVIEW_SCOPE_MISMATCH"
REVIEW_REVISION_STALE = "REVIEW_REVISION_STALE"
REVIEW_DIGEST_MISMATCH = "REVIEW_DIGEST_MISMATCH"
EVIDENCE_PROVENANCE_INVALID = "EVIDENCE_PROVENANCE_INVALID"
EVIDENCE_SCOPE_MISMATCH = "EVIDENCE_SCOPE_MISMATCH"
NO_TRACEABLE_CITATION = "NO_TRACEABLE_CITATION"
PUBLICATION_COMMIT_UNAVAILABLE = "PUBLICATION_COMMIT_UNAVAILABLE"

_Flags = tuple[bool, bool, bool, bool, bool]


class ReleaseInputError(Exception):
    """The captured input cannot be checked safely; no ReleaseDecision is produced."""


class CurrentPort(Protocol):
    """INV-03: read-only access to one captured release input bundle."""

    def read_current(
        self, question_id: str
    ) -> tuple[CorpusSnapshot, ReviewProjectionView, tuple[EvidenceRecord, ...]]:
        """Return the current captured bundle for one question."""
        ...


class ReleaseGate:
    """FR-D-02/INV-04: deterministic checks over a draft and one captured bundle."""

    def __init__(self, *, current: CurrentPort, clock: Callable[[], datetime]) -> None:
        self._current = current
        self._clock = clock

    def check(self, *, draft: AnswerDraft) -> ReleaseDecision:
        """Run the fixed check order and return a blocked decision; never release."""
        validated = AnswerDraft.model_validate(draft)
        decided_at = self._clock()

        if validated.status != "draft":
            return self._blocked(
                validated,
                reason=DRAFT_NOT_RELEASABLE,
                flags=(False, False, False, False, False),
                decided_at=decided_at,
            )

        bundle = self._current.read_current(validated.question_id)
        snapshot, projection, evidence = _validated_bundle(bundle)
        if validated.snapshot_id != snapshot.snapshot_id:
            return self._blocked(
                validated,
                reason=SNAPSHOT_SCOPE_MISMATCH,
                flags=(False, False, False, False, True),
                decided_at=decided_at,
            )

        request = AnswerRequest(
            snapshot=snapshot,
            question_id=validated.question_id,
            answer_id=validated.answer_id,
            requested_at=decided_at,
            evidence=evidence,
        )
        try:
            assessment = assess_eligibility(projection=projection, request=request)
        except ProjectionScopeMismatchError:
            return self._blocked(
                validated,
                reason=REVIEW_SCOPE_MISMATCH,
                flags=(True, False, False, False, True),
                decided_at=decided_at,
            )
        except (
            ProjectionShapeError,
            UnknownAcceptedEvidenceError,
            EvidenceProvenanceError,
        ) as error:
            raise ReleaseInputError(
                "the captured review projection or evidence cannot be checked safely"
            ) from error

        if validated.review_revision != assessment.revision:
            return self._blocked(
                validated,
                reason=REVIEW_REVISION_STALE,
                flags=(True, False, False, False, True),
                decided_at=decided_at,
            )
        if validated.review_digest != assessment.digest:
            return self._blocked(
                validated,
                reason=REVIEW_DIGEST_MISMATCH,
                flags=(True, False, False, False, True),
                decided_at=decided_at,
            )

        documents = {document.document_id: document for document in snapshot.documents}
        captured = {record.evidence_id: record for record in evidence}
        for evidence_id in _claimed_ids(validated):
            record = captured.get(evidence_id)
            if record is not None and not _provenance_matches(
                record, snapshot, documents
            ):
                return self._blocked(
                    validated,
                    reason=EVIDENCE_PROVENANCE_INVALID,
                    flags=(True, True, False, False, True),
                    decided_at=decided_at,
                )

        accepted = set(assessment.decision.approved_evidence_ids)
        approved = set(validated.approved_evidence_ids)
        sent = set(validated.sent_evidence_ids)
        if not (approved <= accepted) or not (sent <= accepted):
            return self._blocked(
                validated,
                reason=EVIDENCE_SCOPE_MISMATCH,
                flags=(True, True, False, False, True),
                decided_at=decided_at,
            )

        citation = set(validated.citation_evidence_ids)
        if not citation or not (citation <= sent) or not (citation <= accepted):
            return self._blocked(
                validated,
                reason=NO_TRACEABLE_CITATION,
                flags=(True, True, True, False, True),
                decided_at=decided_at,
            )

        return self._blocked(
            validated,
            reason=PUBLICATION_COMMIT_UNAVAILABLE,
            flags=(True, True, True, True, True),
            decided_at=decided_at,
        )

    @staticmethod
    def _blocked(
        draft: AnswerDraft,
        *,
        reason: str,
        flags: _Flags,
        decided_at: datetime,
    ) -> ReleaseDecision:
        """INV-04: bind every decision to the validated draft under check."""
        (
            snapshot_check_passed,
            review_check_passed,
            evidence_check_passed,
            citation_check_passed,
            answer_check_passed,
        ) = flags
        return ReleaseDecision(
            schema_version=1,
            answer_id=draft.answer_id,
            snapshot_id=draft.snapshot_id,
            question_id=draft.question_id,
            review_revision=draft.review_revision,
            review_digest=draft.review_digest,
            status="blocked",
            reason_codes=(reason,),
            snapshot_check_passed=snapshot_check_passed,
            review_check_passed=review_check_passed,
            evidence_check_passed=evidence_check_passed,
            citation_check_passed=citation_check_passed,
            answer_check_passed=answer_check_passed,
            decided_at=decided_at,
        )


def _validated_bundle(
    bundle: object,
) -> tuple[CorpusSnapshot, object, tuple[EvidenceRecord, ...]]:
    """FR-D-02: accept one three-item bundle of the captured types, without repair."""
    if not isinstance(bundle, tuple) or len(bundle) != 3:
        raise ReleaseInputError("captured bundle must be a three-item tuple")
    snapshot = bundle[0]
    projection = bundle[1]
    evidence = bundle[2]
    if not isinstance(snapshot, CorpusSnapshot):
        raise ReleaseInputError("captured snapshot is not a CorpusSnapshot")
    if not isinstance(evidence, tuple):
        raise ReleaseInputError("captured evidence must be a tuple")
    records: list[EvidenceRecord] = []
    for record in evidence:
        if not isinstance(record, EvidenceRecord):
            raise ReleaseInputError("captured evidence contains a non-EvidenceRecord")
        records.append(record)
    return snapshot, projection, tuple(records)


def _claimed_ids(draft: AnswerDraft) -> tuple[str, ...]:
    """Every evidence identity the draft claims, in first-claim order."""
    ordered: list[str] = []
    seen: set[str] = set()
    for evidence_id in (
        *draft.approved_evidence_ids,
        *draft.sent_evidence_ids,
        *draft.citation_evidence_ids,
    ):
        if evidence_id not in seen:
            seen.add(evidence_id)
            ordered.append(evidence_id)
    return tuple(ordered)


def _provenance_matches(
    record: EvidenceRecord,
    snapshot: CorpusSnapshot,
    documents: dict[str, DocumentVersion],
) -> bool:
    """INV-02/INV-04: the claimed record must belong to the captured snapshot."""
    if record.snapshot_id != snapshot.snapshot_id:
        return False
    document = documents.get(record.document_id)
    if document is None:
        return False
    return document.version_sha256 == record.version_sha256
