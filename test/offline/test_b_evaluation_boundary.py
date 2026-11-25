"""Test proposal for B's opt-in fixed-ID evaluation and raw request capture."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from runpy import run_path

import pytest
from pytest_socket import disable_socket

from papertrace.contracts import CorpusSnapshot, DocumentVersion, EvidenceRecord, SourceLocator
from papertrace.retrieval import gateway as b

pytestmark = pytest.mark.enable_socket
ROOT = Path(__file__).resolve().parents[2]
REQUESTED_AT = datetime(2026, 11, 25, tzinfo=timezone.utc)
PENDING = "SYNTHETIC_PENDING_EVALUATION_SENTINEL"
PROVIDER = "synthetic-provider"
MODEL = "synthetic-model"


@pytest.fixture
def run_qual02(tmp_path, monkeypatch):
    disable_socket(allow_unix_socket=True)
    monkeypatch.setenv("PQA_HOME", str(tmp_path))
    monkeypatch.setenv("LITELLM_LOCAL_MODEL_COST_MAP", "True")
    smoke = run_path(str(ROOT / "scripts/paperqa_smoke.py"))
    gate = run_path(str(ROOT / "scripts/semantic_evidence.py"))
    data = (ROOT / "test/evaluation/cases.json").read_bytes()
    case = next(row for row in json.loads(data)["cases"] if row["id"] == "QUAL-02")
    material = case["input"]
    fixed_evidence = tuple((row["id"], row["text"]) for row in material["approved_evidence"])
    source = {**dict(fixed_evidence), "pending": PENDING}
    documents = {
        label: DocumentVersion(
            schema_version=1,
            document_id=f"doc-{label}",
            version_sha256=sha256(text.encode("utf-8")).hexdigest(),
            title=label,
            source_name=f"{label}.txt",
            status="ready",
        )
        for label, text in source.items()
    }
    snapshot = CorpusSnapshot(
        schema_version=1, documents=tuple(documents.values()), created_at=REQUESTED_AT,
    )
    records = {
        label: EvidenceRecord(
            schema_version=1,
            snapshot_id=snapshot.snapshot_id,
            document_id=document.document_id,
            version_sha256=document.version_sha256,
            locator=SourceLocator(
                schema_version=1,
                line_start=1,
                line_end=1,
                chunk_id=f"chunk-{label}",
                parser_name="papertrace-synthetic",
                parser_version="1",
            ),
            excerpt=source[label],
            retrieved_at=REQUESTED_AT,
        )
        for label, document in documents.items()
    }
    mapping = {label: records[label].evidence_id for label, _ in fixed_evidence}
    system = (ROOT / "prompts/answer-system-v1.0.txt").read_bytes().decode("utf-8")

    def run(
        selected=("ev-a", "ev-b"),
        *,
        evaluation=True,
        approved=("ev-a", "ev-b"),
        max_sources=None,
        invalid_binding=None,
        cite=None,
        observer_error=False,
        over_budget=False,
        alter_messages=False,
    ):
        events = []

        class CaptureModel(smoke["OfflineLLM"]):
            provider: str = PROVIDER
            model: str = MODEL

            def count_tokens(self, text):
                return 12001 if over_budget else 100

            async def call_single(self, messages, *args, **kwargs):
                actual = tuple((message.role, message.content) for message in messages)
                events.append(("model", actual))
                ids = [row["id"] for row in json.loads(actual[1][1])["approved_evidence"]]
                response_ids = [cite] if cite is not None else ids
                return smoke["LLMResult"](
                    model=self.name,
                    text=f"Synthetic comparison ({', '.join(response_ids)}).",
                    prompt_count=0,
                    completion_count=0,
                )

        def observe(messages):
            assert isinstance(messages, tuple)
            events.append(("capture", messages))
            if observer_error:
                raise RuntimeError("synthetic unavailable capture sink")

        def no_source_read(*args, **kwargs):
            pytest.fail("Generation unexpectedly entered retrieval")

        extra = {}
        if evaluation:
            binding_type = getattr(b, "EvaluationCaseBinding", None)
            assert binding_type is not None, "B has no evaluation case binding entry point"
            binding = {
                "dataset_sha256": sha256(data).hexdigest(),
                "case_id": "QUAL-02",
                "snapshot_id": snapshot.snapshot_id,
                "question": material["question"],
                "fixed_evidence": fixed_evidence,
                "fixed_to_runtime": tuple(mapping.items()),
            }
            if invalid_binding == "missing":
                binding["fixed_to_runtime"] = (("ev-a", mapping["ev-a"]),)
            elif invalid_binding == "duplicate":
                binding["fixed_to_runtime"] = tuple((label, mapping["ev-a"]) for label in mapping)
            elif invalid_binding == "pending":
                binding["fixed_to_runtime"] = (
                    ("ev-a", mapping["ev-a"]), ("ev-b", records["pending"].evidence_id),
                )
            elif invalid_binding == "text":
                binding["fixed_evidence"] = (("ev-a", "Changed text"), fixed_evidence[1])
            elif invalid_binding == "snapshot":
                binding["snapshot_id"] = "snap-" + "0" * 64
            elif invalid_binding == "question":
                binding["question"] = "Different evaluation question?"
            extra = {"evaluation_binding": binding_type(**binding), "request_observer": observe}

        if alter_messages:
            original = smoke["Docs"].aquery

            def changed_query(docs, session, *, settings, **kwargs):
                settings.prompts.qa = "{context} unexpected suffix"
                return original(docs, session, settings=settings, **kwargs)

            monkeypatch.setattr(smoke["Docs"], "aquery", changed_query)
        bridge = b.PaperQA2Adapter(
            source_reader=no_source_read,
            settings=smoke["_settings"](),
            answer_llm_model=CaptureModel(name=MODEL, purpose="answer"),
            summary_llm_model=object(),
            embedding_model=object(),
            temporary_directory=tmp_path,
        )
        gateway = b.Gateway(
            adapter=bridge,
            source_reader=no_source_read,
            model_factory=bridge,
            clock=lambda: REQUESTED_AT,
            **extra,
        )
        network = {"attempts": 0}
        fence, fence_ex = smoke["_configure_network_fence"](network)
        with fence, fence_ex:
            result = gateway.generate(
                b.GenerationRequest(
                    snapshot=snapshot,
                    question=material["question"],
                    approved_evidence=tuple(records[label] for label in approved),
                    selected_evidence_ids=tuple(records[label].evidence_id for label in selected),
                    policy=b.GenerationPolicy(provider=PROVIDER, model=MODEL, max_sources=max_sources),
                )
            )
        assert network["attempts"] == 0
        assert result.accounting is not None
        assert result.accounting.answer_model_attempts == sum(kind == "model" for kind, _ in events)
        return result, events

    return run, mapping, gate["_check_request"], case, system


def test_default_generation_keeps_canonical_ids(run_qual02):
    run, mapping, _, _, _ = run_qual02
    result, events = run(evaluation=False)
    ((kind, messages),) = events
    assert kind == "model"
    ids = tuple(row["id"] for row in json.loads(messages[1][1])["approved_evidence"])
    assert ids == result.sent_evidence_ids == tuple(mapping.values())
    assert result.status is b.GenerationStatus.SUCCESS


@pytest.mark.parametrize(
    ("selected", "sent", "max_sources"),
    [
        pytest.param(("ev-a", "ev-b"), ("ev-a", "ev-b"), None, id="forward"),
        pytest.param(("ev-b", "ev-a"), ("ev-b", "ev-a"), None, id="reverse"),
        pytest.param(("ev-b", "ev-a"), ("ev-b",), 1, id="trimmed"),
    ],
)
def test_fixed_ids_capture_actual_request_and_resolve_runtime_citations(
    run_qual02, selected, sent, max_sources,
):
    run, mapping, check_request, case, system = run_qual02
    result, events = run(selected, max_sources=max_sources)
    assert [kind for kind, _ in events] == ["capture", "model"]
    capture, actual = (messages for _, messages in events)
    assert capture == actual
    messages = [{"role": role, "content": content} for role, content in capture]
    check_request({"request": messages, "sent_ids": sent}, case, system)
    assert PENDING not in messages[1]["content"]
    assert result.status is b.GenerationStatus.SUCCESS
    assert result.sent_evidence_ids == tuple(mapping[label] for label in sent)
    assert result.citation_aliases == tuple((label, mapping[label]) for label in sent)


@pytest.mark.parametrize("invalid", ["missing", "duplicate", "pending", "text", "snapshot", "question"])
def test_invalid_binding_never_reaches_capture_or_model(run_qual02, invalid):
    run, _, _, _, _ = run_qual02
    result, events = run(invalid_binding=invalid)
    assert result.status is b.GenerationStatus.REFUSED
    assert result.sent_evidence_ids == ()
    assert events == []


def test_crop_cannot_create_a_citation_alias_for_unsent_evidence(run_qual02):
    run, mapping, _, _, _ = run_qual02
    result, events = run(("ev-b", "ev-a"), max_sources=1, cite="ev-a")
    assert [kind for kind, _ in events] == ["capture", "model"]
    assert result.sent_evidence_ids == (mapping["ev-b"],)
    assert result.citation_aliases == ()
    assert result.unknown_citation_keys == ("ev-a",)


@pytest.mark.parametrize("refusal", ["empty", "over-budget", "mismatch", "capture-error"])
def test_evaluation_checks_precede_model_entry(run_qual02, refusal):
    run, _, _, _, _ = run_qual02
    settings = {
        "empty": {"selected": (), "approved": ()},
        "over-budget": {"over_budget": True},
        "mismatch": {"alter_messages": True},
        "capture-error": {"observer_error": True},
    }[refusal]
    result, events = run(**settings)
    assert result.status is b.GenerationStatus.REFUSED
    assert result.sent_evidence_ids == ()
    assert [kind for kind, _ in events] == (["capture"] if refusal == "capture-error" else [])
