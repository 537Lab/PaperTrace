# CI closeout: inherited full-regression diagnostics tests

Owner: LIN ZIQI, explicitly assigned shared CI by the student on 25 November 2026.
This is a test-only inheritance proposal. Main baseline: d893cefe162eb687fbd2854ee63b29569e087b2e.

## Observed remote blockers

Actual main run 45559243816: prior inventories collect successfully; team-offline has 931 cases, 905 passed and 26 failed, with no collection errors; team-runtime passes 1/1; frozen upstream has 324 passed, 82 failed, 7 skipped and 1 xfailed. The exact failed node identifiers and child diagnostics are not transported by the present workflow. They cannot be inferred from aggregate counts or relabelled as dependency failures without evidence.

Initialization and runtime locks have 12 conflicting package versions. Do not merge their installations into the trusted verifier, disable plugins or remove runtime tests to manufacture success.

## Authorized bounded next step

Inherit the exact 76-node test and English design blobs from PR #22 b15cb10, preserving all current main files and both histories. Implement the existing bounded/redacted diagnostics and six-file failure-only artifact qualification contract only after a non-implementer approves the new exact head. Keep the original failure verdict, complete baseline/current inventories, all test selections, socket isolation, lockfiles and upstream immutable. Actual environment partitioning or any gate-policy change requires its own concrete tests and independent approval; this proposal does not pre-authorize such a change.

The earlier #22 approval belongs to ziqilin669, who now owns the proposed implementation. The trusted gate excludes implementation participants from eligible approvals, so that old approval cannot authorize this author's implementation. Request a different student's approval rather than bypassing this check. No new OpenCode session is claimed and no role/permission is broadened.

After diagnostics land through independent source review, reproduce each of the 26 team failures with the correct isolated interpreter, classify setup/dependency versus behavior failures, and assign source defects to their module owners. Compare upstream failures with the frozen baseline and retain every unresolved failure. Full regression remains FAIL until the real required evidence passes; known baseline failures do not become PASS merely by being documented.

No provider call, secret change, workflow change or production implementation is included in this test proposal. Keep the proposal open and unmerged while RED. Build the implementation from its exact independently approved head and reference this test PR in the implementation body.
