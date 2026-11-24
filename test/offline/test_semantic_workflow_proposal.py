"""Offline contract for preflight and authenticated rating intake; never model calls."""

import json
from importlib import import_module
from pathlib import Path

import pytest
import yaml
from test_semantic_evidence import fixture

ROOT = Path(__file__).resolve().parents[2]
PREFIX = "/repos/537Lab/PaperTrace"
RAW_HASH = "a" * 64


def evaluator_module(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "test/evaluation"))
    try:
        evaluator = import_module("evaluator")
    except ModuleNotFoundError as error:
        if error.name == "evaluator":
            pytest.fail("IMPLEMENTATION_MISSING: evaluator")
        raise
    assert callable(getattr(evaluator, "preflight", None)), "IMPLEMENTATION_MISSING: preflight"
    assert callable(getattr(evaluator, "accept_ratings", None)), "IMPLEMENTATION_MISSING: intake"
    return evaluator


def workflow_fixture(tmp_path):
    ctx, github = fixture(tmp_path)
    run = github.responses[f"{PREFIX}/actions/runs/401"]
    run.update(status="in_progress", conclusion=None, updated_at="2026-11-13T10:21:00Z")
    return ctx, github


def preflight(evaluator, ctx, github):
    return evaluator.preflight(
        ctx, github, pr_number=20, run_id=401, authorization_review_id=301,
    )


def test_live_preflight_requires_exact_server_context(tmp_path, monkeypatch):
    evaluator = evaluator_module(monkeypatch)
    ctx, github = workflow_fixture(tmp_path)
    approved = preflight(evaluator, ctx, github)
    assert approved["head_sha"] == ctx.head
    assert approved["authorization"] == github.report["authorization"]
    assert approved["dataset_sha256"] == github.report["target"]["dataset_sha256"]


@pytest.mark.parametrize(
    "fault",
    ("wrong-head", "wrong-event", "self-auth", "no-auth", "wrong-dataset", "read-only"),
)
def test_preflight_rejects_invalid_authorization_before_provider_stage(tmp_path, monkeypatch, fault):
    evaluator = evaluator_module(monkeypatch)
    ctx, github = workflow_fixture(tmp_path)
    run = github.responses[f"{PREFIX}/actions/runs/401"]
    reviews = github.responses[f"{PREFIX}/pulls/20/reviews?per_page=100"]
    if fault == "wrong-head":
        run["head_sha"] = "f" * 40
    elif fault == "wrong-event":
        run["event"] = "pull_request"
    elif fault == "self-auth":
        reviews[0]["user"]["login"] = "implementer"
    elif fault == "no-auth":
        reviews.pop(0)
    elif fault == "wrong-dataset":
        authorization = json.loads(reviews[0]["body"].split(": ", 1)[1])
        authorization["dataset_sha256"] = "f" * 64
        reviews[0]["body"] = "Evaluation authorization: " + json.dumps(authorization)
    elif fault == "read-only":
        github.responses[f"{PREFIX}/collaborators/independent-student/permission"] = {
            "permission": "read",
        }
    with pytest.raises(ValueError):
        preflight(evaluator, ctx, github)


def rating_fixture(tmp_path):
    ctx, github = workflow_fixture(tmp_path)
    ratings = github.report["scores"]["independent_ratings"]
    reviews = github.responses[f"{PREFIX}/pulls/20/reviews?per_page=100"]
    reviews[-1].update(
        state="COMMENTED",
        body="Semantic ratings: " + json.dumps({
            "run_id": 401, "head_sha": ctx.head, "raw_sha256": RAW_HASH, "ratings": ratings,
        }),
    )
    return ctx, github, ratings


def intake(evaluator, ctx, github):
    return evaluator.accept_ratings(
        ctx, github, pr_number=20, run_id=401, raw_sha256=RAW_HASH,
        captured_at="2026-11-13T10:25:00Z",
    )


def test_rating_intake_uses_actual_independent_review(tmp_path, monkeypatch):
    evaluator = evaluator_module(monkeypatch)
    ctx, github, ratings = rating_fixture(tmp_path)
    adopted = intake(evaluator, ctx, github)
    assert adopted["review_id"] == 302
    assert adopted["reviewer"] == "independent-student"
    assert adopted["ratings"] == ratings


@pytest.mark.parametrize("fault", ("wrong-hash", "wrong-head", "self-review", "early", "missing"))
def test_intake_rejects_invalid_or_incomplete_human_review(tmp_path, monkeypatch, fault):
    evaluator = evaluator_module(monkeypatch)
    ctx, github, _ = rating_fixture(tmp_path)
    review = github.responses[f"{PREFIX}/pulls/20/reviews?per_page=100"][-1]
    body = json.loads(review["body"].split(": ", 1)[1])
    if fault == "wrong-hash":
        body["raw_sha256"] = "b" * 64
    elif fault == "wrong-head":
        review["commit_id"] = "f" * 40
    elif fault == "self-review":
        review["user"]["login"] = "implementer"
    elif fault == "early":
        review["submitted_at"] = "2026-11-13T10:24:00Z"
    elif fault == "missing":
        body["ratings"].pop()
    review["body"] = "Semantic ratings: " + json.dumps(body)
    with pytest.raises(ValueError):
        intake(evaluator, ctx, github)


def test_evaluation_workflow_has_only_manual_dispatch_and_separate_review_stage():
    path = ROOT / ".github/workflows/semantic-evaluation.yml"
    assert path.is_file(), "IMPLEMENTATION_MISSING: evaluation workflow"
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    events = workflow.get("on", workflow.get(True))
    assert isinstance(events, dict)
    assert set(events) == {"workflow_dispatch"}
    assert set(events["workflow_dispatch"]["inputs"]) == {
        "target_pr", "target_head", "authorization_review_id",
    }
    jobs = workflow["jobs"]
    assert set(jobs) == {"preflight", "collect", "finalize"}
    assert jobs["collect"]["needs"] == "preflight"
    assert jobs["finalize"]["needs"] == "collect"
    assert jobs["collect"]["environment"] == "papertrace-evaluation-execution"
    assert jobs["finalize"]["environment"] == "papertrace-independent-rating"
    for job in jobs.values():
        for permission, value in job.get("permissions", workflow.get("permissions", {})).items():
            assert value in {"read", "none"}, permission
