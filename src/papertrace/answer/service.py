"""D answer service for slice 1: read the projection, gate, refuse before generation.

Traceability: FR-D-01, FR-D-02, FR-D-03 (partial), INV-01, INV-04. There is no
generation collaborator in this slice and no model, SDK or HTTP call is made.
"""

from typing import Literal

from papertrace.answer.eligibility import evaluate_eligibility
from papertrace.answer.model import (
    REFUSAL_GENERATION_PATH_NOT_ENABLED,
    REFUSAL_NO_APPROVED_EVIDENCE,
    AnswerRequest,
    ReviewProjectionPort,
    ReviewProjectionView,
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
        decision = evaluate_eligibility(projection=projection, request=request)
        if decision.eligible:
            return self._draft(
                request=request,
                projection=projection,
                approved=decision.approved_evidence_ids,
                refusal_reason=REFUSAL_GENERATION_PATH_NOT_ENABLED,
                status="failed",
            )
        return self._draft(
            request=request,
            projection=projection,
            approved=(),
            refusal_reason=REFUSAL_NO_APPROVED_EVIDENCE,
            status="abstained",
        )

    def _draft(
        self,
        *,
        request: AnswerRequest,
        projection: ReviewProjectionView,
        approved: tuple[EvidenceId, ...],
        refusal_reason: str,
        status: _DraftStatus,
    ) -> AnswerDraft:
        """INV-04: copy revision/digest, keep sent and cited empty, never invent values."""
        return AnswerDraft(
            schema_version=1,
            answer_id=request.answer_id,
            snapshot_id=request.snapshot.snapshot_id,
            question_id=request.question_id,
            review_revision=projection.revision,
            review_digest=projection.digest,
            approved_evidence_ids=approved,
            sent_evidence_ids=(),
            citation_evidence_ids=(),
            status=status,
            body="",
            refusal_reason=refusal_reason,
            generated_at=request.requested_at,
        )
