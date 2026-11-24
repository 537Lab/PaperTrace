"""GOV-02: artifact IDs are allocated after upload; fixtures never certify live calls."""

import json
from importlib import import_module
from pathlib import Path

import pytest

from test_semantic_evidence import fixture, module

ROOT = Path(__file__).resolve().parents[2]


def test_report_can_be_uploaded_before_artifact_id_exists(tmp_path):
    ctx, github = fixture(tmp_path)
    del github.report["provenance"]["artifact_id"]
    github.pack()
    checked = module().verify_semantic(ctx, github=github, pr_number=20)
    assert checked["status"] == "PASS", checked
    assert checked["details"]["artifact_id"] == 501


@pytest.mark.parametrize("fault", ("legacy-wrong-id", "legacy-null-id", "server-run", "digest"))
def test_transport_keeps_server_and_legacy_binding(tmp_path, fault):
    ctx, github = fixture(tmp_path)
    if fault == "legacy-wrong-id":
        github.report["provenance"]["artifact_id"] = 502
    elif fault == "legacy-null-id":
        github.report["provenance"]["artifact_id"] = None
    else:
        del github.report["provenance"]["artifact_id"]
    github.pack()
    server = github.responses["/repos/537Lab/PaperTrace/actions/artifacts/501"]
    if fault == "server-run":
        server["workflow_run"]["id"] = 402
    elif fault == "digest":
        server["digest"] = "sha256:" + "0" * 64
    checked = module().verify_semantic(ctx, github=github, pr_number=20)
    assert checked["status"] == "FAIL", checked


def test_prepare_fixed_requests_preserves_actual_envelopes(monkeypatch):
    # Load only the prospective evaluator, without importing any SDK or calling a model.
    monkeypatch.syspath_prepend(str(ROOT / "test/evaluation"))
    try:
        evaluator = import_module("evaluator")
    except ModuleNotFoundError as error:
        if error.name == "evaluator":
            pytest.fail("IMPLEMENTATION_MISSING: evaluator")
        raise
    dataset = json.loads((ROOT / "test/evaluation/cases.json").read_bytes())
    system_prompt = "Synthetic offline system prompt."
    rows = evaluator.prepare_requests(dataset, system_prompt)
    cases = [case for case in dataset["cases"] if case["kind"] == "real-model-quality"]
    expected = [(case, repeat) for case in cases for repeat in range(1, 4)]
    assert len(rows) == len(expected) == 18
    for row, (case, repeat) in zip(rows, expected, strict=True):
        assert row["case_id"] == case["id"]
        assert row["repeat"] == repeat
        evidence = case["input"]["approved_evidence"]
        assert row["sent_ids"] == [item["id"] for item in evidence]
        assert len(row["request"]) == 2
        assert row["request"][0] == {"role": "system", "content": system_prompt}
        assert row["request"][1]["role"] == "user"
        assert json.loads(row["request"][1]["content"]) == {
            "question": case["input"]["question"],
            "approved_evidence": evidence,
        }
