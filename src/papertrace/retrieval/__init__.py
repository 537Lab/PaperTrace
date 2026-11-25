"""Module B: PaperQA2 retrieval adapter and neutral generation port.

Only this package may import ``paperqa`` in new team source (FR-B-01/QA-01).
The public surface is :mod:`papertrace.retrieval.gateway`; the view projection
is :mod:`papertrace.retrieval.view`.  Nothing here grants review or release
authority (INV-03/INV-04).
"""

from papertrace.retrieval.gateway import (
    Gateway,
    GenerationPolicy,
    GenerationRequest,
    GenerationResult,
    GenerationStatus,
    PaperQA2Adapter,
    RetrievalAttempt,
    RetrievalConfig,
    RetrievalRequest,
    RetrievalResult,
    RetrievalStatus,
    UnsafeIndexError,
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
