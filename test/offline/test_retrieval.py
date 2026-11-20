"""B1 RED proposal suite for Module B retrieval and neutral generation ports.

Synthetic, offline, deterministic. No real paper, model, provider, credential,
network socket or personal path is used. The planned business module
``papertrace.retrieval`` is imported lazily inside helpers so collection stays
healthy while B2 is still unimplemented; each behavioural test then fails with a
clear assertion rather than an import crash.

Traceability: FR-B-01/02, FR-D-03, INV-01/02/03/04/07/08, COST-01, SEC-01,
QA-01, GOV-01..04. Plan v2.1 is the authority for the expected public surface
encoded below; this file does not modify shared contracts and does not create a
production gateway.
"""

from __future__ import annotations

import ast
import hashlib
import importlib
import importlib.util
import re
import sys
import types
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "retrieval"
ROOT = Path(__file__).resolve().parents[2]

SANDBOX_CLOCK = datetime(2026, 1, 1, tzinfo=timezone.utc)
ALTERNATE_CLOCK = datetime(2026, 2, 2, tzinfo=timezone.utc)
PROVIDER = "synthetic-provider"
MODEL = "synthetic-model"
PARSER_NAME = "synthetic-parser"
PARSER_VERSION = "1.0"
REVIEW_DIGEST = "d" * 64
SNAPSHOT_TIME = "2026-01-01T00:00:00Z"


# --------------------------------------------------------------------------- #
# Lazy, collection-safe imports
# --------------------------------------------------------------------------- #
def _planned_module(name: str, feature: str):
    """Import a planned module without turning absence into a collection error."""
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as exc:
        raise AssertionError(
            f"B1 RED: approved Module B {feature} is not implemented yet ({name}); "
            "this suite refuses to pass by skip or xfail."
        ) from exc


def gateway_module():
    """The single planned B public gateway."""
    return _planned_module("papertrace.retrieval.gateway", "gateway")


def view_module():
    """The planned B-only status projection; it must not carry review authority."""
    return _planned_module("papertrace.retrieval.view", "view projection")


@lru_cache(maxsize=1)
def contracts_module():
    """The real shared contract module; never re-implemented in this suite."""
    return _planned_module("papertrace.contracts", "shared contracts")


@lru_cache(maxsize=1)
def fake_module():
    """Load the approved synthetic spies by path without touching sys.path."""
    path = FIXTURES / "fake_adapter.py"
    assert path.is_file(), f"B1 fixture missing: {path}"
    spec = importlib.util.spec_from_file_location("papertrace_b1_fake_adapter", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------- #
# Synthetic corpus and helpers
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=1)
def fixture_bundle():
    """Real hashes of the synthetic bytes, then real shared-contract records."""
    contracts = contracts_module()
    source_a = (FIXTURES / "source-a.txt").read_bytes()
    source_b = (FIXTURES / "source-b.txt").read_bytes()

    document_model = contracts.DocumentVersion
    doc_a = document_model(
        schema_version=1,
        document_id="doc-synthetic-a",
        version_sha256=hashlib.sha256(source_a).hexdigest(),
        title="Synthetic source A (not a real paper)",
        source_name="source-a.txt",
        status="ready",
    )
    doc_b = document_model(
        schema_version=1,
        document_id="doc-synthetic-b",
        version_sha256=hashlib.sha256(source_b).hexdigest(),
        title="Synthetic source B (not a real paper)",
        source_name="source-b.txt",
        status="ready",
    )
    snapshot = contracts.CorpusSnapshot(
        schema_version=1,
        documents=(doc_a, doc_b),
        created_at=SNAPSHOT_TIME,
    )
    return types.SimpleNamespace(
        source_a=source_a,
        source_b=source_b,
        doc_a=doc_a,
        doc_b=doc_b,
        snapshot=snapshot,
        documents={doc_a.document_id: doc_a, doc_b.document_id: doc_b},
        sources={doc_a.document_id: source_a, doc_b.document_id: source_b},
    )


def line_text(document_id: str, start: int, end: int) -> str:
    """Exact 1-based inclusive synthetic source slice."""
    source = fixture_bundle().sources[document_id].decode("utf-8")
    lines = source.splitlines()
    assert 1 <= start <= end <= len(lines), "test fixture range must be real"
    return "\n".join(lines[start - 1 : end])


def make_locator(
    *,
    line_start: int | None = None,
    line_end: int | None = None,
    page_start: int | None = None,
    page_end: int | None = None,
    chunk_id: str = "chunk-synthetic-a",
):
    """Build a real shared SourceLocator with parser provenance."""
    return contracts_module().SourceLocator(
        schema_version=1,
        page_start=page_start,
        page_end=page_end,
        line_start=line_start,
        line_end=line_end,
        chunk_id=chunk_id,
        parser_name=PARSER_NAME,
        parser_version=PARSER_VERSION,
    )


def make_context(
    document_id: str,
    *,
    line_start: int | None = None,
    line_end: int | None = None,
    page_start: int | None = None,
    page_end: int | None = None,
    excerpt: str | None = None,
    chunk_id: str = "chunk-synthetic-a",
    summary: str | None = "Synthetic advisory summary.",
    score: float | None = 0.5,
    upstream_context_id: str | None = "synthetic-upstream-context",
    version_sha256: str | None = None,
    **overrides: object,
):
    """A synthetic upstream context shape accepted by the approved fake."""
    bundle = fixture_bundle()
    doc = bundle.documents[document_id]
    if excerpt is None:
        assert line_start is not None and line_end is not None
        excerpt = line_text(document_id, line_start, line_end)
    values: dict[str, object] = {
        "document_id": doc.document_id,
        "version_sha256": version_sha256 or doc.version_sha256,
        "excerpt": excerpt,
        "line_start": line_start,
        "line_end": line_end,
        "page_start": page_start,
        "page_end": page_end,
        "chunk_id": chunk_id,
        "summary": summary,
        "score": score,
        "upstream_context_id": upstream_context_id,
    }
    values.update(overrides)
    return fake_module().FakeContext(**values)


def make_evidence(
    document_id: str,
    *,
    line_start: int | None = None,
    line_end: int | None = None,
    page_start: int | None = None,
    page_end: int | None = None,
    excerpt: str | None = None,
    snapshot_id: str | None = None,
    version_sha256: str | None = None,
    chunk_id: str = "chunk-synthetic-a",
    advisory_summary: str | None = "Synthetic advisory summary; not authority.",
    upstream_context_id: str | None = "synthetic-upstream-context",
):
    """Build a real shared EvidenceRecord from synthetic source provenance."""
    bundle = fixture_bundle()
    doc = bundle.documents[document_id]
    if excerpt is None:
        assert line_start is not None and line_end is not None
        excerpt = line_text(document_id, line_start, line_end)
    locator = make_locator(
        line_start=line_start,
        line_end=line_end,
        page_start=page_start,
        page_end=page_end,
        chunk_id=chunk_id,
    )
    return contracts_module().EvidenceRecord(
        schema_version=1,
        snapshot_id=snapshot_id or bundle.snapshot.snapshot_id,
        document_id=doc.document_id,
        version_sha256=version_sha256 or doc.version_sha256,
        locator=locator,
        excerpt=excerpt,
        retrieved_at=SNAPSHOT_TIME,
        advisory_summary=advisory_summary,
        upstream_context_id=upstream_context_id,
    )


def make_source_reader(*, fail_with: Exception | None = None, override: dict | None = None):
    """The A-shaped controlled source reader, wired to this synthetic snapshot."""
    bundle = fixture_bundle()
    sources: dict[tuple[str, str, str], bytes] = {}
    for document_id, source in bundle.sources.items():
        doc = bundle.documents[document_id]
        key = (bundle.snapshot.snapshot_id, doc.document_id, doc.version_sha256)
        sources[key] = source
    if override:
        sources.update(override)
    return fake_module().FakeSourceReader(sources=sources, fail_with=fail_with)


def make_gateway(
    *,
    adapter=None,
    reader=None,
    factory=None,
    index=None,
    clock=None,
):
    """Build the approved single B port with counted fakes."""
    gateway = gateway_module()
    fake = fake_module()
    return gateway.Gateway(
        adapter=adapter if adapter is not None else fake.FakeRetrievalAdapter(),
        source_reader=reader if reader is not None else make_source_reader(),
        model_factory=factory if factory is not None else fake.FakeModelFactory(),
        index=index,
        clock=clock if clock is not None else (lambda: SANDBOX_CLOCK),
    )


def retrieval_request(gateway, **config_changes):
    """A retrieval request with the approved provider/model/retry defaults."""
    values: dict[str, object] = {
        "provider": PROVIDER,
        "model": MODEL,
        "max_retries": 0,
        "parser_name": PARSER_NAME,
        "parser_version": PARSER_VERSION,
    }
    values.update(config_changes)
    return gateway.RetrievalRequest(
        snapshot=fixture_bundle().snapshot,
        question="Synthetic retrieval question; not a real research question.",
        config=gateway.RetrievalConfig(**values),
    )


def retrieve_with(adapter, *, reader=None, clock=None, **config_changes):
    """Run one synthetic retrieval and return both gateway module and result."""
    gateway = gateway_module()
    port = make_gateway(adapter=adapter, reader=reader, clock=clock)
    return gateway, port.retrieve(retrieval_request(gateway, **config_changes))


def generation_policy(gateway, **changes):
    """The approved D-supplied policy with every dangerous upstream feature off."""
    values: dict[str, object] = {
        "provider": PROVIDER,
        "model": MODEL,
        "max_input_tokens": 12000,
        "compress_at_tokens": 9000,
        "max_output_tokens": 2000,
        "max_sources": None,
        "get_evidence_if_no_contexts": False,
        "pre_prompt": None,
        "post_prompt": None,
        "autonomous_agent": False,
    }
    values.update(changes)
    return gateway.GenerationPolicy(**values)


def generation_request(
    gateway,
    *,
    approved,
    selected,
    policy=None,
    question="Synthetic generation question; no real research question.",
    review_revision=1,
    review_digest=REVIEW_DIGEST,
):
    """A D→B neutral generation request carrying no review authority itself."""
    return gateway.GenerationRequest(
        snapshot=fixture_bundle().snapshot,
        question=question,
        approved_evidence=tuple(approved),
        selected_evidence_ids=tuple(selected),
        policy=policy if policy is not None else generation_policy(gateway),
        review_revision=review_revision,
        review_digest=review_digest,
    )


@lru_cache(maxsize=1)
def generation_records():
    """Stable synthetic evidence for generation-boundary tests only."""
    bundle = fixture_bundle()
    ev_a = make_evidence(
        "doc-synthetic-a",
        line_start=3,
        line_end=4,
        chunk_id="chunk-synthetic-a",
        advisory_summary="Synthetic summary A; advisory only.",
        upstream_context_id="ctx-evidence-a",
    )
    ev_b = make_evidence(
        "doc-synthetic-b",
        line_start=9,
        line_end=10,
        chunk_id="chunk-synthetic-b",
        advisory_summary="Synthetic summary B; advisory only.",
        upstream_context_id="ctx-evidence-b",
    )
    pending = make_evidence(
        "doc-synthetic-b",
        line_start=6,
        line_end=7,
        chunk_id="chunk-synthetic-b",
        advisory_summary="Pending synthetic marker text; never reviewed.",
        upstream_context_id="ctx-pending-b",
    )
    return types.SimpleNamespace(bundle=bundle, ev_a=ev_a, ev_b=ev_b, pending=pending)


def assert_no_generation_outbound(factory, adapter) -> None:
    """FR-D-03 / COST-01: a pre-call refusal touches nothing outbound."""
    assert factory.create_calls == 0
    assert factory.sdk_calls == 0
    assert factory.http_calls == 0
    assert factory.sessions == []
    assert factory.create_payloads == []
    assert factory.questions == []
    assert factory.ask_order == []
    assert adapter.search_calls == 0
    assert adapter.requests == []


def imported_roots(path: Path) -> set[str]:
    """Root module names imported by a Python file, without executing it."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    return roots


# --------------------------------------------------------------------------- #
# Fixture and architecture safety
# --------------------------------------------------------------------------- #
def test_retrieval_fixtures_are_synthetic_secret_free_and_path_free():
    """SEC-01 / COST-01: approved synthetic fixtures carry no real data."""
    names = ("source-a.txt", "source-b.txt", "README.md", "fake_adapter.py")
    for name in names:
        path = FIXTURES / name
        assert path.is_file(), f"B1 fixture missing: {path}"
        text = path.read_text(encoding="utf-8")
        assert "SYNTHETIC" in text.upper()
        for pattern in (
            r"(?i)api[_-]?key\s*[:=]\s*\S+",
            r"(?i)secret\s*[:=]\s*\S+",
            r"(?i)password\s*[:=]\s*\S+",
            r"sk-[A-Za-z0-9]{8,}",
        ):
            assert re.search(pattern, text) is None, f"credential-like fixture value in {name}"
        assert "/Users/" not in text
        assert "/home/" not in text
        assert re.search(r"[A-Za-z]:\\\\", text) is None
        assert re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text) is None


def test_fake_adapter_imports_neither_papertrace_nor_paperqa():
    """B1 fake must not accidentally become production or upstream code."""
    fake_roots = imported_roots(FIXTURES / "fake_adapter.py")
    assert "papertrace" not in fake_roots
    assert "paperqa" not in fake_roots


def test_only_retrieval_module_may_import_paperqa_in_team_source():
    """FR-B-01 / QA-01: B-only dependency boundary for new team source."""
    team_source = ROOT / "src" / "papertrace"
    assert team_source.is_dir(), "shared papertrace source package is missing"
    violations: list[str] = []
    for path in sorted(team_source.rglob("*.py")):
        relative = path.relative_to(team_source)
        if relative.parts and relative.parts[0] == "retrieval":
            continue
        if "paperqa" in imported_roots(path):
            violations.append(str(relative))
    assert violations == [], f"paperqa imported outside B retrieval: {violations}"


# --------------------------------------------------------------------------- #
# Retrieval provenance, identity and locator handling
# --------------------------------------------------------------------------- #
def test_retrieval_maps_verified_contexts_to_real_evidence_records():
    """FR-B-01 / INV-02: real snapshot/document/version/excerpt/locator survive."""
    fake = fake_module()
    bundle = fixture_bundle()
    reader = make_source_reader()
    ctx_a = make_context(
        "doc-synthetic-a",
        line_start=3,
        line_end=4,
        chunk_id="chunk-a-3-4",
        summary="Synthetic advisory A.",
        score=0.9,
        upstream_context_id="upstream-context-a",
    )
    ctx_b = make_context(
        "doc-synthetic-b",
        line_start=9,
        line_end=10,
        chunk_id="chunk-b-9-10",
        summary="Synthetic advisory B.",
        score=0.2,
        upstream_context_id="upstream-context-b",
    )
    adapter = fake.FakeRetrievalAdapter(
        script=[fake.FakeOutcome(contexts=(ctx_a, ctx_b))]
    )
    gateway, result = retrieve_with(adapter, reader=reader)

    assert result.status is gateway.RetrievalStatus.SUCCESS
    assert len(result.evidence) == 2
    assert all(isinstance(item, contracts_module().EvidenceRecord) for item in result.evidence)

    by_document = {item.document_id: item for item in result.evidence}
    evidence_a = by_document["doc-synthetic-a"]
    evidence_b = by_document["doc-synthetic-b"]

    assert evidence_a.snapshot_id == bundle.snapshot.snapshot_id
    assert evidence_a.version_sha256 == bundle.doc_a.version_sha256
    assert evidence_a.excerpt == ctx_a.excerpt
    assert evidence_a.advisory_summary == ctx_a.summary
    assert evidence_a.upstream_context_id == ctx_a.upstream_context_id
    assert evidence_a.evidence_id != ctx_a.upstream_context_id
    assert evidence_a.locator.line_start == 3
    assert evidence_a.locator.line_end == 4
    assert evidence_a.locator.page_start is None
    assert evidence_a.locator.chunk_id == ctx_a.chunk_id
    assert evidence_a.locator.parser_name == PARSER_NAME
    assert evidence_a.locator.parser_version == PARSER_VERSION

    assert evidence_b.version_sha256 == bundle.doc_b.version_sha256
    assert evidence_b.excerpt == ctx_b.excerpt
    assert evidence_b.locator.line_start == 9
    assert evidence_b.locator.line_end == 10

    for item in (evidence_a, evidence_b):
        assert item.evidence_id.startswith("ev-")
        assert item.__class__.model_validate_json(item.model_dump_json()) == item

    expected_reads = {
        (
            bundle.snapshot.snapshot_id,
            bundle.doc_a.document_id,
            bundle.doc_a.version_sha256,
        ),
        (
            bundle.snapshot.snapshot_id,
            bundle.doc_b.document_id,
            bundle.doc_b.version_sha256,
        ),
    }
    actual_reads = {
        (call["snapshot_id"], call["document_id"], call["version_sha256"])
        for call in reader.calls
    }
    assert actual_reads == expected_reads
    assert adapter.search_calls == 1


def test_retrieval_preserves_page_range_locator_with_parser_metadata():
    """FR-B-01 / INV-02: a complete 1-based page range is also valid."""
    fake = fake_module()
    excerpt = line_text("doc-synthetic-a", 1, 1)
    context = make_context(
        "doc-synthetic-a",
        line_start=None,
        line_end=None,
        page_start=1,
        page_end=1,
        excerpt=excerpt,
        chunk_id="chunk-page-a",
    )
    adapter = fake.FakeRetrievalAdapter(
        script=[fake.FakeOutcome(contexts=(context,))]
    )
    _, result = retrieve_with(adapter)

    assert result.status is gateway_module().RetrievalStatus.SUCCESS
    evidence = result.evidence[0]
    assert evidence.locator.page_start == 1
    assert evidence.locator.page_end == 1
    assert evidence.locator.line_start is None
    assert evidence.locator.chunk_id == "chunk-page-a"
    assert evidence.locator.parser_name == PARSER_NAME
    assert evidence.locator.parser_version == PARSER_VERSION


def test_retrieval_deduplicates_identical_provenance_but_keeps_advisory_separate():
    """FR-B-01 / INV-02: same provenance yields one stable evidence identity."""
    fake = fake_module()
    context_one = make_context(
        "doc-synthetic-a",
        line_start=3,
        line_end=4,
        chunk_id="chunk-dedup-a",
        summary="First advisory wording.",
        score=0.1,
        upstream_context_id="ctx-one",
    )
    context_two = make_context(
        "doc-synthetic-a",
        line_start=3,
        line_end=4,
        chunk_id="chunk-dedup-a",
        summary="Second advisory wording.",
        score=0.9,
        upstream_context_id="ctx-two",
    )
    adapter = fake.FakeRetrievalAdapter(
        script=[fake.FakeOutcome(contexts=(context_one, context_two))]
    )
    _, result = retrieve_with(adapter)

    assert result.status is gateway_module().RetrievalStatus.SUCCESS
    assert len(result.evidence) == 1
    expected = make_evidence(
        "doc-synthetic-a",
        line_start=3,
        line_end=4,
        chunk_id="chunk-dedup-a",
        advisory_summary="ignored advisory; identity excludes it",
    )
    assert result.evidence[0].evidence_id == expected.evidence_id


def test_retrieval_identity_ignores_advisory_summary_score_upstream_id_and_time():
    """FR-B-01 / INV-02: advisory and retrieval time are not evidence identity."""
    fake = fake_module()
    gateway = gateway_module()
    first_context = make_context(
        "doc-synthetic-a",
        line_start=3,
        line_end=4,
        chunk_id="chunk-identity-a",
        summary="Advisory one.",
        score=0.1,
        upstream_context_id="upstream-one",
    )
    second_context = make_context(
        "doc-synthetic-a",
        line_start=3,
        line_end=4,
        chunk_id="chunk-identity-a",
        summary="Advisory two.",
        score=0.99,
        upstream_context_id="upstream-two",
    )

    first_port = make_gateway(
        adapter=fake.FakeRetrievalAdapter(
            script=[fake.FakeOutcome(contexts=(first_context,))]
        ),
        clock=lambda: SANDBOX_CLOCK,
    )
    first_result = first_port.retrieve(retrieval_request(gateway))
    second_port = make_gateway(
        adapter=fake.FakeRetrievalAdapter(
            script=[fake.FakeOutcome(contexts=(second_context,))]
        ),
        clock=lambda: ALTERNATE_CLOCK,
    )
    second_result = second_port.retrieve(retrieval_request(gateway))

    assert first_result.status is gateway.RetrievalStatus.SUCCESS
    assert second_result.status is gateway.RetrievalStatus.SUCCESS
    first_evidence = first_result.evidence[0]
    second_evidence = second_result.evidence[0]
    assert first_evidence.evidence_id == second_evidence.evidence_id
    assert first_evidence.advisory_summary != second_evidence.advisory_summary
    assert first_evidence.retrieved_at != second_evidence.retrieved_at


def test_retrieval_identity_changes_with_excerpt_or_locator_change():
    """FR-B-01 / INV-02, INV-04: provenance changes must create a new identity."""
    fake = fake_module()
    gateway = gateway_module()
    first_context = make_context(
        "doc-synthetic-a",
        line_start=3,
        line_end=4,
        chunk_id="chunk-identity-a",
    )
    changed_excerpt_context = make_context(
        "doc-synthetic-a",
        line_start=8,
        line_end=9,
        chunk_id="chunk-identity-a",
    )
    line_locator_context = make_context(
        "doc-synthetic-a",
        line_start=1,
        line_end=1,
        chunk_id="chunk-identity-a",
    )
    page_locator_context = make_context(
        "doc-synthetic-a",
        line_start=None,
        line_end=None,
        page_start=1,
        page_end=1,
        excerpt=line_text("doc-synthetic-a", 1, 1),
        chunk_id="chunk-identity-a",
    )

    first_port = make_gateway(
        adapter=fake.FakeRetrievalAdapter(
            script=[fake.FakeOutcome(contexts=(first_context,))]
        )
    )
    first_result = first_port.retrieve(retrieval_request(gateway))
    excerpt_port = make_gateway(
        adapter=fake.FakeRetrievalAdapter(
            script=[fake.FakeOutcome(contexts=(changed_excerpt_context,))]
        )
    )
    excerpt_result = excerpt_port.retrieve(retrieval_request(gateway))
    line_port = make_gateway(
        adapter=fake.FakeRetrievalAdapter(
            script=[fake.FakeOutcome(contexts=(line_locator_context,))]
        )
    )
    line_result = line_port.retrieve(retrieval_request(gateway))
    page_port = make_gateway(
        adapter=fake.FakeRetrievalAdapter(
            script=[fake.FakeOutcome(contexts=(page_locator_context,))]
        )
    )
    page_result = page_port.retrieve(retrieval_request(gateway))

    assert (
        first_result.evidence[0].evidence_id
        != excerpt_result.evidence[0].evidence_id
    )
    assert (
        line_result.evidence[0].evidence_id
        != page_result.evidence[0].evidence_id
    )
    assert line_result.evidence[0].excerpt == page_result.evidence[0].excerpt


@pytest.mark.parametrize(
    "case",
    [
        "unknown_document",
        "unknown_version",
        "missing_line_endpoint",
        "reversed_line_range",
        "out_of_bounds_line_range",
        "missing_page_endpoint",
        "reversed_page_range",
        "no_range_at_all",
    ],
)
def test_retrieval_rejects_invalid_provenance_and_locator(case):
    """FR-B-01 / INV-02, INV-04: fail closed instead of guessing provenance."""
    fake = fake_module()
    excerpt = line_text("doc-synthetic-a", 3, 4)
    if case == "unknown_document":
        context = fake.FakeContext(
            document_id="doc-synthetic-unknown",
            version_sha256="a" * 64,
            excerpt=excerpt,
            line_start=3,
            line_end=4,
            chunk_id="chunk-unknown",
            summary="Synthetic unknown document.",
            score=0.4,
            upstream_context_id="ctx-unknown",
        )
    elif case == "unknown_version":
        context = make_context(
            "doc-synthetic-a",
            line_start=3,
            line_end=4,
            version_sha256="b" * 64,
        )
    elif case == "missing_line_endpoint":
        context = make_context(
            "doc-synthetic-a",
            line_start=3,
            line_end=None,
            excerpt=excerpt,
        )
    elif case == "reversed_line_range":
        context = make_context(
            "doc-synthetic-a",
            line_start=5,
            line_end=4,
            excerpt=excerpt,
        )
    elif case == "out_of_bounds_line_range":
        context = make_context(
            "doc-synthetic-a",
            line_start=50,
            line_end=51,
            excerpt=excerpt,
        )
    elif case == "missing_page_endpoint":
        context = make_context(
            "doc-synthetic-a",
            page_start=1,
            page_end=None,
            excerpt=line_text("doc-synthetic-a", 1, 1),
        )
    elif case == "reversed_page_range":
        context = make_context(
            "doc-synthetic-a",
            page_start=2,
            page_end=1,
            excerpt=line_text("doc-synthetic-a", 1, 1),
        )
    else:
        context = make_context(
            "doc-synthetic-a",
            excerpt=line_text("doc-synthetic-a", 1, 1),
        )

    adapter = fake.FakeRetrievalAdapter(
        script=[fake.FakeOutcome(contexts=(context,))]
    )
    _, result = retrieve_with(adapter)

    assert result.status is gateway_module().RetrievalStatus.PARSE_ERROR
    assert result.evidence == ()
    assert adapter.search_calls == 1


def test_retrieval_rejects_excerpt_that_cannot_be_verified_in_source():
    """FR-B-01 / INV-02: an unverifiable excerpt is not a candidate."""
    fake = fake_module()
    context = make_context(
        "doc-synthetic-a",
        line_start=3,
        line_end=4,
        excerpt="This synthetic excerpt is absent from every controlled source.",
    )
    reader = make_source_reader()
    adapter = fake.FakeRetrievalAdapter(
        script=[fake.FakeOutcome(contexts=(context,))]
    )
    _, result = retrieve_with(adapter, reader=reader)

    assert result.status is gateway_module().RetrievalStatus.PARSE_ERROR
    assert result.evidence == ()
    assert reader.calls, "verification must consult the controlled source, not the context alone"


def test_retrieval_rejects_source_bytes_that_do_not_match_the_snapshot_version():
    """FR-B-01 / INV-02: the snapshot version is verified, not just trusted."""
    fake = fake_module()
    bundle = fixture_bundle()
    context = make_context("doc-synthetic-a", line_start=3, line_end=4)
    override = {
        (
            bundle.snapshot.snapshot_id,
            bundle.doc_a.document_id,
            bundle.doc_a.version_sha256,
        ): b"mutated synthetic bytes",
    }
    reader = make_source_reader(override=override)
    adapter = fake.FakeRetrievalAdapter(
        script=[fake.FakeOutcome(contexts=(context,))]
    )
    _, result = retrieve_with(adapter, reader=reader)

    assert result.status is gateway_module().RetrievalStatus.PARSE_ERROR
    assert result.evidence == ()


def test_retrieval_fails_closed_without_partial_evidence():
    """FR-B-01 / FR-B-02: one bad candidate cannot leak a partial candidate set."""
    fake = fake_module()
    valid = make_context("doc-synthetic-a", line_start=3, line_end=4)
    invalid = make_context(
        "doc-synthetic-b",
        line_start=9,
        line_end=10,
        version_sha256="b" * 64,
    )
    adapter = fake.FakeRetrievalAdapter(
        script=[fake.FakeOutcome(contexts=(valid, invalid))]
    )
    _, result = retrieve_with(adapter)

    assert result.status is gateway_module().RetrievalStatus.PARSE_ERROR
    assert result.evidence == ()


# --------------------------------------------------------------------------- #
# Empty result, failure classes and bounded retry
# --------------------------------------------------------------------------- #
def test_retrieval_empty_result_is_not_a_failure():
    """FR-B-02: an honest empty result is distinct from a broken execution."""
    fake = fake_module()
    adapter = fake.FakeRetrievalAdapter(script=[fake.FakeOutcome()])
    _, result = retrieve_with(adapter)

    assert result.status is gateway_module().RetrievalStatus.EMPTY_RESULT
    assert result.evidence == ()
    assert adapter.search_calls == 1
    assert len(result.attempts) == 1


@pytest.mark.parametrize(
    ("kind", "status_name"),
    [
        ("timeout", "TIMEOUT"),
        ("parse_error", "PARSE_ERROR"),
        ("upstream_error", "UPSTREAM_ERROR"),
    ],
)
def test_retrieval_distinguishes_timeout_parse_and_upstream_failures(kind, status_name):
    """FR-B-02: each injected failure keeps a distinct, reported status."""
    fake = fake_module()
    gateway = gateway_module()
    failure = fake.FakeFailure(
        kind=kind,
        stage="aget_evidence",
        retryable=(kind == "timeout"),
    )
    adapter = fake.FakeRetrievalAdapter(
        script=[fake.FakeOutcome(failure=failure)]
    )
    _, result = retrieve_with(adapter)

    assert result.status is getattr(gateway.RetrievalStatus, status_name)
    assert result.evidence == ()
    assert result.stage == "aget_evidence"
    assert len(result.attempts) == 1
    assert adapter.search_calls == 1


def test_retrieval_default_max_retries_is_zero_but_allows_one_initial_call():
    """FR-B-02 / COST-01: default zero retries still performs the first attempt."""
    fake = fake_module()
    failure = fake.FakeFailure(kind="timeout", retryable=True)
    adapter = fake.FakeRetrievalAdapter(
        script=[fake.FakeOutcome(failure=failure)]
    )
    _, result = retrieve_with(adapter)

    assert result.status is gateway_module().RetrievalStatus.TIMEOUT
    assert adapter.search_calls == 1
    assert len(result.attempts) == 1


def test_retrieval_retries_are_bounded_and_keep_fixed_provider_and_model():
    """FR-B-02 / COST-01: approved retries never switch provider or model."""
    fake = fake_module()
    gateway = gateway_module()
    timeout = fake.FakeOutcome(
        failure=fake.FakeFailure(kind="timeout", retryable=True)
    )
    success = fake.FakeOutcome(
        contexts=(make_context("doc-synthetic-a", line_start=3, line_end=4),)
    )

    retrying_adapter = fake.FakeRetrievalAdapter(
        script=[timeout, timeout, success]
    )
    _, retrying_result = retrieve_with(retrying_adapter, max_retries=2)
    assert retrying_result.status is gateway.RetrievalStatus.SUCCESS
    assert retrying_adapter.search_calls == 3
    assert len(retrying_result.attempts) == 3
    for attempt in retrying_result.attempts:
        assert attempt.provider == PROVIDER
        assert attempt.model == MODEL
        assert attempt.stage

    bounded_adapter = fake.FakeRetrievalAdapter(script=[timeout])
    _, bounded_result = retrieve_with(bounded_adapter, max_retries=1)
    assert bounded_result.status is gateway.RetrievalStatus.TIMEOUT
    assert bounded_adapter.search_calls == 2
    assert len(bounded_result.attempts) == 2
    for attempt in bounded_result.attempts:
        assert attempt.provider == PROVIDER
        assert attempt.model == MODEL


def test_retrieval_does_not_retry_non_retryable_errors():
    """FR-B-02: parse errors fail once, even when a retry budget was supplied."""
    fake = fake_module()
    parse_failure = fake.FakeOutcome(
        failure=fake.FakeFailure(kind="parse_error", retryable=False)
    )
    success = fake.FakeOutcome(
        contexts=(make_context("doc-synthetic-a", line_start=3, line_end=4),)
    )
    adapter = fake.FakeRetrievalAdapter(
        script=[parse_failure, success]
    )
    _, result = retrieve_with(adapter, max_retries=3)

    assert result.status is gateway_module().RetrievalStatus.PARSE_ERROR
    assert adapter.search_calls == 1
    assert len(result.attempts) == 1


def test_untrusted_index_is_rejected_before_loader_or_adapter_is_touched():
    """INV-08 / SEC-01: no pickle-like artifact is ever deserialized."""
    fake = fake_module()
    gateway = gateway_module()
    untrusted = fake.CountingUntrustedSource()
    adapter = fake.FakeRetrievalAdapter(script=[fake.FakeOutcome()])
    request = retrieval_request(gateway)

    with pytest.raises(gateway.UnsafeIndexError):
        port = make_gateway(adapter=adapter, index=untrusted)
        port.retrieve(request)

    assert untrusted.load_calls == 0
    assert adapter.search_calls == 0


# --------------------------------------------------------------------------- #
# Generation pre-call rejection
# --------------------------------------------------------------------------- #
def test_generation_rejects_empty_approved_before_any_outbound_call():
    """FR-D-03 / INV-01: zero approved evidence means zero generation attempts."""
    fake = fake_module()
    gateway = gateway_module()
    factory = fake.FakeModelFactory()
    adapter = fake.FakeRetrievalAdapter()
    port = make_gateway(adapter=adapter, factory=factory)

    result = port.generate(
        generation_request(
            gateway,
            approved=(),
            selected=(),
            policy=generation_policy(gateway),
        )
    )

    assert result.status is gateway.GenerationStatus.REFUSED
    assert result.refusal_reason == "EMPTY_APPROVED"
    assert result.raw_output == ""
    assert result.sent_evidence_ids == ()
    assert_no_generation_outbound(factory, adapter)


def test_generation_rejects_selected_evidence_outside_approved_before_session():
    """FR-D-03 / INV-04: selection is a subset check before any model call."""
    fake = fake_module()
    gateway = gateway_module()
    records = generation_records()
    factory = fake.FakeModelFactory()
    adapter = fake.FakeRetrievalAdapter()
    port = make_gateway(adapter=adapter, factory=factory)

    result = port.generate(
        generation_request(
            gateway,
            approved=(records.ev_a,),
            selected=(records.pending.evidence_id,),
            policy=generation_policy(gateway),
        )
    )

    assert result.status is gateway.GenerationStatus.REFUSED
    assert result.refusal_reason == "SELECTED_OUTSIDE_APPROVED"
    assert result.sent_evidence_ids == ()
    assert_no_generation_outbound(factory, adapter)


@pytest.mark.parametrize(
    "changes",
    [
        {"max_input_tokens": 12001},
        {"compress_at_tokens": 12001},
        {"max_output_tokens": 2001},
        {"max_input_tokens": 9000, "compress_at_tokens": 9001},
        {"max_sources": -1},
    ],
)
def test_generation_rejects_invalid_budget_before_session(changes):
    """FR-D-03 / INV-07: 12000/9000/2000 budget boundaries are enforced."""
    fake = fake_module()
    gateway = gateway_module()
    records = generation_records()
    factory = fake.FakeModelFactory()
    adapter = fake.FakeRetrievalAdapter()
    port = make_gateway(adapter=adapter, factory=factory)

    result = port.generate(
        generation_request(
            gateway,
            approved=(records.ev_a,),
            selected=(records.ev_a.evidence_id,),
            policy=generation_policy(gateway, **changes),
        )
    )

    assert result.status is gateway.GenerationStatus.REFUSED
    assert result.refusal_reason == "INVALID_BUDGET"
    assert_no_generation_outbound(factory, adapter)


@pytest.mark.parametrize(
    "changes",
    [
        {"get_evidence_if_no_contexts": True},
        {"pre_prompt": "Synthetic unapproved pre prompt."},
        {"post_prompt": "Synthetic unapproved post prompt."},
        {"autonomous_agent": True},
    ],
)
def test_generation_rejects_unsafe_session_policy_before_factory(changes):
    """FR-D-03 / INV-01: implicit retrieval, pre/post and agents stay off."""
    fake = fake_module()
    gateway = gateway_module()
    records = generation_records()
    factory = fake.FakeModelFactory()
    adapter = fake.FakeRetrievalAdapter()
    port = make_gateway(adapter=adapter, factory=factory)

    result = port.generate(
        generation_request(
            gateway,
            approved=(records.ev_a,),
            selected=(records.ev_a.evidence_id,),
            policy=generation_policy(gateway, **changes),
        )
    )

    assert result.status is gateway.GenerationStatus.REFUSED
    assert result.refusal_reason == "UNSAFE_SESSION_POLICY"
    assert_no_generation_outbound(factory, adapter)


def test_generation_rejects_empty_serializer_output_before_asking_the_model():
    """FR-D-03: an empty actual-sent set is not a valid generation request."""
    fake = fake_module()
    gateway = gateway_module()
    records = generation_records()
    factory = fake.FakeModelFactory()
    adapter = fake.FakeRetrievalAdapter()
    port = make_gateway(adapter=adapter, factory=factory)

    result = port.generate(
        generation_request(
            gateway,
            approved=(records.ev_a,),
            selected=(records.ev_a.evidence_id,),
            policy=generation_policy(gateway, max_sources=0),
        )
    )

    assert result.status is gateway.GenerationStatus.REFUSED
    assert result.refusal_reason == "EMPTY_SENT"
    assert_no_generation_outbound(factory, adapter)


@pytest.mark.parametrize(
    "case",
    ["snapshot_mismatch", "version_mismatch"],
)
def test_generation_rejects_evidence_outside_snapshot_or_version(case):
    """FR-D-03 / INV-02, INV-04: only current snapshot/version evidence is usable."""
    fake = fake_module()
    gateway = gateway_module()
    bundle = fixture_bundle()
    factory = fake.FakeModelFactory()
    adapter = fake.FakeRetrievalAdapter()
    port = make_gateway(adapter=adapter, factory=factory)

    if case == "snapshot_mismatch":
        foreign = make_evidence(
            "doc-synthetic-a",
            line_start=3,
            line_end=4,
            snapshot_id="snap-" + "a" * 64,
        )
        reason = "EVIDENCE_OUTSIDE_SNAPSHOT"
    else:
        foreign = make_evidence(
            "doc-synthetic-a",
            line_start=3,
            line_end=4,
            version_sha256="b" * 64,
        )
        reason = "EVIDENCE_VERSION_MISMATCH"

    assert foreign.snapshot_id == bundle.snapshot.snapshot_id or case == "snapshot_mismatch"
    result = port.generate(
        generation_request(
            gateway,
            approved=(foreign,),
            selected=(foreign.evidence_id,),
            policy=generation_policy(gateway),
        )
    )

    assert result.status is gateway.GenerationStatus.REFUSED
    assert result.refusal_reason == reason
    assert_no_generation_outbound(factory, adapter)


# --------------------------------------------------------------------------- #
# Generation actual send, raw output and citation aliases
# --------------------------------------------------------------------------- #
def test_generation_records_actual_sent_after_serializer_without_pending_text():
    """FR-D-03 / INV-04: sent is the post-serializer set, never all approved."""
    fake = fake_module()
    gateway = gateway_module()
    records = generation_records()
    factory = fake.FakeModelFactory(
        scripted=[
            fake.FakeGenerationOutput(
                raw_output="Synthetic raw draft [1].",
                citations=(
                    fake.FakeCitationClaim("1", (records.ev_a.evidence_id,)),
                ),
                usage_tokens=17,
            )
        ]
    )
    adapter = fake.FakeRetrievalAdapter()
    port = make_gateway(adapter=adapter, factory=factory)

    result = port.generate(
        generation_request(
            gateway,
            approved=(records.ev_a, records.ev_b),
            selected=(records.ev_a.evidence_id, records.ev_b.evidence_id),
            policy=generation_policy(gateway, max_sources=1),
        )
    )

    assert result.status is gateway.GenerationStatus.SUCCESS
    assert result.raw_output == "Synthetic raw draft [1]."
    assert len(result.sent_evidence_ids) == 1
    assert set(result.sent_evidence_ids) <= {
        records.ev_a.evidence_id,
        records.ev_b.evidence_id,
    }
    assert factory.create_calls == 1
    session = factory.sessions[0]
    assert len(session.contexts) == 1
    sent_context = session.contexts[0]
    assert sent_context.evidence_id == result.sent_evidence_ids[0]
    assert sent_context.text in (records.ev_a.excerpt, records.ev_b.excerpt)
    assert "PENDING-MARKER-B" not in sent_context.text
    assert factory.questions == [
        "Synthetic generation question; no real research question."
    ]
    assert adapter.search_calls == 0


def test_generation_returns_raw_output_and_one_to_one_alias_map():
    """FR-D-03 / INV-04: raw output and unambigous alias→evidence mapping survive."""
    fake = fake_module()
    gateway = gateway_module()
    records = generation_records()
    raw = "Synthetic raw answer citing [1] and [2]."
    factory = fake.FakeModelFactory(
        scripted=[
            fake.FakeGenerationOutput(
                raw_output=raw,
                citations=(
                    fake.FakeCitationClaim("1", (records.ev_a.evidence_id,)),
                    fake.FakeCitationClaim("2", (records.ev_b.evidence_id,)),
                ),
                usage_tokens=42,
            )
        ]
    )
    port = make_gateway(factory=factory)

    result = port.generate(
        generation_request(
            gateway,
            approved=(records.ev_a, records.ev_b),
            selected=(records.ev_a.evidence_id, records.ev_b.evidence_id),
            policy=generation_policy(gateway),
        )
    )

    assert result.status is gateway.GenerationStatus.SUCCESS
    assert result.raw_output == raw
    assert dict(result.citation_aliases) == {
        "1": records.ev_a.evidence_id,
        "2": records.ev_b.evidence_id,
    }
    assert result.unknown_citation_keys == ()
    assert result.ambiguous_citation_keys == ()
    assert set(result.sent_evidence_ids) == {
        records.ev_a.evidence_id,
        records.ev_b.evidence_id,
    }


def test_generation_preserves_unknown_citation_keys_without_silent_mapping():
    """FR-D-03: unknown keys stay visible to D; they are never deleted or mapped."""
    fake = fake_module()
    gateway = gateway_module()
    records = generation_records()
    raw = "Synthetic raw answer with an unresolved [9]."
    factory = fake.FakeModelFactory(
        scripted=[
            fake.FakeGenerationOutput(
                raw_output=raw,
                citations=(fake.FakeCitationClaim("9", ()),),
            )
        ]
    )
    port = make_gateway(factory=factory)

    result = port.generate(
        generation_request(
            gateway,
            approved=(records.ev_a,),
            selected=(records.ev_a.evidence_id,),
            policy=generation_policy(gateway),
        )
    )

    assert result.status is gateway.GenerationStatus.SUCCESS
    assert result.raw_output == raw
    assert set(result.unknown_citation_keys) == {"9"}
    assert "9" not in dict(result.citation_aliases)
    assert result.ambiguous_citation_keys == ()


def test_generation_refuses_ambiguous_alias_without_arbitrary_mapping():
    """FR-D-03: an alias collision is a reported failure, not a guessed mapping."""
    fake = fake_module()
    gateway = gateway_module()
    records = generation_records()
    raw = "Synthetic raw answer with ambiguous [3]."
    factory = fake.FakeModelFactory(
        scripted=[
            fake.FakeGenerationOutput(
                raw_output=raw,
                citations=(
                    fake.FakeCitationClaim(
                        "3",
                        (records.ev_a.evidence_id, records.ev_b.evidence_id),
                    ),
                ),
            )
        ]
    )
    port = make_gateway(factory=factory)

    result = port.generate(
        generation_request(
            gateway,
            approved=(records.ev_a, records.ev_b),
            selected=(records.ev_a.evidence_id, records.ev_b.evidence_id),
            policy=generation_policy(gateway),
        )
    )

    assert result.status is gateway.GenerationStatus.AMBIGUOUS_CITATIONS
    assert result.raw_output == raw
    assert set(result.ambiguous_citation_keys) == {"3"}
    assert "3" not in dict(result.citation_aliases)
    assert set(result.sent_evidence_ids) == {
        records.ev_a.evidence_id,
        records.ev_b.evidence_id,
    }


def test_generation_creates_fresh_isolated_sessions_with_sanitized_policy():
    """FR-D-03 / INV-04: no old session reuse; only selected contexts; flags off."""
    fake = fake_module()
    gateway = gateway_module()
    records = generation_records()
    factory = fake.FakeModelFactory(
        scripted=[
            fake.FakeGenerationOutput(raw_output="Synthetic first answer."),
            fake.FakeGenerationOutput(raw_output="Synthetic second answer."),
        ]
    )
    port = make_gateway(factory=factory)

    first = port.generate(
        generation_request(
            gateway,
            approved=(records.ev_a, records.ev_b),
            selected=(records.ev_a.evidence_id,),
            policy=generation_policy(gateway, max_sources=1),
        )
    )
    second = port.generate(
        generation_request(
            gateway,
            approved=(records.ev_a, records.ev_b),
            selected=(records.ev_b.evidence_id,),
            policy=generation_policy(gateway, max_sources=1),
        )
    )

    assert first.status is gateway.GenerationStatus.SUCCESS
    assert second.status is gateway.GenerationStatus.SUCCESS
    assert factory.create_calls == 2
    assert len(factory.sessions) == 2
    first_session, second_session = factory.sessions
    assert first_session is not second_session
    assert first_session.reused is False
    assert second_session.reused is False
    assert {context.evidence_id for context in first_session.contexts} == {
        records.ev_a.evidence_id
    }
    assert {context.evidence_id for context in second_session.contexts} == {
        records.ev_b.evidence_id
    }
    assert records.ev_b.evidence_id not in {
        context.evidence_id for context in first_session.contexts
    }
    assert "PENDING-MARKER-B" not in "".join(
        context.text for context in second_session.contexts
    )
    assert len(factory.questions) == 2
    for payload in factory.create_payloads:
        policy = payload["policy"]
        assert policy.get_evidence_if_no_contexts is False
        assert policy.pre_prompt is None
        assert policy.post_prompt is None
        assert policy.autonomous_agent is False


# --------------------------------------------------------------------------- #
# Authority boundaries and view projection
# --------------------------------------------------------------------------- #
def test_result_types_are_not_review_or_release_decisions():
    """INV-03 / INV-04: B returns candidates/raw output, never human authority."""
    fake = fake_module()
    gateway = gateway_module()
    contracts = contracts_module()
    malicious = make_evidence(
        "doc-synthetic-a",
        line_start=3,
        line_end=4,
        advisory_summary="ACCEPTED by synthetic model; RELEASED without human review.",
        upstream_context_id="ctx-malicious",
    )
    factory = fake.FakeModelFactory(
        scripted=[
            fake.FakeGenerationOutput(
                raw_output="Synthetic draft with a suspicious advisory.",
                citations=(fake.FakeCitationClaim("1", (malicious.evidence_id,)),),
            )
        ]
    )
    port = make_gateway(factory=factory)

    result = port.generate(
        generation_request(
            gateway,
            approved=(malicious,),
            selected=(malicious.evidence_id,),
            policy=generation_policy(gateway),
        )
    )

    assert result.status is gateway.GenerationStatus.SUCCESS
    assert not isinstance(result, (contracts.ReviewDecision, contracts.ReleaseDecision))
    assert not hasattr(result, "review_decision")
    assert not hasattr(result, "release_decision")
    assert not hasattr(result, "accepted")
    assert not hasattr(result, "released")


def test_retrieval_view_projects_status_without_authority():
    """INV-03 / INV-04 / QA-01: the view shows state, not acceptance or release."""
    fake = fake_module()
    context = make_context(
        "doc-synthetic-a",
        line_start=3,
        line_end=4,
        summary="ACCEPTED and RELEASED; this is only malicious advisory text.",
        score=1.0,
    )
    adapter = fake.FakeRetrievalAdapter(
        script=[fake.FakeOutcome(contexts=(context,))]
    )
    _, result = retrieve_with(adapter)

    assert result.status is gateway_module().RetrievalStatus.SUCCESS
    projection = view_module().project_retrieval_view(result)
    assert projection["status"] == result.status.value
    assert len(projection["evidence"]) == 1
    item = projection["evidence"][0]
    for key in (
        "evidence_id",
        "document_id",
        "version_sha256",
        "locator",
        "excerpt",
        "advisory_summary",
    ):
        assert key in item, f"view projection lost required display field {key}"
    for forbidden in (
        "accepted",
        "accepted_by",
        "review_decision",
        "release_decision",
        "released",
        "release_status",
    ):
        assert forbidden not in item
        assert forbidden not in projection
    assert not hasattr(item, "accepted")
    assert not hasattr(item, "released")
