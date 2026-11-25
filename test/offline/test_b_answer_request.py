"""FR-D-03, INV-01 and INV-07 at B's real PaperQA2 answer-model boundary."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from runpy import run_path

import pytest
import yaml
from pytest_socket import disable_socket

from papertrace.contracts import CorpusSnapshot, DocumentVersion, EvidenceRecord, SourceLocator
from papertrace.retrieval.gateway import (
    Gateway,
    GenerationPolicy,
    GenerationRequest,
    GenerationStatus,
    PaperQA2Adapter,
)

# asyncio.run needs a local socketpair. The fixture immediately blocks IP sockets.
pytestmark = pytest.mark.enable_socket

ROOT = Path(__file__).resolve().parents[2]
SYSTEM_PROMPT = ROOT / "prompts" / "answer-system-v1.0.txt"
SYSTEM_PROMPT_YAML = ROOT / "prompts" / "prompt_v1.0.yaml"
PENDING = "PENDING_NEVER_SEND: an unreviewed synthetic study."
PROVIDER = "synthetic-provider"
MODEL = "synthetic-model"
REQUESTED_AT = datetime(2026, 11, 24, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def approved_system_prompt():
    expected = yaml.safe_load(SYSTEM_PROMPT_YAML.read_bytes())["system"]
    assert isinstance(expected, str) and expected.strip()
    assert len(expected.splitlines()) == 6
    assert expected.endswith("\n") and not expected.endswith("\n\n")
    return expected


def _validated_system_prompt(approved: str) -> str:
    assert SYSTEM_PROMPT.is_file(), "Missing the versioned system prompt used by Gate 4"
    content = SYSTEM_PROMPT.read_bytes()
    assert content == approved.encode("utf-8"), "Versioned system TXT differs from approved YAML"
    return content.decode("utf-8")


@pytest.fixture
def capture_qual02(tmp_path, monkeypatch):
    disable_socket(allow_unix_socket=True)
    monkeypatch.setenv("PQA_HOME", str(tmp_path))
    monkeypatch.setenv("LITELLM_LOCAL_MODEL_COST_MAP", "True")
    smoke = run_path(str(ROOT / "scripts" / "paperqa_smoke.py"))
    check_request = run_path(str(ROOT / "scripts" / "semantic_evidence.py"))["_check_request"]
    cases = json.loads((ROOT / "test/evaluation/cases.json").read_bytes())["cases"]
    case = next(item for item in cases if item["id"] == "QUAL-02")
    material = case["input"]

    material_by_label = {
        row["id"]: row["text"] for row in material["approved_evidence"]
    }
    material_by_label["pending"] = PENDING
    documents = {
        label: DocumentVersion(
            schema_version=1,
            document_id=f"doc-{label}",
            version_sha256=sha256(f"{text}\n".encode("utf-8")).hexdigest(),
            title=label,
            source_name=f"{label}.txt",
            status="ready",
        )
        for label, text in material_by_label.items()
    }
    snapshot = CorpusSnapshot(
        schema_version=1,
        documents=tuple(documents.values()),
        created_at=REQUESTED_AT,
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
            excerpt=material_by_label[label],
            retrieved_at=REQUESTED_AT,
        )
        for label, document in documents.items()
    }
    gate_case = {
        "input": {
            "question": material["question"],
            "approved_evidence": [
                {"id": records[row["id"]].evidence_id, "text": row["text"]}
                for row in material["approved_evidence"]
            ],
        }
    }

    def run(selected, expected, *, approved=("ev-a", "ev-b"), max_sources=None, over_cap=False):
        calls = []
        counted = []
        citations = ", ".join(records[label].evidence_id for label in expected)

        class CaptureModel(smoke["OfflineLLM"]):
            provider: str = PROVIDER
            model: str = MODEL

            def count_tokens(self, text):
                counted.append(text)
                return 12001 if over_cap else 100

            async def call_single(self, messages, *args, **kwargs):
                calls.append(
                    [{"role": message.role, "content": message.content} for message in messages]
                )
                return smoke["LLMResult"](
                    model=self.name,
                    text=f"Synthetic comparison ({citations}).",
                    prompt_count=0,
                    completion_count=0,
                )

        def no_source_read(*args, **kwargs):
            pytest.fail("Approved evidence generation unexpectedly entered retrieval")

        bridge = PaperQA2Adapter(
            source_reader=no_source_read,
            settings=smoke["_settings"](),
            answer_llm_model=CaptureModel(name=MODEL, purpose="answer"),
            summary_llm_model=object(),
            embedding_model=object(),
            temporary_directory=tmp_path,
        )
        gateway = Gateway(
            adapter=bridge,
            source_reader=no_source_read,
            model_factory=bridge,
            clock=lambda: REQUESTED_AT,
        )
        network = {"attempts": 0}
        fence, fence_ex = smoke["_configure_network_fence"](network)
        with fence, fence_ex:
            result = gateway.generate(
                GenerationRequest(
                    snapshot=snapshot,
                    question=material["question"],
                    approved_evidence=tuple(records[label] for label in approved),
                    selected_evidence_ids=tuple(records[label].evidence_id for label in selected),
                    policy=GenerationPolicy(
                        provider=PROVIDER, model=MODEL, max_sources=max_sources
                    ),
                )
            )
        assert network["attempts"] == 0
        assert result.accounting is not None
        assert result.accounting.answer_model_attempts == len(calls)
        sent = tuple(records[label].evidence_id for label in expected)
        assert result.sent_evidence_ids == sent
        return result, calls, counted

    return run, check_request, gate_case


@pytest.mark.parametrize(
    ("selected", "expected", "max_sources"),
    [
        pytest.param(("ev-a", "ev-b"), ("ev-a", "ev-b"), None, id="forward"),
        pytest.param(("ev-b", "ev-a"), ("ev-b", "ev-a"), None, id="reverse"),
        pytest.param(("ev-b", "ev-a"), ("ev-b",), 1, id="trimmed"),
    ],
)
def test_qual02_model_entry_has_exact_approved_json(
    capture_qual02, approved_system_prompt, selected, expected, max_sources
):
    run, check_request, gate_case = capture_qual02
    result, calls, counted = run(selected, expected, max_sources=max_sources)
    assert result.status is GenerationStatus.SUCCESS
    (messages,) = calls
    assert [message["role"] for message in messages] == ["system", "user"]
    system, user = (message["content"] for message in messages)
    assert PENDING not in user
    # Report the legacy template failure even before the versioned system is wired.
    try:
        json.loads(user)
    except json.JSONDecodeError:
        pytest.fail("request-invalid-structured-material: captured user content is not JSON")
    check_request(
        {"request": messages, "sent_ids": result.sent_evidence_ids},
        gate_case,
        _validated_system_prompt(approved_system_prompt),
    )
    assert f"{system}\n{user}" in counted
    assert result.citation_aliases == tuple(
        (evidence_id, evidence_id) for evidence_id in result.sent_evidence_ids
    )
    assert result.unknown_citation_keys == ()


def test_qual02_model_entry_uses_versioned_system_prompt(
    capture_qual02, approved_system_prompt
):
    run, _, _ = capture_qual02
    _, calls, _ = run(("ev-a",), ("ev-a",))
    (messages,) = calls
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == _validated_system_prompt(approved_system_prompt)


@pytest.mark.parametrize("scenario", ["empty-approved", "over-cap", "pending-selected"])
def test_qual02_refusals_enter_no_answer_model(capture_qual02, scenario):
    run, _, _ = capture_qual02
    if scenario == "empty-approved":
        result, calls, _ = run((), (), approved=())
    elif scenario == "over-cap":
        result, calls, counted = run(("ev-a",), (), over_cap=True)
        assert counted
    else:
        result, calls, _ = run(("pending",), ())
    assert result.status is GenerationStatus.REFUSED
    assert result.raw_output == ""
    assert calls == []
