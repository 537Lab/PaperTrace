"""Module D answer surface: approved-evidence gate and pre-generation refusal.

Traceability: FR-D-01, FR-D-02, FR-D-03 (partial), INV-01, INV-04. D-local
interfaces only; this package never imports PaperQA2, provider SDKs or HTTP stacks.
"""

from papertrace.answer.eligibility import evaluate_eligibility
from papertrace.answer.errors import (
    AnswerPreparationError,
    EvidenceProvenanceError,
    ProjectionScopeMismatchError,
    ProjectionShapeError,
    ReviewProjectionInvalidError,
    ReviewStateUnavailableError,
    UnknownAcceptedEvidenceError,
)
from papertrace.answer.model import (
    REFUSAL_GENERATION_PATH_NOT_ENABLED,
    REFUSAL_NO_APPROVED_EVIDENCE,
    AnswerRequest,
    EligibilityDecision,
    ReviewProjectionPort,
    ReviewProjectionView,
)
from papertrace.answer.service import AnswerService

__all__ = [
    "AnswerPreparationError",
    "AnswerRequest",
    "AnswerService",
    "EligibilityDecision",
    "EvidenceProvenanceError",
    "ProjectionScopeMismatchError",
    "ProjectionShapeError",
    "REFUSAL_GENERATION_PATH_NOT_ENABLED",
    "REFUSAL_NO_APPROVED_EVIDENCE",
    "ReviewProjectionInvalidError",
    "ReviewProjectionPort",
    "ReviewProjectionView",
    "ReviewStateUnavailableError",
    "UnknownAcceptedEvidenceError",
    "evaluate_eligibility",
]
