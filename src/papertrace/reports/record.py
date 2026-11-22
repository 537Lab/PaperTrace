"""Module E record envelope: immutable research history package. FR-E-01/02, INV-02/04/05/08.

This is a versioned wrapper around the five shared models. It never adds private
fields to them, never re-generates answers and never upgrades a blocked draft to
released. Synthetic-only offline development; no model or network calls.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from hashlib import sha256
from typing import Annotated, Any, Literal, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    field_validator,
    model_validator,
)

from papertrace.contracts import (
    AnswerDraft,
    CorpusSnapshot,
    DocumentVersion,
    EvidenceId,
    EvidenceRecord,
    NonBlank,
    ReleaseDecision,
    ReviewDecision,
    Sha256,
    UTCTimestamp,
)

__all__ = [
    "ExportPermission",
    "ExportPermissionDenied",
    "InvalidRecord",
    "RecordConflict",
    "ResearchRecord",
    "ReviewEvent",
]

# UUIDv4-shaped record identifier; path-hostile input is rejected before any I/O.
RecordId = Annotated[
    str,
    StringConstraints(
        strict=True,
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    ),
]

SENSITIVE_KEY_MARKERS = (
    "api_key",
    "apikey",
    "access_key",
    "secret",
    "password",
    "passwd",
    "token",
    "credential",
    "authorization",
    "cookie",
    "private_key",
    "session_key",
)

_ABSOLUTE_PATH = re.compile(
    r"(?:"
    r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]"  # Windows drive root
    r"|\\\\[^\\\s]+"  # UNC share
    r"|(?<![\w.])/(?:[^/\s]+/)*[^/\s]*"  # POSIX absolute path
    r")"
)


def _strip_control(value: str) -> str:
    return "".join((" " if ord(c) < 32 or ord(c) == 127 else c) for c in value)


def contains_absolute_path(value: str) -> bool:
    """SEC-01: detect machine-local absolute paths without touching the filesystem."""
    return _ABSOLUTE_PATH.search(value) is not None


def _reject_absolute_path(value: str) -> str:
    if contains_absolute_path(value):
        raise ValueError("free text cannot contain a local absolute path")
    return value


SafeText = Annotated[str, AfterValidator(_reject_absolute_path)]


class _ReportModel(BaseModel):
    """Closed, immutable E-owned envelope; unknown fields fail closed (QA-01)."""

    model_config = ConfigDict(frozen=True, extra="forbid", revalidate_instances="always")


class InvalidRecord(ValueError):
    """FR-E-02, SEC-01: record is missing, malformed, unsafe or tampered."""


class RecordConflict(InvalidRecord):
    """INV-05/08: append-only history never overwrites an existing record id."""


class ExportPermissionDenied(InvalidRecord):
    """FR-E-02, SEC-01: original text needs a verified grant for this record and scope."""


def _canonical_json(payload: Any) -> str:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def canonical_digest(payload: Any) -> str:
    """QA-01, INV-02: one deterministic digest rule shared with C's ledger tokens."""
    return sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


class ReviewEvent(_ReportModel):
    """FR-E-01: one append-only ledger entry, replayed by hash not by trust."""

    command_id: NonBlank
    decision: ReviewDecision

    @field_validator("command_id")
    @classmethod
    def safe_command_id(cls, value: str) -> str:
        if any(ord(c) < 32 or ord(c) == 127 for c in value):
            raise ValueError("command_id cannot contain control characters")
        return value


def _ledger_digest(events: tuple[ReviewEvent, ...], snapshot_id: str, question_id: str) -> str:
    """Reproduce C's ledger digest from the recorded events only (INV-05)."""
    return canonical_digest(
        {
            "schema_version": 1,
            "snapshot_id": snapshot_id,
            "question_id": question_id,
            "revision": len(events),
            "events": [
                {
                    "command_id": event.command_id,
                    "decision": event.decision.model_dump(mode="json"),
                }
                for event in events
            ],
        }
    )


def _check_metadata(value: Mapping[str, Any], *, where: str) -> None:
    """SEC-01, FR-E-02: reject credentials and local paths anywhere in run metadata."""
    for key, item in value.items():
        lowered = str(key).lower()
        if any(marker in lowered for marker in SENSITIVE_KEY_MARKERS):
            raise ValueError(f"{where} must not contain credential-like key {key!r}")
        if isinstance(item, Mapping):
            _check_metadata(item, where=where)
        elif isinstance(item, (list, tuple)):
            for element in item:
                if isinstance(element, Mapping):
                    _check_metadata(element, where=where)
                elif isinstance(element, str) and contains_absolute_path(element):
                    raise ValueError(f"{where} must not contain local absolute paths")
        elif isinstance(item, str) and contains_absolute_path(item):
            raise ValueError(f"{where} must not contain local absolute paths")


class ResearchRecord(_ReportModel):
    """FR-E-01/02: immutable snapshot+evidence+ledger+draft+release research package."""

    record_schema_version: Literal[1]
    record_id: RecordId
    saved_at: UTCTimestamp
    question: NonBlank
    snapshot: CorpusSnapshot
    evidence: tuple[EvidenceRecord, ...]
    review_events: tuple[ReviewEvent, ...]
    review_revision: int = Field(strict=True, ge=0)
    review_digest: Sha256
    draft: AnswerDraft
    release: ReleaseDecision
    run_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("record_schema_version", mode="before")
    @classmethod
    def explicit_schema(cls, value: object) -> int:
        if type(value) is not int or value != 1:
            raise ValueError("record_schema_version must be the explicit integer 1")
        return value

    @field_validator("question", mode="after")
    @classmethod
    def safe_question(cls, value: str) -> str:
        return _strip_control(_reject_absolute_path(value))

    @model_validator(mode="after")
    def consistent_package(self) -> Self:
        """INV-02/04/05: associations, ledger replay and no status promotion."""
        snapshot_id = self.snapshot.snapshot_id
        documents = {doc.document_id: doc for doc in self.snapshot.documents}
        question_id = self.draft.question_id

        evidence_ids: set[str] = set()
        for item in self.evidence:
            if item.evidence_id in evidence_ids:
                raise ValueError("record contains duplicate evidence identity")
            evidence_ids.add(item.evidence_id)
            if item.snapshot_id != snapshot_id:
                raise ValueError("evidence belongs to a different snapshot")
            document: DocumentVersion | None = documents.get(item.document_id)
            if document is None:
                raise ValueError("evidence document is absent from the snapshot")
            if document.version_sha256 != item.version_sha256:
                raise ValueError("evidence version does not match the snapshot document")
        if not self.evidence:
            raise ValueError("record requires at least one evidence item")

        if len(self.review_events) != self.review_revision:
            raise ValueError("review_revision does not match replayed ledger length")
        if self.review_revision == 0:
            raise ValueError("record requires at least one human review event")
        seen_commands: set[str] = set()
        for event in self.review_events:
            decision = event.decision
            if event.command_id in seen_commands:
                raise ValueError("duplicate ledger command_id")
            seen_commands.add(event.command_id)
            if decision.snapshot_id != snapshot_id:
                raise ValueError("review event belongs to a different snapshot")
            if decision.question_id != question_id:
                raise ValueError("review event belongs to a different question")
            if decision.evidence_id not in evidence_ids:
                raise ValueError("review event references unknown evidence")
        if _ledger_digest(self.review_events, snapshot_id, question_id) != self.review_digest:
            raise ValueError("review_digest does not match recorded ledger")

        for label, bound in (("draft", self.draft), ("release", self.release)):
            if bound.snapshot_id != snapshot_id:
                raise ValueError(f"{label} belongs to a different snapshot")
            if bound.question_id != question_id:
                raise ValueError(f"{label} belongs to a different question")
            if bound.review_revision != self.review_revision:
                raise ValueError(f"{label} review_revision does not match ledger")
            if bound.review_digest != self.review_digest:
                raise ValueError(f"{label} review_digest does not match ledger")
        if self.draft.answer_id != self.release.answer_id:
            raise ValueError("release decision judges a different answer")
        for name in ("approved_evidence_ids", "sent_evidence_ids", "citation_evidence_ids"):
            if not set(getattr(self.draft, name)) <= evidence_ids:
                raise ValueError(f"draft {name} reference outside record evidence")
        if self.release.status == "released" and self.draft.status != "draft":
            raise ValueError("released requires an answer draft, not abstained/failed")

        _check_metadata(self.run_metadata, where="run_metadata")
        return self


class ExportPermission(_ReportModel):
    """FR-E-02, SEC-01: declared export grant; authority is only the trusted verifier.

    A grant may declare a read-only purpose such as ``internal-read``; rejecting the
    purpose is the exporter's job, so construction stays permissive and type-visible.
    """

    record_id: RecordId
    evidence_ids: tuple[EvidenceId, ...]
    purpose: Literal["external-export", "internal-read"]
    granted_by: NonBlank

    @field_validator("evidence_ids")
    @classmethod
    def unique_grants(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("permission contains duplicate evidence identity")
        return value

    @field_validator("granted_by")
    @classmethod
    def safe_grantor(cls, value: str) -> str:
        return _strip_control(_reject_absolute_path(value))


def to_validation_error(error: ValidationError) -> InvalidRecord:
    """FR-E-02: surface malformed packages as one explicit E error type."""
    return InvalidRecord(f"invalid research record: {error.error_count()} problem(s)")


def parse_record(raw: str | bytes | Mapping[str, Any]) -> ResearchRecord:
    """FR-E-01: read back only through the closed envelope; no silent repair."""
    try:
        if isinstance(raw, (str, bytes)):
            data = json.loads(raw)
        else:
            data = dict(raw)
        return ResearchRecord.model_validate(data)
    except ValidationError as error:
        raise to_validation_error(error) from None
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
        raise InvalidRecord("research record is not readable JSON") from None


def record_conflict_for(record_id: str) -> RecordConflict:
    """INV-05/08: one conflict message shape shared by store and callers."""
    return RecordConflict(f"history record already exists: {record_id}")
