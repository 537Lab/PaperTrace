# Module D design record: deterministic release checks (test-preparation draft)

| Item | Value |
|---|---|
| Date | 2026-11-23 |
| Phase | **Test preparation only**; no `src/` file was written |
| Status | Supervisor verified collection and prerequisite RED on both bases. Local test proposal awaiting packaging and independent approval of the exact GitHub test commit |
| Module | D `answer` |
| Slice | Release gate over one captured `(CorpusSnapshot, ReviewProjectionView, evidence)` bundle |
| Base commit | `ab2df44c575536f9ef5991bc0dfb6bf42b34168c` |
| Test file | `test/offline/test_answer_release.py` |
| This record | `docs/team/designs/module-D/20261123-d-release-gate-plan.md` |

## 1. Authorization, scope and non-goals

The supervising student approved the two-file test-preparation step for the reviewed
release-check plan. That approval covers only the two files above. It is **not** an
approval of any test commit, any `src/` implementation, any merge, or any provider/model
call.

Explicitly unchanged and outside this edit scope:

- all files under `src/`, including `src/papertrace/contracts.py`;
- existing tests, fixtures and offline configuration;
- CI, workflows, permissions, ADRs, the shared AI-use log and Git state;
- dependencies, lockfiles and any network or provider configuration.

Explicitly outside the test scope:

- B generation, raw-output parsing, citation-key mapping and pagination;
- E report persistence, history and export;
- real provider/product model invocation, delegation or network access;
- claims of an atomic A/C snapshot read or a release transaction.

No fallback implementation, `skip`/`xfail`, `sys.path` manipulation, `sys.modules`
replacement, or module import hook is used in the test process.

## 2. Target result

A researcher asks D to decide whether one already-produced `AnswerDraft` may be treated
as a release candidate for the captured snapshot and C projection. D must:

1. revalidate the draft against the shared `AnswerDraft` contract before trusting it;
2. block any structurally valid non-draft without reading A or C;
3. read exactly one captured bundle through `read_current(question_id=...)`;
4. compare the draft's snapshot identity, then run the existing
   `assess_eligibility` path over the captured C projection;
5. compare the validated review revision and digest;
6. check claimed evidence provenance and membership, then citation traceability;
7. return a `ReleaseDecision` whose check flags and reason codes state exactly what
   was verified.

Even when all five checks pass, D does **not** release. The maximum outcome in this
slice is `blocked` with `PUBLICATION_COMMIT_UNAVAILABLE`, because persistence and the
final consistency boundary belong to E and application orchestration, not to D's
release check.

## 3. Proposed D-local interface

The future public test target is `papertrace.answer.release`. These names are proposed
D-local interfaces, not a shared-contract change:

```python
class ReleaseInputError(Exception):
    """The captured input cannot be checked safely; no ReleaseDecision is produced."""


class ReleaseGate:
    def __init__(self, *, current, clock) -> None: ...
    def check(self, *, draft) -> ReleaseDecision: ...


class CurrentPort(Protocol):
    def read_current(
        self, question_id: str
    ) -> tuple[CorpusSnapshot, ReviewProjectionView, tuple[EvidenceRecord, ...]]: ...
```

The gate reuses `AnswerDraft` and `ReleaseDecision` from
`src/papertrace/contracts.py`; it does not add fields, enums or a second decision
model. `stale` remains a blocked reason, never a new `ReleaseDecision.status` value.

The reconstructed `AnswerRequest` uses:

- the captured `CorpusSnapshot` and captured evidence tuple;
- the validated draft's `question_id` and `answer_id`;
- the same fixed clock time used for `ReleaseDecision.decided_at`.

## 4. Fixed check order and result matrix

The first failing stage decides the outcome; later stages do not run. "Bundle reads"
counts calls to `read_current` for that check.

| # | Stage | Condition | Outcome | Flags (snapshot/review/evidence/citation/answer) | Bundle reads |
|---|---|---|---|---|---|
| 0 | Contract revalidation | malformed `AnswerDraft`, including an already-instantiated but malformed instance | contract `pydantic.ValidationError`; no decision | — | 0 |
| 1 | Answer gate | contract-valid `AnswerDraft` whose `status` is `abstained` or `failed` | `blocked` / `DRAFT_NOT_RELEASABLE` | F/F/F/F/F | 0 |
| 2 | Captured read | one `read_current` call using the draft's `question_id` | bundle captured | — | 1 |
| 3 | Snapshot | draft snapshot ID differs from the captured snapshot ID | `blocked` / `SNAPSHOT_SCOPE_MISMATCH` | F/F/F/F/T | 1 |
| 4 | Review scope | `assess_eligibility` raises `ProjectionScopeMismatchError` | `blocked` / `REVIEW_SCOPE_MISMATCH` | T/F/F/F/T | 1 |
| 5 | Review revision | draft revision differs from the validated projection revision | `blocked` / `REVIEW_REVISION_STALE` | T/F/F/F/T | 1 |
| 6 | Review digest | draft digest differs from the validated projection digest | `blocked` / `REVIEW_DIGEST_MISMATCH` | T/F/F/F/T | 1 |
| 7 | Evidence provenance | a draft-claimed evidence ID maps to a captured record whose snapshot/document/version provenance does not match the captured snapshot | `blocked` / `EVIDENCE_PROVENANCE_INVALID` | T/T/F/F/T | 1 |
| 8 | Evidence membership | draft approved/sent sets are outside the current validated accepted set | `blocked` / `EVIDENCE_SCOPE_MISMATCH` | T/T/F/F/T | 1 |
| 9 | Citation | citation set is empty or not a traceable subset of the sent/accepted set | `blocked` / `NO_TRACEABLE_CITATION` | T/T/T/F/T | 1 |
| 10 | All checks pass | snapshot, review, evidence and citation checks all pass | `blocked` / `PUBLICATION_COMMIT_UNAVAILABLE`; no `released` | T/T/T/T/T | 1 |

The answer flag is a draft-level precondition: it is `true` for every contract-valid
draft, including drafts that later fail snapshot, review, evidence or citation checks.
It is `false` only for a non-draft, where the earlier stages were never evaluated.

`ReleaseDecision` fields are bound to the draft under check: `answer_id`,
`snapshot_id`, `question_id`, `review_revision` and `review_digest` come from the
validated draft, so a stale decision records the revision/digest that the draft
claimed, not a later projection value.

## 5. Input errors and propagated failures

No `ReleaseDecision` is produced in these cases:

| Condition | Expected behavior | Cause chaining |
|---|---|---|
| Malformed captured bundle (wrong arity, non-snapshot, non-evidence) | `ReleaseInputError` | chained where available; not asserted for every arity case |
| `assess_eligibility` raises `ProjectionShapeError` | `ReleaseInputError` | `ProjectionShapeError` chained |
| A currently accepted ID is absent from the captured evidence tuple (`UnknownAcceptedEvidenceError`) | `ReleaseInputError` | `UnknownAcceptedEvidenceError` chained |
| Currently accepted trusted evidence has invalid provenance (`EvidenceProvenanceError`) | `ReleaseInputError` | `EvidenceProvenanceError` chained |
| The current port raises `PermissionError` or `OSError` | the same exception object propagates | unchanged |
| A real C ledger raises `ReviewLedgerCorrupted` | the same exception type propagates; the ledger file is not repaired | unchanged |

`ProjectionScopeMismatchError` is deliberately **not** an input error: it is a
review-scope mismatch and maps to the blocked decision in row 4 of the matrix.

A read failure or malformed bundle is attempted once. The gate does not retry, does
not read a second bundle, and does not silently substitute a blank projection.

## 6. Runtime negatives versus contract-revalidation negatives

The following relations can never be valid runtime inputs because `AnswerDraft`
rejects them before the gate can decide:

- `sent_evidence_ids` outside `approved_evidence_ids`;
- `citation_evidence_ids` outside `sent_evidence_ids`.

They are tested as contract-revalidation cases, including an already-instantiated
malformed draft created through `model_construct` and then passed to the gate. The
gate must raise the actual contract `ValidationError` and read zero bundles.

Runtime negatives are structurally valid drafts, including:

- a historical approved ID that remains in the draft's approved/sent sets but is no
  longer in the new trusted accepted set, with the draft's revision/digest equal to
  the new projection (evidence scope);
- a draft that claims a captured record with foreign provenance (evidence provenance);
- an explicit empty-citation draft whose evidence memberships are otherwise valid
  (citation traceability).

## 7. Test inventory

`test/offline/test_answer_release.py` defines 23 test functions; with parametrization it
defines 29 cases (authoring count, not a measured collection).

| Test | Cases | What it substantiates |
|---|---|---|
| `test_release_gate_module_prerequisite` | 1 | Only explicit prerequisite assertion for the exact missing release module |
| `test_malformed_instantiated_draft_raises_contract_validation_error` | 1 | Revalidation before any read; actual contract `ValidationError` |
| `test_legacy_answer_service_result_blocks_without_reading_current` | 2 | Real `AnswerService.prepare` abstained/failed results; `DRAFT_NOT_RELEASABLE`; zero reads |
| `test_all_checks_pass_blocks_with_publication_commit_unavailable` | 1 | Five true flags; blocked `PUBLICATION_COMMIT_UNAVAILABLE`; exact clock time; no release; no ledger write |
| `test_snapshot_scope_mismatch_blocks_before_projection_assessment` | 1 | Snapshot comparison before projection assessment; F/F/F/F/T |
| `test_projection_scope_mismatch_maps_to_review_scope_mismatch` | 2 | `ProjectionScopeMismatchError` becomes blocked `REVIEW_SCOPE_MISMATCH` |
| `test_review_revision_is_checked_before_digest` | 1 | Revision before digest; `REVIEW_REVISION_STALE` then `REVIEW_DIGEST_MISMATCH` |
| `test_historical_approved_id_outside_new_trusted_set_is_evidence_scope` | 2 | Real reset/excluded ledger state; stale approved ID; evidence check before citation |
| `test_draft_claimed_foreign_provenance_is_evidence_provenance_invalid` | 1 | Draft-claimed foreign provenance; `EVIDENCE_PROVENANCE_INVALID` |
| `test_empty_citation_is_not_traceable` | 1 | Explicit empty-citation runtime negative; `NO_TRACEABLE_CITATION` |
| `test_projection_shape_error_becomes_release_input_error` | 1 | `ProjectionShapeError` wrapped with cause |
| `test_unknown_current_accepted_id_becomes_release_input_error` | 1 | `UnknownAcceptedEvidenceError` wrapped with cause |
| `test_trusted_accepted_foreign_provenance_becomes_release_input_error` | 1 | `EvidenceProvenanceError` wrapped with cause |
| `test_malformed_bundle_becomes_release_input_error` | 3 | Wrong arity, non-evidence and non-snapshot bundles |
| `test_port_errors_propagate_unchanged` | 2 | Same `PermissionError`/`OSError` object propagates; one read |
| `test_real_corrupted_ledger_propagates_without_repair` | 1 | Real C ledger `ReviewLedgerCorrupted` propagates; bytes unchanged |
| `test_gate_does_not_retry_a_malformed_bundle` | 1 | No fallback read after a malformed bundle |
| `test_gate_uses_only_the_first_captured_bundle` | 1 | No second read for freshness; captured bundle is final |
| `test_changing_projection_exposes_duplicate_reads` | 1 | Revision, digest, accepted membership and other required attributes read once; `verify_current` not called; claims use the first validated values |
| `test_sequential_ledger_changes_do_not_mutate_returned_decision` | 1 | Two/three checks on one gate; real accept then reset; old decision unchanged |
| `test_impossible_sent_and_citation_relations_are_contract_errors` | 1 | Contract-revalidation negatives; gate revalidates and reads zero bundles |
| `test_release_module_source_does_not_import_paperqa` | 1 | Static structural supplement: no `paperqa` import in the release module source |
| `test_release_import_is_isolated_from_paperqa_in_a_fresh_interpreter` | 1 | Fresh child interpreter imports D without importing PaperQA |

The changing-projection test does not read any trap property before calling the gate.
It asserts getter counts only after the call, and it never invokes the trap's
`verify_current`; it only asserts that the gate did not call it. No test monkeypatches
`assess_eligibility` or replaces module functions; the trap is a duck-typed projection
passed through the real validation path.

## 8. Requirement and invariant mapping

Only the D-side, offline-substantiated portions are claimed.

| ID | Substantiated by this test preparation | Not claimed |
|---|---|---|
| `FR-D-01` | Non-draft/empty-approved drafts are blocked before any current read; the legacy abstained and failed results are exercised | Model factory, SDK and HTTP attempt counters; those are B/integration observations |
| `FR-D-02` | Snapshot, review revision/digest, evidence provenance/membership and citation traceability are checked; stale and mismatched cases do not release | Real generation-time race with A/C writers; raw model-output citation parsing |
| `INV-01` | D-side early stop and zero bundle read for a non-draft; no generation collaborator exists in this slice | Zero factory/SDK/HTTP attempts in a live generation chain |
| `INV-02` | Snapshot/evidence identities are used; foreign provenance is rejected; contract revalidation is exercised | A's storage, snapshot swap or actual source-file existence |
| `INV-03` | D consumes C's projection and real ledger state; no model or UI value can create an accepted set inside D | Human authenticity of C's ledger commands; that remains C's authority |
| `INV-04` | `cited ⊆ sent ⊆ approved` is enforced through contract revalidation plus D checks; freshness tokens are compared; no `released` is produced | Atomic final E commit / release transaction |
| `QA-01` | `AnswerDraft` revalidation and `ReleaseDecision` JSON roundtrip for the tested objects | Roundtrip/negative coverage for all five shared contracts |
| offline `COST-01` | No product model, credential or network call is made; the child-interpreter test observes PaperQA import isolation | A production zero-billing or zero-outbound-attempt proof |

`FR-D-03` is not claimed as complete by the static import scan. The scan is a
supplementary structural observation about D's release module source, not proof of
the B adapter's controlled generation path.

## 9. ADR-001 scope

ADR-001 is `accepted-limited-scope` for the current D slice 1, the C→D projection
boundary and the B→D generation boundary. This test-preparation draft:

- exercises only the C→D read model and D's release decision;
- does not change the ADR, the shared contracts, the B adapter or any permission;
- does not approve an implementation PR, a merge, a real provider/model call, or any
  future ADR extension;
- does not treat the student's approval of this two-file test preparation as test-
  commit approval or source-implementation approval.

The release gate is within D's existing answer/publication responsibility. The test
does not expand ADR-001 to E persistence, B generation internals, or application
orchestration.

## 10. What still requires A, C, E and application coordination

| Boundary | Still required | This test preparation does not provide |
|---|---|---|
| A | A current-snapshot pointer and an atomic snapshot read; real managed source files | Real A state; tests use synthetic captured snapshots |
| C | Authentic human ledger commands, full replay and concurrent revision changes during a check | Human approval; tests use a real synthetic ledger in `tmp_path` |
| E | Report persistence, history and the final freshness recheck under the single-writer boundary | Any persistence decision; D's maximum is blocked `PUBLICATION_COMMIT_UNAVAILABLE` |
| B | Controlled generation, raw-output/citation mapping, actual sent payload and zero-attempt accounting | Generation or pagination; outside the test scope |
| Application orchestration | Atomic A+C capture, release transaction or compare-and-swap, single-writer critical section | An atomic snapshot or release transaction; the gate checks only one captured bundle |

## 11. Verification status: measured versus delegated

This agent did **not** execute pytest, Ruff, mypy, the schema gate or any Git command
in this session. No test result, pass, collection count or exit code is claimed.

| Check | Status in this session | Notes |
|---|---|---|
| Source/document review | Performed by the agent | Read `AGENTS.md`, `Prompt.md`, module-D notes, contracts, requirements, ADR-001, integration contract, existing D/C tests and C service |
| Targeted pytest for this file | **NOT_RUN**; delegated to supervisor | Expected RED at the explicit prerequisite assertion |
| Legacy D/C regression (`test_answer.py`, `test_review.py`) | **NOT_RUN**; delegated | No source or existing-test changes in this session |
| Paired offline baseline (`test/offline`) | **NOT_RUN**; delegated | No baseline result is claimed |
| Configured Ruff | **NOT_RUN**; delegated | Test file is intentionally Ruff-shaped; not measured |
| mypy | **NOT_RUN**; unchanged `src/` | No `src/` change; not part of this delegated set |
| Schema gate | **NOT_RUN**; unchanged contract/schema | No contract or schema change; not part of this delegated set |
| Source/scope integrity | **NOT_RUN**; delegated | Only the two authorized files were written by this agent |

Delegated offline commands for the supervisor (relative to the project root):

```sh
.venv/bin/python -m pytest -c papertrace.pytest.ini test/offline/test_answer_release.py
.venv/bin/python -m pytest -c papertrace.pytest.ini test/offline/test_answer.py test/offline/test_review.py
.venv/bin/python -m pytest -c papertrace.pytest.ini test/offline
.venv/bin/python -m ruff check --config papertrace.ruff.toml src/papertrace test/offline scripts
```

The supervisor should also check that the diff contains exactly the two authorized
paths and that no `src/`, contract, CI, ADR, AI-log, permission or Git setting changed.

Some non-target reads (directory listings, a local `conftest.py` and the initialization
status file) were denied by the native permission boundary during authoring. The agent
did not bypass those denials. Neither authorized target file was blocked.

### Intended first failure

With the current base and no `papertrace.answer.release`, the first collected test,
`test_release_gate_module_prerequisite`, fails through the explicit prerequisite
assertion:

```text
expected RED: proposed module papertrace.answer.release is not implemented
(approved test-preparation stage); no fallback is used
```

Every other case fails through the same helper, not through a collection error. A
`ModuleNotFoundError` for the leaf or its `papertrace.answer` parent is the only case
converted into this explicit assertion; unrelated transitive import errors propagate.

## 12. Review notes and open decisions

1. **Evidence-stage order.** The draft matrix checks provenance of a draft-claimed
   record before membership in the current accepted set, so
   `EVIDENCE_PROVENANCE_INVALID` and `EVIDENCE_SCOPE_MISMATCH` are distinguishable.
   A reviewer should confirm this order is the intended reading of "check evidence
   then citation membership". If membership is intended first, the foreign-provenance
   runtime negative would instead return `EVIDENCE_SCOPE_MISMATCH`, and the test should
   be changed before implementation.
2. **One clock value per check.** The all-pass test asserts one clock call and the
   sequential test asserts one call per check across three checks, each with a decision
   time equal to the injected fixed clock. If the intended gate reads the clock more
   than once per check, these assertions are too strict.
3. **Decision token binding.** The tests assert that blocked decisions carry the
   draft's claimed revision/digest, not the current projection's. This is the
   contract reading of a decision bound to the specific draft.
4. **`verify_current` boundary.** D does not call C's `verify_current`; it compares the
   validated revision/digest from the one captured projection. The trap asserts this
   call count is zero. A reviewer should confirm this is the intended non-CAS scope.
5. **Fresh-interpreter isolation.** The isolation test runs a child interpreter from
   the project's `src` import root; it does not mutate the test process's `sys.path`,
   `sys.modules` or environment. It observes import-time PaperQA isolation only, not
   runtime behavior.
6. **No E persistence.** The all-pass outcome is intentionally blocked. If a later
   slice adds a release transaction, that is a new plan and new approval, not a change
   to this matrix.
7. **Decision time for early blocks.** The shared assertion helper expects every
   returned decision, including `DRAFT_NOT_RELEASABLE` and early blocked stages, to use
   the injected clock time. If a different time source is intended for non-generated
   drafts, that assertion is too strict.

## 13. Agent/model disclosure and proposed AI-use log entry

Factual disclosure:

- Tool/session: OpenCode desktop session, agent role `papertrace-build-D`
  (test-preparation stage).
- Runtime model label: "DeepSeek V4.1 Flash 1017" (provider `deepseek`; model ID
  `deepseek-flash`), not independently verified by this project.
- The agent read project documents, wrote only the two authorized files, and made no
  `src/` edit, commit, push, merge, network call, product-model call or delegation.
- The supervising student approved the two-file test-preparation step for the reviewed
  release-check plan. This is not the independent test-commit approval, does not prove
  code correctness, and does not authorize source implementation.
- The supervisor is delegated to run the offline checks; this record does not claim
  those checks were run by the agent.

Proposed entry for the shared AI-use log, **not applied**; the shared log is outside
this edit scope and awaits its editor:

```yaml
- entry_id: D-RELEASE-TESTPREP-20261123-01
  timestamp: null  # exact time not recorded; entry date 2026-11-23
  tool: OpenCode desktop session, agent role papertrace-build-D (test-preparation stage)
  model: deepseek-flash (provider deepseek; runtime label "DeepSeek V4.1 Flash 1017", not independently verified)
  purpose: Offline release-gate tests and design record for module D; no src implementation
  scope:
  - test/offline/test_answer_release.py
  - docs/team/designs/module-D/20261123-d-release-gate-plan.md
  status: local-test-proposal-verified-at-prerequisite-awaiting-exact-commit-approval
  verification:
  - Not executed by the agent; delegated to the supervisor
  limitations:
  - Not an independent test-commit approval
  - Not a real human approval, product-model evaluation or production security proof
  - No src/contract/CI/ADR/AI-log/permission/Git changes
```

## 14. Limitations and non-claims

- The test module imports only the standard library, `pytest` and `pydantic` at
  module level; all `papertrace` modules are resolved lazily inside tests, so
  collection remains safe before `papertrace.answer.release` exists.
- The supervisor measured the prerequisite RED below. Behavior verification requires
  the implementation. Independent approval applies to the exact published test commit.
- The gate checks one captured bundle. It does not prove that A and C were read
  atomically, that the bundle was fresh at the instant of a later E write, or that a
  release transaction exists.
- The real C ledger tests use synthetic reviewers, reasons and decisions. They do not
  represent a real human review or prove C's authenticity guarantees.
- The import-isolation test is a structural/supplementary observation, not proof that
  a future generation adapter makes zero outbound attempts.
- D does not produce `released` in this slice and does not decide E persistence.
- No semantic faithfulness, relevance or model-quality claim is made.

## 15. Revision record

| Date | Change |
|---|---|
| 2026-11-23 | Initial test-preparation draft: matrix, test inventory, invariant mapping, ADR-001 scope, A/C/E coordination, factual verification status |


## 16. Supervisor verification of the final test draft

The OpenCode authoring session ended before running checks. The supervisor tested SHA256
`96c744a2190afdb9e3bd90d68d171e8b65704fe882598237b1a2e422ac05e3f9` using the existing project interpreter and disabled test sockets. The
assembled base was `ab2df44c575536f9ef5991bc0dfb6bf42b34168c`. A fresh source-free
archive used `f26e4fc2768de44da556b204295c2dfa2b94f10c`.

| Check | Measured result |
|---|---|
| Full offline collection on each base | 456 collected with zero collection errors |
| Target run on each base | All 29 failed at the explicit missing `papertrace.answer.release` prerequisite |
| Assembled offline suite | 421 passed, 33 failed, 2 skipped |
| Assembled paired baseline | 421 passed, 4 failed, 2 skipped. The original 427 nodes kept the same outcomes |
| Configured Ruff on the new file | Passed on both bases |
| Full configured Ruff | Existing `scripts/paperqa_smoke.py:37` I001 |

A temporary fixture probe reached the `check` call boundary in all 26 behavior cases and
stopped there. The probe verified fixture construction. `ReleaseGate` behavior remains
unmeasured. The assembled baseline failures were four local configuration contract
assertions. HEAD, index entries and all 349 protected tracked files matched preflight.

The next reviewable delivery is a test-only commit. A student who did not implement
these tests must approve that exact commit before source implementation begins.
