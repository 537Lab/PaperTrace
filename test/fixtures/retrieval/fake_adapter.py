"""Offline spies for Module B1 retrieval tests. Synthetic data only.

This module deliberately imports nothing from ``papertrace`` and nothing from
``paperqa``. It provides duck-typed inputs and recorders so the B1 tests can
assert on what the (still-unimplemented) ``papertrace.retrieval.gateway``
actually passes across each boundary:

* :class:`FakeRetrievalAdapter` -- a scripted ``Docs.aget_evidence`` stand-in.
  It records every request it receives (snapshot, question, config, verified
  source documents) and the call order, and either returns synthetic contexts
  or raises a *reported* failure. It never returns a bare ``"OK"``.
* :class:`FakeModelFactory` / :class:`FakeSession` -- a counted stand-in for the
  model/session creation boundary. The factory records ``create`` calls and a
  per-session SDK/HTTP counter so a pre-call rejection can be proven to keep
  every outbound count at zero.

Nothing here loads a real model, opens a socket, or reads credentials.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# --------------------------------------------------------------------------- #
# Retrieval adapter boundary
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class FakeContext:
    """A synthetic upstream evidence candidate (never a real paper chunk)."""

    document_id: str
    version_sha256: str
    excerpt: str
    line_start: int | None = None
    line_end: int | None = None
    page_start: int | None = None
    page_end: int | None = None
    chunk_id: str = "chunk-1"
    summary: str | None = None
    score: float | None = None
    upstream_context_id: str | None = None


@dataclass(frozen=True)
class FakeFailure:
    """A reported adapter failure; ``kind`` maps to a B-private failure status."""

    kind: str  # "timeout" | "parse_error" | "upstream_error"
    stage: str = "aget_evidence"
    retryable: bool = False


@dataclass(frozen=True)
class FakeOutcome:
    """Synthetic adapter result: contexts, a failure, or both (invalid)."""

    contexts: tuple[FakeContext, ...] = ()
    failure: FakeFailure | None = None


@dataclass
class FakeRetrievalAdapter:
    """Scripted, recording retrieval adapter.

    ``script`` is consumed one entry per call; the last entry repeats if the
    gateway calls more times than scripted (so an over-retry is observable).
    """

    script: list[FakeOutcome] = field(default_factory=lambda: [FakeOutcome()])
    search_calls: int = 0
    requests: list[object] = field(default_factory=list)
    call_order: list[str] = field(default_factory=list)

    def search(self, request: object) -> FakeOutcome:
        index = min(self.search_calls, len(self.script) - 1)
        self.search_calls += 1
        self.call_order.append("adapter.search")
        self.requests.append(request)
        return self.script[index]


# --------------------------------------------------------------------------- #
# Controlled source-text port (A's ``read_source`` shape)
# --------------------------------------------------------------------------- #
@dataclass
class FakeSourceReader:
    """Records the exact ``(snapshot_id, document_id, version_sha256)`` asked."""

    sources: dict[tuple[str, str, str], bytes]
    calls: list[dict[str, str]] = field(default_factory=list)
    fail_with: Exception | None = None

    def __call__(
        self, *, snapshot_id: str, document_id: str, version_sha256: str
    ) -> bytes:
        self.calls.append(
            {
                "snapshot_id": snapshot_id,
                "document_id": document_id,
                "version_sha256": version_sha256,
            }
        )
        if self.fail_with is not None:
            raise self.fail_with
        return self.sources[(snapshot_id, document_id, version_sha256)]


@dataclass
class CountingUntrustedSource:
    """A non-bytes "source" that must be rejected before any deserialization."""

    load_calls: int = 0

    def load(self) -> object:
        self.load_calls += 1
        raise AssertionError("untrusted index must never be deserialized")


# --------------------------------------------------------------------------- #
# Generation port boundary (model factory / session)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class FakeCitationClaim:
    """One raw citation key with the evidence IDs it could resolve to.

    A real adapter resolves a key through its own alias table; ``candidates``
    with more than one entry models an upstream alias collision that B must
    refuse to map arbitrarily.
    """

    key: str
    candidates: tuple[str, ...]


@dataclass(frozen=True)
class FakeGenerationOutput:
    """Raw, pre-cleanup generation result echoed back by a fake session."""

    raw_output: str
    citations: tuple[FakeCitationClaim, ...] = ()
    usage_tokens: int = 0
    sent_evidence_ids: tuple[str, ...] | None = None


@dataclass
class FakeSession:
    """Records what was actually serialized into it, then returns a scripted reply."""

    factory: "FakeModelFactory"
    contexts: tuple[object, ...]
    scripted: list[FakeGenerationOutput]
    ask_calls: int = 0
    sdk_calls: int = 0
    http_calls: int = 0
    reused: bool = False

    def ask(self, question: str) -> FakeGenerationOutput:
        self.ask_calls += 1
        self.factory.ask_order.append("session.ask")
        self.factory.questions.append(question)
        index = min(self.ask_calls - 1, len(self.scripted) - 1)
        return self.scripted[index]


@dataclass
class FakeModelFactory:
    """Counts every factory/session/SDK/HTTP touch; proves zero on rejection."""

    create_calls: int = 0
    sdk_calls: int = 0
    http_calls: int = 0
    sessions: list[FakeSession] = field(default_factory=list)
    create_payloads: list[object] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    ask_order: list[str] = field(default_factory=list)
    failure: Exception | None = None
    scripted: list[FakeGenerationOutput] = field(
        default_factory=lambda: [FakeGenerationOutput(raw_output="synthetic draft [1]")]
    )

    def create(self, *, policy: object = None, contexts: object = ()) -> FakeSession:
        self.create_calls += 1
        self.create_payloads.append({"policy": policy, "contexts": contexts})
        if self.failure is not None:
            raise self.failure
        session = FakeSession(
            factory=self, contexts=tuple(contexts), scripted=list(self.scripted)
        )
        self.sessions.append(session)
        return session
