# Module B synthetic retrieval fixtures

These files are **hand-written synthetic data**. They are not real papers, do
not contain any real finding, citation, patient datum, credential, member
identity, or personal absolute path, and they make **no model call** and open
**no network socket**.

## Files

- `source-a.txt` — two short synthetic paragraphs with stable lines, used to
  exercise exact 1-based inclusive line-range locators and excerpt lookback.
- `source-b.txt` — a second synthetic source with a clearly-labelled
  `PENDING-MARKER-B` line, used to prove that unreviewed/excluded source text
  never reaches a generation payload, and for cross-source checks.
- `fake_adapter.py` — offline spies only (a scripted retrieval adapter, a
  recording controlled-source reader, and a counted model factory/session).
  It imports neither `papertrace` nor `paperqa`, loads no model, and returns no
  fixed `"OK"`: every call records its real inputs, order and attempt count.

## Provenance and limits

- Document versions in the tests are the real `sha256` of these bytes; snapshot
  and evidence identities are derived by the shared `papertrace.contracts`
  algorithms — never by handwriting a hash that only *looks* valid.
- The fake adapter proves the module-B **boundary** (what is passed, deduped,
  remapped, retried or refused). It is **not** evidence of real PaperQA2
  wiring, retrieval quality, or model semantic quality. Real upstream wiring is
  covered separately by the offline smoke and must not be inferred from here.
- These fixtures are for `test/offline/test_retrieval.py` only. Do not add real
  paper text, secrets, or machine-specific paths here.
