"""Synthetic Actions payloads and Git histories; never actual student approval."""

import importlib.util
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]


def load(name):
    spec = importlib.util.spec_from_file_location(
        f"papertrace_event_test_{name}", ROOT / f"scripts/{name}.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_current_push_route_has_a_pr_context_instead_of_missing_number(monkeypatch):
    """Reproduce the old real workflow -> metadata verifier path, with no network."""
    monkeypatch.delenv("PAPERTRACE_PR_NUMBER", raising=False)
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
    step = next(
        step
        for step in workflow["jobs"]["test-approval"]["steps"]
        if "GITHUB_TOKEN" in step.get("env", {})
    )
    assert '--event-name "$GITHUB_EVENT_NAME"' in step["run"], (
        "push currently enters verify_test_approval without a PR number"
    )
    assert '--event-path "$GITHUB_EVENT_PATH"' in step["run"]


def test_raw_push_without_a_resolved_pr_does_not_silently_pass(monkeypatch):
    monkeypatch.delenv("PAPERTRACE_PR_NUMBER", raising=False)

    class NoPr:
        head = "a" * 40
        base = "b" * 40

        def changes(self):
            return ["src/papertrace/ui.py"]

    report = load("gate_evidence").verify_test_approval(NoPr())
    assert report["status"] == "BLOCKED"
    assert report["details"]["reason"] == "missing-pr-number"


def fixture_module(name):
    spec = importlib.util.spec_from_file_location(
        f"event_fixture_{name}", ROOT / f"test/offline/{name}.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def merged_fixture(tmp_path, open_tests=False):
    fixtures = fixture_module("test_gate_evidence")
    ctx, _, github = fixtures.approved_test_pr(tmp_path)
    if open_tests:
        test_pr = github.responses["/repos/537Lab/PaperTrace/pulls/10"]
        test_pr.update(state="open", merged=False, merged_at=None, merge_commit_sha=None)
        ctx.base = test_pr["base"]["sha"]
        ctx._changed += ["test/offline/test_widget.py", "docs/team/plan.md"]
        github.responses["/repos/537Lab/PaperTrace/pulls/20"]["base"]["sha"] = ctx.base
        github.responses["/repos/537Lab/PaperTrace/pulls/20/files?per_page=100"] = [
            {"filename": path} for path in ctx._changed
        ]
    # Real synthetic merge commit, not a made-up Git response.
    original_head = ctx.head
    fixtures.git(tmp_path, "checkout", "-qB", "main", ctx.base)
    fixtures.git(tmp_path, "merge", "--no-ff", "-qm", "synthetic human merge", original_head)
    merge = fixtures.git(tmp_path, "rev-parse", "HEAD")
    pr = github.responses["/repos/537Lab/PaperTrace/pulls/20"]
    pr.update(
        state="closed", merged=True, merged_at="2035-01-01T12:00:00Z", merge_commit_sha=merge
    )
    github.responses[f"/repos/537Lab/PaperTrace/commits/{merge}/pulls?per_page=100"] = [pr]
    gates = load("gates")
    push_ctx = gates.GateContext(
        root=tmp_path, base=ctx.base, head=merge, repository="537Lab/PaperTrace"
    )
    event = {
        "repository": {"full_name": "537Lab/PaperTrace", "default_branch": "main"},
        "ref": "refs/heads/main",
        "before": ctx.base,
        "after": merge,
        "forced": False,
        "deleted": False,
        "created": False,
    }
    return push_ctx, ctx, github, event


def test_normal_main_push_replays_genuine_test_approval_instead_of_requiring_open_pr(tmp_path):
    push_ctx, old_ctx, github, event = merged_fixture(tmp_path)
    events = load("ci_events")
    assert events.validate_event(push_ctx, "push", event) == "merged"
    replay = events.merged_context(push_ctx, github=github)
    assert replay.pr_number == 20 and replay.head == old_ctx.head and replay.base == old_ctx.base
    assert replay.merged_commit == push_ctx.head
    report = load("gate_evidence").verify_test_approval(replay, github=github)
    assert report["status"] == "PASS", report


@pytest.mark.parametrize(
    "mutation",
    [
        "no-pr",
        "not-merged",
        "wrong-merge",
        "wrong-repository",
        "wrong-base",
        "wrong-tree",
        "two-prs",
    ],
)
def test_push_cannot_authorize_a_missing_or_unreviewed_merge(tmp_path, mutation):
    push_ctx, _, github, event = merged_fixture(tmp_path)
    route = f"/repos/537Lab/PaperTrace/commits/{push_ctx.head}/pulls?per_page=100"
    pr = github.responses["/repos/537Lab/PaperTrace/pulls/20"]
    if mutation == "no-pr":
        github.responses[route] = []
    elif mutation == "not-merged":
        pr["merged"] = False
    elif mutation == "wrong-merge":
        pr["merge_commit_sha"] = "e" * 40
    elif mutation == "wrong-repository":
        pr["head"]["repo"]["full_name"] = "other/repo"
    elif mutation == "wrong-base":
        pr["base"]["sha"] = "e" * 40
    elif mutation == "wrong-tree":
        pr["head"]["sha"] = push_ctx.base
    else:
        github.responses[route] = [pr, dict(pr, number=21)]
    events = load("ci_events")
    events.validate_event(push_ctx, "push", event)
    with pytest.raises(events.EventError):
        events.merged_context(push_ctx, github=github)


@pytest.mark.parametrize(
    "mutation",
    [
        "forced",
        "deleted",
        "created",
        "tag",
        "feature-push",
        "wrong-after",
        "wrong-before",
        "bad-sha",
        "wrong-repo",
        "unknown-event",
    ],
)
def test_abnormal_events_fail_closed(tmp_path, mutation):
    ctx, _, github, event = merged_fixture(tmp_path)
    name = "push"
    if mutation in {"forced", "deleted", "created"}:
        event[mutation] = True
    elif mutation == "tag":
        event["ref"] = "refs/tags/main"
    elif mutation == "feature-push":
        event["ref"] = "refs/heads/feature-a"
    elif mutation == "wrong-after":
        event["after"] = "a" * 40
    elif mutation == "wrong-before":
        event["before"] = "b" * 40
    elif mutation == "bad-sha":
        event["after"] = ctx.head.upper()
    elif mutation == "wrong-repo":
        event["repository"]["full_name"] = "other/repo"
    else:
        name = "issue_comment"
    events = load("ci_events")
    with pytest.raises(events.EventError):
        events.validate_event(ctx, name, event)


@pytest.mark.parametrize("mutation", ["revoked", "wrong-test-sha", "unapproved-test-change"])
def test_main_push_does_not_bypass_invalidated_test_approval(tmp_path, mutation):
    push_ctx, _, github, _ = merged_fixture(tmp_path)
    prefix = "/repos/537Lab/PaperTrace"
    if mutation == "revoked":
        github.responses[f"{prefix}/pulls/10/reviews?per_page=100"][0]["state"] = "DISMISSED"
    elif mutation == "wrong-test-sha":
        github.responses[f"{prefix}/pulls/10/reviews?per_page=100"][0]["commit_id"] = "f" * 40
    else:
        github.responses[f"{prefix}/pulls/20/files?per_page=100"].append({
            "filename": "test/offline/unapproved.py"
        })
    events = load("ci_events")
    replay = events.merged_context(push_ctx, github=github)
    checked = load("gate_evidence").verify_test_approval(replay, github=github)
    assert checked["status"] == "FAIL", checked


def test_native_commit_pr_list_need_not_contain_the_detail_only_merged_flag(tmp_path):
    ctx, _, github, _ = merged_fixture(tmp_path)
    route = f"/repos/537Lab/PaperTrace/commits/{ctx.head}/pulls?per_page=100"
    record = dict(github.responses["/repos/537Lab/PaperTrace/pulls/20"])
    del record["merged"]  # Native list responses expose merged_at; detail confirms merged.
    github.responses[route] = [record]
    assert load("ci_events").merged_context(ctx, github=github).pr_number == 20


@pytest.mark.parametrize(
    ("closed_at", "expected"),
    [("2035-01-01T12:05:00Z", "PASS"), ("2026-11-13T10:06:00Z", "FAIL")],
)
def test_closing_redundant_test_proposal_only_after_implementation_merge_is_valid(
    tmp_path, closed_at, expected
):
    push_ctx, _, github, _ = merged_fixture(tmp_path, open_tests=True)
    github.responses["/repos/537Lab/PaperTrace/pulls/10"].update(
        state="closed", closed_at=closed_at
    )
    replay = load("ci_events").merged_context(push_ctx, github=github)
    checked = load("gate_evidence").verify_test_approval(replay, github=github)
    assert checked["status"] == expected, checked


def test_regular_pr_context_is_validated_not_resolved_as_a_merge(tmp_path):
    ctx, old, _, _ = merged_fixture(tmp_path)
    from dataclasses import replace

    pr_ctx = replace(ctx, head=old.head, pr_number=20)
    event = {
        "repository": {"full_name": "537Lab/PaperTrace", "default_branch": "main"},
        "pull_request": {"number": 20, "base": {"sha": old.base}, "head": {"sha": old.head}},
    }
    events = load("ci_events")
    assert events.validate_event(pr_ctx, "pull_request", event) == "pr"
    event["pull_request"]["number"] = 21
    with pytest.raises(events.EventError):
        events.validate_event(pr_ctx, "pull_request", event)


@pytest.mark.parametrize(
    ("event_name", "ref", "accepted"),
    [
        ("pull_request", "refs/pull/20/merge", True),
        ("push", "refs/heads/main", True),
        ("workflow_dispatch", "refs/heads/main", True),
        ("push", "refs/heads/feature", False),
    ],
)
def test_actual_bash_selector_uses_pr_base_but_already_adopted_main_after_merge(
    tmp_path, event_name, ref, accepted
):
    import os
    import subprocess

    ctx, original, _, _ = merged_fixture(tmp_path)
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
    selector = next(
        step["run"]
        for step in workflow["jobs"]["test-approval"]["steps"]
        if step.get("id") == "control"
    )
    # Run exactly the Actions shell, with real Git objects and no network/auth env.
    (tmp_path / "target").symlink_to(tmp_path, target_is_directory=True)
    output = tmp_path / "actions-output.txt"
    environment = {
        "PATH": os.environ["PATH"],
        "PAPERTRACE_BASE": ctx.base,
        "PAPERTRACE_HEAD": ctx.head,
        "PAPERTRACE_EVENT": event_name,
        "PAPERTRACE_REF": ref,
        "GITHUB_OUTPUT": str(output),
    }
    result = subprocess.run(
        ["bash", "-c", selector], cwd=tmp_path, env=environment, capture_output=True, timeout=10
    )
    assert (result.returncode == 0) is accepted
    if accepted:
        values = dict(line.split("=", 1) for line in output.read_text().splitlines())
        assert values["sha"] == (ctx.base if event_name == "pull_request" else ctx.head)
        assert values["base"] == original.base


def test_gates_cli_replays_merged_context_and_keeps_actual_quality_head(
    tmp_path, monkeypatch, capsys
):
    import json

    ctx, original, github, event = merged_fixture(tmp_path)
    payload = tmp_path / "event.json"
    payload.write_text(json.dumps(event))
    gates = load("gates")
    events = load("ci_events")
    transport = load("gate_evidence")
    monkeypatch.setattr(events, "_transport", lambda: github)
    real_support = gates.support_module
    monkeypatch.setattr(
        gates,
        "support_module",
        lambda name: events if name == "ci_events" else real_support(name),
    )
    observed = []
    monkeypatch.setattr(
        gates,
        "test_approval_gate",
        lambda target: transport.verify_test_approval(target, github=github),
    )
    monkeypatch.setattr(
        gates,
        "schema_gate",
        lambda target: (
            observed.append((target.base, target.head))
            or gates.result("schema", "PASS", "Synthetic wiring only")
        ),
    )
    args = [
        "--root",
        str(tmp_path),
        "--base",
        ctx.base,
        "--head",
        ctx.head,
        "--event-name",
        "push",
        "--event-path",
        str(payload),
    ]
    assert gates.main(["--gate", "test-approval", *args]) == 0
    result = json.loads(capsys.readouterr().out)["results"][0]
    assert result["status"] == "PASS" and result["details"]["reviewed_head"] == original.head
    assert gates.main(["--gate", "schema", *args]) == 0
    capsys.readouterr()
    assert observed == [(ctx.base, ctx.head)]


def test_post_merge_semantic_evidence_is_revalidated_not_skipped(tmp_path):
    from dataclasses import replace

    semantic_fixtures = fixture_module("test_semantic_evidence")
    old, github = semantic_fixtures.fixture(tmp_path)
    git = semantic_fixtures.git
    git(tmp_path, "checkout", "-qB", "main", old.base)
    git(tmp_path, "merge", "--no-ff", "-qm", "synthetic semantic merge", old.head)
    merge = git(tmp_path, "rev-parse", "HEAD").decode().strip()
    pr = github.responses["/repos/537Lab/PaperTrace/pulls/20"]
    pr.update(
        number=20,
        state="closed",
        merged=True,
        merged_at="2035-01-01T12:00:00Z",
        merge_commit_sha=merge,
    )
    pr["base"]["ref"] = "main"
    github.responses[f"/repos/537Lab/PaperTrace/commits/{merge}/pulls?per_page=100"] = [pr]
    push_ctx = load("gates").GateContext(root=tmp_path, base=old.base, head=merge)
    replay = load("ci_events").merged_context(push_ctx, github=github)
    verifier = load("semantic_evidence")
    assert verifier.verify_semantic(replay, github=github)["status"] == "PASS"
    github.report["runs"][0]["request"][1]["content"] = (
        "Changed and unauthorized real request material"
    )
    github.pack()
    assert verifier.verify_semantic(replay, github=github)["status"] == "FAIL"
    # Closing the PR is not itself sufficient permission to replay an unbound head.
    assert (
        verifier.verify_semantic(replace(replay, merged_commit=None), github=github)["status"]
        == "FAIL"
    )
