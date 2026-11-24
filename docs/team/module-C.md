# Module C | Source comparison, human review and the append-only ledger

> **Owner C:** end-to-end responsibility for the review feature, their own view, requirements/design, supervision of OpenCode, tests and PRs. This task book is not an authorization record; the business logic still awaits member implementation.
>
> Always start from the [team start entry](../../TEAM_START_HERE.md); the authoritative source for fields is [`integration-contract.md`](integration-contract.md) and the real contracts.

## User outcome and responsibilities

The researcher can compare at least two independent sources for the same question/snapshot and clearly see the source text, the AI summary, version/locator and the review rationale; only an explicit human action can accept, exclude or reset; decisions are replayable and old events are never overwritten. No valid decision means pending.

C is the sole owner of human-review authority and of the append-only ledger. Schema fields such as `actor_kind="human"` and the anonymous `reviewer_ref` are only shapes and do not prove a real person's identity; this product is a local single-user flow and does not claim to withstand a malicious local administrator. No fake/model/import/UI cache may write an authoritative accepted.

## Must and reviewable outcomes

| Requirement/invariant | Required behaviour and acceptance |
|---|---|
| `FR-C-01`, `INV-03/05` | An explicit human command appends an `accepted/excluded/pending` decision; the rationale is non-empty and the scope corresponds to question/snapshot/evidence; revision increases monotonically and the digest can be recomputed; conflicts/forgeries/corruption are rejected and fail closed. A reset appends pending and does not delete old events. |
| `FR-C-02`, `INV-02` | Compare ≥2 sources at the same time; literature version, locator, source text, summary and rationale are all visible; similar/opposing evidence keeps distinct identities; display/ordering/refresh does not modify the ledger. |
| `INV-04/06`, `QA-01`, `SEC-01` | Decisions bind to a fixed snapshot/question; old decisions are not migrated to new literature; calling the service while bypassing the view is still subject to the same human/scope/revision checks; anonymous material does not record a real identity. |

An empty ledger has revision 0 and no accepted entries; the exact digest/replay/idempotency/atomic-write policy must be designed and approved at Plan, and permissions are never filled in from UI cache.

## Boundaries and proposed change scope

- Consumes `EvidenceRecord`, `CorpusSnapshot` and restricted source-text reads from B/A; provides D/E with a replayable projection and token for a given question/snapshot. D is the release authority; C does not decide release and does not directly modify A/B/E files.
- **Routine module scope (confirmed once at Plan; routine edits/new files inside the scope are not approved one by one):** `src/papertrace/review/` (ledger service and view), `test/offline/test_review.py`, `test/fixtures/review/`. Shared contracts/fixtures, requirements/trace, app orchestration, dependencies/CI and governance logs are approved separately.
- `.opencode/rules.md` is human-only and AI must not modify it; do not read the real `.env`, papers, history or personal directories, and do not call models/network.

## Fake-first development and acceptance without waiting for B/D

Use the shared canonical `EvidenceRecord`/`CorpusSnapshot` with hand-written synthetic evidence holding two opposing viewpoints plus one irrelevant viewpoint; the fake candidate feed may only produce candidates and never returns an authoritative accepted. Implement the pure service/replay first, then have the view call the same service, so the state machine is not duplicated.

Minimum verification: with no decision, and with only a model suggestion, the state stays pending; human accept/exclude/reset produce the correct events and revision/digest; repeated submission/ordering/refresh does not grant twice; a forged human/import accepted is rejected; an old revision conflict does not overwrite; a bad digest/cross-question/snapshot is rejected; similar content is not merged; a direct service call cannot bypass; a new decision invalidates the old D draft. Zero model calls throughout; synthetic operations must not masquerade as real approval records.

## D1–D9: module evidence C should leave behind

| Item | Evidence for this module |
|---|---|
| D1 | Fit criterion, tests and trace for `FR-C-01/02`, `INV-03/04/05`. |
| D2 | Human-only authority, ledger append/replay, revision/digest, conflict/idempotency/bad-ledger policy and necessary ADRs. |
| D3 | This round's exact path/tool permissions and the service-layer human/scope boundary; client-provided strings are not identity authentication. |
| D4 | Pre-approved negative tests, service/UI consistency, full regression, independent review memo and real bug/debt. |
| D5 | The genuine complete original session of the student supervising OpenCode and the reasons for intervention; Hermes initialization must not be counted. The course count basis is pending confirmation. |
| D6 | This module's real feature/collaboration contribution, findings and reflection material; the final identity is filled in by the person. |
| D7 | Local diff/PR, real CI/independent review; the earlier remote protection 403 did not take effect and must be verified at the end. |
| D8 | Ledger/projection, comparison view, synthetic fixtures and positive/negative/regression reproduction. |
| D9 | The Plan stop point in the root `Prompt.md`, test/plan/path approvals and supervised execution records. |

Acceptance requires real service tests of the human-interaction boundary; a disabled button, hand-written accepted JSON or a model suggestion do not count as passing.
