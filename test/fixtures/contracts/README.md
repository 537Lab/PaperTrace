# Hand-written synthetic contract fixtures

Everything here was written by hand during initialization as engineering test data. It does not come from real papers, model replies, human approvals, release runs or student coursework. `reviewer-A` is a non-name code, not a signature.

- The seven `<ModelName>.json` files cover the five main contracts plus `DocumentVersion` and `SourceLocator`.
- Each JSON envelope explicitly carries `synthetic: true`, `provenance` and `contract`; only the value of `data` may be passed to the corresponding Pydantic model. The metadata is not a business field.
- `synthetic-paper-a.txt` is a hand-written one-line non-scientific text. `DocumentVersion.version_sha256` is the real hash of that file's exact UTF-8 bytes, including the trailing LF; the excerpt does not include the trailing newline.
- The document, snapshot, evidence, review and draft IDs share consistent example links. `ReviewDecision.status="accepted"` only shows the data shape and does not mean a real person accepted it. `ReleaseDecision` is explicitly `blocked` with reason `SYNTHETIC_NOT_RUNTIME_VERIFIED`, and all five check flags are false.
- The example `review_digest` is the SHA-256 of the canonical JSON `{"synthetic": true, "reviews": [example review]}`, used only to keep the example references consistent; it is not the C/D authoritative ledger algorithm or proof of authentication.
- Full fields, canonical hashes and the not-yet-implemented authority checks are in `docs/contracts/schema.md`.

Do not copy this directory as real research evidence or semantic evaluation results. Real model evaluation, human approval and runtime release for the business modules are not developed yet.
