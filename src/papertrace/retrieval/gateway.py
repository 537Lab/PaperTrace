"""Module B public gateway: the single port A and D talk to.

This is the only approved public entry point for retrieval and neutral
generation.  It holds no review or release authority (INV-03/INV-04) and
rejects untrusted indexes before any loader runs (INV-08).
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from typing import Any

from papertrace.retrieval.service import (
    EvaluationCaseBinding,
    GenerationPolicy,
    GenerationRequest,
    GenerationResult,
    GenerationStatus,
    ModelFactory,
    PaperQA2Adapter,
    RequestObserver,
    RetrievalAdapter,
    RetrievalAttempt,
    RetrievalConfig,
    RetrievalRequest,
    RetrievalResult,
    RetrievalStatus,
    SourceReader,
    UnsafeIndexError,
    run_generation,
    run_retrieval,
)

__all__ = [
    "EvaluationCaseBinding",
    "Gateway",
    "GenerationPolicy",
    "GenerationRequest",
    "GenerationResult",
    "GenerationStatus",
    "PaperQA2Adapter",
    "RetrievalAttempt",
    "RetrievalConfig",
    "RetrievalRequest",
    "RetrievalResult",
    "RetrievalStatus",
    "UnsafeIndexError",
]


def _reject_untrusted_index(index: object | None) -> None:
    """INV-08 / SEC-01: refuse pickle-like artifacts without touching a loader."""
    if index is None:
        return
    if isinstance(index, (bytes, bytearray, memoryview)):
        raise UnsafeIndexError("raw bytes cannot be loaded as a trusted index")
    if isinstance(index, str):
        raise UnsafeIndexError("path strings cannot be loaded as a trusted index")
    if hasattr(index, "load") or hasattr(index, "read_pickle"):
        raise UnsafeIndexError("index loader is not an approved trusted source")
    raise UnsafeIndexError("index object is not an approved trusted source")


class Gateway:
    """Single B port: bounded retrieval plus mechanical neutral generation."""

    def __init__(
        self,
        *,
        adapter: RetrievalAdapter,
        source_reader: SourceReader,
        model_factory: ModelFactory,
        index: object | None = None,
        clock: Any,
        evaluation_binding: EvaluationCaseBinding | None = None,
        request_observer: RequestObserver | None = None,
    ) -> None:
        _reject_untrusted_index(index)
        self._adapter = adapter
        self._source_reader = source_reader
        self._model_factory = model_factory
        self._clock = clock
        self._evaluation_binding = evaluation_binding
        self._request_observer = request_observer

    @staticmethod
    def ingest(request: dict[str, Any]) -> dict[str, Any]:
        """Validate controlled UTF-8 TXT bytes into a bounded parse receipt.

        The check is local and synchronous: it performs no I/O, touches no
        loader, and never returns source text, paths, or exception details.
        """
        document_id = request["document_id"]
        version_sha256 = request["version_sha256"]
        source_name = request["source_name"]
        source_bytes = request["source_bytes"]

        def receipt(status: str, reason_code: str | None) -> dict[str, Any]:
            reference = None
            if status == "ready":
                reference = f"txt-validated:{document_id}:{version_sha256}"
            return {
                "document_id": document_id,
                "version_sha256": version_sha256,
                "status": status,
                "stage": "parse",
                "reason_code": reason_code,
                "representation_ref": reference,
            }

        if (
            not source_name.lower().endswith(".txt")
            or any(character in source_name for character in "/\\:")
            or any(ord(character) < 32 or ord(character) == 127 for character in source_name)
        ):
            return receipt("failed", "UNSUPPORTED_FORMAT")

        if hashlib.sha256(source_bytes).hexdigest() != version_sha256:
            return receipt("failed", "HASH_MISMATCH")

        try:
            text = source_bytes.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            return receipt("failed", "INVALID_UTF8")

        if not text.strip():
            return receipt("failed", "EMPTY_TEXT")

        return receipt("ready", None)

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        """Run bounded, verified retrieval against the fixed snapshot."""
        return run_retrieval(
            request=request,
            adapter=self._adapter,
            reader=self._source_reader,
            clock=self._clock,
        )

    def generate(self, request: GenerationRequest) -> GenerationResult:
        """Execute D's approved generation request with zero pre-call outbound."""
        return run_generation(
            request=request,
            factory=self._model_factory,
            evaluation_binding=self._evaluation_binding,
            request_observer=self._request_observer,
        )

    @staticmethod
    def sanitized_contexts(
        contexts: Sequence[Any],
    ) -> tuple[Any, ...]:
        """Expose only the immutable selection for callers that inspect it."""
        return tuple(contexts)
