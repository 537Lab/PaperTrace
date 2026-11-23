"""A-only framework-neutral library view adapter delegating to CorpusService."""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from papertrace.contracts import CorpusSnapshot

from .service import CorpusService


@dataclass(frozen=True, slots=True)
class LibraryRow:
    """Ready-library row; carries no source bytes or external absolute paths."""

    document_id: str
    title: str
    source_name: str
    version_sha256: str
    status: str


@dataclass(frozen=True, slots=True)
class LibraryOverview:
    """Immutable ready-only library page state."""

    snapshot_id: str
    corpus_revision: int
    rows: tuple[LibraryRow, ...]


@dataclass(frozen=True, slots=True)
class ImportRow:
    """Immutable per-file import outcome."""

    document_id: str
    source_name: str
    version_sha256: str
    status: str
    stage: str
    reason_code: str | None


@dataclass(frozen=True, slots=True)
class ImportFeedback:
    """Immutable import batch receipt."""

    snapshot_id: str
    complete: bool
    rows: tuple[ImportRow, ...]


def _feedback(batch: dict[str, Any]) -> ImportFeedback:
    """Map a service import/retry batch receipt to ImportFeedback."""
    snapshot: CorpusSnapshot = batch["snapshot"]
    rows = tuple(
        ImportRow(
            document_id=item["document_id"],
            source_name=item["source_name"],
            version_sha256=item["version_sha256"],
            status=item["status"],
            stage=item["stage"],
            reason_code=item["reason_code"],
        )
        for item in batch["items"]
    )
    return ImportFeedback(
        snapshot_id=snapshot.snapshot_id, complete=batch["complete"], rows=rows
    )


def library_overview(service: CorpusService) -> LibraryOverview:
    """Ready rows from current_snapshot; ValueError on FRESHNESS_MISMATCH."""
    snapshot: CorpusSnapshot = service.current_snapshot()
    snapshot_id, corpus_revision = service.freshness()
    if snapshot_id != snapshot.snapshot_id:
        raise ValueError("FRESHNESS_MISMATCH")
    rows = tuple(
        LibraryRow(
            document_id=doc.document_id,
            title=doc.title,
            source_name=doc.source_name,
            version_sha256=doc.version_sha256,
            status=doc.status,
        )
        for doc in snapshot.documents
        if doc.status == "ready"
    )
    return LibraryOverview(
        snapshot_id=snapshot_id, corpus_revision=corpus_revision, rows=rows
    )


def import_selected(
    service: CorpusService,
    paths: Sequence[Path],
    replacements: dict[Path, str] | None = None,
) -> ImportFeedback:
    """Delegate the explicitly selected files to CorpusService.import_files."""
    return _feedback(service.import_files(paths, replacements))


def retry_selected(
    service: CorpusService, document_ids: Sequence[str]
) -> ImportFeedback:
    """Delegate the explicit retry request to CorpusService.retry_failed."""
    return _feedback(service.retry_failed(document_ids))


def remove_selected(
    service: CorpusService, document_ids: Sequence[str]
) -> LibraryOverview:
    """Delegate removal to CorpusService.remove, then re-read snapshot/revision."""
    service.remove(document_ids)
    return library_overview(service)


def restore_selected(
    service: CorpusService, document_ids: Sequence[str]
) -> LibraryOverview:
    """Delegate restore to CorpusService.restore, then re-read snapshot/revision."""
    service.restore(document_ids)
    return library_overview(service)
