"""Live GitHub evidence verifiers for the PaperTrace blocking gates.

Production calls use read-only GitHub API requests. Injected transports are for
synthetic offline tests only.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime
from hashlib import sha1
from pathlib import Path

REPOSITORY = "537Lab/PaperTrace"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
PROTECTED_GATE_PATHS = {
    "scripts/gates.py", "scripts/gate_evidence.py", ".github/workflows/ci.yml",
    "scripts/full_regression.py", "scripts/semantic_evidence.py", "scripts/opencode_support.py", "opencode.jsonc",
    "test/offline/test_gate_evidence.py", "test/evaluation/cases.json",
    "test/evaluation/report-schema.json",
}


def _result(gate: str, status: str, summary: str, **details):
    return {"gate": gate, "status": status, "summary": summary, "details": details}


def _changed_paths(ctx):
    return sorted(set(ctx.changes()))


def _resolve_pr_number(value):
    candidate = value if value is not None else os.environ.get("PAPERTRACE_PR_NUMBER")
    if isinstance(candidate, bool):
        return None
    if isinstance(candidate, int):
        return candidate if candidate > 0 else None
    if isinstance(candidate, str) and re.fullmatch(r"[1-9][0-9]*", candidate):
        return int(candidate)
    return None


def _trusted_reviewers():
    raw = os.environ.get("PAPERTRACE_TRUSTED_TEST_APPROVERS", "")
    names = {item.strip().casefold() for item in raw.split(",") if item.strip()}
    if not names:
        return None
    if any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,37})", name) for name in names):
        raise _EvidenceInvalid("invalid-optional-reviewer-policy")
    return names


def _protected_gate_paths(paths):
    return sorted(
        path for path in paths
        if path in PROTECTED_GATE_PATHS or path.startswith(".github/workflows/")
    )


def _running_unchanged_base_verifier(ctx):
    """ADR-002: candidate self-certification is not a trusted control channel."""
    try:
        source = Path(__file__).read_bytes()
        oid = sha1(f"blob {len(source)}\0".encode() + source, usedforsecurity=False).hexdigest()
        return oid == _git_text(ctx, "rev-parse", f"{ctx.base}:scripts/gate_evidence.py")
    except (OSError, AttributeError, _EvidenceBlocked):
        return False


def _code_or_prompt(path: str) -> bool:
    value = path.lower()
    return (
        value.startswith(("src/", "packages/", "scripts/", "test/", "tests/", "prompts/", ".github/workflows/", ".github/actions/", ".opencode/"))
        or value in {
            "prompt.md", "agents.md", "opencode.jsonc", ".agent/rules.md",
            "pyproject.toml", "uv.lock", "papertrace.pytest.ini", "papertrace.ruff.toml", "mypy.ini", ".python-version",
        }
        or (value.startswith("requirements") and value.endswith((".lock", ".in")))
        or value.endswith((".py", ".js", ".ts", ".tsx", ".sh"))
    )


def verify_test_approval(ctx, github=None, pr_number=None):
    """Verify a merged, approved tests-only PR precedes the implementation PR."""
    changed = _changed_paths(ctx)
    applicable = [path for path in changed if _code_or_prompt(path)]
    if not applicable:
        return _result("test-approval", "NOT_REQUIRED", "No code or prompt changes", changed_paths=[])
    protected = _protected_gate_paths(changed)
    if protected and not _running_unchanged_base_verifier(ctx):
        return _result(
            "test-approval", "BLOCKED", "Candidate changes the gate that would judge them",
            changed_paths=applicable, protected_paths=protected,
            reason="protected-gate-changed",
        )
    number = _resolve_pr_number(pr_number)
    if number is None:
        return _result(
            "test-approval", "BLOCKED", "A live pull request number is required",
            changed_paths=applicable, reason="missing-pr-number",
        )
    try:
        if getattr(ctx, "repository", REPOSITORY) != REPOSITORY:
            raise _EvidenceInvalid("unexpected-literal-repository")
        reviewers = _trusted_reviewers()
        details = _verify_test_approval(ctx, github or _LiveGitHub(), number, changed, reviewers)
        return _result(
            "test-approval", "PASS", "Tests-only PR was independently approved before implementation PR publication",
            changed_paths=applicable, **details,
        )
    except _EvidenceBlocked as error:
        return _result(
            "test-approval", "BLOCKED", "Required live GitHub approval evidence is unavailable",
            changed_paths=applicable, pr_number=number, reason=str(error),
        )
    except _EvidenceInvalid as error:
        return _result(
            "test-approval", "FAIL", "GitHub approval evidence is contradictory or invalid",
            changed_paths=applicable, pr_number=number, reason=str(error),
        )


class _EvidenceBlocked(Exception):
    pass


class _EvidenceInvalid(Exception):
    pass


def _github_environment():
    """SEC-01: forward only approved GitHub authentication/network context."""
    allowed = {"PATH", "HOME", "XDG_CONFIG_HOME", "GH_CONFIG_DIR", "GH_TOKEN", "GITHUB_TOKEN",
               "HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY", "NO_PROXY", "https_proxy", "http_proxy", "all_proxy", "no_proxy",
               "SSL_CERT_FILE", "SSL_CERT_DIR", "LANG", "LC_ALL", "TMPDIR"}
    environment = {key: value for key, value in os.environ.items() if key in allowed}
    environment.update(GH_HOST="github.com", GH_PROMPT_DISABLED="1", GH_PAGER="cat")
    if not environment.get("GH_TOKEN") and environment.get("GITHUB_TOKEN"):
        environment["GH_TOKEN"] = environment["GITHUB_TOKEN"]
    return environment


class _LiveGitHub:
    """Read-only native gh transport; no product model credentials or API writes."""

    def _request(self, route, paginated=False):
        if not isinstance(route, str) or not route.startswith(f"/repos/{REPOSITORY}/") or ".." in route.split("/"):
            raise _EvidenceInvalid("unexpected-github-api-target")
        command = ["gh", "api", "--method", "GET", "--hostname", "github.com", "-H", "Accept: application/vnd.github+json",
                   "-H", "X-GitHub-Api-Version: 2022-11-28"]
        if paginated:
            command.extend(("--paginate", "--slurp"))
        command.append(route)
        try:
            process = subprocess.run(command, capture_output=True, timeout=60, check=False, env=_github_environment())
        except (OSError, subprocess.TimeoutExpired) as error:
            raise _EvidenceBlocked("github-api-unavailable") from error
        if process.returncode:
            raise _EvidenceBlocked("github-api-unavailable")
        if len(process.stdout) > 25_000_000:
            raise _EvidenceInvalid("github-response-too-large")
        return process.stdout

    def get(self, route):
        paginated = route.endswith("?per_page=100")
        raw = self._request(route, paginated)
        try:
            value = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise _EvidenceBlocked("github-api-invalid-response") from error
        return _flatten_pages(value) if paginated else value

    def download_artifact(self, artifact_id):
        if not isinstance(artifact_id, int) or isinstance(artifact_id, bool) or artifact_id < 1:
            raise _EvidenceInvalid("invalid-artifact-id")
        return self._request(f"/repos/{REPOSITORY}/actions/artifacts/{artifact_id}/zip")


def _flatten_pages(value):
    if not isinstance(value, list):
        return value
    flattened = []
    for item in value:
        flattened.extend(_flatten_pages(item) if isinstance(item, list) else [item])
    return flattened


def _api(client, route):
    try:
        return client.get(route)
    except (_EvidenceBlocked, _EvidenceInvalid):
        raise
    except Exception as error:
        raise _EvidenceBlocked("github-api-unavailable") from error


def _api_list(client, route, key=None):
    value = _api(client, route)
    if key is not None:
        value = value.get(key) if isinstance(value, dict) else None
    value = _flatten_pages(value)
    if not isinstance(value, list) or len(value) > 1000:
        raise _EvidenceBlocked("github-api-list-missing-or-over-limit")
    return value


def _login(record):
    user = record.get("user") if isinstance(record, dict) else None
    value = user.get("login") if isinstance(user, dict) else None
    return value.casefold() if isinstance(value, str) else None


def _repo(record):
    value = record.get("repo") if isinstance(record, dict) else None
    name = value.get("full_name") if isinstance(value, dict) else None
    return name.casefold() if isinstance(name, str) else None


def _check_pr_repositories(pr):
    base = pr.get("base")
    head = pr.get("head")
    if not isinstance(base, dict) or not isinstance(head, dict):
        raise _EvidenceInvalid("pull-request-repository-metadata-missing")
    if _repo(base) != REPOSITORY.casefold() or _repo(head) != REPOSITORY.casefold():
        raise _EvidenceInvalid("wrong-repository-or-fork")


def _parse_time(value):
    if not isinstance(value, str):
        raise _EvidenceInvalid("server-timestamp-missing")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise _EvidenceInvalid("server-timestamp-invalid") from error
    if parsed.tzinfo is None:
        raise _EvidenceInvalid("server-timestamp-must-include-timezone")
    return parsed


def _require_sha(value, reason):
    if not isinstance(value, str) or not FULL_SHA.fullmatch(value):
        raise _EvidenceInvalid(reason)
    return value


def _git_text(ctx, *args):
    try:
        return ctx.git(*args).decode("ascii").strip()
    except Exception as error:
        raise _EvidenceBlocked("required-git-object-unavailable") from error


def _is_ancestor(ctx, ancestor, descendant):
    try:
        ctx.git("merge-base", "--is-ancestor", ancestor, descendant)
    except Exception as error:
        raise _EvidenceInvalid("required-sha-is-not-an-ancestor") from error


def _github_files(client, number):
    files = _api_list(client, f"/repos/{REPOSITORY}/pulls/{number}/files?per_page=100")
    names = []
    for item in files:
        name = item.get("filename") if isinstance(item, dict) else None
        if not isinstance(name, str):
            raise _EvidenceBlocked("pull-request-file-list-incomplete")
        names.append(name)
    if len(set(names)) != len(names):
        raise _EvidenceInvalid("duplicate-pull-request-file")
    return set(names)


def _test_pr_reference(body):
    if not isinstance(body, str):
        return None
    matches = re.findall(r"(?im)^\s*Test approval PR\s*:\s*#?([1-9][0-9]*)\s*$", body)
    return int(matches[0]) if len(matches) == 1 else None


def _test_file_allowed(path):
    if path.startswith(("test/offline/", "test/integration/", "test/live/", "test/fixtures/")):
        return path.endswith(".py") or path.startswith("test/fixtures/")
    if path.startswith(("docs/team/", "docs/plans/", "docs/reviews/")):
        return path.endswith(".md")
    if path == "docs/ai-use-log.yaml":
        return True
    return False


def _select_approval(client, pr_number, target_sha, author_logins, allowlist, created_at, merged_at):
    prefix = f"/repos/{REPOSITORY}/pulls/{pr_number}"
    reviews = _api_list(client, f"{prefix}/reviews?per_page=100")
    events = _api_list(client, f"/repos/{REPOSITORY}/issues/{pr_number}/events?per_page=100")
    if not reviews:
        raise _EvidenceBlocked("independent-approve-missing")
    ordered = sorted(
        (item for item in reviews if isinstance(item, dict)),
        key=lambda item: _parse_time(item.get("submitted_at")),
    )
    latest = {}
    for review in ordered:
        login = _login(review)
        if login and review.get("state") in {"APPROVED", "CHANGES_REQUESTED", "DISMISSED"}:
            latest[login] = review
    approvals = [review for review in ordered if review.get("state") == "APPROVED"]
    if not approvals:
        if any(review.get("state") in {"DISMISSED", "CHANGES_REQUESTED"} for review in ordered):
            raise _EvidenceInvalid("approval-revoked-or-changes-requested")
        raise _EvidenceBlocked("independent-approve-missing")
    eligible = [
        review for login, review in latest.items()
        if login not in author_logins and (allowlist is None or login in allowlist)
        and review.get("state") == "APPROVED"
        and (review.get("user") or {}).get("type") != "Bot" and not login.endswith("[bot]")
    ]
    if not eligible:
        if any((review.get("user") or {}).get("type") == "Bot" or (_login(review) or "").endswith("[bot]") for review in approvals):
            raise _EvidenceInvalid("non-human-approval-rejected")
        if any(_login(review) in author_logins for review in approvals):
            raise _EvidenceInvalid("self-approval-rejected")
        if allowlist is not None and any(_login(review) not in allowlist for review in approvals):
            raise _EvidenceInvalid("reviewer-not-in-trusted-student-allowlist")
        if any(review.get("state") in {"DISMISSED", "CHANGES_REQUESTED"} for review in ordered):
            raise _EvidenceInvalid("approval-revoked-or-changes-requested")
        raise _EvidenceBlocked("no-current-independent-approve")
    review = eligible[-1]
    reviewer = _login(review)
    if review.get("commit_id") != target_sha:
        raise _EvidenceInvalid("approved-sha-does-not-match-test-pr-head")
    reviewed_at = _parse_time(review.get("submitted_at"))
    if reviewed_at < created_at:
        raise _EvidenceInvalid("approval-predates-test-pr")
    if merged_at is not None and reviewed_at >= merged_at:
        raise _EvidenceInvalid("approval-not-before-test-pr-merge")
    for event in events:
        if not isinstance(event, dict) or event.get("event") not in {"review_dismissed", "dismissed"}:
            continue
        event_time = _parse_time(event.get("created_at"))
        dismissed = event.get("dismissed_review") or event.get("review") or {}
        dismissed_login = _login(dismissed) if isinstance(dismissed, dict) else None
        if event_time >= reviewed_at and (dismissed_login in {None, reviewer}):
            raise _EvidenceInvalid("approval-dismissal-event-after-review")
    permission = _api(client, f"/repos/{REPOSITORY}/collaborators/{reviewer}/permission")
    level = permission.get("permission") if isinstance(permission, dict) else None
    if level not in {"write", "maintain", "admin"}:
        raise _EvidenceInvalid("reviewer-lacks-write-permission")
    return review, reviewed_at


def _safety_review(ctx, client, current, number, changed, participants, allowlist):
    """GOV-02: safety paths need a real current-head review and accompanying ADR."""
    safety = [path for path in changed if (
        path in {"AGENTS.md", "Prompt.md", "opencode.jsonc", "src/papertrace/contracts.py"}
        or path.startswith((".opencode/", ".agent/", ".github/workflows/", "src/paperqa/", "packages/"))
        or path in PROTECTED_GATE_PATHS
        or (path.startswith(("src/papertrace/answer/", "src/papertrace/review/", "src/papertrace/retrieval/", "src/papertrace/library/", "src/papertrace/reports/"))
            and Path(path).name not in {"view.py", "ui.py", "__init__.py"})
    )]
    if not safety:
        return {}
    matches = re.findall(r"(?im)^Architecture decision:\s*(docs/architecture/adr/[A-Za-z0-9_.-]+\.md)\s*$", current.get("body") or "")
    if len(matches) != 1 or ".." in matches[0].split("/"):
        raise _EvidenceBlocked("architecture-decision-reference-required")
    adr = matches[0]
    adr_blob = _require_sha(_git_text(ctx, "rev-parse", f"{ctx.head}:{adr}"), "architecture-decision-missing")
    review, _ = _select_approval(client, number, ctx.head, participants, allowlist,
                                 _parse_time(current.get("created_at")), None)
    return {"safety_paths": safety, "architecture_decision": adr, "architecture_decision_blob": adr_blob,
            "safety_review_id": review.get("id"), "safety_reviewer": _login(review)}


def _verify_test_approval(ctx, client, pr_number, changed, allowlist):
    if not ctx.head or not ctx.base:
        raise _EvidenceBlocked("full-base-and-head-shas-required")
    base_sha = _require_sha(ctx.base, "invalid-base-sha")
    head_sha = _require_sha(ctx.head, "invalid-head-sha")
    current = _api(client, f"/repos/{REPOSITORY}/pulls/{pr_number}")
    if not isinstance(current, dict) or current.get("number") != pr_number:
        raise _EvidenceBlocked("implementation-pull-request-not-found")
    _check_pr_repositories(current)
    if current.get("state") != "open" or current.get("merged") is True:
        raise _EvidenceInvalid("implementation-pr-is-not-open")
    if current.get("base", {}).get("sha") != base_sha or current.get("head", {}).get("sha") != head_sha:
        raise _EvidenceInvalid("local-base-or-head-does-not-match-live-pr")
    remote_changes = _github_files(client, pr_number)
    if remote_changes != set(changed):
        raise _EvidenceInvalid("local-change-set-does-not-match-live-pr-files")
    implementation_paths = {path for path in remote_changes if _code_or_prompt(path)}
    if not any(not _test_file_allowed(path) for path in implementation_paths):
        raise _EvidenceBlocked("test-proposal-only-do-not-merge-red-tests")
    test_number = _test_pr_reference(current.get("body"))
    if test_number is None or test_number == pr_number:
        raise _EvidenceBlocked("implementation-pr-must-reference-one-test-approval-pr")
    test_pr = _api(client, f"/repos/{REPOSITORY}/pulls/{test_number}")
    if not isinstance(test_pr, dict) or test_pr.get("number") != test_number:
        raise _EvidenceBlocked("referenced-test-pr-not-found")
    _check_pr_repositories(test_pr)
    merged = test_pr.get("merged") is True
    if not merged and test_pr.get("state") != "open":
        raise _EvidenceInvalid("test-proposal-was-closed-without-merge")
    test_head = _require_sha(test_pr.get("head", {}).get("sha"), "invalid-test-pr-head")
    merge_sha = _require_sha(test_pr.get("merge_commit_sha"), "test-pr-merge-sha-missing") if merged else None
    if test_pr.get("base", {}).get("ref") != current.get("base", {}).get("ref"):
        raise _EvidenceInvalid("test-pr-target-branch-differs")
    test_files = _github_files(client, test_number)
    if not test_files or any(not _test_file_allowed(path) for path in test_files):
        raise _EvidenceInvalid("test-pr-contains-non-test-or-non-plan-files")
    if not any(path.startswith("test/offline/") and path.endswith(".py") for path in test_files):
        raise _EvidenceInvalid("test-pr-does-not-contain-offline-test-code")
    if not any(path.startswith(("docs/team/", "docs/plans/")) for path in test_files) and not re.search(r"(?im)^Plan:\s*\S", test_pr.get("body") or ""):
        raise _EvidenceInvalid("test-pr-does-not-contain-execution-plan")
    test_author = _login(test_pr)
    implementation_author = _login(current)
    if not test_author or not implementation_author:
        raise _EvidenceBlocked("pull-request-author-missing")
    commits = _api_list(client, f"/repos/{REPOSITORY}/pulls/{pr_number}/commits?per_page=100")
    participants = {test_author, implementation_author}
    for commit in commits:
        for key in ("author", "committer"):
            actor = commit.get(key) or {}
            if actor.get("login") and actor.get("type") != "Bot":
                participants.add(actor["login"].casefold())
    review, approved_at = _select_approval(
        client, test_number, test_head,
        participants, allowlist,
        _parse_time(test_pr.get("created_at")), _parse_time(test_pr.get("merged_at")) if merged else None,
    )
    implementation_created = _parse_time(current.get("created_at"))
    merged_at = _parse_time(test_pr.get("merged_at")) if merged else None
    if implementation_created <= max(approved_at, merged_at or approved_at):
        raise _EvidenceInvalid("implementation-pr-first-server-observation-not-after-approval-and-merge")
    if test_pr.get("base", {}).get("ref") != current.get("base", {}).get("ref"):
        raise _EvidenceInvalid("test-pr-base-branch-mismatch")
    if merged:
        _is_ancestor(ctx, merge_sha, base_sha)
    else:
        _is_ancestor(ctx, test_head, head_sha)
    _is_ancestor(ctx, base_sha, head_sha)
    anchor = _require_sha(merge_sha if merged else test_head, "implementation-anchor-missing")
    required_commits = set(_git_text(ctx, "rev-list", head_sha, "^" + anchor, "^" + base_sha).splitlines())
    by_sha = {item.get("sha"): item for item in commits if isinstance(item, dict)}
    if not required_commits or not required_commits.issubset(by_sha):
        raise _EvidenceInvalid("implementation-commit-list-is-incomplete")
    commit_times = {}
    for sha in sorted(required_commits):
        timestamp = _parse_time(by_sha[sha].get("commit", {}).get("committer", {}).get("date"))
        if timestamp != _parse_time(_git_text(ctx, "show", "-s", "--format=%cI", sha)):
            raise _EvidenceInvalid("commit-timestamp-does-not-match-git-object")
        if timestamp < approved_at:
            raise _EvidenceInvalid("implementation-commit-predates-test-approval")
        commit_times[sha] = timestamp.isoformat()
    test_tree = _git_text(ctx, "rev-parse", f"{test_head}:test")
    if not FULL_SHA.fullmatch(test_tree):
        raise _EvidenceInvalid("approved-test-tree-is-invalid")
    changed_tests = {path for path in changed if path.startswith(("test/", "tests/"))}
    if changed_tests - test_files:
        raise _EvidenceInvalid("implementation-changes-unapproved-test-files")
    test_blobs = {}
    for path in test_files:
        if path == "docs/ai-use-log.yaml":
            continue  # Each PR appends its own disclosure, not a frozen test input.
        original = _git_text(ctx, "rev-parse", f"{test_head}:{path}")
        current_blob = _git_text(ctx, "rev-parse", f"{head_sha}:{path}")
        if original != current_blob:
            raise _EvidenceInvalid("approved-test-or-plan-file-changed-after-approval")
        test_blobs[path] = original
    safety = _safety_review(ctx, client, current, pr_number, changed, participants, allowlist)
    return {
        "pr_number": pr_number, "test_pr_number": test_number,
        "test_pr_head": test_head, "test_tree_sha": test_tree,
        "review_id": review.get("id"), "reviewer": _login(review),
        "approved_at": approved_at.isoformat(), "test_pr_merged_at": merged_at.isoformat() if merged_at else None,
        "approved_test_and_plan_blobs": test_blobs,
        "implementation_pr_created_at": implementation_created.isoformat(),
        "implementation_commits": commit_times,
        **safety,
        "ordering_evidence": "GitHub server timestamps establish PR publication order only; they cannot prove when local code was first written",
    }
