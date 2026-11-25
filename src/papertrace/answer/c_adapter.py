"""D-local read adapter over C's public review ledger projection.

Traceability: FR-D-01, FR-D-02 (partial), FR-D-03 (partial), INV-01, INV-03,
INV-04, QA-01, COST-01. The adapter delegates each read to C's public
``ReviewLedger.projection`` and returns that projection unchanged; it does not
map, cache, recompute, write, or downgrade any C failure. No model, network,
provider or ledger-write path exists here.
"""

from papertrace.review import ReviewLedger, ReviewProjection


class CReviewProjectionAdapter:
    """INV-03/INV-04: read-only C projection for D's existing projections port."""

    def __init__(self, *, ledger: ReviewLedger) -> None:
        self._ledger = ledger

    def read_projection(self, question_id: str) -> ReviewProjection:
        """Return C's own current projection; C errors propagate unchanged."""
        return self._ledger.projection(question_id)
