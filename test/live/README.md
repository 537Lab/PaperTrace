# Live tests: pending feature development and separate authorization

This directory is not a passing test suite; there is currently no business adapter, real model test or provider credential injection configuration, so an empty directory must not be run and reported as PASS. The default initialization calls no model and reads no API key, and `test/offline` is strictly separated from live.

After members complete the A–E business logic, they add positive and negative live cases that can be traced to requirement IDs for the real adapter, and obtain independent student review, a plan and prior test approval. Before calling, approve the provider/model/version, synthetic data scope, call count, per-call timeout, maximum cost and abort strategy; keys are injected from a controlled service but are not stored in the repository/transcripts/reports. Follow the convention in `test/evaluation/README.md` to save the input/prompt/source/test hashes, the real content/usage/finish_reason and the cost. The initialization gate does not accept approvals self-declared inside the repository.

Full prior regression must cover upstream `tests/`, `packages/*/tests` and all team historical suites; see `docs/ci/full-regression.md`. Offline contracts passing does not mean PaperQA2 integration, live or semantic quality passes.
