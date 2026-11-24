# Six gate categories: execution entry points and real boundaries

Basis: this semester's Project Requirement Sheet p10; p6 D4 requires complete prior tests. The implementation is `scripts/gates.py`; details are in [test approval](test-approval.md), [real semantic evaluation](../../test/evaluation/README.md), and [full regression](full-regression.md) respectively.

| Gate | Executable logic | Must not be misread |
|---|---|---|
| test-approval | Native GitHub test proposal/implementation PR, independent review, SHA/blobs, server timing, security ADR/human review | Still BLOCKED without real student approval |
| static | Ruff/mypy, dependency lock closure, pinned upstream, AST/API contracts, sensitive heuristics, actual OpenCode configuration | Static PASS is not a security certification or a runtime sandbox |
| schema | Actual JSON Schema, unique IDs, invariant ==0, locatable sources, external refs forbidden | Does not prove that business fit criteria are implemented |
| semantic | Product AI diff triggers, GitHub artifact and real authorization/per-case scoring/original thresholds | NOT_REQUIRED for inapplicable diffs; mocks do not prove quality |
| regression | All three sources collected/executed, base node list, live authorization, skip/xfail/xpass rejection | initialization is never full |
| ai-log | Real newly added disclosure after base; only swapping IDs / deleting old records is forbidden | Content truthfulness still requires human review |

```sh
.venv/bin/python scripts/gates.py --gate schema --base <previous full 40-char SHA>
.venv/bin/python scripts/gates.py --gate static --scope full --base <baseSHA>
.venv/bin/python scripts/gates.py --gate all --scope full --base <baseSHA> --head <headSHA> --pr-number <PR number> --runtime-python <runtime interpreter> --upstream-python <upstream interpreter>
```
Placeholders must be replaced. When `--head` is omitted, the actual worktree is checked; when it is provided, the executed input must match that head. When base is not an ancestor, an explicit BLOCKED message says to sync the branch; local module development need not stop because of it. Exit codes: 0 = every gate in the selected scope PASS or confirmed inapplicable; 1 = FAIL; 2 = evidence/authorization/environment BLOCKED. `all` is no longer hardcoded to always fail, and it does not erase any unmet item.

## CI trust and first adoption

Six stable jobs validate the candidate `target` from the exact base checkout `.control` at the PR/review stage; main push and manual main re-checks use the control program already merged into main, and the metadata gates first restore the original PR's base/head from the real merge record and re-verify the original approval. A direct push or a missing source does not pass on that account, and static/Schema/regression/disclosure actually check the new main. The GitHub read-only token enters only the metadata verification step; target tests are never run with the token; pull_request_target is not used. PR/review and main push trigger checks; feature-branch pushes no longer run redundantly with the PR. Regression runs the real OpenCode sandbox tests on a macOS runner with the verified-existing `@opencode/cli@2.0.12`; it consumes the existing Actions quota and does not enable a new plan or auto-purchase credits. The socket guard of the target tests is not OS isolation.

The workflow itself can still be modified by a PR, so reading the base script back cannot be presented as unbypassable protection. Private-repository branch protection currently returns API 403, and visible red/green in Actions does not mean required checks are in effect. The simplest route is manual independent PR review; enable, read back, and validate protection with real violating/legitimate control cases only after students/teachers themselves verify the Education Pro/Team entitlements.

The base of the first fix PR is still the old verifier, so the new code cannot approve itself; the genuinely missing prior approval / model evidence / complete upstream results are all retained. Future PRs are validated by this base verifier only after a real person has reviewed and adopted it. No retroactive approval is fabricated; this round's agent does not merge main. For the real person's limited checks, Approve, and the first merge steps, see [one-time adoption](minimal-gates.md#one-time-first-adoption-of-pr-1-bootstrap); do not bypass a genuine red light without a basis for course acceptance.

Current results are maintained only in [INITIALIZATION_STATUS.md](../../INITIALIZATION_STATUS.md); historical logs are kept in artifacts and are not passed off as results of this round.
