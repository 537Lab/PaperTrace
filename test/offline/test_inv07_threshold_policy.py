"""Verify the INV-07 soft threshold ceiling at both B gateway entry modes."""

from pathlib import Path
from runpy import run_path

import pytest

from papertrace.retrieval import gateway as b

pytestmark = pytest.mark.enable_socket
run_qual02 = run_path(str(Path(__file__).with_name("test_b_evaluation_boundary.py")))["run_qual02"]


@pytest.mark.parametrize("evaluation", [False, True], ids=["product", "fixed-id"])
@pytest.mark.parametrize(
    ("cap", "threshold", "refused"),
    [
        pytest.param(12000, 9000, False, id="global-ceiling"),
        pytest.param(12000, 9001, True, id="over-global-ceiling"),
        pytest.param(8500, 8500, False, id="smaller-cap"),
        pytest.param(8500, 8501, True, id="over-smaller-cap"),
    ],
)
def test_threshold_configuration_is_bounded(monkeypatch, run_qual02, evaluation, cap, threshold, refused):
    run, mapping, _, _, _ = run_qual02
    generation_policy = b.GenerationPolicy

    def configured_policy(**kwargs):
        return generation_policy(max_input_tokens=cap, compress_at_tokens=threshold, **kwargs)

    monkeypatch.setattr(b, "GenerationPolicy", configured_policy)
    result, events = run(evaluation=evaluation)
    assert result.accounting is not None
    if refused:
        assert result.status is b.GenerationStatus.REFUSED
        assert result.refusal_reason == "INVALID_BUDGET"
        assert result.accounting.answer_model_attempts == 0
        assert result.sent_evidence_ids == ()
        assert result.citation_aliases == ()
        assert events == []
        return

    assert result.status is b.GenerationStatus.SUCCESS
    assert result.accounting.answer_model_attempts == 1
    assert result.sent_evidence_ids == (mapping["ev-a"], mapping["ev-b"])
    assert [event for event, _ in events] == (["capture", "model"] if evaluation else ["model"])
