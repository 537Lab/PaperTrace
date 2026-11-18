"""Read-only comparison view and decision prompt for module C.

Traceability: FR-C-02; INV-02/INV-04/INV-06.

Every function here only reads the ledger. Appending authority belongs to
``ReviewLedger.commit_decision`` / ``submit_decision`` alone.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from papertrace.contracts import SourceLocator
from papertrace.review.service import ReviewLedger, ReviewLedgerError


class InsufficientIndependentSources(ReviewLedgerError):
    """Comparison needs at least two evidence rows from two documents."""


@dataclass(frozen=True)
class ComparisonRow:
    """One side-by-side evidence row; status comes only from the ledger."""

    document_id: str
    evidence_id: str
    title: str
    source_name: str
    version_sha256: str
    excerpt: str
    advisory_summary: str | None
    status: str
    reason: str | None
    revision: int | None
    locator: SourceLocator


@dataclass(frozen=True)
class ComparisonView:
    """Immutable collection of comparison rows."""

    question_id: str
    rows: tuple[ComparisonRow, ...]


@dataclass(frozen=True)
class DecisionPrompt:
    """Read-only context for a possible explicit human command."""

    question_id: str
    evidence_id: str
    expected_revision: int
    allowed_actions: tuple[str, ...]
    current_status: str


def comparison_view(
    ledger: ReviewLedger,
    question_id: str,
    evidence_ids: Iterable[str],
) -> ComparisonView:
    """Render in-scope evidence rows without writing the ledger."""

    records = [ledger.evidence_record(evidence_id) for evidence_id in evidence_ids]
    if len({record.evidence_id for record in records}) < 2:
        raise InsufficientIndependentSources("comparison needs at least two distinct evidence rows")
    if len({record.document_id for record in records}) < 2:
        raise InsufficientIndependentSources(
            "comparison needs evidence from at least two distinct documents"
        )

    projection = ledger.projection(question_id)
    statuses = projection.status_by_evidence
    reasons = projection.latest_reason_by_evidence
    revisions = projection.latest_revision_by_evidence
    rows: list[ComparisonRow] = []
    for record in records:
        document = ledger.document(record.document_id)
        rows.append(
            ComparisonRow(
                document_id=record.document_id,
                evidence_id=record.evidence_id,
                title=document.title,
                source_name=document.source_name,
                version_sha256=record.version_sha256,
                excerpt=record.excerpt,
                advisory_summary=record.advisory_summary,
                status=statuses.get(record.evidence_id, "pending"),
                reason=reasons.get(record.evidence_id),
                revision=revisions.get(record.evidence_id),
                locator=record.locator,
            )
        )
    return ComparisonView(question_id=question_id, rows=tuple(rows))


def decision_prompt(ledger: ReviewLedger, question_id: str, evidence_id: str) -> DecisionPrompt:
    """Return the current revision and the allowed human actions, read-only."""

    record = ledger.evidence_record(evidence_id)
    projection = ledger.projection(question_id)
    return DecisionPrompt(
        question_id=question_id,
        evidence_id=record.evidence_id,
        expected_revision=projection.revision,
        allowed_actions=("accept", "exclude", "reset"),
        current_status=projection.status_by_evidence.get(record.evidence_id, "pending"),
    )
