"""GOV-02: Actions event validation and replay of the exact merged PR evidence.

Main push does not invent approval or trust a check-name/green badge. It locates
one native merged PR and reuses the existing evidence validators on its head.
"""

import importlib.util
import re
from dataclasses import replace
from pathlib import Path

REPOSITORY = "537Lab/PaperTrace"
SHA = re.compile(r"[0-9a-f]{40}")


class EventError(ValueError):
    """A missing association is BLOCKED; contradictory event evidence is FAIL."""

    def __init__(self, reason, blocked=False):
        super().__init__(reason)
        self.blocked = blocked


def _sha(value):
    if not isinstance(value, str) or not SHA.fullmatch(value) or value == "0" * 40:
        raise EventError("invalid-event-sha")
    return value


def validate_event(ctx, name, event):
    """No Actions payload may silently fall back to a no-PR quality pass."""
    if not isinstance(event, dict) or event.get("repository", {}).get("full_name") != REPOSITORY or ctx.repository != REPOSITORY:
        raise EventError("wrong-event-repository")
    _sha(ctx.base)
    _sha(ctx.head)
    if name in {"pull_request", "pull_request_review"}:
        pr = event.get("pull_request", {})
        number = pr.get("number") or event.get("number")
        if isinstance(number, bool) or not isinstance(number, int) or number < 1 or number != ctx.pr_number:
            raise EventError("event-pr-number-mismatch")
        if pr.get("base", {}).get("sha") != ctx.base or pr.get("head", {}).get("sha") != ctx.head:
            raise EventError("event-pr-base-or-head-mismatch")
        return "pr"
    if name not in {"push", "workflow_dispatch"}:
        raise EventError("unsupported-ci-event")
    default = event["repository"].get("default_branch")
    if default != "main" or event.get("ref") != "refs/heads/main":
        raise EventError("post-merge-event-must-target-main")
    if name == "push":
        if any(event.get(flag) is not False for flag in ("forced", "deleted", "created")):
            raise EventError("non-regular-main-push")
        if _sha(event.get("before")) != ctx.base or _sha(event.get("after")) != ctx.head:
            raise EventError("push-before-or-after-mismatch")
    # dispatch has ref/sha supplied separately by Actions; it still needs a native
    # merged association below, so dispatch is not an escape for direct pushes.
    return "merged"


def _transport():
    spec = importlib.util.spec_from_file_location("papertrace_event_transport", Path(__file__).with_name("gate_evidence.py"))
    if spec is None or spec.loader is None:
        raise EventError("trusted-github-transport-unavailable", blocked=True)
    control = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(control)
    return control._LiveGitHub()


def merged_context(ctx, github=None):
    """Bind merged main tree to one PR; retain its original base/head for replay.

    Normal team merge method: update to latest main, review that head, then
    Create a merge commit. Squash is accepted only with identical reviewed tree.
    Merge-time conflict edits or a batch spanning other main work fail closed.
    """
    client = github or _transport()
    prefix = f"/repos/{REPOSITORY}"
    try:
        prs = client.get(f"{prefix}/commits/{ctx.head}/pulls?per_page=100")
        if not isinstance(prs, list) or len(prs) > 1000:
            raise EventError("invalid-merged-pr-association")
        matches = [pr for pr in prs if isinstance(pr, dict) and pr.get("merged_at")
                   and pr.get("state") == "closed" and pr.get("merge_commit_sha") == ctx.head]
        if len(matches) != 1:
            raise EventError("unique-merged-pr-required-for-main-push", blocked=not matches)
        number = matches[0].get("number")
        if isinstance(number, bool) or not isinstance(number, int) or number < 1:
            raise EventError("invalid-merged-pr-number")
        pr = client.get(f"{prefix}/pulls/{number}")
        if pr.get("number") != number or pr.get("merged") is not True or pr.get("state") != "closed" or pr.get("merge_commit_sha") != ctx.head or not pr.get("merged_at"):
            raise EventError("merged-pr-record-mismatch")
        base, head = pr.get("base", {}), pr.get("head", {})
        if base.get("repo", {}).get("full_name") != REPOSITORY or head.get("repo", {}).get("full_name") != REPOSITORY or base.get("ref") != "main":
            raise EventError("merged-pr-repository-or-target-mismatch")
        reviewed = _sha(head.get("sha"))
        if _sha(base.get("sha")) != ctx.base:
            raise EventError("push-range-does-not-match-reviewed-pr-base")
        ctx.git("merge-base", "--is-ancestor", ctx.base, ctx.head)
        if ctx.git("rev-parse", f"{ctx.head}^{{tree}}") != ctx.git("rev-parse", f"{reviewed}^{{tree}}"):
            raise EventError("merged-tree-differs-from-reviewed-head")
        return replace(ctx, head=reviewed, pr_number=number, merged_commit=ctx.head)
    except EventError:
        raise
    except Exception as error:
        raise EventError("merged-pr-evidence-unavailable", blocked=True) from error
