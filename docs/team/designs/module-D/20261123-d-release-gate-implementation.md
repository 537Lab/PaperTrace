# Module D design record: deterministic release gate implementation

| Item | Value |
|---|---|
| Date | 2026-11-23 |
| Phase | Source implementation (Module D, release-gate slice) |
| Status | Implementation and this record written; offline verification delegated to the supervisor; no test outcome is claimed here |
| Module | D `answer` |
| Slice | Deterministic release gate over one captured `(CorpusSnapshot, ReviewProjectionView, evidence)` bundle |
| Added source | `src/papertrace/answer/release.py` |
| Added record | `docs/team/designs/module-D/20261123-d-release-gate-implementation.md` |
| Test basis | `test/offline/test_answer_release.py`, approved at test head `f0b251fad52061a0d60e0674f078b2e63d1c81fb` |
| Plan basis | `docs/team/designs/module-D/20261123-d-release-gate-plan.md` |

## 1. Authorization and provenance supplied

The supervising student authorized this source stage after independent GitHub review
`6016556804` approved PR #24 at `f0b251fad52061a0d60e0674f078b2e63d1c81fb` on
2026-11-23 at 12:23:15 HKT. These values are recorded as supplied by the supervisor;
this session did not query GitHub or re-verify the approval.

The supervisor also reported that:

- the exact approved test head was prepared in this isolated checkout;
- the six pre-existing D source files (`__init__.py`, `c_adapter.py`,
  `eligibility.py`, `errors.py`, `model.py`, `service.py`) were restored
  byte-for-byte from the independently reviewed PR #21 commit
  `ab2df44c575536f9ef5991bc0dfb6bf42b34168c`;
- C source was checked against the same donor;
- those D/C files and all other existing files are protected from edits in this
  stage.

This record does not replace the supervisor's verification, the GitHub approval
record, or any future implementation review. ADR-001 is unchanged and remains
`proposed-awaiting-human`; this slice stays within D's existing answer/publication
responsibility and does not extend it to E persistence, B generation internals or
application orchestration.

## 2. Scope

Only two files were added:

- `src/papertrace/answer/release.py`;
- this design record.

No test, fixture, shared contract, `papertrace.answer` export, existing D/C file,
ADR, dependency, lockfile, permission, CI, workflow, Git state or shared AI-use log
was edited. The release module is imported directly by the approved test leaf; the
package export list is deliberately unchanged.

## 3. Implementation

### 3.1 D-local interface

`papertrace.answer.release` defines:

- `ReleaseInputError(Exception)`: the captured input cannot be checked safely, so
  no `ReleaseDecision` is produced;
- `CurrentPort(Protocol).read_current(question_id)` returning one captured
  `(CorpusSnapshot, ReviewProjectionView, tuple[EvidenceRecord, ...])` bundle;
- `ReleaseGate(*, current, clock).check(*, draft) -> ReleaseDecision`;
- module-level reason-code strings and an internal five-boolean flag tuple.

The gate reuses `AnswerDraft`, `AnswerRequest` and `ReleaseDecision`; it does not
add fields, enums or a second decision model. `stale` remains a blocked reason, not
a status.

### 3.2 Fixed check order and outcomes

Every returned decision is `blocked`, is bound to the validated draft's
`answer_id`, `snapshot_id`, `question_id`, `review_revision` and `review_digest`,
and uses one clock reading taken after contract revalidation.

| Stage | Outcome | Flags (snapshot/review/evidence/citation/answer) |
|---|---|---|
| Contract revalidation failure | contract `pydantic.ValidationError`; no decision | — |
| Contract-valid non-draft (`abstained`/`failed`) | `DRAFT_NOT_RELEASABLE`; port not touched | F/F/F/F/F |
| Captured bundle malformed | `ReleaseInputError`; no decision | — |
| Draft snapshot differs from captured snapshot | `SNAPSHOT_SCOPE_MISMATCH`; projection not assessed | F/F/F/F/T |
| `ProjectionScopeMismatchError` from `assess_eligibility` | `REVIEW_SCOPE_MISMATCH` | T/F/F/F/T |
| Draft revision differs from validated revision | `REVIEW_REVISION_STALE` | T/F/F/F/T |
| Draft digest differs from validated digest | `REVIEW_DIGEST_MISMATCH` | T/F/F/F/T |
| Draft-claimed record has foreign provenance | `EVIDENCE_PROVENANCE_INVALID` | T/T/F/F/T |
| Draft approved/sent sets are outside validated accepted set | `EVIDENCE_SCOPE_MISMATCH` | T/T/F/F/T |
| Citation set is empty or not a traceable subset | `NO_TRACEABLE_CITATION` | T/T/T/F/T |
| All checks pass | `PUBLICATION_COMMIT_UNAVAILABLE`; never `released` | T/T/T/T/T |

The answer flag is a draft-level precondition: it is `true` for every contract-valid
draft that reaches later stages and `false` only for a non-draft.

### 3.3 Revalidation and trust boundary

- `AnswerDraft.model_validate(draft)` is called first, including for an
  already-instantiated draft. The shared contract uses
  `revalidate_instances="always"`, so a `model_construct` instance that violates
  `valid_scope` or the declared subset relations raises the real contract
  `ValidationError` before any port read or clock read.
- The captured bundle is read exactly once through
  `read_current(question_id=validated.question_id)` and is validated as a
  three-item tuple with a `CorpusSnapshot`, a tuple of `EvidenceRecord` objects,
  and a projection object. No retry, fallback bundle, blank projection or silent
  substitution exists.
- The reconstructed `AnswerRequest` uses the captured snapshot and evidence, the
  validated draft's `question_id`/`answer_id`, and the same `decided_at` used for
  the decision.
- `assess_eligibility` is the single validation path for the captured projection.
  Its returned `revision`, `digest` and accepted membership are reused; projection
  fields are not read again. `verify_current` is not called and C's ledger is not
  imported.

### 3.4 Evidence and citation checks

- Draft-claimed evidence IDs are inspected in first-claim order across approved,
  sent and citation sets. When a claimed ID maps to a captured record, that
  record's snapshot document/version provenance must match the captured snapshot;
  otherwise the decision is `EVIDENCE_PROVENANCE_INVALID`. This check runs before
  membership so a foreign record is reported as a provenance failure rather than
  only a scope failure.
- The validated accepted set comes from
  `assessment.decision.approved_evidence_ids`. Draft approved and sent sets must be
  subsets of it; otherwise the decision is `EVIDENCE_SCOPE_MISMATCH`.
- Citation traceability requires a non-empty citation set that is a subset of both
  sent and accepted evidence; the contract already enforces `cited ⊆ sent` on any
  revalidated draft, but the check is repeated on the validated sets.

### 3.5 Exceptions

- `ProjectionShapeError`, `UnknownAcceptedEvidenceError` and
  `EvidenceProvenanceError` from `assess_eligibility` become `ReleaseInputError`
  with the original exception chained as `__cause__`.
- `ProjectionScopeMismatchError` is deliberately not an input error; it maps to the
  blocked `REVIEW_SCOPE_MISMATCH` decision.
- `PermissionError` and `OSError` from the current port, and
  `ReviewLedgerCorrupted` from a real C ledger, propagate unchanged. No ledger
  repair, retry or fallback decision is attempted.
- Malformed bundles raise `ReleaseInputError` without inventing a decision; no
  cause is required for wrong arity or wrong captured types.

## 4. Sequential snapshot limits

- The gate treats one captured bundle as final. It does not prove that A and C were
  read atomically, does not detect a change that happens after the capture, and
  does not provide a compare-and-swap, lock or release transaction.
- One clock reading is used per `check` call that returns a decision, for both the
  decision timestamp and the reconstructed request timestamp. Contract
  revalidation failure raises before the clock is read.
- A projection whose values change between reads cannot pass by accident: the gate
  does not re-read projection fields, and `assess_eligibility` itself reads each
  shape field once.
- Even when all five flags are true, D does not release. Persistence, the final
  freshness recheck and the single-writer consistency boundary remain E and
  application-orchestration work in a future approved slice.

## 5. Actual observations in this session

- Read: project instructions, the approved release plan, the approved test, the
  shared contracts, all six existing D source files (`__init__`, `c_adapter`,
  `eligibility`, `errors`, `model`, `service`), C's public review service,
  requirements/invariants/integration-contract excerpts, ADR-001 and
  relevant prior D design records.
- Observed that `assess_eligibility` already returns an `EligibilityAssessment`
  carrying the revision, digest and accepted membership validated in one pass, so
  the release gate can reuse them without a second projection read.
- Observed that `AnswerDraft` is a frozen contract with
  `revalidate_instances="always"`, and that `ReleaseDecision.consistent_decision`
  requires a reason code for every blocked outcome. The implementation relies on
  both rather than reimplementing them.
- Added exactly the two files listed in section 2. No pytest, Ruff, mypy, schema
  gate, Git or network command was executed in this session, so no pass, failure,
  collection count, byte-identity or approval result is claimed here.
- A `docs/` directory listing and `docs/architecture/` directory listing were
  denied by the native permission boundary and were not bypassed; required
  specific files were read directly. One initial blueprint read used a wrong path
  under `docs/` and was denied; the canonical root `architecture-blueprint.md` was
  then read.

## 6. Non-claims and remaining work

- No test result, independent review result, merge decision or remote CI status is
  claimed. Supervisor verification of the exact diff, tests and protected-file
  identity is separate.
- No claim is made about concurrency safety, atomic A/C capture, C ledger
  authenticity, digest recomputation, E persistence or real publication.
- The gate performs no model, provider, SDK, HTTP or PaperQA2 call and does not
  import `paperqa`.
- A future release transaction, E persistence layer or real publication path
  requires a new plan and approval; it is not a change to this matrix.

## 7. Revision record

| Date | Change |
|---|---|
| 2026-11-23 | Initial implementation record for the approved release-gate test head |
