# Module E | Research history, source traceability and export

> **Owner E:** end-to-end responsibility for the reports/history/export user features, their own view, requirements/design, supervision of OpenCode, tests and PRs; the role is not merely writing course materials. This task book is not a business implementation or an authorization record.
>
> Always start from the [team start entry](../../TEAM_START_HERE.md); contract details are in [`integration-contract.md`](integration-contract.md) and the real `src/papertrace/contracts.py`.

## User outcome and responsibilities

The researcher can save a research run that succeeded, was blocked, abstained or failed; after closing and reopening, the snapshot, sources, review and release status of that time can still be located; JSON and Markdown can be exported. When the literature later changes version, the old research run keeps its original content and is marked superseded, rather than being backfilled from the current library.

E owns the versioned research record envelope, immutable history, read-back and export. The five shared models remain the single source of truth for fields/enums; E does not regenerate answers, does not modify C's ledger and does not upgrade blocked to released on the strength of an external bool/button. A missing original must be shown as missing, not replaced by a same-named file.

## Must and reviewable outcomes

| Requirement/invariant | Required behaviour and acceptance |
|---|---|
| `FR-E-01`, `INV-02/04` | Save and read back across sessions the question, snapshot, evidence/locators, human review records and tokens, approved/sent/cited, AnswerDraft and ReleaseDecision; the JSON re-parses; Markdown expresses the same sources and states as JSON. |
| `FR-E-02`, `INV-05/08` | History is append-only; a version change only shows superseded and does not modify old records. The default export contains no credentials, local absolute paths, unlicensed full text or private model reasoning; out-of-bounds paths/symlink escapes/write failures do not damage history. |
| `QA-01`, `SEC-01` | Use the real model fields and enums; the schema version/unknown-field policy is explicit; synthetic sensitive sentinels can test redaction without scanning private directories. |

The history envelope is a later versioned wrapper that must be settled at Plan with the relevant producers/consumers co-reviewing it; no private fields are added to the frozen models. AnswerDraft currently has only `draft/abstained/failed` and ReleaseDecision only `released/blocked`; `stale/superseded/incomplete` are envelope/display semantics, and the transport enums must not be changed at will. Missing usage/cost is recorded as unknown, not filled in with zero.

## Boundaries and proposed change scope

- Consumes the original version objects and review ledger from A/B/C/D; the final consistency commit is designed jointly by the approved app orchestration/D/E, with E owning storage/read-back/export and not building another release gate.
- **Routine module scope (confirmed once at Plan; routine edits/new files inside the scope are not approved one by one):** `src/papertrace/reports/` (storage, reading, exporter and view), `test/offline/test_reports.py`, `test/fixtures/reports/`. The record envelope's external interface, shared models, A/C/D ports, entry/lock/orchestration, dependencies/CI and governance logs are approved separately.
- Does not write A's library/C's ledger/D's release gate, does not read `.env`, credentials or real private papers/history, and does not go online or introduce a large database/cloud service without approval.

## Fake-first development and acceptance without waiting for A–D

Use the canonical five models and hand-written synthetic complete released, blocked, abstained and failed records; the fixtures state explicitly that they are synthetic and do not pretend to be real human review, OpenCode sessions or model output. Fake data is read and written only inside the test's temporary output directory.

Minimum verification: save/close-reopen/JSON roundtrip; the required JSON/Markdown fields and evidence/locator match with no mismatch; old content hashes are unchanged after a version change; blocked/abstained/failed stay unreleased; missing objects/wrong associations/bad digests/unknown schema are not patched into success; path traversal, symlink, conflict, interrupted write/disk failure cause no writes outside the scope and do not damage old bundles; synthetic sensitive values, absolute paths and unlicensed full-text markers do not enter the export. External reading/export permission must be verified separately; the Apache-2.0 root licence is no reason to assume papers may be shared.

## D1–D9: module evidence E should leave behind

| Item | Evidence for this module |
|---|---|
| D1 | Export/history fit, tests and trace for `FR-E-01/02`, `INV-02/04/05/08`. |
| D2 | Versioned envelope, immutable storage/restore, licence field allow-list, the final commit boundary with D and necessary ADRs. |
| D3 | Exact paths/tool authorization for reports and export targets, path protection and frozen-baseline/exception evidence. |
| D4 | Prior approval, cross-session/redaction/path/interruption negative tests, team regression and independent review memo. |
| D5 | The genuine complete original session of the student supervising OpenCode plus the history/licence interventions; Hermes initialization does not count as member development. The transcript basis is pending verification. |
| D6 | E's real business/collaboration contribution and reflection material; the formal identity/contribution is filled in by the person, and course documents cannot replace the feature. |
| D7 | Local diff, real PR/CI/independent review and branch-protection read-back; the earlier protection 403 did not take effect and must be re-checked. |
| D8 | History/export service/view, synthetic research bundles, positive/negative/read-back tests and reproduction steps. |
| D9 | The Plan stop point in the root `Prompt.md`, prior test/plan/path approvals and supervised Verify records. |

Acceptance reads the fields/status back from the final export artefact; checking only an "export succeeded" message or generating a few Markdown samples is not enough.
