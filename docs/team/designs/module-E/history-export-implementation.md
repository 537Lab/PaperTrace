# Module E implementation verification

Implementation branch: `feat/E-history-export`.
Test approval PR: #8
Approved test head: `81e834596771cfbf5d140b2e68cb9431fcf083af`.
GitHub reviews read back as APPROVED at 2026-11-22T01:48:12Z and 01:49:29Z.
This is prior test approval, not independent approval of this implementation.

## Behavior

Four E-owned files implement a versioned research record, append-only UUID history,
readback, JSON/Markdown exports and a superseded history view. Shared contracts,
approved tests and other modules are unchanged. Record associations and review
digests are checked. Existing record IDs cannot be overwritten. Original excerpts
require a record/evidence/purpose-bound grant accepted by a trusted verifier;
the application must supply that verifier. A caller-provided identity string is
not authorization. Default exports hide excerpts and redact local paths.

Publishing uses a sibling temporary file, fsync and exclusive hard linking.
Unsupported hard links fail closed and clean the temporary file; there is no
copy-to-final fallback that could expose partial records. This requires a local
filesystem supporting hard links. This is not a sandbox against concurrent
malicious replacement of directory ancestors.

## Actual local validation, 2026-11-22

Windows Python 3.12 with the exact `requirements-init.lock` packages installed in
the separate verification directory. Pytest uses pytest_socket and sockets are
disabled. Elevated execution enables Windows symlink negative tests.

- `test/offline/test_reports.py`: 32 passed after the final storage and lint fixes.
- Ruff for `src/papertrace/reports`: passed.
- Mypy for `src/papertrace/reports`: passed, four source files.
- Combined contracts/reports: 180 passed, one failed. The unchanged shared
  `synthetic-paper-a.txt` is checked out as CRLF while Git stores LF; its byte
  hash differs. No fixture or approved test was rewritten to hide that failure.
- Full team offline regression: 312 passed, 74 failed, 2 skipped in 209.30s.
  All 32 E tests passed within this run. Failures include Windows lacking C's
  `fcntl` dependency, unavailable WSL/bash, child test processes unable to find
  pytest_socket in the separate target installation, LF/CRLF fixture integrity,
  frozen-tree/static checks, and semantic binding/runtime-distribution checks.
  The semantic checks report binding mismatches and duplicate installed
  distributions; their complete root cause has not been independently isolated.
  These are actual non-E failures/environment blockers, not expected E RED.
  The two skips require macOS sandbox-exec. No claim of a green full regression,
  upstream regression, CI or real-provider semantic evaluation.
- With explicit approved base and full implementation SHA, ai-log and schema
  gates both PASS. An initial schema invocation using the unavailable default
  upstream base failed at input resolution; it is not the final gate result.
- Whole-tree ruff fails on the unchanged scripts/paperqa_smoke.py import order.

## Development evidence

OpenCode 2.0.12, agent `papertrace-build-E`, configured school model
`cityucs/CS5351/DeepSeek-V4-Flash`, session
`ses_dff02f043ffep3PJYXRMy43zJA`. Codex supervised the session, supplied the
approved scope, ran validation and identified the unsafe storage fallback.
OpenCode wrote the source and corrected the fallback and final lint whitespace.
Denied shell/file attempts and an output-length interruption occurred before
the successful split implementation; these are not successful verification.
The actual sanitized session export is retained in the enclosing Team workspace
as `E-opencode-session-sanitized.json`; raw continuation output is also retained.
The sanitized export is a disclosure artifact, not an unredacted transcript or
evidence of human approval. No credentials belong in repository evidence.

Implementation PR: https://github.com/537Lab/PaperTrace/pull/14 (open).
Remaining work: independent human review and remote CI verification.
PR #8 and implementation PR stay open; do not merge.

## Integration follow-up

Main was synchronized on the remote branch. The exact 5af4292 archive was
verified again: 32 E tests passed, E ruff and mypy passed. A local copy is in
Team/PaperTrace-E-submitted-5af4292. Git HTTPS transport repeatedly failed;
GitHub authenticated API was used for synchronization and evidence upload.
The original worktree retains local c05cef5 and has not been falsely represented
as synchronized with the remote Git history.

CI for 5af4292: ai-use-log, schema and semantic-evaluation succeeded. Static
checks failed lint while types, dependencies, frozen baseline, architecture,
contract API, secret heuristics and permission checks passed. Test approval
reported missing execution plan in the test PR body. The previously approved
plan summary was truthfully added to PR8 body afterwards, explicitly dated as
a later recording; approved test head 81e8345 was unchanged. This documentation
commit requests fresh CI; no successful approval check is claimed before rerun.
Full remote regression was still in progress at this observation.
