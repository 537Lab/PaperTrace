# ADR-002: Single entry point, independent fake development and reviewed upstream fixes

- **Status: proposed-awaiting-human**; not a decision the student has approved.
- **Scope:** clarifies development startup, the A–E parallel boundary and the PaperQA2 baseline exception process; it does not change FR/INV, shared model fields, the six gate categories or functional ownership.
- **Authoritative entry:** [team start entry](../../../TEAM_START_HERE.md); the interfaces are defined by [`integration-contract.md`](../../team/integration-contract.md) and the real `src/papertrace/contracts.py`.

## Problem

The old task documents repeated the startup commands, reading order, approval flow and integration details; B's upstream adapter was easily misread as a precondition for D; and “freezing upstream” could be read as never fixing even a necessary defect. This increases startup burden, serializes the modules and leaves the safety exception ambiguous.

## Proposed decision

1. **One startup entry.**`TEAM_START_HERE.md` is the only team entry; the README, work plan and task documents all link back to it. `docs/team/startup.md` serves only as a reference for clone/initialization commands. A Plan reads the root startup rules, its own task document, the relevant registry/contract and the interface contract; architecture material is consulted as needed, with no unlimited serial reading list.
2. **Separate B's mechanism from D's policy.**B maintains the only PaperQA2 adapter and the neutral retrieval/generation ports; D owns the authorized set, context/budget, citation verification and the release gate. D develops independently against a fake port that can record the final payload, calls and freshness, without waiting for B to finish and without importing `paperqa` directly. An approved Plan may list exact read-only upstream source paths for D to verify behavior.
3. **Fake-first, without treating a fake as live.**A–E can all be developed against the shared legitimate contracts and self-written synthetic fixtures. A fake must expose the actual input, state, counts and faults; it can verify only deterministic logic, not model quality, paper licensing or remote protection.
4. **Ordinary feature changes keep the baseline.**The fixed tag/commit is the audit baseline and is protected by the existing `frozen_check`. A normal module PR does not touch `src/paperqa/`, `packages/`, the original upstream tests or the dependency lock. A necessary compatibility fix is not permanently forbidden, but it requires a separate ADR + human PR that explicitly updates the `frozen_check` fitness rule/comparison basis and provides the reproduction, the minimal diff, the licensing/dependency impact, the affected owners, positive and negative tests and the affected regression; a verbal approval alone cannot make the current CI pass. The fix must not be mixed into a business PR or add a bypass authorization platform.
5. **Permissions remain deny-by-default.**Paths that are not listed are unreadable and unwritable by default; the allowlist is limited by role and by this round's approved plan, and explicit module directory rules may be used. After a scope is approved once, routine edits, new files and common offline commands do not need repeated approval. A necessary directory glob must state its boundary and verify that the resolved path is still inside the repository. There is no unconditional allow-all exception.

## Consequences and acceptance

A/C/E can proceed without installing the real PaperQA2; D can first verify zero calls, the three sets and freshness; B remains responsible for the single upstream call boundary. Interface and safety changes are still reviewed against the integration contract, the requirements trace and the ADR. This ADR does not pre-authorize Build, dependency installation, model calls, external network, permission changes or upstream writes. Until the student accepts it, the proposal is not treated as approved; without measurements it stays proposed/blocked and is not marked PASS.
