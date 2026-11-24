# Runtime Policy Catalog: Normal Paths, Degradation, and Failure

> Status: proposal; all A–E enforcers, runtime monitoring, and integration cases await member development. The event reasons in this document are **design labels** and do not automatically correspond to `ReleaseDecision` enum fields; contract fields/enums follow `contracts.py`.
> Goal: failures are explainable and stoppable, without relying on "ask the model to promise again". Related: [root blueprint](../../architecture-blueprint.md), [invariants](invariants.md), [state](memory-design.md).

## 1. State Rules and Priority

- **Candidate** does not equal accepted; **draft** does not equal released; a legitimate abstention is not a successful research conclusion either.
- Without a human decision the state is pending; only a valid human ledger change in C grants authorization. Generation is bound to the snapshot, question, and review revision/digest.
- When freshness changes, this round is stale, and it must not be released just because the citations are still valid; source/authorization/structure anomalies are blocked; model/storage errors are failed; no evidence is abstained. These are product state semantics: if the current contract expresses stale on the release decision rather than the draft, create the corresponding object instead of forcing in an extra state.
- Multiple failures are handled by the stricter path: permission/source corruption → scope/freshness → budget/deadline → model error → content quality. No failure may widen permissions, switch providers automatically, delete failure accounting, or overwrite history.

## 2. Complete Inventory of Models and Outbound Calls

All models are disabled by default. Installing dependencies or initializing the environment is not outbound-call permission; once approved, B's internal gateway governs the factory/SDK/HTTP together and must not wrap only D's final call. A capability present in the pinned source does not mean the MVP has enabled it.[3][5]

| Path and pinned source location | MVP policy | Authorization and metering point / prohibited bypasses |
|---|---|---|
| citation inference `docs.py:180–206`[3] | **Off**; an explicit citation/docname must be supplied | If the field is missing, report an input error and do not call a model to fill it in |
| structured citation `docs.py:224–261`[3] | **Off**, `use_doc_details=false` | Do not infer from an existing citation that this switch is unnecessary |
| metadata providers `docs.py:266–295`[3] | **Off** | No default Crossref/S2 outbound connection; if enabled later, a separate data/HTTP policy is required |
| PDF parser / media enrichment `docs.py:297–311`, `settings.py:243–250`[3][5] | Only the pinned text parser; multimodal=false | parser/FQN are not arbitrary user-callable configuration; OCR/VLM are not called quietly |
| Ingest embeddings `docs.py:360–386`[3] | Deferred by default; B may enable it explicitly after approval | Defer only postpones, it is not free; approve the file scope, batches, tokens, and amount; meter every SDK/HTTP attempt |
| Retrieval embeddings `docs.py:437–489,515–528`[3] | Controlled by B after approval | Missing vectors are filled in and the query is embedded too; both are deducted from the same budget, so answer usage alone must not be recorded |
| Candidate summary/score `docs.py:538–575`, `core.py:233–269`[3][6] | Controlled by B after approval; advisory only | Per-chunk calls, failed attempts, and summary versions are booked; no summary result is produced without approval |
| summary retry/text fallback `core.py:270–288,383–400`[6] | No additional automatic attempts by default; enabling must be explicit | An upstream internal retry must pass a new gateway reservation; hidden SDK retries are disabled by default, and requests are blocked when they cannot be disabled |
| `aquery` automatic evidence filling `docs.py:615–623`[3] | **Off**, `get_evidence_if_no_contexts=false` | D's empty set returns before B/factory; no sentinel contexts posing as approved |
| pre `docs.py:626–639`; post `:694–711`[3] | **Off**, both None | An empty string is not None and still opens the branch; "run post after review" must not be used to bypass the citation gate |
| answer `docs.py:655–682`[3] | Allowed only with an approval and a non-empty accepted/sent | D's permit → B's fresh session → final-hop counting/budget; the raw output returns to D for validation |
| High-level Agent/fake-agent, search terms/selector, timeout fallback `agents/main.py:121–183,186–216`[8] | **Off** | A "fake" fixed sequence still does not equal a fake model; the high-level CLI/Agent must not be used to bypass the workbench |
| Model factory `docs.py:178–179,602–607`, `settings.py:915–955`[3][5] | Permit first, factory second | With an empty approved set/no permit, entry is never reached; initialization may have SDK side effects, so objects must not be created first and successful answers counted afterwards |
| HTTP SDK retry, startup probes, tokenizer/model downloads | Refused by default; internal implementation pending verification | HTTP attempts and business calls are counted separately; an unknown path must not be called zero; cache downloads need separately prepared authorization |
| History compaction / evaluation LLM judge | No model compaction by default in the MVP; live evaluation approved separately | Deterministic truncation/manual annotation take priority; if a judge is enabled it also counts against the invocation budget, and evaluation must not be treated as free |

`PQASession.add_tokens:414–433` only accumulates after the fact for an existing result; complete cost metering must also cover pre-attempts and cases where usage is not returned. The upstream default serializer has no unified hard token cap; neither can alone serve as an outbound budget gate.[4][5]

### 2.1 Two-Phase Accounting for Controlled Invocations

Before the call, write `request_id`, operation, permitted provider/model, data ID range, prompt/representation/tokenizer/policy versions, input/output cap, deadline, maximum attempts, and the cost reservation. **Every** factory initialization/SDK attempt/HTTP attempt is recorded separately; if one business call sends two HTTP requests, record two, and failures are not counted as zero.

After the call, check the real model identifier, usage/finish reason, actual attempt count, and known/unknown amount; missing usage or an unknown/unresolved price is not filled in as 0. The provider may already have processed a cancellation, so reversing costs already incurred outbound cannot be promised. Freeze new requests while the cost contract is unreconciled; do not switch to a cheaper model on your own, raise limits, or let a reflection loop retry.

## 3. Input, Document, and Candidate Paths

| Policy ID / trigger | Performer | Concrete action and UI state | Recovery / monitoring / planned acceptance |
|---|---|---|---|
| RP-A01 Unauthorized path, out-of-bounds symlink, non-allowlisted format | A | Reject before reading; no copy, no parse | The user re-selects source text they are entitled to; `import_denied`; T-A-01 negative case |
| RP-A02 Corrupt/empty/scanned PDF, unsupported parser | A→B | The single file is failed with the reason shown; successfully processed documents are kept; the batch is incomplete | The user supplies a valid file or explicitly picks a new approach, and OCR is not enabled automatically; `parse_failed`; T-A-01 |
| RP-A03 Different content found at the same path, document metadata removed/changed | A | New SHA/new snapshot; the old snapshot becomes read-only; results being generated become stale afterwards | Retrieve/human-review from the current snapshot; `snapshot_changed`; T-A-02 |
| RP-A04 Duplicate document, or identical text under different logical IDs | A | Duplication/conflict is shown explicitly; sources are not auto-merged by summary | A new snapshot after a human confirms the identities; `duplicate_import`; T-A-01/02 |
| RP-A05 Managed bytes hash does not match the manifest | A/B/D | Quarantine the document and its associated evidence; block release for this round | Rebuild a new version from a trusted source; `source_hash_mismatch`; T-INV-02 |
| RP-B01 No model/data/cost permit | B | Show "model not yet authorized"; do not create a factory/SDK and do not fabricate retrieval results | A new request after separate approval; `invocation_denied`; T-B-02/COST |
| RP-B02 Empty retrieval | B/C | Return zero candidates and an explicit empty result; no automatic web access/library switching | The user adjusts the question or documents; human review is still required; `retrieval_empty`; T-B-02 |
| RP-B03 Timeout, 429, transport error | B | Terminate the current attempt; retry only within the approved attempt count/budget/deadline, otherwise failed | Do not switch models; unknown requests are not resent automatically; `attempt_failed`; T-B-02 |
| RP-B04 Malformed summary JSON / anomalous score / model contains IDs or accept instructions | B/C | Reject non-compliant structures; authoritative fields are not mapped; source text is kept and the summary is explicitly failed/advisory only | A bounded retry after approval, or the user views source text only; `summary_invalid`; T-B-01/02, T-INV-03 |
| RP-B05 Locator missing or unable to resolve back to source text | B | That item cannot enter the approvable candidates; no "similar sentence" substitution | Rebuild with the pinned parser / manual inspection; `locator_unresolvable`; T-INV-02 |
| RP-B06 Cached representation fingerprint changed / unknown version | B | Cache miss; mixing embedding spaces or old summary state is prohibited | Rebuild under a permit, or block; `representation_invalidated`; T-B-01 |
| RP-B07 Third-party pickle/index package | A/B | Reject/quarantine before the loader, and do not extract and unpickle before checking | Supply authorized source text; `index_import_denied`; T-INV-08 |

## 4. Human Review, Context, Generation, and Release Paths

| Policy ID / trigger | Performer | Concrete action and state | Recovery / monitoring / planned acceptance |
|---|---|---|---|
| RP-C01 No decision, old-snapshot/old-question decision | C/D | Project pending; does not enter current accepted | The user explicitly reviews the current source text; `review_pending`; T-C-01, T-INV-01 |
| RP-C02 Fake human payload / refresh replay / model auto-accept | C | Reject the command; do not append accepted; record deduplication/rejection | Resubmit through real interaction; `review_command_rejected`; T-INV-03 |
| RP-C03 Normal exclusion/reset/retract-then-accept | C | Append an event and advance revision/digest; do not overwrite the old decision | All old generation results must become stale; `review_revision_changed`; T-C-01 |
| RP-D01 No current accepted | D | The `AnswerDraft` is abstained; 0 factory/SDK/HTTP; B is not called to generate | A new request after reviewing the evidence; `empty_approved_abstention`; T-INV-01 |
| RP-D02 accepted non-empty but sent empty after trimming | D | Abstain as well, with no answer call; do not fabricate one piece of evidence to make it non-empty | Narrow the context or the question; `empty_sent_abstention`; T-INV-07 |
| RP-D03 ≥9k trigger, >12k / does not fit the model window | D/B | Deterministic compaction / remove material by whole units, re-inject, final count; reject if still unsuitable | The user narrows the question/evidence; `context_over_budget`; T-INV-07 |
| RP-D04 Constraint missing / wrong constraint hash / inconsistent authorization table | D/B | Block before outbound; do not let the model restore the "constraints" | Reassemble from the authoritative template/ledger, and stop if it still fails; `constraint_check_failed`; T-INV-07 |
| RP-D05 Cost/count exhausted, deadline reached | B | 0 new attempts (including retries/fallback); requests already outbound are cancelled on a best-effort basis but stay booked | New authorization is needed and a restart does not reset to zero; `budget_denied`; T-INV-07/COST |
| RP-D06 Provider empty text/truncation/unknown usage/protocol error | B/D | failed, or a restricted unreleased draft; HTTP 200 is not treated as success | Manual reconciliation / a separately approved new request; `answer_invalid`/`usage_unresolved`; T-D-03 |
| RP-D07 Raw output cites unknown, excluded, unsent / cross-question evidence | D | blocked; keep the original problem point; do not publish after deleting the bad key | A new round or manual handling; automatic self-certifying retries are prohibited; `citation_scope_violation`; T-INV-04 |
| RP-D08 Assertions without citations | D | Not released as a successful research conclusion; explicitly rejected or left pending | A new round after adding human-reviewed sources; `citation_missing`; T-D-02 |
| RP-D09 snapshot/review revision/digest changes during generation | D | stale, not released; blocked even if the final accepted set is identical | A new round from a new snapshot/new review; `release_stale`; T-INV-04 |
| RP-D10 Someone writes state after the release check but before E commits | D→E | Re-check in the single-writer critical section and block as stale; leave no half-record that could pass as released | A new request once state is stable; `publish_conflict`; T-INV-04 |
| RP-D11 A document contains "system/approve/escalate/increase budget" text | B/D | Treated as untrusted material only; does not change identity/ledger/permissions; if the output is contaminated, block per the gates | Manual exclusion or a new round; `untrusted_instruction_seen` (diagnostic only, not perfect detection); T-INV-03/06/07 |
| RP-D12 Citation structure valid but semantic support uncertain / evidence conflicting | D/UI | State explicitly that "structure/source verifiable does not equal scientifically correct"; hand over to human inspection / keep the uncertainty | Human reading or a fixed semantic evaluation; do not claim the code finds every conflict; T-C-02/real evaluation |

## 5. History, Export, Recovery, and Development-Governance Paths

| Policy ID / trigger | Performer | Concrete action | Recovery / monitoring / planned acceptance |
|---|---|---|---|
| RP-E01 Attempt to overwrite a report/history under the same ID | E | Reject and keep the old bytes; a new version uses a new report ID | A human checks the conflict; `historical_write_denied`; T-INV-05 |
| RP-E02 Unknown schema / hash mismatch / corrupt ledger | A/C/E | Workspace read-only, repair-needed; do not automatically pick the "most recent file" as truth | From a trusted backup to an isolated copy; `state_integrity_failed`; T-E-01/INV-02/05 |
| RP-E03 Disk full / no write permission / interrupted half-write | The module that writes state | Do not advance the success pointer; staging is not treated as a complete result; do not claim released to the UI | Manual recovery after resolving the storage problem; `state_commit_failed`; T-E-01 |
| RP-E04 Export contains secrets/absolute paths/unauthorized full text | E | Allowlist field check, reject dangerous exports; do not package a configuration dump | A new export after the user confirms the distributable scope; `export_policy_denied`; T-E-02/SEC |
| RP-E05 Viewing an old snapshot's report | E/UI | Read-only history showing the original snapshot/review version; superseded annotations may be appended | A current new release must go through D again; `history_viewed`; T-INV-05 |
| RP-E06 Interruption/restart with the request in-flight or unknown | B/D/UI | No automatic continuation; re-read A/C/E and re-check freshness/budget | A new request after a human checks the invocation status/new permit; `recovery_paused`; T-D-03 |
| RP-G01 Second writer/second instance | UI/module lock | Reject the write or go read-only; no silent last-writer-wins | Exit the extra instance and confirm lock ownership; `writer_lock_denied`; T-INV-05 |
| RP-G02 A coding agent goes out of scope / tries to modify human-only files, frozen source, or push | Tool boundary/CI | Reject immediately and stop that round; preserve a minimal diff/denial log | Human review; other people's work is not force-cleaned; `permission_denied`; T-INV-06 |
| RP-G03 prompt/model changed but real semantic evaluation is missing/unapproved | CI/human review | gate blocked; no skip-as-pass; a mock's fixed answer is not a substitute | Actually run it after specifying budget/model/data and keep the receipt; GOV-02 |
| RP-G04 Plan/tests not pre-approved, missing AI logs or security ADR | CI/human review | Do not implement or do not merge; a PR must not self-fill approved to prove itself | Real student review, update the collaboration artifacts; GOV-01/03/04 |

## 6. General Stop and Recovery Discipline

- An error must not automatically change human review, change requirement thresholds, change models, or widen the data scope; an abstention is not passed to an LLM to "polish" it into an affirmative conclusion.
- Every event carries request/snapshot/review/policy identifiers, and key metering keeps known/unknown separate. Ordinary logs do not store full source text/questions/credentials/host paths or private reasoning.
- The specific fallback is executed first; the student then decides whether to add evidence, re-review, authorize a new request, or reopen an ADR. An agent does not approve its own recovery.
- The scope this policy guarantees is only the workbench's controlled entry points; a user bypassing it to call the upstream library directly is not covered. No unverifiable promise is made about requests the provider has already executed, malicious tampering by a host user, or scientific truth.

## Sources

[3] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/docs.py — pinned baseline src/paperqa/docs.py
[4] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/types.py — pinned baseline src/paperqa/types.py
[5] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/settings.py — pinned baseline src/paperqa/settings.py
[6] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/core.py — pinned baseline src/paperqa/core.py
[8] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/agents/main.py — pinned baseline src/paperqa/agents/main.py
