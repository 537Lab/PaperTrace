# Module A | Library, import state and version snapshots

> **Owner A:** end-to-end responsibility for the library feature, requirements, design, supervision of OpenCode, tests, their own view and PRs. This task book states reviewable acceptance; it does not mean the feature is implemented or that this round's Build has been approved.
>
> Always start from the [team start entry](../../TEAM_START_HERE.md); the authoritative source for interface facts is [`integration-contract.md`](integration-contract.md) and the real `src/papertrace/contracts.py`.

## User outcome and responsibilities

The researcher explicitly selects authorized local PDF/TXT files; every file has an explainable import status; the available literature forms a fixed snapshot; a version change or removal only changes the new snapshot, while old snapshots stay traceable.

A owns logical document identity, the source-byte SHA256 version, managed sources, per-file status and the ready-only `CorpusSnapshot`. B owns the controlled parse/representation calls; A keeps the import facts and must not record an error returned by B as ready. A does not perform retrieval, human review or answer release.

## Must and reviewable outcomes

| Requirement/invariant | Required behaviour and acceptance |
|---|---|
| `FR-A-01` | Handle only the PDF/TXT files the user explicitly selected; report success/failure and the stage/reason per item. Keep the logical literature ID separate from the content SHA256; the same name with different bytes yields a new version; invalid, empty, out-of-bounds paths or parse failures must not masquerade as ready. |
| `FR-A-02`, `INV-02`, `INV-05` | Content/member changes create a new snapshot; old snapshots and history records stay byte-identical. A snapshot contains only ready `DocumentVersion` entries, and downstream use is refused when the source file/hash does not match. Removal does not claim physical erasure of upstream vectors. |
| `INV-06`, `QA-01`, `SEC-01` | The service layer and the view share path/type/identity validation; contracts use the real models/hash implementations; no reads or writes outside the paths, no absolute-path leakage and no personal data. |

Fit criterion/priority follow `docs/req/requirements.yaml`; this task book neither copies nor relaxes the thresholds.

## Boundaries and proposed change scope

- **Handed to B:** controlled files, manual metadata, explicit configuration; receives success/failure stages. Assume by default that any parsing/embedding may call out, and do not call local import offline.
- **Handed to C/D/E:** fixed snapshot plus version verification/restricted source reading interfaces; do not hand over mutable PaperQA objects, and modules must not modify A's files directly.
- **Routine module scope (confirmed once at Plan; routine edits/new files inside the scope are not approved one by one):** `src/papertrace/library/` (service and own view), `test/offline/test_library.py`, `test/fixtures/library/`. After this round's scope is approved, the corresponding Build role permissions apply; shared contracts/fixtures, entry/orchestration, requirements, dependencies/lock, CI, logs and the upstream baseline are approved separately.
- Upstream fixes follow the ADR-002 reviewed-patch process; module PRs must not modify the frozen baseline directly. Must not read `.env`, `~/.pqa`, credentials or unauthorized paper directories.

## Fake-first development and acceptance without waiting for B

Use the canonical `CorpusSnapshot` / `DocumentVersion` with hand-written synthetic TXT/small PDFs; inject a fake parser/import port that can return success, parse failure and timeout, and that records its inputs. The fake initializes no model, network or real upstream.

Minimum verification: valid import and per-item status; the same-byte repeat policy, and the same name with different bytes changing version; bad/empty files, path traversal, partial failure; source hash change/read-back loss; old snapshots unchanged; a direct service call bypassing the view still refuses out-of-bounds access. Verify that a snapshot contains only ready entries and that failures are neither lost nor disguised; identity is computed through the shared model, not hand-filled with a random hash. The full offline team regression and gate status rest on real execution evidence; the cases in this task book are not PASS.

## D1–D9: module evidence A should leave behind

| Item | Evidence for this module |
|---|---|
| D1 | Registry fit for `FR-A-01/02` and `INV-02/05` → use-case/trace mapping and change sources. |
| D2 | State machine, version/snapshot/removal, B ingestion port, exception and history policies; ADR for security-semantics changes. |
| D3 | This round's exact path/tool authorization, restricted source storage, and frozen-baseline/exception audit evidence. |
| D4 | Pre-approved test version, path/version-change/failure negative tests, team regression, real review memo and bug/debt. |
| D5 | The complete raw session of the student genuinely supervising OpenCode and the reasons for human intervention; Hermes initialization must not count as member development. The basis for the course transcript count is pending student/instructor confirmation. |
| D6 | A's real feature/collaboration contribution and reflection material; identity and contribution are filled in by the person, no pre-writing. |
| D7 | Local diff, real PR/CI/independent review and the actual read-back of branch protection; the currently known protection 403 has not taken effect and must be re-checked at the end. |
| D8 | Library service/view, synthetic fixtures, positive/negative/regression tests and reproducible commands. |
| D9 | Root `Prompt.md` startup, Plan stop and test/plan/path approvals, supervised Build/Verify records. |

Module acceptance must also demonstrate the end-to-end user outcome, human approval before implementation, and real independent review; the task book or an empty shell does not count as done.
