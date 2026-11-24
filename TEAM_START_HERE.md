# PaperTrace | The Team's Single Entry Point

This file is the single entry point for new members, module authors, and collaborators. Other documents explain only a single command, design, or delivery rule, and you are not expected to read the whole repository along one endless reading chain.

PaperTrace is a local research-evidence review workbench: **A library → B retrieval → C human review → D controlled answering/release → E history/export**. The business features are still to be developed by the students separately; do not mistake the initialization contracts or fake data for the production application.

## 0. What can be done now, and the single adoption step

PR [#1](https://github.com/537Lab/PaperTrace/pull/1) is the shared engineering starting point awaiting human review; **it is not merged yet and is not a complete product**. A maintainer and another human need to review the latest head and the course acceptance boundary following the [one-time first adoption steps](docs/ci/minimal-gates.md#one-time-first-adoption-of-pr-1-bootstrap); agents do not self-approve or merge on the student's behalf. The missing verifier on the remote first base, the full-upstream FAIL, and the gaps in real student/model evidence are all retained; a red light is not described as passing.

Once you receive the invitation you can claim a feature, read the task brief, and prepare a Plan and tests immediately; formal source implementation still waits for real plan/test approval. Before adoption, if a preparation branch truly must be created early, create `plan/<module>-<name>` from the reviewed PR #1 head, and do not mistakenly start from the old main; after adoption, everyone syncs the latest main and then creates `test/<module>-<name>` and `feat/<module>-<name>`. There is no need to initialize again, wait for other modules to be implemented, or build new approval tooling.

## 1. Join and verify the initialized environment

The team repository is private: first ask the owner to invite your GitHub account. The clone steps, the Python/uv environment, and the initialization test commands that can be run directly are on the [startup commands page](docs/team/startup.md). The initialization dependencies are not the PaperQA2 or Streamlit business environment; installation and live calls need separate approval.

## 2. Claim one complete feature

| Member | Long-term feature ownership | Task brief |
|---|---|---|
| A | Paper library, per-item import status, content versions, and immutable snapshots | [Module A](docs/team/module-A.md) |
| B | Candidate retrieval, the single PaperQA2 adapter boundary, and the controlled call port | [Module B](docs/team/module-B.md) |
| C | Source-text/summary comparison, human decisions, and a replayable review ledger | [Module C](docs/team/module-C.md) |
| D | The accepted/sent/cited sets, budget, and the deterministic release gate | [Module D](docs/team/module-D.md) |
| E | Immutable research history, source traceability, and JSON/Markdown export | [Module E](docs/team/module-E.md) |

The task brief defines feature acceptance and an unblocked fake path; it is not implementation authorization. For the five-person work arrangement, role rotation, and course deliverables see the [work plan](TEAM_WORK_PLAN.md); for shared objects and boundaries see the [integration contract](docs/team/integration-contract.md).

## 3. Do the minimal necessary reading, then stop at Plan

Before starting a module Plan, read only:

1. The root `AGENTS.md` and `Prompt.md` (follow the entry points in them; do not rewrite or bypass them).
2. Your own `docs/team/module-X.md`, the `docs/req/requirements.yaml` entries relevant to this module, and `src/papertrace/contracts.py`.
3. The parts of `docs/team/integration-contract.md` related to this module's interface/safety boundary.

Read the corresponding ADR / `permission-model.md` / `verification-constraints.md` only when a question involves a particular architecture decision, permission, or verification rule. There is no need to read all documents, upstream tests, or personal directories just to start. On conflict, record the question and stop; do not choose the looser interpretation yourself.

Use the course-required **OpenCode** to start the Plan from the root `Prompt.md`. The Plan must list requirement IDs, data flow/failure strategy, positive and negative tests, exact read/write paths, tool/dependency/network needs, and how fakes are verified, and then stop. **The supervising student approves the plan and a one-time module/offline-tool scope → OpenCode prepares only this module's tests (business implementation is strictly forbidden at this point) → a non-implementer approves the specific test commit on GitHub → restricted business Build → Verify. The test proposal PR may stay open/RED; red tests must not be merged, and there is no repeated per-file approval.**

## 4. Independent development, supervision, and verification

- Each module has its own synthetic contract objects and fake adapter paths; services, views, and boundary tests can be completed first without waiting for other modules and without a model. A fake proves only interfaces, authorization, and input observation, not real model quality.
- B exclusively owns `import paperqa` in newly added team code and maintains the upstream calls and the neutral port; this does not forbid A/D from reviewing upstream source within the exact read-only paths listed in an approved Plan. D develops its own authorization, budget, citation, and release logic in parallel using a fake port that records the final payload, without waiting for B to finish, and cannot import/call PaperQA2 directly.
- Any change to business dependencies, outbound calls, prompts, safety semantics, or shared contracts is proposed and approved separately per the task brief/integration contract. A security-critical change requires an ADR, at least one negative test that will fail, and review by the student themself.
- The Build must be OpenCode supervised by the student, keeping the real complete sessions and the reasons for human intervention; the Hermes initialization in this round is not a student OpenCode contribution or a D5 session.
- Verify runs the offline regression and all six course gate categories within their real applicable scope; gates must not be deleted, downgraded, or passed off as passing through `skip` / `NOT_REQUIRED` / fake / the existence of a document. See [`docs/ci/gates.md`](docs/ci/gates.md) for live results.
- An independent reviewer cannot be the author or a co-implementer; PRs and D1–D9 evidence are checked against the [handover checklist](docs/team/handover-checklist.md).

## 5. Non-negotiable deterministic boundaries

1. A paper's logical identity, SHA256 content version, snapshot, and evidence source identity must not be conflated; history is not replaced by a new file with the same name.
2. Without a valid human `ReviewDecision` the state is pending; model suggestions, UI caches, or the `actor_kind="human"` field alone do not constitute real approval.
3. With no accepted evidence, refuse before the model factory/SDK/HTTP; a model must not be called to produce an abstention reason, and B must not be allowed to fetch evidence automatically.
4. An answer has `cited ⊆ sent ⊆ approved`, and the snapshot and review revision/digest are checked before and after release; any change blocks the old draft.
5. Third-party indexes, credentials, `.env`, personal directories, unlicensed paper content, and unapproved network/model calls all stay out of the development process.
6. The upstream core is protected by the existing `frozen_check` pinned baseline and is not changed by ordinary module PRs. When a compatibility fix is genuinely needed, it requires a separate ADR + human PR that explicitly updates the `frozen_check` fitness rule/comparison basis and runs the affected regressions; verbal approval alone cannot make the current CI pass. No bypass authorization platform is added.

Items the course still needs the student to verify include the D5 "five annotated" vs. "one complete raw/from-scratch" interpretation, the baseline reuse boundary, the exact deadline, and the final delivery format. D6 identity, relative contribution (average 1.0), and genuine reflection are filled in by the student themself; the 10-minute demo is separate from the ZIP. Do not fill anything in on the student's behalf or claim the course is complete.
