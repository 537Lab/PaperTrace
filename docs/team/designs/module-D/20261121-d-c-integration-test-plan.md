# Module D — C-to-D projection integration: test-preparation plan
## (2026-11-21; local publication-preparation revision 2026-11-22)

## 1. Scope and stage authority

This record covers the local publication-preparation revision of the D/C
integration test slice. The only writable files are
`test/offline/test_answer_c_integration.py` and this design record. No `src/`
file is changed, and no `src/papertrace/answer/c_adapter.py` implementation is
authorized here.

This stage does not commit, push, open or merge a pull request, approve a
review, or call a PaperTrace product model, provider, live retrieval path or
real semantic evaluation. The tests themselves are deterministic offline tests;
the AI coding-assistant session that edited them is a separate development-tool
channel (§12).

The supervising side reports that the student authorized local test-preparation
on 2026-11-21 and authorized this publication-readiness correction on
2026-11-22 HKT. Those are local authoring authorizations for tests/design only;
they are not independent GitHub approval and are not an approval record.

A different student who did not implement the tests must still approve the exact
test commit on GitHub before any source stage. The test proposal PR may remain
open and RED; an implementation PR must branch from that test head and contain
the exact line `Test approval PR: #N`. Synthetic `reviewer_ref` strings in the
tests are runtime test data, never GitHub approval.

## 2. Read basis

- `AGENTS.md`, `Prompt.md`, `architecture-blueprint.md`, `.opencode/rules.md`,
  `.agent/rules.md`.
- `docs/team/module-D.md`, `docs/team/module-C.md`,
  `docs/team/integration-contract.md`.
- `docs/req/requirements.yaml`: `FR-D-01/02/03`, `INV-01/03/04`, `QA-01`,
  `COST-01`.
- `src/papertrace/contracts.py` and the existing D interfaces
  `src/papertrace/answer/{__init__,model,errors,eligibility,service}.py`.
- C's two public-interface files `src/papertrace/review/__init__.py` and
  `src/papertrace/review/service.py` (`ReviewLedger`, `ReviewProjection`,
  `ReviewLedgerCorrupted`, and the actual `prepare_decision` /
  `commit_decision` behavior).

## 3. Proposed D-local adapter interface (import target only)

```python
class CReviewProjectionAdapter:
    def __init__(self, *, ledger: ReviewLedger) -> None: ...
    def read_projection(self, question_id: str) -> ReviewProjection: ...
```

- Lives in `papertrace.answer.c_adapter`. It only reads C's public
  `ReviewLedger.projection` and returns that ledger's `ReviewProjection` object
  for the requested question.
- No mapping/dictionary compatibility layer, no copied hashing or revision
  algorithm, no ledger writes, and no exception capture, wrapping or downgrade:
  C's exceptions propagate unchanged.
- The name and constructor form a D-local testable interface proposal, not an
  implementation and not a new shared contract. Tests provide no fallback stub;
  absence must remain visible.
- Tests use it only as the injected collaborator of the existing
  `AnswerService(projections=...)`. `AnswerRequest`, `AnswerDraft` and
  `AnswerService` keep their approved slice-1 definitions; no D source interface
  is added or modified in this stage.

## 4. Runtime dependency resolution and exact failure classification

Collection must be safe on a source-free publication base. The test module
therefore keeps only real shared-contract and C public-interface imports at
module import time; it never imports `papertrace.answer` at the top level.

- `load_answer_package()` performs the real D import during test/helper
  execution. Only an exact `ModuleNotFoundError.name == "papertrace.answer"` is
  converted into an ordinary failed assertion carrying
  `MISSING_D_PREREQUISITE`. That failure identifies a missing D prerequisite; it
  does not claim the adapter RED and does not execute C-to-D integration behavior.
- No fallback module, class, exception or default token is created. A missing
  D submodule, a missing third-party dependency or any other `ImportError` /
  `ModuleNotFoundError` is re-raised unchanged during execution.
- `verified_project_modules()` imports real D and its service, imports real C
  and its service, derives the four expected files from
  `Path(__file__).resolve().parents[2] / "src" / "papertrace"`, and asserts each
  module's exact resolved `__file__`. It runs during test/helper execution,
  after D is loaded and before any adapter probe. An unrelated installed
  checkout or unexpected module origin fails visibly rather than passing as a
  valid import.
- `probe_adapter()` first runs the four-file C/D origin preflight, then imports
  the proposed adapter. Only an exact
  `ModuleNotFoundError.name == "papertrace.answer.c_adapter"` is classified as
  adapter-not-implemented. Every other missing dependency/import error
  propagates unchanged. Missing D therefore cannot make the
  adapter-classification control pass.
- `require_answer_api()` resolves the real D exports (`AnswerService`,
  `AnswerRequest`, `AnswerPreparationError`, `ProjectionScopeMismatchError`,
  refusal constants) only after the origin preflight. A missing export is an
  explicit interface failure, not a fallback.

Expected runtime taxonomy:

| Condition | Classification | Location |
|---|---|---|
| Exact missing `papertrace.answer` | ordinary missing-D prerequisite assertion | `load_answer_package()` |
| Exact missing `papertrace.answer.c_adapter` after preflight | expected adapter RED | `probe_adapter()` |
| Missing D submodule or third-party dependency | unchanged import error | execution |
| Module origin outside this checkout | visible preflight assertion | `verified_project_modules()` |
| Missing real D export, adapter class or interface | visible interface assertion | `require_answer_api()` / `build_adapter()` |

Consequently, a source-free checkout should collect normally and fail every
test with an honest missing-prerequisite assertion. A checkout with approved D
but without the adapter should collect 15 items, pass the preflight and
missing-adapter-classification controls, and fail the 13 behavior tests at
explicit adapter availability. These are expected classifications; the
post-revision dual-base runs are still NOT_RUN (§8.3).

## 5. Behavior groups and requirement mapping

All ledgers are synthetic and created at runtime under `tmp_path` through C's
real `prepare_decision -> commit_decision` path. Revision and digest values are
always compared with C's own `ledger.projection(...)`; no hash is hardcoded and
no counter design is assumed. Synthetic `reviewer_ref` strings are runtime test
data and never GitHub approval. The test code makes no PaperTrace product-model,
live-retrieval or real semantic invocation and no product SDK/network call
(COST-01); §12 separates that from the AI coding-assistant channel.

| Group | Scenario and assertions | Requirements |
|---|---|---|
| CT-D-01 | An absent ledger file and an existing but empty ledger file both yield an abstained draft with `NO_APPROVED_EVIDENCE`, empty approved/sent/cited/body, and revision/digest equal to C's current projection. File absence is not a read failure. | FR-D-01; INV-01; INV-04 |
| CT-D-02 | One accepted decision through the real prepare/commit path yields `failed` / `GENERATION_PATH_NOT_ENABLED`, approved exactly equal to C's accepted set, and empty sent/cited/body. Generation stays disabled. | FR-D-01; FR-D-03 (partial); INV-04 |
| CT-D-03 | all-pending, all-excluded, and mixed accepted/excluded/pending states; only accepted evidence may enter approved; resetting a previously accepted item to pending must not let a later preparation reuse that approval. Does not establish `verify_current` or release race safety. | FR-D-02 (partial); INV-03; INV-04 |
| CT-D-04 | Acceptance for Q1 does not authorize Q2: the adapter's Q2 projection and the resulting draft both carry Q2's own actual scope/revision/digest, Q2 has no accepted evidence, and the draft is an abstained answer with empty approved. No invented token values and no assumption about independent revision counters. | INV-03; INV-04 |
| CT-D-05 | A ledger bound to snapshot A receives a valid request for snapshot B: `ProjectionScopeMismatchError` is raised and no draft is returned; a matching-A normal control produces a failed draft. Real contracts validate every fixture object before the D behavior runs. | FR-D-02 (partial); INV-04; QA-01 |
| CT-D-06 | The final newline is removed from a real nonempty valid synthetic ledger at its actual `tmp_path` path; C's real parser raises `ReviewLedgerCorrupted` through both the adapter and the service, with no draft and no abstained fallback. No invented D wrapper exception or added `__cause__` is asserted. | QA-01; INV-01 |
| CT-D-07 | A normal read of the valid ledger is proven first. A specific `PermissionError` instance (plus an `OSError` parameter case) is injected only at that ledger path's `Path.read_bytes` boundary, delegating every other path to the original method. The hook is proven reached and the caller receives that same exception instance, with no draft returned. | FR-D-02 (partial); INV-01; QA-01 |

Additional interface checks: the adapter must return C's `ReviewProjection`
(not a dict) per question; the two questions' returned headers must match their
own real C projections. Normal-read controls run before fault injection so the
fault tests cannot pass vacuously.

## 6. Synthetic materials, sequential reuse and fault injection

- No corrupt fixture is checked in: corpus text, ledger directories, the empty
  ledger state and the truncated ledger are all generated under `tmp_path`.
- Snapshots, documents, evidence and locators use the real shared models and
  default identity algorithms: `EvidenceRecord.evidence_id` and
  `CorpusSnapshot.snapshot_id` are computed by the contracts, and each fixture
  object round-trips through its own JSON contract before behavior runs.
- Ledger paths are discovered with `rglob("*.jsonl")` after a real commit; C's
  internal filename logic is not copied. CT-D-01's "existing empty file" state is
  produced by truncating a real commit to zero bytes, which is a valid empty
  ledger.
- CT-D-06 removes only the final newline byte and keeps the rest of the real
  content.
- CT-D-07 uses `monkeypatch.setattr(Path, "read_bytes", guarded)`; the guard
  raises the injected instance only for the target ledger path, delegates all
  other paths to the original `Path.read_bytes`, and records the hit path.
- Sequential reuse: the reset test (CT-D-03) constructs one adapter and one
  `AnswerService` before the first preparation and calls that same service before
  and after committing the real C reset. A projection retained inside either
  reused instance would surface as a non-empty second approved set; the test
  asserts the second draft is abstained with empty approved/sent/cited/body,
  `NO_APPROVED_EVIDENCE`, and the actual post-reset revision/digest. This is
  sequential reuse coverage only, not a concurrency or `verify_current` claim.
- No existing test, fixture, `test_answer.py`, C file, contract, CI/gate,
  dependency or governance file is modified.

## 7. Verification to be run by the supervising side

The supervising side runs these with the initialized project interpreter from a
prepared snapshot; they are interpreter arguments, not an OpenCode shell grant.

```sh
python -m pytest -c papertrace.pytest.ini -p no:cacheprovider test/offline/test_answer_c_integration.py
python -m pytest -c papertrace.pytest.ini -p no:cacheprovider test/offline
python -m ruff check --no-cache --config papertrace.ruff.toml src/papertrace test/offline scripts
python -m mypy --config-file mypy.ini --cache-dir <task temporary directory> src/papertrace
python scripts/gates.py --gate schema
```

Publication verification must use both prepared bases:

1. A cumulative source-free snapshot: the new test file must collect normally,
   then report ordinary missing-D prerequisite failures rather than a
   collection error.
2. The exact approved-D19 source snapshot: the same collection must reach 15
   items; the preflight and missing-adapter classification controls should pass,
   and the 13 behavior tests should fail only at explicit adapter availability.

Reports must separate exit codes, collection/setup/import failures and behavior
failures. Targeted and full configured Ruff must run in both bases; import
ordering must not depend on D being present. Mypy, schema, whitespace and
protected-file/source/setup identity checks are also separate. Full upstream
regression, live calls, real semantic evaluation and native-engine E2E remain
separate and are not replaced by these checks.

## 8. Verification snapshots

### 8.1 Historical pre-revision snapshot (2026-11-21, supervisor-run)

This snapshot describes the earlier 615-line test file and 131-line design
record, before the 2026-11-22 correction. It is retained as history, not as a
description of the current files.

Pre-revision identities: test file 615 lines, SHA256
`a25c6cff22dd37e215c603044777d19cc34d1337ccd4b4e135a9346f6954bd41`;
design record 131 lines, SHA256
`933475fb44cb3680b40c652b54eac935233f5ca89d96c76e94440e32737ccec0`.

| Check | Recorded result |
|---|---|
| `pytest ... test/offline/test_answer_c_integration.py --tb=short` | exit 1; collected 15; 2 passed, 13 failed. All 13 failed at `adapter_module()`'s explicit missing-adapter assertion; the missing module name was exactly `papertrace.answer.c_adapter`. Collection and the real C/D imports succeeded; some real C/fixture setup assertions ran, but adapter-mediated D behavior assertions and read-fault injection were not reached. |
| `pytest ... test/offline --tb=short` | exit 1; collected 404; 386 passed, 16 failed, 2 skipped (53.99 s). The 16 failures are the 13 adapter-availability failures, 2 known configuration allow-versus-ask assertions at `test_opencode_configuration.py:106` (one wrapper calls the same test), and `test_full_regression.py::test_timeout_stops_owned_test_descendants` where the local sandbox rejected subprocess `ps` with `PermissionError` errno 1. The 2 skips are workflow tests whose executable is not installed. These 16 must not all be classified as expected adapter RED, and those tests must not be weakened. |
| `ruff check --no-cache ...` | exit 1; only `scripts/paperqa_smoke.py:37` I001; no finding in the new test. |
| `mypy --config-file mypy.ini --cache-dir <temporary> src/papertrace` | exit 0; no issues in 10 source files. This does not type-check the new test. |
| `scripts/gates.py --gate schema` | exit 0; schema PASS. Other course gates were not run by that command. |
| Resolved module-path checks | The supervisor confirmed all four C/D package/module files resolve to this worktree; `git diff --check` passed; no `src` changes or new commits. |

Full upstream regression, live calls, real semantic evaluation and remote PR
refresh were NOT_RUN. These results apply only to the historical file
identities above.

### 8.2 Supervisor pre-revision snapshot (2026-11-22 HKT, publication base)

This is the measured state of the 682-line test file and 215-line design record
before the current correction. It is not a post-revision result.

Input identities:

- Test file: 682 lines, SHA256
  `9349ddb8f1bb567acdfaa4bd4f4562d2ea7aa5352030eab92ec68b9aa9a48e65`.
- Design record: 215 lines, SHA256
  `a77a1e3dceb3155bbe6e94f7ee9f24ca6a3ee1f265647170f2c7f011e55613ab`.

Supervisor measurements with the existing project CPython 3.14.8 interpreter,
configured pytest and disabled sockets:

| Base + file | Check | Recorded result |
|---|---|---|
| main `6235c33d460b48d1ff11a10624d1bcd5919ea4f0` + this pre-revision draft | pytest collection | exit 2; no tests collected; one `ModuleNotFoundError` at the top-level import of `papertrace.answer`. |
| main `6235c33...` + this pre-revision draft | targeted configured Ruff | FAIL / I001 in this new file's import block. This is not the shared `scripts/paperqa_smoke.py` finding. |
| approved D `3d536aa2382f3c4b803dd2b7caf0dd1fe95aed82` + this pre-revision draft | pytest collection | exit 0; 15 collected. |
| approved D `3d536aa...` + this pre-revision draft | pytest execution | exit 1; 2 passed, 13 failed. All 13 failed at explicit adapter availability, not adapter behavior; the adapter-mediated assertions and read-fault hooks were not reached. |
| approved D `3d536aa...` + this pre-revision draft | targeted configured Ruff | PASS. |

Ruff's inferred first-party grouping changes when D is absent, so a lint pass on
the old authoring checkout is insufficient; the revision must work in both
snapshots. These are PRE-REVISION results for the identities above.

### 8.3 Authoring-session post-revision status (supervisor results in section 14)

At the coding-session stop point, post-revision dual-base results were NOT_RUN.
The supervising side was to run
the collection and execution checks in a cumulative source-free snapshot and in
the exact approved-D19 source snapshot, plus targeted and full configured Ruff
in both bases, mypy/schema/whitespace and protected-file/source/setup identity
checks appropriate to the publication tree. Full offline collection and
execution with paired baseline, full upstream regression, live calls, real
semantic evaluation and native-engine E2E remain separate. No post-revision
pass, failure count or behavior outcome is claimed here.

## 9. Local publication-preparation correction

The correction in this stage:

- removes eager top-level `papertrace.answer` imports, symbol resolution,
  origin preflight execution and adapter probing from module import time;
- resolves real D exports and the adapter during test/helper execution;
- classifies only the exact missing D package as an ordinary missing-prerequisite
  assertion, and only the exact missing adapter module after the four-file C/D
  origin preflight as the expected adapter RED;
- keeps every other missing dependency/import error unchanged;
- verifies the four exact C/D module `__file__` paths before probing the adapter;
- preserves all 11 test functions and their parametrizations (15 items), the
  seven CT-D behavior groups, real C ledger preparation/commit, contract
  round-trips, actual projection tokens, the matching/foreign snapshot controls,
  the real truncated ledger, the same-instance read-fault injection and the
  sequential-reset service reuse. No assertion is weakened;
- keeps configured import ordering portable across both source-present and
  source-absent snapshots, without `noqa`, an I001 ignore, a lint-threshold
  change, a collection hook, a blanket catch, a global fake D symbol, or
  `sys.path` / `sys.modules` surgery.

## 10. Safety review and ADR still required

`scripts/gate_evidence.py`'s `_safety_review` condition includes the
`src/papertrace/answer/` prefix (read-only observation). A future
`src/papertrace/answer/c_adapter.py` is therefore on a safety-reviewed source
path: its implementation PR still needs a genuinely applicable ADR reference and
an independent review of its exact head. This test-preparation stage does not
exempt source changes and does not alter any gate.

## 11. Unresolved items

- The complete prior regression matched earlier failure counts, but neither run
  retained failing node IDs or assertion output; per-node attribution remains
  unresolved, and regression failures must not be categorized as inherited or
  expected without evidence.
- The shared Ruff I001 reproduces on an unchanged file
  (`scripts/paperqa_smoke.py`) and is not introduced by this slice.
- In the local test-preparation environment, the approved read exception for C's
  `service.py` makes two existing configuration tests fail at
  `test/offline/test_opencode_configuration.py:106`. This is a local
  governance/test-expectation mismatch, not an integration-test failure and not
  inherited from the base; tests and configuration are not modified here and the
  mismatch is left to governance review.
- D's generation path, citation parsing, freshness/`verify_current` and release
  gate remain outside this slice.
- The exact test commit and its independent GitHub approval do not exist yet.
  Publication packaging and the clean-source-free verification are supervisor
  actions; this stage does not create a branch, commit, pull request or review.
- Post-revision checks were NOT_RUN by the coding session; the later supervisor
  measurements and remaining limitations are recorded in section 14.

## 12. AI assistance and session disclosure

The two files in this stage were edited in an OpenCode session scoped to this
authoring checkout. The session used file reads, shell identity/whitespace
checks, native file edits and one shell-assisted in-file rename within the
authorized test file; it did not use subagents, plugins, symlinks,
installs, Git commit/push/PR/review/merge, a PaperTrace product model, a product
provider call, live retrieval or a real semantic evaluation.

The assistant environment self-reports the model identity as DeepSeek V4.1 Flash
1017 (provider ID `deepseek`, model ID `deepseek-flash`). That identity is
self-reported by the assistant environment and is not independently verified by
the project. Communication between the coding assistant and its own provider is
a development-tool channel, separate from the tests' property of making no
PaperTrace product-model or product-SDK/network invocation. No raw transcript,
private session quotation or invented review is recorded here; the real session
and human interventions remain with the supervising side.

## 13. Stop point

This stage stops after the two files are revised. The next checkpoint is the
supervising side's clean source-free verification and publication packaging,
then a real GitHub approval of the exact test commit by another student who did
not implement the tests. Only after that may a separately authorized source stage
implement `c_adapter.py` with its applicable ADR and an independent exact-head
implementation review.


## 14. Supervisor publication-candidate verification (2026-11-23 HKT)

The supervisor independently verified the author-reported test SHA256
`9c7e4f5c6226d8348e9155c2f222b3810d2194e904ff2f324d709f20050635d6` and
original authored design SHA256
`5f22743fb1e4cac80f052d4979398b65a171ce6099c3ac548830c94dc1de7881`.
The published-candidate test is an exact copy; only the candidate design receives
this dated supervisor addendum and clarified historical NOT_RUN labels. No source
implementation or approved existing test/fixture/plan was changed.

The existing project CPython 3.14.8 interpreter and repository pytest config were
used, with disabled sockets and no installation. Commands below used the same
arguments in each independently exported checkout (no override pytest/Ruff config):

```sh
python -m pytest -c papertrace.pytest.ini -p no:cacheprovider --disable-socket --collect-only -q test/offline/test_answer_c_integration.py
python -m pytest -c papertrace.pytest.ini -p no:cacheprovider --disable-socket -q test/offline/test_answer_c_integration.py --tb=short
python -m pytest -c papertrace.pytest.ini -p no:cacheprovider --disable-socket --collect-only -q test/offline
python -m pytest -c papertrace.pytest.ini -p no:cacheprovider --disable-socket -q test/offline --tb=short
python -m pytest -c papertrace.pytest.ini -p no:cacheprovider --disable-socket -q test/offline --ignore=test/offline/test_answer_c_integration.py --tb=short
python -m ruff check --no-cache --config papertrace.ruff.toml test/offline/test_answer_c_integration.py
python -m ruff check --no-cache --config papertrace.ruff.toml src/papertrace test/offline scripts
python -m mypy --config-file mypy.ini --cache-dir <temporary-cache> src/papertrace
python scripts/gates.py --gate schema --base 6235c33d460b48d1ff11a10624d1bcd5919ea4f0
```

| Check | Cumulative source-free base, PR15 `3f624b5` | Approved D implementation base, PR19 `3d536aa` |
|---|---|---|
| New-file collection | exit0;15 collected | exit0;15 collected |
| New-file execution | exit1;15 failed;0 errors/skip | exit1;2 passed/13 failed;0 errors/skip |
| Full offline collection | exit0;427 collected | exit0;427 collected |
| Full offline execution | exit1;360 passed/65 failed/2 skipped | exit1;411 passed/14 failed/2 skipped |
| Paired baseline, new file excluded | exit1;360 passed/50 failed/2 skipped;412 collected | exit1;409 passed/1 failed/2 skipped;412 collected |
| Targeted configured Ruff | exit0/PASS | exit0/PASS |
| Full configured Ruff | exit1;only unchanged public `scripts/paperqa_smoke.py:37 I001` | same finding, exit1 |
| mypy | exit0/PASS;5 source files | exit0/PASS;10 source files |
| Schema in a valid Git checkout | exit0/PASS | exit0/PASS |

Paired JUnit comparison: all412 pre-existing node outcomes are unchanged in each
base; the full-minus-baseline node set is exactly the15 new tests. On source-free
base,15 new failures all identify the missing real D prerequisite. Its50 baseline
failures comprise32 old-D and17 token-test missing-D assertions plus the sandbox
`test_timeout_stops_owned_test_descendants` ps PermissionError. On approved-D,
13 new failures stop at exact missing-adapter availability; adapter-mediated
behavior and fault hooks remain NOT_REACHED. The lone baseline failure is the
same sandbox ps PermissionError. These are distinct from unknown remote failures.
The two skips concern unavailable OpenCode executable checks; they are not PASS.

Initial schema attempts directly in Git archives failed exit1/ValueError because
the archives lacked Git metadata; this was a verification-fixture limitation.
Schema subsequently passed in the real cumulative candidate checkout and in the
unchanged approved-D snapshot after adding its own correct Git metadata. No gate,
source, schema or configuration was weakened or changed to obtain that result.

The candidate descends from approved test head
`3f624b5b2f685cd0133291d97206176fe7daa290`, targeting current main
`6235c33d460b48d1ff11a10624d1bcd5919ea4f0`. It retains all six previously approved
test/fixture/plan blobs and adds only this test/design plus append-only truthful
AI disclosures. Neither local setup file nor any D source is included. No new
commit/PR or independent approval exists yet. PR15 and PR19 remain open/unmerged.
The later source stage must respect the approved test ancestry, unchanged blobs,
post-approval commit/PR timing and applicable safety ADR; this is not authorization
to implement the adapter now or reuse older source commit timing as new approval.

The coding session's one shell-assisted symbol rename is retained as a disclosed
tool-use deviation within the authorized test path. Verification of its resulting
file does not grant future shell-write permission or certify native-tool enforcement.
The supervisor has not independently audited a complete raw OpenCode transcript
or provider/model identity. These offline checks invoked no PaperTrace product
model/live/real semantic evaluation. Full upstream regression, real evaluation,
OpenCode/native-engine E2E and remote CI for this candidate remain NOT_RUN.
