# PaperTrace | Integration contract and contract change process

## 0. Force of this document and current phase

This document is the **semantic handover contract** shared by all five modules, used for requirement/test approval and subsequent implementation. This round establishes only the shared contract, synthetic fixtures, and offline gates; **business calls and orchestration are not yet implemented**. This document does not create separate shared models, nor does it present design ports as already callable.

Gate definitions and actual run status are in [`../ci/gates.md`](../ci/gates.md); both the test cases in the assignment document and the interaction tables in this document are implementation contracts and do not mean they have been run or passed.

- Source of truth for types, fields, enums, serialization, and identity algorithms: `src/papertrace/contracts.py` and its shared test/canonical fixtures.
- Source of truth for requirements and invariants: `docs/req/requirements.yaml`, `docs/architecture/invariants.md`; architecture and permissions follow `architecture-blueprint.md`, ADRs, and permission-model.
- When the prose conflicts with the real shared contract, the **approved real contracts files** are the basis for program interfaces, and the conflict must be registered immediately; this is not a license to weaken invariants. When fields needed to implement a safety rule are missing, block the affected integration/release, follow the change process in section 8 of this page, and do not quietly add compatibility fields or default-approve inside a module.
- The numbering and meaning of `INV-01`–`INV-08`, `QA-01`, `PERF-01`, `COST-01`, `SEC-01`, `GOV-01`–`GOV-04` are not rearranged on this page. Module tests align with the registry using these real IDs.

## 1. Module ownership, allowed dependencies, and UI boundary

| Module | Authoritative ownership | Provides outward only | Must never do |
|---|---|---|---|
| A `library` | Literature logical identity, content version, import status, snapshots | Version-pinned CorpusSnapshot; restricted file access/status information | Import `paperqa` directly; call a partial failure a complete library; approve evidence on behalf of C |
| B `retrieval` | PaperQA2 mapping, retrieval execution, low-level adaptation for controlled generation | EvidenceRecord; raw results from the neutral generation port / actually sent and citation mapping | Produce human accepted; release answers; return cross-module mutable Docs/PQASession |
| C `review` | Human decisions and the append-only review ledger | ReviewDecision sets; replayable revision/digest; effective-decision projection | Auto-approve from AI scores; overwrite historical decisions in place; modify literature versions |
| D `answer` | Approved set / sent set / cited set; call authorization, context policy, and the deterministic release gate | AnswerDraft, ReleaseDecision, and the verification reasons | Import `paperqa` directly; fetch unreviewed evidence; replace the gate with a model self-assessment |
| E `reports` | Research history, trace storage, and export | Research records and exports bound to the original snapshot/ledger/draft/release | Regenerate answers; promote a blocked draft to released; write back into review |

**Only B may import `paperqa` in newly added team source code.** The frozen upstream source's own imports are not subject to this new-code restriction; upstream must not be modified for the sake of structural checks. D is the owner of the answer capability and B maintains the third-party adaptation/calls: D decides approved inputs, budget, prompts, and release, and B does not gain approval/release authority. B-only is a code dependency boundary, not a ban on A/D reading upstream source; A/D may verify behavior within the exact read-only paths explicitly listed and approved in this round's Plan, but must not directly import/call upstream.

Modules do not call one another by importing a neighbor's private implementation. Later application orchestration passes shared models through dependency injection/neutral ports and is responsible for ordering and consistent reads; ports are proposed by the relevant business owner and approved in a Plan, **not implemented in advance this round as one large cross-module service**. For example, D's offline tests can inject a fake generation port and do not depend on B being finished.

The UI only displays state, collects operations, and calls application orchestration:

- Each person's view lives in their own module directory, accepts neutral inputs/commands, and does not each write its own approval state machine.
- A's first assembly PR wires navigation and dependency injection; the actual entry/orchestration paths are specified in that PR's approved plan, and others do not change the same entry point at the same time.
- "The button is not clickable" is not a security control; calling the service directly while bypassing the UI must still be subject to review and release constraints.
- Streamlit session state may only cache display state and cannot become the authoritative ledger, snapshot, or ReleaseDecision.

## 2. Semantic responsibilities of the five shared models

This table describes semantics, not another field definition; when implementing, read the field names and validators directly from contracts.

| Model | Producer → consumer | Semantics that must hold | Rejection/invalidation conditions |
|---|---|---|---|
| `CorpusSnapshot` | A → B/C/D/E | The logical literature ID is separate from the SHA256 content version; the snapshot content hash is stable; `documents` contains only DocumentVersion with `status="ready"` and does not change in place with the current library; failure/in-progress information stays in A's import records instead of being stuffed into the snapshot | File content does not match the version, source inaccessible, batch incomplete and the process does not allow it, identity cannot be verified |
| `EvidenceRecord` | B → C/D/E | Binds snapshot, doc, version, locator, and source text; summary/relevance are advisory; the stable evidence ID is computed from these five items by the shared algorithm | Foreign snapshot, nonexistent version, missing or unverifiable source text/locator, identity hash mismatch |
| `ReviewDecision` | C (human operations only) → D/E | Appends accept/exclude/reset-to-pending within the snapshot, question, and evidence scope; does not erase old records; ledger revision/digest are replayable. No decision means pending, not accepted; field validation of `actor_kind="human"` does not by itself prove the operation is genuine | Non-human source, out-of-scope evidence/question, write conflict on an old revision, replay digest mismatch |
| `AnswerDraft` | D (through B's low-level calls) → release verification/E | Binds the question, snapshot, review version, actually input evidence, and raw citation mapping; a draft does not automatically qualify for release | Unknown citation, context contamination, generation error/truncation, change in associated state |
| `ReleaseDecision` | D's deterministic gate → UI/E | States explicitly whether release is possible and why; bound to the specific judged draft, snapshot, and review version; not a model self-assessment | Inability to reproduce the three-set relation, freshness/identity verification failure, unauthorized calls, etc. all fail closed |

Business states may have **display labels** such as "waiting/importing/available/failed", "pending/accepted/excluded", and "draft/blocked/releasable", but wire enums always use the real definitions in contracts; Chinese UI labels are not schema values.

Key actual values in the current v1: ReviewDecision is `pending/accepted/excluded` with `actor_kind="human"`; AnswerDraft is `draft/abstained/failed`; ReleaseDecision is `released/blocked`. `stale` is a blocking reason/display state, not a ReleaseDecision enum that may be added at will. All five models explicitly set `schema_version=1` and reject unknown fields. Information not in the five models, such as raw model replies, usage, representation fingerprints, and import failure lists, should be stored separately by the owner in approved ports/versioned record bundles; do not add extra fields to frozen models.

### Identity and digest rules

1. The logical literature ID represents the same literature entry; SHA256 represents the file content version. File name, title, DOI, upstream MD5, and `dockey` cannot individually substitute for the content version.
2. Snapshot identity comes from the content hash specified by the shared contract and is not replaced by the current time, a random number, or a display index in a list. File order, normalization, and encoding rules call the shared implementation; modules must not each write their own hash algorithm.
3. Evidence identity comes from the shared hash algorithm over `(snapshot, doc, version, locator, source text)`. The source text is the source passage, not a model summary; changing any meaningful source content must produce a new identity. Do not use a prefix of a summary as a stable ID.
4. `SourceLocator` must have a complete 1-based inclusive page range or line range, together with `chunk_id`, `parser_name`, and `parser_version`; a chunk name alone does not yet satisfy the current contract. With only a page range, a precise sentence offset must not be fabricated; when upstream cannot provide a verifiable line range, B should build the mapping from the controlled source text, and if that is impossible it must fail explicitly/review the contract first rather than fabricate line numbers.
5. Repeated import of identical content is handled by A's policy, which explicitly distinguishes idempotent reuse from a new logical entry; old history is never silently overwritten. Saved research records read only their original version and are not automatically migrated to the latest snapshot.

## 3. The six handovers of later application orchestration

The following are **design interactions**, not implemented function signatures. The approved plan must map them to minimal ports, inputs/outputs, errors, and testable call counts; do not let the UI directly assemble five sets of mutable objects.

| Step | Caller / owner | Input | Output and mandatory checks | Action after failure |
|---|---|---|---|---|
| 1 Library preparation | Orchestration → A; A calls B through the neutral ingestion port | Locally allowed files explicitly selected by the user, human metadata, expected version | Per-file import results and a pinned snapshot; A decides library state, B only reports parse/index results | Keep the failure list, never quietly expand to the user's directories; incomplete work must not be marked complete |
| 2 Candidate retrieval | Orchestration → B | Pinned snapshot, question, approved retrieval configuration | A valid set of EvidenceRecord, all sources belonging to the snapshot, source text/summary kept separate | An empty set returns "no evidence" normally; errors fail explicitly and do not automatically request a whole-library answer |
| 3 Human review | view → orchestration → C | evidence ID, human choice/reason, expected ledger revision | A new ReviewDecision and a new revision/digest; read back to confirm | A conflict on an old revision is not overwritten; keep the form and require a refresh confirmation |
| 4 Controlled generation | Orchestration → D → B's neutral generation port | Pinned snapshot, the human ledger at that revision, question, approved evidence, context/budget policy | D records approved; records sent after final serialization; B creates a new filtered session, executes only aquery, and returns the raw result | With empty approved/sent the port call count is zero; unknown/stale/budget errors all stop the flow, and no further evidence search is allowed |
| 5 Release verification | Orchestration → D, reading current tokens from A/C | Draft, actual input/raw citations, snapshot/review tokens at start and end | A deterministic ReleaseDecision; only a pass becomes a release candidate | Keep the draft and the specific blocking reason; do not delete unknown citations and then claim a pass |
| 6 Save/export | Orchestration → E | Immutable snapshot, evidence, ledger, draft, release, and necessary run metadata | History can be read back; export keeps the same version/state/citation mapping, and the release commit and token comparison sit within one consistency boundary | If the original version is missing, mark it explicitly incomplete/blocked; do not substitute the current library and do not pass off blocked as released |

B's parse/index preparation and retrieval may have independent errors or costs; A's "import" operation is therefore not considered free or offline. Fake ingestion/retrieval ports remain the default, and real calls are not allowed before business dependencies and live use are approved.

## 4. The most important call constraints between B and D

The frozen upstream source has been checked at `src/paperqa/docs.py`: when contexts are empty, `aquery` may call `aget_evidence` again; `pre/post` may make extra model requests; a session can reuse old contexts; formatting handles unknown citations but does not prove semantic support. It is therefore not enough to write "the prompt requires using only approved evidence".

The later B adapter must operate within D's authorization boundary:

- The ingestion/retrieval route uses `Docs.aadd` and `Docs.aget_evidence`; it does not use `agents.ask`, `run_agent`, autonomous CLI flows, or a "fake agent". A fake agent may still request a real model.
- The generation route uses `Docs.aquery`, **creating a new session each time that contains only the evidence D selected**, and does not accept/reuse an old session or the full contexts from B's retrieval.
- Explicitly set `answer.get_evidence_if_no_contexts=false`, `prompts.pre=None`, `prompts.post=None`; do not attach old answers, unreviewed conversation history, or hidden background sources. Other model roles and client initialization are likewise subject to network/budget boundaries; a role must not be assumed to have no outbound connectivity just because it "shouldn't need one".
- D decides the tiered context, budget/truncation, constraint re-injection, and prompt version; B serializes per the approved policy and records the **finally actually sent** source IDs and citation key mapping. The serializer's ordering, cutoff, and `answer_max_sources` may make sent smaller than approved, so it is not enough to record the pre-filter list.
- B returns the raw model output and citation mapping, and D completes parsing/verification before formatting removes unknown citations. Unknown keys must not be silently deleted first and then treated as "not cited"; upstream `has_successful_answer` is not a ReleaseDecision.
- B/D tests must be able to intercept the sent content and prove that excluded and pending source text never flows into the request. A test fake must not just return "OK" without observing its input.

## 5. The three sets, ledger tokens, and concurrent invalidation

- `approved`: the set of evidence IDs that belong to the selected snapshot and question scope and were validly accepted by a human at the specified ledger revision/digest. Excluded and undecided items are not included; decisions for another question cannot be reused directly.
- `sent`: the set of evidence IDs actually sent after this round's budgeting, ordering, filtering, and serialization; if other evidence sources are mixed into the body, that is a leak even without explicit IDs and must be blocked.
- `cited`: the set of actually cited IDs parsed from the raw generation result and reliably mapped; an unknown citation must not be mapped to an arbitrary approved ID.

Release requires at least `cited ⊆ sent ⊆ approved` plus satisfaction of the registry's other fit criteria. The three-set relation only proves source authorization/structure; **it cannot prove that each natural-language claim is supported by the source text**; faithfulness, relevance, and safety escapes still require fixed-set semantic evaluation and human review.

Generation start captures `(snapshot content identity, ledger revision, ledger digest)` and re-checks it at generation completion and at final save/release. Both revision/digest must be replay-consistent with the original ledger; "only a different piece of evidence changed" is no reason to ignore an overall review-version change.

To prevent modification between "after verification" and "before save", the approved orchestration design must choose a consistency mechanism for the final release commit (for example, compare-then-commit inside a single-process lock, or compare-and-swap with expected tokens) and verify it with a controllable-concurrency fixture. This design must not be just two ordinary reads with no commit protection. A/C/E provide the necessary ports, and D remains the sole release decision; the UI must not add an `if accepted` in place of it.

Any token change, literature retraction, lost source, ledger conflict, or parse failure: this round's draft is kept but not released, and the user is required to re-review/regenerate on the new version; old approvals are not automatically migrated to the new snapshot. Historical release records keep the state and version that were valid at the time and may show "different from the current version", but history must not be tampered with.

## 6. Errors, offline isolation, and observable information

| Situation | Must be presented to the caller/user | Forbidden fallback |
|---|---|---|
| Partial import failure, file replaced | Which items failed, current version/integrity, allowed explicit retry | Reuse a same-named cache and claim the whole library is complete |
| Retrieval returns nothing / parse error | Distinguish an empty set from an execution failure, keep the source and the stage | Start an autonomous Agent to search the web for an answer |
| Ledger write conflict / non-human decision | Re-confirm after refresh; reject the invalid write | Overwrite the latest decision, treat model suggestions as confirmation |
| approved/sent empty | Not answerable and the reason, model call count zero | Call the model to "explain why there is no evidence" |
| Request timeout / rate limit / budget exhausted | Failure stage, real attempts and cost, draft not released | Retry without approval, switch provider, switch model |
| Unknown citation / token change during generation | The specific blocking reason, keep the original draft and version | Delete the citation, take the latest ledger and let it through automatically |
| Historical file missing / unsafe export target | Record as incomplete or refuse the path; the original record is unaffected | Read a personal directory to fill in the text, overwrite unrelated files |

Logs record only permitted IDs, states, stages, versions, counts, and redacted errors. Source text/questions/answers may contain private data, so full run evidence goes into controlled research records; do not print full settings, absolute personal paths, or credentials by default. Importing foreign pickle caches is forbidden, and state is never inherited from the real `~/.pqa`.

## 7. Shared fixtures and integration acceptance

Start from the canonical fixtures in `test/fixtures/contracts/`; only the `data` of their wrapper is input to the shared models, and synthetic metadata cannot be passed into `extra="forbid"` models. Module tests are planned for `test/offline/test_library.py`, `test_retrieval.py`, `test_review.py`, `test_answer.py`, and `test_reports.py` (the last four in the same directory), and module-specific synthetic material is planned for `test/fixtures/<module>/`; confirm the corresponding module scope once in the Plan. Within that scope, normal creation of tests/fixtures does not require per-file re-approval, but changes to shared fixtures still need review by the affected owner. Do not modify shared fixture expectations to accommodate an implementation; identities are computed by the real models/shared algorithms and must not be filled in by hand with plausible-looking random hashes.

Minimum cross-module scenarios:

1. Normal chain: two candidates from the same snapshot, one accepted by a human and one excluded; only approved items are sent/cited, and E reads back the same version.
2. Default pending: no review at all or only a high model score; D's call count is zero, and E may save the failure reason but has no released.
3. Budget truncation: approved is larger than sent; the model citing approved-but-unsent evidence must still be blocked.
4. Unknown citation: save the raw output; do not rely on the upstream post-cleanup answer as the only check.
5. Retraction/replacement mid-flight: replace the literature or write a new review revision while the request is executing; the old draft must not be released and history is not overwritten.
6. Identity tampering/cross-snapshot: same name with different content, evidence reused across snapshots, wrong locator/source text hash, and conflicting ledgers are all rejected.
7. Failure and recovery: one import fails, retrieval error, model timeout, export path traversal/existing file conflict; no implicit success and no unexpected overwrite.
8. Calling the service without going through the UI still enforces the same authorization/release gates; everything is synthetic and external model calls are zero.

Each case states the real requirement/invariant ID, its assertions, and the evidence that the test fails when that rule is violated. Offline fixture integration is not a live model-quality evaluation. Run entry points and actual gate status are in [`../ci/gates.md`](../ci/gates.md).

## 8. Contract change: propose → approve → sync → re-verify

Any change to fields/enums, hash/normalization algorithms, default states, review authority, set relations, ports, or exception semantics may not be decided verbally:

1. **The proposer creates a change record/follow-up issue:** write down the current contract version or commit, requirement IDs, problem reproduction, old/new serialization samples, affected consumers, compatibility/migration plan, and failure risks. When GitHub is not yet available, keep the local discussion and diff and do not fabricate an issue URL.
2. **Notify every affected owner:** at least the producer and each consumer must confirm; a change in the safety meaning of snapshots, review, or release requires an ADR and a genuine human approval, and the approver cannot be the author of the change. State which work may continue as fixture development during the freeze and which integrations are paused.
3. **Approve tests before implementing:** provide old/new canonical fixtures, tests that accept/reject the old format, at least one negative case, and cross-module regression; rotate upfront test approval, the independent reviewer, and the integrator according to the work plan.
4. **A separate shared-contract PR:** minimally update contracts, schema/fixtures/tests, affected requirements, ADRs, invariants, the trace matrix, runtime policy, and this page; explicitly state the new version and how old records are handled, and do not mix in a large batch of business features.
5. **Sync by dependency:** merge the contract first, then let A–E each sync their mappings/tests; results that are safely incompatible default to blocked and are not automatically converted to accepted/released. Assign one temporary editor for shared files, with other owners supplying patches, to avoid overwriting each other.
6. **Re-verify and lift the freeze:** full offline regression and gates; when prompts/models are affected, add an authorized live fixed-set evaluation. Read back the real interfaces and records, and lift the corresponding integration freeze only after a non-author has reviewed and approved. Record who approved which version and the evidence; "everyone implicitly agreed" is not acceptable.

### Upstream compatibility fixes and the pinned baseline

Ordinary module PRs keep the pinned PaperQA2 baseline, protected by the existing `frozen_check` under the current fitness rule/comparison definition. A necessary compatibility fix requires a separate ADR + human PR that explicitly updates that rule/comparison definition, names the affected source/owners, and runs negative tests plus the affected regression; verbal approval alone cannot make the current CI pass. Do not modify or bypass the gate in a business PR, and do not add a side-channel authorization platform. A/D raise precise read-only checks of upstream under their own approved Plans; B-only still constrains only the import/adapter implementation location in newly added source.

A contract change does not transfer long-term feature ownership; rotating support roles also does not permit an integrator to modify someone else's business boundary without the author's or approval's consent.
