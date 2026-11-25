# Module D design record: standalone answer panel test plan

| Item | Value |
|---|---|
| Date | 2026-11-25 |
| Phase | **Test preparation only**; no `src/` was written |
| Module | D `answer` |
| Slice | Standalone Streamlit preview panel over the real `AnswerGenerationService` and `ReleaseGate` |
| Base | D #50 at `8f0866675157b3e8fdce264ba3cd6e65e8e3892f` |
| Writable paths used | `test/offline/test_answer.py` (append only), this record |
| Local result | 46 collected, 33 passed, 13 expected failures from absent panel modules. See the supervising verification below. |
| Approval state | The supervising student approved this exact plan and this single test-preparation submission. The exact test commit has **no** independent GitHub approval yet. |

## 1. Authorization and provenance supplied

The supervising student supplied this scope. This record does not create or repeat an
independent approval, and this session issued no approval of its own.

- Only the two paths in the table above were edited. No source, shared contract,
  dependency, lockfile, configuration, permission, CI, workflow, Git state or shared
  AI-use log was changed.
- The prior contents of `test/offline/test_answer.py` were preserved
  byte-for-byte as a prefix; the new panel tests are appended after the existing
  33 cases.
- The test proposal may remain an open RED PR. It must not be merged just to obtain
  approval.
- A different student who did not implement these tests must approve the exact test
  commit on GitHub. Role selection, this record, the session model and tool
  permissions do not prove that approval.
- Only after that genuine non-author GitHub `Approve` may implementation add
  `src/papertrace/answer/view.py` and `src/papertrace/answer/preview.py` on the
  approved test head. The implementation PR must be created from the test head and
  its description must contain the exact line `Test approval PR: #N`.
- The shared `app.py` entrypoint is a later integration step. This slice is a
  standalone preview, not the shared application.

The student approved the planning submission and later approved the exact plan and
one OpenCode test-preparation submission. The PaperTrace product model call budget
for this slice is **zero**.

## 2. Target behavior

The preview shows one question, one synthetic snapshotted corpus, one synthetic
review projection, the generated draft, canonical citation IDs and the release
decision. It has exactly two UI-facing commands:

1. a display render;
2. an explicit Generate request.

It has no publication command. The panel is a display and command surface only.
`AnswerGenerationService` remains the authority for evidence eligibility, the
generation boundary, citation reconciliation and draft status. `ReleaseGate` remains
the authority for the publication check. The panel never computes an approved set,
never rewrites a digest, never converts a model result into `accepted`, and never
turns a blocked decision into a released one.

The proposed render semantics are:

| Situation | Panel action |
|---|---|
| First render (no previous scope) | Record the display scope, clear any previous view, and process an explicit Generate request if present. |
| Same scope, no Generate request | Re-render the stored view; do not call generation. |
| Same scope, Generate requested | Call `AnswerGenerationService.run` exactly once, run `ReleaseGate.check` only for a `draft`, store and render the result. |
| Scope changed | Clear the stored view, render `None`, and ignore a Generate request in that render. Do not call generation. |

The display scope is the tuple `(question_id, snapshot_id, review_revision,
review_digest)`. It is UI display state, not an authorization token. A scope change
cannot grant evidence or publication authority; it only makes the old display
ineligible to remain visible.

## 3. Requirement and invariant mapping

| ID | What these tests observe | What is not claimed |
|---|---|---|
| `FR-D-01` | Open/rerun and an empty accepted projection produce zero generation-boundary calls and no application data writes. | SDK, HTTP or provider-layer attempt counts; those remain B/adapter evidence. |
| `FR-D-02` | A rejected duplicate-sent result suppresses raw output; the real release gate returns `PUBLICATION_COMMIT_UNAVAILABLE`; a scope change clears the old view. | A real publication transaction, E persistence or save-time atomicity. |
| `FR-D-03` | Exactly one controlled call for one explicit Generate action; no generation on ordinary rerun; lazy panel entrypoints; no Streamlit import in tests. | Real PaperQA2/provider quality or the concrete B adapter. |
| `INV-01` | Zero boundary calls when the projected accepted set is empty. | Runtime four-layer outbound accounting. |
| `INV-03` | The panel has no write path and cannot synthesize `accepted`; the projection and current-bundle write spies stay empty. | C ledger authenticity or replay; that remains C's authority. |
| `INV-04` | The displayed citation IDs are the validated draft's canonical IDs; the release gate remains blocked; scope changes discard stale display state without generation. | Semantic support of a claim by the cited excerpt. |

## 4. Proposed D-local interfaces

These are test targets, not existing implementation. Tests resolve them lazily so
pytest collects cleanly while the modules are absent.

### 4.1 `papertrace.answer.view`

```python
@dataclass(frozen=True)
class PanelScope:
    question_id: QuestionId
    snapshot_id: SnapshotId
    review_revision: int
    review_digest: str


@dataclass(frozen=True)
class PanelView:
    scope: PanelScope
    question_text: str
    draft_status: Literal["draft", "abstained", "failed"] | None
    body: str
    citation_evidence_ids: tuple[EvidenceId, ...]
    refusal_reason: str | None
    release_decision: ReleaseDecision | None
    accounting_observed: bool
    observed_answer_model_attempts: int | None


class PanelUI(Protocol):
    def render(self, view: PanelView | None) -> None: ...
    def take_generate_request(self) -> bool: ...


class AnswerPanel:
    def __init__(
        self,
        *,
        generation: AnswerGenerationService,
        release_gate: ReleaseGate,
        ui: PanelUI,
    ) -> None: ...

    def render(
        self, *, request: AnswerGenerationRequest, scope: PanelScope
    ) -> PanelView | None: ...
```

`PanelUI` deliberately has no publication method. `PanelView` is a display model;
it carries the release decision only so the UI can display it.

### 4.2 `papertrace.answer.preview`

```python
def render_preview(
    *,
    ui: PanelUI,
    generation: AnswerGenerationService,
    release_gate: ReleaseGate,
    request: AnswerGenerationRequest,
    scope: PanelScope,
) -> PanelView | None: ...


def main() -> None: ...
```

`main()` is the standalone Streamlit entrypoint. Streamlit is imported inside
`main()`, never at module scope, so offline collection and import do not require the
Streamlit runtime. `main()` constructs synthetic trusted state, a synthetic
projection, a counting double at D's generation port, the real
`AnswerGenerationService` and the real `ReleaseGate`, then drives `AnswerPanel`
through the Streamlit UI adapter.

### 4.3 Existing interfaces reused unchanged

- `AnswerGenerationService`, `AnswerGenerationRequest`, `GenerationPolicySpec`,
  `GenerationCallResult`, `GenerationAccounting`, `Reason` strings and
  `AnswerGenerationOutcome` from `papertrace.answer.generation`.
- `ReleaseGate`, `CurrentPort` and the release reason strings from
  `papertrace.answer.release`.
- `AnswerRequest`, `ReviewProjectionView`, `ReviewProjectionPort` and
  `REFUSAL_NO_APPROVED_EVIDENCE` from `papertrace.answer.model`.
- `AnswerDraft`, `ReleaseDecision`, `EvidenceRecord`, `CorpusSnapshot` and the ID
  aliases from `papertrace.contracts`.

No package `__init__` export is required. The tests import the submodules directly,
so the existing public export list stays unchanged.

## 5. Panel authority boundary

- `AnswerPanel` never reads `outcome.result.raw_output` to build a failed view. It
  displays `draft.body` and `draft.citation_evidence_ids`; D already empties those
  for a rejected result. This is why a duplicate-sent rejection cannot leak raw
  output into the panel.
- Accounting display uses `outcome.accounting` only. `accounting_observed` records
  whether D exposed a validated accounting value at all; the attempt count comes from
  `outcome.accounting.answer_model_attempts`. The raw B result is not a display
  authority.
- `ReleaseGate.check` is called only when the outcome carries a `draft` with status
  `draft`. Reflexive or failed outcomes do not receive a release decision.
- The panel keeps only the last scope and last view in memory. It does not persist
  them, does not replay C's ledger and does not call a write port.
- The test UI is a display double, not an authorization source. Its
  `request_publication` method is a trap: it increments a counter and raises if the
  panel ever calls it. The test also asserts that the proposed `PanelUI` protocol
  exposes no such name.

## 6. Test matrix

All new cases are appended to `test/offline/test_answer.py`. The existing 33 cases
are unchanged. The new tests are 13 cases across 7 test functions.

| Case | Test | Cases | Observation |
|---|---|---|---|
| OP-1 | `test_panel_open_and_rerun_do_not_generate_or_write` | 1 | Two renders with no Generate request: both views are `None`; generation calls, projection reads, current-bundle reads and both write spies are empty; no publication request. |
| OP-2 | `test_explicit_generate_calls_boundary_once_and_rerun_reuses_display` | 1 | First render with Generate: exactly one boundary call; view status `draft`; body is the validated draft body; citation IDs are the canonical evidence IDs; a second render without Generate re-renders the same view and adds no call. |
| OP-3 | `test_generate_without_approved_evidence_shows_refusal_and_skips_boundary` | 1 | Revision-0 empty projection with an explicit Generate: status `abstained`, refusal reason `NO_APPROVED_EVIDENCE`, no body or citations, zero boundary calls, one projection read, no release read. |
| OP-4 | `test_blocked_release_keeps_draft_visible_and_offers_no_publication_control` | 1 | Real `ReleaseGate` over the same captured bundle returns `PUBLICATION_COMMIT_UNAVAILABLE`; the draft body and canonical citation IDs stay visible; no publication request; the `PanelUI` protocol has no `request_publication`. |
| OP-5 | `test_repeated_sent_ids_suppress_output_and_show_validated_accounting` | 4 | Duplicate sent IDs cause D to reject the result: status `failed`, reason `RESULT_SHAPE_INVALID`, empty body and citations, raw output not shown. The panel distinguishes observed `1`, observed `0`, unknown `None`, and absent accounting (`accounting_observed=False`). |
| OP-6 | `test_scope_change_clears_previous_result_without_generation` | 4 | After one successful display, changing question, snapshot, revision or digest clears the visible panel to `None`; the generation call count and projection reads do not change. |
| OP-7 | `test_preview_entrypoint_keeps_streamlit_out_of_module_scope` | 1 | `papertrace.answer.preview` exposes `render_preview` and `main`, and its module-scope imports contain no `streamlit`. |

## 7. Negative-control rationale

- Each panel case starts from the real synthetic corpus/snapshot helpers already in
  the file; only the target condition changes.
- OP-2 is the positive control for OP-1 and OP-5: it proves the same wiring can reach
  exactly one boundary call and display a validated draft.
- OP-3 is the zero-call control for the empty approved set. It asserts both the
  refusal text and the zero boundary count; hiding the button alone would not pass.
- OP-4 uses the real release gate rather than a stub, so a panel that merely displays
  a green status cannot pass. The reason-code assertion is exact.
- OP-5 has four accounting cases so that `0`, `None`, and absent accounting cannot
  collapse into the same display. A panel that reads the raw result instead of
  `outcome.accounting` does not satisfy the field assertions.
- OP-6 injects a Generate request on the scope-changing render. If the panel ignores
  scope state and calls generation again, both the call count and the projection-read
  list fail.
- The write spies are not part of the production protocols; they are observation
  aids. They do not claim an OS sandbox or a complete persistence audit.

## 8. Offline independence and Streamlit replay

- The tests import no Streamlit module and construct no Streamlit object.
- `papertrace.answer.view` and `papertrace.answer.preview` are resolved lazily inside
  test helpers, so collection succeeds while the modules are missing and the new
  cases fail as availability RED rather than collection errors.
- OP-7 statically checks the preview module's module-scope imports. This is a
  structural observation, not proof that a later call path cannot import Streamlit.
- The real Streamlit button replay is a separate post-implementation step using the
  existing local AppTest environment. It is not part of this offline test proposal
  and is not claimed here.

## 9. Expected RED state

Before implementation:

- pytest collects the file and all existing 33 cases pass.
- The 13 new cases fail on the deliberate availability assertions for
  `papertrace.answer.view` or `papertrace.answer.preview`.
- No new case should fail with a collection error, import-time Streamlit error,
  fixture error or network attempt.
- The reason text for each new failure should be the proposed panel module/symbol
  availability assertion.

After the exact test commit receives a genuine non-author GitHub `Approve`,
implementation may add the two source files. The test file and this record must not
be edited to make implementation pass; a changed test requires a new reviewed test
commit.

## 10. Verification commands for the supervising runner

This session ran no shell command. The supervising runner should execute the exact
offline checks below from the repository root:

```sh
.venv/bin/python -m pytest -c papertrace.pytest.ini test/offline/test_answer.py --collect-only -q
.venv/bin/python -m pytest -c papertrace.pytest.ini test/offline/test_answer.py
.venv/bin/python -m pytest -c papertrace.pytest.ini test/offline
.venv/bin/python -m ruff check --config papertrace.ruff.toml test/offline/test_answer.py
.venv/bin/python -m ruff check --config papertrace.ruff.toml src/papertrace test/offline scripts
.venv/bin/python -m mypy --config-file mypy.ini src/papertrace
.venv/bin/python scripts/gates.py --gate schema
git diff --check
```

Expected targeted shape: 46 collected, 33 existing passed, 13 new availability
failures, no collection error. The full offline suite should contain the prior
baseline plus these 13 cases; the exact prior baseline count must be read from the
runner's checkout, not assumed here. Ruff should be clean for the changed test file;
the known existing `scripts/paperqa_smoke.py` finding, if still present, is outside
this slice. mypy, schema and `git diff --check` should be reported exactly as
observed.

After implementation, the same commands plus the real Streamlit AppTest button
replay, targeted suite, offline suite, Ruff, mypy, schema and AI-use-log verification
belong in the implementation record. Product model calls remain zero.

## 11. Limitations and non-claims

- This is a test proposal, not an implementation, a test result, a GitHub approval,
  a merge or a publication decision.
- No behavior of the proposed panel is exercised until implementation exists. The
  expected RED only proves the modules are absent and collection is clean.
- The panel tests do not prove real provider quality, PaperQA2 behavior, the concrete
  B adapter, token accounting, SDK/HTTP attempt counts or semantic faithfulness.
- The release gate is real, but the captured bundle is synthetic. No real C ledger,
  A snapshot pointer, E persistence or single-writer transaction is exercised.
- The test UI is a display double. It does not prove Streamlit rendering, widget
  identity or browser behavior; those remain for the AppTest replay.
- The module-scope import check for Streamlit is static and not an OS sandbox.
- No product model, credential, network or live provider call was used or is
  authorized here.
- No absolute host path, credential or private data is recorded.

## 12. Supervising verification and AI-use record

- Collection completed with 46 cases and no errors. The 33 existing cases passed.
  The 13 added cases failed at the planned module-availability assertions.
- A separate probe executed the real generation and release services with the new
  fixtures. It confirmed one successful generation call, zero calls on abstention,
  the expected release block, and accounting preservation for the four repeated-ID
  cases. Streamlit AppTest is part of implementation verification.
- Scoped Ruff, mypy, schema and `git diff --check` passed. Full-source Ruff on
  the pinned #50 base still reports the existing import-order finding in
  `scripts/paperqa_smoke.py`.
- Full offline in the available initialization environment recorded 586 passes,
  two OpenCode discovery skips, and 16 failures. Thirteen were the expected panel
  failures. The three PaperQA2 bridge failures also reproduced on unchanged #50
  because this interpreter lacks `lmi`.
- OpenCode CLI v2.3.0 used `papertrace-build-D` and `deepseek/deepseek-flash`.
  Its two-file edits and the supervising checks are disclosed by
  `D-PANEL-TESTPREP-20261125-01` in the project AI-use log. The transcript was
  archived privately. The independent review of the test commit remains pending.

## 13. Open questions for implementation review

1. Should `PanelScope` use the shared `QuestionId`, `SnapshotId` and `Sha256` type
   aliases directly, or plain `str` annotations backed by test comparisons? This record
   proposes the shared aliases and does not add new shared definitions.
2. Should the first render accept a Generate request in the same run? This proposal
   does, because a Streamlit button click may arrive on the first render, while a
   later non-initial scope change deliberately ignores the click and clears the view.
3. Should the panel expose a separate "clear" command, or is a scope change the only
   clearing action? This proposal uses only scope change; no extra command is added.
4. Should accounting display live on `PanelView` as the two proposed fields, or in a
   nested display model? This proposal keeps the fields flat so a test can distinguish
   observed zero, unknown and absent without parsing text.
