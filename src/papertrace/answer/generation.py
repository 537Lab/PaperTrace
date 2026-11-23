"""D generation coordinator: one controlled call through a B-neutral port.

Traceability: FR-D-02, FR-D-03 (partial), INV-01, INV-03, INV-04, INV-07 (partial).
This module owns D's pre-call gates, result validation/reconciliation and draft
mapping. It deliberately knows nothing about PaperQA2, B internals, SDKs, HTTP,
publication or release decisions. The port adapter is separate follow-up work.
"""

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Annotated, Literal, Protocol, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from papertrace.answer.eligibility import assess_eligibility
from papertrace.answer.model import (
    REFUSAL_NO_APPROVED_EVIDENCE,
    AnswerRequest,
    ReviewProjectionPort,
)
from papertrace.contracts import (
    AnswerDraft,
    CorpusSnapshot,
    EvidenceId,
    EvidenceRecord,
    NonBlank,
    QuestionId,
    ReviewRevision,
    Sha256,
)

REASON_EMPTY_SELECTION = "EMPTY_SELECTION"
REASON_SELECTION_OUTSIDE_APPROVED = "SELECTION_OUTSIDE_APPROVED"
REASON_STALE_REVIEW = "STALE_REVIEW_DURING_GENERATION"
REASON_GENERATION_REFUSED = "GENERATION_REFUSED"
REASON_EMPTY_OUTPUT = "EMPTY_OUTPUT"
REASON_RESULT_SHAPE_INVALID = "RESULT_SHAPE_INVALID"
REASON_UNKNOWN_CITATIONS = "UNKNOWN_CITATIONS"
REASON_AMBIGUOUS_CITATIONS = "AMBIGUOUS_CITATIONS"
REASON_SENT_OUTSIDE_APPROVED = "SENT_OUTSIDE_APPROVED"
REASON_SENT_OUTSIDE_SELECTED = "SENT_OUTSIDE_SELECTED"
REASON_CITATION_OUTSIDE_SENT = "CITATION_OUTSIDE_SENT"

_MARKER = re.compile(r"\(([^()]*)\)")
_TOKEN_SEPARATOR = re.compile(r"[\s,;]+")

_DraftStatus = Literal["draft", "abstained", "failed"]


class GenerationPolicySpec(BaseModel):
    """FR-D-03/INV-07: only the policy fields this slice forwards to B."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: NonBlank
    model: NonBlank
    max_input_tokens: Annotated[int, Field(strict=True, ge=1, le=12000)] = 12000
    compress_at_tokens: Annotated[int, Field(strict=True, ge=1)] = 9000
    max_output_tokens: Annotated[int, Field(strict=True, ge=1, le=2000)] = 2000
    max_sources: Annotated[int, Field(strict=True, ge=1)] | None = None
    get_evidence_if_no_contexts: bool = False
    pre_prompt: None = None
    post_prompt: None = None
    autonomous_agent: bool = False

    @field_validator("get_evidence_if_no_contexts", "autonomous_agent", mode="before")
    @classmethod
    def exactly_false(cls, value: object) -> bool:
        """INV-07: safety switches stay exactly False; no truthy coercion."""
        if value is not False:
            raise ValueError("safety switch must be exactly False")
        return False

    @model_validator(mode="after")
    def compress_within_input_cap(self) -> Self:
        """INV-07: compression cannot exceed the input window or B's 9000 cap."""
        if self.compress_at_tokens > min(9000, self.max_input_tokens):
            raise ValueError("compress_at_tokens exceeds min(9000, max_input_tokens)")
        return self


class AnswerGenerationRequest(BaseModel):
    """FR-D-01/FR-D-03: typed outer request; the question id stays D-local."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    base: AnswerRequest
    question_text: NonBlank
    selected_evidence_ids: tuple[EvidenceId, ...]
    policy: GenerationPolicySpec

    @field_validator("selected_evidence_ids")
    @classmethod
    def unique_selection(cls, value: tuple[EvidenceId, ...]) -> tuple[EvidenceId, ...]:
        """INV-01: selection is an identity set, not a multiset."""
        if len(set(value)) != len(value):
            raise ValueError("selected_evidence_ids contains duplicate identity")
        return value


class GenerationCallRequest(BaseModel):
    """FR-D-03: B-neutral payload; deliberately no question_id."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    snapshot: CorpusSnapshot
    question_text: NonBlank
    approved_evidence: tuple[EvidenceRecord, ...]
    selected_evidence_ids: tuple[EvidenceId, ...]
    review_revision: ReviewRevision
    review_digest: Sha256
    policy: GenerationPolicySpec

    @field_validator("selected_evidence_ids")
    @classmethod
    def unique_selection(cls, value: tuple[EvidenceId, ...]) -> tuple[EvidenceId, ...]:
        """INV-01: selection stays unique on the outbound request too."""
        if len(set(value)) != len(value):
            raise ValueError("selected_evidence_ids contains duplicate identity")
        return value


class GenerationAccounting(BaseModel):
    """FR-D-03: immutable diagnostic accounting carried from B's public result.

    ``answer_model_attempts`` observes entries into B's answer-model boundary; it
    is not D's gateway-call count and never authorizes a draft or release.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: NonBlank
    model: NonBlank
    answer_model_attempts: Annotated[int, Field(strict=True, ge=0)] | None = None


class GenerationCallResult(BaseModel):
    """FR-D-02: permissive B-neutral result; the coordinator checks semantics."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: Literal["REFUSED", "SUCCESS", "AMBIGUOUS_CITATIONS"]
    raw_output: str
    sent_evidence_ids: tuple[str, ...]
    citation_aliases: tuple[tuple[str, str], ...]
    unknown_citation_keys: tuple[str, ...]
    ambiguous_citation_keys: tuple[str, ...]
    refusal_reason: str | None
    invalid_sent_evidence_ids: tuple[str, ...] = ()
    accounting: GenerationAccounting | None = None


class GenerationPort(Protocol):
    """FR-D-03: D's only outbound generation seam; B is never imported here."""

    def call(self, request: GenerationCallRequest) -> GenerationCallResult:
        """Return one B-neutral generation result."""
        ...


class GenerationResultShapeError(Exception):
    """The adapter could not convert an external B result into D's typed shape."""


class AnswerGenerationOutcome(BaseModel):
    """FR-D-02/INV-04: diagnostics plus a non-release AnswerDraft.

    There is deliberately no usage, truncation-evidence or release field in this
    slice; ``truncation`` is always ``"unknown"``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    draft: AnswerDraft | None
    reason: str | None
    revision_before: int | None
    revision_after: int | None
    digest_before: str | None
    digest_after: str | None
    sent_request: GenerationCallRequest | None
    result: GenerationCallResult | None
    raw_unknown_keys: tuple[str, ...]
    truncation: Literal["unknown"] = "unknown"
    question_id: QuestionId
    question_text: str


@dataclass(frozen=True)
class _ResultCheck:
    reason: str | None
    raw_unknown_keys: tuple[str, ...]


def extract_citation_keys(raw_output: str) -> tuple[str, ...]:
    """Section 4 convention: parenthesized, whitespace/comma/semicolon groups."""
    keys: list[str] = []
    seen: set[str] = set()
    for marker in _MARKER.finditer(raw_output):
        for token in _TOKEN_SEPARATOR.split(marker.group(1).strip()):
            if token and token not in seen:
                seen.add(token)
                keys.append(token)
    return tuple(keys)


def _blank_or_duplicate(values: Sequence[object]) -> bool:
    """FR-D-02: reported identifiers and keys are nonblank and unique."""
    strings: list[str] = []
    for value in values:
        if not isinstance(value, str) or not value.strip():
            return True
        strings.append(value)
    return len(set(strings)) != len(strings)


def _result_shape_invalid(result: GenerationCallResult) -> bool:
    """FR-D-02: field-level shape before any cross-field set check."""
    if not isinstance(result.raw_output, str):
        return True
    if _blank_or_duplicate(result.sent_evidence_ids):
        return True
    if _blank_or_duplicate(result.unknown_citation_keys):
        return True
    if _blank_or_duplicate(result.ambiguous_citation_keys):
        return True
    if _blank_or_duplicate(result.invalid_sent_evidence_ids):
        return True
    alias_keys: list[str] = []
    for entry in result.citation_aliases:
        if not isinstance(entry, tuple) or len(entry) != 2:
            return True
        key, target = entry
        if (
            not isinstance(key, str)
            or not isinstance(target, str)
            or not key.strip()
            or not target.strip()
        ):
            return True
        alias_keys.append(key)
    if len(set(alias_keys)) != len(alias_keys):
        return True
    if result.refusal_reason is not None:
        if (
            not isinstance(result.refusal_reason, str)
            or not result.refusal_reason.strip()
        ):
            return True
    return False


def _status_reason_inconsistent(result: GenerationCallResult) -> bool:
    """FR-D-02: only a refusal carries a refusal reason in this contract."""
    if result.status == "REFUSED":
        return result.refusal_reason is None
    return result.refusal_reason is not None


def _raw_unknown_diagnostic(result: GenerationCallResult) -> tuple[str, ...]:
    """INV-04: extraction-ordered raw keys that no report resolves.

    Shape/reconciliation failures still expose genuinely unknown extracted keys
    instead of losing them. Only a nonblank alias key with a nonblank target, or
    a reported ambiguous key, resolves/excludes a key; a blank alias is not a
    resolution, and reported unknown keys stay unknown. Duplicate mappings and
    overlapping unknown/ambiguous reports remain failures, never successes.
    """
    raw_output = result.raw_output
    if not isinstance(raw_output, str):
        return ()
    resolved: set[str] = set()
    aliases = result.citation_aliases
    if isinstance(aliases, (tuple, list)):
        for entry in aliases:
            if not isinstance(entry, (tuple, list)) or len(entry) != 2:
                continue
            key, target = entry
            if (
                isinstance(key, str)
                and isinstance(target, str)
                and key.strip()
                and target.strip()
            ):
                resolved.add(key)
    reported_ambiguous = result.ambiguous_citation_keys
    ambiguous = (
        {key for key in reported_ambiguous if isinstance(key, str)}
        if isinstance(reported_ambiguous, (tuple, list))
        else set()
    )
    return tuple(
        key
        for key in extract_citation_keys(raw_output)
        if key not in resolved and key not in ambiguous
    )


def _invalid_sent_contract_invalid(result: GenerationCallResult) -> bool:
    """Section 14: an INVALID_SENT_EVIDENCE refusal has no sent or alias payload.

    The unauthorized IDs travel only in ``invalid_sent_evidence_ids`` for D's
    internal diagnostics; nonempty sent/alias data would otherwise reach the
    ordinary authorization checks before the refusal is recognized.
    """
    if result.status != "REFUSED" or result.refusal_reason != "INVALID_SENT_EVIDENCE":
        return False
    return bool(result.sent_evidence_ids or result.citation_aliases)


def _partition_valid(
    result: GenerationCallResult, extracted: tuple[str, ...]
) -> bool:
    """INV-04: resolved, unknown and ambiguous keys partition extracted keys."""
    resolved = {key for key, _ in result.citation_aliases}
    unknown = set(result.unknown_citation_keys)
    ambiguous = set(result.ambiguous_citation_keys)
    if resolved & unknown or resolved & ambiguous or unknown & ambiguous:
        return False
    return resolved | unknown | ambiguous == set(extracted)


def _check_result(
    *, result: GenerationCallResult, approved: set[str], selected: set[str]
) -> _ResultCheck:
    """FR-D-02/INV-04: ordered, fail-closed result validation."""
    if _result_shape_invalid(result) or _status_reason_inconsistent(result):
        return _ResultCheck(
            REASON_RESULT_SHAPE_INVALID, _raw_unknown_diagnostic(result)
        )
    if _invalid_sent_contract_invalid(result):
        return _ResultCheck(
            REASON_RESULT_SHAPE_INVALID, _raw_unknown_diagnostic(result)
        )

    sent = result.sent_evidence_ids
    if not set(sent) <= approved:
        return _ResultCheck(REASON_SENT_OUTSIDE_APPROVED, ())
    if not set(sent) <= selected:
        return _ResultCheck(REASON_SENT_OUTSIDE_SELECTED, ())
    if not {target for _, target in result.citation_aliases} <= set(sent):
        return _ResultCheck(REASON_CITATION_OUTSIDE_SENT, ())

    extracted = extract_citation_keys(result.raw_output)
    if not _partition_valid(result, extracted):
        return _ResultCheck(
            REASON_RESULT_SHAPE_INVALID, _raw_unknown_diagnostic(result)
        )

    if result.status == "REFUSED":
        return _ResultCheck(REASON_GENERATION_REFUSED, ())

    unknown = set(result.unknown_citation_keys)
    if unknown:
        # "Ordered, deduplicated" means extraction order, not adapter order.
        raw_unknown = tuple(key for key in extracted if key in unknown)
        return _ResultCheck(REASON_UNKNOWN_CITATIONS, raw_unknown)
    if result.ambiguous_citation_keys:
        return _ResultCheck(REASON_AMBIGUOUS_CITATIONS, ())
    if result.status == "AMBIGUOUS_CITATIONS":
        return _ResultCheck(REASON_RESULT_SHAPE_INVALID, ())
    if result.status == "SUCCESS":
        if not result.raw_output.strip():
            return _ResultCheck(REASON_EMPTY_OUTPUT, ())
        if not sent:
            return _ResultCheck(REASON_RESULT_SHAPE_INVALID, ())
        return _ResultCheck(None, ())
    return _ResultCheck(REASON_RESULT_SHAPE_INVALID, ())


def _deduplicate(values: Iterable[str]) -> tuple[str, ...]:
    """INV-04: keep first occurrence while dropping repeated evidence identity."""
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return tuple(ordered)


def _build_draft(
    *,
    request: AnswerGenerationRequest,
    revision: int,
    digest: str,
    approved: tuple[EvidenceId, ...],
    status: _DraftStatus,
    sent: tuple[EvidenceId, ...] = (),
    cited: tuple[EvidenceId, ...] = (),
    body: str = "",
    reason: str | None = None,
) -> AnswerDraft:
    """INV-04: copy validated tokens; never invent sent, cited or release state."""
    return AnswerDraft(
        schema_version=1,
        answer_id=request.base.answer_id,
        snapshot_id=request.base.snapshot.snapshot_id,
        question_id=request.base.question_id,
        review_revision=revision,
        review_digest=digest,
        approved_evidence_ids=approved,
        sent_evidence_ids=sent,
        citation_evidence_ids=cited,
        status=status,
        body=body,
        refusal_reason=reason,
        generated_at=request.base.requested_at,
    )


class AnswerGenerationService:
    """FR-D-01/FR-D-02/FR-D-03: one assessment, at most one port call, one draft."""

    def __init__(
        self, *, projections: ReviewProjectionPort, generation: GenerationPort
    ) -> None:
        self._projections = projections
        self._generation = generation

    def run(self, request: AnswerGenerationRequest) -> AnswerGenerationOutcome:
        """Read the projection, gate, call once, validate and map a draft."""
        projection = self._projections.read_projection(request.base.question_id)
        assessment = assess_eligibility(projection=projection, request=request.base)
        approved_ids = assessment.decision.approved_evidence_ids
        approved_set = set(approved_ids)
        selected_ids = request.selected_evidence_ids
        selected_set = set(selected_ids)

        if not approved_set:
            return self._pre_call_outcome(
                request=request,
                revision=assessment.revision,
                digest=assessment.digest,
                approved=(),
                status="abstained",
                reason=REFUSAL_NO_APPROVED_EVIDENCE,
            )
        if not selected_set:
            return self._pre_call_outcome(
                request=request,
                revision=assessment.revision,
                digest=assessment.digest,
                approved=approved_ids,
                status="abstained",
                reason=REASON_EMPTY_SELECTION,
            )
        if not selected_set <= approved_set:
            return self._pre_call_outcome(
                request=request,
                revision=assessment.revision,
                digest=assessment.digest,
                approved=approved_ids,
                status="failed",
                reason=REASON_SELECTION_OUTSIDE_APPROVED,
            )

        records_by_id = {
            record.evidence_id: record for record in request.base.evidence
        }
        approved_records = tuple(
            records_by_id[evidence_id] for evidence_id in approved_ids
        )
        call_request = GenerationCallRequest(
            snapshot=request.base.snapshot,
            question_text=request.question_text,
            approved_evidence=approved_records,
            selected_evidence_ids=selected_ids,
            review_revision=assessment.revision,
            review_digest=assessment.digest,
            policy=request.policy,
        )

        result: GenerationCallResult | None
        check: _ResultCheck
        try:
            candidate: object = self._generation.call(call_request)
        except GenerationResultShapeError:
            result = None
            check = _ResultCheck(REASON_RESULT_SHAPE_INVALID, ())
        else:
            if isinstance(candidate, GenerationCallResult):
                result = candidate
                check = _check_result(
                    result=candidate,
                    approved=approved_set,
                    selected=selected_set,
                )
            else:
                result = None
                check = _ResultCheck(REASON_RESULT_SHAPE_INVALID, ())

        post_projection = self._projections.read_projection(request.base.question_id)
        post_assessment = assess_eligibility(
            projection=post_projection, request=request.base
        )
        stale = (
            post_assessment.revision != assessment.revision
            or post_assessment.digest != assessment.digest
        )

        if check.reason is not None:
            return self._failure_outcome(
                request=request,
                call_request=call_request,
                result=result,
                reason=check.reason,
                raw_unknown_keys=check.raw_unknown_keys,
                approved=approved_ids,
                draft_revision=assessment.revision,
                draft_digest=assessment.digest,
                revision_before=assessment.revision,
                digest_before=assessment.digest,
                revision_after=post_assessment.revision,
                digest_after=post_assessment.digest,
            )
        if stale:
            return self._failure_outcome(
                request=request,
                call_request=call_request,
                result=result,
                reason=REASON_STALE_REVIEW,
                raw_unknown_keys=(),
                approved=post_assessment.decision.approved_evidence_ids,
                draft_revision=post_assessment.revision,
                draft_digest=post_assessment.digest,
                revision_before=assessment.revision,
                digest_before=assessment.digest,
                revision_after=post_assessment.revision,
                digest_after=post_assessment.digest,
            )

        if result is None:
            # Defensive only: a missing result can never be a success.
            return self._failure_outcome(
                request=request,
                call_request=call_request,
                result=None,
                reason=REASON_RESULT_SHAPE_INVALID,
                raw_unknown_keys=(),
                approved=approved_ids,
                draft_revision=assessment.revision,
                draft_digest=assessment.digest,
                revision_before=assessment.revision,
                digest_before=assessment.digest,
                revision_after=post_assessment.revision,
                digest_after=post_assessment.digest,
            )

        cited = _deduplicate(
            target for _, target in result.citation_aliases
        )
        draft = _build_draft(
            request=request,
            revision=assessment.revision,
            digest=assessment.digest,
            approved=approved_ids,
            status="draft",
            sent=result.sent_evidence_ids,
            cited=cited,
            body=result.raw_output,
        )
        return AnswerGenerationOutcome(
            draft=draft,
            reason=None,
            revision_before=assessment.revision,
            revision_after=post_assessment.revision,
            digest_before=assessment.digest,
            digest_after=post_assessment.digest,
            sent_request=call_request,
            result=result,
            raw_unknown_keys=(),
            question_id=request.base.question_id,
            question_text=request.question_text,
        )

    def _pre_call_outcome(
        self,
        *,
        request: AnswerGenerationRequest,
        revision: int,
        digest: str,
        approved: tuple[EvidenceId, ...],
        status: Literal["abstained", "failed"],
        reason: str,
    ) -> AnswerGenerationOutcome:
        """FR-D-01: a gate failure is decided before any port call."""
        draft = _build_draft(
            request=request,
            revision=revision,
            digest=digest,
            approved=approved,
            status=status,
            reason=reason,
        )
        return AnswerGenerationOutcome(
            draft=draft,
            reason=reason,
            revision_before=revision,
            revision_after=None,
            digest_before=digest,
            digest_after=None,
            sent_request=None,
            result=None,
            raw_unknown_keys=(),
            question_id=request.base.question_id,
            question_text=request.question_text,
        )

    def _failure_outcome(
        self,
        *,
        request: AnswerGenerationRequest,
        call_request: GenerationCallRequest,
        result: GenerationCallResult | None,
        reason: str,
        raw_unknown_keys: tuple[str, ...],
        approved: tuple[EvidenceId, ...],
        draft_revision: int,
        draft_digest: str,
        revision_before: int,
        digest_before: str,
        revision_after: int,
        digest_after: str,
    ) -> AnswerGenerationOutcome:
        """FR-D-02: a post-call failure never carries body, sent or citations."""
        draft = _build_draft(
            request=request,
            revision=draft_revision,
            digest=draft_digest,
            approved=approved,
            status="failed",
            reason=reason,
        )
        return AnswerGenerationOutcome(
            draft=draft,
            reason=reason,
            revision_before=revision_before,
            revision_after=revision_after,
            digest_before=digest_before,
            digest_after=digest_after,
            sent_request=call_request,
            result=result,
            raw_unknown_keys=raw_unknown_keys,
            question_id=request.base.question_id,
            question_text=request.question_text,
        )
