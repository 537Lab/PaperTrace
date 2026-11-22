# Module D design record: validated projection-token reuse (2026-11-22)

| Item | Value |
|---|---|
| Date | 2026-11-22 (HKT) |
| Stage | **Test preparation / documentation cleanup only**; no `src/` was written |
| Status | Local tests supervisor-reviewed (23 collected, 12 behavioral failures, 11 passes); design cleanup and publication preparation pending. No new test commit/PR exists; post-fix behavior is NOT_MEASURED |
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
  status: local-tests-supervisor-reviewed-design-cleanup-pending
  approvals:
  - Student local approval of the two-file test-preparation plan on 2026-11-22 HKT; not a GitHub test-commit approval or source authorization
  verification:
  - 'Coding-session run: new file 23 collected, 12 failed, 11 passed (pytest 9.2.0, CPython 3.14.8)'
  - 'Coding-session run: existing test_answer.py 33 passed'
  - 'Coding-session run: full test/offline 16 failed (12 new + 4 known local configuration), 394 passed, 2 skipped'
  - 'Supervisor paired run: new file 12 failed / 11 passed; full test/offline 17 failed (12 new + 4 known local configuration + 1 sandbox ps failure), 393 passed, 2 skipped; paired baseline 5 failed / 382 passed, 2 skipped'
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
