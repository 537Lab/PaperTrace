# PR review index (D4)

The team repository had not been created yet at the time of the initialization commit; the private repository https://github.com/537Lab/PaperTrace now exists. This round still has no student PR and no human student APPROVE. This file only indexes reviews that genuinely happened and cannot replace GitHub approval.

Each PR is recorded in `docs/reviews/PR-<number>.md`: requirements/fit criterion and change scope; architecture/INV alignment; implementation and normal/negative test quality; security/permissions/efficiency; operational metadata (baseline/HEAD, tools, commands, dependencies, model and cost authorization, what really ran and what did not); findings and disposition; the independent reviewer's genuine verdict APPROVE/CHANGES REQUIRED/REJECT. Approval must bind to the actual version and cannot be self-certified by the author editing documents.

Delivery checks for this round's initialization and engineering unblocking are in `INITIALIZATION_STATUS.md` and `artifacts/verification/unblock-*`; the lead has re-run all 250 offline tests and a real PaperQA API smoke. Independent AI re-review found gaps in base trust, removal of live markers, runxfail and similar areas, which were fixed with negative cases. Their nature is AI-assisted engineering verification, not the human approval the course requires.
