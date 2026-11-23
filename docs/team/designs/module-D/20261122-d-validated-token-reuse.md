# Module D design record: validated projection-token reuse (2026-11-22)

| Item | Value |
|---|---|
| Date | 2026-11-22 (HKT) |
| Stage | **Test preparation / documentation cleanup only**; no `src/` was written |
| Status | PR #15 review corrections locally supervisor-verified on both the reviewed D implementation and the real main-based no-D publication checkout; independent approval of the revised exact test head is still required. Earlier revision-session NOT_RUN statements are historical; section 9.3 records the later publication-base checks. Post-fix behavior is NOT_MEASURED |
| Module | D `answer`, slice 1 |
| Defect scope | `AnswerService.prepare` re-reads `projection.revision` and `projection.digest` after eligibility validation |
| Local implementation identity | `0fa0d01e4d3ddf26ffdc8200f86c1f53e51e23a6` (this worktree); remote #13 head `287a55ca12333133d5fa094d67b1e32cfbd4f148` differs by a documentation-only extra commit and is not called the same head |

## 1. Authorization boundary

The student approved the two-file test-preparation scope locally on 2026-11-22 HKT.
That local approval covers test preparation only:

- Writable paths: `test/offline/test_answer_validated_tokens.py` and this record.
- Read-only: D source, the approved `test_answer.py`, its two fixtures, the approved
  design records, and contract files.
- Not granted: any `src/` implementation, the C adapter, generation, publication,
  commits, push, PR creation/approval/merge, dependency changes, model/provider calls,
  shared-contract/CI/permission/ADR edits, or shared AI-use log edits.
- The local host/permission setup (worktree, `opencode.jsonc`,
  `.opencode/permissions.jsonc`) was made by the supervisor and is excluded from the
  future published test commit.

ADR-001 in remote PR #13 head `287a55ca` is treated as accepted-limited-scope for
current D slice 1 and the stated C/B boundaries. This record does not reset it, does
not invent a human approval, and does not extend it to the new tests, future code,
merge or real model evaluation. A design expansion outside that scope still needs the
relevant owner decision.

GitHub approval by an independent, non-implementing student remains a later checkpoint
before any source implementation, and it must cover the exact cumulative test head. It
is not the only remaining immediate action: supervisor review and publication
preparation come first. The local approval and this record are not a GitHub Approve.

## 2. Defect and observed pre-fix behavior

- `src/papertrace/answer/eligibility.py` validates `revision` and `digest` once,
  through `_validate_shape`, and returns only an `EligibilityDecision`.
- `src/papertrace/answer/service.py` then builds the draft in `_draft` and reads
  `projection.revision` and `projection.digest` again (lines 63-64 of that file).
- A projection whose values change between reads therefore yields a draft whose
  `review_revision`/`review_digest` were never the values accepted by validation.

Measured on the local implementation identity above with the new tests' trap projection
(accepted evidence, first read `revision=7`, `digest=A`; later read `revision=9`,
`digest=B`): the draft received `review_revision=9` and `review_digest=B`, and each
token was read twice. This is a sequential snapshot-consistency defect inside one
`prepare` call. It is not evidence about concurrency, ledger authenticity or release
freshness.

## 3. Proposed fix design (not implemented)

Proposal, not a claim about the current source and not a test requirement:

1. Keep the public `evaluate_eligibility(projection=..., request=...) ->
   EligibilityDecision` API and its return type unchanged.
2. Have one validation path return, alongside the decision, the immutable validated
   tokens (`revision`, `digest`) produced during validation. A D-internal immutable
   validated assessment (name illustrative) may carry them; the public
   `evaluate_eligibility` stays as a thin compatibility wrapper.
3. `AnswerService.prepare` calls that path once and passes the validated tokens to the
   draft builder. `_draft` no longer receives the projection as a token source, so it
   cannot re-read `revision`/`digest`.

`EligibilityDecision` itself is exported from `papertrace.answer`, so adding required
fields to that public dataclass is not inherently compatible: callers outside this
repository could construct or unpack it even though a repository search found no
external direct construction. Adding validated-token fields to the public dataclass is
therefore an alternative that would need its own compatibility review, not an assumed
safe default. The tests deliberately do **not** assert any new private or public
symbol, an internal return type, or a call count on validation helpers. They only
observe draft values, draft shape and token read counts through the public
`AnswerService`.

Out of scope for this record and the tests: real C integration/adapter mapping,
generation and publication, `verify_current`, release freshness, retries/model
attempts, concurrent mutation of a projection, and any claim of complete course
acceptance.

## 4. Test design (`test/offline/test_answer_validated_tokens.py`)

All data is synthetic: the approved `synthetic-corpus-a.txt` fixture, contract-valid
`CorpusSnapshot`/`EvidenceRecord` objects built from its bytes, and a duck-typed
projection double. The approved test helpers are not imported, because that would
couple this file to pytest's non-package `test/offline` import mode; no approved fixture
was edited and no third file was added.

`TokenTrapProjection` exposes `revision`/`digest` as properties with **separate**
counters (`revision_reads`, `digest_reads`) and returns the first ("A") value on read
one and later ("B") values afterwards. Tests never read these properties themselves and
never consume them before `prepare`; draft assertions compare against immutable A/B
constants. A shape-invalid first token is followed by valid later values, so deferring
validation to the later valid values would yield a draft instead of the required error.

| ID | Tests | Covered behavior |
|---|---|---|
| VT-D-01 | `test_static_projection_controls_preserve_the_draft_contract` (3 cases: accepted, unreviewed-empty revision 0, reviewed-empty nonzero) | Valid static projections still produce the approved draft shape; guards against fixture/helper breakage unrelated to the defect |
| VT-D-02 | `test_draft_uses_the_validated_first_token_values[eligible-both-vary]` | Both fields vary: draft keeps A revision and A digest; `failed`, approved membership preserved |
| VT-D-03 | `...[eligible-revision-only]`, `...[abstained-revision-only]` | Revision-only trap: a digest-only check cannot mask it |
| VT-D-04 | `...[eligible-digest-only]`, `...[abstained-digest-only]` | Digest-only trap: a revision-only check cannot mask it |
| VT-D-05 | `test_successful_prepare_reads_each_token_exactly_once` (6 cases) | Each token read exactly once for both the not-enabled (eligible) and no-evidence (abstained) outcomes |
| VT-D-06 | `test_invalid_first_token_raises_without_using_later_valid_values` (negative revision first; malformed digest first) | `ProjectionShapeError`, no draft, failing token read once; later getters are not required to run |
| VT-D-07 | Embedded in every draft assertion via `assert_draft_identity` | Approved membership, refusal reasons, empty `sent`/`cited`/`body`, ids/time, and `AnswerDraft` JSON round-trip |
| Instrument control | `test_token_cases_change_only_the_declared_field` (6 cases) | No case is vacuous because A and B are equal |

Case counts: 5 test functions, 23 collected cases.

## 5. Local verification actually run

Interpreter: the existing project CPython 3.14.8 interpreter with pytest 9.2.0, invoked
from this worktree; `python` below denotes it. It was not installed or copied into this
worktree. The test file and source files were unchanged between the two runs below.

### 5.1 Coding session run (2026-11-22, about 10:30 HKT)

| Check | Actual result |
|---|---|
| `python -m pytest -c papertrace.pytest.ini test/offline/test_answer_validated_tokens.py` | exit 1; collected 23; **12 failed, 11 passed** |
| `python -m pytest -c papertrace.pytest.ini test/offline/test_answer.py` | exit 0; 33 passed |
| `python -m pytest -c papertrace.pytest.ini test/offline` | exit 1; **16 failed, 394 passed, 2 skipped** |
| `python -m pytest ... test/offline --ignore=test/offline/test_answer_validated_tokens.py` | exit 1; **4 failed, 383 passed, 2 skipped** (unchanged baseline) |
| `python -m ruff check --config papertrace.ruff.toml test/offline/test_answer_validated_tokens.py` | exit 0; all checks passed |
| `python -m ruff check --config papertrace.ruff.toml src/papertrace test/offline scripts` | exit 1; exactly one existing `I001` at `scripts/paperqa_smoke.py:37` (unchanged, not fixed here) |
| `python -m mypy --config-file mypy.ini src/papertrace` | exit 0; no issues in 10 source files |
| `python scripts/gates.py --gate schema` | exit 0; PASS; `remote_enforcement: NOT_DEPLOYED_OR_VERIFIED` |
| `git diff --check` | exit 0 (tracked changes) |

Assertion reach in that run:

- The four revision-varying VALUE cases fail at
  `draft.review_revision == first revision`; the two digest-only VALUE cases pass the
  revision assertion and fail at `draft.review_digest == first digest`. Both fields are
  therefore independently exposed.
- All six READ-COUNT cases stop at `revision_reads == 1` with actual value `2`. Their
  subsequent `digest_reads` assertions are **NOT_REACHED** in that run; the digest-only
  value cases above are what independently expose digest re-reading.
- The trap returns a later valid value on a second read; it does not raise. The
  invalid-first cases raise from `ProjectionShapeError` validation instead.

Failure classification (coding-session run):

- **12 new failures are behavioral RED for this defect**, not import/collection errors:
  6 draft-value failures and 6 read-count failures. No assertion in these tests
  requires a new implementation symbol.
- **11 passes** are the 3 static controls, 2 invalid-first cases and 6 instrument
  controls; these pass before the fix and are expected to stay passing.
- **4 baseline failures** are exactly the known local configuration-contract nodes in
  `test_opencode_configuration.py` (human-only rules, role permission paths, course
  manifest split, embedded rules). They assert broad D source/test write grants that
  the supervisor's restricted local setup intentionally changed. They are not
  behavioral RED for the token defect; tests, permissions and the failures were left
  visible and unmodified.
- **2 skips** are the pre-existing "OpenCode executable is not installed" cases.
- **UNCHANGED**: D source, `test/offline/test_answer.py`, both synthetic fixtures and
  both existing design records; `git status` shows only this record and the new test as
  authored changes beyond the supervisor's two local config files.

### 5.2 Supervisor run (2026-11-22, about 10:36-10:39 HKT)

| Check | Actual result |
|---|---|
| New token file | exit 1; 23 collected; **12 failed / 11 passed** |
| `test/offline/test_answer.py` | exit 0; 33 passed |
| Whole `test/offline` | exit 1; **412 collected; 17 failed / 393 passed / 2 skipped** |
| Paired baseline excluding the new file | exit 1; **389 collected; 5 failed / 382 passed / 2 skipped** |
| New-file Ruff | PASS |
| Whole requested Ruff scope | retains exactly the unchanged `scripts/paperqa_smoke.py:37 I001` |
| mypy | PASS, 10 source files |
| Local schema gate | PASS; `remote_enforcement` remains `NOT_DEPLOYED_OR_VERIFIED` |
| Module file origins | four C/D module file origins matched this checkout |
| Protected identities | ten checked protected source/contract/test/fixture/design files matched HEAD byte-for-byte |
| Approved blobs | four approved PR #3 non-log blobs matched their recorded identities |
| Tracked `git diff --check` | exit 0 |
| Untracked new files, `git diff --no-index --check /dev/null <file>` | no whitespace diagnostics; exit 1 because the files differ |

The supervisor run's 17 failures are: the same 12 token-defect RED cases, the same 4
known local configuration-contract failures, and 1 environment/sandbox failure at
`test_full_regression.py::test_timeout_stops_owned_test_descendants` (`ps`: Operation
not permitted). That sandbox failure is disclosed as neither token RED, upstream
regression, nor a passing check, and it does not contradict the coding-session result
of 16 failed / 394 passed / 2 skipped. The paired delta is exactly 12 failures and 11
passes attributable to the new test file.

`test/offline` was run in both sessions. **NOT_RUN:** full upstream regression beyond
`test/offline`, PaperTrace product-model calls, live/network tests, real semantic
evaluation, actual OpenCode executable E2E, GitHub Actions/approval, and post-fix
behavior (NOT_MEASURED). These offline checks do not imply that the coding assistant
made no provider requests.

## 6. Non-claims and limits

- Not a GitHub Approve, not an implementation authorization, not a merge or
  publication decision.
- Not proof that the proposed fix shape is the one maintainers will choose; only the
  observable behavior above is required.
- Not proof of concurrency safety, C ledger authenticity, digest recomputation,
  release freshness, or the absence of provider requests in any future slice.
- Not a claim that existing local configuration failures are acceptable for merge;
  they are disclosed, not waived.
- Static lint/AST observations are supplementary; they are not a sandbox.

## 7. Proposed AI-use disclosure (not written to the shared log)

An AI coding assistant was used for test preparation (OpenCode desktop session, role
`papertrace-build-D`, test-preparation stage). The provider/model values below are what
the assistant reported; its model identity was not independently verified. These
offline checks made no PaperTrace product-model, live/network test, or real
semantic-evaluation invocation; that does not imply the assistant made no provider
requests. The shared `docs/ai-use-log.yaml` was not modified. If the supervisor
integrates this work into a cumulative test proposal, the following is a draft
append-only entry, subject to the shared-log editor's decision:

```yaml
- entry_id: D1-TOKEN-TESTPREP-20261122-01
  timestamp: '2026-11-22T02:32:46Z'
  tool: OpenCode desktop session, agent role papertrace-build-D (test-preparation stage)
  model: deepseek-flash (provider deepseek; runtime label "DeepSeek V4.1 Flash 1017", not independently verified)
  purpose: Add offline regression tests and a design record for validated revision/digest reuse in module D slice 1; no src implementation
  scope:
  - test/offline/test_answer_validated_tokens.py
  - docs/team/designs/module-D/20261122-d-validated-token-reuse.md
  status: local-tests-supervisor-reviewed-revised-addressing-pr15-findings
  approvals:
  - Student local approval of the two-file test-preparation plan on 2026-11-22 HKT; not a GitHub test-commit approval or source authorization
  verification:
  - 'Coding-session run: new file 23 collected, 12 failed, 11 passed (pytest 9.2.0, CPython 3.14.8)'
  - 'Coding-session run: existing test_answer.py 33 passed'
  - 'Coding-session run: full test/offline 16 failed (12 new + 4 known local configuration), 394 passed, 2 skipped'
  - 'Supervisor paired run: new file 12 failed / 11 passed; full test/offline 17 failed (12 new + 4 known local configuration + 1 sandbox ps failure), 393 passed, 2 skipped; paired baseline 5 failed / 382 passed, 2 skipped'
  - 'Revision run (see section 9): 23 collected; 12 failed / 11 passed; configured targeted Ruff PASS; old D file 33 passed'
  - ruff on the new file: PASS; repository ruff retains the unchanged scripts/paperqa_smoke.py I001
  - mypy src/papertrace: PASS; schema gate: PASS
  limitations:
  - Not an independent GitHub Approve; no src/ change; no PaperTrace product-model, live/network test or real semantic-evaluation invocation in these offline checks (the assistant's own provider requests are not covered)
  - Post-fix results are NOT_MEASURED; full upstream regression, live/semantic evaluation, OpenCode executable E2E and GitHub Actions are NOT_RUN
```

## 8. Decision log

- 2026-11-22: accepted the two-file plan with the supervisor's corrections: predicted
  results stay NOT_RUN until measured; no new public API is a test requirement; keep
  tests behavioral; do not modify ADR-001 status or the local configuration.
- 2026-11-22: supervisor reviewed the local tests and requested documentation cleanup
  only. This record now separates the coding-session and supervisor runs, states the
  actual assertion reach, corrects the `EligibilityDecision` compatibility wording,
  removes host/private text, and records the sandbox failure without waiving it. No
  test, source or configuration file was changed.
- 2026-11-22: PR #15 review requested changes for module-scope import/collection and a
  configured Ruff I001. The test file now resolves D at execution time and imports only
  stdlib, pytest and contracts at module scope. Section 9 records the change and the
  new local checks; no source, assertion or configuration was changed.

## 9. Revision for PR #15 review findings (2026-11-22)

The public test-only proposal PR #15 (head
`01b02a14b9eb5588a765fbe2e90b35e75c130e53`) received a changes-requested review with
two findings. There is no independent approval for that head. This section records a
local revision only; publication and the main-based no-D checks remain the
supervisor's separate action.

### 9.1 Findings and change

1. **Collection abort on the no-D base.** The file imported `papertrace.answer` at
   module scope. On a main-based test-only branch that module does not exist, so
   pytest aborted collection instead of running the tests. D is now resolved at
   execution time: module scope imports only the standard library, pytest and
   `papertrace.contracts`, and `answer_module()`/`d_symbol()` resolve the module and
   public attributes when a test runs.
   - Only an exact `ModuleNotFoundError` whose `name` is `papertrace.answer` becomes
     the explicit missing-implementation assertion.
   - A missing parent package, a missing dependency of an existing module, and any
     import-time error inside an existing module propagate.
   - A missing public attribute raises a clear assertion instead of an `AttributeError`
     traceback.
   - No skip, `importorskip`, xfail, stub, `sys.modules` substitution, autouse skip,
     `noqa` or configuration override is used in the test file.
2. **Configured Ruff I001 on the new import block.** The same module-scope D import is
   removed from the block; the file now imports only stdlib, pytest and contracts at
   module scope. The configured targeted Ruff command passes on this checkout without
   any Ruff or pytest configuration change. Whether the no-D base still reports any
   import-block issue is checked by the supervisor there and is **NOT_RUN** here. The
   unrelated `scripts/paperqa_smoke.py:37` I001 is separate and remains unchanged.

All five test functions, 23 parametrized cases, case IDs, A/B token values,
independent getter counters, invalid-first cases and draft/contract assertions are
preserved. No assertion was weakened and no source change was made.

### 9.2 Local checks actually run (2026-11-22, revision session)

Interpreter: the existing project CPython 3.14.8 / pytest 9.2.0; `python` denotes it.

| Check | Actual result |
|---|---|
| `python -m pytest -c papertrace.pytest.ini --collect-only -q test/offline/test_answer_validated_tokens.py` | exit 0; 23 tests collected |
| `python -m pytest -c papertrace.pytest.ini -q test/offline/test_answer_validated_tokens.py` | exit 1; **12 failed, 11 passed** |
| `python -m pytest -c papertrace.pytest.ini -q test/offline/test_answer.py` | exit 0; 33 passed |
| `python -m pytest -c papertrace.pytest.ini -q test/offline` | exit 1; **16 failed, 394 passed, 2 skipped** |
| `python -m pytest ... test/offline --ignore=test/offline/test_answer_validated_tokens.py` | exit 1; **4 failed, 383 passed, 2 skipped** |
| `python -m ruff check --config papertrace.ruff.toml test/offline/test_answer.py test/offline/test_answer_validated_tokens.py` | exit 0; all checks passed |
| `python -m ruff check --config papertrace.ruff.toml src/papertrace test/offline scripts` | exit 1; exactly the unchanged `scripts/paperqa_smoke.py:37` I001 |
| `python -m mypy --config-file mypy.ini src/papertrace` | exit 0; 10 source files |
| `python scripts/gates.py --gate schema` | exit 0; PASS; `remote_enforcement: NOT_DEPLOYED_OR_VERIFIED` |
| `git diff --check` | exit 0 (tracked changes) |
| Untracked new files, `git diff --no-index --check /dev/null <file>` | no diagnostics; exit 1 because the files differ |

Failure classification for the 12: 4 revision-value cases, 2 digest-value cases and 6
read-count cases. The read-count cases stop at `revision_reads == 1` (actual 2); the
later `digest_reads` assertion is **NOT_REACHED** in this run. The 11 passes are 6
parameter-table self-checks, 3 static controls and 2 invalid-first cases; the six
self-checks do not exercise the service. The four baseline failures are the known
local configuration-contract nodes; the delta is exactly 12 failures and 11 passes.
No sandbox `ps` failure occurred in these runs; it is environment-dependent and is not
relabeled as token RED.

Local no-D diagnostic (**not** the publication-base check): with a temporary external
`sys.meta_path` blocker for exactly `papertrace.answer` (the test file itself is
unchanged and contains no such substitution), collection still succeeded (23) and
execution produced 17 missing-implementation assertion failures and 6 instrument-control
passes. This is diagnostic evidence that the module-scope import is gone; the
supervisor's main-based no-D collection, execution and configured Ruff runs are
**NOT_RUN** here.

**NOT_RUN:** publication-base/no-D collection, execution and configured Ruff; full
upstream regression beyond `test/offline`; live/network tests; PaperTrace product-model
calls; real semantic evaluation; OpenCode executable E2E; GitHub Actions and approval;
and post-fix behavior (NOT_MEASURED). No source fix, adapter, generation or publication
work was attempted.

### 9.3 Later independent supervisor verification (2026-11-22 HKT)

The results in section 9.2 are the coding-session report. The supervisor then
verified the authored revision and copied the two files, without changing test
code, into the actual main-based PR #15 publication checkout. This is a later
verification snapshot, not a claim that the coding-session checks ran there.
The publication checkout still has no D implementation and uses main
`6235c33d460b48d1ff11a10624d1bcd5919ea4f0` plus the test proposal.

| Check / execution base | Independent result |
|---|---|
| Reviewed D checkout `0fa0d01`: new tests | 23 collected; 12 behavioral failures, 11 passes; zero errors/skips |
| Reviewed D checkout: old D tests | 33 passed |
| Reviewed D checkout: full offline | 412 collected; 17 failed, 393 passed, 2 skipped; zero errors |
| Reviewed D checkout: baseline excluding new file | 389 collected; 5 failed, 382 passed, 2 skipped; zero errors |
| Real no-D publication checkout: full offline collection | exit 0; all 412 tests collected, no collection errors |
| Real no-D publication checkout: new tests | 17 missing-implementation assertion failures, 6 parameter-table passes; zero errors/skips |
| Real no-D publication checkout: full offline execution | 50 failed, 360 passed, 2 skipped; zero errors |
| Configured Ruff on old/new D test files, both checkouts | PASS, without first-party overrides or configuration edits |
| Configured full-scope Ruff, both checkouts | Exactly one unchanged I001 at `scripts/paperqa_smoke.py:37`; no finding in the new test file |
| Reviewed D source mypy | PASS, 10 source files |
| Local schema, both checkouts | PASS; not evidence of remote enforcement |

In the reviewed D checkout the five shared baseline failures are four restricted
local configuration-contract mismatches and one sandbox `ps` PermissionError.
They are separate from the twelve token-defect failures. The full/baseline delta
is exactly twelve failures and eleven passes. Two skips reflect the unavailable
OpenCode executable. The coding session did not encounter the sandbox failure;
the supervisor did, so its result is reported separately.

In the real no-D checkout, 32 failures belong to the unchanged old D proposal,
17 to the new tests' explicit missing-D assertions, and one to the sandbox `ps`
PermissionError. Thus the suite now executes instead of aborting collection.
Those 49 missing-D failures do not reproduce the token defect or certify product
behavior. The six new passes only validate the parameter table.

The supervisor compared all five test-function bodies/decorators using Python ASTs,
normalizing only the exact runtime public-symbol lookups back to their prior
imported names: they match the published version. Parameter tables and case IDs
also match. Source, contracts, old tests, fixtures and existing local permission
modifications remain unchanged. The original four non-log PR #3 blobs are retained.
Package origins were checked explicitly in each checkout. The supervisor's real
no-D checks did not use import blockers, stubs, skips or module substitutions.

The two review findings are resolved in this local candidate. This is not a
GitHub Approve or a full CI/merge acceptance. Source repair, post-fix measurement,
full upstream execution, live/product-model evaluation and executable OpenCode
E2E were not performed in this verification. Publication and a fresh exact-head
independent review remain separate actions.
