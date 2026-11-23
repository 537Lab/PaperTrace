"""Internal retrieval and generation implementation for Module B.

This module is the only place that touches ``paperqa``; the public gateway
re-exports the approved surface.  Everything here is offline-testable: the
adapter, source reader and model factory are injected collaborators, so the
suite can count calls and prove a fail-closed refusal made zero outbound
requests.

Traceability: FR-B-01/02, FR-D-03, INV-01..04, INV-07, INV-08, COST-01,
SEC-01.
"""

from __future__ import annotations

import asyncio
import copy
import hashlib
import importlib
import re
import tempfile
from collections.abc import Callable, Coroutine, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Protocol, TypeVar, cast, runtime_checkable

from papertrace.contracts import (
    CorpusSnapshot,
    DocumentVersion,
    EvidenceRecord,
    SourceLocator,
)

# --------------------------------------------------------------------------- #
# B-private result/refusal codes (NOT shared contracts: FR-B-02, INV-08)
# --------------------------------------------------------------------------- #


class RetrievalStatus(Enum):
    """B-private retrieval outcome; never added to shared contracts."""

    SUCCESS = "SUCCESS"
    EMPTY_RESULT = "EMPTY_RESULT"
    TIMEOUT = "TIMEOUT"
    PARSE_ERROR = "PARSE_ERROR"
    UPSTREAM_ERROR = "UPSTREAM_ERROR"


class GenerationStatus(Enum):
    """B-private generation outcome; review/release decisions stay elsewhere."""

    REFUSED = "REFUSED"
    SUCCESS = "SUCCESS"
    AMBIGUOUS_CITATIONS = "AMBIGUOUS_CITATIONS"
    INVALID_SENT_EVIDENCE = "INVALID_SENT_EVIDENCE"


REFUSAL_EMPTY_APPROVED = "EMPTY_APPROVED"
REFUSAL_SELECTED_OUTSIDE_APPROVED = "SELECTED_OUTSIDE_APPROVED"
REFUSAL_INVALID_BUDGET = "INVALID_BUDGET"
REFUSAL_UNSAFE_SESSION_POLICY = "UNSAFE_SESSION_POLICY"
REFUSAL_EMPTY_SENT = "EMPTY_SENT"
REFUSAL_EVIDENCE_OUTSIDE_SNAPSHOT = "EVIDENCE_OUTSIDE_SNAPSHOT"
REFUSAL_EVIDENCE_VERSION_MISMATCH = "EVIDENCE_VERSION_MISMATCH"
REFUSAL_MODEL_POLICY_MISMATCH = "MODEL_POLICY_MISMATCH"
REFUSAL_INPUT_BUDGET_EXCEEDED = "INPUT_BUDGET_EXCEEDED"

MAX_INPUT_TOKENS = 12000
COMPRESS_AT_TOKENS = 9000
MAX_OUTPUT_TOKENS = 2000


class UnsafeIndexError(RuntimeError):
    """INV-08: raised before an untrusted index/loader is ever touched."""


# --------------------------------------------------------------------------- #
# Injected collaborator protocols (production adapters implement these)
# --------------------------------------------------------------------------- #


@runtime_checkable
class SourceReader(Protocol):
    """A's controlled source-text port; keyword-only, version matched by B."""

    def __call__(
        self, *, snapshot_id: str, document_id: str, version_sha256: str
    ) -> bytes: ...


@runtime_checkable
class RetrievalAdapter(Protocol):
    """A single synchronous wrapper over ``Docs.aget_evidence`` (B-owned)."""

    def search(self, request: "RetrievalRequest") -> Any: ...


@runtime_checkable
class ModelFactory(Protocol):
    """Neutral model/session construction port; counts must be observable."""

    def create(self, *, policy: Any = None, contexts: Sequence[Any] = ()) -> Any: ...


# --------------------------------------------------------------------------- #
# Request/result shapes (approved B1 surface)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class RetrievalConfig:
    """Approved retrieval configuration; retries default to zero (FR-B-02)."""

    provider: str
    model: str
    max_retries: int = 0
    parser_name: str = "unknown-parser"
    parser_version: str = "0"

    def __post_init__(self) -> None:
        if self.max_retries < 0:
            raise ValueError("max_retries cannot be negative")


@dataclass(frozen=True)
class RetrievalRequest:
    """Fixed snapshot plus question plus approved config (FR-B-01)."""

    snapshot: CorpusSnapshot
    question: str
    config: RetrievalConfig


@dataclass(frozen=True)
class RetrievalAttempt:
    """One real attempt record; provider/model are fixed across retries."""

    stage: str
    provider: str
    model: str
    elapsed_seconds: float = 0.0


@dataclass(frozen=True)
class RetrievalResult:
    """Retrieval outcome: candidates plus attempts, or an explicit failure."""

    status: RetrievalStatus
    evidence: tuple[EvidenceRecord, ...] = ()
    attempts: tuple[RetrievalAttempt, ...] = ()
    stage: str | None = None


@dataclass(frozen=True)
class GenerationPolicy:
    """D-supplied generation policy; unsafe upstream features default off."""

    provider: str
    model: str
    max_input_tokens: int = MAX_INPUT_TOKENS
    compress_at_tokens: int = COMPRESS_AT_TOKENS
    max_output_tokens: int = MAX_OUTPUT_TOKENS
    max_sources: int | None = None
    get_evidence_if_no_contexts: bool = False
    pre_prompt: str | None = None
    post_prompt: str | None = None
    autonomous_agent: bool = False


@dataclass(frozen=True)
class GenerationRequest:
    """D→B neutral generation request; carries no review authority itself."""

    snapshot: CorpusSnapshot
    question: str
    approved_evidence: tuple[EvidenceRecord, ...]
    selected_evidence_ids: tuple[str, ...]
    policy: GenerationPolicy
    review_revision: int = 0
    review_digest: str = ""


@dataclass(frozen=True)
class GenerationResult:
    """Raw output plus actual-sent set and alias map; never a decision."""

    status: GenerationStatus
    raw_output: str = ""
    sent_evidence_ids: tuple[str, ...] = ()
    citation_aliases: tuple[tuple[str, str], ...] = ()
    unknown_citation_keys: tuple[str, ...] = ()
    ambiguous_citation_keys: tuple[str, ...] = ()
    refusal_reason: str | None = None
    invalid_sent_evidence_ids: tuple[str, ...] = ()


# --------------------------------------------------------------------------- #
# Concrete PaperQA2 bridge (the only production import boundary)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class _PaperQAOutcome:
    """Duck-typed outcome consumed by the ordinary verified retrieval path."""

    contexts: tuple[Any, ...] = ()
    failure: Any = None


@dataclass(frozen=True)
class _PaperQAContext:
    """PaperQA Context projected into B's provenance-bearing adapter shape."""

    document_id: str
    version_sha256: str
    excerpt: str
    line_start: int
    line_end: int
    chunk_id: str
    summary: str | None
    upstream_context_id: str
    page_start: int | None = None
    page_end: int | None = None


@dataclass(frozen=True)
class _PaperQACitationClaim:
    """One raw PaperQA citation key and its deterministic evidence candidate."""

    key: str
    candidates: tuple[str, ...]


@dataclass(frozen=True)
class _PaperQAGenerationOutput:
    """PaperQA answer projected into the neutral generation output shape."""

    raw_output: str
    citations: tuple[_PaperQACitationClaim, ...]
    sent_evidence_ids: tuple[str, ...] | None = None
    refusal_reason: str | None = None


@dataclass(frozen=True)
class _PaperQAFailure:
    """A concrete bridge failure with retry and stage information intact."""

    kind: str
    stage: str
    retryable: bool


class _GenerationRefusal(RuntimeError):
    """Internal fail-closed signal converted to a neutral refusal result."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


_T = TypeVar("_T")


def _run_immediate_coroutine(coroutine: Coroutine[Any, Any, _T]) -> _T:
    """Drive an injected no-I/O async recorder without opening an event loop.

    The approved offline test doubles complete on their first ``send``.  A
    suspending injected collaborator is rejected instead of silently creating
    an event-loop socket that would bypass the suite's network fence.
    """
    try:
        coroutine.send(None)
    except StopIteration as completed:
        return cast(_T, completed.value)
    coroutine.close()
    raise RuntimeError("injected Docs coroutine unexpectedly suspended")


class PaperQA2Adapter:
    """Concrete, synchronous B bridge over ``Docs``' approved async methods.

    Only controlled UTF-8 text sources are supported in this slice.  Binary
    PDF/OCR provenance needs a separately approved page reader; rejecting it is
    safer than inventing offsets or checking extracted text against PDF bytes.
    Models and settings are injected so offline deterministic doubles exercise
    the real ``Docs.aadd``/``aget_evidence``/``aquery`` paths without keys.
    """

    def __init__(
        self,
        *,
        source_reader: SourceReader,
        settings: Any,
        answer_llm_model: Any,
        summary_llm_model: Any,
        embedding_model: Any,
        docs_factory: Callable[..., Any] | None = None,
        temporary_directory: str | Path | None = None,
    ) -> None:
        self._source_reader = source_reader
        self._settings = settings
        self._answer_llm_model = answer_llm_model
        self._summary_llm_model = summary_llm_model
        self._embedding_model = embedding_model
        self._docs_factory = docs_factory
        self._temporary_directory = (
            Path(temporary_directory) if temporary_directory is not None else None
        )

    def _new_docs(self, *, name: str) -> Any:
        if self._docs_factory is not None:
            return self._docs_factory(name=name)
        paperqa = importlib.import_module("paperqa")
        return paperqa.Docs(name=name)

    def search(self, request: RetrievalRequest) -> _PaperQAOutcome:
        """Materialize controlled text, call ``aadd`` then ``aget_evidence``."""
        coroutine = self._search(request)
        if self._docs_factory is not None:
            return _run_immediate_coroutine(coroutine)
        return asyncio.run(coroutine)

    async def _search(self, request: RetrievalRequest) -> _PaperQAOutcome:
        docs = self._new_docs(name=f"papertrace-{request.snapshot.snapshot_id}")
        cache = _VerifiedSources()
        by_dockey: dict[str, tuple[DocumentVersion, bytes]] = {}
        temp_parent = (
            str(self._temporary_directory)
            if self._temporary_directory is not None
            else None
        )
        with tempfile.TemporaryDirectory(dir=temp_parent) as directory:
            root = Path(directory)
            for index, document in enumerate(request.snapshot.documents):
                if not document.source_name.lower().endswith(".txt"):
                    return _PaperQAOutcome(
                        failure=_PaperQAFailure(
                            kind="parse_error",
                            stage="source_decode",
                            retryable=False,
                        )
                    )
                try:
                    source = _verify_and_read_source(
                        self._source_reader, request.snapshot, document, cache
                    )
                    source.decode("utf-8")
                except (UnicodeDecodeError, ValueError):
                    return _PaperQAOutcome(
                        failure=_PaperQAFailure(
                            kind="parse_error",
                            stage="source_decode",
                            retryable=False,
                        )
                    )
                path = root / f"source-{index}.txt"
                path.write_bytes(source)
                dockey = document.document_id
                by_dockey[dockey] = (document, source)
                try:
                    await docs.aadd(
                        path,
                        citation=document.title,
                        docname=document.document_id,
                        dockey=dockey,
                        settings=self._settings,
                        llm_model=self._answer_llm_model,
                        embedding_model=self._embedding_model,
                    )
                except TimeoutError:
                    return _PaperQAOutcome(
                        failure=_PaperQAFailure(
                            kind="timeout", stage="aadd", retryable=True
                        )
                    )
                except Exception:
                    return _PaperQAOutcome(
                        failure=_PaperQAFailure(
                            kind="upstream_error", stage="aadd", retryable=False
                        )
                    )

            try:
                session = await docs.aget_evidence(
                    request.question,
                    settings=self._settings,
                    embedding_model=self._embedding_model,
                    summary_llm_model=self._summary_llm_model,
                )
            except TimeoutError:
                return _PaperQAOutcome(
                    failure=_PaperQAFailure(
                        kind="timeout", stage="aget_evidence", retryable=True
                    )
                )
            except Exception:
                return _PaperQAOutcome(
                    failure=_PaperQAFailure(
                        kind="upstream_error",
                        stage="aget_evidence",
                        retryable=False,
                    )
                )

        projected: list[_PaperQAContext] = []
        for context in tuple(getattr(session, "contexts", ()) or ()):
            text = getattr(context, "text", None)
            upstream_document = getattr(text, "doc", None)
            context_dockey = getattr(upstream_document, "dockey", None)
            document_source = (
                by_dockey.get(context_dockey)
                if isinstance(context_dockey, str)
                else None
            )
            if document_source is None:
                raise ValueError("PaperQA context is not bound to the fixed snapshot")
            document, source = document_source
            raw_excerpt = getattr(text, "text", None)
            if not isinstance(raw_excerpt, str):
                raise ValueError("PaperQA context has no source excerpt")
            excerpt = raw_excerpt.rstrip("\r\n")
            line_start, line_end = _locate_complete_lines(source, excerpt)
            upstream_id = getattr(context, "id", None)
            if not isinstance(upstream_id, str) or not upstream_id.strip():
                raise ValueError("PaperQA context has no stable context id")
            summary = getattr(context, "context", None)
            projected.append(
                _PaperQAContext(
                    document_id=document.document_id,
                    version_sha256=document.version_sha256,
                    excerpt=excerpt,
                    line_start=line_start,
                    line_end=line_end,
                    chunk_id=_stable_chunk_id(
                        document=document,
                        line_start=line_start,
                        line_end=line_end,
                        excerpt=excerpt,
                    ),
                    summary=summary if isinstance(summary, str) else None,
                    upstream_context_id=upstream_id,
                )
            )
        return _PaperQAOutcome(contexts=tuple(projected))

    def create(self, *, policy: Any = None, contexts: Sequence[Any] = ()) -> Any:
        """Create one fresh, selected-evidence-only PaperQA generation session."""
        if not isinstance(policy, _SessionPolicy):
            raise _GenerationRefusal(REFUSAL_MODEL_POLICY_MISMATCH)
        bound_provider = getattr(self._answer_llm_model, "provider", None)
        bound_model = getattr(self._answer_llm_model, "model", None)
        if bound_provider != policy.provider or bound_model != policy.model:
            raise _GenerationRefusal(REFUSAL_MODEL_POLICY_MISMATCH)
        return _PaperQAGenerationSession(
            bridge=self,
            policy=policy,
            contexts=tuple(contexts),
        )


# --------------------------------------------------------------------------- #
# Retrieval mapping / verification helpers
# --------------------------------------------------------------------------- #


@dataclass
class _VerifiedSources:
    """Cache of controlled source bytes verified against snapshot versions."""

    bytes_by_key: dict[tuple[str, str, str], bytes] = field(default_factory=dict)


def _verify_and_read_source(
    reader: SourceReader,
    snapshot: CorpusSnapshot,
    document: DocumentVersion,
    cache: _VerifiedSources,
) -> bytes:
    """Read once per document and re-check the content hash (INV-02)."""
    key = (snapshot.snapshot_id, document.document_id, document.version_sha256)
    if key not in cache.bytes_by_key:
        data = reader(
            snapshot_id=snapshot.snapshot_id,
            document_id=document.document_id,
            version_sha256=document.version_sha256,
        )
        digest = hashlib.sha256(data).hexdigest()
        if digest != document.version_sha256:
            raise ValueError("controlled source bytes do not match snapshot version")
        cache.bytes_by_key[key] = data
    return cache.bytes_by_key[key]


def _line_range(source: bytes, start: int | None, end: int | None) -> str | None:
    """Return the exact 1-based inclusive line text, or None if unverifiable."""
    if start is None or end is None or end < start:
        return None
    lines = source.decode("utf-8").splitlines()
    if start < 1 or end > len(lines):
        return None
    return "\n".join(lines[start - 1 : end])


def _normalized_source_text(source: bytes) -> str:
    """Decode controlled UTF-8 bytes with deterministic newline normalization."""
    return source.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")


def _excerpt_occurs_in_source(source: bytes, excerpt: str) -> bool:
    """Verify page-only text belongs to controlled bytes without guessing a page."""
    normalized_excerpt = excerpt.replace("\r\n", "\n").replace("\r", "\n")
    return normalized_excerpt in _normalized_source_text(source)


def _locate_complete_lines(source: bytes, excerpt: str) -> tuple[int, int]:
    """Return a unique exact 1-based line range, or fail closed."""
    normalized_source = _normalized_source_text(source)
    normalized_excerpt = excerpt.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized_excerpt:
        raise ValueError("PaperQA excerpt is empty")
    first = normalized_source.find(normalized_excerpt)
    if first < 0 or normalized_source.find(normalized_excerpt, first + 1) >= 0:
        raise ValueError("PaperQA excerpt is absent or ambiguous in controlled source")
    end_offset = first + len(normalized_excerpt)
    if first > 0 and normalized_source[first - 1] != "\n":
        raise ValueError("PaperQA excerpt does not begin at a verifiable line boundary")
    if end_offset < len(normalized_source) and normalized_source[end_offset] != "\n":
        raise ValueError("PaperQA excerpt does not end at a verifiable line boundary")
    line_start = normalized_source.count("\n", 0, first) + 1
    line_end = line_start + normalized_excerpt.count("\n")
    if _line_range(source, line_start, line_end) != normalized_excerpt:
        raise ValueError("PaperQA excerpt does not match its controlled source lines")
    return line_start, line_end


def _stable_chunk_id(
    *,
    document: DocumentVersion,
    line_start: int,
    line_end: int,
    excerpt: str,
) -> str:
    """Build identity only from fixed source provenance, never advisory IDs."""
    digest = hashlib.sha256()
    for value in (
        document.document_id,
        document.version_sha256,
        str(line_start),
        str(line_end),
        excerpt,
    ):
        encoded = value.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
    return f"paperqa-{digest.hexdigest()}"


def _map_context_to_evidence(
    context: Any,
    request: RetrievalRequest,
    reader: SourceReader,
    cache: _VerifiedSources,
    retrieved_at: datetime,
) -> EvidenceRecord:
    """Turn one upstream context into a real, verifiable EvidenceRecord."""
    snapshot = request.snapshot
    document_id = getattr(context, "document_id", None)
    version_sha256 = getattr(context, "version_sha256", None)
    excerpt = getattr(context, "excerpt", None)

    documents = {doc.document_id: doc for doc in snapshot.documents}
    document = documents.get(document_id) if isinstance(document_id, str) else None
    if document is None:
        raise ValueError("context document is not part of the fixed snapshot")
    if version_sha256 != document.version_sha256:
        raise ValueError("context version does not match snapshot document version")
    if not isinstance(excerpt, str) or not excerpt.strip():
        raise ValueError("context has no usable excerpt")

    source = _verify_and_read_source(reader, snapshot, document, cache)

    line_start = getattr(context, "line_start", None)
    line_end = getattr(context, "line_end", None)
    page_start = getattr(context, "page_start", None)
    page_end = getattr(context, "page_end", None)
    if line_start is not None or line_end is not None:
        if line_start is None or line_end is None:
            raise ValueError("line locator needs both endpoints")
        expected = _line_range(source, line_start, line_end)
        if expected is None:
            raise ValueError("line locator cannot be resolved in the controlled source")
        if expected != excerpt:
            raise ValueError("excerpt does not match the controlled source lines")
    elif page_start is not None or page_end is not None:
        if page_start is None or page_end is None:
            raise ValueError("page locator needs both endpoints")
        if not _excerpt_occurs_in_source(source, excerpt):
            raise ValueError("page-only excerpt does not occur in controlled source")

    chunk_id = getattr(context, "chunk_id", None)
    if not isinstance(chunk_id, str) or not chunk_id.strip():
        raise ValueError("context has no chunk identity")

    locator = SourceLocator(
        schema_version=1,
        page_start=page_start,
        page_end=page_end,
        line_start=line_start,
        line_end=line_end,
        chunk_id=chunk_id,
        parser_name=request.config.parser_name,
        parser_version=request.config.parser_version,
    )

    summary = getattr(context, "summary", None)
    upstream_id = getattr(context, "upstream_context_id", None)
    return EvidenceRecord(
        schema_version=1,
        snapshot_id=snapshot.snapshot_id,
        document_id=document.document_id,
        version_sha256=document.version_sha256,
        locator=locator,
        excerpt=excerpt,
        retrieved_at=retrieved_at,
        advisory_summary=summary if isinstance(summary, str) else None,
        upstream_context_id=upstream_id if isinstance(upstream_id, str) else None,
    )


_FAILURE_KIND_TO_STATUS = {
    "timeout": RetrievalStatus.TIMEOUT,
    "parse_error": RetrievalStatus.PARSE_ERROR,
    "upstream_error": RetrievalStatus.UPSTREAM_ERROR,
}


def _failure_status(failure: Any) -> tuple[RetrievalStatus, str]:
    """Map an injected failure to a distinct B-private status (FR-B-02)."""
    kind = getattr(failure, "kind", None)
    stage = getattr(failure, "stage", "aget_evidence")
    status = (
        _FAILURE_KIND_TO_STATUS.get(kind, RetrievalStatus.UPSTREAM_ERROR)
        if isinstance(kind, str)
        else RetrievalStatus.UPSTREAM_ERROR
    )
    return status, str(stage)


# --------------------------------------------------------------------------- #
# Retrieval execution
# --------------------------------------------------------------------------- #


def run_retrieval(
    *,
    request: RetrievalRequest,
    adapter: RetrievalAdapter,
    reader: SourceReader,
    clock: Any,
) -> RetrievalResult:
    """Execute bounded retrieval and verify every candidate provenance."""
    config = request.config
    attempts: list[RetrievalAttempt] = []
    cache = _VerifiedSources()
    max_attempts = max(0, int(config.max_retries)) + 1
    last_status = RetrievalStatus.UPSTREAM_ERROR
    last_stage: str | None = None

    for _ in range(max_attempts):
        attempts.append(
            RetrievalAttempt(
                stage="aget_evidence",
                provider=config.provider,
                model=config.model,
            )
        )
        try:
            outcome = adapter.search(request)
        except Exception:
            last_status, last_stage = RetrievalStatus.UPSTREAM_ERROR, "aget_evidence"
            last_retryable = False
        else:
            failure = getattr(outcome, "failure", None)
            if failure is not None:
                last_status, last_stage = _failure_status(failure)
                last_retryable = bool(getattr(failure, "retryable", False))
            else:
                contexts = tuple(getattr(outcome, "contexts", ()) or ())
                if not contexts:
                    return RetrievalResult(
                        status=RetrievalStatus.EMPTY_RESULT,
                        evidence=(),
                        attempts=tuple(attempts),
                    )
                retrieved_at = clock()
                evidence: dict[str, EvidenceRecord] = {}
                try:
                    for context in contexts:
                        record = _map_context_to_evidence(
                            context, request, reader, cache, retrieved_at
                        )
                        evidence.setdefault(record.evidence_id, record)
                except Exception:
                    return RetrievalResult(
                        status=RetrievalStatus.PARSE_ERROR,
                        evidence=(),
                        attempts=tuple(attempts),
                        stage="evidence_mapping",
                    )
                return RetrievalResult(
                    status=RetrievalStatus.SUCCESS,
                    evidence=tuple(evidence.values()),
                    attempts=tuple(attempts),
                )

        if not last_retryable:
            break

    return RetrievalResult(
        status=last_status,
        evidence=(),
        attempts=tuple(attempts),
        stage=last_stage,
    )


# --------------------------------------------------------------------------- #
# Generation validation / serialization
# --------------------------------------------------------------------------- #


def _validate_policy(policy: GenerationPolicy) -> str | None:
    """Return a refusal reason for an invalid budget, else None (INV-07)."""
    if not (1 <= policy.max_input_tokens <= MAX_INPUT_TOKENS):
        return REFUSAL_INVALID_BUDGET
    if not (1 <= policy.compress_at_tokens <= MAX_INPUT_TOKENS):
        return REFUSAL_INVALID_BUDGET
    if not (1 <= policy.max_output_tokens <= MAX_OUTPUT_TOKENS):
        return REFUSAL_INVALID_BUDGET
    if policy.compress_at_tokens > policy.max_input_tokens:
        return REFUSAL_INVALID_BUDGET
    if policy.max_sources is not None and policy.max_sources < 0:
        return REFUSAL_INVALID_BUDGET
    return None


def _validate_session_policy(policy: GenerationPolicy) -> str | None:
    """Return a refusal reason if unsafe implicit behaviour is enabled."""
    if policy.get_evidence_if_no_contexts:
        return REFUSAL_UNSAFE_SESSION_POLICY
    if policy.pre_prompt is not None or policy.post_prompt is not None:
        return REFUSAL_UNSAFE_SESSION_POLICY
    if policy.autonomous_agent:
        return REFUSAL_UNSAFE_SESSION_POLICY
    return None


@dataclass(frozen=True)
class _SessionContext:
    """Minimal context handed to the session; text is the verified excerpt."""

    evidence_id: str
    text: str


@dataclass(frozen=True)
class _SessionPolicy:
    """Sanitized policy actually handed to the factory (all flags off)."""

    provider: str
    model: str
    max_input_tokens: int
    compress_at_tokens: int
    max_output_tokens: int
    max_sources: int | None
    get_evidence_if_no_contexts: bool = False
    pre_prompt: str | None = None
    post_prompt: str | None = None
    autonomous_agent: bool = False


def _copy_answer_model(
    model: Any, *, max_output_tokens: int, preserve_legacy_identity: bool = False
) -> Any:
    """Bind D's output limit, copying modern model configurations."""
    copier = getattr(model, "model_copy", None)
    if preserve_legacy_identity:
        outbound = model
    else:
        outbound = copier(deep=True) if callable(copier) else copy.deepcopy(model)
    if hasattr(outbound, "max_tokens"):
        outbound.max_tokens = max_output_tokens
    config = getattr(outbound, "config", None)
    if isinstance(config, dict):
        model_list = config.get("model_list")
        if isinstance(model_list, list):
            for entry in model_list:
                if not isinstance(entry, dict):
                    continue
                parameters = entry.get("litellm_params")
                if isinstance(parameters, dict):
                    parameters["max_tokens"] = max_output_tokens
    return outbound


def _default_serialized_aliases(settings: Any, contexts: Sequence[Any]) -> tuple[str, ...]:
    """Mirror PaperQA's bounded score filter when no ID trace is exposed."""
    answer = getattr(settings, "answer", None)
    maximum = getattr(answer, "answer_max_sources", len(contexts))
    cutoff = getattr(answer, "evidence_relevance_score_cutoff", 0)
    try:
        limit = max(0, int(maximum))
    except (TypeError, ValueError):
        limit = len(contexts)
    try:
        threshold = float(cutoff)
    except (TypeError, ValueError):
        threshold = 0.0
    ordered = sorted(
        contexts,
        key=lambda item: (
            -float(getattr(item, "score", 0)),
            str(getattr(getattr(item, "text", None), "name", "")),
        ),
    )[:limit]
    return tuple(
        str(item.id)
        for item in ordered
        if float(getattr(item, "score", 0)) >= threshold
    )


async def _serialize_final_contexts(
    *, settings: Any, contexts: Sequence[Any], question: str
) -> tuple[str, tuple[str, ...]]:
    """Run the final serializer once and retain its observable selected IDs."""
    serializer = getattr(settings, "context_serializer", None)
    if callable(serializer):
        rendered = await serializer(
            contexts=contexts,
            question=question,
            pre_str=None,
        )
        serialized = rendered if isinstance(rendered, str) else str(rendered)
        observed = getattr(settings, "serialized_context_ids", None)
        if isinstance(observed, (tuple, list)):
            return serialized, tuple(str(item) for item in observed)
        return serialized, _default_serialized_aliases(settings, contexts)

    aliases = _default_serialized_aliases(settings, contexts)
    selected = {alias for alias in aliases}
    serialized = "\n".join(
        f"{getattr(item, 'id', '')}: {getattr(item, 'context', '')}"
        for item in contexts
        if getattr(item, "id", None) in selected
    )
    return serialized, aliases


def _final_prompt_text(*, settings: Any, serialized: str, question: str) -> str:
    """Build the system/context/question text whose tokens guard the call."""
    prompts = getattr(settings, "prompts", None)
    system = getattr(prompts, "system", "")
    answer = getattr(settings, "answer", None)
    answer_length = getattr(answer, "answer_length", "")
    qa_template = getattr(prompts, "qa", None)
    if isinstance(qa_template, str):
        try:
            user_prompt = qa_template.format(
                context=serialized,
                question=question,
                answer_length=answer_length,
            )
        except (KeyError, ValueError, IndexError):
            user_prompt = f"{serialized}\nQuestion: {question}"
    else:
        user_prompt = f"{serialized}\nQuestion: {question}"
    return f"{system}\n{user_prompt}"


@dataclass
class _PaperQAGenerationSession:
    """One-use synchronous wrapper over a fresh ``Docs.aquery`` session."""

    bridge: PaperQA2Adapter
    policy: _SessionPolicy
    contexts: tuple[_SessionContext, ...]
    _asked: bool = False

    def ask(self, question: str) -> _PaperQAGenerationOutput:
        if self._asked:
            raise RuntimeError("PaperQA generation sessions are single-use")
        self._asked = True
        coroutine = self._ask(question)
        if self.bridge._docs_factory is not None:
            return _run_immediate_coroutine(coroutine)
        return asyncio.run(coroutine)

    async def _ask(self, question: str) -> _PaperQAGenerationOutput:
        paperqa_types = importlib.import_module("paperqa.types")
        docs = self.bridge._new_docs(name="papertrace-approved-generation")
        settings = self.bridge._settings.model_copy(deep=True)
        settings.answer.get_evidence_if_no_contexts = False
        settings.answer.answer_max_sources = max(1, len(self.contexts))
        settings.prompts.pre = None
        settings.prompts.post = None
        if hasattr(settings.prompts, "answer_iteration_prompt"):
            settings.prompts.answer_iteration_prompt = None

        alias_to_evidence: dict[str, str] = {}
        paperqa_contexts: list[Any] = []
        for index, selected in enumerate(self.contexts, start=1):
            alias = f"b{index}"
            alias_to_evidence[alias] = selected.evidence_id
            document = paperqa_types.Doc(
                docname=alias,
                citation=f"Approved evidence {alias}",
                dockey=selected.evidence_id,
                content_hash=hashlib.sha256(selected.text.encode("utf-8")).hexdigest(),
            )
            text = paperqa_types.Text(
                text=selected.text,
                name=alias,
                doc=document,
            )
            paperqa_contexts.append(
                paperqa_types.Context(
                    id=alias,
                    context=selected.text,
                    question=question,
                    text=text,
                    score=10,
                )
            )

        session = paperqa_types.PQASession(
            question=question,
            contexts=paperqa_contexts,
        )
        serialized, serialized_aliases = await _serialize_final_contexts(
            settings=settings,
            contexts=paperqa_contexts,
            question=question,
        )
        valid_aliases = tuple(
            dict.fromkeys(
                alias for alias in serialized_aliases if alias in alias_to_evidence
            )
        )
        if not serialized.strip() or not valid_aliases:
            return _PaperQAGenerationOutput(
                raw_output="",
                citations=(),
                sent_evidence_ids=(),
                refusal_reason=REFUSAL_EMPTY_SENT,
            )

        valid_alias_set = set(valid_aliases)
        final_contexts = [
            context
            for context in paperqa_contexts
            if getattr(context, "id", None) in valid_alias_set
        ]
        session.contexts = final_contexts
        outbound_model = _copy_answer_model(
            self.bridge._answer_llm_model,
            max_output_tokens=self.policy.max_output_tokens,
            # Older PaperQA settings expose no serializer method and expect the
            # exact injected model object.  Modern settings are copied so the
            # bridge never mutates the caller's reusable model configuration.
            preserve_legacy_identity=not callable(
                getattr(settings, "context_serializer", None)
            ),
        )
        counter = getattr(outbound_model, "count_tokens", None)
        if not callable(counter):
            raise _GenerationRefusal(REFUSAL_INPUT_BUDGET_EXCEEDED)
        prompt_tokens = counter(
            _final_prompt_text(
                settings=settings,
                serialized=serialized,
                question=question,
            )
        )
        if (
            not isinstance(prompt_tokens, int)
            or isinstance(prompt_tokens, bool)
            or prompt_tokens < 0
            or prompt_tokens > self.policy.max_input_tokens
        ):
            return _PaperQAGenerationOutput(
                raw_output="",
                citations=(),
                sent_evidence_ids=(),
                refusal_reason=REFUSAL_INPUT_BUDGET_EXCEEDED,
            )

        answered = await docs.aquery(
            session,
            settings=settings,
            llm_model=outbound_model,
            summary_llm_model=self.bridge._summary_llm_model,
            embedding_model=self.bridge._embedding_model,
        )
        post_serialized_aliases = getattr(settings, "serialized_context_ids", None)
        if isinstance(post_serialized_aliases, (tuple, list)):
            actual_aliases = tuple(
                dict.fromkeys(
                    str(alias)
                    for alias in post_serialized_aliases
                    if str(alias) in valid_alias_set
                )
            )
        else:
            actual_aliases = valid_aliases
        if not actual_aliases:
            return _PaperQAGenerationOutput(
                raw_output="",
                citations=(),
                sent_evidence_ids=(),
                refusal_reason=REFUSAL_EMPTY_SENT,
            )
        raw = getattr(answered, "raw_answer", None)
        if not isinstance(raw, str):
            answer = getattr(answered, "answer", "")
            raw = answer if isinstance(answer, str) else str(answer)

        claims: list[_PaperQACitationClaim] = []
        seen: set[str] = set()
        for group in re.findall(r"\(([^()]*)\)", raw):
            for key in re.split(r"[\s,;]+", group.strip()):
                if not key or key in seen:
                    continue
                seen.add(key)
                evidence_id = alias_to_evidence.get(key)
                claims.append(
                    _PaperQACitationClaim(
                        key=key,
                        candidates=(evidence_id,) if evidence_id is not None else (),
                    )
                )
        return _PaperQAGenerationOutput(
            raw_output=raw,
            citations=tuple(claims),
            sent_evidence_ids=tuple(
                alias_to_evidence[alias] for alias in actual_aliases
            ),
        )


def _select_evidence(
    request: GenerationRequest,
) -> tuple[list[EvidenceRecord], str | None]:
    """Validate provenance/version and pick the deterministic send order."""
    snapshot = request.snapshot
    documents = {doc.document_id: doc for doc in snapshot.documents}
    approved = list(request.approved_evidence)
    by_id: dict[str, EvidenceRecord] = {}
    for record in approved:
        document = documents.get(record.document_id)
        if document is None or record.snapshot_id != snapshot.snapshot_id:
            return [], REFUSAL_EVIDENCE_OUTSIDE_SNAPSHOT
        if record.version_sha256 != document.version_sha256:
            return [], REFUSAL_EVIDENCE_VERSION_MISMATCH
        by_id[record.evidence_id] = record

    selected_ids: list[str] = []
    for evidence_id in request.selected_evidence_ids:
        if evidence_id not in by_id:
            return [], REFUSAL_SELECTED_OUTSIDE_APPROVED
        if evidence_id not in selected_ids:
            selected_ids.append(evidence_id)

    selected = [by_id[evidence_id] for evidence_id in selected_ids]
    max_sources = request.policy.max_sources
    if max_sources is not None:
        selected = selected[:max_sources]
    return selected, None


def _refusal(reason: str) -> GenerationResult:
    """A refusal that performed zero outbound calls."""
    return GenerationResult(status=GenerationStatus.REFUSED, refusal_reason=reason)


def _read_citation_fields(output: Any) -> tuple[str, tuple[Any, ...]]:
    """Extract raw text and citation claims from a scripted/real output object."""
    raw = getattr(output, "raw_output", "")
    claims = tuple(getattr(output, "citations", ()) or ())
    return raw if isinstance(raw, str) else str(raw), claims


def _resolve_citations(
    claims: Sequence[Any], sent_ids: set[str]
) -> tuple[
    tuple[tuple[str, str], ...],
    tuple[str, ...],
    tuple[str, ...],
]:
    """Map aliases only when unambiguous and inside the actual sent set."""
    aliases: list[tuple[str, str]] = []
    unknown: list[str] = []
    ambiguous: list[str] = []
    for claim in claims:
        key = getattr(claim, "key", None)
        candidates = tuple(getattr(claim, "candidates", ()) or ())
        if not isinstance(key, str) or not key.strip():
            continue
        usable = [cid for cid in candidates if cid in sent_ids]
        if not usable:
            unknown.append(key)
        elif len(set(usable)) > 1:
            ambiguous.append(key)
        else:
            aliases.append((key, usable[0]))
    return tuple(aliases), tuple(unknown), tuple(ambiguous)


def run_generation(
    *,
    request: GenerationRequest,
    factory: ModelFactory,
) -> GenerationResult:
    """Mechanically execute D's approved generation request (FR-D-03)."""
    policy = request.policy

    if not request.approved_evidence:
        return _refusal(REFUSAL_EMPTY_APPROVED)

    budget_reason = _validate_policy(policy)
    if budget_reason is not None:
        return _refusal(budget_reason)

    session_reason = _validate_session_policy(policy)
    if session_reason is not None:
        return _refusal(session_reason)

    selected, provenance_reason = _select_evidence(request)
    if provenance_reason is not None:
        return _refusal(provenance_reason)
    if not selected:
        return _refusal(REFUSAL_EMPTY_SENT)

    sanitized = _SessionPolicy(
        provider=policy.provider,
        model=policy.model,
        max_input_tokens=policy.max_input_tokens,
        compress_at_tokens=policy.compress_at_tokens,
        max_output_tokens=policy.max_output_tokens,
        max_sources=policy.max_sources,
        get_evidence_if_no_contexts=False,
        pre_prompt=None,
        post_prompt=None,
        autonomous_agent=False,
    )
    contexts = tuple(
        _SessionContext(evidence_id=record.evidence_id, text=record.excerpt)
        for record in selected
    )

    try:
        session = factory.create(policy=sanitized, contexts=contexts)
        output = session.ask(request.question)
    except _GenerationRefusal as refusal:
        return _refusal(refusal.reason)

    output_refusal = getattr(output, "refusal_reason", None)
    if isinstance(output_refusal, str):
        return _refusal(output_refusal)

    reported_sent = getattr(output, "sent_evidence_ids", None)
    selected_ids = tuple(record.evidence_id for record in selected)
    if reported_sent is None:
        final_sent = selected_ids
    else:
        selected_set = set(selected_ids)
        final_sent = tuple(reported_sent)
        invalid_ids = tuple(
            evidence_id for evidence_id in final_sent if evidence_id not in selected_set
        )
        if invalid_ids:
            return GenerationResult(
                status=GenerationStatus.INVALID_SENT_EVIDENCE,
                invalid_sent_evidence_ids=invalid_ids,
            )
    if not final_sent:
        return _refusal(REFUSAL_EMPTY_SENT)
    raw, claims = _read_citation_fields(output)
    sent_ids = set(final_sent)
    aliases, unknown, ambiguous = _resolve_citations(claims, sent_ids)

    return GenerationResult(
        status=(
            GenerationStatus.AMBIGUOUS_CITATIONS
            if ambiguous
            else GenerationStatus.SUCCESS
        ),
        raw_output=raw,
        sent_evidence_ids=final_sent,
        citation_aliases=aliases,
        unknown_citation_keys=unknown,
        ambiguous_citation_keys=ambiguous,
    )
