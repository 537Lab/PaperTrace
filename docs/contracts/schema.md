# PaperTrace shared data contract v1

Status: **the shared interfaces and offline structural validation are implemented; the A–E business logic, the real human-review ledger and the real release decision are not implemented.**

Implementation: `src/papertrace/contracts.py`. Architecture follows ADR-001; requirement QA-01. INV-01 to INV-05 have only the local data-structure support described below, so this cannot be used to claim that the end-to-end invariants are satisfied. The initialization was performed by Hermes; it is not a student OpenCode development contribution or a course D5 Transcript.

## 1. General conventions

- All seven models are Pydantic v2 with `frozen=True`, `extra="forbid"` and `revalidate_instances="always"`. Collections are tuples in memory and arrays in JSON; no mutable dict/list fields are stored.
- Every object, including the nested `DocumentVersion` and `SourceLocator`, must explicitly provide `schema_version: 1`. A missing value, another version, the string `"1"` and the boolean `true` are all rejected, with no silent migration.
- All times must carry a time zone and are normalized to UTC on validation; JSON serialization uses UTC. Time fields have no current-time default, so callers must pass them explicitly. Naive times are rejected.
- `NonBlank` means a string containing at least one non-whitespace character; there is no automatic trimming, no case conversion and no Unicode normalization.
- A SHA-256 must be **64 lowercase hexadecimal characters**, matching `^[0-9a-f]{64}$`. Uppercase, surrounding whitespace, non-hexadecimal characters and automatic repair are not accepted.
- `PositiveInt` is a strict integer with `>= 1`; booleans and numeric strings are not accepted.
- `ReviewRevision` is a strict integer with `>= 0`; 0 means no human review event has occurred, so only an abstention/failure or a block can be recorded, and neither an approved draft nor a release can be formed. The revision of a real ReviewDecision still starts at 1.
- Frozen and valid JSON do not equal truth, authorization or a cryptographic signature. Pydantic bypass APIs such as `model_construct()` and `model_copy(update=...)` should not be applied to untrusted input; call `model_validate()` / `model_validate_json()` to re-validate. A Python object itself must not be treated as trusted approval.

### Identifier rules

| Type / field | Exact rule | Meaning |
|---|---|---|
| `document_id` | `^doc-[a-z0-9][a-z0-9_-]{0,63}$` | logical document ID assigned by the caller, not a content hash |
| `snapshot_id` | `^snap-[0-9a-f]{64}$` | content-derived identity of the canonical JSON below |
| `evidence_id` | `^ev-[0-9a-f]{64}$` | identity derived from the source text and source locator below |
| `question_id` | `^q-[a-z0-9][a-z0-9_-]{0,63}$` | question ID assigned by the caller |
| `answer_id` | `^ans-[a-z0-9][a-z0-9_-]{0,63}$` | draft/run ID assigned by the caller, not a hash of the answer content |
| `reviewer_ref` | `^reviewer-[A-Z][A-Z0-9_-]{0,31}$` | a non-name code such as `reviewer-A`; not a signature or proof of authentication |
| items in `reason_codes` | `^[A-Z][A-Z0-9_]{0,63}$` | stable machine reason code; arbitrary natural language must not be used instead |
| `chunk_id` | `NonBlank` | opaque identifier of the parsed chunk; a page or line range is still required for location |

All identifiers are validated verbatim; upstream `Context.id`, summaries, document titles or citation display names are never turned into IDs that can grant authorization.

## 2. Exact fields

Every model below additionally contains a required `schema_version: Literal[1]`, which the tables do not list again.

### `DocumentVersion` (A → B/C/D/E)

| Field | Type / requiredness | Constraint |
|---|---|---|
| `document_id` | `DocumentId`, required | logical identity |
| `version_sha256` | `Sha256`, required | should be computed by A over the raw file bytes; the contract validates only the format |
| `title` | `NonBlank`, required | display title, Unicode allowed |
| `source_name` | `NonBlank`, required | bare file name, not a local path or URI |
| `status` | `Literal["ready"]`, required | only a ready version may enter the shared snapshot |

`source_name` rejects `/`, `\`, `:`, `.`, `..` and the control characters U+0000–U+001F / U+007F. The field is not a file-access authorization, nor a cross-platform filesystem sanitizer. A's importing and failed states belong to future A-internal business logic and do not fake ready in the shared ready-document model.

A content change under the same `document_id` should produce a new `version_sha256` and a new snapshot. Different logical documents that share the same byte hash are not merged automatically by this contract; deduplication and file reading are not implemented yet.

### `CorpusSnapshot` (A → all modules)

| Field | Type / requiredness | Constraint |
|---|---|---|
| `documents` | `tuple[DocumentVersion, ...]`, required | ready documents only; logical IDs must not repeat; stored in ascending ID order |
| `created_at` | UTC aware datetime, required | records the capture time and does not participate in the identity hash |
| `snapshot_id` | `SnapshotId`, may be omitted to be generated | if passed explicitly it must exactly match the canonical hash |

A snapshot cannot contain two versions of the same logical ID, nor the same version twice. An empty document tuple is allowed to represent an empty ready corpus; this neither permits a scientific answer to be generated nor proves that A has implemented append-only historical storage.

### `SourceLocator` (embedded in evidence)

| Field | Type / default | Constraint |
|---|---|---|
| `page_start` / `page_end` | `PositiveInt | None`, default `None` | 1-based, inclusive page range |
| `line_start` / `line_end` | `PositiveInt | None`, default `None` | 1-based, inclusive line range |
| `chunk_id` | `NonBlank`, required | identifier of the original parsed chunk |
| `parser_name` | `NonBlank`, required | name of the parser used for the location |
| `parser_version` | `NonBlank`, required | version of the parser used for the location |

At least one complete range (pages or lines) is required; a start requires an end and vice versa; the end must not be smaller than the start. Pages and lines may both be present. A locator with only `chunk_id` or free text and no range is invalid. Whether a locator matches the real source file is checked by later B/D adapters; no file is read inside the model.

### `EvidenceRecord` (B → C/D/E)

| Field | Type / default | Constraint |
|---|---|---|
| `snapshot_id` | `SnapshotId`, required | the declared source snapshot |
| `document_id` | `DocumentId`, required | the declared logical document |
| `version_sha256` | `Sha256`, required | the declared content version of the source |
| `locator` | `SourceLocator`, required | structured source locator |
| `excerpt` | `NonBlank`, required | verbatim source excerpt, not a model summary |
| `retrieved_at` | UTC aware datetime, required | does not participate in evidence identity |
| `advisory_summary` | `str | None`, default `None` | explicitly advisory only; grants no review authority |
| `upstream_context_id` | `str | None`, default `None` | opaque upstream debugging correlation, not used as team evidence identity |
| `evidence_id` | `EvidenceId`, may be omitted to be generated | if passed explicitly, the canonical hash is validated |

**There is no `accepted` or `status` field. Without a corresponding valid review decision the record is treated as pending; accepted cannot be inferred from a model summary, an upstream score, a `Context.id` or the evidence object itself.** `excerpt` is not automatically whitespace-stripped or rewritten, and any change of source characters changes the evidence identity.

### `ReviewDecision` (C → D/E)

| Field | Type / requiredness | Constraint |
|---|---|---|
| `evidence_id` | `EvidenceId`, required | the evidence under review |
| `snapshot_id` | `SnapshotId`, required | the snapshot this decision applies to |
| `question_id` | `QuestionId`, required | the question this decision applies to |
| `status` | `pending | accepted | excluded`, required | the only shared model allowed to express review status |
| `actor_kind` | `Literal["human"]`, required | a model/agent cannot declare the decider type |
| `reviewer_ref` | `ReviewerRef`, required | non-name code; no signature is generated |
| `revision` | `PositiveInt`, required | declared revision number of the review ledger |
| `reason` | `NonBlank`, required | a reason must be recorded for pending events as well |
| `decided_at` | UTC aware datetime, required | event time of the decision / reset to pending |

Review authority should come only from `ReviewDecision` records produced by real human actions in C and stored in a trusted ledger. `actor_kind="human"` is itself only a structural restriction and does not authenticate the operator; C must still implement the human/machine operation boundary, the append-only ledger, revision advancement and digest computation. **This round implements none of that business logic, and there is certainly no real approval.**

### `AnswerDraft` (D → E)

| Field | Type / default | Constraint |
|---|---|---|
| `answer_id` | `AnswerId`, required | draft/generation run identity |
| `snapshot_id` | `SnapshotId`, required | the snapshot this generation is bound to |
| `question_id` | `QuestionId`, required | the question this generation is bound to |
| `review_revision` | `ReviewRevision`, required | the review revision this generation is bound to; 0 is used only for abstained/failed |
| `review_digest` | `Sha256`, required | the ledger digest this generation is bound to; this model validates the format only |
| `approved_evidence_ids` | `tuple[EvidenceId, ...]`, required | declared approved set, no duplicates |
| `sent_evidence_ids` | `tuple[EvidenceId, ...]`, required | declared set actually sent this round, no duplicates |
| `citation_evidence_ids` | `tuple[EvidenceId, ...]`, required | declared set cited in the body, no duplicates |
| `status` | `draft | abstained | failed`, required | direct `released` is not allowed |
| `body` | `str`, required | status constraints in the table below |
| `refusal_reason` | `str | None`, default `None` | abstention/failure reason |
| `generated_at` | UTC aware datetime, required | explicit generation/failure event time |

The three ID tuples keep their input order but must each be unique, and `citation_evidence_ids ⊆ sent_evidence_ids ⊆ approved_evidence_ids` always holds.

| Status | approved / sent | body | citation | refusal_reason |
|---|---|---|---|---|
| `draft` | both non-empty | must contain non-whitespace characters | may be empty, but must be within sent | must be `None` |
| `abstained` / `failed` | may be empty; still subject to the subset constraint | must be exactly `""` | must be empty | must contain non-whitespace characters |

With an empty approved set, only `abstained` / `failed` with an empty body and empty citations can be produced. On failure the previously sent approved IDs may be retained for traceability, but no scientific answer may leak. Whether a generation call was actually avoided is a future D runtime responsibility; only data constraints exist here.

**These sets are declarations, not verification of an external ledger's truth.** This round does not check whether they really are the current accepted set, does not verify the real outbound content, does not parse the citation markers in `body`, and does not compute an authoritative `review_digest`. A valid AnswerDraft does not on its own become eligible for release.

### `ReleaseDecision` (D → E)

| Field | Type / requiredness | Constraint |
|---|---|---|
| `answer_id` / `snapshot_id` / `question_id` | corresponding ID, required | declared bound objects |
| `review_revision` / `review_digest` | `ReviewRevision` / `Sha256`, required | declared bound review version; 0 is used only for blocked |
| `status` | `released | blocked`, required | recorded form of the release decision |
| `reason_codes` | `tuple[ReasonCode, ...]`, required | machine codes only; no implicit default |
| `snapshot_check_passed` | strict bool, required | declares the snapshot/document version check result |
| `review_check_passed` | strict bool, required | declares the review revision, digest and scope check result |
| `evidence_check_passed` | strict bool, required | declares the actually-sent vs approved range check result |
| `citation_check_passed` | strict bool, required | declares the citation mapping and source check result |
| `answer_check_passed` | strict bool, required | declares the draft structure/state check result |
| `decided_at` | UTC aware datetime, required | decision time |

`released` requires all five checks to be `True` and `reason_codes` to be empty. `blocked` requires at least one reason code; structural checks may all be true while another runtime policy blocks the release. Boolean fields do not accept `1` or `"true"`.

This is a **result-recording model, not a release engine**. A caller constructing five trues still cannot prove that checks were run; D must re-check from trusted runtime state and then construct the decision. It does not replace the real release decision, race protection, semantic quality evaluation or human approval.

## 3. Canonical hashing: must be identical across modules

Define `canonical_json(x)`:

```python
json.dumps(
    x,
    ensure_ascii=False,
    sort_keys=True,
    separators=(",", ":"),
    allow_nan=False,
).encode("utf-8")
```

Then use `hashlib.sha256(...).hexdigest()`. There is no trailing newline and no whitespace separator; there is no whitespace stripping, no case conversion, and no Unicode normalization such as NFC/NFKC. This is this project's canonical JSON for the limited fields described below, and it does not claim to implement full RFC 8785.

### Snapshot identity

```text
snapshot_id = "snap-" + SHA256(canonical_json({
  "schema_version": 1,
  "documents": [complete DocumentVersion JSON, in ascending document_id order]
}))
```

Each document item contains exactly `schema_version`, `document_id`, `version_sha256`, `title`, `source_name`, `status`. `created_at` and `snapshot_id` itself do not participate in the hash. A change of title/display file name changes the snapshot identity even if the content SHA is unchanged; reordering documents and a different capture time do not change the identity. An omitted ID is generated automatically; an inconsistent explicit ID is rejected.

### Evidence identity

```text
evidence_id = "ev-" + SHA256(canonical_json({
  "schema_version": 1,
  "snapshot_id": snapshot_id,
  "document_id": document_id,
  "version_sha256": version_sha256,
  "locator": complete SourceLocator JSON,
  "excerpt": verbatim excerpt
}))
```

The complete locator contains `schema_version`, `page_start`, `page_end`, `line_start`, `line_end`, `chunk_id`, `parser_name`, `parser_version`. Range fields that were not provided still participate in the hash as JSON `null` after validation to `None`; they are not omitted. The upstream ID, the summary and `retrieved_at` **do not participate in the identity**. A change of source snapshot, document, content version, locator/parser or excerpt must invalidate the original evidence ID.

The authoritative ledger assembly, ordering, revision and verification protocol for `review_digest` are still to be determined and jointly tested by C/D during the formal implementation; this model constrains only the 64-hex value and the explicit binding, and does not implement the ledger ahead of time. The digests in the synthetic fixtures are only hashes of explicitly synthetic structures, not runtime endorsement or signatures.

## 4. Boundary between structural validation and business authority

| What this round's models already do | Still to be implemented by student modules; cannot be self-proven by the contract |
|---|---|
| Validation of versions, IDs, times, locators, duplicates, states and subset shapes | A: hashing of real file bytes, source of the ready state, persisted snapshots, and history that is never overwritten |
| Deriving and verifying the snapshot ID from canonical document metadata | B/D: the document really belongs to the snapshot, the locator and excerpt match the source file, the parser is reproducible |
| Deriving and verifying the evidence ID from source text and locator | C: authentication of real human actions, appending of review events, monotonic revision advancement, trusted digest |
| Forbidding evidence from carrying accepted; the review actor must be human | D: read the approved set from the trusted ledger and only ever send that set |
| An empty approved set can only be an empty-body abstention/failure | D: zero model calls with zero approved evidence, blocking as soon as the corpus/review changes mid-generation |
| Citation declarations can only come from the declared sent/approved scope | D: parsing of the actual body citations, version mapping, external ledger and freshness verification |
| A released declaration requires all five trues and no reason codes | D: the real release decision and semantic thresholds; E: display/export and history only from trusted decisions |

The cross-object and external-state verification above is **not implemented in this round**. A single valid object, or consistent references in a synthetic scenario, must not be taken as a passing runtime authorization test.

## 5. Examples, Schema and running

- `test/fixtures/contracts/`: seven hand-written wrappers explicitly marked `synthetic: true`, plus one self-written TXT. Only the wrapper's `data` is contract input; the metadata cannot be passed into the closed models. There are no real papers, paid model responses, real-person signatures or approvals.
- The seven `*.schema.json` files in this directory are generated by the real `model_json_schema()`, and tests confirm there is no drift. `uniqueItems` is explicitly exposed. Canonical hash equality, locator range relationships, status conditions and cross-field subsets rely on Pydantic validators, so ordinary JSON Schema validation alone cannot be claimed to have checked everything.
- The tests cover JSON round-trips and Unicode for all seven classes; the five main classes each have negative tests; they include wrong version, extra fields, duplicate identities, hash mismatch, invalid SHA, missing locator, reversed range, forged actor, empty approved set, citations outside the declared scope, unauthorized state, inappropriate release, naive times and re-validation of constructed instances.
- The tests import only the team's shared interfaces; they do not import PaperQA, access the network, read credentials, or call models.

Standalone verification command (explicitly bypassing the upstream pytest configuration):

```sh
PYTHONPATH=src .venv/bin/python -m pytest -c /dev/null --disable-socket test/offline/test_contracts.py
```

The real per-item RED→GREEN record and the later regression/static check output are stored in `artifacts/verification/contracts-tdd.txt`. That file is engineering execution evidence, not a prior human test approval record or a student OpenCode Transcript.
