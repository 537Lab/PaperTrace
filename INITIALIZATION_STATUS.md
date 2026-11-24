# PaperTrace Development Readiness Status (2026-11-14 engineering unblock)

**Conclusion: work may start with conditions.** A–E can progress requirements/Plan/test preparation/fake modules independently; real non-implementer test approval is required before any business implementation. The full upstream regression, real model quality, student adoption, and remote protection have not been faked as complete. The production business/full Streamlit application is not yet implemented.

This round created `fix/development-unblock` from `e6ab25299a9b962099bd22edeba2dd745428b39d`, retaining upstream `c692d0dfeac4a0296599f7fe21a253a58b7ac12a` and the original history, with no difference in the tracked bytes of the core/packages/original tests/pyproject/uv.lock/LICENSE. The latest hash of the fix branch/PR is authoritative on GitHub; no circular SHA is fabricated in the file.

## Actual verification and boundaries

| Scope | Actual result | Not to be claimed from it |
|---|---|---|
| All team offline tests | **332 passed, 0 skipped**; the previous round's 299 items are retained, and this round adds 33 PR/main event and approval-replay checks | Not a full upstream/API/real-model pass |
| OpenCode v2.0.12 | The real loopback fake + tool-loop 2 cases pass: Plan write denied, test-preparation-only RED, own source write succeeds after a simulated review, cross-module write denied, Verify GREEN | A simulated review is not student approval, D5 contribution, or real model quality |
| Static/schema/disclosure | This round's real static, schema, and ai-log checks all PASS; see artifacts/verification/final-ci-events.json, the original closeout/unblock evidence is retained | Static analysis is not a supply-chain security certification |
| PaperQA2 | 83-package isolated runtime; real aadd→aget_evidence→aquery, with three sources in the same index and only 1 accepted item sent to a new session; excluded/pending items do not re-enter the prompt; with zero accepted items and documents still present, zero retrieval/model calls; 1 integration passed | embedding/summary/answer are all explicit fakes, not the formal B/D modules or a real model evaluation |
| Full upstream | The original uv.lock actually installs 261 packages, plus a separate hash lock adding pytest-socket; both base/current collect **377** nodes, 9 live items await authorization, and no prior node is lost; the default no-network run has real failures and stops at the time limit | **Full regression FAIL/not passed**; it is not downgraded to initialization, unmarked items are not deleted, and the failures are not hidden |

The raw summary of the full regression is in `artifacts/verification/unblock-full-regression.json`. The first fault, `tests/test_agents.py::test_get_directory_index`, was measured attempting an OpenAI call, which the socket guard rejected; even though it is not marked live, it was neither missed nor let through. Real API/paid/private data are not approved; this round does not lift the boundary, does not read private model keys, and does not retry paid calls. Not all failures should be attributed to this single cause; the complete API results are still missing.

### This round's wrap-up scope (continuing from 931cea6, no re-initialization)

Only the three semantic gate issues found in independent re-review are fixed: a request must correspond to the fixed question/accepted evidence body/sent IDs and a versioned system prompt; the v3 report binds the runtime lock, the configuration inputs, and the actual Python/installed versions of the same evaluator interpreter; Gate4 triggers on the configuration content and the production dependency closure, and no longer demands paid evaluation for unrelated changes such as Ruff/pytest. The B/D interface and the upstream model source remain protected by the trigger and the summary binding. The actual 83-package runtime check passes; the fixed data/thresholds, the six gates, and the A–E functional responsibilities are unchanged.

This increment fixes only the verifier/tests/contract, and the local Gate4 is NOT_REQUIRED; it does not mean the whole fix branch, future B/D business, or real quality evaluation is approved. A new report still requires real Actions artifacts, budget, and independent human review; nothing is released without valid real evidence.

## True status of the six gate categories

1. **test-approval: the verifier is implemented, currently BLOCKED**, with no real student pre-approval; synthetic API positive/negative cases are not approval.
2. **static: local PASS**, including the actual OpenCode configuration and the exact lock/pinned-byte checks; it exempts only Git-ignored standard SCM/egg-info build metadata, and any newly added upstream source still FAILs.
3. **schema: validation runs locally**, the 27 registry entries are not redefined and no business implementation is implied.
4. **semantic: the verifier is implemented; applicable changes are BLOCKED without a real artifact/approval/score**. The fixed 4 safety + 6 quality × 3 = 18 real quality calls and the original thresholds are unchanged; the report binds the real GitHub run/artifact/digest/current head/review, and ordinary documentation/coding-assistant rules are not given a fake evaluation. The business evaluator is reviewed separately by B/D after the interface is implemented and then lands in base; this round does not write it ahead of time.
5. **regression: actually full FAIL** (upstream no-network failures/time limit, and live awaiting authorization); the team's 332 + runtime 1 passing cannot replace full.
6. **ai-log: verified against the real newly added disclosure**; the Hermes engineering fixes and the student's formal OpenCode process are kept separate.

### Final event acceptance (continuing from 552d918)

The old problem of a push having no PR number has been reproduced through a minimal real code path. PRs still use base to verify an open PR; a main push checks the single native merged PR, the before/base/merge SHA/same tree, and then replays the test approval and applicable semantic evidence, while the other quality checks inspect the new main directly. Withdrawn approval, unapproved tests, a wrong source/event, and a direct push with no PR are all rejected; the same question is not turned into an unconditional skip. A test proposal may be closed only after the implementation merges, without breaking legitimate traceability. The real bash selector and CLI path also have offline positive/negative verification. The current 332 offline tests, Ruff/mypy, and PaperQA2 smoke 1 all pass; this is not CI verification after a merge on the real main (this round does not merge).

The first adoption is a [limited, one-time human review action](docs/ci/minimal-gates.md#one-time-first-adoption-of-pr-1-bootstrap), and no new approval service/switch is added. PR #1 still awaits a real person, and candidate self-certification or an AI re-check is not passed off as human review; if the course does not allow a shared engineering project/known failing baseline, do not merge on your own. After members are invited they can claim/Plan/prepare tests, and formal business implementation still follows the real approval order; initialization infrastructure is not expanded further.

## Remote side and first adoption

Private repository protection API 403; the visible CI is not enforced required checks. Keep it private, do not upgrade the plan, do not make it public, and do not change main's history. A PR takes the candidate from the target and the control program from the exact base; a main push uses the already-merged control program and traces the actual merged PR, with the token used only in metadata steps; when the first fix base still has the old verifier, `BASE_VERIFIER_UPGRADE_REQUIRED` is explicit, a real person reviews and adopts it, and no prior approval is back-dated. The macOS native-tool regression consumes the existing Actions quota; no new paid plan is opened. The actual remote run must be read back from PR checks; a historical first run cannot stand in for this round's result.

## What the student themself must still complete

- The five members claim features and approve and understand the architecture/shared contracts/this round's proposal; plans are approved by the supervising student, and a non-implementer approves the specific test version before implementation.
- Supervise OpenCode yourself and keep the real complete sessions and interventions; do not pass this round's fake session or the Hermes initialization off as D5/individual contribution.
- Real model/provider/data/budget authorization, fixed-set evaluation, and independent scoring; the real results of the full prior/API regression.
- GitHub accounts/invitations, eligibility and protection read-back/control PRs; confirm with the instructor the D5 five-annotated vs. one raw/from-scratch interpretation, the baseline reuse, and the exact DDL.
- The formal D1–D9 deliverables, D6 identity/relative contribution averaging 1.0/genuine reflection, and the 10-minute demo separate from the ZIP. None of these is filled in or marked complete on the student's behalf.

Enter from [TEAM_START_HERE.md](TEAM_START_HERE.md); the only command reference is [startup](docs/team/startup.md). There is no requirement to "wait until all five modules are implemented before developing"; but this round is not unconditionally mergeable, releasable, or the final course submission.
