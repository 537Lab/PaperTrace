# Technical debt register (D4)

The following are genuine known gaps, not production failures that have already occurred. All statuses are OPEN; closing requires attached tests and approval evidence.

| ID/category | Debt | Responsible feature/closure condition |
|---|---|---|
| DEBT-01 evaluation debt | No real model connectivity or semantic baseline | B/D: approve provider/model/papers/budget, plus a real fixed evaluation and usage receipt |
| DEBT-02 guardrail debt | GitHub protection and trusted pre-implementation test approval are not deployed | Whole team/authorized administrator: read back the rules, six categories of failing PR plus legitimate controls |
| DEBT-03 hidden dependencies | The 261 packages pinned by uv.lock have actually been installed; 377 base/current nodes have been collected, but full execution with network access disabled has failures/timeouts, and 9 live items are unauthorized | B/D: keep the original tests, and complete the full prior run after obtaining real API data/cost permission; the 250 offline tests must not be passed off as a substitute |
| DEBT-04 prompt rot | The runtime prompt is only a first draft of the architecture contract, with no real quality validation | D: real controls and thresholds, re-run on every model/prompt change |
| DEBT-05 hallucinated dependencies | Must prevent agents from adding non-existent or unlicensed libraries | Each module: exact lock/official source/license verification; if unproven, do not use |
| DEBT-06 untouchable code | Upstream freeze does not mean fixes are permanently forbidden | B: with evidence, a minimal ADR + attribution + human review + regression; do not rewrite by default |
| DEBT-07 agent-induced bloat | The five modules are not yet implemented; guard against expansion of a generic framework | Each module: minimal vertical slice, no redundant intermediate layers, review checks |
| DEBT-08 human/cognitive debt | The student has not yet approved this round's contract, architecture, or the applicability of the initialization tooling | Whole team: explain each module's inputs/authorization/failure paths and genuinely approve the plan |
