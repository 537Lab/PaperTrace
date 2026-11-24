# PaperTrace coding-agent entry point

This project extends a fixed PaperQA2 baseline and does not replace it. Read this file first, then `Prompt.md`. Submit a plan first and wait for the student's real approval of the tests and the plan before developing the authorized scope. "Must" in these files is a constraint, not evidence that it has been satisfied.

## Reading order
1. `Prompt.md`, `architecture-blueprint.md`, `.opencode/rules.md` (human-maintained only) and `.agent/rules.md`.
2. Your own `docs/team/module-A.md` to `module-E.md`, the relevant `docs/req/requirements.yaml` entries, `src/papertrace/contracts.py` and the integration contract.
3. The relevant ADRs, invariants, permissions, state, verification and course sources as needed. Do not read the whole governance tree for a small change; the course basis is in `docs/sources/course-compliance.md`.

## Baseline, layout and authority
- Baseline: `c692d0dfeac4a0296599f7fe21a253a58b7ac12a`, tag `papertrace-upstream-baseline`.
- Frozen: `src/paperqa/`, `packages/`, `tests/`, `pyproject.toml`, `uv.lock`, `LICENSE`. The upstream README and automatic release workflow are preserved in `docs/upstream/`; the old workflow does not run automatically.
- New code goes only in `src/papertrace/`; shared definitions live only in `contracts.py`. A = library, B = retrieval, C = review, D = answer, E = reports. Only B's adapter may import PaperQA2 directly; D uses it through B's controlled answer port and must not bypass approval filtering. Members must not create these business implementations before their own turn.
- Team tests live in `test/offline/` and `test/live/`; the legacy `tests/` tree is kept as-is. Initialization passing is not full upstream regression passing.
- The model only advises. Human decisions grant evidence; D's deterministic checks decide whether a draft may be released; the UI and contract serialization cannot replace runtime authorization.
- Do not read `.local/`, credentials, environment secrets or private directories. Do not push, change Git settings, workflows, permissions or human rules, import third-party pickle indexes, add dependencies, or make paid calls.

## Executable verification
```sh
.venv/bin/python -m pytest -c papertrace.pytest.ini test/offline
.venv/bin/python -m ruff check --config papertrace.ruff.toml src/papertrace test/offline scripts
.venv/bin/python -m mypy --config-file mypy.ini src/papertrace
.venv/bin/python scripts/gates.py --gate schema
```
After the student confirms the module scope and the common offline tools once, routine edits, new files and exact offline commands in that scope do not need repeated approval. Other shell commands default to ask, and high-impact operations still need separate confirmation. The real status of models, full regression and remote human review is recorded in `docs/ci/gates.md` and `INITIALIZATION_STATUS.md`.

## Human checkpoints
Requirements classification/plan → **the supervising student approves the plan** → generate only this module's tests, synthetic fixtures and plan records (no business implementation) → **a non-implementer approves the exact test version beforehand** → OpenCode implements within the restricted scope → three-tier verification → independent human PR review. Test preparation may use the module role but carries no source-implementation authorization. Approval is a real student act; choosing a role does not itself prove approval. Keep real records for each stage, never fabricate approvals, and do not present this round's Hermes engineering fixes as student OpenCode contributions. Safety paths and shared-contract changes require an ADR and review by the affected owners; ordinary module details do not need a new ADR each time. The baseline exception process is in ADR-002 and is still protected by `frozen_check`.
