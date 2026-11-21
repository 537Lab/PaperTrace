"""Module B status projection for the future UI.

This module only formats retrieval state for display.  It never grants
acceptance or release authority (INV-03/INV-04) and never re-runs retrieval.
"""

from __future__ import annotations

from typing import Any

from papertrace.retrieval.service import RetrievalResult

__all__ = ["project_retrieval_view"]

_FORBIDDEN_AUTHORITY_KEYS = (
    "accepted",
    "accepted_by",
    "review_decision",
    "release_decision",
    "released",
    "release_status",
)


def _project_evidence(record: Any) -> dict[str, Any]:
    """Display-only projection of one evidence candidate."""
    locator = record.locator
    return {
        "evidence_id": record.evidence_id,
        "snapshot_id": record.snapshot_id,
        "document_id": record.document_id,
        "version_sha256": record.version_sha256,
        "locator": {
            "page_start": locator.page_start,
            "page_end": locator.page_end,
            "line_start": locator.line_start,
            "line_end": locator.line_end,
            "chunk_id": locator.chunk_id,
            "parser_name": locator.parser_name,
            "parser_version": locator.parser_version,
        },
        "excerpt": record.excerpt,
        "advisory_summary": record.advisory_summary,
        "upstream_context_id": record.upstream_context_id,
        "retrieved_at": record.retrieved_at.isoformat(),
    }


def project_retrieval_view(result: RetrievalResult) -> dict[str, Any]:
    """Project a retrieval result to display data without any authority fields."""
    projection: dict[str, Any] = {
        "status": result.status.value,
        "evidence": [_project_evidence(record) for record in result.evidence],
    }
    if result.stage is not None:
        projection["stage"] = result.stage
    for forbidden in _FORBIDDEN_AUTHORITY_KEYS:
        projection.pop(forbidden, None)
    return projection
