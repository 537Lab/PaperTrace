# PaperTrace Engineering Report

This revision supplies LIN ZIQI's confirmed Module E contribution and reflection. Other members and the integration coordinator must add their own sections and the final whole-project evidence; this is not a completed group report.

# Module E Contribution - LIN ZIQI (60195853)

This section is ready for integration into the group's root Report.md.

| Sprint | Approximate hours | Delivered work |
|---|---:|---|
| Sprint 1 | 10 | Requirements, E responsibility boundaries, architecture and interface planning |
| Sprint 2 | 15 | Test-first implementation supervision, security/error-path repairs and page iterations |
| Sprint 3 | 15 | Integration diagnostics, independent reviews, English presentation and delivery evidence |
| **Total** | **40** | Retrospective estimates confirmed by the contributor |

Module E: Research history, provenance and controlled export
Contributor: LIN ZIQI (60195853)
Evidence updated: 25 November 2026; historical runs retain their original version scope.

Requirements and responsibility
Module E implements FR-E-01/02 and supports INV-02/04/05/08: a researcher can archive a research attempt, reopen it across sessions and export a consistent JSON or Markdown projection. Records preserve the original question, corpus snapshot, evidence and locators, review events and revision/digest, answer draft and release decision. The archive supports blocked, abstained and failed attempts rather than retaining only successful answers. E does not grant review approval, generate answers, or turn a blocked decision into a released result.

Design and implementation
The implementation separates a validated ResearchRecord envelope, an append-only HistoryStore, controlled exporters and an injectable reports panel. Existing history is not overwritten. A later corpus snapshot produces a superseded indication while retaining the historical bytes. The panel archives only after an explicit save action; opening or refreshing it does not create records. Selection determines which record is reopened and downloaded. Default exports hide original excerpts and redact local paths and sensitive information. Excerpt export requires a trusted authorization validator bound to the record and covered evidence, rather than a checkbox or a self-declared reviewer identity.

Test-first development and review corrections
The work used a student-approved plan, separate test proposals and exact-commit independent reviews. PR #8 covers core persistence, provenance and security; PR #31 adds page interaction tests. Review feedback led to additional negative cases for export authorization, symlink escape, absolute-path exposure and disk-write failure. Later repairs cover nested free-text redaction, legitimate zero-evidence/zero-review attempts, nested sensitive metadata and mutation after model validation. The page test setup was corrected when its load-failure mock also affected list loading; the assertions were retained and the new test head independently approved. An optional Streamlit import defect was reproduced in an environment without Streamlit and corrected without adding a dependency or disabling type checking.

Verification and observed results
The accepted E baseline contains 117 passing module tests. A saved clean-environment log reports full-project mypy success for the then-current 11 source files. Actual synthetic Streamlit AppTest evidence covers explicit saving, refresh without saving, historical reopening, duplicate immutability and blocked-state preservation. A separate integration harness combines real A overview/service/view code (30761595), the shared entrypoint (f64baad3) and E (91338a42). It verifies A snapshot delivery, upstream-error save inhibition, reference JSON/Markdown export equivalence and snapshot drift without rewriting history. D-to-E accounting diagnostics distinguish 0, 1 and unknown counts and preserve failure/blocked status. The older D #43 diagnostic exposed an upstream duplicate-sent accounting gap; Issue #44 reports a subsequent #50 check, which must not be relabelled as this pack's independent rerun.

Latest component acceptance and remaining limits
The inspected delivery main is 38db05423956ac4b03b9f9c6ede8208b33e71e5e. All D/E component source blobs and contracts are identical to the d893cefe snapshot independently exercised on 25 November 2026. That replay passed 195 tests: E history/export, shared entrypoint and D answer panel. A separate actual Streamlit AppTest drove the real D panel/coordinator and E panel/store/exporters: first load generated nothing, one Generate click crossed the synthetic generation boundary once, ordinary reruns did not regenerate, explicit Save created one record, reopening retained blocked status, both download bodies matched the real exporters, and repeated Save preserved stored bytes. The English facade is diagnostic presentation outside product source. Synthetic generation and captured review ports were used; no provider call or actual C-ledger filesystem integration was claimed.

Four duplicate-sent failure cases independently preserved observed attempt counts one, zero, unknown and absent accounting through D outcome.accounting, E persistence, reopening and default JSON export. Every result remained failed/blocked, original excerpts were hidden by default, and duplicate record IDs could not overwrite history. Markdown does not currently expose the run_metadata accounting block; JSON/history retain it.

These checks do not certify the full default application, publication transaction, final supported-runtime regression or live model quality. The current app.main() still displays a configured-module-ports message, and its non-A/E panel assembly remains a coordinator-owned acceptance task. Real-paper excerpt permission has not been supplied; default hiding remains required. The final video must identify the actual recorded version and distinguish component/synthetic demonstrations from complete live product acceptance.

The evaluated source/workflow and final release SHA are not frozen by this materials PR. E's 18 independent score rows remain blank pending actual same-SHA requests, responses, runtime/fixed evidence-ID mapping, authorization and a trusted raw-capture hash. C should cross-check the same evidence; no simulated score may be used as a human rating. Other members' report/transcript sections and the group contribution denominator must be supplied by their owners.

AI-use attribution
OpenCode assisted module development under restricted roles; Codex assisted supervision, diagnosis, verification, packaging and AI-assisted review. The supplied transcripts include permission failures and interrupted attempts. They do not establish human approval by themselves. Human review is evidenced separately by GitHub review records. No AI-generated explanation is presented as manually handwritten code, personal observation or a fabricated approval.

Confirmed effort: approximately 40 hours, split Sprint 1/2/3 as 10/15/15. Final team normalization is left to the consolidated report.

## Individual Reflection

Individual Reflection

LIN ZIQI | 60195853



My responsibility was to coordinate Module E's research-history and export functionality, with AI assistance for implementation, verification and review. A central lesson from the recorded work is that persistence is a trust boundary. A record may be structurally valid while still containing an absolute path in a nested reason, mutated metadata, or an unauthorized excerpt. Validation at construction alone was therefore insufficient: persistence and export needed their own checks.



The review process also changed the definition of a valid research record. An attempt with no candidate evidence and no review events is a legitimate outcome, not necessarily corrupted data. Preserving abstained, failed and blocked attempts makes the archive more useful and prevents the interface from implying that every saved record is a published answer. Similarly, an unknown model-attempt count must remain unknown rather than being converted to zero.



The implementation history exposed limitations in both tests and environments. One failure-injection test affected list loading before it reached the intended selected-record boundary. Correcting that setup required preserving the original assertions and obtaining approval for the new test version. The optional Streamlit import issue showed why a working developer environment cannot substitute for a clean CI environment.



For final delivery, I need to keep evidence claims proportional to the checks actually performed. A synthetic AppTest demonstrates button behaviour and persistence, but it does not demonstrate real model quality or the complete public workflow. Exact commits, independent reviews, archived outputs and explicit NOT_RUN labels help distinguish these outcomes. In future work I would schedule producer-to-consumer integration and evidence collection earlier, so final delivery is less dependent on late branch assembly and missing evaluation ownership.


## Evidence handoff

The annotated transcript entry is `transcripts/60195853-LIN_ZIQI.md`; full redacted native sessions are under `transcripts/native/60195853/`. Exact-version source/test/review evidence is retained in the Module E package. The team should normalize contributions after all member totals are agreed.
