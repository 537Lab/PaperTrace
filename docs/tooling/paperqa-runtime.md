# PaperQA2 offline runtime smoke

## Purpose and boundaries

This smoke calls the real `Docs.aadd` → `Docs.aget_evidence` → `Docs.aquery` path on the pinned upstream PaperQA2 checkout, verifying the dependency/API wiring and the boundary at which evidence enters the final prompt. The upstream baseline is `c692d0dfeac4a0296599f7fe21a253a58b7ac12a`; the script imports the source directly through `src/` and `packages/paper-qa-pypdf/src/` without an editable install, avoiding `setuptools_scm` rewriting `src/paperqa/version.py`.

This is not a formal business feature or a real model test: there is only one hand-written synthetic `.txt` evidence file; embedding, summary and answer are all local deterministic test doubles, and the answer is explicitly marked `SIMULATED_OFFLINE_ANSWER:`. It uses no private keys, real papers, real LLM/provider or paid calls, and does not verify answer quality, actual PDF parsing, Docling/OCR, retrieval services or the A–E business adapters.

## Runtime environment and locked dependencies

The environment at test time was Python `3.14.6` and uv `0.12.9` (`aarch64-apple-darwin`). `requirements-runtime.lock` is resolved from `requirements-runtime.in` and `.local/unblock/runtime/baseline-uv-constraints.txt`, and currently pins **83 exact hash-pinned packages**. The lock governs the full transitive dependency versions; the measured versions of the direct dependencies are as follows:

| Purpose | Distribution version |
|---|---|
| PaperQA API/runtime | `fhaviary==0.34.0`, `fhlmi==1.10.0`, `litellm==1.84.1`, `numpy==2.4.3`, `pydantic==2.12.5`, `pydantic-settings==2.16.1`, `pypdf==6.9.1` |
| Other runtime direct dependencies | `anyio==4.12.1`, `html2text==2025.4.15`, `httpx==0.28.1`, `httpx-aiohttp==0.1.12`, `pybtex==0.25.1`, `rich==14.3.3`, `setuptools==82.0.1`, `tantivy==0.25.1`, `tenacity==9.1.4`, `tiktoken==0.12.0` |
| pytest / lightweight collection | `pytest==9.0.2`, `pytest-asyncio==1.3.0`, `pytest-recording==0.13.4`, `pytest-socket==0.8.1`, `pytest-subtests==0.15.0`, `pytest-timeout==2.4.0`, `typeguard==4.5.1` |

No broad set of upstream dev/test extras, ML/Docling packages or model weights was installed. `pytest-socket` is required: `papertrace.pytest.ini` uses `--disable-socket`, and the upstream offline tests import `pytest_socket`. That config file name is not one pytest discovers by default, so `-c papertrace.pytest.ini` must be passed explicitly when running the smoke.

## Reproducing from the repository root

```bash
cd <the PaperTrace directory you cloned>
RUNTIME=.local/unblock/runtime
mkdir -p "$RUNTIME/home" "$RUNTIME/tmp" "$RUNTIME/cache" artifacts/verification
uv venv "$RUNTIME/.venv" --python 3.14
# Use the committed, hash-pinned lock; routine installs neither recompute it nor rely on local helper constraints.
uv pip sync --python "$RUNTIME/.venv/bin/python" requirements-runtime.lock

PYTHONDONTWRITEBYTECODE=1 "$RUNTIME/.venv/bin/python" -m pytest \
  -c papertrace.pytest.ini \
  test/integration/test_paperqa_smoke.py -q

/usr/bin/env -i \
  PATH="$PWD/$RUNTIME/.venv/bin:/usr/bin:/bin" \
  HOME="$PWD/$RUNTIME/home" \
  TMPDIR="$PWD/$RUNTIME/tmp" \
  XDG_CACHE_HOME="$PWD/$RUNTIME/cache" \
  PYTHONNOUSERSITE=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  "$PWD/$RUNTIME/.venv/bin/python" \
  scripts/paperqa_smoke.py --json \
  --report artifacts/verification/unblock-paperqa-smoke.json \
  | tee artifacts/verification/unblock-paperqa-smoke.txt
```

The test subprocess uses a whitelisted environment and does not inherit the caller's dotenv, user site-packages or API keys. The script puts upstream `src/` and `packages/paper-qa-pypdf/src/` on `sys.path` itself; this smoke does not need `uv pip install --no-deps . ./packages/paper-qa-pypdf`. If another runner needs explicit module paths, `PYTHONPATH=src:packages/paper-qa-pypdf/src` can be used; do not do an editable install for this smoke.

## Offline guarantees

- `LITELLM_LOCAL_MODEL_COST_MAP=True` is set before importing `lmi` / PaperQA, forcing LiteLLM to use the bundled local cost map and avoiding its default import-time remote cost-map request. The JSON records `source=local`, `url=null`, `is_env_forced=true`, `fallback_reason=null`, and asserts that no remote-failure fallback occurred.
- During execution `socket.socket.connect` and `connect_ex` are patched: any connection attempt fails immediately and is counted. The actual report is `network_connect_attempts=0`. The pytest runner also disables networking through `--disable-socket` in `papertrace.pytest.ini` and through `pytest-socket`.
- Both LLM and embedding calls are intercepted by local fake implementations; there are no provider API calls. The real code path covers only PaperQA's local document, evidence and prompt assembly.

## Verified behavior

In the positive scenario three synthetic sources — approved/excluded/pending — are added to the same `Docs`, real retrieval returns three candidate contexts, and the real aquery is then called with a new `PQASession` containing only the approved context. The actual final user prompt (full text saved in the JSON) contains the approved fact; `excluded_marker_in_final_prompt=false` and `pending_marker_in_final_prompt=false`. Model method call counts follow the actual JSON output of this run; the answer is simulated output and does not represent model quality.

The empty-approved scenario keeps the same three documents in the Docs but passes a new session with zero contexts and returns an abstention; embedding, summary, answer and lazy retrieval calls are all `0`. `get_evidence_if_no_contexts=false`, so it does not fall back to implicit retrieval; the pre, post and answer-iteration prompts are all set to `None`. The session ID returned by the empty scenario differs from the positive result and has no contexts (`session_is_fresh=true`), so the earlier positive session's evidence is not reused.

## Actual results and evidence files

- `artifacts/verification/unblock-paperqa-pytest.txt`: the integration smoke using the ini specified above; result **1 passed**.
- `artifacts/verification/unblock-paperqa-smoke.json`: the machine-readable report actually emitted by the script, `status=PASS`, containing runtime versions, the full final prompt, positive/negative call counts, the LiteLLM cost-map source and the socket connection count.
- `artifacts/verification/unblock-paperqa-smoke.txt`: the JSON stdout of the same script run.
- `artifacts/verification/unblock-paperqa-collection.txt`: the lightweight `--collect-only` output for `test/` using the same runtime and ini: **historical snapshot of 207 tests collected (not the current total)**, with no collection errors. This only verifies collection; the whole upstream/project test suite was not executed, and it should not be read as 207 tests passing.

Lightweight collection command:

```bash
RUNTIME=.local/unblock/runtime
/usr/bin/env -i \
  PATH="$PWD/$RUNTIME/.venv/bin:/usr/bin:/bin" \
  HOME="$PWD/$RUNTIME/home" \
  TMPDIR="$PWD/$RUNTIME/tmp" \
  XDG_CACHE_HOME="$PWD/$RUNTIME/cache" \
  PYTHONNOUSERSITE=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  "$PWD/$RUNTIME/.venv/bin/python" -m pytest \
  -c papertrace.pytest.ini --collect-only -q -p no:cacheprovider test
```
