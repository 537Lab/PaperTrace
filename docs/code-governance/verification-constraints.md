# Verification constraints (D4)

Any "pass" must be bound to the same code/test/requirement/config version, command, runtime environment, exit code and raw log. Course Project p6 requires three-level verification and p10 requires six categories of blocking gates; this document does not claim that D4/D7 are fully achieved.

## Three-level verification

1. **Structure:** requirement schema, module/import boundaries, frozen baseline diff, type/lint, dependency consistency, path/permissions, security rules and sensitive-file checks. Static checking is not an OS sandbox, and configuration parsing is not tool interception.
2. **Regression:** `.venv/bin/python -m pytest -c papertrace.pytest.ini test/offline` in the initialized environment covers only `test/offline/` and is not equal to full regression. The complete prior regression must be collected separately and report three sources: ① a full run of the team's `test/offline/`; ② runtime tests in the repository `test/` outside offline; ③ `tests/` and `packages/*/tests/` under the fixed upstream project configuration. The full upstream collection must be compared against the fixed baseline node IDs, with nothing omitted or silently marked; unauthorized live items must be listed item by item as BLOCKED and must not masquerade as skip-as-pass. Live may run only when the operator explicitly selects `--run-live` and independent human review has already authorized the data/provider/model/budget; by default there is never any external network access. The actual entry point/commands follow the runner synchronized by the lead and the real receipts.
3. **Behavior:** fixed cases check provenance, human authorization, the three sets, freshness, failure policy and model semantics. A fake only proves deterministic code and input boundaries; real prompt/model evaluation requires approved data and provider, a fixed set and real thresholds, and is BLOCKED when not approved/not executed.

Every feature has at least one positive case and one locatable negative test; every invariant must have an assertion that fails when deliberately violated. Tests are tagged with real `FR-*` / `INV-*`; a non-author approves the test version in advance, and tests are re-reviewed after their semantics change. Security code cannot be self-certified by the same generating agent. Keep the genuine RED/GREEN; do not delete failing assertions or tune thresholds to reach green.

The six categories of gates must all be retained: test approval before implementation, static/security/dependency checks, requirement schema, real semantic evaluation, complete prior regression, and an AI-use log for code/prompt changes. No gate may be deleted, downgraded, or passed off as passing via skip/fake/empty suite; remote required checks count as enabled only after configuration read-back and validation with a violating/legitimate control pair.

## Independence and records

- Each PR uses a genuine independent review in `docs/review-memo.md`; the verdict is only `APPROVE` / `CHANGES REQUIRED` / `REJECT`.
- Significant bugs are recorded in `docs/bug-diary.md` and technical debt in `docs/debt-register.md`; no entry is fabricated without facts.
- Genuine student OpenCode sessions / human interventions are the only D5 evidence; Hermes initialization, synthetic fixtures or script output cannot substitute for them.
- Remote protection must be configured after authorization, read back, and validated with a deliberately violating PR and a legitimate control; without read-back evidence it is marked pending.
