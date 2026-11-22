# E review repair following new test approval

PR8 test head: 9b6629b2f3a62c9f00bec7a30ce12cb913d31baa.
Independent reviewer: 537Lab, APPROVED at 2026-11-22T10:04:32Z.
This branch starts at that exact head, synchronizes main 6235c33, and preserves
all approved test/fixture/plan blobs. Earlier PR14 remains open and unmerged.

The existing reports implementation from PR14 e8ecf815 was brought forward with
historical attribution. Its original session was ses_dff02f043ffep3PJYXRMy43zJA.
Only export.py and record.py are repaired in this round through actual OpenCode
session ses_dfd25ca84ffeUfKp8Rkay2N0pC, papertrace-build-E, configured school model
cityucs/CS5351/DeepSeek-V4-Flash. Codex supervises and performs verification.

External JSON/Markdown projections recursively redact nested string values and
keys after excerpt permission filtering. This includes review reasons, document
titles, command IDs, locator/parser text and upstream context identifiers.
Internal record models/stored bytes and snapshot/evidence/review tokens remain
unchanged. Exported redacted projections are not internal restore packages.

The E envelope now permits empty evidence and revision-zero/empty event histories.
Shared models still require appropriate abstained/failed and blocked states.
Length/revision consistency, canonical empty-ledger digest, reference scope,
draft/release binding and no-release-promotion constraints remain enforced.
No shared contracts, approved tests, other modules, dependencies or CI changed.

The original 28 behavioral RED cases now pass. Full 75-case E suite and E Ruff
passed. Initial strict mypy detected an Any return from the recursive sanitizer;
OpenCode was asked for a type-only correction before final verification.
Full offline regression is recorded separately; module success does not mean
all repository CI, upstream regression or real-model quality passed.

Raw continuation events and sanitized actual session export are retained in the
Team workspace. A denied shell discovery attempt was not executed; the session
continued with scoped read/edit tools. An initial local main merge failed due
to shallow history; after deepening Git history it merged normally. No unrelated
history override, rewritten timestamps or fabricated approval was used.

A replacement implementation PR is required because PR14 predates approval of
the new test head. This is a new delivery of historical source plus scoped
repairs, not a claim that all source was originally written after this approval.
Independent exact-head implementation review is still required. Do not merge
PR8, PR14 or the replacement without the team's explicit merge decision.
