"""Module B public gateway: the single port A and D talk to.

This is the only approved public entry point for retrieval and neutral
generation.  It holds no review or release authority (INV-03/INV-04) and
rejects untrusted indexes before any loader runs (INV-08).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from papertrace.retrieval.service import (
    GenerationPolicy,
    GenerationRequest,
    GenerationResult,
    GenerationStatus,
    ModelFactory,
    PaperQA2Adapter,
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
    ) -> None:
        _reject_untrusted_index(index)
        self._adapter = adapter
        self._source_reader = source_reader
        self._model_factory = model_factory
        self._clock = clock

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
        return run_generation(request=request, factory=self._model_factory)

    @staticmethod
    def sanitized_contexts(
        contexts: Sequence[Any],
    ) -> tuple[Any, ...]:
        """Expose only the immutable selection for callers that inspect it."""
        return tuple(contexts)
