from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import os
import re
import socket
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BASELINE_COMMIT = "c692d0dfeac4a0296599f7fe21a253a58b7ac12a"
RUNTIME = ROOT / ".local" / "unblock" / "runtime"
TMP_ROOT = RUNTIME / "tmp"

# Import the fixed checkout directly. Do not pip-install -e the project: that may
# rewrite the ignored setuptools_scm version file under src/paperqa/.
for source_path in (
    ROOT / "src",
    ROOT / "packages" / "paper-qa-pypdf" / "src",
):
    sys.path.insert(0, str(source_path))

# LiteLLM fetches its model-cost metadata at import time by default. Force its
# bundled map before importing lmi/PaperQA so this offline probe makes no startup
# HTTP request either.
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"

get_model_cost_map_source_info = importlib.import_module(
    "litellm.litellm_core_utils.get_model_cost_map"
).get_model_cost_map_source_info
from aviary.core import Message  # noqa: E402
from lmi import EmbeddingModel, LLMModel  # noqa: E402
from lmi.types import LLMResult  # noqa: E402
from pydantic import PrivateAttr  # noqa: E402

from paperqa import Docs, Settings  # noqa: E402
from paperqa.prompts import CANNOT_ANSWER_PHRASE  # noqa: E402
from paperqa.types import PQASession  # noqa: E402
from paperqa.version import __version__ as PAPERQA_VERSION  # noqa: E402

APPROVED_FACT = (
    "AZURITE_FACT: Azurite is the pigment identified as stable deep blue indoors."
)
EXCLUDED_MARKER = "EXCLUDED_NEVER_INCLUDE_54f0d1"
PENDING_MARKER = "PENDING_NEVER_INCLUDE_9a31c7"
QUESTION = "Which pigment does the approved evidence identify as stable deep blue indoors?"


def _embedding(text: str, dimensions: int) -> list[float]:
    """Stable, local hash embedding for exercising the real vector-store path."""
    vector = [0.0] * dimensions
    for token in re.findall(r"[a-z0-9]+", text.lower()):
        bucket = int.from_bytes(hashlib.sha256(token.encode()).digest()[:4], "big")
        vector[bucket % dimensions] += 1.0
    norm = sum(value * value for value in vector) ** 0.5
    return [value / norm for value in vector] if norm else vector


class OfflineEmbedding(EmbeddingModel):
    name: str = "deterministic-hash-test-double"
    ndim: int = 128
    _call_count: int = PrivateAttr(default=0)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self._call_count += 1
        return [_embedding(text, self.ndim) for text in texts]


class OfflineLLM(LLMModel):
    name: str
    purpose: str
    context_id: str = ""
    _prompts: list[str] = PrivateAttr(default_factory=list)

    @property
    def call_count(self) -> int:
        return len(self._prompts)

    @property
    def prompts(self) -> list[str]:
        return self._prompts

    async def call_single(
        self,
        messages: list[Message] | str,
        callbacks=None,
        name: str | None = None,
        **kwargs,
    ) -> LLMResult:
        if isinstance(messages, str):
            prompt = messages
        else:
            prompt = "\n".join(str(message.content or "") for message in messages)
        self._prompts.append(prompt)

        if self.purpose == "summary":
            source_summary = next((marker for marker in (EXCLUDED_MARKER, PENDING_MARKER) if marker in prompt), APPROVED_FACT)
            text = json.dumps({"summary": source_summary, "relevance_score": 9}, ensure_ascii=False)
        elif self.purpose == "answer":
            # This is a deterministic demonstration response, not a real model answer.
            text = (
                "SIMULATED_OFFLINE_ANSWER: the evidence identifies azurite as the"
                f" stable deep-blue pigment indoors ({self.context_id})."
            )
        else:
            raise ValueError(f"Unknown fake model purpose: {self.purpose}")
        return LLMResult(model=self.name, text=text, prompt_count=0, completion_count=0)


def _configure_network_fence(counter: dict[str, int]):
    def denied_connect(_sock, _address):
        counter["attempts"] += 1
        raise AssertionError("network connection attempted in offline PaperQA smoke")

    def denied_connect_ex(_sock, _address):
        counter["attempts"] += 1
        raise AssertionError("network connection attempted in offline PaperQA smoke")

    return (
        patch.object(socket.socket, "connect", denied_connect),
        patch.object(socket.socket, "connect_ex", denied_connect_ex),
    )


def _settings() -> Settings:
    settings = Settings(
        _env_file=None,
        llm="offline/fake-answer",
        summary_llm="offline/fake-summary",
        embedding="sparse",
        answer={
            "evidence_k": 5,
            "answer_max_sources": 2,
            "get_evidence_if_no_contexts": False,
            "evidence_skip_summary": False,
        },
        parsing={"multimodal": False, "use_doc_details": False},
        prompts={"pre": None, "post": None, "answer_iteration_prompt": None},
    )
    return settings


async def _exercise() -> dict[str, Any]:
    RUNTIME.mkdir(parents=True, exist_ok=True)
    TMP_ROOT.mkdir(parents=True, exist_ok=True)
    network_counter = {"attempts": 0}
    fence_connect, fence_connect_ex = _configure_network_fence(network_counter)

    with fence_connect, fence_connect_ex:
        settings = _settings()
        embedding = OfflineEmbedding()
        summary_model = OfflineLLM(name="offline-fake-summary", purpose="summary")
        answer_model = OfflineLLM(name="offline-fake-answer", purpose="answer")
        docs = Docs(name="paperqa-unblock-approved-fixture")

        source_path = TMP_ROOT / "approved-evidence.txt"
        source_path.write_text(
            "Synthetic source for offline integration verification.\n\n"
            + APPROVED_FACT
            + "\n",
            encoding="utf-8",
        )
        await docs.aadd(
            source_path,
            citation="Synthetic approved-source fixture (not a real paper)",
            docname="approved-source-fixture",
            settings=settings,
            llm_model=answer_model,
            embedding_model=embedding,
        )

        # Populate the SAME real store with excluded/pending sources, then pass
        # only approved contexts in a fresh query. This is a technical selection
        # fixture, not C's human ledger or B/D's production adapter.
        for label, marker in (("excluded", EXCLUDED_MARKER), ("pending", PENDING_MARKER)):
            extra = TMP_ROOT / (label + "-evidence.txt")
            extra.write_text("Synthetic rejected or pending source: " + marker + "\n", encoding="utf-8")
            await docs.aadd(extra, citation="Synthetic " + label + " fixture", docname=label + "-source-fixture",
                            settings=settings, llm_model=answer_model, embedding_model=embedding)
        candidates = await docs.aget_evidence(
            QUESTION,
            settings=settings,
            embedding_model=embedding,
            summary_llm_model=summary_model,
        )
        if len(candidates.contexts) != 3:
            raise AssertionError("the fixed Docs.aget_evidence path must retain all three candidates")
        approved_contexts = [context for context in candidates.contexts if context.text.name.startswith("approved-source-fixture")]
        session = PQASession(question=QUESTION, contexts=approved_contexts)
        answer_model.context_id = session.contexts[0].id
        answered = await docs.aquery(
            session,
            settings=settings,
            llm_model=answer_model,
            summary_llm_model=summary_model,
            embedding_model=embedding,
        )
        final_prompt = answer_model.prompts[-1]

        empty_docs = docs  # No approved contexts, but rejected evidence is still in the real store.
        empty_embedding = OfflineEmbedding()
        empty_summary = OfflineLLM(name="offline-empty-summary", purpose="summary")
        empty_answer = OfflineLLM(name="offline-empty-answer", purpose="answer")
        empty_session = PQASession(question="What does the empty approved collection prove?")
        lazy_retrieval_calls = {"count": 0}
        original_aget_evidence = Docs.aget_evidence

        async def count_lazy_retrieval(self, *args, **kwargs):
            if self is empty_docs:
                lazy_retrieval_calls["count"] += 1
            return await original_aget_evidence(self, *args, **kwargs)

        with patch.object(Docs, "aget_evidence", count_lazy_retrieval):
            empty_result = await empty_docs.aquery(
                empty_session,
                settings=settings,
                llm_model=empty_answer,
                summary_llm_model=empty_summary,
                embedding_model=empty_embedding,
            )

    empty_answer_text = empty_result.answer or empty_result.raw_answer
    positive_answer_text = answered.answer or answered.raw_answer
    return {
        "status": "PASS",
        "upstream_commit": BASELINE_COMMIT,
        "versions": {
            "python": sys.version.split()[0],
            "paperqa_source": PAPERQA_VERSION,
            "fhaviary": importlib.metadata.version("fhaviary"),
            "fhlmi": importlib.metadata.version("fhlmi"),
            "litellm": importlib.metadata.version("litellm"),
            "numpy": importlib.metadata.version("numpy"),
            "pydantic": importlib.metadata.version("pydantic"),
            "pypdf": importlib.metadata.version("pypdf"),
        },
        "litellm_model_cost_map": get_model_cost_map_source_info(),
        "source_locations": {
            "Docs": str(Path(Docs.__module__.replace(".", "/") + ".py")),
            "docs_py": "<repo>/src/paperqa/docs.py",
            "Settings": "<repo>/src/paperqa/settings.py",
            "PQASession_and_Context": "<repo>/src/paperqa/types.py",
        },
        "models": {
            "embedding": "deterministic hash-vector test double; no provider",
            "summary_llm": "deterministic JSON test double; simulated output",
            "answer_llm": "deterministic answer test double; simulated output",
        },
        "positive": {
            "docs_type": type(docs).__name__,
            "session_type": type(answered).__name__,
            "context_count": len(answered.contexts),
            "candidate_context_count": len(candidates.contexts),
            "excluded_available_in_docs": any(EXCLUDED_MARKER in context.text.text for context in candidates.contexts),
            "pending_available_in_docs": any(PENDING_MARKER in context.text.text for context in candidates.contexts),
            "generation_session_is_new": session.id != candidates.id,
            "retrieved_contexts": [
                {"name": context.text.name, "summary": context.context, "score": context.score}
                for context in answered.contexts
            ],
            "answer": positive_answer_text,
            "answer_is_simulated": positive_answer_text.startswith(
                "SIMULATED_OFFLINE_ANSWER:"
            ),
            "approved_fact_in_final_prompt": APPROVED_FACT in final_prompt,
            "excluded_marker_in_final_prompt": EXCLUDED_MARKER in final_prompt,
            "pending_marker_in_final_prompt": PENDING_MARKER in final_prompt,
            "final_user_prompt": final_prompt,
            "embedding_calls": embedding._call_count,
            "summary_calls": summary_model.call_count,
            "answer_calls": answer_model.call_count,
        },
        "negative": {
            "context_count": len(empty_result.contexts),
            "documents_available": len(empty_docs.docs),
            "answer": empty_answer_text,
            "answer_contains_cannot_answer": CANNOT_ANSWER_PHRASE in empty_answer_text,
            "embedding_calls": empty_embedding._call_count,
            "summary_calls": empty_summary.call_count,
            "answer_calls": empty_answer.call_count,
            "lazy_retrieval_calls": lazy_retrieval_calls["count"],
            "session_is_fresh": (
                empty_result.id != answered.id and not empty_result.contexts
            ),
        },
        "prompt_pre_enabled": settings.prompts.pre is not None,
        "prompt_post_enabled": settings.prompts.post is not None,
        "get_evidence_if_no_contexts": settings.answer.get_evidence_if_no_contexts,
        "network_connect_attempts": network_counter["attempts"],
        "limitations": [
            "All embedding, summary, and answer model outputs are injected simulations.",
            "This proves API wiring and prompt-boundary behavior only, not answer quality.",
            "Three synthetic sources are in the store; only one manually selected context is sent; no A-E business adapter or human ledger is implemented.",
        ],
    }


def run_smoke() -> dict[str, Any]:
    report = asyncio.run(_exercise())
    checks = (
        report["positive"]["context_count"] == 1,
        report["positive"]["approved_fact_in_final_prompt"],
        not report["positive"]["excluded_marker_in_final_prompt"],
        not report["positive"]["pending_marker_in_final_prompt"],
        report["positive"]["answer_is_simulated"],
        report["negative"]["context_count"] == 0,
        report["negative"]["embedding_calls"] == 0,
        report["negative"]["summary_calls"] == 0,
        report["negative"]["answer_calls"] == 0,
        report["negative"]["lazy_retrieval_calls"] == 0,
        report["negative"]["session_is_fresh"],
        report["negative"]["answer_contains_cannot_answer"],
        report["network_connect_attempts"] == 0,
        report["litellm_model_cost_map"]["source"] == "local",
        report["litellm_model_cost_map"]["is_env_forced"],
        report["litellm_model_cost_map"]["url"] is None,
        report["litellm_model_cost_map"]["fallback_reason"] is None,
        not report["prompt_pre_enabled"],
        not report["prompt_post_enabled"],
        not report["get_evidence_if_no_contexts"],
    )
    if not all(checks):
        report["status"] = "FAIL"
        raise AssertionError(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print the result as JSON")
    parser.add_argument(
        "--report",
        type=Path,
        help="write the JSON proof artifact at this path (relative to the repository root)",
    )
    args = parser.parse_args()
    report = run_smoke()
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        report_path = args.report if args.report.is_absolute() else ROOT / args.report
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
