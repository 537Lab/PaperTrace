# PaperTrace | Work Plan and Collaboration Rules

> New members start from the [team's single entry point](TEAM_START_HERE.md). This file concentrates on ownership, role rotation, course evidence, and gates; module technical acceptance lives in the individual task briefs.

## 1. Goal and current scope

PaperTrace is a local research-evidence review workbench: import authorized papers, retrieve candidates, have a human review them, answer using only accepted evidence, and then save a traceable research history. The shared contracts/tests/governance foundation established in this round is not the five-module business, and it does not prove that a runnable production Streamlit application exists. All implementations, approvals, OpenCode sessions, model evaluations, and remote protections must be recorded with actual evidence separately.

The pinned upstream is `Future-House/paper-qa@c692d0dfeac4a0296599f7fe21a253a58b7ac12a`. Ordinary feature PRs do not change its `src/paperqa/`, `packages/`, original `tests/`, `pyproject.toml`, `uv.lock`; this is not a permanent ban on necessary fixes. Exceptions must go through the reviewed patch process in [ADR-002](docs/architecture/adr/002-development-readiness.md), without bare edits and without bypassing any test/permission gate.

## 2. Five-feature ownership and parallel interfaces

| Owner | End-to-end Must feature | Boundary and handover |
|---|---|---|
| A | Paper import state, logical identity, content SHA256 version, immutable snapshots | Emits a ready-only `CorpusSnapshot`; does not import `paperqa` and does not review on C's behalf |
| B | Candidate retrieval, source location, thin PaperQA2 adapter, controlled calls/neutral port | The team's only `paperqa` import; grants no human-review or release authority |
| C | Source-text vs. summary comparison, explicit human accept/exclude/reset, append-only review ledger | Emits replayable decisions with revision/digest; models and UI state grant no authorization |
| D | The accepted/actually sent/actually cited three sets, controlled answering, deterministic release gate | Owns answering and release itself; executes through B's port, with zero factory/SDK/HTTP calls when the accepted set is empty |
| E | Research history, source traceability, JSON/Markdown export | Reads back the original snapshot/review/answer/release state; does not overwrite history or escalate authorization |

The single source of truth for shared models is `src/papertrace/contracts.py`. Interface details and error semantics are in [`docs/team/integration-contract.md`](docs/team/integration-contract.md); requirements/thresholds are in `docs/req/requirements.yaml`; do not build a second registry in the task briefs.

### Parallel fake development paths

Start with the canonical objects in `test/fixtures/contracts/` and the synthetic fixtures written by each module; only the `data` of the shared wrapper is the model input. Each module's key fakes and their observable assertions are listed in its task brief: A fake parser/import port; B fake parser/retrieval/generation adapter; C fake candidate feed (which cannot return an authoritative accepted); D a fake generation port that records the final input and attempt counts and does not depend on B being finished; E synthetic research bundles in the valid/blocked/abstained/failed states.

All fakes and materials are marked synthetic; they prove only deterministic interfaces, authorization, failures, and input boundaries, not real model quality, licensing, or performance. Real PaperQA2 offline integration and dependencies for B/D, and provider/model live calls, are approved separately. D may review upstream API behavior within the read-only paths listed precisely in its Plan, but may not import `paperqa` directly.

## 3. Minimal workflow and permissions

Each feature author is responsible for requirements, design, supervising OpenCode, positive and negative tests, their own view, the PR, and the demo; there is no "documents only" member.

1. **Plan:** following the minimal reading set in the single entry point, list the real FRs/INVs, inputs/outputs/failures, exact relative paths, fake tests, dependencies, and side effects; then stop and wait for approval.
2. **Review before writing:** after the supervising student approves the plan, OpenCode only prepares module tests/fixtures/design records and does not write business source code; the test proposal PR may stay open/RED. Only after another classmate who did not take part in the implementation approves the specific test commit on GitHub does business implementation begin; the module scope for this round (which may include explicit directory rules and their new files) and the common offline tools are confirmed once. Inside that scope there is no per-file/per-command re-approval; re-confirmation is required only when extending to shared code, other modules, dependencies, network, or cost. Configuration remains `R=deny, W=deny` by default, with explicit allowlists limiting the scope, and no unconditional allow-all is configured.
3. **Supervised build:** the student themself uses the OpenCode required by the course, checking and intervening step by step and recording the reasons. If requirements, interfaces, or security semantics change, go back to approval; implementation cannot come first with approval filled in afterwards.
4. **Verify:** save the real command, version, exit code, scope, and raw result; run the relevant negative tests, the team's full offline suite, and the full prior regression. The `test/offline` run on the initialized `.venv` belongs only to the first category, not to full regression; the three-source/collection parity/live BLOCKED rules are in [`verification-constraints.md`](docs/code-governance/verification-constraints.md) and [`full-regression.md`](docs/ci/full-regression.md). The real applicable status is determined by `docs/ci/gates.md` and the verification evidence.
5. **Independent PR:** a non-author reviewer checks the diff, tests, permissions, AI-use log, bug/debt, ADRs, and D1–D9. Real GitHub merging and protection are verified separately.

**Every feature needs a locatable requirement/invariant trace and at least one negative test that fails when the boundary is broken.** Security-critical changes such as review authority, source identity, generation/release, budget, permissions, upstream patches, and historical state require an ADR, negative tests, review by the affected owner, and review by the student themself. Rule changes made after human review must be synchronized within one sprint; `.opencode/rules.md` is human-only and agents may not change it themselves.

## 4. D1–D9 individual evidence

Each member provides only the evidence that actually occurred in their own module; planned content does not count as a completed item. The course text and the interpretations still to be confirmed are in [`docs/sources/course-compliance.md`](docs/sources/course-compliance.md).

| Deliverable | Real evidence each module author must leave |
|---|---|
| D1 Requirements | Must FRs, registry fit criteria, associated INVs/quality items, source and test traces; do not build a second requirements table |
| D2 Architecture | This module's responsibilities, interface/failure/state/budget impact, and necessary ADRs; security-critical decisions require human review |
| D3 Coding governance | The exact paths/permissions/tools for this round, human-only rules, and boundary verification; do not claim permission enforcement that was not executed |
| D4 Verification governance | The pre-approved version, positive/negative/regression results, an independent review memo, real bugs/debt |
| D5 OpenCode sessions | The original complete sessions produced under student supervision, with the real human interventions. The course's p2 "five annotated" and p6 "one full raw/from scratch" interpretations must be verified by the student/instructor; the Hermes initialization cannot pass as them |
| D6 Process report | The member's real feature, checkable contribution, and reflection material; the final identity is filled in by the student. The original text requires an average contribution of 1.0, at most 10,000 words (excluding figures), and more than 15 pages at 12pt single spacing; formatting/delivery is verified by the student |
| D7 Repository/gates | Real local diffs, PR/CI, human review, and evidence of protection blocking. Private-repository branch protection did not take effect earlier because of a 403; it must be re-read and rehearsed at the end and cannot be marked complete |
| D8 Source/tests | This module's business source code, its own view, synthetic fixtures, positive/negative/regression tests, and reproducible commands |
| D9 Static Prompt | Genuinely started from the same root `Prompt.md`, with the Plan stopping to wait for test/plan/permission approval and the execution record kept; do not copy a conflicting prompt |

**The 10-minute demo is submitted separately and does not go into the ZIP.** Introduction p20 requires the student to genuinely supervise OpenCode; the instructor's exact deadline must still be checked against the latest course notice. Do not fabricate identities, contributions, approvals, transcripts, model results, or CI conclusions.

## 5. Process role rotation (does not transfer feature ownership)

An author/co-implementer cannot approve their own tests or independently review their own PR. The pre-test approver and the final reviewer may be the same non-implementer; the integrator may rotate according to actual availability, and four classmates do not have to be convened for every small PR. The table below is an optional first-round division of labor, not an additional gate.

| Feature author | First-round test/plan approval | Independent reviewer | Integrator |
|---|---|---|---|
| A | B | C | D |
| B | C | D | E |
| C | D | E | A |
| D | E | A | B |
| E | A | B | C |

Later rounds may shift along A→B→C→D→E, and when someone is absent another non-implementer substitutes for approval/review; assign differently only on an independence conflict. No one may be made the permanent CI/management owner.

## 6. The six course gate categories (kept in full)

The six gate categories on p10 of the instructor's Project handout must not be deleted, downgraded, replaced with fake results, or marked green because they are not implemented this round. Report each one separately per round against the real applicable conditions:

1. test approval before implementation;
2. static analysis, type/dependency, and security-path checks;
3. requirements schema;
4. real semantic evaluation for prompt/model changes;
5. full prior regression;
6. a real AI-use log corresponding to code/prompt changes.

`NOT_REQUIRED`, skip, fake, a gate name in a document, or a local check ≠ a passing course gate; a real model evaluation that is not approved/not run must be BLOCKED. GitHub required checks/security-path protection can be called in effect only after the authorized configuration is complete, read back, and validated with both violating and legitimate control PRs. The current runtime status is not copied into this file; read `docs/ci/gates.md` instead.

## 7. Trimmable scope and open items

When resources are insufficient, trim non-Must items first — UI polish, automation, multi-user support, cloud, and complex reporting platforms — without cutting D1–D9, the six gates, human approval, the deterministic safety boundary, or real evidence.

Still to be confirmed by the student: the boundary for OpenCode/reusing PaperQA2, the D5 transcript interpretation, the exact date/time zone for Week 13, and the formal submission requirements. The course introduction also requires a 10-minute demo, separate from the ZIP; do not guess the date.
