# Module D implementation record: validated projection-token reuse (2026-11-22)

| Item | Value |
|---|---|
| Date | 2026-11-22 (HKT) |
| Stage | **Local source implementation and local verification only**; no commit, push or PR action |
| Module | D `answer`, slice 1 |
| Checkout | branch `codex/d-token-fix` |
| HEAD | `3f624b5b2f685cd0133291d97206176fe7daa290` — the approved cumulative test head of test proposal PR #15 (open, unmerged) |
| Upstream baseline | `c692d0dfeac4a0296599f7fe21a253a58b7ac12a` (`papertrace-upstream-baseline`) |
| Tests and checks | All executed locally; post-fix results below are MEASURED in this session unless marked NOT_RUN |

## 1. Scope and authorization

The student authorized this exact local source-fix scope on 2026-11-22 HKT for the
`papertrace-build-D` role, implementation stage. The writable set for this session was:

1. `src/papertrace/answer/eligibility.py`
2. `src/papertrace/answer/service.py`
3. this record (new)

Read-only and untouched by this session: `model.py`, `errors.py`, `__init__.py`,
`src/papertrace/contracts.py`, `test/offline/test_answer.py`,
`test/offline/test_answer_validated_tokens.py`, `test/fixtures/answer/*`, both
previously approved D design records, all ADRs, CI/gate scripts, dependencies,
permissions and the shared AI-use log. No commit, push, PR creation/editing/review/merge,
message or product-model call was made.

The independent test approvals recorded for PR #15 cover the exact cumulative test
contract only. They are not approval of this implementation, not a merge decision and
not evidence of full CI, upstream regression or model quality. PR #15 must stay open and
unmerged; its `test-proposal-only-do-not-merge-red-tests` state is deliberate.

## 2. Base and restored source attribution

The five files under `src/papertrace/answer/` in this checkout were restored
byte-for-byte by the supervisor from the historical local implementation identity
`0fa0d01e4d3ddf26ffdc8200f86c1f53e51e23a6`, and individually matched by the supervisor
against the remote PR #13 head `287a55ca12333133d5fa094d67b1e32cfbd4f148` blobs. That
source is prior student implementation, not new assistant authorship, and it still
contained the token defect described below. This session changed exactly two of those
five files and did not rewrite the other three.

## 3. Defect and implemented fix

Pre-fix behavior (measured in this checkout before editing, see section 5): validation
read `revision` and `digest` once, returned only an `EligibilityDecision`, and the draft
builder then read both properties again from the same projection. A projection whose
values change between reads therefore produced a draft carrying values that validation
never accepted.

Implemented, matching the previously proposed minimal design:

- `eligibility.py` now has one validation path, `assess_eligibility(*, projection,
  request)`, which performs every existing check exactly once and returns a D-internal
  frozen `EligibilityAssessment(decision, revision, digest)`. The tokens are the ones
  accepted during validation.
- `evaluate_eligibility(*, projection, request) -> EligibilityDecision` is now a thin
  compatibility wrapper returning `assess_eligibility(...).decision`. Its keyword-only
  signature and return type are unchanged.
- `AnswerService.prepare` calls `assess_eligibility` exactly once and no longer passes
  the projection to the draft builder. `_draft` takes `revision` and `digest` values, so
  it cannot read either property again, for either outcome.
- Preserved unchanged: invalid-first rejection (each token is read once during
  validation; a later getter is never consulted, so a bad first value cannot be
  replaced by a valid later one), the shape/scope/membership/provenance checks and their
  existing error types, empty approved evidence → `abstained` /
  `NO_APPROVED_EVIDENCE`, non-empty approved evidence → `failed` /
  `GENERATION_PATH_NOT_ENABLED`, and empty `sent_evidence_ids`,
  `citation_evidence_ids` and `body`. No generation collaborator, model, SDK or HTTP
  path was added, and no failure is caught and converted into a draft.

## 4. Compatibility and guarantee

- `EligibilityDecision` keeps its three fields (`eligible`, `approved_evidence_ids`,
  `reason`); no field was added, so existing construction and attribute checks still
  hold. It remains the only exported decision type.
- `EligibilityAssessment` is D-internal: it is not exported from `papertrace.answer`
  (`__init__.py` was not modified, and its `__all__` is unchanged). It is a data copy of
  validation-time values; it recomputes and re-authenticates nothing.
- Behavior changes only in the case where the projection yields different
  `revision`/`digest` on a second read; all other observable behavior is unchanged.

Guarantee established: **within one sequential `prepare` call**, validation and the draft
use one read each of `revision` and `digest`.

Explicitly not established by this slice: concurrency safety, atomic ledger behavior,
digest recomputation or authenticity, `verify_current`, release freshness, the C adapter
mapping, retries or model attempts, generation, publication, context budgeting, and any
claim of complete course acceptance. Sequential token reuse alone does not prove
freshness or complete release safety.

## 5. Measured results

Interpreter: the pre-existing project virtual-environment interpreter referenced by the
repository workflow, invoked from this checkout; it was not installed or copied here.
Pytest, Ruff and mypy used their committed check configurations without overrides.
The two OpenCode permission/setup files retain the supervisor's restricted local
changes; those files are excluded from the publication candidate.

### 5.1 Before the edit (this session, same checkout)

| Command scope | Result |
|---|---|
| `test/offline/test_answer_validated_tokens.py` | exit 1; 23 collected; **12 failed, 11 passed** |
| `test/offline/test_answer.py` | exit 0; 33 passed |

The 12 failures were 6 draft-value cases and 6 read-count cases; the failing token was
read twice. This reproduces the supervisor's pre-fix baseline for the same checkout.

### 5.2 After the edit (this session)

| Command scope | Result |
|---|---|
| `test/offline/test_answer_validated_tokens.py` | exit 0; **23 passed** |
| `test/offline/test_answer.py` | exit 0; **33 passed** (unchanged) |
| `test/offline` | exit 1; 412 collected; **2 failed, 408 passed, 2 skipped** |
| `test/offline --ignore=test/offline/test_answer_validated_tokens.py` | exit 1; 389 collected; **2 failed, 385 passed, 2 skipped** |
| `test/offline/test_full_regression.py` alone | exit 0; 17 passed |
| Ruff on `src/papertrace/answer` and both D test files | exit 0; all checks passed |
| Ruff on `src/papertrace test/offline scripts` | exit 1; only the pre-existing `scripts/paperqa_smoke.py:37` I001 |
| mypy `src/papertrace` | exit 0; no issues in 10 source files |
| `scripts/gates.py --gate schema` | exit 0; PASS; `remote_enforcement: NOT_DEPLOYED_OR_VERIFIED` |
| `git diff --check` (tracked changes) | exit 0 |
| `git diff --no-index --check /dev/null <untracked file>` | no whitespace diagnostics; exit 1 only because the files differ |

Failure attribution, node by node, against the paired baseline:

- The full/baseline delta is exactly the 23 new D cases: 23 more passes, zero new
  failures, no node changed state for any other reason.
- The 2 remaining failures are the known local configuration-contract nodes
  `test_opencode_configuration.py::test_role_permissions_allow_owned_work_and_restrict_shared_or_sensitive_paths`
  and `::test_role_permissions_separate_course_manifest_from_engine_configuration`. They
  assert the broad D write lists that the supervisor's deliberately restricted local
  setup replaced. They are not token RED and are not caused by this change; the tests
  and the configuration were left unmodified.
- The supervisor's pre-fix full-suite baseline in this checkout was 412 collected,
  15 failed / 395 passed / 2 skipped (12 token cases, the same 2 configuration nodes,
  and 1 sandbox `ps` PermissionError). In this session that `ps` node
  (`test_full_regression.py::test_timeout_stops_owned_test_descendants`) passed, so the
  observed change is the 12 token cases plus 1 environment-dependent node; the sandbox
  failure is environment-dependent, is not relabeled as token RED and was not
  "fixed" by this implementation.
- The 2 skips are the pre-existing "OpenCode executable is not installed" cases.

## 6. Files and identities

Post-fix blob identity (`git hash-object`) for the five D source files:

| File | Blob ID | Changed here |
|---|---|---|
| `__init__.py` | `55e6db94ed3327d3472af387c5f85055026fcbc0` | no |
| `eligibility.py` | `11e62e9aee9614f15293b17cc5006cb6f017e012` | **yes** |
| `errors.py` | `456a807399eb7ac1f89a1548915b0b6e1470f63e` | no |
| `model.py` | `87fa9c906d84661f94e353ce433afbe3aeb2b577` | no |
| `service.py` | `e83a054ecdff73824784b66d67e5f12048409baa` | **yes** |

The three unchanged files still carry the identities produced by the restoration; the
supervisor can compare them with the restored and PR #13 identities. The six approved test/fixture/design blobs match HEAD (`3f624b5b`).
The new implementation record is untracked under `docs/team/`; the existing approved
design records and files under `test/` are unchanged. The only other modified tracked files are the supervisor's local setup
files and the supervisor-restored ADR-001, none of which this session wrote.

## 7. ADR applicability

ADR-001 (accepted-limited-scope for D slice 1 and the stated C/B boundaries) applies and
was not modified or extended by this session. This change adds no shared contract,
permission, dependency or CI change and no new external interface, so the author assesses it as within the existing limited ADR scope.
The independent implementation/safety reviewer must confirm that applicability; this
record does not grant a new architecture approval. ADR-001 does not replace an independent source/safety review: an independent,
non-implementing human review of the implementation PR is still required, and any
freshness, concurrency or atomicity work would need its own design decision.

## 8. AI and session evidence (factual)

OpenCode desktop session, agent role `papertrace-build-D`, implementation stage. Provider
`deepseek`; model ID `deepseek-flash`; runtime label "DeepSeek V4.1 Flash 1017" as reported
by the assistant and not independently verified. Offline checks used disabled sockets and
made no PaperTrace product-model, live/network test or real semantic-evaluation
invocation; that statement does not cover the assistant's own provider traffic. The shared
`docs/ai-use-log.yaml` was not modified by this session; the supervisor reconciles
historical and current disclosures separately.

## 9. Decision log and remaining work

- 2026-11-22: implemented the previously proposed minimal design (one validation path
  returning decision plus validated tokens; public wrapper unchanged), within the
  authorized two-file scope.
- 2026-11-22: measured before/after results above; no test, fixture, configuration,
  permission or gate was changed, loosened or suppressed.

Remaining, outside this session:

- Independent supervisor verification of this local state, then a replacement
  implementation PR created from the exact approved test head branch, with
  `Test approval PR: #15` and the ADR-001 reference in its description.
- Independent human PR review; PR #15 stays open and unmerged.
- NOT_RUN here: full upstream regression beyond `test/offline`, live/network tests,
  PaperTrace product-model and real semantic evaluation, OpenCode executable E2E,
  native-engine permission E2E, and GitHub Actions.
- Future slices (C adapter, generation, freshness/`verify_current`, retries, publication,
  concurrency, atomic ledger) are not started and need their own authorization.

## 10. Supervisor verification (2026-11-22 HKT)

Codex independently inspected the two source diffs against the restored donor blobs
and reran the existing interpreter checks. It did not author or alter business code.
The public decision type, function signature, validation order and exception paths
are preserved. The draft builder accepts copied tokens and cannot re-read the
projection. All six approved test/fixture/plan blobs, the three unchanged source
blobs, restored ADR and both restricted setup hashes match the preparation manifest.

| Independently executed check | Measured result |
|---|---|
| Token regression | 23 passed |
| Original D tests | 33 passed |
| Full team offline | 412 collected; 3 failed, 407 passed, 2 skipped; no collection errors |
| Targeted Ruff / mypy / schema / tracked whitespace | PASS / PASS (10 files) / PASS / PASS |
| Full-scope Ruff | FAIL: only unchanged `scripts/paperqa_smoke.py:37` I001 |

JUnit node comparison against the supervisor's pre-fix run identifies exactly 12
failed-to-passed token cases; there are no added/removed nodes or other outcome
changes. The same three failures remain: two restricted-local-setup contract
assertions and `test_timeout_stops_owned_test_descendants` failing because sandbox
`ps` is not permitted. This differs from the coding session's two-failure result;
its passing sandbox node is not evidence that the implementation repaired it.
The two skips report the missing OpenCode executable.

The shared AI log preserves all existing entries and restores three historical
implementation/delivery/ADR disclosures from PR #13 verbatim as parsed values.
New disclosures distinguish the OpenCode implementation report from Codex
verification/packaging. Assistant-provider use is not a product-model invocation.
A local publication candidate excludes both restricted setup files and preserves
the exact approved test head ancestry and six protected blobs. There is no new
implementation commit, remote head, PR review or merge at this checkpoint.
Full upstream/live/real semantic evaluation and native OpenCode E2E remain NOT_RUN.
