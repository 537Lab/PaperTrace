# Shared Full-Regression Diagnostics — Test-Preparation Design Record

Status: **test preparation only, revised twice, still RED by design**. This record
describes tests and proposed contracts; it is not an implementation, an approval, or a
claim that any remote check ran. The two new files are the whole candidate.

Date: 2026-11-23 (HKT). Role: module D build session, locally narrowed by the supervisor
to shared-diagnostics test preparation only.

Revision note: the first revision fixed the built-in-subtest prerequisite, the exact
tamper binding, the ordered workflow validator, and the pre-upload qualification function.
This second focused revision freezes the qualification CLI status protocol, binds the
upload guard to the actual gate and qualification step outcomes, scans the complete
workflow for overlapping uploads, and tests the real proposed `module.main(argv)` CLI
wrapper with a monkeypatched qualification boundary. A third narrow correction aligns the
guard with Actions implicit `success()` semantics and explicitly opts the hidden
`.local` paths into v4 artifact transport. Historical measurements from earlier drafts and
the supervisor snapshots remain separately labelled.

## 1. Base and source identities

| Item | Value / state |
|---|---|
| Checkout branch | `codex/shared-regression-tests` |
| Exact checkout HEAD | `6235c33d460b48d1ff11a10624d1bcd5919ea4f0` |
| Frozen upstream baseline | `c692d0dfeac4a0296599f7fe21a253a58b7ac12a` (tag `papertrace-upstream-baseline`) |
| New test file | `test/offline/test_full_regression_diagnostics.py` |
| New design record | `docs/team/designs/shared/20261123-regression-diagnostics-plan.md` |
| File SHA256 / byte hashes | **NOT_RUN** — no approved hashing command; supervisor verifies |
| Tracked `git diff --check` | PASS; untracked files inspected natively; independent byte/whitespace check remains supervisor-held |

The checkout contains two pre-existing local setup modifications, `opencode.jsonc` and
`.opencode/permissions.jsonc`, created by the supervisor to narrow this session. They are
**not part of this candidate** and must not enter a test publication. The candidate changes
no tracked file, no `src/`, no `scripts/`, no workflow, no ADR, no existing test, and no
dependency, lock, configuration, rule, or AI-use log entry.

## 2. GOV-02 evidence scope (fit criterion unchanged)

GOV-02 in `docs/req/requirements.yaml` remains exactly as written: every round executes
structure, complete prior regression, and three-level behaviour verification; prompt/model
changes require real fixed semantic evaluation before production. Its fit criterion remains
`unverified_prompt_or_model_production_merges == 0`, with the existing verification text
"six gates; fail-closed rather than skip-as-pass". This work does **not** change the
requirement, metric, operator, threshold, verification text, registry, or gate set.

The proposed diagnostics are **advisory observability** only:

- the legacy runner verdict (`PASS` / `FAIL` / `BLOCKED`), counting, selection, isolation,
  and cleanup remain the authority;
- diagnostics cannot upgrade a prior `FAIL` or `BLOCKED`, cannot stop another suite, and
  cannot replace a real semantic evaluation;
- a diagnostics packaging, qualification, or upload failure is recorded separately from the
  gate verdict and from diagnostics availability;
- no prompt or model changed, so no fixed semantic evaluation is claimed or required by
  this candidate;
- remote enforcement and branch protection remain **NOT_DEPLOYED_OR_VERIFIED**.

## 3. Accepted implementation direction (not implemented here)

The student-accepted direction, recorded for the later implementation stage:

- keep the implementation in the existing `scripts/full_regression.py`;
- add bounded child-hook events with incremental persistence;
- package a manifest in the parent on **all** return paths;
- write fresh per-suite/phase files;
- leave legacy counting, selection, verdict, isolation, and cleanup unchanged;
- treat diagnostics collection and packaging errors as advisory;
- do not treat diagnostics as a trusted authorization channel against malicious candidate
  code;
- add failure-only artifact transport, pre-upload qualification, and a reachable summary.

This record and the tests do not implement any of that. The exact test commit still needs a
real independent GitHub Approve by a non-implementer before shared source/workflow work.

## 4. Proposed diagnostics schema and flow

### 4.1 Feature markers and layout

- `scripts/full_regression.py` exposes `DIAGNOSTICS_SCHEMA_VERSION = 1`. Absence of this
  marker is the exact availability-RED classification for the base diagnostics tests.
- A separate `DIAGNOSTICS_TRANSPORT_SCHEMA_VERSION = 1` and callable
  `qualify_diagnostics_artifacts(...)` mark the pre-upload handoff. Absence is a separate
  exact availability-RED classification for transport-qualification tests.
- For each suite output directory, diagnostics live in `diagnostics/`:
  - `events.jsonl` (UTF-8 JSON Lines, hard cap **1,228,800 bytes** per suite/phase,
    including newlines, marker, and terminal);
  - `manifest.json` (UTF-8 JSON object, hard cap **65,536 bytes**).
- Default six directories: `.local/full-regression/{team-offline,team-runtime,upstream}`
  and their `-prior` inventory counterparts. The six-directory total cap is
  **7,766,016 bytes** = `6 × (1,228,800 + 65,536)`.
- Each diagnostics directory contains only those two regular files. Raw local
  `stdout.txt`, `stderr.txt`, and `pytest-report.json` remain outside it under the existing
  local policy.

### 4.2 Manifest fields

| Field | Contract |
|---|---|
| `schema_version` | `1` |
| `suite` | suite name |
| `mode` | `execution` or `inventory-only` (or `unknown` when genuinely unspecified) |
| `status` | `complete`, `partial`, or `unavailable` |
| `advisory` | `true` |
| `trusted` | `false` — diagnostics never authorize a verdict |
| `identity.target_sha` | 40-character lowercase Git SHA, or explicit `null`/`"unknown"` |
| `identity.control_sha` | 40-character lowercase Git SHA, or explicit `null`/`"unknown"` |
| `identity.base_sha` | 40-character lowercase Git SHA, or explicit `null`/`"unknown"` |
| `identity.source_tree_sha256` | 64-character tree digest, or explicit `null`/`"unknown"`; never substituted for a Git identity |
| `identity.job_key` | opaque non-numeric string or `null`; never a numeric job id |
| `legacy.status` | the actual legacy verdict for this suite |
| `legacy.report` | `present`, `missing`, `malformed`, `oversized`, or `not_started` |
| `events.bytes` | actual `events.jsonl` size, bounded by the cap |
| `events.terminal_present` | boolean; missing terminal is explicit |
| `events.torn_tail_ignored` | boolean; a flagged incomplete tail is not presented as complete |
| `events.truncated` / `events.sampled` | boolean; dropped data is explicit |
| `counts.unique_nodes_retained` | retained unique-node count; not an exact whole-suite total once data is dropped |
| `counts.unique_nodes_exact` | `false` whenever retention is sampled/truncated or certification is incomplete |
| `counts.pending_live` | retained pending-live count |
| `counts.collection_errors` | retained collection-error count |
| `limits` | exact `{events_bytes: 1228800, manifest_bytes: 65536, bundle_bytes: 7766016}` |
| `error` | `null`, or a bounded object `{type, detail_state, detail}` with `detail_state` in `available`/`truncated`/`unavailable`; `detail` is at most 512 UTF-8 bytes and contains no newline, carriage return, or ESC |

The manifest must not contain `longrepr`, `longreprtext`, `locals`, `captured`, environment
dumps, raw stdout/stderr, or absolute host paths.

### 4.3 Event fields and writing guarantee

Each JSONL line is one object:

- `schema_version`: `1`;
- `suite`: suite name;
- `event`: `collection`, `collection_error`, `report`, or `terminal`;
- collection: `nodeid`;
- collection error: `nodeid`, `kind` in `missing-dependency`/`collection-failure`, bounded
  error data;
- report: `when` in `setup`/`call`/`teardown`, `nodeid`, `outcome` in
  `passed`/`failed`/`skipped`/`xfailed`/`xpassed`, optional bounded error object;
- a `subtest` string for a built-in `_pytest.subtests` report, bounded and containing the
  subcase message when safely available;
- terminal: completion/count marker.

Writing is a **single-writer best-effort** guarantee: the child serializes and writes whole
lines, but an interruption (timeout, cancellation, process exit) can leave a torn tail.
The manifest must flag that case (`torn_tail_ignored`, missing terminal) rather than claim a
complete file. The parent must not present a torn tail as valid JSON.

The child bounds serialized bytes after escaping and never intentionally splits a UTF-8
sequence or emits invalid JSON. Node ids, parameters, exception text, subtest context, and
messages are untrusted data: they are bounded and serialized, never evaluated with `eval`,
`exec`, or `compile`. A fingerprint, if present, is advisory only.

### 4.4 Parent flow and freshness

1. Resolve the suite output root.
2. Create `diagnostics/`. If it is a symlink or non-directory, unlink it (never follow) and
   create a real directory.
3. For `events.jsonl` and `manifest.json`: if the existing entry is a regular file or
   symlink, unlink it without following; if it is a directory or other non-regular type,
   mark diagnostics unavailable and **do not recursively delete** the unexpected entry.
4. Reject a stale file by size before reading it; never load an oversized untrusted file
   wholesale.
5. Build the existing scrubbed child environment and add exactly one diagnostic path under
   the output root. The path variable name contains `DIAGNOSTIC`; its value is exactly the
   intended diagnostics directory or events file. Trusted workflow metadata and credentials
   are not forwarded to the child.
6. Let the child append bounded events incrementally.
7. Package the manifest on every return path, including spawn failure, timeout,
   missing/malformed/oversized legacy output, and unsafe artifact paths.
8. On packaging failure, expose an advisory summary on the returned suite report
   (`diagnostics.status = unavailable`, `trusted = false`, bounded reason). Never raise,
   stop later suites, or alter the legacy verdict.
9. In a full run, aggregate `diagnostics.bundle_bytes` over the six default directories
   only and expose the six `diagnostics.suites` entries. Create `full-regression.json` even
   when a suite's diagnostics packaging failed. Ignore rogue directories outside the six.
10. Leave raw local files in place; they are not part of the upload allowlist.

These are check-time path guards, not an OS sandbox. Malicious candidate code can tamper
with its own diagnostics; the design therefore marks diagnostics untrusted and never uses
them to certify a result.

## 5. Pre-upload qualification and CLI status protocol

The six-file allowlist alone does not prove provenance, ownership, regularity, or bounds.
The proposed minimal handoff is:

- `scripts/full_regression.py` exposes
  `qualify_diagnostics_artifacts(root, output, *, expected_identity, suites=(...))`;
- the same script exposes a CLI mode `--qualify-diagnostics` for the workflow step;
- the function returns
  `{"status": "qualified"|"withheld", "files": [relative six paths or empty], "reasons": [...]}`
  and never modifies the legacy gate report.

### 5.1 CLI invocation and independent metadata

Supported invocation shape (one explicit command, no shell composition):

```text
python .control/scripts/full_regression.py --qualify-diagnostics
  --root "$GITHUB_WORKSPACE/target"
  --output "$GITHUB_WORKSPACE/target/.local/full-regression"
  --expected-target-sha "$PAPERTRACE_HEAD"
  --expected-control-sha "${{ steps.control.outputs.sha }}"
  --expected-base-sha "${{ steps.control.outputs.base }}"
```

The workflow checker accepts only `$PAPERTRACE_HEAD`/`${{ env.PAPERTRACE_HEAD }}` for the
target, `${{ steps.control.outputs.sha }}` for the control verifier, and
`${{ steps.control.outputs.base }}` for the comparison base. It rejects literal candidate
SHAs, manifest paths, `target/.local` reads, and any other self-described metadata. The
trusted qualification function derives `source_tree_sha256` from the target root itself.
The CLI passes exactly the three trusted Git identities to the function's
`expected_identity`; it does not accept the candidate manifest as proof.

The supported executable form is one `set -euo pipefail` line followed by exactly one
command line. Comments, `echo`/`printf`, `exit 0`, additional commands, shell operators,
wrong root/output, and missing/extra flags are rejected. This is a narrow static command
form, not a general shell or Actions-expression engine.

### 5.2 Status and exit mapping

| Function result / condition | CLI exit | Transport effect |
|---|---|---|
| `status="qualified"` and exactly six current regular paths | `0` | The qualification step outcome is `success`; the upload guard may allow the six literal paths |
| `status="withheld"` | `1` | Nonzero; the upload guard is false even if the six physical files still exist |
| Validation error, unknown status, missing/invalid trusted metadata | `2` | Nonzero; upload guard false; bounded diagnostic output, no success |
| Unexpected exception outside the documented validation errors | propagates | Not converted to qualified/success |

Withholding does **not** depend on deleting or emptying files. The six physical paths may
remain on disk; the upload condition is
`failure() && !cancelled() && steps.<gate-id>.outcome == 'failure' && steps.<qualify-id>.outcome == 'success'`,
so only exit 0 for `qualified` (plus the actual gate failure and an uncancelled job) can
authorize transport. The CLI tests include a withheld case where all six files still exist.

Checks before transport:

1. Only the six current-suite directories are considered; prior, rogue, raw, environment,
   cache, and lock material is excluded by construction.
2. Each accepted path is a regular file, not a symlink, and resolves under the expected
   diagnostics directory. Escaping paths and symlinked directories are withheld.
3. `events.jsonl` is at most 1,228,800 bytes; `manifest.json` is at most 65,536 bytes; the
   six-directory aggregate is at most 7,766,016 bytes. File sizes are checked before
   reading; oversized material is withheld without wholesale loading.
4. Manifest identity matches the supplied current-run `expected_identity` exactly:
   `target_sha`, `control_sha`, `base_sha`, and `source_tree_sha256`. A null/unknown
   expected value requires explicit null/unknown in the manifest; a real expected value
   requires an exact match. Stale, missing, or invented provenance is withheld.
5. `advisory` is true and `trusted` is false. Exactly `events.jsonl` and `manifest.json`
   are returned per suite.
6. Explicitly partial material (for example a timeout manifest with
   `status="partial"`, missing terminal, and torn-tail/truncation flags) may be qualified
   only when it is regular, bounded, and provenance-current. Unqualified partial material is
   withheld. This policy is tested in the runner handoff.

The workflow qualification step runs after the gate with `failure()` or an explicitly
supported `failure() || cancelled()` form. Cancellation is conservative: qualification may
run, but the upload guard below explicitly requires `!cancelled()` in addition to the
actual gate failure outcome, so cancellation after a gate failure does not upload. Static
YAML establishes ordering and condition shape; it cannot prove runtime provenance. The
runner qualification and CLI tests are the executable contract for provenance, regular
files, symlinks, bounds, partial policy, and exit mapping.

## 6. Workflow and artifact contract

- The actual regression job has no job-level `if` that can permanently skip the chain.
- The actual regression gate has an explicit step `id` and no step-level `if`; only an
  ordinary executed gate has a trustworthy `failure` outcome. Pre-gate failure or
  `if: false`/skipped gate leaves the gate outcome non-`failure`, so upload is not eligible.
- Ordered chain in the actual regression job: trusted base-verifier validation → gate id →
  qualification → one diagnostics upload → `always()` summary.
- Exactly one diagnostics-overlapping `actions/upload-artifact` step across the **whole
  workflow** (any action SHA; the tests do not lock a version). The checker scans every job
  and rejects pre-gate duplicates, other-job diagnostics uploads, broader raw-material
  uploads (`target/.local`, `full-regression`, raw stdout/stderr/report), wildcards and
  overlapping paths. Unrelated non-overlapping artifact uploads remain allowed.
- The upload condition explicitly models Actions status semantics:
  `failure() && !cancelled() && steps.<gate-id>.outcome == 'failure' && steps.<qualify-id>.outcome == 'success'`
  (parenthesized gate form accepted). Actions applies implicit `success()` when an `if`
  expression contains no status-check function; an outcome-only guard would therefore be
  skipped in the FAIL/BLOCKED case because the preceding gate failed. Explicit `failure()`
  keeps the failed-step case eligible, and `!cancelled()` prevents a cancelled job from
  uploading. The guard contains no `success()`/`always()` and no job-level failure shortcut.
- Its path allowlist is exactly six literal files:
  - `target/.local/full-regression/team-offline/diagnostics/events.jsonl`
  - `target/.local/full-regression/team-offline/diagnostics/manifest.json`
  - `target/.local/full-regression/team-runtime/diagnostics/events.jsonl`
  - `target/.local/full-regression/team-runtime/diagnostics/manifest.json`
  - `target/.local/full-regression/upstream/diagnostics/events.jsonl`
  - `target/.local/full-regression/upstream/diagnostics/manifest.json`
- No wildcard, no `-prior` directory, no rogue suite, no `stdout.txt`, `stderr.txt`,
  `pytest-report.json`, environment/home/cache content, or lock/secret file.
- `if-no-files-found` is `warn`/`ignore`; missing or withheld diagnostics stay
  distinguishable from a failed upload.
- `with.include-hidden-files: true` is required. The six allowed paths are beneath
  `target/.local`, and `actions/upload-artifact` v4.4+ excludes hidden files/directories by
  default; literal paths alone do not bypass that filter. The checker accepts YAML boolean
  `true` or the action input string `'true'`, and rejects missing/`false`/`'false'`. This is
  only an opt-in for the already allowlisted hidden material, not permission to upload
  directories, raw output, secrets, or to change the action version. References:
  GitHub Actions status-check functions documentation and the `actions/upload-artifact` v4
  README section "Uploading hidden files".
- The gate step keeps `set -euo pipefail`, its original failing exit, no
  `continue-on-error`, and no `|| true`/`|| exit 0`/`set +e`.
- A later summary step with `if: always()` writes `$GITHUB_STEP_SUMMARY` and references the
  actual gate, qualification, and upload step **outcomes** (not only conclusions possibly
  rewritten by `continue-on-error`), plus `cancelled`/`job.status`. Thus a failed upload
  cannot hide the gate summary.

Accepted static condition subset (exact normalized strings):

- qualification: `failure()`, `failure() || cancelled()`, `cancelled() || failure()`;
- upload:
  `failure() && !cancelled() && steps.<gate>.outcome == 'failure' && steps.<qualify>.outcome == 'success'`
  and the parenthesized gate form;
- summary: `always()`.

Any other expression is refused, including the old outcome-only guard (implicit
`success()`), a guard missing `!cancelled()`, `failure() || true`, `failure() && false`,
`success()`, and `always() && false`. The validator uses this narrow subset and a
single-command shell form; it is not a general Actions-expression or shell engine.

Static state table tied to the parsed real references and explicit status functions:

| Scenario | `failure()` | `cancelled()` | Gate outcome | Qualification outcome | Upload eligible? |
|---|---|---|---|---|---|
| PASS | false | false | `success` | `success` | No |
| Gate FAIL/BLOCKED + qualified | true | false | `failure` | `success` | Yes |
| Cancelled after gate already failed + qualified | true | true | `failure` | `success` | No |
| Withheld/error | true | false | `failure` | `failure` | No |
| Missing diagnostics | true | false | `failure` | `skipped` | No |
| Failure before gate / skipped gate | true | false | `skipped` | `success` | No |
| Gate cancelled | true | true | `cancelled` | `success` | No |

The eligible predicate explicitly tested is
`failure() and not cancelled() and gate_outcome == 'failure' and qualify_outcome == 'success'`.
Cancellation is an independent job fact; the gate's recorded failure outcome need not
change. The old outcome-only guard is **not** eligible because it lacks an explicit status
function and thus receives implicit `success()`, which is false after the preceding gate
failed. A failed upload does not alter the gate's original failing exit; the always-summary
still runs and records the upload outcome. This table is a static contract check, not
Actions E2E. Actual GitHub Actions execution remains **NOT_RUN**.

The checker's negative matrix includes:

- comment-only qualification mention followed by `printf`/`exit 0`;
- wrong root/output or candidate-manifest-derived expected metadata;
- a second `always()` diagnostics upload before the gate, in another job, or a broader raw
  `target/.local` upload;
- gate `if: false`, a job-level `failure()` condition, or other gate/job conditions that can
  skip the chain;
- substring/extra conditions such as `failure() || true`, `failure() && false`,
  `success()`, unguarded qualification success, gate `success`, and `always() && false`;
- the old outcome-only expression (implicit `success()`), and a guard missing
  `!cancelled()`;
- missing/`false`/`'false'` `include-hidden-files`.

Positive mutations rename the gate/qualification/upload step ids and use the alternate
trusted target reference `${{ env.PAPERTRACE_HEAD }}`; the checker binds by actual
references rather than incidental names. The synthetic upload uses YAML boolean `true` for
`include-hidden-files`; the string `'true'` is also accepted.

## 7. Coverage-to-test mapping

| Constraint | Tests |
|---|---|
| Legacy success/failure/skip/xfail counting and raw local files unchanged | `test_legacy_success_verdict_and_raw_files_are_unchanged`, `test_legacy_failure_phases_and_skip_verdicts_are_unchanged` |
| Legacy timeout keeps partial inventory/outcomes; `ps` not required | `test_legacy_timeout_keeps_partial_inventory_and_outcomes` |
| Legacy spawn failure, missing/malformed/oversized report classification | `test_legacy_spawn_failure_is_blocked`, `test_legacy_missing_malformed_and_oversized_reports_are_classified` |
| Collection dependency vs collection failure distinction | `test_legacy_collection_dependency_and_collection_failure_are_distinct` |
| Pending live and inventory-only legacy modes | `test_legacy_pending_live_and_inventory_only_modes_are_unchanged` |
| Legacy full-run PASS remains possible | `test_legacy_full_runner_can_still_pass_a_complete_prior_suite` |
| Built-in subtests fixture runs with only the default child plugins; legacy 2 failed / 2 passed / 0 collection errors | `test_legacy_builtin_subtests_fixture_runs_without_external_plugin` |
| Success bundle schema, identity nulls, terminal, setup/call/teardown events | `test_diagnostics_success_bundle_schema_identity_and_terminal` |
| Setup/call/teardown failures and bounded error details | `test_diagnostics_record_setup_call_and_teardown_failures` |
| Collection dependencies, collection failures, no raw traceback | `test_diagnostics_collection_dependency_and_collection_failure_are_explicit` |
| Pending live produces no execution events; inventory-only has no report events | `test_diagnostics_pending_live_and_inventory_only_are_explicit` |
| Timeout keeps completed events, missing terminal, incomplete certification | `test_diagnostics_timeout_keeps_completed_events_and_incomplete_status` |
| Spawn failure packages an advisory manifest | `test_diagnostics_spawn_failure_is_packaged_as_advisory_unavailable` |
| Missing/malformed/oversized legacy input classification and bounded reading | `test_diagnostics_missing_malformed_and_oversized_legacy_reports_are_classified` |
| Oversized stale events rejected before wholesale load (memory bound) | `test_diagnostics_oversized_stale_event_file_is_not_loaded_wholesale` |
| Fresh files, no stale append, repeated runs | `test_diagnostics_stale_and_repeated_runs_are_fresh_not_appended` |
| Symlinked directory/artifacts not followed; outside target untouched | `test_diagnostics_symlink_paths_are_not_followed` |
| Directory at `events.jsonl` is advisory, not recursively deleted | `test_diagnostics_directory_at_event_path_is_advisory_and_not_deleted` |
| Manifest packaging failure is advisory; FAIL/BLOCKED preserved | `test_diagnostics_manifest_packaging_failure_is_advisory_and_preserves_verdict` |
| Tamper fault bound to one unique diagnostic env entry and exact current-run events/manifest paths; proof after writes; parent observes torn content and overwrites the fake manifest | `test_diagnostics_tamper_fault_is_bound_to_exact_current_run_paths` |
| Event/manifest byte budgets, sampling/truncation flags, exactness flags | `test_diagnostics_event_and_manifest_budgets_hold_for_large_inventory` |
| Six current/prior directories, bundle total, rogue exclusion | `test_diagnostics_six_current_and_prior_directories_fit_the_bundle_budget` |
| Built-in subtest failed subcase visible as a `subtest` report, not only a parent failure | `test_diagnostics_builtin_subtest_failure_is_visible_when_available` |
| Git identities vs tree digest, missing provenance null, non-numeric job key | `test_diagnostics_missing_provenance_is_null_and_identities_are_distinct` |
| Child environment adds only the diagnostic path; no credentials/metadata | `test_diagnostics_child_environment_adds_only_the_diagnostic_path` |
| Untrusted long/non-UTF-8-boundary message and node id bounded, never evaluated | `test_diagnostics_untrusted_messages_are_bounded_and_not_evaluated` |
| Diagnostics packaging failure cannot stop other suites; summary written | `test_diagnostics_failure_does_not_stop_other_suites_and_summary_is_written` |
| Pre-upload qualification accepts current regular bounded six-file bundle | `test_transport_qualification_accepts_current_bounded_six_file_bundle` |
| Pre-upload qualification withholds stale/unknown provenance | `test_transport_qualification_withholds_stale_or_unknown_provenance` |
| Pre-upload qualification withholds symlink/escaping material | `test_transport_qualification_withholds_symlink_or_escaping_material` |
| Pre-upload qualification withholds oversized material without wholesale read | `test_transport_qualification_withholds_oversized_material` |
| Explicit partial policy is qualified consistently | `test_transport_qualification_allows_explicit_partial_bundle` |
| CLI exits 0 only for qualified and forwards exact root/output/trusted identity | `test_transport_cli_qualified_exits_zero_and_forwards_trusted_identity` |
| CLI withheld exits 1 while the six physical files remain | `test_transport_cli_withheld_exits_one_and_keeps_six_physical_files` |
| CLI validation error/unknown status exits 2 | `test_transport_cli_validation_error_exits_two` |
| CLI requires independent metadata before calling qualification | `test_transport_cli_requires_independent_metadata_before_qualifying` |
| CLI does not hide unexpected exceptions | `test_transport_cli_does_not_hide_unexpected_exception` |
| Gate step keeps original failing exit | `test_regression_gate_step_keeps_its_original_failing_exit` |
| Supported failure/cancellation condition policies accepted | `test_workflow_transport_chain_accepts_supported_failure_policies` |
| Substring tricks `failure() || true`, `failure() && false`, `success()`, unguarded upload, and invalid summary conditions rejected | `test_workflow_transport_chain_rejects_substring_condition_tricks` |
| Ordered trusted validation/gate/qualification/upload/summary in the actual regression job; unrelated-jobs and reordered steps rejected | `test_workflow_transport_chain_requires_ordered_regression_job_chain` |
| Six-literal allowlist rejects prior/rogue/raw/wildcard and `if-no-files-found: error` | `test_workflow_transport_allowlist_rejects_prior_rogue_raw_or_wildcard` |
| Summary always reachable; records actual gate, qualification, upload outcomes and cancellation | `test_workflow_summary_records_actual_outcome_and_cancellation` |
| Comment/printf/exit cannot masquerade as qualification | `test_workflow_rejects_comment_or_print_only_qualification` |
| Wrong root/output or candidate-manifest-derived metadata rejected | `test_workflow_rejects_wrong_root_output_or_self_described_metadata` |
| Pre-gate, other-job, or broader raw uploads rejected by whole-workflow scan | `test_workflow_rejects_pre_gate_other_job_or_broader_raw_uploads` |
| Skipped gate or job-level condition cannot authorize upload | `test_workflow_rejects_skipped_gate_or_job_conditions` |
| Renamed step ids and alternate trusted target reference accepted | `test_workflow_accepts_renamed_ids_and_trusted_metadata_variant` |
| Unrelated non-overlapping artifact upload remains allowed | `test_workflow_allows_unrelated_non_overlapping_upload` |
| Hidden-file transport opt-in: boolean/string `true` accepted; missing/`false` rejected | `test_workflow_transport_requires_hidden_file_opt_in` |
| State table binds upload to explicit `failure() && !cancelled()` plus actual gate failure + qualification success; cancellation after gate failure withholds | `test_workflow_state_table_binds_upload_to_gate_and_qualification` |
| Old outcome-only guard rejected because implicit `success()` fails after the preceding gate | `test_workflow_rejects_outcome_only_upload_with_implicit_success` |
| Real `ci.yml` currently has no referenced gate id/qualified transport chain | `test_real_workflow_exposes_qualified_failure_transport_chain` |

## 8. Measurements

### 8.1 Author pre-revision historical observations (first draft, 2026-11-23)

These are retained as history, not as current post-revision results.

| Check | Historical result |
|---|---|
| First-draft new file collect-only | 32 tests collected, exit 0 |
| First-draft new file `--tb=short` | 9 passed, 22 failed, 1 skipped, exit 1, 12.18 s |
| Existing runner/events targeted | 50 passed, exit 0, 19.24 s |
| Full `test/offline` | 359 passed, 26 failed, 3 skipped, exit 1, 59.55 s |
| Full minus new file | 350 passed, 4 failed, 2 skipped, exit 1, 47.40 s |
| Ruff new file / targeted existing | PASS / PASS |
| Full Ruff | 1 pre-existing `scripts/paperqa_smoke.py:37` I001 |
| mypy / schema / preflight | PASS / PASS / PASS |
| Git HEAD | exact approved SHA |
| File SHA256 | NOT_RUN |
| Actions execution, remote enforcement, product model/live/upstream | NOT_RUN |

The fourth-vs-fifth baseline difference was an environment observation: the known
`test_timeout_stops_owned_test_descendants` `ps` sandbox failure passed in the author
environment. No fix is claimed.

### 8.2 Supervisor pre-revision snapshot (2026-11-23 07:29 HKT)

Recorded separately by the supervisor before this revision:

- new32: 9 passed / 22 failed / 1 skipped, 0 collection errors. Failures: 19 runner-marker
  availability + 3 workflow availability. The existing subtest skip was the external-plugin
  prerequisite bug corrected by this revision.
- existing50: 49 passed / 1 failed (`ps` PermissionError).
- full388: 358 passed / 27 failed / 3 skipped.
- paired356: 349 passed / 5 failed / 2 skipped; 356 old node states identical between full
  and paired; delta exactly new32.
- baseline5: 4 local narrowed-setup configuration assertions + 1 `ps` sandbox failure.
  Author 50/0 and baseline 4 were different environment observations, not fixes.
- New/target Ruff PASS; full Ruff only unchanged `scripts/paperqa_smoke.py:37` I001;
  mypy5 PASS; schema PASS with remote enforcement `NOT_DEPLOYED_OR_VERIFIED`; static
  preflight PASS. 331 protected tracked files, setup hashes, input bytes, and index
  unchanged. This was static permission validation, not native-engine E2E.

### 8.3 Supervisor pre-closure snapshot (2026-11-23 08:28 HKT)

Recorded separately by the supervisor before this closure:

- new52: 25 passed / 27 failed / 0 skipped (20 base-marker availability, 6 transport
  marker/entry availability, 1 real-workflow availability).
- existing50: 49 passed / 1 failed (`ps` PermissionError).
- full408: 374 passed / 32 failed / 2 skipped.
- paired356: 349 passed / 5 failed / 2 skipped.
- All 356 old node states identical between full and paired.
- Baseline5: 4 local narrowed-setup configuration assertions + 1 sandbox `ps`
  PermissionError. Author 50-pass and paired 4-fail are different environment observations,
  not code fixes.
- New/target Ruff PASS; full Ruff only unchanged shared `paperqa_smoke.py:37` I001; mypy5
  and schema and static preflight PASS. 331 protected tracked files and setup bytes
  unchanged, index empty. Student drafts unchanged during supervisor verification.
- Actual behaviour behind the missing markers, linked tamper execution, and Actions E2E
  remained NOT_REACHED/NOT_RUN.

### 8.4 Post-closure measurements

Measured after this closure with the exact approved commands:

| Check | Post-closure result |
|---|---|
| New file collect-only | 68 tests collected, exit 0 |
| New file `--tb=short` | 36 passed, 32 failed, 0 skipped, exit 1, 9.06 s |
| Existing runner/events targeted | 50 passed, exit 0, 9.93 s |
| Full `test/offline` | 386 passed, 36 failed, 2 skipped, exit 1, 33.27 s |
| Full minus new file | 350 passed, 4 failed, 2 skipped, exit 1, 26.77 s |
| Ruff new file / targeted existing | PASS / PASS |
| Full Ruff | 1 unchanged pre-existing `scripts/paperqa_smoke.py:37` I001 |
| mypy / schema / preflight | PASS (5 files) / PASS (27 requirements) / PASS |
| Git identity/status/diff checks | HEAD matches; two pre-existing setup modifications; two candidate paths untracked; tracked `git diff --check` PASS |
| File SHA256 | NOT_RUN (no approved hashing command) |
| Actions execution, remote enforcement, product model/live/upstream | NOT_RUN |

### 8.5 Supervisor action-compatibility snapshot (2026-11-23 08:56 HKT)

Recorded separately by the supervisor before this correction:

- new68: 36 passed / 32 failed / 0 skipped.
- existing50: 49 passed / 1 failed (`ps` PermissionError).
- full424: 385 passed / 37 failed / 2 skipped.
- paired356: 349 passed / 5 failed / 2 skipped.
- All 356 old full/paired node states identical; delta exactly the 68 new tests.
- Baseline5: 4 narrowed-local-setup contract assertions + 1 sandbox `ps` PermissionError.
  Author 50-pass and paired 4-fail are a different environment observation, not code fixes.
- New/target Ruff PASS; full Ruff only unchanged shared `paperqa_smoke.py:37` I001; mypy5,
  schema and preflight PASS. 331 protected tracked files, both setup hashes and draft hashes
  unchanged during independent checks, index empty.
- 32 availability failures = 20 base marker + 6 qualification function + 5 CLI + 1 real
  workflow missing referenced gate id. CLI, tamper and qualification runtime behaviour
  remains NOT_REACHED.
- The four former handoff mutants are correctly rejected. The new total is net +16; three
  old positive parameter ids were replaced when their conditions changed, so this record
  does not claim every old-52 exact node id remains identical.

### 8.6 Post-correction measurements

Measured after the two Actions-compatibility corrections with the exact approved commands:

| Check | Post-correction result |
|---|---|
| New file collect-only | 71 tests collected, exit 0 |
| New file `--tb=short` | 39 passed, 32 failed, 0 skipped, exit 1, 8.75 s |
| Existing runner/events targeted | 50 passed, exit 0, 9.92 s |
| Full `test/offline` | 389 passed, 36 failed, 2 skipped, exit 1, 33.25 s |
| Full minus new file | 350 passed, 4 failed, 2 skipped, exit 1, 25.12 s |
| Ruff new file / targeted existing | PASS / PASS |
| Full Ruff | 1 unchanged pre-existing `scripts/paperqa_smoke.py:37` I001 |
| mypy / schema / preflight | PASS (5 files) / PASS (27 requirements) / PASS |
| Git identity/status/diff checks | HEAD matches; two pre-existing setup modifications; two candidate paths untracked; tracked `git diff --check` PASS |
| File SHA256 | NOT_RUN (no approved hashing command) |
| Actions execution, remote enforcement, product model/live/upstream | NOT_RUN |

## 9. Real RED categories (current post-correction state)

At this commit the new file is intentionally RED:

- **Availability RED — runner base diagnostics (20 tests).** These include the success,
  phase, collection, pending, timeout, spawn, legacy-report, stale/fresh, symlink, unsafe
  path, packaging, tamper, budget, six-directory, provenance, child-env, untrusted-text,
  failure-isolation, and built-in-subtest diagnostic tests. They stop at the absent
  `DIAGNOSTICS_SCHEMA_VERSION`; no behavioural diagnostic assertion behind the marker is
  claimed to have executed. The tamper test checks availability before injection.
- **Availability RED — qualification function (6 tests).** They stop at the absent
  `DIAGNOSTICS_TRANSPORT_SCHEMA_VERSION`/`qualify_diagnostics_artifacts`; no provenance,
  symlink, oversized, or partial qualification function assertion is claimed to have
  executed.
- **Availability RED — qualification CLI (5 tests).** They stop at the same absent
  transport marker before invoking the proposed `module.main(argv)` wrapper; no exit-code,
  identity-forwarding, or physical-file assertion is claimed to have executed.
- **Availability RED — real workflow transport (1 test).** The actual `ci.yml` has no
  referenced gate id/qualification/upload/summary chain; the validator reports the first
  exact missing piece (currently the gate step id).
- **Passing controls (39 tests).** Eight legacy runner controls, one built-in-subtest
  legacy control (2 failed / 2 passed / 0 collection errors), the gate-exit control, and
  twenty-nine synthetic workflow-contract checks. The synthetic checks **actually executed**:
  four supported explicit-status/condition policies, ten invalid condition/guard mutants,
  the old outcome-only implicit-success negative, ordered-chain negatives, the four A–D
  mutants, renamed ids/alternate trusted metadata, unrelated upload allowance, hidden-file
  opt-in positives/negatives, the cancellation/status-function state table, four allowlist
  negatives, and summary reachability. They reject the synthetic invalid workflows without
  claiming missing runner/workflow implementation.
- **No skips or xfails.** The previous external `pytest_subtests` skip and plugin request
  are removed; the installed built-in fixture runs a real child.
- Behaviour RED is not pre-classified. Once the markers and workflow land, the same tests
  become behavioural assertions with visible tracebacks. The CLI/tamper/qualification
  behaviour behind the markers remains NOT_REACHED in this candidate.

The four full-suite `test_opencode_configuration.py` failures remain the supervisor's known
local-narrowing artefacts, not diagnostics RED. The two `test_opencode_workflow.py` skips
remain the unavailable-OpenCode-executable limitation.

## 10. Collection safety and limitations

- The new test module imports only the standard library, `pytest`, and `yaml` at module
  level. It does not import `scripts/full_regression.py` or any diagnostic API during
  collection.
- The trusted runner is loaded at runtime with `importlib`; a missing future feature is a
  precise runtime availability RED, not an import error.
- No helper is imported from the non-package `test/offline` tree, and no diagnostics
  fallback is implemented in test helpers. The workflow validator is test-side static
  contract checking; it is not a runner implementation.
- The CLI tests feature-gate on the transport marker, then monkeypatch the actual
  qualification-call boundary to exercise only control flow. The stub is not a validator
  fallback and does not implement production qualification.
- Synthetic pytest repositories are created under `tmp_path`; there is no third persistent
  file and no write outside the temporary tree.
- The built-in `subtests` fixture is used without installing or requesting
  `pytest_subtests`; the child runs with only `pytest_socket`.
- Child processes use the existing scrubbed environment; no network, credential, live
  provider, product model, or upstream full-regression execution occurs.
- Workflow tests parse YAML only; no GitHub Actions job is executed. The qualification
  command check is a narrow single-command parser (`shlex` plus an explicit token/flag
  allowlist), not a general shell or Actions-expression engine. Comments, `echo`/`printf`,
  `exit`, operators, wrong root/output, and self-described metadata are rejected.
- The CLI result reaches workflow gating only through the qualification step outcome:
  exit 0/qualified → `success`; withheld → `1`; validation/unknown → `2`; unexpected
  exception propagates. The physical six paths may remain; the upload guard requires
  `failure() && !cancelled() && steps.<gate>.outcome == 'failure' && steps.<qualify>.outcome == 'success'`,
  and the hidden `.local` files require `include-hidden-files: true`.
- The static state table is a YAML/condition contract, not Actions E2E.
- These tests are behavioural contracts against a trusted local runner, not an OS sandbox
  or remote enforcement proof. Malicious candidate code can tamper with its own diagnostic
  files; the manifest and events are intentionally marked untrusted.
- Independent file hashing, byte/whitespace verification, and any later packaging/remote
  operation remain supervisor-held.

## 11. Coordinated owner changes required by existing tests

Two existing assertions are incompatible with the accepted failure-gated upload and must be
updated deliberately in the later implementation PR; this test-preparation candidate does
not edit them:

1. `test/offline/test_gates.py::test_fixed_evaluation_and_workflow_contracts` currently
   forbids any step-level `if` or `continue-on-error` and assumes the gate command is the
   last step of every job. The accepted chain requires step-level conditions and a later
   summary.
2. `test/offline/test_gates.py::test_metadata_ci_uses_trusted_base_without_running_target_code_with_token`
   asserts that `workflow["jobs"]["regression"]["steps"][-1]["run"]` contains `--scope full`.
   Appending qualification/upload/summary steps invalidates the positional assumption.

The implementation PR must locate the gate step by content, allow only the diagnostics
exceptions, keep the gate's original failing exit, and prevent success uploads. That is a
reviewed contract change, not permission to weaken the gate or delete old assertions
silently.

## 12. Truthful AI/session attribution

- Authoring assistant model/provider identity is **self-reported** by the session:
  DeepSeek V4.1 Flash 1017, provider ID `deepseek`, model ID `deepseek-flash`; it is not
  independently verified by these offline tests.
- No assistant session id, token count, cost, human approval, remote run, or enforcement
  result is invented in this record.
- The student approved the exact two-file test-preparation scope and the isolated
  supervisor setup on 2026-11-23 HKT. That is not an independent GitHub test approval.
- The exact eventual test commit still requires a real GitHub Approve by another student
  who did not implement the tests. PR21 approval does not authorize this work or a merge.
- The assistant's own provider inference is distinct from any PaperTrace product-model
  invocation. Offline product/live/network checks in this repository do not measure the
  assistant's provider behaviour. No product model, network, live provider, or upstream
  full regression was invoked.

## 13. Remaining owner ADR/adoption decisions

- Adopt or revise the proposed base-diagnostics schema shape, field names, status values,
  exact byte limits, and `subtest` reporting field.
- Adopt or revise the minimal pre-upload qualification entry, its return shape, the CLI
  status/exit protocol, the supported single-command form, and the partial-material policy.
- Require the regression gate to have an explicit step id and no step `if`; the upload
  guard must explicitly include `failure() && !cancelled()` and bind to that gate's
  `failure` outcome plus qualification `success`. An outcome-only guard is rejected because
  implicit `success()` is false after the preceding gate fails.
- Require `with.include-hidden-files: true` (YAML boolean or action string `'true'`) for the
  six allowlisted paths under `target/.local`; missing/false is not transportable. This does
  not authorize directories, raw output, secrets, or an action-version change.
- Choose the cancellation policy explicitly. This draft chooses conservative withholding:
  cancellation may qualify diagnostics but never authorizes upload; the summary records
  unknown/partial availability.
- Approve the protected-path implementation (`scripts/full_regression.py`, workflow, and any
  gate-summary changes) with the required ADR, independent current-head safety review, and
  trusted-main adoption.
- Select the upload action version, retention, and exact summary mechanism/step ids; the
  tests intentionally do not lock a specific action SHA.
- Update the two existing workflow assertions described in section 11, with review.
- Record the implementation PR's real AI-use log entry and review memo; this test-only
  candidate does not fabricate one.
- Verify file hashes, whitespace, remote GitHub enforcement, and branch protection outside
  this offline session. None of those is claimed here.
