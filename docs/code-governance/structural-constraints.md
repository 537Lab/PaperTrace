# Structural constraints (D3)

Basis: ADR-001 and proposed ADR-002 (both awaiting student approval); `INV-01`–`INV-08`; course Project p5–6. This document specifies the target structure and does not claim that business modules or tool permissions are already implemented/enforced.

## Module responsibilities

- A `library/`: import status, logical identity, SHA256 version and immutable snapshots; only ready papers enter the shared snapshot.
- B `retrieval/`: the sole PaperQA2 adapter, retrieval/generation-neutral ports and controlled call metering.
- C `review/`: genuine human commands, an append-only ledger and revision/digest; structural fields cannot self-certify human.
- D `answer/`: approved/sent/cited, deterministic context/budget, citation and freshness checks, and the sole release decision; it depends on an observable fake B port and must not import `paperqa` directly.
- E `reports/`: immutable research history and license-bounded exports, without changing A/C/D authoritative state.
- `contracts.py` is the sole shared data boundary and does not become a sixth business module; thin views only display/collect operations, and entry points do not duplicate authorization rules.

Leaf modules must not have circular imports and must not directly import a neighbor's private implementation. Modules hand off through approved neutral ports and the five shared models. Only B may import `paperqa` in the team's new business code. The user interface or `session_state` is not the authority for the human review ledger, the current snapshot or release.

## Traceable structure

Every Must feature and security-critical constraint must be linked to real `FR-*` / `INV-*`, at least one locatable test, and the module charter/trace. Every feature has at least one negative test; the test must fail when the target boundary is broken. Changes to security-critical semantics (approval authority, source identity, model egress/budget, release gate, permissions, history) require an ADR, review by the affected owner and the student in person, and cannot take effect through implementation or test changes alone. Human-approved requirement/rule changes must be synchronized to the related requirements, architecture, tests, permissions and prompts within one sprint.

## Baseline and exceptions

The upstream `src/paperqa/`, `packages/`, original `tests/`, `pyproject.toml` and `uv.lock` keep a fixed baseline in ordinary feature PRs and are protected by the existing `frozen_check`; they are not permanently unmodifiable. A necessary compatibility fix requires an independent ADR plus a human PR, explicitly updates that fitness rule/comparison basis, lists the problem, minimal diff, license/dependencies and affected scope, and runs the negative test and the affected regression. Verbal approval alone should not make the current CI pass, and no bypass authorization platform is added.

**Permissions deny by default:** every unapproved path is `R=deny, W=deny`. Feature ownership or a charter's candidate directories is not write authorization; this round's Plan must list the exact relative files, tools and created files, and be approved by a non-author. Permission boundaries are in [`permission-model.md`](../architecture/permission-model.md); actual tool/version evidence is recorded separately; structural checks are not an OS sandbox.
