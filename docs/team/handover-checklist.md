# PaperTrace | Module handover and merge checklist

Purpose: each member supplies **real evidence** item by item in their own module PR/local handover. This page gives the checking semantics and does not pre-fill any approval or PASS. `[ ]` means still to be actually verified, not a blank-conclusion template. The team private repository https://github.com/537Lab/PaperTrace has been created, and PR links must be real; branch protection and required checks are still not in effect (403), that item is explicitly marked as pending, and PRs, approvals, or pass records must not be invented.

## 1. First decide whether review can start

- [ ] The claim is one complete feature among A/B/C/D/E, with this module's business logic, its own view, and requirements/design/tests, not just CI or documentation.
- [ ] The handover note lists the actual changed paths, baseline/branch/commit or current diff, what was and was not done, reproducible commands, and known risks, and does not present plans from the assignment document as implemented.
- [ ] The author, upfront test/plan approver, independent reviewer, and integrator for this round follow the rotation and do not self-review; a co-implementer does not serve as the PR's independent approver.
- [ ] A human-approved plan/test version, its time, and the allowed write paths exist and predate implementation; approval is renewed after any change to requirement or test semantics.
- [ ] The real OpenCode Plan → human approval → confirmed Build permission → Build → Verify record is complete; it is not an unsupervised one-click run.

Without this evidence, give `CHANGES REQUIRED` or explicitly BLOCKED for the relevant parts; the amount of finished code does not offset a missing process.

## 2. Feature handover focus for each module

| Module | Positive behavior to demonstrate at minimum | Blocking/negative behavior that must be reproducible | Exact objects handed downstream |
|---|---|---|---|
| A | Explicit file selection, per-item import status, generation of a pinned-version snapshot; the same version is replayable | A same-name replacement yields a new version; a partial failure is not called complete; history does not drift; path traversal is rejected | CorpusSnapshot, version/status verification ports; not a mutable PaperQA Docs |
| B | Evidence bound to a snapshot; source text/summary/locator kept separate; third-party mapping observable | Old/foreign versions rejected; errors do not fall back to a whole-library answer; no human accepted is produced; no foreign pickle is imported | EvidenceRecord; the neutral generation result/raw citations/actually-sent mapping authorized by D |
| C | Compare sources, human accept/exclude, ledger append, revision/digest replay | No decision means pending; AI cannot approve; conflict on an old revision; a source-text change does not reuse the old review | ReviewDecision and a consistent read at a pinned revision/digest |
| D | Uses only approved evidence, records approved/sent/cited, deterministic ReleaseDecision | Empty approval means zero calls; unsent evidence/unknown citations are blocked; a state change during generation is blocked; bypassing the UI still applies | AnswerDraft, ReleaseDecision, and the associated three sets/version/run metadata |
| E | Save/read back the research chain; export preserves source, review, state, and version | An old snapshot is not swapped for the latest; blocked is not passed off as released; a missing dependency is explicitly incomplete; path traversal writes nothing out | Immutable history records, verifiable exports and their content digests |

All transfers use the real `src/papertrace/contracts.py`; conflicts are handled through the change process in [integration-contract.md](integration-contract.md), and a module does not stuff in private accepted/released markers for compatibility.

## 3. D1–D9: what every person must provide

The shared repository is responsible for aggregation, but every member must contribute this module's evidence; this is not about handing the nine deliverables to nine different roles.

| Deliverable | What the module author actually provides | Review landing point |
|---|---|---|
| D1 Requirements | Own FR IDs, priority, machine-checkable fit criterion, linked to `INV-01`–`INV-08`/non-functional items; state requirement changes and their source | The specific entries in `docs/req/requirements.yaml`, the schema, and the trace matrix; do not create a separate registry |
| D2 Architecture | Module responsibilities, inputs/outputs/failures, dependencies/authority, state lifetime, context and budget impact; ADRs where needed | Concrete updates to the blueprint, ADRs, invariants, memory, permission, runtime-policy, and evaluation/trace; a diagram alone is not enough |
| D3 Coding governance | A record of having read the real AGENTS/rules, the approved paths and tools; approval for new dependencies/core exceptions | `AGENTS.md`, structural-constraints, the manifest, and the `.opencode`/`.agent` rules; evidence of actual engine permissions is checked separately |
| D4 Verification governance | Upfront test approval; structural/negative/regression/behavior results; real bugs and debt; independent verdict | verification-constraints, `docs/review-memo.md`, bug/debt entries, and raw logs; do not invent bugs when there are none |
| D5 Real session | The original complete OpenCode transcript, annotations and reasons for student interventions, plan approvals/rejections/redirections; locatable to this module's implementation | `transcripts/`; Hermes initialization records must not be passed off as it, and verbatim dialogue must not be written after the fact; final count/naming follows teacher confirmation |
| D6 Process report material | Work actually completed, checkable contribution volume, ambiguities/defects/human-found problems encountered, genuine personal reflection material | The student fills real identity/contribution/reflection into the final `Report.md`; this page and the assignment document remain anonymous, and identical contribution weights must not be invented |
| D7 Repository and gates | Real PR/commit/CI, blocking of failure cases, and human-review evidence; state truthfully that protection is not in effect | https://github.com/537Lab/PaperTrace (not upstream); branch protection/required checks are not in effect (403), and a workflow must not be substituted for them |
| D8 Source and tests | Module source, view, canonical synthetic fixtures, positive and negative tests, regression, reproduction inputs and dependencies | The exact files under `src/papertrace/<module>/`, `test/offline/test_<module>.py`, and the approved `test/fixtures/<module>/`; live is isolated separately, and upstream `tests/` is not deleted |
| D9 Static startup Prompt | A real record of starting from the existing root `Prompt.md`, the Plan stopping to wait, the human-approved version, and subsequent execution | Do not copy it into five mutually conflicting startup prompts; module-specific task supplements cannot bypass the root rules |

## 4. Minimum content of test and run evidence

- [ ] Each feature has at least one positive and one negative case; each invariant has an assertion that fails when deliberately violated; each test is tagged with the real requirement/invariant ID.
- [ ] Cases assert actual semantics: source version, set relations, state not drifting, input content, call counts, error causes; not merely that a file exists, a function returns non-empty, or fixed fake text.
- [ ] There are boundary tests for direct UI calls, service calls without the UI, and cross-module data reuse; the UI does not own a second authorization logic.
- [ ] The full team offline regression has been run with `.venv/bin/python -m pytest -c papertrace.pytest.ini test/offline`; keep the exit code, the actual passed/failed/skipped/collected counts, and the versions. Look at the real output; do not pre-fill numbers here.
- [ ] The commands and results for the remaining schema/static/dependency/API/permission/log gates are checked per [`../ci/gates.md`](../ci/gates.md); items not run are marked not run, and failing items keep the raw failure output.
- [ ] Confirm that the network and real models are disabled in offline; mocks/fakes are explicitly marked synthetic. Do not fill PASS without running live, and do not use fakes to prove faithfulness/relevance compliance.
- [ ] When prompt/model changes, provide the fixed evaluation set, the approved provider/model, data licensing, request/retry and spend limits, and real replay results; without approval the corresponding semantic gate is BLOCKED.
- [ ] Do not treat the initialization `.venv`/`requirements-init.lock` as an installed PaperQA2 business stack; business dependencies and parser version/license changes have separate approval.

## 5. Item-by-item read-back of interfaces, state, and security

- [ ] The literature logical ID, SHA256 version, and snapshot content hash all come from the shared algorithms; no hand-edited identity, file name substituted for version, or reuse of a stale snapshot.
- [ ] The evidence ID/locator/source text match the source literature; summary/relevance are non-authoritative; no ReviewDecision equals pending.
- [ ] Human-only review, ledger revision/digest, conflict rejection, and history replay are all verified; front-end session state cannot forge approval.
- [ ] D's approved/sent/cited come from the specified review projection, the actual request, and the raw citations; `cited ⊆ sent ⊆ approved`, and the snapshot/review tokens at start/end and at the final commit are consistent.
- [ ] B creates a new filtered session for each controlled generation, with `get_evidence_if_no_contexts=false` and `pre/post=None`, does not reuse old contexts/old answers, and runs no autonomous Agent; D does not import `paperqa` directly.
- [ ] Empty approval, empty input after budget truncation, unknown citations, mid-flight retraction/replacement, and model failure all prevent release; citations that were approved but not sent are blocked as well.
- [ ] E's history/export can read back the specific original version and the release reason; a blocked draft is clearly identified, and the latest library is not used to backfill missing history.
- [ ] The original core/packages/tests/pyproject/uv.lock have no unapproved changes; changes to shared contracts/entry points/locks/governance have separate scope approval.
- [ ] No credentials, personal paths, or third-party pickle indexes were read or committed; output-directory validation, redacted logging, and data/dependency licensing have been checked.

## 6. Shared files, logs, and the independent verdict

On handover, provide a short note pointing item by item at the following **real entries or file locations**; do not paste a long process recap:

1. This round's requirement IDs and the original approved plan/test version.
2. Changed paths and interface differences; if the contract changed, attach the section 8 change approval and migration/compatibility evidence.
3. Reproduction steps for normal operation and the minimal negative case, and the location of the raw results for the full suite/gates.
4. The AI-use log entry, the OpenCode transcript, and the locations and reasons for human interventions; Hermes initialization and member development contributions are clearly separated.
5. New bugs/debt/ADRs, unresolved problems, items that must not be mistaken for complete, and the inputs the next person needs to handle.
6. The independent reviewer's `APPROVE` / `CHANGES REQUIRED` / `REJECT` and the blocking reasons; the integrator checks that the approved version matches the current diff.

The shared log is merged by that round's designated editor from each author's real entries; not updating it to avoid conflicts is not allowed, and the integrator must not fabricate someone else's work. After review finds a problem, fix it, re-run, and keep the old failure; do not delete negative cases, change thresholds, or fake "reviewed".

## 7. Final check before merge/final submission

- [ ] The current diff matches the approved scope, and newly added external side effects/tool permissions are re-approved.
- [ ] The local evidence, the six CI checks, non-author human review, and the security-path ADR all correspond to the same version; **required checks are not yet enabled** (free-tier private repository 403), so this item remains incomplete and is marked truthfully; it must not be written as passed.
- [ ] The team's full prior suite shows zero regression after integration; live and real quality status are not overridden by offline results.
- [ ] The final package contains no keys, personal caches, foreign indexes, or unlicensed paper originals; upstream attribution/licenses are retained.
- [ ] D1–D9, real identity/contribution/reflection, and the transcript stance are checked by the student personally; the 10-minute video and the ZIP are prepared separately, and the teacher's exact deadline is filled in only after verification.

Any safety escape, unreviewed citation, an old version passed off as current, forged approval/transcript, or leak of sensitive information must stop the merge/release. Files created, offline tests run, live compliance, GitHub protection in effect, and course submission are five different facts and are reported separately in the final handover.
