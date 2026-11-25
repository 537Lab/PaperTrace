"""GOV-02: artifact IDs are allocated after upload; fixtures never certify live calls."""

import json
from hashlib import sha256
from importlib import import_module
from pathlib import Path

import pytest
from test_semantic_evidence import canonical, fixture, module

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


@pytest.mark.parametrize(
    ("fault", "status", "reason"),
    [
        ("quality", "FAIL", "frozen-quality-threshold-failed"),
        ("rating", "FAIL", "invalid-item-rating-counts-or-rationale"),
        ("request", "FAIL", "request-question-evidence-or-sent-ids-mismatch"),
        ("excluded", "FAIL", "request-question-evidence-or-sent-ids-mismatch"),
        ("missing-auth", "BLOCKED", "real-budget-authorization-review-missing"),
        ("wrong-auth", "FAIL", "budget-authorization-not-independent-current-head-approve"),
        ("review-hash", "FAIL", "independent-post-run-report-review-missing-or-wrong-hash"),
        ("runtime", "FAIL", "runtime-installed-versions-do-not-match-lock"),
        ("attempts", "FAIL", "incomplete-fixed-set-or-budget-exceeded"),
        ("cost", "FAIL", "incomplete-fixed-set-or-budget-exceeded"),
        ("timeout", "FAIL", "call-time-outside-authorization-run-or-deadline"),
    ],
)
def test_omitted_id_does_not_weaken_original_validation(tmp_path, fault, status, reason):
    """Each synthetic mutation must reach its specific invariant, not fail at schema."""
    ctx, github = fixture(tmp_path)
    report = github.report
    del report["provenance"]["artifact_id"]
    github.pack()
    baseline = module().verify_semantic(ctx, github=github, pr_number=20)
    # Keep the negative controls independent of the RED positive node:
    # the new transport is required to reach the real common validation path.
    assert baseline["status"] == "PASS", baseline
    ratings = report["scores"]["independent_ratings"]
    reviews = github.responses["/repos/537Lab/PaperTrace/pulls/20/reviews?per_page=100"]
    first = report["runs"][0]
    if fault == "quality":
        ratings[0]["correct_citations"] = 0
        report["scores"]["citation_precision"] = sum(
            row["correct_citations"] for row in ratings
        ) / sum(row["citation_count"] for row in ratings)
    elif fault == "rating":
        ratings[0]["rationale"] = " "
    elif fault in {"request", "excluded"}:
        payload = json.loads(first["request"][1]["content"])
        if fault == "request":
            payload["approved_evidence"][0]["text"] = "Substituted synthetic material."
        else:
            payload["approved_evidence"].append({"id": "ev-unapproved", "text": "Excluded material."})
        first["request"][1]["content"] = json.dumps(payload, ensure_ascii=False)
        first["prompt_sha256"] = sha256(canonical(first["request"])).hexdigest()
    elif fault == "missing-auth":
        reviews.pop(0)
    elif fault == "wrong-auth":
        reviews[0]["commit_id"] = "f" * 40
    elif fault == "runtime":
        report["runtime_environment"]["packages"]["litellm"] = "0.0.1"
    elif fault == "attempts":
        first["attempts"] += 1
    elif fault == "cost":
        first["cost"] = report["authorization"]["max_cost"] + 1
    elif fault == "timeout":
        first["finished_at"] = "2026-11-13T10:22:00Z"
    github.pack()
    if fault == "review-hash":
        reviews[-1]["body"] = "Semantic report SHA256: " + "0" * 64
    checked = module().verify_semantic(ctx, github=github, pr_number=20)
    assert checked["status"] == status, checked
    assert checked["details"]["reason"] == reason, checked
