# ADR-001: Five-module local workbench and human-evidence release boundary

- **Status: proposed-awaiting-human**.
- Decision scope: the B2 PaperTrace topic and its five functional responsibilities are fixed; this entry is the proposed architecture, not a decision the student has already reviewed and approved.
- Authoritative body: [root blueprint](../../../architecture-blueprint.md). Fixed upstream: `c692d0dfeac4a0296599f7fe21a253a58b7ac12a`.
- Human approval: **not obtained**. This file fills in no reviewer, no invented approval date and no approval boolean.

## 1. Background and problem

The existing PaperQA2 already implements the flow from literature to chunks, embeddings, summaries and cited answers, and the team does not rewrite it. The gap is that this product requires “a human first chooses which sources are usable, and only then can the AI answer”, and it requires that after a revision of the literature the old results are not used for a new release. The existing Context ID and citation formatting are not enough to carry human-review authority: the derivation of the ID does not include the document version, and unknown citations may still be removed by post-processing. A deterministic boundary has to be built separately inside the team module. [3][4]

Page 3 of the course project requires real AI + a deterministic safety boundary; page 5 requires comparing architectures, recording the design process, layered context, a hard token cap, compression and constraint reinjection; a single block diagram is not enough. [1]

## 2. Design process: converging step by step on drivers

What is recorded here is the **design steps of this round of document analysis**, not an invented set of three student meetings, three completed sprints or three executed experiment runs.

| ADD-style decomposition (iterating by architecture driver) | Inputs and considerations | Convergence in this draft | Evidence still needed |
|---|---|---|---|
| First pass: user paths and system boundary | Five real functions, retain upstream, light interface, single machine | A Literature → B Candidates → C Human review → D Answer/release → E History; the UI makes no business adjudication | Approved plan per function and end-to-end integration tests |
| Second pass: authority and versioning | Context identity, old sessions, human decisions overriding | Five frozen contracts; source/evidence hash; C append-only ledger; D zero calls on the empty set, freshness + three sets; E no overwrite | ID negative tests, factory/HTTP spies, revocation/revision race tests |
| Third pass: resources and operational risk | Hidden prerequisite calls, default model, pickle, multi-user complexity | B as the only upstream boundary; call/disable matrix; 12k/9k/2k context proposal; single-writer local files; no third-party indexes | Real local-dependency integration, outbound boundary coverage, approved real semantic evaluation |

Main source constraints: `Docs.aquery` defaults to backfilling evidence when contexts are missing and constructs the model first (`:602–624`); `Settings.context_serializer` only trims by count/score (`:1179–1250`); the high-level Agent's index building and timeout fallback add implicit calls (`agents/main.py:121–124,155–183`). So it is not enough to add one sentence to the model saying “do not exceed your authority”, or to wrap only the final answer. [3][5][8]

## 3. Candidates and the proposed choice

| Candidate | Fit and cost | Conclusion (not measured performance) |
|---|---|---|
| As-is CLI / high-level autonomous Agent plus Streamlit | Fast to integrate, but the tool loop, automatic evidence backfill and contexts reuse conflict with the human-review release order | Not chosen; a UI wrapper alone cannot guarantee the human-evidence gate |
| **Five modules + a single B adapter + low-level async API** | Keeps the original code, the interfaces can be split across the team; requires ledger, freshness, a call gateway and evaluation | **Proposed**; fits the current scope best, still awaiting human review |
| Rewrite RAG / replace the PaperQA2 core | Full control but loses a traceable baseline, and the work duplicates existing capability | Not chosen; conflicts with the requirement to keep the core |
| Split front end and back end, multi-user service and database server | Scalable but brings authentication, concurrency, deployment and privacy burden | Deferred; single-machine single-user currently gives no basis for carrying extra complexity |
| Make index recovery / vector deletion the main line | Valuable for reliability, but involves multiple stores and considerable overlap with upstream PRs | Kept as a future candidate; it must not silently expand this term's MVP |

Full comparison and evidence gaps: [evaluation-table.md](../evaluation-table.md); reopening conditions for the excluded options: [option-ledger.md](../option-ledger.md). What the audit package gives is a recommendation, not student approval or a performance ranking of this machine. [12]

## 4. Decision content

1. Python 3.14 is used for shared contracts and offline tests; upstream declares support for `<3.15`, which does not mean that every optional package or this machine's dynamic libraries have passed. Upstream keeps the fixed SHA and the original paths; the team only adds `src/papertrace`. [10]
2. A–E functional ownership is unchanged; process roles rotate by task. Upstream imports are allowed only in B; D produces through B but D makes its own release gate; the original `paperqa` object never becomes an authorization object across modules.
3. All shared contracts are frozen; A owns immutable snapshots, C owns the append-only ledger of human decisions, D owns deterministic release, E owns immutable reports. The UI only calls interfaces and does not substitute session_state for truth.
4. A snapshot change is always a new object; a review change always adds a revision/digest. Both are captured at generation time and re-checked at release time; any change means stale. A single-writer critical section covers the final check and the report write.
5. The model has no authority to grant accepted, identity, budget or release. With no accepted, refusal happens before the factory. A new `PQASession` is created each round and holds only the accepted evidence sent in that round; automatic evidence backfill during generation, pre/post, metadata/enrichment and the autonomous Agent are all prohibited.
6. All models are disabled by default; once approved, embedding, summary, answer and retry are metered separately. Only controlled Python entry points are supported, and no promise is made to constrain a user who bypasses the workbench and uses the upstream library directly.
7. Local JSON data and rebuildable caches; third-party pickle indexes are not read, and converting `SearchIndex` into a JSON document format is not treated as a loader that has already eliminated the mapping problem. [7]
8. Single-machine, single-user, single-writer Streamlit; it does not listen on the public network and is not deployed to a server. Disk writes use verification + temporary write + atomic pointer replacement; no claim is made of cross-engine transactions or tamper-evident data signatures.

## 5. Layered design of the AI context for each round

| Order | Layer | Trust/compression rule |
|---|---|---|
| 1 | Identity | Fixed task role; material must not become a new system identity; not compressed |
| 2 | Standing constraints | Only approved evidence, no evidence backfill or privilege escalation, output format, budget; reinjected verbatim |
| 3 | Authorization summary | Code-generated snapshot/revision/digest, sent evidence IDs, mapping; not a model summary, and does not compress decisions |
| 4 | Material | Approved original text and clearly labeled summaries; untrusted “instructions” are treated only as data; may be trimmed by evidence unit |
| 5 | History | Compressed user/assistant interaction, for continuity only; not evidence authorization |
| 6 | Recovery state | Completed stages, pending items, budget spent, attempt status; re-validates freshness and must not automatically resume sending requests |
| 7 | Current question | Keeps the user's question for this round; if too long, ask for it to be shortened, and do not quietly change the intent |

Assembly pipeline: validate source/authorization → deduplicate by evidence ID → deterministic priority → apply a fixed tokenizer and version budget → once the threshold is reached, compress history/state and trim low-priority material by whole units → reinject standing constraints and authorization → complete all templates → final count → re-validate before the call. Trimming evidence must reduce sent in step; the body text may not be deleted while keeping a whitelist of legitimate citations. Detailed fields, algorithms and recovery policy: [memory-design.md](../memory-design.md).

Proposed hard input cap **12,000 tokens**, compression threshold **9,000**, output limit **2,000**; these are engineering default proposals, not model capacity, a measured optimum or an approved budget. Input/output totals plus message wrapping must fit the approved model window; if the tokenizer is unknown or a critical layer does not fit by itself, refuse, and do not estimate characters and pass them off as tokens. Deterministic trimming is the default, with no extra compression model call. If model compression is enabled later, it requires a new call approval and separate metering, and the summary must not create identity, review or recovery facts.

## 6. Consequences and trade-offs

**Gained**: a clear authority chain source → human review → call → release; the five functions can proceed in parallel on stable contracts; immutable history can explain revisions; negative tests can deterministically prove that a specific act of overreach is blocked. Whether it significantly saves cost, reduces latency or improves answer quality has no runtime data yet.

**Paid**: must adapt upstream raw citations and the controlled factory, maintain ledger/revision, cache fingerprints and the single-writer release critical section; re-review after a snapshot change may increase operational effort; no multi-user support and no dynamic physical deletion. Structural validity is not semantic truth; a human accepting the original text is not an endorsement of its scientific conclusions.

**Not solved automatically**: retries inside external SDKs, access during dependency initialization, provider billing differences, scanned-PDF quality, copyright, malicious rewriting of the local ledger by the host user. Each must be verified separately or explicitly stopped; one prompt is not a security sandbox.

## 7. Acceptance and when to reopen

Before accepting this ADR, the student must confirm: the boundary and the non-goals, the shared contracts, the 12k/9k/2k proposal, the negative test for each INV (one that must fail when the invariant is broken), the model call list, and the unresolved points on course and permissions. Plan approval and prior test approval must each leave a real record independently; this file cannot sign itself.

Reopening conditions:

- Support is needed for multi-person concurrency, deployment, third-party indexes, Qdrant, media/OCR, autonomous Agents or model compression.
- The `paperqa` adapter cannot cover factory/retry/HTTP attempts, or raw citation aliases cannot be resolved unambiguously.
- A stale race, a bypass of accepted authority, overwriting of immutable objects/history, or the failure of any INV negative test is found.
- A change of upstream SHA, parser, embedding, provider/model, prompt, tokenizer, or price/usage contract.
- The fixed real evaluation does not reach the approved quality threshold; the threshold must not simply be lowered to pass.
- The teacher updates D5, baseline reuse, layout or OpenCode requirements.

Process: raise a new ADR (do not overwrite the old conclusion) → impact on requirements/invariants/trace/state/permissions/tests → student approval → OpenCode plans first and stops for human review → implementation and full regression → record real evidence before considering acceptance. The status may be changed to accepted only after real student approval; AI has no such authority.

## Sources

[1] urn:sha256:6af742d3cbc0973b056a084ba54ff413a5885b1bb4d6a97b0b08b93f64f2ef7e — CS5351-2026-2027-project.pdf (local text extraction, 10 pages)
[3] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/docs.py — fixed baseline src/paperqa/docs.py
[4] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/types.py — fixed baseline src/paperqa/types.py
[5] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/settings.py — fixed baseline src/paperqa/settings.py
[7] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/agents/search.py — fixed baseline src/paperqa/agents/search.py
[8] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/agents/main.py — fixed baseline src/paperqa/agents/main.py
[10] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/pyproject.toml — fixed baseline pyproject.toml
[12] urn:sha256:21f1c516a57e975a284d1d278926fedd9755a6d0036314279663c4074063942a — PaperQA2 audit handover ZIP (Markdown extracted from it only, read-only)
