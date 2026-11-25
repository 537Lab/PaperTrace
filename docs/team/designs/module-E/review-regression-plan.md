# E review regressions and repair plan

Status: tests proposed; independent approval of the new PR8 head is required.
Reviewed implementation: PR14 e8ecf815b5aa20b6c16725e20b35f7ba7fb68487.
Prior approved tests: PR8 81e834596771cfbf5d140b2e68cb9431fcf083af.

## Confirmed defects

The reviewer identified two gaps missed by the original 32 tests. A read-only
synthetic reproducer confirmed both: default JSON exports the original
ReviewDecision.reason absolute path, and a valid abstained/blocked package with
no evidence, no review events and revision zero is rejected.

## Test-first scope

Append tests to test/offline/test_reports.py without weakening the original
32 cases. Use synthetic Windows drive, UNC and POSIX paths in review reasons,
document titles, command IDs, locator strings, upstream context identifiers,
advisory summaries, answer bodies and refusal reasons. Construct valid shared
models and recompute identity-covered references and canonical ledger digests.
Inspect parsed export JSON recursively so escaped Windows paths cannot create
false success. Verify that original stored content and identity tokens remain
unchanged; an external redacted projection is not an internal restore package.

Exercise no-evidence abstained/blocked and failed/blocked histories with both
empty and populated corpora, plus candidates with no review events. Validate
shared models independently before testing the E envelope. Save, reopen, list
and export these records with the canonical revision-zero ledger digest. Keep
negative coverage for inconsistent revisions, bad digests, unknown evidence,
stale draft/release bindings and attempts to mark an empty process released.

No shared contract, existing implementation, other owner module, workflow or
dependency changes are part of this test proposal. Run the proposed tests
against the reviewed implementation to distinguish behavioral RED from absent
implementation on the test-only branch. Use locked verification tools, disabled
sockets and elevated Windows symlink execution as before.

## Source repair after independent approval

Only after another student approves the exact new PR8 test head, continue the
OpenCode E implementation. Apply complete nested free-text redaction to external
exports while preserving identity/status tokens and internal original data.
Remove the blanket nonempty-evidence and nonzero-review requirements, retaining
canonical ledger validation, reference consistency and all shared contract
constraints. Do not fabricate evidence or reviews and do not promote blocked
records to released. Re-run all approved E tests, module lint/types and relevant
regressions; disclose remaining full-suite/environment limitations.

PR8 and PR14 remain open and unmerged. New tests are not approved by the old
81e8345 review. Passing original tests, this plan or AI review cannot substitute
for actual independent approval. If combining an updated test head into the
implementation changes the ancestry/order requirements, verify those gates and
prepare a replacement implementation PR rather than falsifying timestamps.

## Development record

OpenCode session ses_dfecae4b2ffeIwKbVIEJQcj2Z4, papertrace-build-E,
cityucs/CS5351/DeepSeek-V4-Flash. Codex supervises, reproduces defects and
validates tests. A shell request was denied; continuation was restricted to file
tools. Initial proposed tests had model-attribute and JSON-escaping assertion
errors; the supervisor requested corrections before publication. These early
test-harness failures are not counted as behavioral RED evidence.

## Final test-only verification

Locked verification tools, Windows Python 3.12, sockets disabled. The reviewed
e8ecf815 reports source is byte-identical to the local implementation used for
the behavioral run. The amended test file was executed with an explicit pytest
pythonpath pointing at that source; the proposal branch itself has no reports
implementation. Final result: 75 tests, 47 passed, 28 failed, zero errors/skips.
The 28 behavioral failures comprise 21 path-leak cases and seven legitimate
zero-review history cases. All original 32 tests remain unchanged. New negative
invariant cases pass against the old implementation; they must also pass after
repair. Ruff on the proposed test file passes. No source repair has occurred.
JUnit and full output are retained in the Team workspace as
E-review-regressions-old-implementation.xml and .txt.
