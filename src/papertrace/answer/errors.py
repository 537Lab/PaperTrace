"""D-local typed errors for approved-evidence preparation.

Traceability: FR-D-01, FR-D-02, INV-01, INV-04. These are D-local failures, not
shared contract types, and none of them may be converted into an empty approved set.
"""


class AnswerPreparationError(Exception):
    """Base class for failures that must prevent an answer draft from being produced."""


class ReviewStateUnavailableError(AnswerPreparationError):
    """The review projection cannot be read at all; no draft may be produced."""


class ReviewProjectionInvalidError(AnswerPreparationError):
    """The projection was readable but violates D's structural or scope contract."""


class ProjectionShapeError(ReviewProjectionInvalidError):
    """Required attributes, revision, digest or accepted-ID shape are invalid."""


class ProjectionScopeMismatchError(ReviewProjectionInvalidError):
    """The projection header does not match the requested snapshot or question."""


class UnknownAcceptedEvidenceError(ReviewProjectionInvalidError):
    """An accepted evidence ID is absent from the caller-supplied evidence set."""


class EvidenceProvenanceError(ReviewProjectionInvalidError):
    """Accepted evidence does not belong to the requested snapshot or document version."""
