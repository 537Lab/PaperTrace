"""Synthetic GitHub transport fixtures only; never real student approvals."""

import importlib.util
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def gate_module():
    path = ROOT / "scripts/gate_evidence.py"
    spec = importlib.util.spec_from_file_location("papertrace_gate_evidence", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Context:
    root = ROOT
    base = "b" * 40
    head = "c" * 40

    def __init__(self, changed):
        self._changed = changed

    def changes(self):
        return list(self._changed)


class GitContext:
    def __init__(self, root, base, head, changed):
        self.root = root
        self.base = base
        self.head = head
        self._changed = changed

    def changes(self):
        return list(self._changed)

    def git(self, *args):
        completed = subprocess.run(
            ["git", "-C", str(self.root), *args], capture_output=True,
            check=True, timeout=10,
        )
        return completed.stdout


class SyntheticGitHub:
    """Fixture transport; responses are not actual GitHub evidence."""

    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def get(self, route):
        self.calls.append(route)
        if route not in self.responses:
            raise AssertionError(f"unexpected synthetic endpoint: {route}")
        value = self.responses[route]
        return value() if callable(value) else value


def git(root, *args):
    return subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True,
        check=True, timeout=10,
    ).stdout.strip()


def put(root, relative, text):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def approved_test_pr(tmp_path, implementation_path="src/papertrace/ui.py"):
    """Build a synthetic, two-PR history with independent API fixtures."""
    root = tmp_path
    git(root, "init", "-q")
    git(root, "config", "user.name", "Synthetic fixture")
    git(root, "config", "user.email", "fixture@example.invalid")
    put(root, "README.md", "synthetic baseline\n")
    put(root, "docs/architecture/adr/001-architecture.md", "Synthetic existing architecture decision; not human approval.\n")
    put(root, "scripts/gate_evidence.py", (ROOT / "scripts/gate_evidence.py").read_text())
    git(root, "add", ".")
    git(root, "commit", "-qm", "synthetic baseline")
    old_base = git(root, "rev-parse", "HEAD")
    put(root, "test/offline/test_widget.py", "def test_widget():\n    assert True\n")
    put(root, "docs/team/plan.md", "Synthetic test plan; not student approval.\n")
    git(root, "add", ".")
    git(root, "commit", "-qm", "synthetic tests only")
    test_head = git(root, "rev-parse", "HEAD")
    put(root, implementation_path, "VALUE = 'synthetic implementation'\n")
    git(root, "add", ".")
    git(root, "commit", "-qm", "synthetic implementation")
    head = git(root, "rev-parse", "HEAD")
    ctx = GitContext(root, test_head, head, [implementation_path])
    test_pr = {
        "number": 10, "state": "closed", "merged": True,
        "created_at": "2026-11-13T09:50:00Z",
        "merged_at": "2026-11-13T10:05:00Z", "merge_commit_sha": test_head,
        "user": {"login": "implementer"}, "body": "test-only synthetic PR",
        "base": {"ref": "main", "sha": old_base,
                 "repo": {"full_name": "537Lab/PaperTrace"}},
        "head": {"sha": test_head, "repo": {"full_name": "537Lab/PaperTrace"}},
    }
    implementation_pr = {
        "number": 20, "state": "open", "merged": False,
        "created_at": "2026-11-13T10:10:00Z", "merged_at": None,
        "merge_commit_sha": None, "user": {"login": "implementer"},
        "body": "Test approval PR: #10",
        "base": {"ref": "main", "sha": test_head,
                 "repo": {"full_name": "537Lab/PaperTrace"}},
        "head": {"sha": head, "repo": {"full_name": "537Lab/PaperTrace"}},
    }
    review = {
        "id": 101, "state": "APPROVED", "submitted_at": "2026-11-13T10:00:00Z",
        "commit_id": test_head, "user": {"login": "independent-student"},
    }
    prefix = "/repos/537Lab/PaperTrace"
    responses = {
        f"{prefix}/pulls/20": implementation_pr,
        f"{prefix}/pulls/20/files?per_page=100": [{"filename": implementation_path}],
        f"{prefix}/pulls/10": test_pr,
        f"{prefix}/pulls/10/files?per_page=100": [
            {"filename": "test/offline/test_widget.py"},
            {"filename": "docs/team/plan.md"},
        ],
        f"{prefix}/pulls/10/reviews?per_page=100": [review],
        f"{prefix}/issues/10/events?per_page=100": [],
        f"{prefix}/collaborators/independent-student/permission": {"permission": "write"},
        f"{prefix}/pulls/20/commits?per_page=100": lambda: [
            {"sha": sha, "author": {"login": "implementer"}, "committer": {"login": "implementer"},
             "commit": {"committer": {"date": git(root, "show", "-s", "--format=%cI", sha)}}}
            for sha in git(root, "rev-list", f"{ctx.base}..{ctx.head}").splitlines()
        ],
    }
    return ctx, test_head, SyntheticGitHub(responses)


def test_live_github_transport_is_get_only_and_does_not_forward_unrelated_credentials(monkeypatch):
    """SEC-01: a stub process tests transport arguments, not real API evidence."""
    from types import SimpleNamespace
    target = gate_module()
    monkeypatch.setenv("GITHUB_TOKEN", "dummy-test")
    monkeypatch.setenv("UNRELATED_PRIVATE_SENTINEL", "must-not-leave-parent")
    calls = []
    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        assert "UNRELATED_PRIVATE_SENTINEL" not in kwargs["env"]
        return SimpleNamespace(returncode=0, stdout=b'{"number":20}')
    monkeypatch.setattr(target.subprocess, "run", fake_run)
    assert target._LiveGitHub().get("/repos/537Lab/PaperTrace/pulls/20") == {"number": 20}
    assert "GET" in calls[0][0]
    expected = "dummy-test"  # Synthetic transport sentinel, never a saved credential.
    assert calls[0][1]["env"]["GH_TOKEN"] == expected


def test_live_artifact_transport_can_read_actual_zip_bytes_via_get(monkeypatch):
    """GOV-02: production can download artifacts instead of a permanent placeholder."""
    from types import SimpleNamespace
    target = gate_module()
    calls = []
    def fake_run(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=0, stdout=b"synthetic-zip-transport-fixture")
    monkeypatch.setattr(target.subprocess, "run", fake_run)
    assert target._LiveGitHub().download_artifact(501) == b"synthetic-zip-transport-fixture"
    assert calls[0][-1] == "/repos/537Lab/PaperTrace/actions/artifacts/501/zip"
    assert "GET" in calls[0]


def test_docs_only_changes_do_not_require_test_approval():
    report = gate_module().verify_test_approval(Context(["docs/readme.md"]))
    assert report["gate"] == "test-approval"
    assert report["status"] == "NOT_REQUIRED"


def test_code_change_without_pr_number_is_blocked():
    report = gate_module().verify_test_approval(Context(["src/papertrace/module.py"]))
    assert report["status"] == "BLOCKED"
    assert report["details"]["reason"] == "missing-pr-number"


def test_missing_live_github_evidence_still_blocks_without_a_custom_allowlist(monkeypatch):
    class NoNetwork:
        def get(self, route):
            raise AssertionError(f"unexpected API request: {route}")

    monkeypatch.delenv("PAPERTRACE_TRUSTED_TEST_APPROVERS", raising=False)
    report = gate_module().verify_test_approval(
        Context(["src/papertrace/module.py"]), github=NoNetwork(), pr_number=42,
    )
    assert report["status"] == "BLOCKED"
    assert report["details"]["reason"] == "github-api-unavailable"


def test_gate_self_modification_cannot_self_certify(monkeypatch):
    class NoNetwork:
        def get(self, route):
            raise AssertionError(f"unexpected API request: {route}")

    monkeypatch.setenv("PAPERTRACE_TRUSTED_TEST_APPROVERS", "independent-student")
    report = gate_module().verify_test_approval(
        Context(["scripts/gate_evidence.py"]), github=NoNetwork(), pr_number=42,
    )
    assert report["status"] == "BLOCKED"
    assert report["details"]["reason"] == "protected-gate-changed"


def test_optional_reviewer_allowlist_does_not_block_real_write_collaborators(monkeypatch, tmp_path):
    """GOV-01: native GitHub permissions suffice; no custom membership platform."""
    ctx, _, github = approved_test_pr(tmp_path)
    monkeypatch.delenv("PAPERTRACE_TRUSTED_TEST_APPROVERS", raising=False)
    report = gate_module().verify_test_approval(ctx, github=github, pr_number=20)
    assert report["status"] == "PASS"


def test_approved_open_test_plan_pr_can_precede_the_implementation_without_merging_red_tests(monkeypatch, tmp_path):
    """GOV-01: test proposals may be RED; only the implementation PR is merged."""
    ctx, _, github = approved_test_pr(tmp_path)
    prefix = "/repos/537Lab/PaperTrace"
    test_pr = github.responses[f"{prefix}/pulls/10"]
    test_pr.update(state="open", merged=False, merged_at=None, merge_commit_sha=None)
    ctx.base = test_pr["base"]["sha"]
    ctx._changed += ["test/offline/test_widget.py", "docs/team/plan.md"]
    current = github.responses[f"{prefix}/pulls/20"]
    current["base"]["sha"] = ctx.base
    github.responses[f"{prefix}/pulls/20/files?per_page=100"] = [{"filename": path} for path in ctx._changed]
    monkeypatch.setenv("PAPERTRACE_TRUSTED_TEST_APPROVERS", "independent-student")
    assert gate_module().verify_test_approval(ctx, github=github, pr_number=20)["status"] == "PASS"


def test_comment_does_not_automatically_revoke_an_existing_approve(monkeypatch, tmp_path):
    """GOV-01: a GitHub COMMENTED review is not CHANGES_REQUESTED or dismissal."""
    ctx, test_head, github = approved_test_pr(tmp_path)
    route = "/repos/537Lab/PaperTrace/pulls/10/reviews?per_page=100"
    github.responses[route].append({"id": 102, "state": "COMMENTED", "submitted_at": "2026-11-13T10:04:00Z", "commit_id": test_head, "user": {"login": "independent-student"}})
    monkeypatch.setenv("PAPERTRACE_TRUSTED_TEST_APPROVERS", "independent-student")
    assert gate_module().verify_test_approval(ctx, github=github, pr_number=20)["status"] == "PASS"


def test_unrelated_prior_tests_from_other_members_do_not_invalidate_scoped_approval(monkeypatch, tmp_path):
    """GOV-01: bind approved test blobs, not the entire five-person test tree."""
    ctx, test_head, github = approved_test_pr(tmp_path)
    git(tmp_path, "checkout", "-qB", "synthetic-updated-base", test_head)
    put(tmp_path, "test/offline/test_other_module.py", "def test_other():\n    assert True\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "synthetic other member's approved prior tests")
    ctx.base = git(tmp_path, "rev-parse", "HEAD")
    put(tmp_path, "src/papertrace/ui.py", "VALUE = 'synthetic implementation'\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "synthetic implementation on updated base")
    ctx.head = git(tmp_path, "rev-parse", "HEAD")
    pr = github.responses["/repos/537Lab/PaperTrace/pulls/20"]
    pr["base"]["sha"], pr["head"]["sha"] = ctx.base, ctx.head
    monkeypatch.setenv("PAPERTRACE_TRUSTED_TEST_APPROVERS", "independent-student")
    assert gate_module().verify_test_approval(ctx, github=github, pr_number=20)["status"] == "PASS"


def with_safety_review(ctx, github):
    prefix = "/repos/537Lab/PaperTrace"
    current = github.responses[f"{prefix}/pulls/20"]
    current["body"] += "\nArchitecture decision: docs/architecture/adr/001-architecture.md"
    github.responses[f"{prefix}/pulls/20/reviews?per_page=100"] = [{
        "id": 201, "state": "APPROVED", "submitted_at": "2026-11-15T10:15:00Z",
        "commit_id": ctx.head, "user": {"login": "independent-student", "type": "User"},
    }]
    github.responses[f"{prefix}/issues/20/events?per_page=100"] = []


def test_safety_critical_changes_need_an_adr_and_current_head_human_review(monkeypatch, tmp_path):
    """GOV-02: tests approved before coding do not replace safety-path PR review."""
    ctx, _, github = approved_test_pr(tmp_path, "src/papertrace/answer/service.py")
    monkeypatch.delenv("PAPERTRACE_TRUSTED_TEST_APPROVERS", raising=False)
    assert gate_module().verify_test_approval(ctx, github=github, pr_number=20)["status"] == "BLOCKED"
    with_safety_review(ctx, github)
    assert gate_module().verify_test_approval(ctx, github=github, pr_number=20)["status"] == "PASS"


def test_trusted_base_can_review_a_legitimate_gate_change_without_permanent_block(tmp_path, monkeypatch):
    """GOV-02: self-owned verifier is rejected; unchanged base verifier can judge a patch."""
    ctx, _, github = approved_test_pr(tmp_path, "scripts/gates.py")
    with_safety_review(ctx, github)
    monkeypatch.delenv("PAPERTRACE_TRUSTED_TEST_APPROVERS", raising=False)
    report = gate_module().verify_test_approval(ctx, github=github, pr_number=20)
    assert report["status"] == "PASS"
    assert report["details"]["safety_review_id"] == 201


def test_merged_test_pr_review_precedes_implementation_pr_creation(monkeypatch, tmp_path):
    ctx, test_head, github = approved_test_pr(tmp_path)
    monkeypatch.setenv("PAPERTRACE_TRUSTED_TEST_APPROVERS", "independent-student")
    report = gate_module().verify_test_approval(ctx, github=github, pr_number=20)
    assert report["status"] == "PASS"
    assert report["details"]["test_pr_head"] == test_head
    assert report["details"]["implementation_commits"]


@pytest.mark.parametrize("mutation", ["self-review", "wrong-approved-sha", "late-approval", "revoked", "read-only-reviewer", "wrong-repository", "bot-review"])
def test_real_approval_contradictions_fail_closed(monkeypatch, tmp_path, mutation):
    """GOV-01: negative API fixtures are synthetic fault injection, not approvals."""
    ctx, _, github = approved_test_pr(tmp_path)
    prefix = "/repos/537Lab/PaperTrace"
    review = github.responses[f"{prefix}/pulls/10/reviews?per_page=100"][0]
    if mutation == "self-review":
        review["user"]["login"] = "implementer"
    elif mutation == "wrong-approved-sha":
        review["commit_id"] = "f" * 40
    elif mutation == "late-approval":
        review["submitted_at"] = "2026-11-13T10:06:00Z"
    elif mutation == "revoked":
        review["state"] = "DISMISSED"
    elif mutation == "read-only-reviewer":
        github.responses[f"{prefix}/collaborators/independent-student/permission"] = {"permission": "read"}
    elif mutation == "wrong-repository":
        github.responses[f"{prefix}/pulls/10"]["head"]["repo"]["full_name"] = "other/repository"
    else:
        review["user"]["type"] = "Bot"
    monkeypatch.setenv("PAPERTRACE_TRUSTED_TEST_APPROVERS", "independent-student")
    assert gate_module().verify_test_approval(ctx, github=github, pr_number=20)["status"] == "FAIL"
