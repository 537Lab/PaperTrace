"""Safe, framework-neutral projections and commands for the A document library.

This module is an A-only adapter. It neither assigns review/publication
authority nor exposes source bytes or installs shared application navigation.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .service import CorpusService


@dataclass(frozen=True, slots=True)
class LibraryRow:
    """Ready document from the current immutable corpus snapshot."""

    document_id: str
    title: str
    source_name: str
    version_sha256: str
    status: str


@dataclass(frozen=True, slots=True)
class LibraryOverview:
    """Snapshot-bound projection containing no source bytes or external paths."""

    snapshot_id: str
    corpus_revision: int
    rows: tuple[LibraryRow, ...]


@dataclass(frozen=True, slots=True)
class ImportRow:
    """Authoritative status of a single selected import or retry."""

    document_id: str
    source_name: str
    version_sha256: str
    status: str
    stage: str
    reason_code: str | None


@dataclass(frozen=True, slots=True)
class ImportFeedback:
    """Result of an explicit batch, including each failure separately."""

    snapshot_id: str
    complete: bool
    rows: tuple[ImportRow, ...]


def library_overview(service: CorpusService) -> LibraryOverview:
    """Fail closed when snapshot identity and freshness disagree."""
    snapshot = service.current_snapshot()
    freshness_snapshot_id, revision = service.freshness()
    if freshness_snapshot_id != snapshot.snapshot_id:
        raise ValueError("FRESHNESS_MISMATCH")
    return LibraryOverview(
        snapshot_id=snapshot.snapshot_id,
        corpus_revision=revision,
        rows=tuple(
            LibraryRow(
                document_id=member.document_id,
                title=member.title,
                source_name=member.source_name,
                version_sha256=member.version_sha256,
                status=member.status,
            )
            for member in snapshot.documents
        ),
    )


def _feedback(batch: dict[str, Any]) -> ImportFeedback:
    """Project the validated A service result without paths or raw payloads."""
    snapshot = batch["snapshot"]
    return ImportFeedback(
        snapshot_id=snapshot.snapshot_id,
        complete=batch["complete"],
        rows=tuple(
            ImportRow(
                document_id=item["document_id"],
                source_name=item["source_name"],
                version_sha256=item["version_sha256"],
                status=item["status"],
                stage=item["stage"],
                reason_code=item["reason_code"],
            )
            for item in batch["items"]
        ),
    )


def import_selected(
    service: CorpusService,
    paths: Sequence[Path],
    replacements: dict[Path, str] | None = None,
) -> ImportFeedback:
    """Let A authorize the whole selected batch before any ingest side effect."""
    return _feedback(service.import_files(tuple(paths), replacements=replacements))


def retry_selected(
    service: CorpusService, document_ids: Sequence[str]
) -> ImportFeedback:
    """Retry previously failed items; ready or unknown IDs remain forbidden."""
    return _feedback(service.retry_failed(tuple(document_ids)))


def remove_selected(
    service: CorpusService, document_ids: Sequence[str]
) -> LibraryOverview:
    """Remove current membership without deleting immutable history."""
    service.remove(tuple(document_ids))
    return library_overview(service)


def restore_selected(
    service: CorpusService, document_ids: Sequence[str]
) -> LibraryOverview:
    """Restore an already ready version without re-ingesting the source."""
    service.restore(tuple(document_ids))
    return library_overview(service)
