"""Module E reports: immutable research history, traceability and exports.

FR-E-01/02, INV-02/04/05/08, QA-01, SEC-01. Offline and deterministic: this
package stores and re-renders recorded decisions, and never re-generates an
answer, re-authors the review ledger or upgrades a blocked draft. Release
authority stays with module D; E only preserves and exports what was recorded.
"""

from __future__ import annotations

from .export import ExportService, export_json, export_markdown, history_detail, render_record
from .record import (
    ExportPermission,
    ExportPermissionDenied,
    InvalidRecord,
    RecordConflict,
    ResearchRecord,
    ReviewEvent,
    canonical_digest,
    contains_absolute_path,
    parse_record,
    record_conflict_for,
)
from .store import HistoryStore

__all__ = [
    "ExportPermission",
    "ExportPermissionDenied",
    "ExportService",
    "HistoryStore",
    "InvalidRecord",
    "RecordConflict",
    "ResearchRecord",
    "ReviewEvent",
    "canonical_digest",
    "contains_absolute_path",
    "export_json",
    "export_markdown",
    "history_detail",
    "parse_record",
    "record_conflict_for",
    "render_record",
]
