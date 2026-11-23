# Module D — C→D review-projection read adapter: implementation record (2026-11-23)

| Item | Value |
|---|---|
| Date | 2026-11-23 (HKT) |
| Stage | Approved source implementation, local only; no commit, push or PR action |
| Module | D `answer`, slice 1 |
| New files | `src/papertrace/answer/c_adapter.py`; this record |
| Approved test base | PR #20 head `f26e4fc2768de44da556b204295c2dfa2b94f10c` |
| Independent test approval | 537Lab APPROVED review `6013460068` at `2026-11-22T17:16:18Z` on that exact commit; PR #20 remains open and unmerged |
| Historical source dependency | PR #19 head `3d536aa2382f3c4b803dd2b7caf0dd1fe95aed82`, independent approvals `6012760488` / `6012764069` by ziqilin669; PR #19 remains Draft, open and unmerged |
| Scope | Read-only C projection adapter for D's existing port; no generation, release, retry or concurrency work |

The approvals above cover the exact test commit and the earlier historical source
snapshot only. They do not approve this implementation, full CI or any merge; an
independent review of the exact implementation head is still required.

## 1. Authority and preserved setup

The supervising side authorized exactly two writable paths for this stage:
`src/papertrace/answer/c_adapter.py` and this record. Every other path was
read-only, including all existing source, tests, fixtures, approved plans,
contracts, ADRs, AI-use log, CI/gates and dependency/permission files. The
session did not stage, commit, push, switch/rebase, open or review a PR, or
change permissions.

At session start the checkout was on branch `codex/d-c-adapter` at HEAD
`f26e4fc2768de44da556b204295c2dfa2b94f10c`, i.e. the approved PR #20 test head.
The prepared tree also contained the supervisor-only local setup changes
(`opencode.jsonc`, `.opencode/permissions.jsonc`) and untracked restored answer
sources; these were preserved as found. All nine cumulative PR #20 paths and
their approved tests, fixtures, plans and AI log were left unchanged.

## 2. Restored historical dependencies (attribution)

The five files `src/papertrace/answer/{__init__,eligibility,errors,model,service}.py`
were restored by the supervisor setup from PR #19 head `3d536aa` as historical
implementation dependencies. They are not newly authored in this stage and were
read-only here. The existing validated-token repair in `eligibility.py` /
`service.py` is part of that restored source and was not reimplemented.

ADR-001 was likewise restored exactly from PR #19, retaining its
`accepted-limited-scope` wording for D slice 1, the C→D projection and the B→D
generation boundary. No new ADR approval was created or extended.

## 3. Implemented interface

`papertrace.answer.c_adapter` adds one D-local adapter:

```python
class CReviewProjectionAdapter:
    def __init__(self, *, ledger: ReviewLedger) -> None: ...
    def read_projection(self, question_id: str) -> ReviewProjection: ...
```

- It uses C's public exported `ReviewLedger` and `ReviewProjection` from
  `papertrace.review`.
- The constructor is keyword-only and stores the ledger reference.
- `read_projection` delegates to `ledger.projection(question_id)` and returns
  C's projection object unchanged.
- It does not map the projection to a dict, rebuild identity or tokens, cache an
  accepted set, recompute digests, or write the ledger.
- C read errors, including `ReviewLedgerCorrupted` and an injected
  `PermissionError` / `OSError` instance, propagate unchanged; there is no
  fallback to an empty approval set.
- No existing D file or public export changed. `AnswerService` receives the
  adapter through its current `projections` port, and no shared contract, B
  adapter or app orchestration was added.

## 4. Requirement and test mapping

All ledgers are synthetic and created through C's real
`prepare_decision -> commit_decision` path; revisions and digests are compared
with C's own projection and are never recomputed.

| Approved test group / check | Behavior observed | Requirements |
|---|---|---|
| Adapter interface tests (2) | Returns C's `ReviewProjection`, not a dict, for each requested question; missing-adapter classification check now sees the real module | INV-03, INV-04, QA-01 |
| CT-D-01 (2 cases) | Absent or empty ledger abstains with `NO_APPROVED_EVIDENCE` and C's real revision/digest; file absence is not a read failure | FR-D-01, INV-01, INV-04 |
| CT-D-02 | One real accepted decision yields `failed` / `GENERATION_PATH_NOT_ENABLED`, approved exactly C's accepted set, empty sent/cited/body | FR-D-01, FR-D-03 (partial), INV-04 |
| CT-D-03 (3 cases + reset reuse) | all-pending, all-excluded and mixed states keep only accepted evidence in approved; one reused adapter/service observes a real reset as abstained | FR-D-02 (partial), INV-03, INV-04 |
| CT-D-04 | Acceptance for one question does not authorize another; the second draft carries its own scope tokens | INV-03, INV-04 |
| CT-D-05 | A ledger bound to snapshot A raises `ProjectionScopeMismatchError` for a snapshot B request and returns no draft | FR-D-02 (partial), INV-04, QA-01 |
| CT-D-06 | A truncated ledger propagates `ReviewLedgerCorrupted` through adapter and service with no fallback draft | QA-01, INV-01 |
| CT-D-07 (2 cases) | The exact injected `PermissionError` / `OSError` instance reaches the caller after one intercepted ledger read; no draft is returned | FR-D-02 (partial), INV-01, QA-01 |
| Offline isolation | No product model, provider SDK, network or real semantic call; sockets disabled | COST-01 |

## 5. Measured verification

Interpreter: the existing project CPython 3.14.8 / pytest 9.2.0 / pydantic
2.14.3 environment, invoked from this checkout without installing or copying a
virtual environment. The commands below are the full authorized offline check
set, with `--disable-socket -p no:cacheprovider -c papertrace.pytest.ini`.

Before baseline (supervisor-measured in this prepared checkout):

| Check | Result |
|---|---|
| Integration file | 15 collected; 2 passed, 13 failed; 0 errors/skips; all 13 stopped at the explicit missing-adapter availability assertion |
| Existing D tests | 56 passed |
| Existing C tests | 24 passed |
| Full offline | 427 collected; 18 failed, 407 passed, 2 skipped |
| Paired baseline (integration excluded) | 412 collected; 5 failed, 405 passed, 2 skipped |
| Target Ruff / mypy / schema / whitespace | PASS (mypy 10 source files); full Ruff only the unchanged `scripts/paperqa_smoke.py:37` I001; `git diff --check` exit 0 |

After implementation (measured in this session):

| Check | Result |
|---|---|
| `pytest ... test/offline/test_answer_c_integration.py` | exit 0; 15 passed |
| `pytest ... test/offline/test_answer.py test/offline/test_answer_validated_tokens.py` | exit 0; 56 passed |
| `pytest ... test/offline/test_review.py` | exit 0; 24 passed |
| `pytest ... test/offline` | exit 1; 427 collected; 4 failed, 421 passed, 2 skipped |
| `pytest ... test/offline --ignore=test/offline/test_answer_c_integration.py` | exit 1; 412 collected; 4 failed, 406 passed, 2 skipped |
| Target Ruff (`src/papertrace/answer` plus the three D test files) | exit 0; PASS |
| Full configured Ruff | exit 1; only the unchanged `scripts/paperqa_smoke.py:37` I001 |
| mypy | exit 0; PASS, 11 source files |
| `scripts/gates.py --gate schema` | exit 0; schema PASS; remote enforcement `NOT_DEPLOYED_OR_VERIFIED` |
| `scripts/opencode_support.py` | exit 0; static portable preflight PASS; no model started |
| `git diff --check` | exit 0 |
| `git status --short` | only the pre-existing supervisor setup edits plus this record and the untracked `src/papertrace/answer/` tree (five restored files plus the new adapter); no staged changes |

Failure attribution: the four remaining full-offline failures are exactly the
same four nodes in the paired baseline, namely the local
`test/offline/test_opencode_configuration.py` configuration-contract
expectations that assume broader D write permissions than the local Build-D
setup. They are local governance/config expectation mismatches, not adapter
behavior, and no permission list was widened. The previously reported fifth
baseline failure, `test_full_regression.py::test_timeout_stops_owned_test_descendants`
(subprocess `ps` rejected with `PermissionError`), did not reproduce in this
session's shell: the full and paired runs show only the four configuration
failures, so that environment-dependent node passed here. The full-minus-baseline
difference is exactly the 15 integration items, all now passing; no pre-existing
test was edited, skipped or loosened. The two skips remain the unavailable
OpenCode executable checks and are not PASS.

## 6. ADR applicability

ADR-001 is applicable in its recorded limited scope: current D slice 1, the C→D
projection and the B→D generation boundary. This adapter is a read-only C→D
projection implementation inside that scope. The record neither resets nor
extends ADR-001. Because the file lives under the safety-reviewed
`src/papertrace/answer/` prefix, an independent review of the exact
implementation head remains required before any merge; ADR applicability is not
a merge approval.

## 7. Limits of the sequential guarantee

The adapter keeps no projection state, so each `read_projection` call re-reads
the ledger through C and one adapter/service reused after a real C reset
observes the new projection. That is sequential-reuse coverage only. It does not
prove freshness through a future release or write transaction, does not
implement or call `verify_current`, and makes no concurrency or atomicity claim.
Generation, B adapters, citation and budget policies, publication, retries and
release race safety remain outside this slice.

## 8. AI and session disclosure (draft)

The two new files were written in an OpenCode session scoped to this prepared
checkout, using native file writes for the authorized paths, read-only file
inspection, and only the allowed offline verification commands. The session used
no subagents, plugins/MCP, installs, symlinks, permission changes, Git
staging/commit/push, PR or review actions, PaperTrace product-model/provider
calls, live retrieval or real semantic evaluation.

The assistant environment self-reports the model identity as DeepSeek V4.1 Flash
1017 (provider ID `deepseek`, model ID `deepseek-flash`). That identity is
self-reported and not independently verified by the project. Communication with
the assistant provider is a development-tool channel, separate from PaperTrace
product-model calls (COST-01). No raw transcript, session ID or private
quotation is recorded here. Shared AI-use-log reconciliation is a later
supervisor packaging step; this section is the truthful draft disclosure for
this record.

## 9. Remaining work

- Independent review of the exact implementation head by a student who did not
  implement it, covering source and safety; the PR #20 test approval and the
  PR #19 approvals do not cover this implementation.
- Later supervisor packaging of an implementation PR created from the test head
  with the exact body line `Test approval PR: #20` and an ADR-001 reference.
  PR #15, #19 and #20 stay open and unmerged; the RED test proposal must not be
  merged.
- Full upstream regression, live/product-model evaluation, native-engine E2E,
  remote Actions and real semantic evaluation remain NOT_RUN/BLOCKED for this
  local stage. Shared AI-use-log reconciliation belongs to the later supervisor
  step.

## 10. Stop point

The stage stops after the two new files and the local verification above. No
commit, push, PR, review or merge was performed.


## 11. Independent supervisor verification and packaging (2026-11-23 HKT)

The original OpenCode-authored record remains unchanged in the authoring checkout. This candidate-only addendum preserves the author observations above separately from independent supervisor measurements.

Independent checks: C-to-D 15 passed, existing D56 passed, C24 passed; full offline 427 collected with 5 failed/420 passed/2 skipped; paired baseline412 collected with 5 failed/405 passed/2 skipped. All412 prior node states agree in the pair. Compared with the supervisor pre-implementation run, exactly13 missing-adapter failures became passes and every other node state stayed unchanged.

The supervisor additionally observes the environment-dependent ps PermissionError, alongside the same four local permission-contract failures. Target Ruff/mypy11/schema/static preflight pass; full Ruff retains only the unchanged public paperqa_smoke.py I001. No product/live or real semantic evaluation was invoked.

Publication preparation restores the five original D19 sources, limited-scope ADR and token-implementation record unchanged. The candidate AI log preserves all19 PR20 entries, restores five missing historical PR19 entries with identical parsed values and appends two current truthful disclosures. Both local setup files are excluded. Approved test/fixture/plan blobs remain unchanged; no commit, push, new PR, independent implementation approval or merge exists yet.

Clean publication snapshot measured separately: full offline427 collected, 424 passed/1 failed/2 skipped. Only test_timeout_stops_owned_test_descendants fails at the sandbox ps PermissionError. Exactly the four local configuration-contract failures become passes after excluding local setup; every other node outcome matches the restricted authoring run. Schema and AI-log gates pass. Full static fails only the unchanged public script I001; its other seven subchecks pass. These are local measurements, not a remote CI result or complete course acceptance.
