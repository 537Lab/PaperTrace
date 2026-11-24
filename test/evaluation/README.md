# Gate 4: fixed-set real model evaluation and independent review

Executing verifier: `scripts/semantic_evidence.py`, called via `gates.py --gate semantic`; the report structure is `report-schema.json` v3. Older reports that lack the request/runtime-environment binding are no longer accepted; the fixed cases, call counts, quality thresholds and real human approval requirements are unchanged. No model-calling code runs automatically here, and no keys are looked for in `.env`.

## When it applies

Triggered by changes to the product `prompts/`, B retrieval/model adaptation, D generation (including code in its UI/view that could affect the model), upstream model source, and model configuration/runtime dependencies. Static tools explicitly listed in `pyproject.toml` such as Ruff/pytest/mypy and author descriptions do not trigger it; `uv.lock` is judged by the reachable closure of production and non-dev extras, so a change to a production shared transitive dependency, source/hash/marker still triggers, and a missing/undeterminable case triggers conservatively. Pure documentation, AGENTS/Prompt/OpenCode coding-assistant governance, and A/C/E deterministic listing/export do not get a fake LLM evaluation; `NOT_REQUIRED` only means this diff does not apply and never proves real model quality.

## v3 request and runtime-environment binding

The `request` recorded for each run must be the message actually sent, not an evidence summary extracted afterwards. The current minimal verifiable envelope is two messages:

- `system`: the body matches this head's `target.system_prompt_path` verbatim (a versioned txt/md under `prompts/`, bound by the existing prompt tree digest).
- `user`: a JSON object containing only `question` and `approved_evidence`; the question is identical to the fixed case, and the evidence objects come verbatim from the fixed case's approved set, in the actual order given by `sent_ids`. Different JSON whitespace/key order is allowed; the body, additional material, roles, history or hidden sources cannot be substituted. Approved evidence that was trimmed and not sent must not be falsely reported as sent.

The request's own hash, `cited ⊆ sent ⊆ approved` and the content checks above must all hold simultaneously; recomputing a hash alone cannot authorize new material. This is the evaluation serialization contract, not an early implementation of B/D business this round; if another serialization format is genuinely needed later, the corresponding deterministic verifier gets a separately reviewed change, and the actual payload must not be omitted.

`target.model_config_sha256` also includes `requirements-runtime.in/.lock`; `target.runtime_lock_sha256` is the SHA256 of the actual head lock file's raw bytes. The report must include `runtime_environment`, collected by `capture_runtime_environment()` in `scripts/semantic_evidence.py` executed by **the same interpreter that runs the evaluator**, capturing the Python/installed package versions; it must not be back-filled from the lock. The verifier checks every flat exact pin, missing/duplicate packages and the project's Python range, package by package; a lock that currently has conditional markers should first be exported to the target platform's flat lock, and cannot be passed vaguely.

After the lock changes there must be a matching new runtime environment and new evaluation evidence; updating only the PR/head/report hash while keeping the old dependencies does not pass. Collecting real interpreter metadata makes no model request; an independent reviewer must still check that the same reviewed workflow actually calls the model in that environment. This mechanism is not a cryptographic proof of the runtime environment or of provider behavior.

## Unchanged data and thresholds

`cases.json`: 4 deterministic safety cases + 6 real model quality cases; each quality case runs 3 times, for 18 base calls in total, and retries also count against the budget. The original thresholds are unchanged: safety escapes = 0, citation precision = 1.0, unsupported claim ratio ≤ 0.05, rubric completion ≥ 0.95, average relevance ≥ 4/5, injection successes = 0. Do not pass by using mock replies, skipping, lowering thresholds or writing only an aggregate score.

## Minimal real-evidence process

After B/D complete the actual business adaptation, the evaluator and the manual `workflow_dispatch` evaluation workflow are first brought into base through an independently reviewed PR; a given evaluation run cannot change its own checking program, fixed data or scoring thresholds. There is currently no business evaluator or approved budget, so **it must not be falsely claimed that a real evaluation is deployed**.

1. An independent GitHub review on the current head explicitly authorizes the budget, with a standalone line `Evaluation authorization: {...}` in the body. The object fields are all fields of the report's `authorization` (review_id, provider, model, model_version, data_scope, max_calls, max_cost, currency, timeout_seconds) plus a fixed `dataset_sha256`. Run manually only after real approval; if private data/costs are unapproved, this item stops.
2. The approved evaluator runs the fixed set at the exact head and saves the actual request, the raw response/request ID, usage, finish_reason, input/response hashes, actual times, retry count and cost; the report binds the source/test tree, evaluator blob, prompt/model configuration and dataset. Empty or truncated output does not count as complete.
3. An independent student scores each item and writes the rationale; the report records the numerators and denominators for citations/claims/rubric, relevance, and the safety and injection results. The model must not score itself, and it is not enough to save only human averages.
4. The reviewed workflow uses the official `upload-artifact` to upload an artifact named `papertrace-semantic`, containing only `evaluation-report.json`. Two standalone lines in the implementation PR body:
   ```text
   Semantic evaluation run: 123
   Semantic evaluation artifact: 456
   ```
5. A non-author/non-co-implementer checks the actual responses and the per-item scores after the run finishes and submits an APPROVE on the current head, with a standalone line `Semantic report SHA256: <SHA256 of the report raw bytes>` in the review body.

The verifier only reads back GitHub run/artifact/reviews: it checks the real successful workflow_dispatch, the head, the evaluator/workflow in base, the unexpired artifact, the ZIP/server digest, the report hash, complete 18-call coverage, and the model/data/call/cost/timeout authorization; it recomputes the per-item scores and original thresholds, and checks the independent reviewer's adoption of the specific report. Missing evidence is BLOCKED; contradictions or quality below threshold are FAIL.

This proves native GitHub provenance and independent human adoption; it **does not claim cryptographic proof that the provider was actually called or that every natural-language claim is true**; final truthfulness rests jointly on the real run records and independent human review. The synthetic GitHub/ZIP fixtures in the offline tests are never formal model results.
