"""D-local request, projection and decision models (not shared contracts).

Traceability: FR-D-01, FR-D-02, INV-03, INV-04. The projection view stays
structural so C's candidate dataclass can be adapted without importing C here.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from papertrace.contracts import (
    AnswerId,
    CorpusSnapshot,
    EvidenceId,
    EvidenceRecord,
    QuestionId,
    UTCTimestamp,
)

REFUSAL_NO_APPROVED_EVIDENCE = "NO_APPROVED_EVIDENCE"
REFUSAL_GENERATION_PATH_NOT_ENABLED = "GENERATION_PATH_NOT_ENABLED"


class AnswerRequest(BaseModel):
    """FR-D-01: caller-supplied inputs for one approved-evidence decision."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    snapshot: CorpusSnapshot
    question_id: QuestionId
    answer_id: AnswerId
    requested_at: UTCTimestamp
    evidence: tuple[EvidenceRecord, ...]


class ReviewProjectionView(Protocol):
    """INV-03/INV-04: read-only shape C's projection must expose (still provisional)."""

    snapshot_id: str
    question_id: str
    revision: int
    digest: str
    accepted_evidence_ids: Sequence[str]
    events: Sequence[object]


class ReviewProjectionPort(Protocol):
    """INV-03: read-only access to the review projection; never a ledger write."""

    def read_projection(self, question_id: str) -> ReviewProjectionView:
        """Return the current projection for one question."""
        ...


@dataclass(frozen=True)
class EligibilityDecision:
    """FR-D-02/INV-04: pure decision over an already-validated projection."""

    eligible: bool
    approved_evidence_ids: tuple[EvidenceId, ...]
    reason: str | None
