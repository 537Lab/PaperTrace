## What this PR does / which module it belongs to

Module: A / B / C / D / E (circle one)　｜　Does it touch the shared contract or CI: yes / no

<!--
This template turns the six blocking gate categories from course p10 into a checkable evidence list.
All six gate categories are retained; a BLOCKED gate does not become PASS because a box is ticked.
The minimal implementation plan is in docs/ci/minimal-gates.md.
-->

## Six gate-category evidence (the rotating reviewer checks item by item; the author cannot self-approve)

- [ ] **1 Prior test approval**: an independent "test/plan PR" is approved first (it may stay open/RED, merging it first is not mandatory); paste the link, its head SHA, the approver and the approval time. This implementation PR has not modified the approved test files; if it did, they were approved again.
  - Test PR: ____　Approver (≠ this PR's author): ____　Test tree SHA: ____
  - Status when not satisfied: **BLOCKED**; an in-repository `approved: true` or a local timestamp must not be substituted.
- [ ] **2 Static analysis**: the `static-analysis` check is success; paste the actual ruff / mypy / schema output. A full supply-chain audit is still out of scope for this round.
- [ ] **3 Requirements Schema**: the `schema` check is success; if `docs/req/requirements.yaml` changed, describe the corresponding fit criterion and trace updates.
- [ ] **4 Semantic evaluation**: applies only when product prompt/model/AI behavior is touched. Paste the approved provider/model/call-count/cost authorization record, the `docs/reviews/eval-*.json` report, the dataset SHA, and the independent reviewer's per-item rubric rationale.
  - No real calls and independent human scoring → **BLOCKED**; fixed mock replies, skipped calls and self-written PASS are not accepted in any form.
- [ ] **5 Full prior regression**: the three sources — team offline + runtime + upstream — actually executed with 0 skip; paste the upstream `collect-only` list, JUnit, version fingerprints and the human review conclusion on the before/after difference.
  - L2 not finished / skips present / pre-existing baseline failures unaddressed → **BLOCKED**; the 170 green items must not be passed off as full.
- [ ] **6 AI-use log**: the code/prompt changes have left real newly added disclosure in `docs/ai-use-log.yaml`; the reviewer checks that the content is truthful.

## Independent review

- Rotating reviewer (≠ author): ____　Review conclusion: pass / changes required
- Location of the real OpenCode session (D5): ____　(must not be fabricated afterwards, and the initialization session must not be passed off as a personal contribution)
- Known incomplete items / debt: `docs/debt-register.md` entries: ____

## Current remote boundary (do not misread)

Branch protection and required checks are **not yet in effect** (403 on a private repository under the free plan). The six CI checks on this PR really run and show red/green, but they **do not constitute enforced merge blocking**; missing real evidence is BLOCKED, contradictions/quality or test failures are FAIL; no red light may be uniformly explained away as expected success. Reviewers should check the list above manually before merging.
