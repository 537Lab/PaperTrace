"""Module E export and history detail. FR-E-01/02, INV-02/04/05/08, SEC-01.

Exports mirror the saved package: same snapshot, evidence, ledger, draft and
release status. Original excerpts are hidden by default and only appear when a
trusted verifier confirms an export grant bound to this record, evidence set and
``external-export`` purpose. Free text is scrubbed of machine-local absolute
paths and credential-like metadata is never emitted. E never re-generates an
answer and never upgrades ``blocked`` to ``released``.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from typing import Any

from .record import (
    SENSITIVE_KEY_MARKERS,
    ExportPermission,
    ExportPermissionDenied,
    ResearchRecord,
)

__all__ = [
    "ExportService",
    "export_json",
    "export_markdown",
    "history_detail",
    "render_record",
]

PermissionVerifier = Callable[[ExportPermission], bool]

_WINDOWS_PATH = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/][^\s\"'<>|]*")
_UNC_PATH = re.compile(r"\\\\[^\\\s]+[^\s\"'<>|]*")
_POSIX_PATH = re.compile(r"(?<![\w.])/(?:[^/\s\"'<>|]+/)*[^/\s\"'<>|]*")
_PATH_REPLACEMENT = "[redacted-path]"
_METADATA_REPLACEMENT = "[redacted]"


def _scrub_text(value: str) -> str:
    """SEC-01: strip local absolute paths from exported free text."""
    scrubbed = _WINDOWS_PATH.sub(_PATH_REPLACEMENT, value)
    scrubbed = _UNC_PATH.sub(_PATH_REPLACEMENT, scrubbed)
    scrubbed = _POSIX_PATH.sub(_PATH_REPLACEMENT, scrubbed)
    return scrubbed


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(marker in lowered for marker in SENSITIVE_KEY_MARKERS)


def _scrub_metadata(value: Any) -> Any:
    """SEC-01: allow-list by shape; credential-like keys never leave the record."""
    if isinstance(value, Mapping):
        return {
            str(key): _scrub_metadata(item)
            for key, item in value.items()
            if not _is_sensitive_key(str(key))
        }
    if isinstance(value, (list, tuple)):
        return [_scrub_metadata(item) for item in value]
    if isinstance(value, str):
        return _scrub_text(value)
    return value if isinstance(value, (int, float, bool)) or value is None else _METADATA_REPLACEMENT


def _scrub_free_text(value: str | None) -> str | None:
    return None if value is None else _scrub_text(value)


def _verify(
    record: ResearchRecord,
    permission: ExportPermission | None,
    verifier: PermissionVerifier | None,
) -> frozenset[str]:
    """FR-E-02, SEC-01: exporter-side check; a missing verifier denies by default."""
    if permission is None or verifier is None:
        raise ExportPermissionDenied("original excerpt export requires a verified grant")
    if permission.purpose != "external-export":
        raise ExportPermissionDenied("grant purpose does not authorize external export")
    if permission.record_id != record.record_id:
        raise ExportPermissionDenied("grant is bound to a different research record")
    record_evidence = {item.evidence_id for item in record.evidence}
    granted = set(permission.evidence_ids)
    if not granted or not granted <= record_evidence:
        raise ExportPermissionDenied("grant does not cover this record's evidence")
    try:
        trusted = verifier(permission)
    except Exception:
        raise ExportPermissionDenied("grant verification failed") from None
    if trusted is not True:
        raise ExportPermissionDenied("grant is not issued by a trusted authority")
    return frozenset(granted)


def _export_structure(
    record: ResearchRecord, allowed_excerpts: frozenset[str]
) -> dict[str, Any]:
    """FR-E-01, INV-04: one canonical structure behind both export formats."""
    evidence: list[dict[str, Any]] = []
    for item in record.evidence:
        entry = item.model_dump(mode="json")
        entry.pop("excerpt", None)
        entry["advisory_summary"] = _scrub_free_text(item.advisory_summary)
        entry["excerpt_included"] = item.evidence_id in allowed_excerpts
        if entry["excerpt_included"]:
            entry["excerpt"] = _scrub_text(item.excerpt)
        evidence.append(entry)
    draft = record.draft.model_dump(mode="json")
    draft["body"] = _scrub_text(record.draft.body)
    draft["refusal_reason"] = _scrub_free_text(record.draft.refusal_reason)
    return {
        "record_schema_version": record.record_schema_version,
        "record_id": record.record_id,
        "saved_at": record.saved_at.isoformat(),
        "question": _scrub_text(record.question),
        "snapshot": record.snapshot.model_dump(mode="json"),
        "evidence": evidence,
        "review_events": [
            {
                "command_id": event.command_id,
                "decision": event.decision.model_dump(mode="json"),
            }
            for event in record.review_events
        ],
        "review_revision": record.review_revision,
        "review_digest": record.review_digest,
        "draft": draft,
        "release": record.release.model_dump(mode="json"),
        "run_metadata": _scrub_metadata(record.run_metadata),
        "export": {
            "excerpt_policy": "explicit-export-permission",
            "release_authority": "module-D-decision-recorded-not-recomputed",
        },
    }


def render_record(
    record: ResearchRecord,
    *,
    include_excerpts: bool = False,
    permission: ExportPermission | None = None,
    verifier: PermissionVerifier | None = None,
) -> dict[str, Any]:
    """Build the export structure, verifying any excerpt grant first."""
    allowed = frozenset[str]()
    if include_excerpts:
        allowed = _verify(record, permission, verifier)
    return _export_structure(record, allowed)


def _dump(structure: Mapping[str, Any]) -> str:
    return json.dumps(structure, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)


def _locator_text(locator: Mapping[str, Any]) -> str:
    pages = (
        f"pages {locator['page_start']}-{locator['page_end']}"
        if locator.get("page_start") is not None
        else f"lines {locator['line_start']}-{locator['line_end']}"
    )
    return (
        f"{pages}; chunk `{locator['chunk_id']}`; "
        f"parser {locator['parser_name']}@{locator['parser_version']}"
    )


def _markdown(structure: Mapping[str, Any]) -> str:
    """FR-E-01: Markdown expresses the same statuses and sources as the JSON export."""
    lines: list[str] = [
        f"# Research record {structure['record_id']}",
        "",
        f"- Saved at: {structure['saved_at']}",
        f"- Release status: **{structure['release']['status']}**",
        f"- Draft status: {structure['draft']['status']}",
        f"- Review revision: {structure['review_revision']}",
        f"- Review digest: `{structure['review_digest']}`",
        "",
        "## Question",
        "",
        structure["question"],
        "",
        "## Answer",
        "",
        structure["draft"]["body"],
    ]
    refusal = structure["draft"].get("refusal_reason")
    if refusal:
        lines += ["", f"Refusal reason: {refusal}"]
    lines += [
        "",
        f"## Release decision ({structure['release']['status']})",
        "",
    ]
    codes = structure["release"].get("reason_codes") or []
    if codes:
        lines += ["- Reason codes: " + ", ".join(f"`{code}`" for code in codes)]
    for name in ("snapshot", "review", "evidence", "citation", "answer"):
        passed = structure["release"][f"{name}_check_passed"]
        lines.append(f"- {name} check passed: {str(passed).lower()}")
    lines += ["", "## Sources", ""]
    for item in structure["evidence"]:
        lines.append(
            f"- `{item['evidence_id']}` — {item['document_id']} "
            f"(version `{item['version_sha256']}`)"
        )
        lines.append(f"  - Locator: {_locator_text(item['locator'])}")
        if item["excerpt_included"]:
            lines.append(f"  - Excerpt: {item['excerpt']}")
        else:
            lines.append("  - Excerpt: hidden (no verified export permission)")
    lines += ["", "## Review events", ""]
    for event in structure["review_events"]:
        decision = event["decision"]
        lines.append(
            f"- `{event['command_id']}`: {decision['status']} "
            f"`{decision['evidence_id']}` by {decision['reviewer_ref']} "
            f"(revision {decision['revision']})"
        )
    return "\n".join(lines) + "\n"


def export_json(
    record: ResearchRecord,
    *,
    include_excerpts: bool = False,
    permission: ExportPermission | None = None,
    verifier: PermissionVerifier | None = None,
) -> str:
    """FR-E-01, SEC-01: deterministic JSON export; excerpts need a verified grant."""
    structure = render_record(
        record, include_excerpts=include_excerpts, permission=permission, verifier=verifier
    )
    return _dump(structure)


def export_markdown(
    record: ResearchRecord,
    *,
    include_excerpts: bool = False,
    permission: ExportPermission | None = None,
    verifier: PermissionVerifier | None = None,
) -> str:
    """FR-E-01, SEC-01: Markdown export mirroring the JSON evidence and statuses."""
    structure = render_record(
        record, include_excerpts=include_excerpts, permission=permission, verifier=verifier
    )
    return _markdown(structure)


class ExportService:
    """Exporter bound to one trusted grant verifier at construction time."""

    def __init__(self, *, permission_verifier: PermissionVerifier) -> None:
        if not callable(permission_verifier):
            raise ExportPermissionDenied("export service requires a callable verifier")
        self._verifier = permission_verifier

    def export_json(
        self,
        record: ResearchRecord,
        *,
        include_excerpts: bool = False,
        permission: ExportPermission | None = None,
    ) -> str:
        return export_json(
            record,
            include_excerpts=include_excerpts,
            permission=permission,
            verifier=self._verifier,
        )

    def export_markdown(
        self,
        record: ResearchRecord,
        *,
        include_excerpts: bool = False,
        permission: ExportPermission | None = None,
    ) -> str:
        return export_markdown(
            record,
            include_excerpts=include_excerpts,
            permission=permission,
            verifier=self._verifier,
        )


def history_detail(
    record: ResearchRecord, *, current_snapshot_id: str | None = None
) -> dict[str, Any]:
    """FR-E-02: display-only view; superseded marks drift without touching history."""
    superseded = current_snapshot_id is not None and current_snapshot_id != (
        record.snapshot.snapshot_id
    )
    return {
        "record_id": record.record_id,
        "snapshot_id": record.snapshot.snapshot_id,
        "current_snapshot_id": current_snapshot_id,
        "superseded": superseded,
        "review_revision": record.review_revision,
        "review_digest": record.review_digest,
        "draft_status": record.draft.status,
        "release_status": record.release.status,
        "released": record.release.status == "released",
        "saved_at": record.saved_at.isoformat(),
        "evidence_ids": [item.evidence_id for item in record.evidence],
    }
