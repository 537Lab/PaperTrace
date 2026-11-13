"""Deterministic shared data interfaces only; no PaperQA or model calls.

Architecture: ADR-001; QA-01; INV-01..04; SEC-01. See docs/contracts/schema.md.
"""

import json
from collections.abc import Mapping, Sequence
from datetime import timezone
from hashlib import sha256
from typing import Annotated, Any, Literal, Self

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StringConstraints,
    field_validator,
    model_validator,
)

UTCTimestamp = Annotated[
    AwareDatetime, AfterValidator(lambda value: value.astimezone(timezone.utc))
]
PositiveInt = Annotated[int, Field(strict=True, ge=1)]
ReviewRevision = Annotated[int, Field(strict=True, ge=0)]
ReasonCode = Annotated[str, StringConstraints(strict=True, pattern=r"^[A-Z][A-Z0-9_]{0,63}$")]
AnswerId = Annotated[str, StringConstraints(strict=True, pattern=r"^ans-[a-z0-9][a-z0-9_-]{0,63}$")]
QuestionId = Annotated[str, StringConstraints(strict=True, pattern=r"^q-[a-z0-9][a-z0-9_-]{0,63}$")]
ReviewerRef = Annotated[
    str, StringConstraints(strict=True, pattern=r"^reviewer-[A-Z][A-Z0-9_-]{0,31}$")
]
EvidenceId = Annotated[str, StringConstraints(strict=True, pattern=r"^ev-[0-9a-f]{64}$")]
SnapshotId = Annotated[str, StringConstraints(strict=True, pattern=r"^snap-[0-9a-f]{64}$")]
Sha256 = Annotated[str, StringConstraints(strict=True, pattern=r"^[0-9a-f]{64}$")]
DocumentId = Annotated[
    str, StringConstraints(strict=True, pattern=r"^doc-[a-z0-9][a-z0-9_-]{0,63}$")
]
NonBlank = Annotated[str, StringConstraints(strict=True, min_length=1, pattern=r"\S")]


class ContractModel(BaseModel):
    """QA-01, SEC-01: closed, immutable shared interface envelope."""

    model_config = ConfigDict(frozen=True, extra="forbid", revalidate_instances="always")
    schema_version: Literal[1]

    @field_validator("schema_version", mode="before")
    @classmethod
    def explicit_schema_version(cls, value: object) -> int:
        """INV-02, QA-01: preserve protocol values rather than coercing them."""
        if type(value) is not int or value != 1:
            raise ValueError("schema_version must be the explicit integer 1")
        return value


class DocumentVersion(ContractModel):
    """INV-02: a logical document and its distinct content version."""

    document_id: DocumentId
    version_sha256: Sha256
    title: NonBlank
    source_name: NonBlank
    status: Literal["ready"]

    @field_validator("source_name")
    @classmethod
    def safe_source_name(cls, value: str) -> str:
        """QA-01, SEC-01: store a display basename, never a path or control sequence."""
        if value in {".", ".."} or any(c in value for c in "/\\:"):
            raise ValueError("source_name must be a pure filename")
        if any(ord(c) < 32 or ord(c) == 127 for c in value):
            raise ValueError("source_name cannot contain control characters")
        return value


def _canonical_hash(payload: Mapping[str, object]) -> str:
    """INV-02, QA-01: UTF-8 canonical JSON, no lossy normalization or non-finite numbers."""
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _snapshot_id(documents: Sequence[DocumentVersion]) -> str:
    """INV-02, QA-01: identity covers complete ready metadata, not capture time."""
    return "snap-" + _canonical_hash(
        {
            "schema_version": 1,
            "documents": [
                doc.model_dump(mode="json")
                for doc in sorted(documents, key=lambda item: item.document_id)
            ],
        }
    )


class CorpusSnapshot(ContractModel):
    """INV-02, QA-01: immutable, deterministically identified ready corpus."""

    documents: tuple[DocumentVersion, ...]
    created_at: UTCTimestamp
    snapshot_id: SnapshotId = Field(default_factory=lambda data: _snapshot_id(data["documents"]))

    @model_validator(mode="after")
    def canonical_order(self) -> Self:
        """INV-02, QA-01: a single document ordering in memory and serialized output."""
        ids = [doc.document_id for doc in self.documents]
        if len(ids) != len(set(ids)):
            raise ValueError("snapshot has duplicate document identity")
        if self.snapshot_id != _snapshot_id(self.documents):
            raise ValueError("snapshot_id does not match canonical documents")
        object.__setattr__(
            self, "documents", tuple(sorted(self.documents, key=lambda item: item.document_id))
        )
        return self


class SourceLocator(ContractModel):
    """INV-02, INV-04: parser metadata and page/line ranges, never free-form locations."""

    page_start: PositiveInt | None = None
    page_end: PositiveInt | None = None
    line_start: PositiveInt | None = None
    line_end: PositiveInt | None = None
    chunk_id: NonBlank
    parser_name: NonBlank
    parser_version: NonBlank

    @model_validator(mode="after")
    def valid_ranges(self) -> Self:
        """INV-02, INV-04: at least one complete 1-based inclusive range is required."""
        if self.page_start is None and self.line_start is None:
            raise ValueError("locator needs a page or line range")
        for start, end in ((self.page_start, self.page_end), (self.line_start, self.line_end)):
            if (start is None) != (end is None):
                raise ValueError("locator range needs both start and end")
            if start is not None and end is not None and end < start:
                raise ValueError("locator range is reversed")
        return self


def _evidence_id(data: dict[str, Any]) -> str:
    """INV-03, INV-02, INV-04, QA-01: advisory summaries, upstream IDs and retrieval time excluded."""
    payload = {
        key: data[key]
        for key in ("schema_version", "snapshot_id", "document_id", "version_sha256", "excerpt")
    }
    payload["locator"] = data["locator"].model_dump(mode="json")
    return "ev-" + _canonical_hash(payload)


class EvidenceRecord(ContractModel):
    """INV-03, INV-02, INV-04: exact excerpt and provenance only; no accepted/status field."""

    snapshot_id: SnapshotId
    document_id: DocumentId
    version_sha256: Sha256
    locator: SourceLocator
    excerpt: NonBlank
    retrieved_at: UTCTimestamp
    advisory_summary: str | None = None
    upstream_context_id: str | None = None
    evidence_id: EvidenceId = Field(default_factory=_evidence_id)

    @model_validator(mode="after")
    def canonical_identity(self) -> Self:
        """INV-02, INV-04, QA-01: a caller-supplied evidence hash must match its provenance."""
        if self.evidence_id != _evidence_id(self.__dict__):
            raise ValueError("evidence_id does not match canonical provenance")
        return self


class ReviewDecision(ContractModel):
    """INV-03: human review event; authenticity belongs to C's future ledger."""

    evidence_id: EvidenceId
    snapshot_id: SnapshotId
    question_id: QuestionId
    status: Literal["pending", "accepted", "excluded"]
    actor_kind: Literal["human"]
    reviewer_ref: ReviewerRef
    revision: PositiveInt
    reason: NonBlank
    decided_at: UTCTimestamp


class AnswerDraft(ContractModel):
    """INV-04, INV-02, INV-01, QA-01: declared review scope, not proof of a genuine current ledger."""

    answer_id: AnswerId
    snapshot_id: SnapshotId
    question_id: QuestionId
    review_revision: ReviewRevision
    review_digest: Sha256
    approved_evidence_ids: tuple[EvidenceId, ...] = Field(json_schema_extra={"uniqueItems": True})
    sent_evidence_ids: tuple[EvidenceId, ...] = Field(json_schema_extra={"uniqueItems": True})
    citation_evidence_ids: tuple[EvidenceId, ...] = Field(json_schema_extra={"uniqueItems": True})
    status: Literal["draft", "abstained", "failed"]
    body: str
    refusal_reason: str | None = None
    generated_at: UTCTimestamp

    @model_validator(mode="after")
    def valid_scope(self) -> Self:
        """INV-04, INV-02: cited subset of sent subset of approved, without aliases."""
        for name in ("approved_evidence_ids", "sent_evidence_ids", "citation_evidence_ids"):
            values = getattr(self, name)
            if len(values) != len(set(values)):
                raise ValueError(f"{name} contains duplicate evidence identity")
        if not set(self.sent_evidence_ids) <= set(self.approved_evidence_ids):
            raise ValueError("sent evidence is outside approved scope")
        if not set(self.citation_evidence_ids) <= set(self.sent_evidence_ids):
            raise ValueError("citation evidence is outside sent scope")
        if self.status == "draft":
            if self.review_revision == 0:
                raise ValueError("draft requires a nonzero human-review revision")
            if (
                not self.approved_evidence_ids
                or not self.sent_evidence_ids
                or not self.body.strip()
            ):
                raise ValueError("draft requires approved and sent evidence and a nonempty body")
            if self.refusal_reason is not None:
                raise ValueError("draft cannot contain refusal_reason")
        else:
            if self.body != "" or self.citation_evidence_ids:
                raise ValueError("abstained/failed answer must have empty body and no citations")
            if self.refusal_reason is None or not self.refusal_reason.strip():
                raise ValueError("abstained/failed answer needs refusal_reason")
        return self


class ReleaseDecision(ContractModel):
    """INV-04: deterministic check claims; never a substitute for D's checks."""

    answer_id: AnswerId
    snapshot_id: SnapshotId
    question_id: QuestionId
    review_revision: ReviewRevision
    review_digest: Sha256
    status: Literal["released", "blocked"]
    reason_codes: tuple[ReasonCode, ...] = Field(json_schema_extra={"uniqueItems": True})
    snapshot_check_passed: StrictBool
    review_check_passed: StrictBool
    evidence_check_passed: StrictBool
    citation_check_passed: StrictBool
    answer_check_passed: StrictBool
    decided_at: UTCTimestamp

    @model_validator(mode="after")
    def consistent_decision(self) -> Self:
        """INV-04: released claims require every structural check and no reason."""
        if len(self.reason_codes) != len(set(self.reason_codes)):
            raise ValueError("duplicate release reason code")
        checks = (
            self.snapshot_check_passed,
            self.review_check_passed,
            self.evidence_check_passed,
            self.citation_check_passed,
            self.answer_check_passed,
        )
        if self.status == "released" and (
            self.review_revision == 0 or not all(checks) or self.reason_codes
        ):
            raise ValueError("released requires all checks true and no reason codes")
        if self.status == "blocked" and not self.reason_codes:
            raise ValueError("blocked requires at least one reason code")
        return self
