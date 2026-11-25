# E metadata source repair after exact test approval

Approved test head: PR8 1506de96a8da396d2e6852c7abccd8a8ecde8b25.
Independent reviewer ldk13856478627-cell submitted APPROVED at
2026-11-23T04:24:10Z; the supervisor read back the live API and the student then
authorized continuation. Approval of tests does not approve this implementation.

This branch begins at the approved test head and merges main 6235c33. It brings
forward the previous PR18 reports source with historical attribution. The only
new source differences are record.py and store.py. Existing export redaction,
trusted excerpt authorization, source associations and zero-review history
support are retained. All approved tests, fixtures and plans remain unchanged.

record.py now recursively visits every Mapping/list/tuple, checks sensitive keys
and every string leaf for absolute paths. Harmless strings and safe nested data
remain valid. store.py serializes exactly once, parses/validates those exact
bytes before persistence-path creation or writer invocation, then publishes the
same bytes. It does not trust the shallow-frozen object or a later reserialization.
No shared contracts, other modules, dependencies, workflow or gate rules changed.

Actual OpenCode source session: ses_df9493997ffeBGC203oMrwiotM,
papertrace-build-E, configured cityucs/CS5351/DeepSeek-V4-Flash. Codex supervises,
checks exact approval, preserves scope and runs independent verification.
Raw and sanitized session exports are retained in Team. Older source was not
invented in this session; original implementation sessions remain historical.

## Targeted verification

Locked verification tools, Python 3.12 on Windows, sockets disabled; elevated
execution allows symlink negatives. All 88 approved E cases PASS (previously
79 PASS / nine security RED), test collection has no errors/skips. Targeted E
Ruff PASS. Strict mypy PASS for four source files. Approved test/plan diff exit0.
Nine former RED cases are now green, covering nested metadata rejection and
pre-write rejection under real and injected writer paths. Safe mutation/data
controls remain green.

Full team offline regression is recorded separately. Module passes do not prove
all repository CI, full upstream regression, real model quality, C/D generation
or final end-to-end integration. The source-repair PR must receive independent
review of its exact current head. PR8, PR14 and PR18 remain open/unmerged.

Final full local offline regression: 367 passed, 75 failed, two skipped in
208.76 seconds, exit1. All 88 E cases passed; none of the remaining failed nodes
is in test_reports.py. Compared with the preceding reviewed-source comparison
(358 passed, 84 failed, two skipped), the nine E security cases changed to pass.
This aggregate difference does not establish every non-E failure's root cause.
The remaining Windows/platform and verification-environment failures are not
waived or labelled expected E RED. Full output: Team/E-metadata-repair-full-offline.txt.
Local ai-log and schema gates passed against actual main 6235c33. Remote CI is
separate and must be checked on the current source PR head.

Implementation PR: https://github.com/537Lab/PaperTrace/pull/26 (open, unmerged).

The local synthetic E and partial actual D.prepare->E handoff artifacts from the
preceding round remain separately labelled; they use synthetic C/release inputs
and are not evidence of full product integration or trusted export issuance.
