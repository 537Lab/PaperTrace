# PaperTrace

PaperTrace is an evidence-review workbench built on a pinned PaperQA2 baseline. It imports local papers, retrieves candidate evidence, lets a human accept or exclude each item, generates an answer only from accepted evidence, and stores a traceable research record. It extends PaperQA2 rather than replacing it.

## Architecture

The system is split into five modules. A owns the library and document versions; B owns retrieval and the single PaperQA2 adapter; C owns the review ledger; D owns answer preparation and the deterministic release gate; E owns the saved research record and export. Shared data definitions live only in `src/papertrace/contracts.py`.

The model is advisory. Only a human review decision can mark evidence as accepted, an empty accepted set must stop before any generation call, and a draft may be released only when `cited ⊆ sent ⊆ approved` and the review and snapshot identities are still current. D enforces these checks; the UI and serialized contracts cannot grant authorization.

## Project layout

- `src/papertrace/` — the five modules and the shared contracts.
- `src/paperqa/`, `packages/`, `tests/` — the frozen upstream baseline.
- `test/offline/` — deterministic tests; `test/live/` — tests that need separately approved provider access.
- `docs/req/` — machine-readable requirements and the PRD.
- `docs/architecture/` — blueprint, ADRs, invariants, trace matrix, memory, permissions, runtime policies, evaluation.
- `docs/code-governance/` — structural, verification and tool rules.
- `docs/team/` — module charters, integration contract and design records.
- `docs/ci/` — gate definitions and the full-regression procedure.
- `transcripts/` — annotated student–agent sessions.
- `prompts/` — versioned runtime prompts.

## Running the tests

The offline suite is deterministic and blocks sockets:

```sh
.venv/bin/python -m pytest -c papertrace.pytest.ini test/offline
```

The live suite needs separately approved provider access, data, model, call budget and a time limit. No credentials or approvals are committed, so it must not be run to make a gate green:

```sh
.venv/bin/python -m pytest -c papertrace.pytest.ini test/live
```

The full suite adds the team runtime/integration tests and the upstream `tests/` and `packages/` suites in their own environments. It is driven by `scripts/full_regression.py` against a real previous commit, or by the regression gate:

```sh
.venv/bin/python scripts/full_regression.py --base <40-char-sha> \
  --runtime-python .venv-runtime/bin/python \
  --upstream-python .venv-upstream/bin/python \
  --output .local/full-regression
.venv/bin/python scripts/gates.py --gate regression --scope full
```

See `docs/ci/full-regression.md` for the environment setup and the rules on skips, deselection and live tests.

## Blocking gates and branch protection

The CI pipeline implements six blocking gates: test approval before implementation, static analysis (lint, types, architecture, dependency and permission checks), schema validation of the requirements registry, semantic evaluation for prompt or model changes, full prior regression, and an AI-use log update on every code or prompt change. A change that fails any gate cannot merge.

Branch protection requires the CI checks to pass. Changes to safety-critical paths also require human review with an accompanying architecture decision; a role name, a passing script or a document cannot substitute for that approval.

## Repository

The real project repository is <https://github.com/537Lab/PaperTrace>. Current gate results and known failures are reported in `docs/ci/gates.md` and `INITIALIZATION_STATUS.md`; a document describing a gate is not evidence that the gate passed.
