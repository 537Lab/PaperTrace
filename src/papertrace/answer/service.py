"""D answer service for slice 1: read the projection, gate, refuse before generation.

Traceability: FR-D-01, FR-D-02, FR-D-03 (partial), INV-01, INV-04. There is no
generation collaborator in this slice and no model, SDK or HTTP call is made.
"""

from typing import Literal

from papertrace.answer.eligibility import assess_eligibility
from papertrace.answer.model import (
    REFUSAL_GENERATION_PATH_NOT_ENABLED,
    REFUSAL_NO_APPROVED_EVIDENCE,
    AnswerRequest,
    ReviewProjectionPort,
)
from papertrace.contracts import AnswerDraft, EvidenceId

_DraftStatus = Literal["abstained", "failed"]


class AnswerService:
    """FR-D-01/FR-D-03: prepare only an abstained or not-enabled draft."""

    def __init__(self, *, projections: ReviewProjectionPort) -> None:
        self._projections = projections

    def prepare(self, request: AnswerRequest) -> AnswerDraft:
        """Read, gate and return a draft; never call a model or a search tool."""
        projection = self._projections.read_projection(request.question_id)
        assessment = assess_eligibility(projection=projection, request=request)
        decision = assessment.decision
        if decision.eligible:
            return self._draft(
                request=request,
                revision=assessment.revision,
                digest=assessment.digest,
                approved=decision.approved_evidence_ids,
                refusal_reason=REFUSAL_GENERATION_PATH_NOT_ENABLED,
                status="failed",
            )
        return self._draft(
            request=request,
            revision=assessment.revision,
            digest=assessment.digest,
            approved=(),
            refusal_reason=REFUSAL_NO_APPROVED_EVIDENCE,
            status="abstained",
        )

    def _draft(
        self,
        *,
        request: AnswerRequest,
        revision: int,
        digest: str,
        approved: tuple[EvidenceId, ...],
        refusal_reason: str,
        status: _DraftStatus,
    ) -> AnswerDraft:
        """INV-04: copy the validated tokens, keep sent and cited empty, invent nothing.

        The projection is deliberately not a parameter here, so this builder cannot
        read a second, possibly different revision or digest.
        """
        return AnswerDraft(
            schema_version=1,
            answer_id=request.answer_id,
            snapshot_id=request.snapshot.snapshot_id,
            question_id=request.question_id,
            review_revision=revision,
            review_digest=digest,
            approved_evidence_ids=approved,
            sent_evidence_ids=(),
            citation_evidence_ids=(),
            status=status,
            body="",
            refusal_reason=refusal_reason,
            generated_at=request.requested_at,
        )
