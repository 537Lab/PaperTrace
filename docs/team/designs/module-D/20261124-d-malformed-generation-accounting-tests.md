# Module D regression proposal for accounting on a rejected gateway result

The supplemental proposal responds to the independent pre-review of Draft PR
#43 at `c36ad0bffb5b7e7d0465e0b7309e14d2098c400d`.
`FR-D-03` governs the transfer of observed accounting from B. `FR-D-02` and
`INV-04` still govern evidence and review scope for the failed draft.

A B result marked `SUCCESS` with duplicate `sent_evidence_ids` reaches the
real D adapter through a synthetic gateway. D rejects the result as
`RESULT_SHAPE_INVALID`. The failed draft has empty body, sent IDs and cited
IDs, and retains the validated review tokens and approved evidence. The
caller currently loses independently valid B accounting when D discards
that result.

## Proposed observable behavior

Keep `result` empty and expose optional validated accounting on D's internal
`AnswerGenerationOutcome.accounting`. The proposal leaves the internal error
carrier and validation order to the implementation. Preserve the B-reported
provider and model and exactly one of `1`, explicit `0`, or unknown `None`
for the modeled cases. If the accounting object is absent, its attempt count
is a boolean, or its provider is blank, expose no accounting for that case.
The gateway runs once in every test. Diagnose the rejected output without
returning the raw answer or saving its citations in the draft.

The tests use a real B result class and seed the accounting template through
an empty-evidence B Gateway call with a model factory that fails on entry.
Malformed duplicate IDs and test accounting values are supplied by a
synthetic gateway response. Product symbols load only when tests run.

## PR scope agreement

> This slice verifies the offline B-to-D accounting handoff and carries
> observed provider, model and answer-attempt data for diagnostics. The
> outbound authorization grant, approved budget and attempt limits, and call
> deadline under INV-07 are separate acceptance work. The November 24 scope
> agreement leaves that work outside PR #43. Product-model semantic evaluation
> requires an approved model, dataset and run budget.

## Local verification on November 24, 2026 HKT

| Check | Result |
| --- | --- |
| New module collection with selected #42 contract/config files and no D generation source | 6 collected, exit 0 |
| New module execution on #43 | 3 failed, 3 passed, exit 1 |
| Existing accounting and generation suites excluding three L2b bridge cases | 126 passed, 3 deselected, exit 0 |
| Same baseline with the new module | 3 failed, 129 passed, 3 deselected, exit 1 |
| Ruff on the new file | Pass |
| Existing approved #42 accounting test and plan | Git blobs match #42, #43 and the working tree |

All three failures reach the assertion that validated accounting is readable
on the rejected outcome. The earlier assertions for the rejected draft and
single gateway invocation pass. The missing or invalid accounting controls
pass. Full offline and upstream suites, remote checks for this proposal,
product-model calls and semantic evaluation were not run in this session.

## Review and implementation handoff

Freeze the new test and plan as a test-only proposal using the agreed
publication base. Preserve the existing approved test and plan blobs and
append the factual AI-use entry at publication. The test proposal requires
independent approval of its precise GitHub commit. Build the D-local repair
from that approved test commit using supervised OpenCode, rerun these six
cases and the accounting and generation suites, and check the locked
bridge runtime and applicable CI on the final implementation commit.

The current test draft and local verification were prepared by Codex. The
OpenCode handoff prompt is prepared separately and has not been submitted.
