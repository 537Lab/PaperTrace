# Module D design record: generation collaborator plan (test preparation)

| Item | Value |
|---|---|
| Date | 2026-11-23 (HKT) |
| Stage | **Test preparation / design only**; no `src/` was written |
| Module | D `answer` |
| Slice | Opt-in generation collaborator, B-neutral port and public-B adapter; `AnswerService.prepare` unchanged |
| Writable paths used | `test/offline/test_answer_generation.py`, this record |
| Local result | **Revision 4 supervisor measurement:** 118 collected, 3 passed and 115 failed (111 D availability, 1 B contract prerequisite, 3 runtime `lmi`). Section 17 records the full results and the source-free control. |
| Approval state | Student's 2026-11-23 "continue" authorized this precise two-file test preparation and the supervisor's isolated local setup. This is **not** an independent GitHub test approval and **not** source-implementation authorization. |

## 1. Scope and authorization boundary

This record and the test file are a **draft-only, opt-in test proposal**. They do not
change `AnswerService.prepare`, the approved slice-1 tests, shared contracts, B, C, A, E,
CI, dependencies, permissions, `__init__` exports or Git state.

The student's 2026-11-23 instruction authorized:

- generating/editing exactly the two paths above;
- running the precise offline/read-only commands listed in the supervisor handoff;
- the supervisor's isolated local assembly of the D19 source plus the four approved B
  blobs as untracked local dependencies.

It did **not** authorize source implementation, commits, pushes, PR creation or approval,
merges, installs, credentials, live/provider calls, or shared-log edits. The four B blobs
are supervisor-local readonly dependencies, not student-authored changes or new commits.
The source-free publication tree for the future test commit remains separate and
unchanged; the earlier PR20 approval covers C integration tests, **not** this generation
test proposal.

## 2. Target API freeze (proposed, currently absent)

The coordinator and adapter do not exist yet. Tests resolve them at execution time from
the submodules, so no `papertrace.answer.__init__` change is required and a checkout
without them still collects.

### 2.1 `papertrace.answer.generation`

All data models are frozen, closed (`extra="forbid"`), and strict where noted.

```python
class GenerationPolicySpec(BaseModel):
    provider: str                         # strict nonblank
    model: str                            # strict nonblank
    max_input_tokens: int = 12000         # strict int, 1..12000
    compress_at_tokens: int = 9000        # strict int, 1..min(9000, max_input_tokens)
    max_output_tokens: int = 2000         # strict int, 1..2000
    max_sources: int | None = None        # strict int >= 1 when set
    get_evidence_if_no_contexts: bool = False   # exactly False
    pre_prompt: None = None                     # exactly None
    post_prompt: None = None                    # exactly None
    autonomous_agent: bool = False              # exactly False

class AnswerGenerationRequest(BaseModel):
    base: AnswerRequest
    question_text: str                    # strict nonblank
    selected_evidence_ids: tuple[EvidenceId, ...]   # unique
    policy: GenerationPolicySpec

class GenerationCallRequest(BaseModel):   # B-neutral; deliberately no question_id
    snapshot: CorpusSnapshot
    question_text: str
    approved_evidence: tuple[EvidenceRecord, ...]   # approved only, projection order
    selected_evidence_ids: tuple[EvidenceId, ...]   # unique
    review_revision: int                  # strict, >= 0, not bool
    review_digest: str                    # 64 lowercase hex
    policy: GenerationPolicySpec

class GenerationCallResult(BaseModel):
    status: Literal["REFUSED", "SUCCESS", "AMBIGUOUS_CITATIONS"]
    raw_output: str
    sent_evidence_ids: tuple[str, ...]
    citation_aliases: tuple[tuple[str, str], ...]   # (model key, evidence id)
    unknown_citation_keys: tuple[str, ...]
    ambiguous_citation_keys: tuple[str, ...]
    refusal_reason: str | None
    invalid_sent_evidence_ids: tuple[str, ...] = ()  # D-internal diagnostic only

class GenerationPort(Protocol):
    def call(self, request: GenerationCallRequest) -> GenerationCallResult: ...

class AnswerGenerationOutcome(BaseModel):
    draft: AnswerDraft | None
    reason: str | None
    revision_before: int | None
    revision_after: int | None
    digest_before: str | None
    digest_after: str | None
    sent_request: GenerationCallRequest | None
    result: GenerationCallResult | None
    raw_unknown_keys: tuple[str, ...]
    truncation: Literal["unknown"] = "unknown"
    question_id: QuestionId
    question_text: str

class AnswerGenerationService:
    def __init__(self, *, projections: ReviewProjectionPort,
                 generation: GenerationPort) -> None: ...
    def run(self, request: AnswerGenerationRequest) -> AnswerGenerationOutcome: ...

def extract_citation_keys(raw_output: str) -> tuple[str, ...]: ...
class GenerationResultShapeError(Exception): ...
```

Frozen decisions:

- `GenerationCallResult` is **permissive about cross-field semantics and uniqueness**.
  The adapter validates external type shape; the coordinator validates set relations and
  reconciliation. Tests construct inconsistent typed results to reach those checks.
- The outcome has **no usage field and no release/save field**. Usage is unavailable for
  this slice; truncation is always `"unknown"` because no evidence exists. Diagnostic
  `AnswerDraft.status` is not a `ReleaseDecision`.
- Handled outcomes carry an `AnswerDraft` with status `draft`/`abstained`/`failed`.
  `draft=None` is not produced by these tests; assessment exceptions propagate instead.
- `outcome.reason` equals `draft.refusal_reason` for non-success and is `None` for
  success. Key diagnostics use an explicit partition: resolved alias keys (key → sent
  evidence), reported ambiguous keys, and genuinely unknown extracted keys. Unknown and
  ambiguous sets must be disjoint; their union with resolved alias keys must equal the
  keys extracted from raw output. `raw_unknown_keys` is exactly the genuinely unknown
  extracted keys (ordered, deduplicated), excluding resolved and ambiguous keys; the
  complete raw unknown/ambiguous lists stay in `outcome.result`. Overlap or disagreement
  is `RESULT_SHAPE_INVALID`; it is never filtered into success.
- Distinct alias keys may target the same sent evidence. `AnswerDraft.citation_evidence_ids`
  deduplicates resulting evidence identities while `outcome.result.citation_aliases`
  preserves every raw key → evidence mapping. Repeated alias targets are valid; repeated
  alias keys are invalid.
- **Confirmed B invalid-sent contract (user handoff, not a GitHub approval):**
  `GenerationStatus.INVALID_SENT_EVIDENCE`, `sent_evidence_ids=()`, empty citation
  mapping, and `invalid_sent_evidence_ids` carried with the B result to D for internal
  diagnostics. The adapter maps it to
  `GenerationCallResult(status="REFUSED", refusal_reason="INVALID_SENT_EVIDENCE",
  sent_evidence_ids=(), citation_aliases=(),
  invalid_sent_evidence_ids=<exact reported IDs>)`. D returns a failed
  `GENERATION_REFUSED` draft with empty body/sent/citations. The invalid IDs remain on the
  D-internal result/outcome; they are never added to the shared `AnswerDraft` and no
  E/publication interface is introduced.
- The call request stores approved records only. The question id stays in D's outer
  request/outcome; B receives `question_text` as `GenerationRequest.question`.
  Approved records follow the projection's accepted-ID order; selected ids follow the
  call request's order. `AnswerDraft.approved_evidence_ids` uses the same projection
  order, and cited ids are deduplicated in alias order.
- The id↔text association is a trusted-caller precondition, not authenticated by the
  frozen request. C does not store question text, so D cannot re-derive it.

### 2.2 `papertrace.answer.b_gateway_adapter`

Proposed public class `BGatewayGenerationAdapter(gateway=...)` implements
`GenerationPort`. It imports `papertrace.retrieval.gateway` **inside `call`** (no
module-scope B or `paperqa` import), converts policy field-by-field (no `getattr`
passthrough), builds the B request with `question=request.question_text`, and converts
B's `GenerationResult` explicitly:

- known `GenerationStatus` members are recognized by enum identity and mapped to D
  literal strings; a plain string, a foreign enum, or any unknown value raises
  `GenerationResultShapeError` — never stringified into success;
- the confirmed `GenerationStatus.INVALID_SENT_EVIDENCE` member maps to D `REFUSED` with
  `refusal_reason="INVALID_SENT_EVIDENCE"`, empty `sent_evidence_ids`/`citation_aliases`,
  and the reported IDs in the D-internal `invalid_sent_evidence_ids` tuple; the local B16
  donor lacks this member/field, so the B Gateway-to-D case is a B-contract prerequisite
  test, not a faked status;
- `raw_output` must be `str`; evidence-id and key fields must be non-`str`/non-`bytes`
  sequences of `str` without duplicates; alias entries must be two-item pairs with unique
  keys and string targets; `refusal_reason` must be `str | None`;
- malformed external data raises `GenerationResultShapeError`, which the coordinator maps
  to a failed `RESULT_SHAPE_INVALID` outcome. Other port exceptions propagate unchanged.

### 2.3 Unchanged legacy surface

`AnswerService.prepare`, `assess_eligibility`, `evaluate_eligibility` and
`EligibilityDecision` keep their exact current semantics. The legacy controls observe one
projection read and the exact old output/tokens; they do not inject or observe a
generation port, so they do not claim a measured zero generation-call count. The new
entry point is a separate class.

## 3. Run pipeline and reason codes

### 3.1 Fixed order

1. **Typed construction.** Invalid policy, generation request or call request raises
   `pydantic.ValidationError` before `run`; a service/port/reader is never invoked.
   This covers strict ranges, bool-as-int, reversed caps, `max_sources=0`, safety
   switches that are not exactly `False`/`None`, blank strings, duplicate selected IDs,
   coerced/non-string identifiers, extra fields, and a `question_id` on the B-neutral
   call request.
2. **Pre-call assessment.** Read the projection once; `assess_eligibility` performs the
   existing scope/membership/provenance checks. These errors propagate unchanged.
3. **Pre-call gates with zero port calls.** No approved evidence → abstained
   `NO_APPROVED_EVIDENCE`; empty selection → abstained `EMPTY_SELECTION`; selection not a
   subset of approved → failed `SELECTION_OUTSIDE_APPROVED` (never intersected).
4. **One controlled call.** Build the call request from approved records, selected IDs,
   T0 revision/digest and the policy, then call the port exactly once.
5. **Result validation** in this order: runtime type; field shape/uniqueness/blank
   checks; status/refusal consistency; `sent ⊆ approved`; `sent ⊆ selected`;
   `cited ⊆ sent`; D-extracted key reconciliation (resolved keys ∪ unknown ∪ ambiguous
   must equal extraction, pairwise disjoint); unknown keys; ambiguous keys; SUCCESS
   raw nonblank. Malformed reported sets fail; nothing is silently filtered.
6. **Post-call assessment.** A new projection read/assessment gives T1. T1 ≠ T0 → failed
   `STALE_REVIEW_DURING_GENERATION`. Assessment errors propagate unchanged.
7. **Draft construction.** Success requires a nonzero review revision, nonempty
   approved/sent/body and a subset-consistent cited set. Cited evidence identities are
   deduplicated for `AnswerDraft`; raw unknown/ambiguous keys stay in diagnostics.
   No release decision is produced.
8. **Confirmed invalid-sent result.** The adapter's D-neutral `REFUSED` result with
   `refusal_reason="INVALID_SENT_EVIDENCE"` yields a failed `GENERATION_REFUSED` draft
   with empty body/sent/citations. `outcome.result.invalid_sent_evidence_ids` retains the
   exact reported unauthorized IDs; `AnswerDraft` never carries that field.

### 3.2 Reason vocabulary

| Reason | Draft status | Meaning |
|---|---|---|
| `NO_APPROVED_EVIDENCE` | `abstained` | approved projection is empty |
| `EMPTY_SELECTION` | `abstained` | caller selected no evidence |
| `SELECTION_OUTSIDE_APPROVED` | `failed` | selection is not a subset of approved |
| `STALE_REVIEW_DURING_GENERATION` | `failed` | post-call revision/digest differs |
| `GENERATION_REFUSED` | `failed` | B returned a refusal status with a reason |
| `EMPTY_OUTPUT` | `failed` | SUCCESS text is empty/whitespace |
| `RESULT_SHAPE_INVALID` | `failed` | non-result object, shape error, duplicate/blank field, status/reason inconsistency, extraction disagreement, or overlapping unknown/ambiguous categories |
| `UNKNOWN_CITATIONS` | `failed` | consistently reported unknown keys (D is stricter than B's SUCCESS) |
| `AMBIGUOUS_CITATIONS` | `failed` | consistently reported ambiguous keys |
| `SENT_OUTSIDE_APPROVED` | `failed` | reported sent is outside approved |
| `SENT_OUTSIDE_SELECTED` | `failed` | reported sent is approved but not selected |
| `CITATION_OUTSIDE_SENT` | `failed` | alias target is outside reported sent |

Failure checks are ordered `sent ⊆ approved` before `sent ⊆ selected`, so an
approved-but-unselected sent yields the more specific `SENT_OUTSIDE_SELECTED`, while a
foreign id yields `SENT_OUTSIDE_APPROVED`.

### 3.3 Tokens and draft diagnostics

- Pre-call outcomes: `revision_before`/`digest_before` are T0; after is `None`;
  `sent_request`/`result` are `None`.
- Post-call outcomes: before T0, after T1.
- Success drafts use T0 (equal to T1). Stale failed drafts use T1. Other call-time
  failures use T0 (equal to T1 in the controls).
- `test_gn_d08_run_reuses_the_validated_first_read_tokens` uses a trap projection whose
  first read is valid and whose later read differs, proving `run` does not re-read
  revision/digest and produces no false stale result.

## 4. Citation-marker grammar (proposed interoperability convention)

This is **not a finalized B/D contract**. The current approved B concrete bridge parses
parenthesized citation tokens and produces aliases such as `b1`; the D parser mirrors
that convention for the synthetic fixtures:

1. A citation marker is a parenthesized group with no nested parentheses:
   `\(([^()]*)\)`.
2. Inside a group, strip surrounding whitespace and split on one or more of space, comma
   or semicolon: `[\s,;]+`.
3. Drop empty tokens; deduplicate keys preserving first occurrence.
4. An unclosed parenthesis is not a marker. An empty group contributes no key. A nested
   expression such as `((b1))` yields the inner `b1`.

Paired controls in the test:

| Control | Input | Expected |
|---|---|---|
| single | `The cell stores 12 units (b1).` | `("b1",)` |
| comma / space / semicolon | `(b1, b2)`, `(b1 b2)`, `(b1;b2)` | `("b1", "b2")` |
| adjacent | `(b1)(b2)` | `("b1", "b2")` |
| duplicate | `(b1) and (b1)` | `("b1",)` |
| ordinary prose parentheses | `The value (see Figure 2) is synthetic.` | `("see", "Figure", "2")` |
| empty / spaces-only | `()`, `(   )` | `()` |
| malformed citation-like | `(b1` | `()` |
| plain prose | no marker | `()` |
| nested | `((b1))` | `("b1",)` |

The ordinary-prose row is deliberately a **negative/limit** control: the broad grammar
cannot distinguish prose parentheses from citations, so such text fails closed unless B
reports the same keys. This usability/contract risk is a B-owner decision, not a claim
that the grammar is final.

## 5. Test matrix and actual reach

All tests are in `test/offline/test_answer_generation.py`; 118 drafted cases in total.
Revision 4 adds two cases. Both were executed by the supervisor and stopped at their
respective prerequisites. See section 17. The prior 111-, 115- and 116-case revisions were intentionally extended;
see sections 13, 15 and 16 for the deltas.

| ID | Tests / cases | Level | Covered behavior | Not claimed |
|---|---|---|---|---|
| GN-D-01 | `test_gn_d01_...` 3 cases (no review, all pending, all excluded) | L1 | zero port calls; abstained `NO_APPROVED_EVIDENCE`; empty body/sent/cited; T0 tokens | SDK/HTTP accounting |
| GN-D-02 | `test_gn_d02_...` 1 case | L1 | zero calls; abstained `EMPTY_SELECTION` | same |
| GN-D-03 | `test_gn_d03_...` 2 cases (unaccepted supplied, foreign id) | L1 | zero calls; failed `SELECTION_OUTSIDE_APPROVED`; no intersection | C ledger authenticity |
| GN-D-04 | 23 invalid policy cases, 5 valid boundaries/defaults, 4 invalid requests, 6 invalid call requests, 1 no-question-id check | L1/API | `ValidationError` before run; zero reads/calls; strict ranges/switches and non-string identifiers; B-neutral request | compression/reinjection |
| GN-D-05 | single success; multiple approved with nonempty proper-subset selection; two distinct alias keys to one sent evidence; 12 parser cases; module-import guard | L1 | exactly one call; exact snapshot/text/T0/approved/selected; `sent ⊆ selected ⊆ approved`; `cited ⊆ sent`; two-alias mappings preserved while draft cited IDs dedupe; body = raw; parser grammar | semantic support |
| GN-D-06 | 13 malformed/inconsistent result cases + non-result object + 5 pre-call assessment error cases | L1 | distinct failure reasons; unknown/ambiguous partition and overlap rejection; raw unknown keys retained; ambiguous keys retained in result; no filtering into success; scope/provenance/ledger errors propagate unchanged | B internals |
| GN-D-07 | 4 status cases + invalid-sent neutral-port case + port exception + adapter shape error | L1 | one call/no retry; refused/empty/ambiguous mapping; confirmed invalid-sent result → failed `GENERATION_REFUSED` with invalid IDs retained internally; generic exceptions propagate | timeout policy ownership; release gate |
| GN-D-08 | stale revision/digest; 3 propagating assessment errors; first-read trap | L1 | failed `STALE_REVIEW_DURING_GENERATION`; no draft body; unchanged exception propagation; token reuse | A pointer freshness, save atomicity |
| GN-D-09 | 2 legacy `prepare` cases | L1 | exact old abstained/not-enabled output/tokens and one projection read; no generation port injected or observed | generation completion, zero-call counting |
| GN-D-10 | real B Gateway + fake factory/session; 3 enum mapping controls; two-alias conversion; mixed known/unknown bridge-boundary failure; B invalid-sent contract-prerequisite case; 12 malformed external results; adapter import guard | L2a/adapter-unit/bridge-boundary | field-by-field conversion; `factory.create` invocation; B-reported sent/aliases; two-alias preservation; mixed known+unknown output fails `UNKNOWN_CITATIONS` with raw/unknown diagnostics retained; actual B types inspected for `INVALID_SENT_EVIDENCE`/`invalid_sent_evidence_ids`; explicit enum/type validation; lazy B import | concrete bridge serializer/count_tokens; local B16 donor lacks confirmed invalid-sent fields; release/save gate |
| GN-D-11 | at-cap/over-cap; repeated fresh sessions and Docs/session identity | L2b | final-prompt count gate before `aquery`; pending/excluded text absent; actual PQASession and factory-returned session objects must be distinct | real provider/tokenizer/semantic; runtime dependency must be available |
| GN-D-12 | static self-check | instrument | source-free collectability; no skip/xfail/global substitution | actual publication-base run |

Instrument controls: each negative has a positive control (valid policy, valid result,
valid status, success path); GN-D-12 checks that the test module does not import the
proposed D/B modules at module scope and does not define substitutes for the proposed
symbols. The static check is not an OS sandbox.

## 6. Integration levels and honest observability

| Level | What it proves | What it does not prove |
|---|---|---|
| L1 (D + fake port) | D's port-call count, exact request, own validation/reconciliation and draft mapping | anything about B internals, serialization, SDK, HTTP |
| L2a (real B Gateway + fake factory/session) | public conversion, `factory.create` invocation, B-reported sent/aliases, two-alias preservation, explicit enum/type mapping | the concrete bridge, token counting, wire traffic |
| L2b (real B bridge + fake Docs/models/`count_tokens`) | bridge's final-prompt cap gate and `aquery` boundary, fresh Docs and actual PQASession/factory-wrapper identity per ask, payload exclusion | real provider behavior, real tokenizer accuracy, semantic quality; the runtime `paperqa.types` import must succeed first |

`Gateway + arbitrary fake factory` is deliberately **not** described as the concrete
bridge test. A fixture-created factory object is not evidence of `factory.create`
invocation; the L2a test counts the invocation separately. The GN-D-10 enum/type
rejection, two-alias conversion and mixed known/unknown cases use a stub gateway
returning crafted B dataclasses; they exercise the adapter's explicit conversion (and,
for the mixed case, the adapter→D service boundary), not the real B Gateway. Only the
main conversion case uses the real B Gateway plus a fake factory/session. Zero L1 port
calls are not measured SDK/HTTP accounting. `--disable-socket` is a supplement, not
proof.

The L2b prerequisite is a **runtime import** of `paperqa.types` followed by a check for
`Doc`, `Text`, `Context` and `PQASession`. Discovery is not enough. A transitive failure
such as `ModuleNotFoundError(name="lmi")` is left uncaught and classified as a runtime
dependency/environment blocker, not a D behavior RED or an availability success. When it
fails, L2b behavior and the session-identity assertions are **NOT_REACHED**.

## 7. Requirements and invariant mapping (corrected)

| ID | Covered here | Not covered / correction |
|---|---|---|
| `FR-D-01` | empty approved/selection → abstained, zero port calls (L1) | SDK/factory/HTTP layer counts need B/adapter integration; not claimed |
| `FR-D-02` | citation structure, `cited ⊆ sent ⊆ approved`, post-call review-token freshness, confirmed invalid-sent diagnostic retained internally | review-token freshness maps to `FR-D-02`/`INV-04`; A's current-snapshot pointer and save atomicity are not tested; invalid IDs are not in `AnswerDraft` |
| `FR-D-03` | one controlled call through a B-neutral port; public-B adapter conversion; lazy B import | full four-layer outbound accounting and provider/model binding are not claimed |
| `INV-01` | zero port calls for empty approved/selection | not SDK/HTTP proof |
| `INV-03` | selection must be inside the approved projection; no intersection | C ledger authenticity is C's authority |
| `INV-04` | three-set relation and review revision/digest comparison around one call | not publication/save atomicity |
| `INV-05` | **not claimed** | `INV-05` belongs to E's append-only historical research records; this D slice does not verify it |
| `INV-07` | partial: strict policy bounds and the bridge's final-prompt cap observation | compression trigger behavior, constraint reinjection, model-window certification and exact tokenizer accuracy are deferred |
| `COST-01` | these offline checks make no PaperTrace product LLM call | does not claim the development assistant made zero provider requests |

No complete release, four-layer outbound or semantic certification is claimed. A
nonempty `AnswerDraft` is diagnostic, not a release decision.

## 8. B-owner open checklist and observed conflict

| Item | Status |
|---|---|
| `Gateway.generate(request) -> GenerationResult`; import path | confirmed in the approved B source |
| `GenerationRequest` fields (`question`, review tokens; no question id) | confirmed |
| `GenerationPolicy` fields/defaults and three disable switches | confirmed |
| Result exposes status/raw/sent/aliases/unknown/ambiguous/refusal | confirmed |
| Upstream imports dynamic inside execution | confirmed in B |
| Usage, attempt counts, finish/truncation, request id | absent; B decision + B-owned ADR path |
| Provider exception/timeout retry/fallback policy | open; B decision needed |
| Fresh session per call | observed behavior in the bridge; B to confirm the guarantee; L2b records actual PQASession and factory-returned wrapper identity for the repeated-run control |
| Citation-marker syntax D should parse | B confirmed `(b1)` and `(b999)` examples. Broader grammar in section 4 remains proposed. |
| `INVALID_SENT_EVIDENCE` wire fields | **user-confirmed:** enum member, `sent_evidence_ids=()`, empty citation mapping, `invalid_sent_evidence_ids` carried to D. Local B16 donor lacks the member/field and filters; B Gateway-to-D test is **B contract prerequisite RED**, not D behavior. No B patch. |
| `count_tokens` on the final prompt before `aquery` | confirmed in the concrete bridge; reachability only at L2b, blocked by the runtime `lmi` import here |

**Observed conflict (do not change B here).** The confirmed invalid-sent contract
specifies a terminal `INVALID_SENT_EVIDENCE` result with empty normal sent and citation
mapping. The local B16 donor lacks that member/field and its `run_generation` still
filters a reported `sent_evidence_ids` tuple to the selected set:
`final_sent = tuple(id for id in reported_sent if id in selected_set)`. The supervisor's
real B16 Gateway probe confirmed that metadata loss (it does not prove text leakage). D's
L1 contract requires rejecting malformed reported sets, but at L2a D cannot observe what
the old donor has already filtered. The B Gateway-to-D test is therefore a narrow B
contract-prerequisite assertion, not a reason to fake or patch B. This slice does not
modify B or shared contracts and does not assert the old filtering as desired behavior.

Secondary B notes: B's citation resolver ignores non-`str`/blank claim keys and can
return `SUCCESS` with unknown keys, while D intentionally fails on unknown keys; alias
keys are unique in the bridge but fake results can violate that, so the adapter validates
uniqueness. These are recorded as observations, not changes.

**Stop condition.** The invalid-sent wire fields and two citation examples are confirmed.
The local B16 donor lacks the new fields. A compatible B donor is needed to exercise the
real gateway case. Broader citation grammar remains proposed and should be reviewed
before freezing the generation test commit.
The earlier PR20 C-integration approval does not cover this generation test commit. No
B/source/shared-contract change is authorized here.

## 9. Historical revision 3 verification (2026-11-23 HKT)

Environment: the supervisor-provided existing project interpreter (CPython 3.14.8,
pytest 9.2.0, pydantic 2.14.3). No new virtual environment, install, symlink or
configuration change was made. Commands were the exact approved offline commands.

**Measurement boundary:** the table below is the last measured revision-3 run. Revision 4
adds two draft cases; per this handoff they were **not executed locally**. Their expected
prerequisites are recorded in section 16 and remain for supervisor measurement.

| Check | Exit | Actual result |
|---|---|---|
| `--collect-only` new file | 0 | **116 tests collected**, no collection error |
| new file execution | 1 | **113 failed, 3 passed**; 0 errors/skips. Of the 113: **110 availability assertions** for absent `generation`/`b_gateway_adapter` and **3 runtime dependency failures** in L2b (`ModuleNotFoundError: No module named 'lmi'`). The 3 passes are 2 legacy `prepare` controls and the static self-check. |
| old D files (`test_answer.py`, `test_answer_validated_tokens.py`) | 0 | **56 passed** |
| full `test/offline` | 1 | **528 collected (412 baseline + 116 new); 117 failed, 409 passed, 2 skipped**; 0 errors |
| paired baseline (`--ignore` new file) | 1 | **412 collected; 4 failed, 406 passed, 2 skipped**; 0 errors. Delta is 110 availability + 3 runtime `lmi` failures + 3 passes. |
| revision 4 new cases | — | Outside this revision 3 run. See section 17 for the supervisor run. |
| new-file Ruff | 0 | all checks passed |
| targeted Ruff (D+B sources + old D tests) | 0 | all checks passed |
| full configured Ruff | 1 | only the unchanged `scripts/paperqa_smoke.py:37` `I001`; no finding in the new file |
| mypy `src/papertrace` | 0 | 14 source files, no issues |
| schema gate | 0 | `PASS`; `remote_enforcement: NOT_DEPLOYED_OR_VERIFIED`; other gates `NOT_RUN` |
| `git diff --check` | 0 | covers tracked setup configs only; **new untracked files are not covered** |
| `git diff --stat` / `--name-only` | 0 | only the supervisor's two setup configs |
| `git status --short` (final sample) | 0 | two modified setup configs, the supervisor's untracked B dependency directory, and both untracked delivery files (this test file and this record). The command sample is not the delivery itself; both new files remain uncommitted and the supervisor packages them later. |

Timing note: the status row above is the **final** sample after this record and the test
file both existed. The earlier-preparation status sample was taken while this record was
still being written, so it listed only the test file among the two deliverables. The
final delivery consists of exactly the two named untracked files; the supervisor's setup
files and B dependency directory are not part of it.

Historical note: the prior 111-case run reported 108 availability failures. That
measurement predates the corrected runtime `paperqa.types` import check and is **not**
retroactively relabeled; the current 113 failures include the 3 runtime `lmi` failures
that the earlier check did not reach.

Failure classification:

- **110 availability/prerequisite RED**: proposed coordinator/adapter modules are absent;
  no behavior was reached. The new mixed-citation bridge-boundary regression is in this
  group: it stops at the missing adapter before any assertion. These are not collection
  errors, skips or xfails.
- **3 runtime dependency/environment failures**: L2b reached the real
  `paperqa.types` import and failed with `ModuleNotFoundError(name="lmi")`. This is not a
  D behavior RED, not an availability success, and not evidence that the bridge ran. No
  install/repair was attempted; L2b behavior and session-identity assertions are
  **NOT_REACHED**.
- **No reached behavioral RED** for the proposed coordinator: the source does not exist
  in this checkout, so the new tests did not execute its behavior.
- **3 passes**: 2 reached legacy `AnswerService.prepare` behaviors and 1 static
  instrument check. They do not exercise the proposed coordinator.
- **4 baseline failures**: the known local configuration-contract nodes that expect broad
  D source/test write grants, intentionally restricted by the supervisor's local setup.
  They are not generation RED and were left visible.
- **2 skips**: OpenCode executable unavailable.
- The sandbox `ps` failure reported in an earlier supervisor run did **not** occur in this
  session; that result is environment-dependent and is not relabeled.
- No source implementation, assembly commit, commit/push, PR, approval, merge or
  publication was performed.

Section 17 records the later supervisor run and the prerequisites reached by both new cases.

## 10. Limits and non-claims

- Not a GitHub Approve; not implementation authorization; not a merge/publication
  decision.
- Only `test/offline` was run. Full upstream regression, live/network tests, real
  provider/model calls, real semantic evaluation, OpenCode executable E2E, GitHub
  Actions and remote enforcement were **NOT_RUN**.
- The L2b fake Docs/models are not an actual frozen-upstream/provider run. The fake
  `count_tokens` tests the bridge's comparison, not tokenizer accuracy. L2b never reached
  behavior here: the corrected runtime `paperqa.types` import failed with
  `ModuleNotFoundError(name="lmi")`. No install or source substitution was attempted.
- The 110 availability RED results from the last measured revision 3 do not reproduce a
  behavior defect; they only prove the proposed modules are absent and the file collects
  normally. The new mixed-citation bridge-boundary regression specifically did not execute
  its assertions. The 3 L2b failures are a runtime dependency/environment blocker, not D
  behavior evidence.
- Revision 4 adds a D-only fake-neutral-port invalid-sent case and a B Gateway-to-D
  contract-prerequisite case; **neither was executed locally this turn**. The local B16
  donor lacks the confirmed enum/field, so the latter is expected B contract prerequisite
  RED; the D-only case is expected D implementation availability RED until the proposed
  D model/service exists.
- No source implementation or B patch is claimed; the confirmed invalid-sent fields exist
  only as the draft test target.
- `INV-07` coverage is partial; compression/reinjection/window certification is deferred.
  `INV-05` is not claimed.
- The citation grammar is a proposed interoperability convention pending B-owner
  confirmation; the B sent-metadata normalization conflict is reported, not resolved.
- No absolute host paths, credentials, private data or shared AI-use log content are
  included here.

## 11. Proposed AI-use disclosure (not written to the shared log)

```yaml
- entry_id: D1-GENERATION-TESTPREP-20261123-01
  revision: 4
  timestamp: '2026-11-23T01:46:00+08:00'
  time_basis: supervisor handoff update time; revision time is not a measured session clock
  tool: OpenCode desktop session, agent role papertrace-build-D (test-preparation stage)
  model: deepseek-flash (provider deepseek; runtime label "DeepSeek V4.1 Flash 1017", not independently verified)
  purpose: Two-file draft revision for the confirmed B invalid-sent contract and proposed D-neutral mapping; no src implementation, no B patch
  scope:
  - test/offline/test_answer_generation.py
  - docs/team/designs/module-D/20261123-d-generation-collaborator-plan.md
  status: local-draft-revision-4-pending-supervisor-measurement
  approvals:
  - Student 2026-11-23 instruction authorized this precise two-file draft revision and supervisor setup; not an independent GitHub test-commit approval and not source authorization
  - B invalid-sent wire fields are user-confirmed in the handoff; no B-owner GitHub approval or contract freeze is fabricated
  verification:
  - Last measured revision 3: new file 116 collected; 113 failed (110 availability + 3 runtime lmi), 3 passes; old D 56 passed; full 528 collected, 117 failed, 409 passed, 2 skipped; paired 412 collected, 4 failed, 406 passed, 2 skipped
  - Revision 4: 118 collected by the supervisor. The two new cases reached their prerequisites as recorded in section 17.
  - Revision 3 Ruff/targeted Ruff pass; full Ruff retains only scripts/paperqa_smoke.py I001; mypy 14 files; schema PASS; remote enforcement NOT_DEPLOYED_OR_VERIFIED
  limitations:
  - Not an independent GitHub Approve; no src/ change; no product model, live/network test, semantic evaluation or OpenCode executable E2E
  - The assistant's own provider requests are not measured; no zero-cost claim
  - L2b behavior/session identity NOT_REACHED; paperqa.types import fails with ModuleNotFoundError(name="lmi")
  - Local B16 donor lacks INVALID_SENT_EVIDENCE/invalid_sent_evidence_ids; B Gateway-to-D case is a contract-prerequisite checkpoint, not reached behavior
```

The shared `docs/ai-use-log.yaml` was not modified. This entry is a proposal for the
shared-log editor, not a record of an approval.

## 12. Decision log and next steps

- 2026-11-23: accepted the two-file test-preparation scope under the student's
  instruction. The proposal deliberately keeps `AnswerService.prepare` unchanged,
  resolves all new API from submodules (no `__init__` export), uses `ValidationError` for
  invalid typed construction, and reports availability RED without skip/xfail.
- 2026-11-23: focused revision 2 added the two-alias positive controls, explicit
  unknown/ambiguous partition, real session identity recording, runtime `paperqa.types`
  import check, removal of the disconnected legacy spy, and the corrected publication
  stop. No B/source/shared-contract change was attempted.
- 2026-11-23: revision 3 added the mixed known/unknown bridge-boundary regression and
  recorded the B `INVALID_SENT_EVIDENCE` contract delta as a proposed, non-frozen mapping.
  No B/source/shared-contract change was attempted.
- 2026-11-23: revision 4 adopts the user-confirmed invalid-sent wire contract and the
  proposed D-neutral mapping as the draft test target. It adds the D-only fake-port case
  and the actual-B-type contract-prerequisite case. The supervisor verified both
  prerequisites. The local B16 donor still lacks the confirmed enum and field.
- Next: review the broader citation grammar and update the B donor when a compatible
  revision is available. The earlier PR20 approval covers C integration. The supervisor
  prepares this generation proposal separately and packages the two revised files
  onto a source-free publication base; an independent student who did not implement these
  tests must approve the exact test commit on GitHub. Only after that may a later
  implementation PR add `src/papertrace/answer/{generation,b_gateway_adapter}.py`; it must
  be created from the test head and contain the exact line `Test approval PR: #N`.

## 13. Revision 2 delta (do not claim all 111 prior cases unchanged)

The prior 111-case revision was intentionally extended to 115 cases and some assertions
were corrected:

1. Added the two-aliases-to-one-evidence positive controls: one L1 coordinator case and
   one public-B adapter conversion case. Both distinct alias keys are preserved and the
   `AnswerDraft` cited IDs deduplicate to one evidence identity. All duplicate/conflicting
   alias-KEY negatives remain; repeated alias targets are valid.
2. Recorded actual `PQASession` objects in the fake `Docs.aquery` recorder and actual
   factory-returned session wrappers in `_RecordingModelFactory`; the repeated-run test
   asserts both identities are distinct. Because L2b is blocked by the `lmi` runtime
   import, these assertions were **NOT_REACHED** in this run.
3. Corrected the unknown/ambiguous diagnostic partition: `raw_unknown_keys` excludes
   reported ambiguous keys; resolved alias keys, unknown keys and ambiguous keys must be
   disjoint and reconcile with raw extraction. Added `unknown-ambiguous-overlap` and
   `ambiguous-not-extracted` negatives; the valid `ambiguous-key` control retains its
   ambiguous diagnostics. Existing unknown/unreconciled/duplicate-key negatives remain.
4. Replaced discovery-only `find_spec("paperqa")` with a runtime import of
   `paperqa.types` plus required API checks. The actual run fails with
   `ModuleNotFoundError(name="lmi")`; this is reported as a runtime dependency/environment
   blocker, not D behavior RED or availability success. L2b is NOT_REACHED.
5. Removed the disconnected `RecordingPort` from GN-D-09 and its vacuous empty-requests
   assertion. The two legacy controls still assert `prepare` output/tokens and one
   projection read; they do not claim to measure a generation port.
6. At revision 2, citation grammar confirmation and the B sent-metadata conflict were
   still open. Section 14 records the subsequent B handoff and remaining decisions.
   The C-integration approval on PR20 only covers its own test commit.

## 14. Confirmed B invalid-sent contract and adopted D-neutral mapping

User-confirmed B wire result (2026-11-23 handoff; not a GitHub approval):

- `GenerationStatus.INVALID_SENT_EVIDENCE` is a terminal status.
- `sent_evidence_ids=()`.
- citation mapping is empty (`citation_aliases=()`).
- `invalid_sent_evidence_ids` is carried with the B result to D for internal diagnostics.

D draft mapping adopted for the test target (not source implementation):

- The adapter recognizes the actual B enum member by identity (no fake status) and maps it
  to `GenerationCallResult(status="REFUSED", refusal_reason="INVALID_SENT_EVIDENCE",
  sent_evidence_ids=(), citation_aliases=(),
  invalid_sent_evidence_ids=<exact reported IDs>)`.
- `GenerationCallResult.invalid_sent_evidence_ids` is D-internal, defaults to `()`, and is
  retained on `outcome.result`. It is never added to shared `AnswerDraft` and no
  E/publication interface is introduced.
- D returns a failed `GENERATION_REFUSED` draft with empty body/sent/citations and no
  release decision.
- The existing malformed-SUCCESS guard remains: a SUCCESS result whose reported sent set is
  outside selected fails `RESULT_SHAPE_INVALID`; the confirmed invalid-sent status is a
  distinct B status and must not be synthesized from malformed SUCCESS.
- The existing mixed known/unknown B SUCCESS case remains a failed `UNKNOWN_CITATIONS`.

Local donor status and checkpoints:

- The exact local B16 donor lacks `GenerationStatus.INVALID_SENT_EVIDENCE` and
  `GenerationResult.invalid_sent_evidence_ids`, and its `run_generation` still filters
  unselected reported sent IDs. The B Gateway-to-D case therefore obtains the actual B
  types and uses narrow contract assertions; locally it is expected **B contract
  prerequisite RED**, not D behavior. No fake B enum/status, skip, xfail or broad
  `ImportError` catch is used, and B is not patched.
- The service-level fake neutral port case is expected **D implementation availability
  RED** until the proposed D model/service exists; it makes the D failure testable
  independent of the B donor.
- Neither new case has been measured in this turn.

## 15. Revision 3 delta (B handoff; do not claim the 115-case set unchanged)

- Added exactly one distinctly named bridge-boundary regression:
  `test_gn_d10_bridge_boundary_mixed_known_and_unknown_citations_fail_unknown_citations`.
  It uses a fake gateway returning B SUCCESS with `(b1)` resolved, `(b999)` unknown,
  actual sent evidence and a valid alias, then runs the proposed adapter into D's service.
  Intended assertions: D fails `UNKNOWN_CITATIONS`; failed draft body/sent/citations empty;
  raw text and unknown key retained; no release decision. In this checkout it stops at the
  missing adapter availability assertion, so **none of those behavioral assertions were
  reached**.
- The existing unknown-only unit case remains. At revision 3 the B
  `INVALID_SENT_EVIDENCE` contract was documented as proposed only; revision 4 now adopts
  the user-confirmed wire contract in section 14 and adds the corresponding tests in
  section 16.
- Case count increased 115 → 116 at revision 3. No source, B, shared-contract, permission
  or fixture change was made.

## 16. Revision 4 delta (confirmed invalid-sent contract)

Two draft cases are added; neither was executed in this turn. Measurements remain with the
supervisor.

1. `test_gn_d07_invalid_sent_evidence_maps_to_failed_generation_and_retains_diagnostic`
   (service-level fake neutral port, D-only).
   - Uses one approved/selected synthetic evidence and one distinct unauthorized synthetic
     evidence.
   - Fake neutral result: `status="REFUSED"`, `sent_evidence_ids=()`,
     `citation_aliases=()`, `refusal_reason="INVALID_SENT_EVIDENCE"`,
     `invalid_sent_evidence_ids=(unauthorized_id,)`.
   - Expected when D exists: one port call; exact unauthorized ID survives on
     `outcome.result.invalid_sent_evidence_ids`; failed `GENERATION_REFUSED` draft with
     empty body/sent/citations; no `invalid_sent_evidence_ids` on `AnswerDraft`; no release
     decision.
   - Expected current prerequisite: **D implementation availability RED** because the
     proposed generation module/service does not exist.
2. `test_gn_d10_b_gateway_invalid_sent_evidence_requires_confirmed_contract`
   (actual public B enum/result types → proposed adapter → D).
   - Obtains actual `GenerationStatus`/`GenerationResult` from the local B donor and uses
     narrow assertions for `hasattr(status_type, "INVALID_SENT_EVIDENCE")` and the presence
     of `invalid_sent_evidence_ids` in the B result's dataclass/model field map
     (`__dataclass_fields__` or `model_fields`).
   - No fake B enum/status, no skip/xfail, no broad `ImportError` catch.
   - Expected current prerequisite: **B contract prerequisite RED** because the local B16
     donor lacks the confirmed member/field (and still filters unselected sent IDs).
   - If a future donor exposes the fields, the case proceeds through the actual enum/result
     into the adapter and D, asserting the D-neutral `REFUSED` mapping, empty normal
     sent/aliases, exact unauthorized ID on the internal result, and failed
     `GENERATION_REFUSED` draft.

The existing mixed known/unknown citation case and the malformed-SUCCESS out-of-selection
guard are preserved. Section 17 reports the execution of all 118 cases.
No source, B, shared-contract, permission or fixture change was made.

**No source implementation, publication, commit or approval is claimed by this record.**


## 17. Supervisor verification of revision 4

The supervisor ran test SHA256 `8c66f6a4512360d3a9a7b2f4c45745561b0382d007f98f4d4091517a564dc973` using the existing project interpreter with
sockets disabled. The assembled setup used D19 and the local B16 donor. The source-free
control used the PR20 test base.

| Check | Measured result |
|---|---|
| Assembled targeted file | 118 collected, 3 passed, 115 failed. 111 D availability failures, 1 B contract prerequisite and 3 missing `lmi` failures |
| Assembled full offline | 530 collected, 409 passed, 119 failed, 2 skipped |
| Paired baseline | 412 collected, 406 passed, 4 failed, 2 skipped. All 412 prior node outcomes matched |
| Source-free targeted file | 118 collected, 1 passed, 114 missing-module failures, 3 missing `lmi` failures |
| Configured Ruff on the changed test | Passed |

The fake-port case reached the missing D generation module assertion. The actual B-type
case reached the missing `GenerationStatus.INVALID_SENT_EVIDENCE` assertion. The
adapter mapping, diagnostic retention and publication denial remain behavior assertions
to validate after implementation. HEAD and index entries matched preflight, as did all
349 protected files including the four existing local B donor files.


## 18. Local candidate verification and B accounting follow-up

The candidate uses the approved PR #24 test head `f0b251fad52061a0d60e0674f078b2e63d1c81fb`.
The generation test file retains the revision 4 SHA-256 in section 17. The source-free checkout
contains the already merged C files and excludes local D implementations and B donor files.

| Run | Passed | Failed | Skipped |
|---|---:|---:|---:|
| Full offline on the candidate | 362 | 210 | 2 |
| Same checkout, generation test excluded | 361 | 93 | 2 |
| Added generation file | 1 | 117 | 0 |

All 456 paired baseline node outcomes match. Of the 117 failures in the new file, 114 reach a
module availability assertion and three stop at `ModuleNotFoundError(name="lmi")`. Configured
Ruff passes for the new file. The frozen upstream lock pins the `fhlmi` distribution at `1.10.0`.
In a separate isolated run with exact B PR #25 `425a971f`, the invalid-sent case passed its B
status and field assertions and reached the missing D adapter. Product behavior remains unmeasured.

B PR #27 at `10ef7a8287d4b0784b567aca7d4d45ffcd1a4132` proposes `accounting` on both its
result and the error from the answer model boundary. Prepare D consumer cases when B confirms the
public result and exception interface.

| Scenario | D consumer expectation |
|---|---|
| B reports a verified preflight refusal | Preserve the configured provider and model and the observed zero attempt count |
| The B call crosses an uninstrumented port | Preserve `None` as unknown |
| B enters the answer model once | Preserve one observed attempt and the configured provider and model |
| The answer model raises after entry | Preserve the observed one attempt for internal diagnostics, preserve the B cause chain, and keep the draft ineligible for release |

Keep token estimates and provider billing fields outside this follow-up. The four accounting cases
are a design note and are outside the 118 tests in this candidate.
