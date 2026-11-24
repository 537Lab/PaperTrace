# D design record: approved-eligibility gate and pre-generation abstention (slice 1)

| Item | Content |
|---|---|
| Date | 2026-11-17 |
| Phase | **test-only**; no `src/` written |
| Status | Tests and fixtures prepared and measured locally: single file 32 failed / 1 passed (all stopping at the missing D module); awaiting a genuine GitHub approval of this test commit by a non-implementer |
| Module | D `answer` |
| Slice | approved-eligibility determination + pre-generation abstention; **no generation collaborator exists** |

## 1. Authorization boundary

This round's scope comes from the student's **self-contained message of 2026-11-17**, which explicitly states that it supersedes the earlier attachment and is "the current approval for this scope, not a reconstruction of an earlier approval, and not an approval of the test commit or of the source implementation".

Approved write paths (these four only):

- `test/offline/test_answer.py`
- `test/fixtures/answer/synthetic-corpus-a.txt`
- `test/fixtures/answer/synthetic-corpus-b.txt`
- `docs/team/designs/module-D/20261117-d-abstain-pre-generation-gate.md`

Explicitly **not** granted by this record or that message:

- No `src/` implementation is approved; this round's D behavior rules forbid writing `src/`, and tool permissions do not change that.
- No specific test commit is approved; another student who did not take part in implementing these tests must actually Approve the specific commit on GitHub.
- Dependency installation, product-model/network calls, commit, push, and merge are not approved.
- Shared contracts, dependencies, lockfiles, configuration, permissions, CI, shared fixtures, and the shared AI-use log were not modified.

## 2. Target outcome of the slice

When a researcher requests an answer for a pinned `CorpusSnapshot` and a question, D first uses a read-only review projection to decide "whether human-approved evidence with verifiable provenance exists":

- No approved evidence → return a contract-valid `abstained` draft and **never enter generation at all** (this slice has no generation port to enter).
- Approved evidence present → the pure-rule gate marks it eligible, but the service returns `failed` (`GENERATION_PATH_NOT_ENABLED`) because the generation path is not yet wired.
- Review state unreadable / projection shape bad / request scope mismatch / approved evidence not belonging to this round's snapshot → raise a D-local typed error and **construct no draft**.

What this slice does not do: no retrieval, no generation, no token budgeting, no release gate, no replay of C's ledger, and no proof of any semantic faithfulness.

## 3. Requirement and invariant trace

| ID | Testable part in this slice | Uncovered part (must not be claimed complete) |
|---|---|---|
| `FR-D-01` | Empty approved set → `abstained`, no draft leak, no generation entry | Real factory/SDK/HTTP layer count of 0 (needs the B adapter and an outbound-call spy; belongs to the integration slice) |
| `FR-D-02` | The cited set is always empty in this slice; approved IDs must belong to this round's snapshot and document version | Real raw citation parsing, freshness races during generation/before writing to disk |
| `FR-D-03` | Being eligible still does not produce a successful draft; the D package statically imports no `paperqa`/vendor SDK/HTTP stack (supplementary observation) | `aquery` arguments, pre/post, automatic evidence top-up, Agent disabling (the B adapter's responsibility) |
| `INV-01` | Zero generation with an empty approved set | Same as above; this slice has no outbound layer to count |
| `INV-04` | The three sets of `cited ⊆ sent ⊆ approved` degenerate in this slice to all-empty, or `sent=cited=∅` | Real citation mapping and the release gate |
| `COST-01` | Tests use no product model, credentials, or network; `--disable-socket` is in effect | — |

## 4. Proposed interfaces (the implementation must match these, or the tests should stay RED)

The following names are **D-local interfaces proposed by this module** and none of them is implemented yet. They are not changes to C/shared contracts.

### 4.1 `papertrace.answer.model`

```python
class AnswerRequest(BaseModel):          # frozen=True, extra="forbid"
    snapshot: CorpusSnapshot
    question_id: QuestionId
    answer_id: AnswerId
    requested_at: UTCTimestamp
    evidence: tuple[EvidenceRecord, ...]


class ReviewProjectionView(Protocol):    # structural; no isinstance checks
    snapshot_id: str
    question_id: str
    revision: int
    digest: str
    accepted_evidence_ids: Sequence[str]
    events: Sequence[object]


class ReviewProjectionPort(Protocol):
    def read_projection(self, question_id: str) -> ReviewProjectionView: ...


@dataclass(frozen=True)
class EligibilityDecision:
    eligible: bool
    approved_evidence_ids: tuple[EvidenceId, ...]
    reason: str | None


REFUSAL_NO_APPROVED_EVIDENCE = "NO_APPROVED_EVIDENCE"
REFUSAL_GENERATION_PATH_NOT_ENABLED = "GENERATION_PATH_NOT_ENABLED"
```

`QuestionId`, `AnswerId`, `UTCTimestamp`, and `EvidenceId` reuse the public type aliases from `papertrace.contracts`; no new shared definitions are added.

### 4.2 `papertrace.answer.errors`

```text
AnswerPreparationError(Exception)
├── ReviewStateUnavailableError
└── ReviewProjectionInvalidError
    ├── ProjectionShapeError
    ├── ProjectionScopeMismatchError
    ├── UnknownAcceptedEvidenceError
    └── EvidenceProvenanceError
```

### 4.3 `papertrace.answer.eligibility`

```python
def evaluate_eligibility(
    *, projection: object, request: AnswerRequest
) -> EligibilityDecision: ...
```

A pure function: no I/O, no clock, no randomness, no model.

### 4.4 `papertrace.answer.service`

```python
class AnswerService:
    def __init__(self, *, projections: ReviewProjectionPort) -> None: ...
    def prepare(self, request: AnswerRequest) -> AnswerDraft: ...
```

**Implementation details are not constrained:** this slice does not require `AnswerDraft` to be imported from any particular module, nor any monkeypatchable internal structure. "Review state unreadable" is asserted only by observable behavior: a typed error is raised and no draft is returned (see §9).

### 4.5 `papertrace.answer.__init__`

Re-export every public name from 4.1–4.4 at the top level (tests resolve them through `papertrace.answer.<name>`). If any name is missing, the tests fail with an assertion failure rather than an import stack.

## 5. Validation pipeline (order fixed)

`evaluate_eligibility` and `AnswerService.prepare` share the same order; the first failing step determines the error type and later steps are not executed.

| # | Check | Rule | Failure type |
|---|---|---|---|
| 1 | Projection readable shape | Required attributes present and not `None` | `ProjectionShapeError` |
| 1a | `revision` | `type(value) is int` (explicitly rejecting `bool`) and `>= 0` | `ProjectionShapeError` |
| 1b | `digest` | matches `^[0-9a-f]{64}$` | `ProjectionShapeError` |
| 1c | `accepted_evidence_ids` | a sequence; each item matches `^ev-[0-9a-f]{64}$`; no duplicates | `ProjectionShapeError` |
| 1d | Header IDs | `question_id` matches `^q-[a-z0-9][a-z0-9_-]{0,63}$`; `snapshot_id` matches `^snap-[0-9a-f]{64}$` | `ProjectionShapeError` |
| 1e | Empty-ledger consistency (temporary) | `revision == 0` ⇒ both `accepted_evidence_ids` and `events` are empty | `ProjectionShapeError` |
| 2 | Header scope | `projection.snapshot_id == request.snapshot.snapshot_id` and `projection.question_id == request.question_id` | `ProjectionScopeMismatchError` |
| 3 | Membership | Every accepted ID must appear in `request.evidence[*].evidence_id` | `UnknownAcceptedEvidenceError` |
| 4 | Evidence provenance | For the record corresponding to each accepted ID: `record.snapshot_id` matches; `record.document_id` belongs to that snapshot; `record.version_sha256` equals that document version | `EvidenceProvenanceError` |
| 5 | Decision | `approved` non-empty ⇒ `eligible=True, reason=None`; otherwise `eligible=False, reason=REFUSAL_NO_APPROVED_EVIDENCE` | — |

Checks this slice does **not** perform (these belong to C's authority): it does not derive accepted from `events`, does not recompute the ledger digest, does not validate `actor_kind`/`reviewer_ref`, and does not replay revision monotonicity. `digest` is checked for shape only and is trusted to come from C; this is an open integration question (see §12).

The same set of checks must be directly triggerable through the pure function `evaluate_eligibility`: the tests go through the service (checking the wrapper layer) and also call the gate directly (checking the gate itself). Service-layer checks must not mask scope/membership/provenance defects in the pure gate.

## 6. Service behavior and draft construction

1. Call `projections.read_projection(request.question_id)` **exactly once**.
2. Exceptions raised by the port **propagate as-is**; they are not wrapped or downgraded into a draft. How read errors map for dict-like/attribute-dict-like projections is still an open question.
3. `evaluate_eligibility(...)`.
4. Not eligible → `AnswerDraft(status="abstained", approved=(), sent=(), citation=(), body="", refusal_reason=REFUSAL_NO_APPROVED_EVIDENCE, ...)`.
5. Eligible → `AnswerDraft(status="failed", approved=decision.approved_evidence_ids, sent=(), citation=(), body="", refusal_reason=REFUSAL_GENERATION_PATH_NOT_ENABLED, ...)`.
6. Both paths must: `review_revision = projection.revision`, `review_digest = projection.digest` (**must not** fabricate these), `answer_id = request.answer_id`, `snapshot_id = request.snapshot.snapshot_id`, `question_id = request.question_id`, `generated_at = request.requested_at`.
7. Never set `sent_evidence_ids` / `citation_evidence_ids`; this slice has no generation, so `sent` and `cited` must be empty.
8. Add no `stale` or similar enum; `stale` is only a future blocking reason/label.

## 7. Temporary mapping to C's proposal (PR #2)

C's proposal (`ledger.projection(question_id)`, with fields `snapshot_id/question_id/revision/digest/accepted_evidence_ids/events`) **is a test proposal, not an approved or implemented interface**. This round D:

- does not import C, does not access the network, and does not depend on its module path.
- The `FakeProjection` in the tests is an explicitly temporary duck-typed stand-in whose field names mirror the proposal, so it can be remapped later.
- does not assume whether the return value is a dataclass or a dict; D only performs attribute access. If C ultimately returns a `Mapping`, an additional adaptation step is needed (open question).

## 8. Synthetic material

Both files are self-written: not real papers, not model output, and not human-approved:

| File | Bytes | SHA-256 (computed from the real bytes at test runtime) | Line 2 source text (used as the excerpt) |
|---|---|---|---|
| `synthetic-corpus-a.txt` | 139 | `c0f9f0280ad186d9e78ffe5d9c5905ce5d4bdb02c275a81c025deb30190646eb` | The synthetic resonance cell stores 12 units of daylight energy. |
| `synthetic-corpus-b.txt` | 150 | `0477e2e63c958ded9db678e78fe56e470d4b0bdf0b43b16ce1cb01299541b833` | The synthetic resonance cell releases 3 units of daylight energy per cycle. |

`DocumentVersion.version_sha256` is computed by the tests from the file bytes on the fly; `CorpusSnapshot`, `EvidenceRecord`, and `SourceLocator` are always constructed through the real shared contracts, never filled in with a random hash by hand. The fixtures' `created_at`/`retrieved_at` are pinned to `2026-11-17T00:00:00Z` to guarantee offline determinism.

## 9. Test inventory (`test/offline/test_answer.py`)

14 test functions and 33 cases in total (including parameterized expansion).

| Test | Coverage | Key assertions |
|---|---|---|
| `test_projection_without_accepted_evidence_abstains` (revision 0 / revision 3+event) | FR-D-01, INV-01 | `abstained`; all three sets empty; `body==""`; the refusal reason constant; `review_revision`/`review_digest` match the projection; `generated_at` taken from the request time |
| `test_pure_gate_marks_accepted_evidence_eligible` | FR-D-02, INV-04 | Decision `eligible=True`, approved IDs exact, `reason is None`, the decision object carries no `sent` |
| `test_pure_gate_rejects_mismatched_scope_membership_and_provenance` (6 cases) | Checks 2–4 | **calls `evaluate_eligibility` directly**; first verifies that the same input can be `eligible=True`, then asserts `ProjectionScopeMismatchError` / `UnknownAcceptedEvidenceError` / `EvidenceProvenanceError` respectively |
| `test_eligible_evidence_is_not_generated_in_this_slice` | FR-D-03 (partial) | `failed`; approved retained; sent/cited empty; reason `GENERATION_PATH_NOT_ENABLED` |
| `test_service_reads_the_projection_once_for_the_requested_question` | FR-D-01 | `reader.reads == [question_id]` |
| `test_proposed_refusal_reasons_are_stable_strings` | Contract stability | The literal values of the two constants |
| `test_unavailable_review_state_raises_without_returning_a_draft` | FR-D-01, INV-01 | Raises `ReviewStateUnavailableError`; the error message propagates as-is; does not pin down where `AnswerDraft` is imported from |
| `test_malformed_projection_raises_shape_error` (11 cases) | Check 1 | Every bad shape is preceded by a "valid projection → abstained" control, then `ProjectionShapeError` is asserted |
| `test_projection_header_scope_mismatch_raises` (2 cases) | Check 2 | The control is `failed`; wrong question / wrong snapshot asserts `ProjectionScopeMismatchError` |
| `test_unknown_accepted_evidence_raises` | Check 4 | The control is `failed`; an unknown ID asserts `UnknownAcceptedEvidenceError` |
| `test_evidence_provenance_mismatch_raises` (foreign snapshot / unknown doc / wrong version) | Checks 3, 4 | The control is `failed`; the three provenance errors assert `EvidenceProvenanceError` |
| `test_returned_drafts_round_trip_through_shared_contracts` | QA-01, INV-04 | `AnswerDraft.model_validate_json(model_dump_json()) == draft` |
| `test_static_import_scanner_flags_provider_and_network_imports` | Supplementary (anti-no-op) | Asserts on known-bad samples that the scanner returns the exact hit list, preventing the scanner from passing while doing nothing |
| `test_answer_package_has_no_direct_upstream_provider_or_network_imports` | FR-D-03 (supplementary) | AST scan of `papertrace/answer/*.py`: no `paperqa`, no vendor SDK, no direct HTTP/network stack imports |

## 10. Why the negative tests catch "a check was deleted"

- Each negative test first runs a control with **the same construction and only the target field corrected**, proving that this input could otherwise reach `abstained`/`failed`; the failure can therefore only be caused by the target check, not by a broken fixture.
- What is asserted is a **specific error type** (such as `UnknownAcceptedEvidenceError`) or a **specific decision** (`eligible is True`, the approved ID tuple), not a broad `failed` state. If the scope or membership check is deleted, the code falls through to a `failed`/`abstained` draft and `pytest.raises` fails immediately.
- Gate-level and service-level negative tests **coexist**: even if the `AnswerService` wrapper keeps the correct checks, deleting the membership/provenance checks inside the pure gate `evaluate_eligibility` is still caught by the 6 cases of `test_pure_gate_rejects_mismatched_scope_membership_and_provenance`.
- "Unreadable state" only asserts that a typed error propagates outward (and checks the error message) and does not pin down where the implementation imports `AnswerDraft` from; if the implementation swallows the error and returns a draft, `pytest.raises` fails immediately.

## 11. What is explicitly not proven

- It does **not** prove that factory/SDK/HTTP outbound attempts are 0, and does **not** complete `FR-D-01`, `FR-D-02`, or `FR-D-03`. This slice has no generation collaborator at all, so `sent=∅` is a structural fact rather than an observation of outbound calls.
- `--disable-socket` and the AST import scan are only **supplementary observations**, not proof of no outbound calls, and not a sandbox. The static scan covers `paperqa`, direct vendor SDKs (`openai`/`anthropic`/`cohere`/`mistralai`/`litellm`/`fhlmi`/`google`), and HTTP/network stacks (`httpx`/`requests`/`aiohttp`/`urllib3`/`socket`/`http.client`/`urllib.request`), but it only proves "the source text contains none of these imports", not that there are no outbound calls at runtime.
- It does not prove the authenticity of C's ledger/authority; `digest` is shape-checked only.
- It does not prove answer faithfulness, relevance, or any model quality; there are zero product-model calls this round.
- Tests passing also does not equal student test approval or implementation approval.

## 12. Open interface questions

1. **Return type of the C projection**: does `ledger.projection(question_id)` return an object or a `Mapping`? This round the tests are written for attribute access; if it is a mapping, an adaptation layer must be added, and this record and the tests should be changed first at that point.
2. **Read-error semantics**: does D propagate C's exception as-is, or require C to raise `ReviewStateUnavailableError` uniformly? The fake in this round's tests raises the D error directly, to avoid assuming C's implementation.
3. **Validation depth for `events`**: this round only requires "a sequence" that is empty when `revision == 0`; whether to validate consistency between events and accepted belongs to C's replay responsibility.
4. **`revision == 0 ⇔ empty ledger`**: this slice treats it as shape consistency; if C allows revision 0 to carry events, that rule needs re-approval.
5. **`digest` algorithm**: D does not recompute it; if D is to verify the digest independently in future, C must provide a reproducible definition (a contract-level change).
6. **Empty `request.evidence`**: currently allowed; in that case any accepted ID triggers `UnknownAcceptedEvidenceError`. Whether an earlier explicit error is needed is undecided.
7. **Duplicate `evidence_id` within a request**: not currently rejected (the shared contract's identity algorithm means a true duplicate can only come from an exactly identical source). Whether to tighten this is undecided.
8. **`answer_id` uniqueness/conflicts**: whether D or the orchestration layer is responsible is undecided.
9. **Source of `generated_at`**: this slice takes `request.requested_at`; introducing an independent clock in future requires new approval.
10. **Use of `requested_at`**: currently only used for `generated_at` and does not participate in freshness; freshness belongs to a later slice.

## 13. AI-use log (proposed entry, kept only in this record)

The shared `docs/ai-use-log.yaml` is **not modified**; this entry is only a proposal with status **awaiting shared-log editor**, and the shared-log editor decides whether to merge it.

```yaml
- entry_id: D1-TESTPREP-20261117-01
  timestamp: '2026-11-17T06:07:18Z'
  tool: OpenCode desktop session, agent role papertrace-build-D (test-preparation stage)
  model: deepseek-flash (provider deepseek; runtime label "DeepSeek V4.1 Flash 1017", not independently verified)
  purpose: offline tests, synthetic fixtures, and design record for module D slice 1 (approved-eligibility gate and pre-generation abstention); no src implementation
  scope:
  - test/offline/test_answer.py
  - test/fixtures/answer/synthetic-corpus-a.txt
  - test/fixtures/answer/synthetic-corpus-b.txt
  - docs/team/designs/module-D/20261117-d-abstain-pre-generation-gate.md
  status: test-preparation-complete-awaiting-independent-test-commit-approval
  approvals:
  - The student's self-contained message of 2026-11-17 approved the "module D test preparation only" scope; this does not constitute test-commit approval or source-implementation approval
  verification:
  - 'Local measurement (.venv, CPython 3.14.8, requirements-init.lock): single file 32 failed / 1 passed; full offline suite 32 failed / 331 passed / 2 skipped'
  - 'All 32 failures are the expected missing-implementation assertions "proposed module papertrace.answer is not implemented"; no collection error'
  - 'ruff: 1 pre-existing error in the unmodified scripts/paperqa_smoke.py (I001); mypy 0; schema PASS'
  limitations:
  - Not a non-implementer's GitHub Approve; does not prove the tests have been human-approved
  - No src/ written; shared contracts/dependencies/CI/permissions/shared fixtures/shared log unchanged
  - Downstream assertions remain unverified until implementation; merging into the shared AI-use log is pending the shared-log editor
```

## 14. Actual verification results (2026-11-17)

### 14.1 Environment (set up after separate student approval)

| Item | Value |
|---|---|
| Interpreter | uv-managed CPython **3.14.8** (downloaded 25.4 MiB) |
| venv | `.venv` (gitignored); `uv venv --python 3.14 --no-project` |
| Dependencies | `uv --no-config pip sync --python .venv/bin/python --no-build requirements-init.lock`, exit 0, 25 locked packages |
| Offline dry run | The cache lacks `librt==0.16.0` (informational; did not block installation after approval) |
| Tracked files | `git status` identical before and after setup; `git diff` empty |

### 14.2 The five approved offline commands

| Command | Exit code | Actual counts |
|---|---|---|
| `.venv/bin/python -m pytest -c papertrace.pytest.ini test/offline/test_answer.py` | **1** | collected **33**; **32 failed, 1 passed** |
| `.venv/bin/python -m pytest -c papertrace.pytest.ini test/offline` | **1** | **32 failed, 331 passed, 2 skipped** (53.04s) |
| `.venv/bin/python -m ruff check --config papertrace.ruff.toml src/papertrace test/offline scripts` | **1** | 1 error: `scripts/paperqa_smoke.py:37:1 I001` (pre-existing, unmodified file); `test_answer.py` is clean |
| `.venv/bin/python -m mypy --config-file mypy.ini src/papertrace` | **0** | `Success: no issues found in 2 source files` |
| `.venv/bin/python scripts/gates.py --gate schema` | **0** | `PASS`; `remote_enforcement: NOT_DEPLOYED_OR_VERIFIED` |

### 14.3 Failure classification

- **Expected missing implementation: 32** (31 `AssertionError` + 1 `pytest.fail`), all with the message `"proposed module papertrace.answer is not implemented"`; pytest collected 33 cases normally, so this is **not a collection error**.
- **Passed: 1**, `test_static_import_scanner_flags_provider_and_network_imports` (does not depend on the D module).
- **Environment failures: 0**.
- **Unrelated**: 2 skips (`OpenCode executable is not installed`); ruff's `I001` is in the unmodified `scripts/paperqa_smoke.py` and this slice does not fix it.
- **Still unverified**: downstream assertions (specific error types, gate decisions, draft round-trip) only really execute after implementation; the current RED only proves the implementation is missing, not that the test semantics are correct.

## 15. Information that must be checked before proposing "independent environment setup commands"

1. `.python-version` is currently `3.13`; `requires-python` is `>=3.11,<3.15`. The student must confirm whether to use 3.13 or 3.14 (`ruff`/`mypy` set `target-version`/`python_version` to 3.14).
2. The minimal dependency set for offline team tests appears to be `requirements-init.lock` (including `pytest==9.2.0`, `pytest-socket==0.8.1`, `pydantic==2.14.3`, `mypy==1.20.2`, `ruff==0.17.5`, `jsonschema`), not the full `requirements-runtime.lock` / upstream extras. Whether this is intentional needs confirmation.
3. Whether that lock stays consistent with `uv.lock`/`pyproject.toml`; installation must be a read-only reproduction such as `--frozen`/`--no-deps` and must not rewrite any lockfile (these files are in the frozen area).
4. Whether the network is available and whether pulling from PyPI (including wheel caches) is allowed; if not, the student must provide an offline wheel directory.
5. `.venv` is a local untracked directory (currently not shown by `git status`); creating it must not produce tracked files.
6. `--disable-socket` from `pytest-socket` must take effect in the offline suite; `papertrace.pytest.ini` already enables it, but this needs to be confirmed by actual measurement.
7. Whether extra dependencies are needed for the runtime sub-suite of `test/offline/test_full_regression.py`; this slice only requires `test/offline/test_answer.py` and `test/offline`.

Until items 1–7 above are confirmed by the student, no installation command is proposed or executed.

## 16. Revision record (2026-11-17, three corrections instructed by the student)

1. The static dependency check was extended from `paperqa` to direct vendor SDKs and HTTP/network stacks, and an "anti-no-op scanner" self-test was added; it still does not claim to prove zero outbound attempts.
2. Added negative tests that **call `evaluate_eligibility` directly** (1–2 cases each for scope, unknown approved, and document/version provenance), so that service-layer checks do not mask pure-gate defects.
3. Removed the monkeypatchable constraint that "`service` must import `AnswerDraft` at module top level"; "unreadable state" only asserts that a typed error propagates outward.

The three corrections do not change the interface names in §4, the validation order in §5, or the draft-construction rules in §6; the case count is updated to 14 test functions / 33 cases.


## 17. C interface check and collaboration status (2026-11-18)

This section is a supplementary record produced by a read-only Codex check of the Tencent collaboration board and GitHub; it is not an OpenCode development session, approval proof, interface-change approval, or integration-pass record. §7 and §12 keep the historical state from when the earlier proposal was formed; information about C's current candidate implementation is superseded by this section. This round's tests, source code, and shared contracts were not modified.

### 17.1 Verified sources

- Tencent shared document, section 18 task board, the "reply to D" item in Li Yuxuan's "needs coordination" row: ComparisonView fields; revision=0 and pending when there is no review record; a corrupted ledger raises ReviewLedgerCorrupted.
- Document: https://docs.qq.com/aio/DRkZieXhmaFZUc0xy
- C implementation PR: https://github.com/537Lab/PaperTrace/pull/4
- Checked source revision: 3f32f9aea3d64ef844d74b2cc2cac51e7f614d6d, src/papertrace/review/service.py. That PR is still open and is not an implementation already on main; C's tests were not independently re-run this round.

### 17.2 Alignment conclusions and open boundaries

| Item | Current candidate implementation in C | Meaning for D |
| --- | --- | --- |
| State read | ReviewLedger.projection(question_id) -> ReviewProjection; the ledger binds to a snapshot at construction | D's proposed read_projection needs an approved neutral adapter to reach projection; D does not depend directly on C's private implementation |
| Return type | A frozen dataclass object whose attributes include snapshot_id, question_id, revision, digest, accepted_evidence_ids, events | Essentially the same shape as the existing FakeProjection; "object or dict" is no longer listed as an unknown for the current candidate source, but the owner still needs to confirm a stable interface |
| No ledger file | Empty events, revision=0, accepted empty, digest computed by C's algorithm | A valid empty review state, and D should abstain; D passes the digest through without recomputing or zero-filling it |
| Corrupted ledger | ReviewLedgerCorrupted | Must not be caught and converted into an empty approved; whether to propagate or map is still to be agreed by both sides |
| Other read failures | An ordinary file read may raise OSError etc. | An I/O failure must not be passed off as "no one has reviewed"; error adaptation must be specified in a later approved scope |
| Version check | verify_current(question_id, revision, digest), failing as ReviewTokenStale / ReviewDigestMismatch | Left to a later freshness/release slice; not added to this round's implementation early |
| Comparison view | ComparisonView, containing source text, summary, state, locator, etc. | For display only; review authority is not derived from display results; D uses the trusted ReviewProjection |

This records the mapping proposal only and does not change the test semantics corresponding to §4/§5/§6. The current source propagates read-port exceptions as-is; if they later need to map to D's ReviewStateUnavailableError, the adaptation layer must be explicit, the cause preserved, and the related tests reviewed in step, with no silent modification.

### 17.3 Approval check (details still to be confirmed)

- The current head of D PR #3 is still 29b2133829666c25b42688ae7e5b42ac6130cbd8.
- GitHub reviewDecision shows APPROVED and the page shows "1 approval received". However, the REST reviews, GraphQL latestReviews, and the page expansion provide no details of the approver and the bound commit; this record neither claims there was no approval nor invents an approver/commit.
- The student who actually approved should provide the account used and a record entry/screenshot of the submitted review; independence and the exact test version must be checked before source implementation begins. Repeated approval solely to record the difference is not required.
- The body of C PR #4 and the Tencent task board still reference 92498e7, while the latest head is 3f32f9a. The C owner is advised to update the review target; D does not edit that task row on their behalf.
- Consolidating D's shared AI-use log entry is still pending; this time only the design record is updated, and the shared log, PRs, approvals, and workflows are not modified.

### 17.4 Student confirmation and verifiable status (2026-11-18, OpenCode session record)

- The student confirmed in this round's message that Li Yafei has approved the test proposal PR #3, and asked that this be recorded as "a confirmation relayed by the student", without fabricating a GitHub review URL, screenshots, or other approval evidence.
- Read-only check (`gh pr view 3`): `state=OPEN`, `reviewDecision=APPROVED`, `headRefOid=29b2133829666c25b42688ae7e5b42ac6130cbd8`, exactly matching the test commit awaiting approval; however `reviews` and `latestReviews` are both empty, and the API provides neither the approver's account nor per-review records.
- Recording stance: the **existence** of the approval is supported jointly by GitHub's aggregate state and the student's relay; **the approver's account and independence have not been independently verified through the API**. This record does not state a "named Approve verified by GitHub" and does not claim to hold screenshots.
- Implementation proceeds with slice 1 based only on that confirmation; if an auditable record binding the approver to the commit is later needed, that student still needs to supply the review entry point or a screenshot.

## 18. Implementation-session AI-use log proposed entry (2026-11-18)

The edit entry point/ownership of the shared `docs/ai-use-log.yaml` is still unresolved, so this entry is recorded **only** in this design record with status **awaiting shared-log editor**; the shared log is not modified. This entry and the test-preparation entry in §13 come from two different sessions and are neither merged nor substitutes for each other.

```yaml
- entry_id: D1-IMPL-20261118-01
  timestamp: '2026-11-17T16:47:39Z'  # local time 2026-11-18 (UTC+8)
  tool: OpenCode desktop session, agent role papertrace-build-D (source implementation stage)
  model: deepseek-flash (provider deepseek; runtime label "DeepSeek V4.1 Flash 1017", not independently verified)
  purpose: 'implement module D slice 1: read the review projection, validate eligibility, and abstain before generation; do not implement generation/release'
  scope:
  - src/papertrace/answer/__init__.py
  - src/papertrace/answer/model.py
  - src/papertrace/answer/errors.py
  - src/papertrace/answer/eligibility.py
  - src/papertrace/answer/service.py
  - docs/team/designs/module-D/20261117-d-abstain-pre-generation-gate.md
  status: implementation-complete-awaiting-pr-review-not-merged
  student_decisions:
  - The student approved this module's test-preparation scope (2026-11-17), and later approved the CPython 3.14 venv and the requirements-init.lock installation
  - 'The student confirmed that Li Yafei approved the test proposal PR #3; recorded only as relayed by the student, with no fabricated review URL/screenshot'
  - The student approved the slice 1 implementation scope and asked that the uncommitted .DS_Store deletion be kept out of the commit
  approvals:
  - 'Test commit approval: Li Yafei''s approval as relayed by the student + GitHub reviewDecision=APPROVED bound to 29b2133; per-review records unavailable (§17.4)'
  - 'Implementation scope: the student''s 2026-11-18 message; does not constitute merge approval'
  verification:
  - '.venv/bin/python -m pytest ... test/offline/test_answer.py → exit 0; 33 passed'
  - '.venv/bin/python -m pytest ... test/offline → exit 0; 363 passed, 2 skipped (the skips are the pre-existing missing OpenCode executable)'
  - 'ruff (run on the D files alone) → exit 0; the global run still fails because of the unmodified scripts/paperqa_smoke.py I001'
  - 'mypy src/papertrace → exit 0, 7 source files'
  - 'scripts/gates.py --gate schema → exit 0, PASS'
  limitations:
  - No product model was called; no new network calls were added (only the previously approved interpreter/dependency downloads)
  - 'Real C integration is unverified: C PR #4 is still open and the projection mapping is a candidate interface'
  - Generation, citation parsing, freshness/token, budget, and the release gate are all unimplemented
  - The static import scan is only a supplementary observation and does not prove zero outbound attempts
  - Merging into the shared AI-use log is pending the shared-log editor; this entry is not a shared-log record
```

## 19. CI failure attribution (2026-11-19)

| Check | PR #6 result | Attribution | Basis |
|---|---|---|---|
| schema | PASS | — | — |
| static | FAIL | Pre-existing: unmodified scripts/paperqa_smoke.py:37 I001; the other 8 sub-checks PASS | This PR's diff does not include scripts/; details from run 44283642138 |
| regression | FAIL | Pre-existing: the full upstream suite fails/times out with networking disabled, and live is not authorized | INITIALIZATION_STATUS.md lines 15, 31 |
| test-approval | BLOCKED | Missing record: GitHub reviews totalCount=0 and the timeline has no review event | PR #3 API query |
| ai-log | FAIL → fixed by this commit | Newly introduced missing item; two disclosures have been appended | This commit |
| semantic | BLOCKED | The team must settle the evaluation definition and evidence | gate summary |

This table is for attribution only and does not constitute an exemption; the pre-existing static and regression failures still block merging and must be resolved by the owner of the corresponding shared file.
