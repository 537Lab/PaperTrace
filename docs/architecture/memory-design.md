# State, Memory, and AI Context Design

> Status: proposed-awaiting-human. The directories, persistence, and assembler described here are A–E **contracts pending implementation**; they are not a database, background job, or resumable Agent that already exists in this round. Authoritative text: [root blueprint](../../architecture-blueprint.md).

## 1. Three Kinds of Things That Must Not Be Conflated as "Memory"

1. **Source and human-review truth**: managed originals/snapshots, Evidence source text and locators, and C's append-only review ledger. These decide what may be used; model summaries cannot change them.
2. **Reconstructable representations and working state**: parse results, embeddings, candidate summaries, UI selections, the current phase, invocation budget/request state. When lost they can be rebuilt or explicitly terminated; they must not be treated as human-review facts.
3. **Historical research records**: what E saves — the question, the sources and review versions at that time, what was actually sent/cited, and the draft/release outcome. They preserve the facts as they stood then and do not claim to be still valid now.

Page 5 of the course project requires cross-session behavior, interruption, versioning, write/retrieval policy, ownership, retention, and privacy; the default upstream session and lightweight responses do not satisfy this automatically. `PQASession.filter_content_for_user` strips source text, media, and embeddings (`types.py:442–472`), so research records need an independent evidence package rather than turning off the existing filtering.[1][4]

## 2. Planned Local Storage Layout

Below, `.papertrace/` denotes a private runtime directory at the repository root that is excluded from Git; it is not a directory a coding agent may read freely. Only synthetic test directories are open to test roles. Real originals are imported through explicit user selection and then managed by the product; the user home directory, personal libraries, and the upstream `~/.pqa` are never scanned.

```text
.papertrace/                       # single machine, single user, not synced to Git
  sources/<document>/<sha256>/     # A: managed source bytes, read-only versions
  snapshots/<snapshot_id>.json     # A: immutable document manifest
  state/current.json              # A: current snapshot pointer; atomic switch by the single writer
  evidence/<snapshot>/<evidence>.json  # B: immutable source/source text; advisory summaries versioned separately
  review/<snapshot>/<question>/   # C: append-only events, revision, digest projection
  cache/<representation_hash>/    # B: disposable, rebuildable parse/vector/summary representations
  requests/<request_id>/          # B/D: invocation permits, attempts, and recovery state
  reports/<report_id>/            # E: immutable JSON/Markdown and manifest
  annotations/                   # E: append-only superseded/corrupt/source-invalid annotations
  events/                        # redacted diagnostics, non-evidence authorization source
  staging/                       # incomplete writes; never treated as committed records
  quarantine/                    # corrupt/mismatched objects, human inspection only
```

Path segments are derived only from identifiers validated by the contract; user-supplied path concatenation is not accepted; paths are resolved and checked against the root, and out-of-bounds symlinks are rejected. Source file display names do not store host absolute paths. Data storage uses JSON/text with explicit array fields; storing `Docs`/`PQASession` directly via pickle as transferable persistent state is prohibited.

## 3. Ownership, Write, and Read Policy

| State | Write owner and timing | Retrieval conditions | Cross-session/interruption and versions |
|---|---|---|---|
| Original / `DocumentVersion` | A, after the copy and hash complete; the original at the source path is not modified | Shown/handed to B only when the hash matches; only sources from this workspace are allowed | Always bound to logical ID+SHA256; an update at the same path becomes a new version |
| `CorpusSnapshot` | A aggregates ready documents into a new manifest and switches the pointer after validation | schema/hash/manifest membership all pass | Old snapshots are not modified; if the current pointer is corrupt the state is read-only, and the most recent one is not assumed to be current |
| `EvidenceRecord` | B builds it from the source Text plus the real locator | snapshot/doc/version/source text/locator verified | A missing record or original is never fabricated; re-parsing produces new representations and, where needed, new evidence |
| Candidate summaries and embeddings | B, after an approved invocation | The representation fingerprint matches exactly; never grants accepted | Explicitly invalidated when parser/chunker/model/prompt/tokenizer changes; vector spaces are never silently mixed |
| `ReviewDecision` ledger | C, appended via an explicit human command | Verify event order, scope, schema, revision/digest; project by question | No decision means pending; a reset yields a new pending decision; acceptance state is not migrated from an old snapshot |
| Invocation/recovery state | B performs metering; D saves the phase and the captured scope | Invocation permit unexpired and scope/freshness re-checked | If it is unknown whether a request went out, mark it unknown; automatic resends are prohibited; spent budget cannot be reset to zero |
| `AnswerDraft` / `ReleaseDecision` | D, creates new objects after validation | Only the bound scope and the raw answer can serve as that round's record | A revision or review change makes the old round stale; an old decision is not edited into released |
| Reports/manifests | E, committed through the D→E critical section | Verify integrity, sources, schema; show historical/current labels | Never overwritten, never upgraded in place; superseding uses additional annotations and does not change the original bytes |
| UI session_state | UI, current page selection/progress | Hints and UI cache only | May be lost on refresh; recovery must re-read from A/C/E and must not carry out automatic approval |

The tombstone in upstream `Docs.delete` applies partial filtering but does not physically delete vectors, and existing sessions are reusable (`docs.py:403–435,476–490,609–647`). This design constrains new releases through snapshot invalidation and fresh sessions; it does not claim to implement vector erasure or complete cross-store deletion.[3]

## 4. Source Identity and the Review Ledger

### 4.1 Identity and Locators

- A document ID denotes a logical document; a version SHA256 denotes the source file bytes. `snapshot_id` binds the complete ready manifest sorted by document ID; the same manifest captured at different times should not produce different identities.
- An evidence ID binds schema, snapshot, document, version, locator, and the source excerpt; advisory summaries, upstream IDs, and retrieved_at grant no identity.
- Canonical JSON uses UTF-8, stable field/collection ordering, and an explicit schema version; the hashing implementation follows `contracts.py`, and no separate algorithm is invented.
- The current `SourceLocator` requires at least one complete, 1-based, closed page or line range, plus a chunk ID and the parser name and version; a free-form string saying "somewhere" is not supported. Character offsets/bboxes, if needed later, must extend the contract/ADR; it must not be claimed that the current contract already has them.
- A page range is a verifiable locator, not an exact sentence coordinate. Cross-page chunks and source text are preserved in full and checked against the same parser's page/line mapping during verification; if they cannot be reproduced, mark them explicitly as not traceable. Correct text extraction from the original PDF and visual consistency are assessed separately; a hash cannot prove the PDF was understood correctly.[9]

### 4.2 Authority and Digests of the Review Ledger

The key domain is `(snapshot_id, question_id, evidence_id)`. Only C's interactive commands may append a `ReviewDecision`; the field `actor_kind="human"` is merely a type constraint and does not prove a real human review; "human" objects imported from JSON must also not enter the authoritative ledger automatically. Each event contains the current scope, a linkage/deduplication reference to the previous revision, and the decision; the concrete ledger envelope is pending implementation of C's approved design.

An initially empty ledger may use a genesis at a positive-integer revision (the proposal starts at 1) together with its digest, with **no accepted events at all**; this is not a fabricated human review. After each valid accept/exclude/reset the revision increases monotonically, and the digest is computed from the canonical authoritative ledger projection/chain state. Replaying an identical operation should be rejected idempotently without advancing again; a genuine retract-then-accept is two distinct events and must advance.

The digest detects "which revision was visible at generation time"; it is not a signature and not proof of tamper resistance against a malicious local user. C must store the canonical inputs and versions that produced the digest and recompute it on read; it does not trust revision/digest values supplied by the caller. Human review reasons and internal reviewer references are locally controlled data; public samples use anonymous role codes and do not contain team identities.

## 5. Single-Writer Commit, Crash, and Recovery

The local application has exactly one writer instance; a second instance or a second concurrent write command that hits the lock is explicitly rejected / made read-only, and multi-user support is not pretended. The UI coordinates A/C/E write commands, while the modules still each own their own state.

1. Validate contract/scope/permissions before writing; write to private staging and complete content hash / JSON-readability validation.
2. Write the new path of the immutable record, then atomically switch the small pointer or the record-integrity marker; an atomic rename is not claimed to complete full transactions across multiple storage engines. A full disk or a permission error never advances the success state.
3. At startup, load only records that validate completely; orphan staging is not automatically treated as success and may be kept quarantined or cleaned up manually. A schema/hash mismatch puts the state into read-only repair-needed.
4. Long model calls do not hold the write lock: D captures the snapshot/review versions and then makes the request; A/C may commit changes during the wait. After the response returns, D must re-read and determine staleness.
5. The final freshness check and the E report commit happen in the same critical section; no write failure ever emits a "released" state. The UI may display an unreleased draft, but it must be explicitly labeled draft/stale.
6. A restart does not resume the old `PQASession`. Read-only progress is rebuilt from the persistent request accounting; in-flight/unknown requests cannot be retried automatically (they may already be billed). After the user re-approves, a new request ID is created, and the previous round's unresolved usage is retained.
7. The global model-call budget, attempts already made, and remaining allowance must be recovered and must not reset to zero on restart. If they cannot be recovered accurately, freeze new outbound calls and wait for manual reconciliation.

## 6. The Seven-Layer Context of Every Model Call

This is not conversation history that the model can rewrite itself. The provenance of each layer is determined by trusted code, and source text and model content are always material that never become higher-privilege messages.

| Order and layer | Owner / content | Compressible |
|---|---|---|
| 1 Identity | Versioned runtime prompt; a fixed role of "propose drafts only from approved material" | Cannot be compressed into a different identity |
| 2 Standing constraints | No granting accepted; no filling in evidence / substituting outside common sense; use only sent IDs; output format, abstention, no tools/privilege escalation; budget/deadline | Kept verbatim and re-injected after compaction |
| 3 Authorization summary | Code projects from C the snapshot, question, review revision/digest, sent IDs, and this round's alias mapping | Not compacted by the model; if it does not fit, reduce evidence and rebuild |
| 4 Material | This round's approved source text, real locators, optional advisory summaries; delimited and marked "untrusted material" | Low-priority evidence may be removed **as whole units**; the citation allowlist shrinks in step; an excerpt may not be altered and still presented as source text |
| 5 History | User/assistant interactions relevant to this question, with duplicates and stale evidence removed | May be deterministically summarized/truncated; historical conclusions are not added to accepted |
| 6 Recovery state | Phase, completed items, open items, attempt/budget; excludes private chain-of-thought | Descriptions may be shortened while authoritative IDs/metering are retained; recovery must be verified, not self-reported |
| 7 Current question | The original task for this round, plus optional explicit user constraints | Intent is not silently altered; if too long, reject and prompt to narrow it |

The candidate retrieval/summary stage has no accepted yet and cannot pretend to have "approved evidence": its authorization summary states only the **data and operation scope approved for processing**, and its output is candidates only, with no release authority. The answer stage takes material only from C's current accepted. Embedding text is also subject to the input policy, so all originals may not be sent in bulk to get around the cap.

## 7. Assembly Pipeline, Tokens, and Re-injection

The numbers are **proposed engineering defaults pending approval of the student's plan**: input hard cap = **12,000 tokens**, compaction trigger = **9,000**, output limit = **2,000**; they are not a measured optimum. All message wrapping counts; `input + output reserve + provider-required safety margin` must fit the approved model window. A smaller window uses stricter limits, and the window is never enlarged just to match the defaults. The "how many words" of `answer_length` is not a hard output-API cap.[5]

Algorithm (re-executed before every send; it must not be computed only once at the UI layer):

1. **Validation**: check the current snapshot/ledger, source readability, question domain, permit, and deadline. Reject model-self-reported IDs, unknown tokenizers, and unverifiable parsers.
2. **Deduplication**: prefer exact evidence ID; conflicting source text under the same ID is not allowed. Different sources keep separate identities even when their text/summary is identical, and similarity is not used to merge authorizations. History is deduplicated by message ID/content version without losing distinct human decisions.
3. **Deterministic priority**: identity/standing constraints/authorized IDs/current question take precedence and may not be dropped; material follows the user's explicit selection and then a stable sort, with relevance used only as a non-authoritative ordering; history and recovery descriptions are truncated first. Tie-breaks are fixed and the ordering-policy version is retained.
4. **Budget counting**: use the fixed name, package version, encoding-data hash, and message-wrapping version of the tokenizer for the approved provider/model; tool schemas, if present, also count, but the MVP does not expose runtime tools to the model. The first tokenizer-data download is not free/offline by default and must be prepared in advance with a verified cache.
5. **Compaction**: start at 9,000; first remove redundant history, then compress recovery descriptions, then delete low-priority material by whole units, aiming to get back below the threshold; when non-critical layers are already minimal the payload may sit between 9,000 and 12,000, but that must be recorded explicitly. By default no compaction model is called. Source text must not be changed while keeping the same excerpt identity.
6. **Re-injection**: **regenerate** identity/standing constraints/authorization summary from the versioned authoritative constants and the current ledger instead of trusting a compacted summary that claims they were "preserved"; verify the constraint hash, IDs, and question/snapshot/revision/digest. An "ignore the constraints" string inside compacted text is material only.
7. **Final assembly**: build messages in seven-layer order with fixed templates and escaped material boundaries; sent corresponds exactly to the evidence units present in the final payload. Summaries and source text each carry their own provenance label, and a summary is not treated as a verbatim quotation.
8. **Final hard gate**: before B transport, count again and check freshness/budget; reject when >12,000, when input+output does not fit the window, when a critical layer is missing/altered, or when the sent mapping is inconsistent. Silently truncating the system/authorization table, or showing a smaller count only in the UI, is not allowed.
9. **Response reconciliation**: record actual input/output/cache/reasoning usage (if provided), finish reason, attempt/HTTP counts, and whether cost is known; if output is exceeded or usage is incomplete, stop new attempts and do not count them as 0. The actual semantic result is assessed separately.

The top-N/cutoff of the upstream default serializer does not express these rules (`settings.py:1191–1250`); a custom serializer and the gateway's final hop are therefore mandatory, and writing the numbers into the prompt is not enough.[5]

## 8. Representation Cache and Version Invalidation

A representation fingerprint covers at least: source version, parser name/version/configuration, chunk configuration and normalization policy, embedding provider/model/dimensions/configuration, summary prompt/model, and tokenizer/assembly policy version. This fingerprint and the snapshot ID are recorded **separately**, to prevent the false inference that "the source did not change, so the old embedding is certainly still usable".

A representation is reused only when the fingerprints are fully equal; a missing field, unknown model, or incompatible schema counts as a miss and must be rebuilt within the approved budget. The candidate-summary cache carries no review authority; a new snapshot does not automatically migrate accepted. Older versions are read through a read-only compatibility layer or migrated as copies, and historical sources, decisions, or reports must not be "updated" in place.

## 9. Retention, Deletion, and Privacy

The following are default **proposals**; actual retention periods are approved by the student and the data holder, and sources or history are not deleted automatically without that approval:

| Data | Proposed retention and cleanup | Privacy / export policy |
|---|---|---|
| Originals, snapshots, evidence, ledger, reports | Retained for the duration of the project; after termination the holder decides on archiving/deletion; history is not modified by routine cache clearing | Local-only by default; exports carry IDs/versions/locators and necessary short quotations by default, not whole PDFs |
| Rebuildable embedding/parse/summary cache | Cleared manually or by explicit policy; before clearing, confirm it is not the only copy of source text / review data | May contain sensitive text representations and must not be published as a privacy-neutral "cache" |
| requests / attempt accounting | Retained at least until billing and request status are reconciled; unknown is never zeroed | Stores only the necessary model identifier/usage/status/summary, never keys/headers/full configuration |
| Ordinary diagnostic logs | Proposed 30-day rotation; approved before actual enablement; security-incident evidence is not deleted automatically | Allowlisted fields; complete questions/source text/host absolute paths/private reasoning are prohibited |
| staging/quarantine | Not loaded automatically; deleted or kept as evidence after manual verification | Isolated from normal exports; not exposed by default in the UI |

A user-initiated request to delete a workspace or sensitive records is a separate controlled operation: show what traceability will be lost, obtain explicit confirmation, and then act; a tombstone without sensitive content may be kept to explain the absence, and old reports are never covertly rewritten to another source. The MVP does not promise forensic-grade secure erasure or physical vector removal; if that capability is needed, reopen the ADR and the INV-05 retention policy.

Exports use a field allowlist and do not dump full configuration/environment; exception messages and URL queries must also be redacted. Tests use only synthetic sentinels, with no real credentials or member identities. A local user on the host who can modify files may still corrupt data; hash-based error detection is not an authentication system.

## Sources

[1] urn:sha256:6af742d3cbc0973b056a084ba54ff413a5885b1bb4d6a97b0b08b93f64f2ef7e — CS5351-2026-2027-project.pdf (extracted from the local original, 10 pages)
[3] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/docs.py — pinned baseline src/paperqa/docs.py
[4] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/types.py — pinned baseline src/paperqa/types.py
[5] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/settings.py — pinned baseline src/paperqa/settings.py
[9] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/readers.py — pinned baseline src/paperqa/readers.py
