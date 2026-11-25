"""Proposal for INV-07 answer context compaction at the B model boundary."""

import json
import logging
from pathlib import Path
from runpy import run_path

import pytest

from papertrace.retrieval import gateway as b

pytestmark = pytest.mark.enable_socket

# Reuse the checked-in QUAL-02 fixture without editing its approved test file
# or relying on pytest's test-module import mode.
run_qual02 = run_path(str(Path(__file__).with_name("test_b_evaluation_boundary.py")))["run_qual02"]


@pytest.mark.parametrize("evaluation", [True, False], ids=["fixed-id", "product"])
@pytest.mark.parametrize(
    ("selected", "pair_tokens", "single_tokens", "key_tokens", "cap", "sent"),
    [
        pytest.param(("ev-a", "ev-b"), 8999, 7000, 100, 12000, ("ev-a", "ev-b"), id="below-threshold"),
        pytest.param(("ev-a", "ev-b"), 9000, 7000, 100, 12000, ("ev-a",), id="at-threshold"),
        pytest.param(("ev-b", "ev-a"), 12001, 7000, 100, 12000, ("ev-b",), id="over-cap-then-fits"),
        pytest.param(("ev-a",), 0, 9000, 100, 12000, ("ev-a",), id="single-at-threshold"),
        pytest.param(("ev-a",), 0, 12000, 100, 12000, ("ev-a",), id="single-at-hard-cap"),
        pytest.param(("ev-a",), 0, 12001, 100, 12000, (), id="compaction-leaves-no-evidence"),
        pytest.param(("ev-a",), 0, 12001, 12001, 12000, (), id="key-content-exceeds-cap"),
        pytest.param(("ev-a", "ev-b"), 8700, 7000, 100, 8500, ("ev-a",), id="smaller-model-budget"),
        pytest.param(("ev-a",), 0, 8501, 100, 8500, (), id="single-exceeds-smaller-budget"),
    ],
)
def test_answer_compaction_and_hard_cap(
    monkeypatch, caplog, run_qual02, evaluation, selected, pair_tokens, single_tokens, key_tokens, cap, sent,
):
    run, mapping, _, case, system = run_qual02
    material = case["input"]
    source = {row["id"]: row["text"] for row in material["approved_evidence"]}
    init_adapter = b.PaperQA2Adapter.__init__
    generation_policy = b.GenerationPolicy
    counted = []
    outbound_ids = {label: label if evaluation else runtime for label, runtime in mapping.items()}
    outbound_labels = {identifier: label for label, identifier in outbound_ids.items()}

    def controlled_count(_model, text):
        assert text.startswith(system + "\n")
        payload = json.loads(text[len(system) + 1 :])
        assert payload["question"] == material["question"]
        ids = tuple(outbound_labels[row["id"]] for row in payload["approved_evidence"])
        tokens = {0: key_tokens, 1: single_tokens, 2: pair_tokens}[len(ids)]
        counted.append((ids, tokens))
        return tokens

    def init_adapter_with_offline_counter(adapter, *, answer_llm_model, **kwargs):
        monkeypatch.setattr(type(answer_llm_model), "count_tokens", controlled_count)
        init_adapter(adapter, answer_llm_model=answer_llm_model, **kwargs)

    def policy_for_window(**kwargs):
        return generation_policy(max_input_tokens=cap, compress_at_tokens=min(cap, 9000), **kwargs)

    monkeypatch.setattr(b.PaperQA2Adapter, "__init__", init_adapter_with_offline_counter)
    monkeypatch.setattr(b, "GenerationPolicy", policy_for_window)
    with caplog.at_level(logging.INFO):
        result, events = run(selected, evaluation=evaluation)
    assert result.accounting is not None
    if not sent:
        assert events == []
        assert result.status is b.GenerationStatus.REFUSED
        assert result.sent_evidence_ids == ()
        assert result.citation_aliases == ()
        assert result.accounting.answer_model_attempts == 0
        return

    assert result.status is b.GenerationStatus.SUCCESS, result.refusal_reason
    assert [kind for kind, _ in events] == (["capture", "model"] if evaluation else ["model"])
    outbound = events[-1][1]
    if evaluation:
        assert events[0][1] == outbound
    system_message, user_message = outbound
    assert system_message == ("system", system)
    assert user_message[0] == "user"
    assert json.loads(user_message[1]) == {
        "question": material["question"],
        "approved_evidence": [{"id": outbound_ids[label], "text": source[label]} for label in sent],
    }
    assert result.sent_evidence_ids == tuple(mapping[label] for label in sent)
    assert result.citation_aliases == tuple((outbound_ids[label], mapping[label]) for label in sent)
    assert result.accounting.answer_model_attempts == 1

    final_tokens = pair_tokens if len(sent) == 2 else single_tokens
    assert (sent, final_tokens) in counted
    if sent != selected:
        assert (selected, pair_tokens) in counted
        assert counted.index((selected, pair_tokens)) < counted.index((sent, final_tokens))
    if final_tokens >= min(cap, 9000):
        assert any(
            getattr(record, "event", None) == "answer_compaction_floor"
            and getattr(record, "input_tokens", None) == final_tokens
            and getattr(record, "input_cap", None) == cap
            for record in caplog.records
        ), "A request remaining at or above the compaction threshold needs a budget record"
