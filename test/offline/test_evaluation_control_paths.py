"""GOV-01/GOV-02: exact evaluation control paths require independent review."""

import pytest
from test_gate_evidence import approved_test_pr, gate_module, git, put, with_safety_review


@pytest.mark.parametrize(
    "path", ("test/evaluation/evaluator.py", "test/evaluation/report-schema.json")
)
def test_evaluation_controls_are_implementation_not_unapproved_test_edits(tmp_path, path):
    ctx, _, github = approved_test_pr(tmp_path, path)
    without_review = gate_module().verify_test_approval(ctx, github=github, pr_number=20)
    assert without_review["status"] == "BLOCKED", without_review
    assert without_review["details"]["reason"] == "architecture-decision-reference-required"
    with_safety_review(ctx, github)
    accepted = gate_module().verify_test_approval(ctx, github=github, pr_number=20)
    assert accepted["status"] == "PASS", accepted
    assert path in accepted["details"]["safety_paths"]
    assert accepted["details"]["safety_review_id"] == 201


@pytest.mark.parametrize(
    "path",
    (
        "test/evaluation/evaluator.py",
        "test/evaluation/report-schema.json",
        "test/evaluation/cases.json",
        "test/evaluation/other.py",
    ),
)
def test_controls_or_dataset_cannot_be_smuggled_into_tests_only_proposal(tmp_path, path):
    ctx, _, github = approved_test_pr(tmp_path)
    route = "/repos/537Lab/PaperTrace/pulls/10/files?per_page=100"
    github.responses[route].append({"filename": path})
    result = gate_module().verify_test_approval(ctx, github=github, pr_number=20)
    assert result["status"] == "FAIL", result
    assert result["details"]["reason"] == "test-pr-contains-non-test-or-non-plan-files"


@pytest.mark.parametrize(
    "path", ("test/offline/unapproved.py", "test/evaluation/other.py", "test/evaluation/cases.json")
)
def test_other_test_edits_remain_disallowed_with_implementation(tmp_path, path):
    ctx, _, github = approved_test_pr(tmp_path)
    put(tmp_path, path, "unapproved synthetic fixture")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "unapproved extra change")
    ctx.head = git(tmp_path, "rev-parse", "HEAD")
    ctx._changed.append(path)
    prefix = "/repos/537Lab/PaperTrace/pulls/20"
    github.responses[prefix]["head"]["sha"] = ctx.head
    github.responses[f"{prefix}/files?per_page=100"] = [
        {"filename": name} for name in ctx._changed
    ]
    with_safety_review(ctx, github)
    result = gate_module().verify_test_approval(ctx, github=github, pr_number=20)
    assert result["status"] == "FAIL", result
    assert result["details"]["reason"] == "implementation-changes-unapproved-test-files"
