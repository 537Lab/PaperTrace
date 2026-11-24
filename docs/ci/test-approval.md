# Gate 1: prior test approval (implemented verifier)

Implementation: `scripts/gate_evidence.py`, called by `gates.py --gate test-approval` from the trusted base. Missing real evidence is BLOCKED; contradictions/self-approval/dismissal/wrong SHA are FAIL; a local `approved:true` is void.

## What the student actually does

1. The supervising student approves the Plan and one module/offline-tool scope; OpenCode is used to **generate only module tests, synthetic fixtures and design plans**, and business source implementation is forbidden at this point.
2. Push this content as a test proposal PR; it may stay open and RED, **do not merge red tests just to get approval**. Put the plan in `docs/team/designs/module-X/`, or as a standalone line `Plan: <specific plan description>` in the PR body. Append the AI-use log truthfully to each PR.
3. Another non-implementer checks the specific tests and `Approve`s on GitHub; the approval must point at the proposal's current head. If the tests change, approve again.
4. Branch the implementation from the test head; only after approval, write business code and open the implementation PR. A standalone line in the implementation PR description:
   ```text
   Test approval PR: #123
   ```
   Replace it with the real number; do not copy it verbatim. The test/plan blobs stay identical; unrelated tests already merged by other students may be present. After the implementation PR is merged, close the unmerged test proposal to avoid merging the old branch again.
5. If the test PR is green anyway, it is also supported to merge it first and then implement from the updated main; merging the test PR is not mandatory.

## Machine checks and honest boundaries

A read-only GitHub API check verifies the same private repository, the actual PR files, author/commit participants, the reviewer's write/maintain/admin permission, a currently valid APPROVED state, SHA and dismissal events. The GitHub server approve/PR created/merged times confirm the ordering of publication; the API commit time matching the local Git object and not preceding the approval is an additional check. **Git dates can be forged and cannot alone prove when the code was first written**; an independent student must review the real OpenCode process. Bots/authors/co-implementers cannot replace student approval; no self-built account service or mandatory allowlist is needed.

Safety paths additionally require the implementation PR body line `Architecture decision: docs/architecture/adr/002-development-readiness.md` (change it to the actually applicable ADR) and an independent human APPROVE on the current head. Ordinary module details do not get a new ADR each time. The approver and the final reviewer may be the same non-implementer.

Self-modification of gates/workflows must be checked by the **unchanged base verifier**; candidate code cannot certify itself. This engineering fix that first introduces the verifier has no traceable student prior approval, so it stays BLOCKED for human adoption; no backdating and no fabricated bootstrap PASS.

Local re-check command (exact 40-character SHA, real PR number):
```sh
.venv/bin/python scripts/gates.py --gate test-approval --scope full --base <baseSHA> --head <headSHA> --pr-number <implementation PR number>
```
Offline API fixtures without a token are only positive/negative tests of the verifier, not student approval.

## The post-merge main check is not another round of prior approval

PR events check the open PR; for a main push `ci_events.py` finds the single merged PR from the real commit association record, binds the event before, the merge SHA, the original base/head and the identical file tree, then hands the original head to the same approval verifier for re-verification. It does not simply trust a green check name, and it does not skip because the environment lacks a PR number. Dismissed/wrong SHA/unapproved tests, unreviewed merge conflicts or sourceless pushes are still rejected. Static/Schema/full regression/disclosure check the actual new main, and the semantic report remains bound to the approved original PR head.

After the implementation merges, an old RED test proposal that is still open may be closed; replay only accepts a `closed_at` not earlier than the implementation's `merged_at`, with the original approval/test blobs still identical. Closing or dismissing the proposal before the merge is still invalid. Maintainers are advised to wait for the main check receipt before closing the test proposal, to reduce API ordering confusion.

The first engineering adoption performs only the [one-time human steps](minimal-gates.md#one-time-first-adoption-of-pr-1-bootstrap); it does not replace ordinary module prior approval. The new main check retains the real evidence the first fix originally lacked instead of reporting `missing-pr-number`.
