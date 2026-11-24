# Module B | Retrieval, the PaperQA2 adapter and neutral ports

> **Owner B:** end-to-end responsibility for the retrieval feature, the thin adapter, error presentation, their own view, supervised development, tests and PRs. B exclusively owns `import paperqa` in the team's new code; the role is not merely writing a call tool for D.
>
> Always start from the [team start entry](../../TEAM_START_HERE.md); shared interfaces follow [`integration-contract.md`](integration-contract.md) and the real contracts.

## User outcome and responsibilities

The researcher picks a fixed library snapshot and asks a question, and sees candidate evidence bound to source text, version, locator and an explicit status; empty results, parse errors, timeouts and call failures are distinguishable. B provides `EvidenceRecord` and the mechanical generation port authorized by D, and **grants no authority for human acceptance or release**.

B maintains the PaperQA2 adapter, the retrieval/generation ports, upstream call options, and observation of what was really sent/attempted. A's ingestion status belongs to A; `approved`, the prompt/budget/trimming policy and release belong to D. B does not treat `Context.id` as the team identity and does not pass mutable `Docs`/`PQASession` to D.

## Must and reviewable outcomes

| Requirement/invariant | Required behaviour and acceptance |
|---|---|
| `FR-B-01`, `INV-02` | Every candidate binds snapshot/doc/version; source text and the advisory summary stay separate; the locator is a checkable 1-based inclusive page/line range with chunk/parser name and version; identity uses the shared implementation. |
| `FR-B-02`, `INV-08` | Empty sets and execution failures are kept apart; timeouts/parse errors/attempt counts are recorded; retries are bounded and go through approval, with no silent model switch; untrusted third-party pickle indexes are refused and licences reviewed item by item. |
| `FR-D-03`, `INV-01/03/04/07` (with D) | Execute only the evidence/configuration approved by D; return the final actually sent payload, the raw output and an unambiguous alias mapping; do not add evidence automatically, do not review and do not release. D's empty-approval branch never reaches B's generation port. |
| `COST-01`, `SEC-01`, `QA-01` | By default no model/network call is triggered; real dependencies, parsers, embeddings and live requests are approved and metered separately; no credentials/personal directories/unlicensed full text. |

The current contracts require `EvidenceRecord` to have no accepted/status field; upstream `Context.id` is not a source identity. When no genuinely verifiable locator is available, fail explicitly rather than guessing line numbers or offsets.

## Boundaries and proposed change scope

- Among new business code only B imports `paperqa`, with calls centralized in the adapter/port; neither A's controlled ingestion nor D's generation may open a bypass. Upstream source is read-only by default; necessary fixes go through ADR-002 and are not ordinary adapter PRs.
- **Routine module scope (confirmed once at Plan; routine edits/new files inside the scope are not approved one by one):** `src/papertrace/retrieval/` (adapter, port, call accounting and view), `test/offline/test_retrieval.py`, `test/fixtures/retrieval/`. Shared contracts, CI, lock/dependencies, prompts, entry orchestration and other module directories are approved separately.
- PaperQA2 real dependencies/licences and the offline adapter form a separate gate; provider/model, data, request counts, retries, cost and deadline need yet another separate approval. An initialized tool environment must not be described as a business environment.

## Fake-first and PaperQA2-specific risks

D need not wait for B: D tests its own final payload and call counts through a fake generation port; B's fake adapter tests the mapping from synthetic source/Context to `EvidenceRecord`. The fake must record its real inputs and attempts and must not dodge boundary checks by returning a fixed `"OK"`.

Minimum verification: cross-snapshot/version/locator errors are rejected; summary changes do not change identity; source text/locator can be checked back; empty sets, timeouts and parse errors are distinguished; a high model score or a malicious excerpt does not write to the review ledger; unknown-citation raw output and mappings go to D; factory/SDK/HTTP counts are all zero before D's empty-approved call.

The real-upstream Plan must verify and test `Docs.aadd`, `aget_evidence`, `aquery` plus the implicit citation inference/enrichment, embeddings, empty-context evidence addition, pre/post and session-reuse risks. The generation adapter must use a newly created session containing only the contexts D selected, explicitly disable automatic evidence addition and `pre/post`, and return the raw output plus the real sent payload after the final serializer. Mark dependency integration as unverified until it has actually run; a fake does not represent model quality.

## D1–D9: module evidence B should leave behind

| Item | Evidence for this module |
|---|---|
| D1 | Fit/test mapping for `FR-B-01/02`, `INV-02/08` and the items shared with D. |
| D2 | Single adapter/port, locator/identity mapping, list of implicit calls, budget/failure policy and necessary ADRs. |
| D3 | B's exact write paths and upstream read-only list, dependencies/licences and evidence of actual tool permissions. |
| D4 | Prior test approval, exception/input-capture/call-count negative tests, real-upstream offline integration scope and review memo. |
| D5 | The original complete OpenCode session formed under student supervision, and the human interventions; Hermes initialization cannot stand in. The transcript basis is confirmed by the student/instructor. |
| D6 | The person's real adapter, feature and collaboration contribution and reflection material; identity is filled in by the person. |
| D7 | Local diff/PR, real CI and independent review; the earlier branch-protection 403 did not take effect, so the final state must be re-checked. |
| D8 | Retrieval service/view, synthetic fixtures, spy/exception/positive-negative regression and real dependency integration records. |
| D9 | Starting from the Plan stop point in the root `Prompt.md`, keep the test/plan/permission approvals and supervised execution records. |

Do not call an existing adapter class, a successful package install or a fake answer feature acceptance or a real semantic PASS.
