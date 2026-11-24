# Permission Model: Deny by Default by Role, File, Tool, and Data

> Status: **planned constraints, awaiting actual configuration and positive/negative verification**. This document does not claim that OpenCode's permissions are already enforced; a permission file existing, its schema being parseable, or an Agent having read the rules are not proof that an out-of-scope action was blocked.
> Constraint sources: INV-06, INV-08, SEC-01, GOV-01, GOV-04; [root blueprint](../../architecture-blueprint.md), [invariants](invariants.md). Page 5 of the course project requires file-level default-no-read/no-write; page 6 separately lists `.opencode/permissions.jsonc` and human-only rules.[1]

## 1. Two Permission Systems That Must Not Be Confused

- **Development permissions**: which code an OpenCode / coding agent may read, which files it may change, and which commands it may run are limited by the approved role and the real tool boundaries. A task sheet saying "responsible for D" does not automatically grant write permission over the whole repository.
- **Product permissions**: the local user selects data, C receives explicit human decisions, and D decides whether an invocation and a release are allowed. The model only receives the permitted text; it cannot call shell/file tools and cannot approve evidence, cost, or release itself.
- **Initialization authorization**: this round creates only contracts, documents, and tooling; it does not mean A–E implementation, model calls, remote repository creation/pushes, or personal-directory access are approved. An architecture-drafting role must not fill in any student approval on their behalf.

## 2. Current Tool Version and Configuration Responsibilities

The controlling environment for this round found OpenCode **v2.0.12**; permission configuration should be checked against that version's **`permissions` array**, not the `permission` map from older tutorials. This architecture subtask did not run OpenCode, load credentials, or verify that configuration, so the actual version/schema/rule loading and the allow/deny receipts rest on the controlling deliverable; no PASS is fabricated here.

| File | Role | What it does not mean |
|---|---|---|
| `.opencode/permissions.jsonc` | The project permission statement / machine-readable contract the course requires to be submitted | The filename alone does not establish that the current OpenCode loads and enforces it automatically |
| `opencode.jsonc` | The project configuration entry point the currently installed version actually recognizes; it should map this table and the approved role/tool rules | Successful config parsing does not mean arbitrary shell/plugin/OS I/O is constrained |
| `.opencode/rules.md` | The human-only always-on rules specified by the course | An agent must not modify it to authorize its own out-of-scope action |
| `.agent/rules.md` | The course covenant, test independence, architecture, and context freshness | It is not an OS filesystem sandbox |
| `AGENTS.md` / `Prompt.md` | The single entry point, reading order, and the plan-first-then-human-review process | Natural language cannot substitute for machine permissions and human-review evidence |

This document gives no unverified configuration snippets; whoever writes the actual configuration must check array fields, match precedence, role selection, and always-on rules against the current version's official schema/help, and test them with controlled harmless fixtures. **Where this table is stricter than the actual machine configuration, tightening is the goal; constraints that are not enforced must not be advertised as an existing security guarantee.**

## 3. Path Principles and the Common Read-Only Set

The project root is written `<repo>`; all paths are relative to it. By default any unlisted path is **R=no, W=no**. Ownership of an approved directory does not equal approval of every file in it; an execution plan must expand into an **exact list of relative files**, and new files that may be created must also be listed one by one. Paths are resolved and then checked against the root, rejecting `..`, absolute paths, and symlink escapes; the same rule must cover read/edit/apply_patch/write, the terminal, scripts, and plugin bypasses.

Common read-only set **R-common** (readable by every approved role, not freely writable):

- `TEAM_START_HERE.md`, `TEAM_WORK_PLAN.md`, `docs/team/startup.md`, `AGENTS.md`, `Prompt.md`, `architecture-blueprint.md`.
- `docs/team/integration-contract.md`.
- `docs/req/prd.yaml`, `docs/req/requirements.yaml`, `docs/req/req-schema.json`.
- `docs/architecture/architecture-blueprint.md`, `adr/001-architecture.md`, `invariants.md`, `trace-matrix.md`, `memory-design.md`, `permission-model.md`, `runtime-policy-catalog.md`, `evaluation-table.md`, `evaluation-logbook.md`, `risk-list.md`, `option-ledger.md`, `source-register.md` (`adr/` paths are relative to the architecture directory).
- `src/papertrace/contracts.py`, `src/papertrace/__init__.py`, `docs/contracts/schema.md`.
- `docs/ci/gates.md`, `docs/ci/full-regression.md`, `docs/tooling/opencode-setup.md`, `docs/licenses/license-review.md`, `test/live/README.md`, `requirements-runtime.in`, `requirements-runtime.lock`.
- `docs/code-governance/structural-constraints.md`, `verification-constraints.md`, `mcp-tool-manifest.md` (the latter two both live in code-governance).
- `.opencode/permissions.jsonc`, `.opencode/rules.md`, `.agent/rules.md`, `opencode.jsonc`: read-only only in the project version confirmed free of secrets; reading the home global configuration is prohibited.

Entries written as short names must be expanded to full relative paths in the machine configuration. What is listed here is the **project plan list**; when a file does not exist, it must not be claimed as done on that basis, nor may a same-named private file from another directory be substituted.

## 4. Coding-Agent Roles × File-Level Authorization

R = read-only; P = may draft a proposal but not approve it; W = writes only within the exact file list of the approved plan. The `service.py` entries, test files, and so on in the table below are proposed locations, and **business implementations are not to be generated now**; if a module needs other files, add the exact paths to the plan first and authorize them after review. Expanding example paths into `src/**` write permission is prohibited.

| Logical role | Additional readable files | Writable files (via a single approved plan) | Actions this role can never self-grant |
|---|---|---|---|
| Plan / requirements analysis | R-common, the current `docs/team/module-X.md`, the public baseline locator summary, the current change diff | P: `docs/plans/module-X-plan.md`, `docs/plans/module-X-test-plan.md` | Modifying implementation, approving its own plan/tests, editing human-only rules |
| A Build | R-common, `docs/team/module-A.md`, `docs/team/integration-contract.md` | W: `src/papertrace/library/__init__.py`, `src/papertrace/library/service.py`, `src/papertrace/library/view.py`, `test/offline/test_library.py`; under `test/fixtures/library/` only the synthetic files listed in this round's Plan | Changing B–E, importing `paperqa` directly, reading real home documents/credentials |
| B Build | R-common, module-B, integration-contract; the upstream sources below per the exact read-only list | W: `src/papertrace/retrieval/__init__.py`, `src/papertrace/retrieval/service.py`, `src/papertrace/retrieval/gateway.py`, `src/papertrace/retrieval/view.py`, `test/offline/test_retrieval.py`; under `test/fixtures/retrieval/` only the synthetic files listed in this round's Plan | Changing upstream in an ordinary feature PR, importing third-party pickles, unapproved model/metadata outbound calls, writing the review ledger |
| C Build | R-common, module-C, integration-contract | W: `src/papertrace/review/__init__.py`, `src/papertrace/review/service.py`, `src/papertrace/review/view.py`, `test/offline/test_review.py`; under `test/fixtures/review/` only the synthetic files listed in this round's Plan | Fabricating human actions itself, writing already-accepted business data, directly modifying old historical events |
| D Build | R-common, module-D, integration-contract, B's public interface files (approved version); exact read-only upstream files may be requested in the Plan | W: `src/papertrace/answer/__init__.py`, `src/papertrace/answer/service.py`, `src/papertrace/answer/view.py`, `test/offline/test_answer.py`; under `test/fixtures/answer/` only the synthetic files listed in this round's Plan; module prompts approved separately | Importing `paperqa` directly, loosening accepted, changing sources/human review, enabling automatic evidence filling |
| E Build | R-common, module-E, integration-contract | W: `src/papertrace/reports/__init__.py`, `src/papertrace/reports/service.py`, `src/papertrace/reports/view.py`, `test/offline/test_reports.py`; under `test/fixtures/reports/` only the synthetic files listed in this round's Plan | Overwriting old reports, deleting reviews/sources, fabricating released or member information |
| Contract maintenance / integration | R-common, all modules' approved public interfaces, `test/offline/test_contracts.py` | P/W: `src/papertrace/contracts.py`, `docs/contracts/schema.md`, contract tests/fixtures; `src/papertrace/app.py` only after a separately approved UI integration plan | Unilaterally changing security contracts, implementing A–E early under the guise of integration work, editing human-only rules |
| Architecture drafting | R-common, authorized course-source extraction/audit material and frozen source | P: the root blueprint and individually approved Markdown in `docs/architecture/` | Marking something as student-approved, interpreting course ambiguity on the teacher's behalf, writing business code |
| Verify / independent testing | R-common, the corresponding module and the frozen-version tests, controlled synthetic fixtures, minimal run results | Independent verification records, new negative tests within the approved list; must not change the implementation or pre-approve the test baseline to force green | Self-signed approval, deleting failing assertions, substituting live for no-budget offline verification |
| PR Review | R-common, that PR's diff/test results, controlled reports | P: the real review draft in `docs/review-memo.md`; necessary debt/bug entries appended per the actual facts | GitHub human approve, merge, push, overwriting historical memos |

In the table, module-X denotes the full path `docs/team/module-X.md`. Process roles may rotate; the A–E functional ownership does not change. Rotation does not accumulate the previous role's write permissions, and the old permit is revoked on switch. Page 4 of the course project requires rotating responsibility; functional ownership must not be misread as a permanent management post.[1]

**Read-only baseline allowlist for B and architecture**: `src/paperqa/docs.py`, `types.py`, `settings.py`, `core.py`, `readers.py`, `llms.py`, `prompts.py`, `agents/main.py`, `agents/env.py`, `agents/search.py`, `agents/tools.py`, `agents/models.py`, `agents/__init__.py` (subsequent entries are all relative to `src/paperqa/`); `pyproject.toml`, `uv.lock`, `LICENSE`; the exact reader files and test-node sources for the required parsers. Expand file names before running; additional read-only source needs also go on the list first.

"B-only" means the team's new business code concentrates `import paperqa` and the adapter/invocation implementation in B; it is **not** a prohibition on A/D understanding upstream behavior. A and D may view upstream APIs in the exact read-only files their own Plan lists (e.g. `src/paperqa/docs.py`, `types.py`, `settings.py`, `core.py`, `readers.py`, `prompts.py`, `llms.py`); this statement does not grant read permission automatically, and they must not import/call upstream directly. Upstream writes still follow ADR-002's separate human PR/frozen_check exception process; verbal waivers are not accepted.

## 5. Unconditional Prohibited Areas and Areas Requiring Separate Authorization

| Area / behavior | Default permission | Reason and exception process |
|---|---|---|
| `src/paperqa/**`, `packages/**`, the original `tests/**`, upstream configuration/lock files | R allowed for listed files; W no for ordinary module PRs | The fixed baseline is protected by the existing `frozen_check`; a necessary compatibility fix requires a separate ADR + human PR that explicitly updates that fitness rule/comparison basis and runs the affected regression. Verbal approval alone must not make the current CI pass; no bypass authorization platform is added. |
| `.opencode/rules.md` | R on the authorized project copy; W no | Human-only for the course; the AI may supply a suggested diff but does not edit or self-sign |
| Any real key/token/cookie/.env, keychain, SSH, browser profile, global provider configuration | R/W both no | Must not be read in order to "check whether a key exists"; credentials are injected by the holder through a security boundary into an approved live process |
| Personal directories outside the repository, unrelated projects, user history | R/W both no | Authorization is not inferred from the default working directory or tool reachability |
| Writes to `.git/**`, `git add/commit/push`, remote/branch-protection changes | No | The coding agent does not commit/push; the initialization controller undertakes only the local initialization commit per this round's delegation, later pushes are performed by someone separately authorized, and the AI does not change remotes on its own |
| `.papertrace/**` real runtime data, original papers, and history | R/W no by default for a coding agent | Only approved redacted copies/exact objects may be used; testing convenience must not become a data-read permit |
| `test/fixtures/**` synthetic samples | R/W only for specifically listed samples | Adding real member identities/keys/full text of papers without permission is prohibited |
| Real model, embedding, metadata, OCR HTTP, or tokenizer downloads | No | Approve provider/model/data/amount/count/configuration separately first; permission to install dependencies is not permission to use models |
| Workflow/dependency/permission/rule/release-gate changes | Proposal only; formal writes need a controlled plan | Safety paths require an ADR + student review; default permissions must not be changed to bypass this table |

## 6. Tools and Commands

What is allowed by default: the minimal read-only file tools, approved exact-file editing, restricted Git read-only status/diff, and reviewed scripts/tests in an isolated environment. Web browsing/external search are open only when separately permitted for the task and no private data is uploaded; runtime models do not have these tools.

The terminal is the key bypass: approving `python`, `sh`, `curl`, or an arbitrary script can bypass the edit tool's path rules. Restricting only `edit` is not enough to claim no-read/no-write. If the executor has no OS-level isolation, generic shells should be refused and only the **script path + content version + arguments + working directory + output directory** allowlisted, with real credentials stripped and network limited. Scripts are re-reviewed after any change; the test `-m offline`/socket monkeypatch is local evidence, not a whole-machine outbound sandbox.

Installing/upgrading tools or dependencies to quietly fix a failing test is prohibited; installation needs a separately approved scope and license, and network fetches and model calls are metered separately. All auto-fix commands may write files and must not be run by default during read-only verification.

## 7. Product-Side Files and Authorization Matrix

| Principal | Readable | Writable / decidable | Not decidable |
|---|---|---|---|
| Local user (explicit selection) | The documents it is entitled to handle, and current/historical evidence and reports | Import, accept/exclude/reset, explicit budget authorization, export | Being locally readable does not grant a license to redistribute the paper |
| A | Managed sources, current/old snapshots | New document versions, new snapshots, the current pointer | accepted and release |
| B | The designated snapshot's sources, candidate/approved evidence, approved permits | Reconstructable representations, candidate records, invocation accounting | Human review and release |
| C | This question's candidates and source text, and their review history | Appended decisions/revision/digest produced by real human-machine interaction | Model facts and budget |
| D | Current A/C projections, this round's B raw output/invocation accounting | context scope, AnswerDraft, ReleaseDecision | Rewriting human review/sources, giving the model tools, or expanding the budget |
| E | Validated report packages and sources within the permitted scope | New reports, appended superseded annotations, exported copies | Treating blocked/stale as currently released |
| Model/provider | Only the text inside this round's final payload | Returns a proposed draft/summary | Files, tools, ledger, policy, identity, budget, and release |

## 8. Real Verification Evidence That Must Be Obtained

1. Record the actual OpenCode version, schema, rule-loading source, role selection, and the expanded exact allowlist, without reading global secret configuration.
2. Verify with self-built non-sensitive fixtures: the allowed scope is readable/writable; unlisted paths/other modules/frozen copies/rule files/out-of-repository sentinels are not readable/writable; path traversal and symlinks are rejected as well.
3. Use harmless commands to verify that git push, generic shells, and network/model access are refused; do not use real keys to test rejection and do not actually attempt remote destruction.
4. Inspect the actual file bytes and the tool-denial receipts, distinguishing the four layers "rule generation", "config recognition", "tool interception", and "OS isolation"; mark any layer that cannot be proven as unverified.
5. Give the results to an independent reviewer and the student for review; without remote-protection administrator authorization, mark it only as "pending authorization" and do not claim the required checks are in effect.

If the above verification has not passed: stop at planning/read-only analysis and do not begin formal business development; real permission fixes are performed after approval by the controller/holder. This document does not pre-fill verification results.

## Sources

[1] urn:sha256:6af742d3cbc0973b056a084ba54ff413a5885b1bb4d6a97b0b08b93f64f2ef7e — CS5351-2026-2027-project.pdf (extracted from the local original, 10 pages)
