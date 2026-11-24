# Invariant Register (INV-01–INV-08)

> Status: proposal, awaiting review by the student in person. **Invariants are zero-tolerance targets and do not mean the application implements them or has passed tests for them.** The A–E runtime enforcers and monitoring all await member development; this round's shared contracts validate only representable data constraints and cannot substitute for runtime human review, real sources, or proof of outbound calls.

Source: page 5 of the course project requires each invariant to have a source requirement, an enforcing component, a verification method, and a concrete operational fallback; page 6 requires tests that fail when an invariant is deliberately violated.[1] Higher-level constraint: [root blueprint](../../architecture-blueprint.md); requirement definitions: `docs/req/requirements.yaml`; full mapping: [trace-matrix.md](trace-matrix.md).

## INV-01 | Empty approved set, zero generation calls

- **Source requirements**: INV-01, FR-D-01, COST-01.
- **Rule**: when there is no human-accepted evidence for the current `(snapshot_id, question_id)`, D abstains immediately; model factory initializations, SDK attempts, and HTTP attempts are all zero. This is not a matter of first letting the LLM judge "is there evidence", nor of calling upstream and then claiming it was free because `session.cost=0` appeared.
- **Enforcing components**: D's pre-generation gate is the first guard; B's generation entry point re-checking the permit is the second guard. The call graph must not create upstream/SDK model objects before D's check.
- **Evidence basis**: upstream `aquery` constructs the model at `docs.py:602–607` and may fill in evidence at `:615–623`; the empty-context abstention at `:649–654` happens later than those steps. The team needs to abstain earlier.[3]
- **Verification (planned T-INV-01)**: an empty ledger, all-pending, all-excluded, and accepted belonging to an old snapshot or another question all assert that D is abstained; the counts at the B entry point/factory/SDK/transport spies are all 0. A legitimate accepted control may proceed to controlled generation. The breakage test deliberately removes D's early gate and must be reported as an error by the spy.
- **Runtime monitoring (pending implementation)**: `empty_approved_abstentions`, `model_factory_inits`, `sdk_attempts`, `http_attempts` correlated by request ID; counting only successful responses is not allowed.
- **Fallback on violation**: stop the current generation chain and any queued retries; quarantine the draft as failed / refuse release; the UI shows "no currently approved evidence, human review required"; revoke that request's invocation permit and record a security event. Costs already incurred outbound are not wiped to 0; recovery requires a new review and a new request, and automatic retry is not allowed.

## INV-02 | Immutable source versions and identity

- **Source requirements**: INV-02, FR-A-01, FR-A-02, FR-B-01.
- **Rule**: the document logical ID is separate from the source-bytes SHA256 version; `CorpusSnapshot.snapshot_id` binds the normalized manifest; an evidence ID binds snapshot/doc/version/locator/source text. All contracts are frozen; editing the original, the locator, or the evidence body must not continue to use the old identity. A summary change grants no new identity. Any locator a human can see must lead back to a managed source.
- **Enforcing components**: A for copying/validation and snapshot commit; B for source-text adaptation and locator binding; the shared contracts for hash validation; D for re-checking sources at release. Any change to a source file or its metadata creates a new snapshot and does not modify the old one.
- **Evidence basis**: upstream `Context.id` is generated from the question plus a summary prefix (`types.py:304–316`), and a PDF chunk can only guarantee an existing page range (`readers.py:92–143`); neither can substitute for the team's source identity.[4][9]
- **Verification (planned T-INV-02)**: changing content at the same path yields a new version and snapshot; tampering with evidence fields while keeping the ID must be rejected; two documents with identical summaries remain distinct sources; changing the parser/locator requires rebuilding evidence; the hash of the old original/snapshot is unchanged. Contract tests for canonical-JSON round-trips / invalid IDs are partial evidence and do not prove the file actually exists.
- **Runtime monitoring (pending implementation)**: `source_hash_mismatch`, `evidence_locator_unresolvable`, `identity_reused_for_changed_content`; record snapshot/representation fingerprints, not host absolute paths.
- **Fallback on violation**: quarantine the affected documents/evidence so they do not enter retrieval or release; text must not be filled in from the "most similar passage"; keep the old snapshot read-only; re-validate from the trusted managed original and generate a new snapshot/evidence, requiring a fresh review. If the original is also corrupt, mark it not traceable rather than fabricating a repair.

## INV-03 | Human review authority cannot be granted by a model

- **Source requirements**: INV-03, FR-C-01, FR-C-02.
- **Rule**: `EvidenceRecord` contains no accepted; without a valid `ReviewDecision` the state is pending. Only an explicit action in the current human-machine interaction may append a human decision; model summaries, relevance, upstream IDs, or `actor_kind="human"` in JSON cannot prove their own authenticity. C projects state by `(snapshot, question, evidence)`, and every valid change advances the review revision/digest; exclusions and resets also advance.
- **Enforcing components**: C's command entry point, append-only ledger, and projection; the UI's explicit form actions, where loading/refreshing must not auto-approve; D does not read accepted from the UI cache or from the model.
- **Verification (planned T-INV-03)**: inserting "already human-accepted" markers into candidates, fake human payloads, and automatic comparison/refresh/session recovery must all fail to increase accepted; idempotency tests for retract/reset/duplicate submission; a new valid operation advances revision/digest and the old ledger is not overwritten. The contract's `actor_kind` literal check only rejects wrong values and does not prove a human actually clicked a button.
- **Runtime monitoring (pending implementation)**: `review_command_rejected`, `review_revision_changed`, `review_digest_mismatch`, operation deduplication IDs, and appended-event counts; no real names/accounts are used as public samples.
- **Fallback on violation**: disable generation/release in the current workspace, quarantine the suspicious review event and preserve its original bytes; display the last verifiable state read-only and do not automatically count suspicious records as accepted; require a fresh human review with an appended corrective event — the AI must not "fix" it by editing the old decision.

## INV-04 | Three sets and pre-release freshness

- **Source requirements**: INV-04, FR-D-02, FR-D-03.
- **Rule**: `citation_evidence_ids ⊆ sent_evidence_ids ⊆ approved_evidence_ids`; approved must be derived from the current C ledger, not self-reported by the caller. At release commit, the snapshot, question, review revision/digest, and sources must still match the point where generation started; any change means stale. Even if a retract-then-accept leaves the set identical, the old revision is not reused. Each new `PQASession` is loaded only with the accepted sources sent in that round, and automatic evidence filling is prohibited.
- **Enforcing components**: D's front gate/back gate; B's deterministic serializer and per-round alias mapping; the D→E final single-writer critical section. Raw citation validation comes before any format cleanup; E may persist only state that D has already validated.
- **Evidence basis**: the default serializer selects top-N/cutoff from the contexts (`settings.py:1191–1201`); the source-citation mapping iterates over all of the session's contexts and drops unknown keys (`types.py:480–515`). So "the session has this key" or "it looks good after cleanup" does not equal a legitimate send in this round.[5][4]
- **Verification (planned T-INV-04)**: unknown/excluded/accepted-but-not-sent/old-question/old-snapshot citations are all blocked; trimming evidence shrinks sent correspondingly; updating a document or review while generation waits causes staleness; a change inserted after the final check and before E writes to disk must be stopped by the lock/re-check. A legitimate unchanged-version control may be released. Contract tests for subset violations cover only static sets.
- **Runtime monitoring (pending implementation)**: the freshness/subset/source reasons on `release_blocked`; approved/sent/cited IDs and revision/digest; `stale_generation_count`.
- **Fallback on violation**: unknown/unsent citations are blocked, version/review changes are stale; no "released research conclusion" is produced, and no cleaned-up version is let through afterwards. Keep the draft and diagnostics for read-only audit only, and require a new round from the current snapshot/ledger; do not regenerate automatically or restore the original permit automatically.

## INV-05 | History is never overwritten

- **Source requirements**: INV-05, FR-E-01, FR-E-02, FR-A-02.
- **Rule**: historical reports, snapshots, evidence, and review events keep the sources and decisions of their time; a new answer/revision creates a new record. Superseding is an appended annotation or a derived view and must not rewrite the old report's body/hash. Without a new release permit, viewing history does not constitute a new current release.
- **Enforcing components**: A for immutable snapshots; C for the append-only ledger; E for report saving, loading, and export. A mutable `PQASession` pickle must not be the only source of history.
- **Verification (planned T-INV-05)**: record the R1 hash → new snapshot/new report/re-review/export → R1 bytes/hash unchanged; writing different content under the same report ID is rejected; a simulated interruption leaves no new report that is treated as complete; an old schema cannot be silently migrated in place.
- **Runtime monitoring (pending implementation)**: `historical_write_denied`, `record_hash_mismatch`, `report_commit_failed`, and superseding relationships; historical events contain no private model reasoning.
- **Fallback on violation**: switch the report area to read-only and stop new releases / the "currently valid" export flag; quarantine the conflicting files; recover from a verifiable backup into a separate repair copy and record the incident, without overwriting the old path to cover it up; if no trusted copy exists, mark it corrupt and not traceable.

## INV-06 | Code, data, and tools are unauthorized by default

- **Source requirements**: INV-06, SEC-01, GOV-01, GOV-04.
- **Rule**: a coding agent has no read/write by default and is explicitly allowlisted by role/path/command; frozen source, real credentials, personal directories outside the repository, human rules, pushes, and real model calls are prohibited by default. A runtime model receives only the data allowed for this round and has no shell/file/review/budget capability. A contract being valid does not mean the caller is authorized to read or write.
- **Enforcing components**: OpenCode's actual configuration and tool boundaries (development); B's outbound/path policy and the A/C/E data-directory allowlists (product); CI structural/permission diff plus a human reviewer (backstop). See [permission-model.md](permission-model.md) for details.
- **Verification (planned T-INV-06)**: one legitimate access per role, a set of out-of-scope reads/writes, path traversal/symlink escape, writes to frozen files, reads of personal directories, and rejection of git push/model commands; positive and negative logs must not come only from rule-file text. Real credentials must not be used as test samples; use synthetic sentinels.
- **Runtime monitoring (pending implementation)**: `permission_denied`, role/path class, command category, and policy hash; denial events do not echo sensitive content or full private paths.
- **Fallback on violation**: terminate that tool/session and revoke write/network permits; preserve a minimal event record and stop merging; after a human checks the diff, roll back only the changes confirmed to belong to that agent, and do not `git reset --hard` other people's work away. If secret exposure is suspected, the holder rotates the secret; the AI does not read secrets to investigate.

## INV-07 | Hard budget cap and constraint re-injection

- **Source requirements**: INV-07, COST-01, FR-D-03.
- **Rule**: the proposed limits are ≤12,000 tokens per AI input, compaction starting at ≥9,000, and ≤2,000 output; a smaller model window takes stricter values. The final payload count must include all templates/wrapping, and key identity/standing constraints/authorized IDs are re-verified after re-injection; compaction creates no sources, decisions, or recovery state. Without an approved amount/count/deadline, no outbound call is made; retries are also re-authorized.
- **Enforcing components**: D's context plan/budget; B's factory and the final hop of the SDK/transport adapter. B's retrieval embeddings/summaries are subject to the same input and cost policy and cannot bypass a cap that applies only to answers.
- **Evidence basis**: the default serializer has no hard token cap, and `PQASession.add_tokens` accumulates after the fact; neither can alone serve as a pre-invocation budget gate.[5][4]
- **Verification (planned T-INV-07)**: the boundaries 8,999/9,000/12,000/12,001 plus over-long questions/material; after compaction the constraint hash, authorized IDs, and sent all line up; with budget/deadline exhausted there are no new factory/SDK/HTTP attempts; missing usage is not recorded as 0; unexpected internal retries must be identified by the transport spy. Exact boundaries require the approved tokenizer version; character ratios must not be passed off as measurements.
- **Runtime monitoring (pending implementation)**: input/output cap, tokenizer/version, assembled token count, constraint hash, compaction count, reserved/actual/unknown cost, attempt counts, deadline.
- **Fallback on violation**: reject this request before it goes outbound; prompt to narrow the question/evidence or re-apply for a budget. If the provider has already exceeded output / billing is unknown, stop subsequent retries, mark usage/cost unresolved, and quarantine the draft; do not switch to another model, and do not truncate the extra output and then call everything compliant.

## INV-08 | No import of untrusted pickle indexes

- **Source requirements**: INV-08, FR-A-01, FR-B-01, SEC-01.
- **Rule**: the MVP builds controlled representations only from authorized source text and does not import third-party/shared/downloaded/unknown-origin pickles, compressed indexes, or arbitrary executable objects. JSON must also be validated for schema/version/path/size and must not contain callable parser/FQN configuration that turns data into code; paper and parser licensing are checked separately.
- **Enforcing components**: A's entry-point format allowlist and license check; B does not expose SearchIndex import; E's exports are data only and an export bundle does not automatically become an executable index; CI scans the controlled paths.
- **Evidence basis**: two places can unpickle — the document loader at `agents/search.py:86–93` and the mapping loader at `:242–257`; changing only the document storage to JSON is not enough. The license terms of the main package and the PyMuPDF subpackage differ.[7][10][11]
- **Verification (planned T-INV-08)**: use a harmless sentinel `.pkl`, a fake `.zip`, callable configuration inside JSON, and path traversal to test entry-point rejection; the spy asserts the pickle loader was not called; a legitimate self-authored TXT/PDF control may proceed to parsing. **Do not execute a malicious pickle PoC**, and do not bypass verification by renaming the file extension.
- **Runtime monitoring (pending implementation)**: `index_import_denied`, `unsafe_artifact_rejected`, and format/schema/provenance categories; do not read a rejected object and then record the rejection afterwards.
- **Fallback on violation**: reject and quarantine the import before loading, without automatic extraction/migration/unpickling; require authorized source text to rebuild the representation. If loading has already happened, stop the process and the release immediately and let a human handle the local security incident; "run it once more to see if it is safe" is not allowed.

## Common Requirements for Breakage Tests and Recovery

All T-INV-xx items are **runtime acceptance designs pending development**. Each must have both a legitimate control and at least one expected-failure negative case; "demonstrating success" by breaking the test itself or deleting a guard is invalid. Test results are bound to the commit, fixture, policy, and model/replay identity; recovery must not delete failure history, widen permissions, switch models automatically, or fabricate human approval. When an invariant violation occurs, execute the specific fallback first, then go through the ADR + human review + regression process; "fix bug" does not replace operational action.

## Sources

[1] urn:sha256:6af742d3cbc0973b056a084ba54ff413a5885b1bb4d6a97b0b08b93f64f2ef7e — CS5351-2026-2027-project.pdf (extracted from the local original, 10 pages)
[3] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/docs.py — pinned baseline src/paperqa/docs.py
[4] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/types.py — pinned baseline src/paperqa/types.py
[5] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/settings.py — pinned baseline src/paperqa/settings.py
[7] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/agents/search.py — pinned baseline src/paperqa/agents/search.py
[9] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/readers.py — pinned baseline src/paperqa/readers.py
[10] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/pyproject.toml — pinned baseline pyproject.toml
[11] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/packages/paper-qa-pymupdf/pyproject.toml — pinned baseline PyMuPDF subpackage license declaration
