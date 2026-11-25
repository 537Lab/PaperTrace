"""Fixed-set request planning and authorized semantic evaluation."""

from __future__ import annotations

import argparse
import asyncio
import importlib
import importlib.util
import io
import json
import math
import os
import re
import stat
import subprocess
import sys
import tempfile
import time
import zipfile
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from decimal import Decimal
from fractions import Fraction
from hashlib import sha256
from pathlib import Path
from types import ModuleType
from typing import Any

from jsonschema import Draft202012Validator  # type: ignore[import-untyped]


def prepare_requests(dataset: dict[str, Any], system_prompt: str) -> list[dict[str, Any]]:
    """Build expected envelopes only; actual dispatched requests require boundary capture."""
    if dataset.get("schema_version") != 1 or dataset.get("dataset_id") != "papertrace-synthetic-v1":
        raise ValueError("Unexpected evaluation dataset identity.")
    if not isinstance(system_prompt, str) or not system_prompt.strip():
        raise ValueError("Missing versioned system prompt.")
    cases = [
        case for case in dataset["cases"] if case["kind"] == "real-model-quality"
    ]
    if [case["id"] for case in cases] != [f"QUAL-{i:02d}" for i in range(1, 7)]:
        raise ValueError("Unexpected evaluation case coverage or order.")
    result = []
    for case in cases:
        question = case["input"]["question"]
        evidence = case["input"]["approved_evidence"]
        if not isinstance(question, str) or not question.strip() or not evidence:
            raise ValueError("Missing authorized evaluation material.")
        if any(
            not isinstance(item, dict)
            or set(item) != {"id", "text"}
            or any(not isinstance(value, str) or not value for value in item.values())
            for item in evidence
        ):
            raise ValueError("Invalid evidence object.")
        ids = [item["id"] for item in evidence]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate evidence identity.")
        body = json.dumps(
            {"question": question, "approved_evidence": evidence},
            ensure_ascii=False,
        )
        for repeat in range(1, 4):
            result.append({
                "case_id": case["id"],
                "repeat": repeat,
                "sent_ids": list(ids),
                "request": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": body},
                ],
            })
    return result


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject duplicate keys, mirroring the Gate 4 report parser."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate-json-key")
        result[key] = value
    return result


def _invalid_constant(value: str) -> Any:
    """Reject NaN and Infinity, mirroring the Gate 4 report parser."""
    raise ValueError("invalid-json-constant")


def _digest_json(value: Any) -> str:
    """Hash a value exactly as the report row records it."""
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    return sha256(encoded).hexdigest()


def collect_attempt(
    *,
    dataset_sha256: str,
    case: dict[str, Any],
    repeat: int,
    system_prompt: str,
    bindings: dict[tuple[str, str], dict[str, str]],
    drive: Any,
) -> dict[str, Any]:
    """Assemble one attempt row from B's checked pre-dispatch request.

    The observed send set, request messages and evidence text all come from the
    observer callback; the draft and result may only confirm what was captured.
    A row requires readable accounting, an exact capture, and consistent draft,
    result and citation mappings.
    """
    case_id = case.get("id")
    if not isinstance(case_id, str) or not case_id:
        raise ValueError("Evaluator case has no identifier.")
    mapping = bindings.get((dataset_sha256, case_id))
    if not isinstance(mapping, dict) or not mapping:
        raise ValueError("Invalid fixed-to-runtime binding registry.")
    runtime_ids = tuple(mapping.values())
    if len(set(runtime_ids)) != len(runtime_ids) or any(
        not isinstance(fixed, str) or not isinstance(runtime, str)
        or not fixed or not runtime
        for fixed, runtime in mapping.items()
    ):
        raise ValueError("Binding registry is not a bijection of identifiers.")
    inverse = {runtime: fixed for fixed, runtime in mapping.items()}
    expected_question = case.get("input", {}).get("question")
    expected_text = {
        item.get("id"): item.get("text")
        for item in case.get("input", {}).get("approved_evidence", [])
    }
    captured: list[tuple[str, str]] = []
    captured_sent: list[str] = []

    def observe(messages: Any) -> None:
        if not isinstance(messages, tuple) or len(messages) != 2:
            raise ValueError("Capture must be exactly a system and a user message.")
        (role_a, system_text), (role_b, user_text) = messages
        if (role_a, role_b) != ("system", "user"):
            raise ValueError("Capture roles must be system then user.")
        if system_text != system_prompt:
            raise ValueError("Captured system message is not the approved version.")
        try:
            payload = json.loads(
                user_text,
                object_pairs_hook=_strict_object,
                parse_constant=_invalid_constant,
            )
        except (TypeError, json.JSONDecodeError) as error:
            raise ValueError("Captured user message is not approved JSON.") from error
        if not isinstance(payload, dict):
            raise ValueError("Captured user message is not an object.")
        evidence = payload.get("approved_evidence")
        if not isinstance(evidence, list) or not evidence:
            raise ValueError("Captured evidence list is empty or malformed.")
        sent: list[str] = []
        for item in evidence:
            if not isinstance(item, dict) or set(item) != {"id", "text"}:
                raise ValueError("Captured evidence item is malformed.")
            if not isinstance(item["id"], str) or not isinstance(item["text"], str):
                raise ValueError("Captured evidence item has non-string fields.")
            if item["id"] not in mapping or expected_text.get(item["id"]) != item["text"]:
                raise ValueError("Captured evidence is not authorized by the fixed case.")
            sent.append(item["id"])
        if len(set(sent)) != len(sent):
            raise ValueError("Captured evidence ids repeat.")
        expected_payload = {
            "question": expected_question,
            "approved_evidence": [
                {"id": item, "text": expected_text[item]}
                for item in sent
            ],
        }
        if payload != expected_payload:
            raise ValueError(
                "Captured user message is not exactly the approved payload."
            )
        captured[:] = [("system", system_text), ("user", user_text)]
        captured_sent[:] = sent

    outcome, response = drive(request_observer=observe)
    accounting = getattr(outcome, "accounting", None)
    attempts = None if accounting is None else accounting.answer_model_attempts
    collected: dict[str, Any] = {
        "record": None,
        "accounting_present": accounting is not None,
        "answer_model_attempts": attempts,
    }
    if not captured or not captured_sent or accounting is None:
        return collected
    draft = getattr(outcome, "draft", None)
    raw_result = getattr(outcome, "result", None)
    if (
        draft is None
        or getattr(draft, "status", None) != "draft"
        or raw_result is None
        or response is None
    ):
        return collected
    draft_sent: list[str] = []
    for value in draft.sent_evidence_ids:
        if value not in inverse:
            return collected
        draft_sent.append(inverse[value])
    result_sent: list[str] = []
    for value in raw_result.sent_evidence_ids:
        if value not in inverse:
            return collected
        result_sent.append(inverse[value])
    observed = set(captured_sent)
    if set(draft_sent) != observed or set(result_sent) != observed:
        return collected
    cited_ids: list[str] = []
    for value in draft.citation_evidence_ids:
        if value not in inverse:
            return collected
        cited_ids.append(inverse[value])
    if not set(cited_ids) <= observed:
        return collected
    request = [{"role": role, "content": content} for role, content in captured]
    collected["record"] = {
        "case_id": case_id,
        "repeat": repeat,
        "request": request,
        "sent_ids": list(captured_sent),
        "cited_ids": cited_ids,
        "input_sha256": _digest_json(case["input"]),
        "prompt_sha256": _digest_json(request),
        "response": response,
        "response_sha256": _digest_json(response),
    }
    return collected


ROOT = Path(__file__).resolve().parents[2]
REPOSITORY = "537Lab/PaperTrace"
WORKFLOW = ".github/workflows/semantic-evaluation.yml"
EVALUATOR = "test/evaluation/evaluator.py"
DATASET = "test/evaluation/cases.json"
SCHEMA = "test/evaluation/report-schema.json"


def _semantic() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "papertrace_evaluator_semantic",
        ROOT / "scripts/semantic_evidence.py",
    )
    if spec is None or spec.loader is None:
        raise ValueError("Evidence verifier unavailable.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _bound_context(
    semantic: ModuleType, ctx: Any, client: Any, pr_number: int, run_id: int
) -> dict[str, Any]:
    """Read the current run, PR, participants and immutable control blobs."""
    control = semantic.control
    if type(pr_number) is not int or pr_number < 1:
        raise ValueError("Invalid PR identity.")
    if type(run_id) is not int or run_id < 1:
        raise ValueError("Invalid workflow run identity.")
    if ctx.repository != REPOSITORY:
        raise ValueError("Unexpected repository.")
    head = control._require_sha(ctx.head, "exact-head-required")
    base = control._require_sha(ctx.base, "exact-base-required")
    prefix = f"/repos/{REPOSITORY}"
    current = control._api(client, f"{prefix}/pulls/{pr_number}")
    control._check_pr_repositories(current)
    if (
        current.get("number") != pr_number
        or current.get("state") != "open"
        or current.get("merged") is True
        or current["head"]["sha"] != head
        or current["base"]["sha"] != base
    ):
        raise ValueError("Current PR does not match the evaluation target.")
    run = control._api(client, f"{prefix}/actions/runs/{run_id}")
    if (
        run.get("id") != run_id
        or run.get("event") != "workflow_dispatch"
        or run.get("status") != "in_progress"
        or run.get("conclusion") is not None
        or run.get("head_sha") != head
        or run.get("repository", {}).get("full_name") != REPOSITORY
        or run.get("path", "").split("@", 1)[0] != WORKFLOW
    ):
        raise ValueError("Evaluation run does not match the approved workflow target.")
    _check_first_attempt(run)
    for path in (WORKFLOW, EVALUATOR, DATASET, SCHEMA):
        if semantic._blob(ctx, base, path) != semantic._blob(ctx, head, path):
            raise ValueError("Evaluation controls differ from the trusted base.")
    participants = {control._login(current)}
    commits = control._api_list(client, f"{prefix}/pulls/{pr_number}/commits?per_page=100")
    if not commits or None in participants:
        raise ValueError("Missing participant identity.")
    for commit in commits:
        for field in ("author", "committer"):
            actor = commit.get(field) or {}
            if actor.get("login") and actor.get("type") != "Bot":
                participants.add(actor["login"].casefold())
    reviews = control._api_list(client, f"{prefix}/pulls/{pr_number}/reviews?per_page=100")
    events = control._api_list(client, f"{prefix}/issues/{pr_number}/events?per_page=100")
    raw_dataset = ctx.read(DATASET, ref=base).encode("utf-8")
    return {
        "current": current,
        "run": run,
        "head": head,
        "participants": participants,
        "reviews": reviews,
        "events": events,
        "dataset": semantic._json(raw_dataset),
        "dataset_sha256": sha256(raw_dataset).hexdigest(),
        "schema": semantic._json(ctx.read(SCHEMA, ref=base).encode("utf-8")),
    }


def _independent(
    semantic: ModuleType,
    client: Any,
    bound: dict[str, Any],
    review: dict[str, Any],
) -> tuple[str, datetime]:
    control = semantic.control
    actor = control._login(review)
    allowed = control._trusted_reviewers()
    if (
        not actor
        or actor in bound["participants"]
        or (allowed is not None and actor not in allowed)
        or (review.get("user") or {}).get("type") != "User"
        or actor.endswith("[bot]")
        or review.get("commit_id") != bound["head"]
    ):
        raise ValueError("Review is not independent and bound to the target.")
    permission = control._api(
        client,
        f"/repos/{REPOSITORY}/collaborators/{actor}/permission",
    )
    if permission.get("permission") not in {"write", "maintain", "admin"}:
        raise ValueError("Reviewer lacks required repository permission.")
    reviewed_at = control._parse_time(review.get("submitted_at"))
    if reviewed_at < control._parse_time(bound["current"]["created_at"]):
        raise ValueError("Review predates the target PR.")
    for event in bound["events"]:
        if event.get("event") not in {"review_dismissed", "dismissed"}:
            continue
        dismissed = event.get("dismissed_review") or event.get("review") or {}
        event_at = control._parse_time(event.get("created_at"))
        if event_at >= reviewed_at and (
            dismissed.get("review_id") == review.get("id")
            or dismissed.get("id") == review.get("id")
            or control._login(dismissed) == actor
        ):
            raise ValueError("Review was dismissed.")
    for later in bound["reviews"]:
        if (
            control._login(later) == actor
            and later.get("state")
            in {
                "CHANGES_REQUESTED",
                "DISMISSED",
            }
            and control._parse_time(later.get("submitted_at")) >= reviewed_at
        ):
            raise ValueError("Review was revoked.")
    return actor, reviewed_at


def _review_payload(semantic: ModuleType, review: dict[str, Any], label: str) -> dict[str, Any]:
    lines = re.findall(
        r"(?m)^" + re.escape(label) + r":\s*(\{[^\n]+\})\s*$",
        review.get("body") or "",
    )
    if len(lines) != 1:
        raise ValueError("Missing unique structured review payload.")
    payload = semantic._json(lines[0].encode("utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Invalid review payload.")
    return payload


def _authorize(
    semantic: ModuleType,
    ctx: Any,
    client: Any,
    *,
    pr_number: int,
    run_id: int,
    authorization_review_id: int,
) -> dict[str, Any]:
    """Validate the server run and review provenance."""
    control = semantic.control
    try:
        bound = _bound_context(semantic, ctx, client, pr_number, run_id)
        matches = [
            review for review in bound["reviews"] if review.get("id") == authorization_review_id
        ]
        if len(matches) != 1 or matches[0].get("state") != "APPROVED":
            raise ValueError("Missing exact budget approval.")
        approval = matches[0]
        _independent(semantic, client, bound, approval)
        payload = _review_payload(semantic, approval, "Evaluation authorization")
        if payload.pop("dataset_sha256", None) != bound["dataset_sha256"]:
            raise ValueError("Authorization dataset mismatch.")
        if payload.get("review_id") != authorization_review_id:
            raise ValueError("Authorization review ID mismatch.")
        validator = Draft202012Validator(bound["schema"]["properties"]["authorization"])
        if not validator.is_valid(payload) or payload["max_calls"] != MAX_CALLS:
            raise ValueError("Invalid fixed-run budget.")
        if any(
            not payload[field].strip()
            for field in (
                "provider",
                "model",
                "model_version",
                "data_scope",
                "currency",
            )
        ):
            raise ValueError("Empty authorization value.")
        approved_at = semantic._authorization(
            {"authorization": payload, "target": {"dataset_sha256": bound["dataset_sha256"]}},
            bound["current"],
            bound["reviews"],
            client,
            bound["head"],
            bound["participants"],
        )
        if approved_at >= control._parse_time(bound["run"]["created_at"]):
            raise ValueError("Authorization must precede workflow creation.")
        return {
            "head_sha": bound["head"],
            "authorization": payload,
            "dataset_sha256": bound["dataset_sha256"],
        }
    except (control._EvidenceInvalid, control._EvidenceBlocked, KeyError, TypeError) as error:
        raise ValueError("Evaluation preflight rejected.") from error


def _check_first_attempt(run: dict[str, Any]) -> None:
    attempt = run.get("run_attempt")
    if os.environ.get("PAPERTRACE_RUN_ATTEMPT") != "1" or type(attempt) is not int or attempt != 1:
        raise ValueError("Evaluation requires a verified first dispatch attempt.")


def _check_dispatch_history(
    semantic: ModuleType, client: Any, run_id: int, authorization_review_id: int, head: str
) -> None:
    control = semantic.control
    route = f"/repos/{REPOSITORY}/actions/runs?event=workflow_dispatch&per_page=100"
    try:
        if isinstance(client, control._LiveGitHub):
            # The shared get() only enables pagination for a lone per_page query.
            pages = semantic._json(client._request(route, paginated=True))
        else:
            pages = control._api(client, route)
    except (control._EvidenceInvalid, control._EvidenceBlocked) as error:
        raise ValueError("Cannot verify evaluation dispatch history.") from error
    if isinstance(pages, dict):
        pages = [pages]
    if not isinstance(pages, list) or not pages or any(
        not isinstance(page, dict) or not isinstance(page.get("workflow_runs"), list)
        for page in pages
    ):
        raise ValueError("Invalid evaluation dispatch history.")
    runs = [run for page in pages for run in page["workflow_runs"]]
    if any(page.get("total_count", len(runs)) != len(runs) for page in pages):
        raise ValueError("Incomplete evaluation dispatch history.")
    for run in runs:
        if not isinstance(run, dict) or type(run.get("id")) is not int:
            raise ValueError("Invalid evaluation dispatch record.")
        if run["id"] == run_id:
            continue
        title = run.get("display_title")
        markers = (
            re.findall(r"(?<![\w-])auth-([1-9][0-9]*)(?![\w-])", title)
            if isinstance(title, str) else []
        )
        if str(authorization_review_id) in markers:
            raise ValueError("Authorization review already bound to another dispatch.")
        if (
            run.get("head_sha") == head
            and (run.get("path") or "").split("@", 1)[0] == WORKFLOW
            and not markers
        ):
            raise ValueError("Same-head dispatch has no authorization review marker.")


def preflight(
    ctx: Any,
    client: Any,
    *,
    pr_number: int,
    run_id: int,
    authorization_review_id: int,
) -> dict[str, Any]:
    """Check the dispatch and budget without creating a provider client."""
    semantic = _semantic()
    approved = _authorize(
        semantic, ctx, client, pr_number=pr_number, run_id=run_id,
        authorization_review_id=authorization_review_id,
    )
    _check_dispatch_history(semantic, client, run_id, authorization_review_id, approved['head_sha'])
    _tariff_prices(approved["authorization"])
    return approved


def accept_ratings(
    ctx: Any,
    client: Any,
    *,
    pr_number: int,
    run_id: int,
    raw_sha256: str,
    captured_at: str,
) -> dict[str, Any]:
    """Read a unique independent, raw-output-bound rating review; no scoring fabrication."""
    semantic = _semantic()
    control = semantic.control
    try:
        if not isinstance(raw_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", raw_sha256):
            raise ValueError("Invalid capture digest.")
        bound = _bound_context(semantic, ctx, client, pr_number, run_id)
        captured = control._parse_time(captured_at)
        if captured < control._parse_time(bound["run"]["created_at"]):
            raise ValueError("Capture predates workflow creation.")
        matches = [
            review
            for review in bound["reviews"]
            if re.search(r"(?m)^Semantic ratings:", review.get("body") or "")
        ]
        if len(matches) != 1 or matches[0].get("state") != "COMMENTED":
            raise ValueError("Missing unique independent ratings review.")
        review = matches[0]
        actor, reviewed_at = _independent(semantic, client, bound, review)
        if reviewed_at <= captured:
            raise ValueError("Ratings must follow actual capture.")
        body = _review_payload(semantic, review, "Semantic ratings")
        if (
            set(body) != {"run_id", "head_sha", "raw_sha256", "ratings"}
            or type(body["run_id"]) is not int
            or body["run_id"] != run_id
            or body["head_sha"] != bound["head"]
            or body["raw_sha256"] != raw_sha256
        ):
            raise ValueError("Rating capture binding mismatch.")
        ratings = body["ratings"]
        schema = bound["schema"]["properties"]["scores"]["properties"]["independent_ratings"]
        if not Draft202012Validator(schema).is_valid(ratings):
            raise ValueError("Invalid item ratings.")
        quality = {
            case["id"]: case
            for case in bound["dataset"]["cases"]
            if case["kind"] == "real-model-quality"
        }
        expected = {(case, repeat) for case in quality for repeat in range(1, 4)}
        seen = set()
        for rating in ratings:
            key = (rating["case_id"], rating["repeat"])
            if key not in expected or key in seen or rating["reviewer"].casefold() != actor:
                raise ValueError("Rating identity or coverage mismatch.")
            seen.add(key)
            rubric = quality[key[0]]["rubric"]
            items = len(rubric.get("must_include", [])) + len(rubric.get("must_not_include", []))
            if (
                rating["correct_citations"] > rating["citation_count"]
                or rating["unsupported_claims"] > rating["claim_count"]
                or rating["rubric_items"] != items
                or rating["rubric_met"] > items
                or not rating["rationale"].strip()
            ):
                raise ValueError("Invalid item rating counts or rationale.")
        if seen != expected:
            raise ValueError("Incomplete independent ratings.")
        return {"review_id": review["id"], "reviewer": actor, "ratings": ratings}
    except (control._EvidenceInvalid, control._EvidenceBlocked, KeyError, TypeError) as error:
        raise ValueError("Independent ratings intake rejected.") from error


SYSTEM_PROMPT = "prompts/answer-system-v1.0.txt"
RUNTIME_LOCK = "requirements-runtime.lock"
MODEL_CONFIG_PATHS = (
    "src/papertrace/retrieval",
    "src/papertrace/answer",
    "src/paperqa",
    "packages",
    "pyproject.toml",
    "uv.lock",
    "requirements-runtime.in",
    RUNTIME_LOCK,
)
PROVIDER = "cityu-litellm"
MODEL = "CS5351/DeepSeek-V4-Flash"
ENDPOINT = "https://llm.cs.cityu.edu.hk/v1"
MAX_CALLS = 18
MAX_PACING_SECONDS = 60
MAX_BODY_BYTES = 1_000_000
MAX_ARTIFACT_BYTES = 25_000_000
MAX_ARTIFACT_PAGES = 10
MAX_REPORT_BYTES = 4_000_000
DIGEST_LINE_BYTES = 65
MAX_INPUT_TOKENS = 12000
MAX_OUTPUT_TOKENS = 2000
RAW_ARTIFACT = "papertrace-semantic-raw"
RAW_FILE = "raw-capture.json"
DIGEST_FILE = "raw-capture.sha256"
REPORT_FILE = "evaluation-report.json"
EXECUTION_ENVIRONMENT = "papertrace-evaluation-execution"
RATING_ENVIRONMENT = "papertrace-independent-rating"


def _now() -> datetime:
    return datetime.now(UTC)


def _target(semantic: ModuleType, ctx: Any, dataset_digest: str) -> dict[str, str]:
    head = ctx.head
    return {
        "head_sha": head,
        "source_tree_sha": semantic._blob(ctx, head, "src"),
        "test_tree_sha": semantic._blob(ctx, head, "test"),
        "dataset_sha256": dataset_digest,
        "prompt_sha256": sha256(ctx.git("ls-tree", "-r", head, "--", "prompts")).hexdigest(),
        "model_config_sha256": sha256(
            ctx.git("ls-tree", "-r", head, "--", *MODEL_CONFIG_PATHS)
        ).hexdigest(),
        "evaluator_path": EVALUATOR,
        "evaluator_sha": semantic._blob(ctx, head, EVALUATOR),
        "system_prompt_path": SYSTEM_PROMPT,
        "runtime_lock_sha256": sha256(ctx.read(RUNTIME_LOCK, ref=head).encode()).hexdigest(),
    }


def _write_json(semantic: ModuleType, path: Path, value: dict[str, Any]) -> bytes:
    raw: bytes = semantic.canonical(value)
    if len(raw) > MAX_REPORT_BYTES:
        raise ValueError("Evaluation evidence exceeds report size limit.")
    with path.open("xb") as output:
        output.write(raw)
    return raw


def _case_corpus(rows: dict[str, str], at: datetime) -> tuple[Any, dict[str, Any]]:
    contracts = importlib.import_module("papertrace.contracts")
    documents = {
        label: contracts.DocumentVersion(
            schema_version=1,
            document_id=f"doc-{label}",
            version_sha256=sha256(body.encode()).hexdigest(),
            title=label,
            source_name=f"{label}.txt",
            status="ready",
        )
        for label, body in rows.items()
    }
    snapshot = contracts.CorpusSnapshot(
        schema_version=1,
        documents=tuple(documents.values()),
        created_at=at,
    )
    records = {
        label: contracts.EvidenceRecord(
            schema_version=1,
            snapshot_id=snapshot.snapshot_id,
            document_id=document.document_id,
            version_sha256=document.version_sha256,
            locator=contracts.SourceLocator(
                schema_version=1,
                line_start=1,
                line_end=1,
                chunk_id=f"chunk-{label}",
                parser_name="fixed-evaluation",
                parser_version="1",
            ),
            excerpt=rows[label],
            retrieved_at=at,
        )
        for label, document in documents.items()
    }
    return snapshot, records


def _answer_inputs(
    case: dict[str, Any],
    snapshot: Any,
    records: dict[str, Any],
    at: datetime,
    ledger_root: Path,
) -> tuple[Any, Any, Any]:
    model = importlib.import_module("papertrace.answer.model")
    review = importlib.import_module("papertrace.review.service")
    adapter = importlib.import_module("papertrace.answer.c_adapter")
    base = model.AnswerRequest(
        snapshot=snapshot,
        question_id=f"q-{case['id'].lower()}",
        answer_id=f"ans-{case['id'].lower()}",
        requested_at=at,
        evidence=tuple(records.values()),
    )
    ledger = review.ReviewLedger(
        ledger_root=ledger_root,
        snapshot=snapshot,
        candidates=base.evidence,
        clock=lambda: at,
    )
    return base, ledger, adapter.CReviewProjectionAdapter(ledger=ledger)


def _fixture_accept(ledger: Any, base: Any, records: list[Any]) -> None:
    """Replay the fixed case's accepted inputs in its isolated evaluation ledger."""
    review = importlib.import_module("papertrace.review.service")
    for revision, record in enumerate(records):
        review.submit_decision(
            ledger,
            question_id=base.question_id,
            evidence_id=record.evidence_id,
            action="accept",
            reviewer_ref="reviewer-FIXED_CASE",
            reason="Fixed evaluation input",
            expected_revision=revision,
        )


def _deterministic(case: dict[str, Any], at: datetime, work: Path) -> dict[str, Any]:
    generation = importlib.import_module("papertrace.answer.generation")
    release = importlib.import_module("papertrace.answer.release")
    contracts = importlib.import_module("papertrace.contracts")
    kind = case["id"]
    data = case["input"]
    label = data.get("accepted", ["ev-a"])[0] if kind != "DET-01" else "ev-a"
    old_text = data.get("old_version", "The fixed case evidence.")
    snapshot, records = _case_corpus({label: old_text}, at)
    base, ledger, projections = _answer_inputs(case, snapshot, records, at, work / "old")
    record = records[label]

    if kind in {"DET-01", "DET-02"}:
        calls = 0
        if kind == "DET-02":
            _fixture_accept(ledger, base, [records[key] for key in data["accepted"]])

        class ObservedGeneration:
            def call(self, _request: Any) -> Any:
                nonlocal calls
                calls += 1
                raw_output = " ".join(f"({key})" for key in data["draft_citations"])
                return generation.GenerationCallResult(
                    status="SUCCESS",
                    raw_output=raw_output,
                    sent_evidence_ids=tuple(records[key].evidence_id for key in data["sent"]),
                    citation_aliases=(),
                    unknown_citation_keys=tuple(data["draft_citations"]),
                    ambiguous_citation_keys=(),
                    refusal_reason=None,
                )

        outcome = generation.AnswerGenerationService(
            projections=projections,
            generation=ObservedGeneration(),
        ).run(
            generation.AnswerGenerationRequest(
                base=base,
                question_text=data.get("question", "Does the citation resolve?"),
                selected_evidence_ids=tuple(
                    records[key].evidence_id for key in data.get("sent", [])
                ),
                policy=generation.GenerationPolicySpec(provider=PROVIDER, model=MODEL),
            )
        )
        if kind == "DET-01":
            return {
                "generation_calls": calls,
                "answer_status": "refused"
                if outcome.draft.status == "abstained"
                else outcome.draft.status,
            }
        return {
            "release_allowed": outcome.draft is not None and outcome.draft.status == "draft",
            "invalid_citations": list(outcome.raw_unknown_keys),
        }

    if kind not in {"DET-03", "DET-04"}:
        raise ValueError("Unrecognized deterministic case.")
    _fixture_accept(ledger, base, [record])
    projection = projections.read_projection(base.question_id)
    draft_snapshot = snapshot
    if kind == "DET-04" and data["draft_version"] != old_text:
        draft_snapshot, _ = _case_corpus({label: data["draft_version"]}, at)
    draft = contracts.AnswerDraft(
        schema_version=1,
        answer_id=base.answer_id,
        snapshot_id=draft_snapshot.snapshot_id,
        question_id=base.question_id,
        review_revision=data.get("generation_review_revision", projection.revision),
        review_digest=projection.digest,
        approved_evidence_ids=(record.evidence_id,),
        sent_evidence_ids=(record.evidence_id,),
        citation_evidence_ids=(record.evidence_id,),
        status="draft",
        body=old_text,
        generated_at=at,
    )
    if kind == "DET-03":
        review = importlib.import_module("papertrace.review.service")
        while projection.revision < data["current_review_revision"]:
            projection = review.submit_decision(
                ledger,
                question_id=base.question_id,
                evidence_id=record.evidence_id,
                action="exclude"
                if record.evidence_id in projection.accepted_evidence_ids
                else "accept",
                reviewer_ref="reviewer-FIXED_CASE",
                reason="Fixed evaluation revision change",
                expected_revision=projection.revision,
            )
    else:
        snapshot, records = _case_corpus({label: data["current_version"]}, at)
        _, _, projections = _answer_inputs(case, snapshot, records, at, work / "current")
        projection = projections.read_projection(base.question_id)

    class Current:
        def read_current(self, question_id: str) -> tuple[Any, Any, tuple[Any, ...]]:
            if question_id != base.question_id:
                raise ValueError("Current evidence question mismatch.")
            return snapshot, projection, tuple(records.values())

    decision = release.ReleaseGate(current=Current(), clock=lambda: at).check(draft=draft)
    reason = decision.reason_codes[0]
    labels = {
        release.REVIEW_REVISION_STALE: "stale-review",
        release.SNAPSHOT_SCOPE_MISMATCH: "stale-corpus",
    }
    return {
        "release_allowed": decision.status == "released",
        "reason": labels.get(reason, reason),
    }


def _tariff_prices(auth: dict[str, Any]) -> tuple[Decimal, Decimal]:
    rates = []
    for key in (
        "PAPERTRACE_LLM_INPUT_COST_PER_MILLION",
        "PAPERTRACE_LLM_OUTPUT_COST_PER_MILLION",
    ):
        value = os.environ.get(key, "").strip()
        if re.fullmatch(r"\+?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)", value) is None:
            raise ValueError("Missing or invalid provider price ceiling.")
        rates.append(Decimal(value))
    input_rate, output_rate = rates
    ceiling = (
        Fraction(input_rate) * MAX_INPUT_TOKENS + Fraction(output_rate) * MAX_OUTPUT_TOKENS
    ) * auth["max_calls"] / 1_000_000
    if ceiling > Decimal(str(auth["max_cost"])):
        raise ValueError("Authorization cannot cover the fixed evaluation at the price ceiling.")
    return input_rate / 1_000_000, output_rate / 1_000_000


def _provider_config(auth: dict[str, Any]) -> dict[str, Any]:
    """Require an operator-verified deployment, quota and upper-bound tariff."""
    base_url = os.environ.get("PAPERTRACE_LLM_BASE_URL") or ENDPOINT
    pinned_version = os.environ.get("PAPERTRACE_LLM_MODEL_VERSION") or MODEL
    if (
        base_url.rstrip("/") != ENDPOINT
        or auth["provider"] != PROVIDER
        or auth["model"] != MODEL
        or auth["model_version"] != pinned_version
        or auth["data_scope"] != "papertrace-synthetic-v1"
        or auth["currency"] != (os.environ.get("PAPERTRACE_LLM_CURRENCY") or "USD")
    ):
        raise ValueError("Provider deployment or data authorization does not match.")
    input_price, output_price = _tariff_prices(auth)
    pacing = float(os.environ.get("PAPERTRACE_LLM_PACING_SECONDS") or "1.5")
    if not math.isfinite(pacing) or not 0 <= pacing <= MAX_PACING_SECONDS:
        raise ValueError("Invalid inter-call pacing.")
    return {
        "endpoint": ENDPOINT + "/chat/completions",
        "input_price": input_price,
        "output_price": output_price,
        "version": pinned_version,
        "pacing": pacing,
        "timeout": min(float(auth["timeout_seconds"]), 120.0),
    }


TokenCounter = Callable[[Sequence[tuple[str, str]]], int]
APPROVED_TOKEN_ENCODINGS = {
    (PROVIDER, MODEL): "cl100k_base",
    ("openai", "gpt-4o-2024-08-06"): "o200k_base",
}


def load_approved_token_counter(*, provider: str, model: str) -> TokenCounter:
    encoding_name = APPROVED_TOKEN_ENCODINGS.get((provider, model))
    if encoding_name is None:
        raise ValueError("No approved tokenizer for this provider/model.")
    encoding = importlib.import_module("tiktoken").get_encoding(encoding_name)

    def count(messages: Sequence[tuple[str, str]]) -> int:
        return 3 + sum(
            3 + len(encoding.encode(role, disallowed_special=()))
            + len(encoding.encode(content, disallowed_special=()))
            for role, content in messages
        )

    return count


def count_final_request_tokens(
    messages: Sequence[tuple[str, str]],
    *,
    counter: TokenCounter | None = None,
    provider: str = PROVIDER,
    model: str = MODEL,
) -> int:
    if (provider, model) not in APPROVED_TOKEN_ENCODINGS:
        raise ValueError("No approved tokenizer for this provider/model.")
    if counter is None:
        counter = load_approved_token_counter(provider=provider, model=model)
    tokens = counter(messages)
    if type(tokens) is not int or not 1 <= tokens <= MAX_INPUT_TOKENS:
        raise ValueError("Invalid or over-budget final request token count.")
    return tokens


class ProviderCapture:
    """Serial one-shot HTTP transport used solely at B's observed model boundary."""

    def __init__(
        self, semantic: ModuleType, config: dict[str, Any], api_key: str, counter: TokenCounter,
    ) -> None:
        self.semantic = semantic
        self.config = config
        self.api_key = api_key
        self.counter = counter
        self.evidence: list[dict[str, Any]] = []
        self.last_finished: float | None = None
        self.active = False
        self.expected: dict[str, Any] | None = None

    def observe(self, messages: tuple[tuple[str, str], ...]) -> None:
        if self.expected is not None:
            raise ValueError("Unexpected second observation for one case.")
        self.expected = {"request": [{"role": role, "content": text} for role, text in messages]}

    async def complete(self, messages: list[Any], max_tokens: int) -> dict[str, Any]:
        request = [{"role": item.role, "content": item.content} for item in messages]
        capture = self.expected
        if (
            capture is None
            or capture["request"] != request
            or self.active
            or len(self.evidence) >= MAX_CALLS
            or not 1 <= max_tokens <= MAX_OUTPUT_TOKENS
        ):
            raise ValueError("Unexpected, concurrent, or over-budget provider attempt.")
        count_final_request_tokens(
            tuple((item.role, item.content) for item in messages), counter=self.counter,
        )
        self.expected = None
        self.active = True
        try:
            if self.last_finished is not None:
                await asyncio.sleep(
                    max(0, self.config["pacing"] - (time.monotonic() - self.last_finished))
                )
            httpx = importlib.import_module("httpx")
            started = _now()
            capture.update(started_at=started.isoformat(), attempts=1)
            self.evidence.append(capture)
            timeout = self.config["timeout"]
            transport = httpx.AsyncHTTPTransport(retries=0, trust_env=False)
            async with (
                asyncio.timeout(timeout),
                httpx.AsyncClient(
                    transport=transport,
                    timeout=timeout,
                    follow_redirects=False,
                    trust_env=False,
                ) as client,
                client.stream(
                    "POST",
                    self.config["endpoint"],
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"model": MODEL, "messages": request, "max_tokens": max_tokens},
                ) as reply,
            ):
                reply.raise_for_status()
                buffer = bytearray()
                async for chunk in reply.aiter_bytes():
                    buffer.extend(chunk)
                    if len(buffer) > MAX_BODY_BYTES:
                        raise ValueError("Provider response exceeds capture limit.")
                response = self.semantic._json(bytes(buffer))
            finished = _now()
            if (finished - started).total_seconds() > timeout:
                raise ValueError("Provider exceeded its authorized deadline.")
            parsed = self._response(response, max_tokens)
            usage = parsed["usage"]
            cost = (
                usage["input_tokens"] * self.config["input_price"]
                + usage["output_tokens"] * self.config["output_price"]
            )
            capture.update(
                finished_at=finished.isoformat(),
                response=parsed,
                cost=float(cost),
                response_sha256=sha256(self.semantic.canonical(parsed)).hexdigest(),
            )
            return parsed
        finally:
            self.last_finished = time.monotonic()
            self.active = False

    def _response(self, value: dict[str, Any], max_tokens: int) -> dict[str, Any]:
        observed_model = value.get("model")
        observed_version = (
            value.get("model_version") or value.get("system_fingerprint") or observed_model
        )
        if observed_model != MODEL or observed_version != self.config["version"]:
            raise ValueError("Provider did not attest the authorized model version.")
        choices = value["choices"]
        if len(choices) != 1:
            raise ValueError("Expected one provider choice.")
        choice = choices[0]
        content, finish = choice["message"]["content"], choice["finish_reason"]
        request_id = value["id"]
        if (
            not isinstance(content, str)
            or not content.strip()
            or finish not in {"stop", "end_turn"}
            or not isinstance(request_id, str)
            or not request_id.strip()
            or any(self.api_key in field for field in (content, request_id))
        ):
            raise ValueError("Invalid provider content or request identity.")
        source = value["usage"]
        tokens = [source[key] for key in ("prompt_tokens", "completion_tokens", "total_tokens")]
        if any(type(count) is not int or count <= 0 for count in tokens):
            raise ValueError("Provider usage is missing or invalid.")
        incoming, outgoing, total = tokens
        if incoming + outgoing != total or incoming > MAX_INPUT_TOKENS or outgoing > max_tokens:
            raise ValueError("Provider usage exceeds evaluated token limits.")
        return {
            "request_id": request_id,
            "model": value["model"],
            "model_version": observed_version,
            "content": content,
            "finish_reason": finish,
            "usage": {
                "input_tokens": incoming,
                "output_tokens": outgoing,
                "total_tokens": total,
            },
        }


def _quality_run(
    case: dict[str, Any],
    repeat: int,
    at: datetime,
    work: Path,
    capture: ProviderCapture,
    dataset_digest: str,
    semantic: ModuleType,
    system_prompt: str,
) -> dict[str, Any]:
    b = importlib.import_module("papertrace.retrieval.gateway")
    generation = importlib.import_module("papertrace.answer.generation")
    gateway_adapter = importlib.import_module("papertrace.answer.b_gateway_adapter")
    settings_type = importlib.import_module("paperqa.settings").Settings
    llm_type: Any = importlib.import_module("lmi").LLMModel
    result_type = importlib.import_module("lmi.types").LLMResult
    material = case["input"]
    sources = {row["id"]: row["text"] for row in material["approved_evidence"]}
    snapshot, records = _case_corpus(sources, at)
    base, ledger, projections = _answer_inputs(case, snapshot, records, at, work)
    _fixture_accept(ledger, base, list(records.values()))
    mapping = {key: record.evidence_id for key, record in records.items()}
    inverse = {value: key for key, value in mapping.items()}

    class AnswerModel(llm_type):  # type: ignore[misc]
        provider: str = PROVIDER
        model: str = MODEL
        max_tokens: int = MAX_OUTPUT_TOKENS

        def count_tokens(self, message: str) -> int:
            prefix = system_prompt + "\n"
            if not message.startswith(prefix):
                raise ValueError("Product prompt differs from the authorized system prompt.")
            return count_final_request_tokens(
                (("system", system_prompt), ("user", message[len(prefix):])),
                counter=capture.counter,
            )

        async def call_single(self, messages: list[Any], **_kwargs: Any) -> Any:
            parsed = await capture.complete(messages, self.max_tokens)
            return result_type(
                model=self.name,
                text=parsed["content"],
                prompt_count=parsed["usage"]["input_tokens"],
                completion_count=parsed["usage"]["output_tokens"],
            )

    def no_retrieval(*_args: Any, **_kwargs: Any) -> Any:
        raise ValueError("Fixed evaluation has no retrieval or expansion permission.")

    settings = settings_type(
        _env_file=None,
        llm=MODEL,
        summary_llm=MODEL,
        embedding="sparse",
        answer={"answer_filter_extra_background": False},
    )

    def observe(messages: tuple[tuple[str, str], ...]) -> None:
        actual = [{"role": role, "content": text} for role, text in messages]
        semantic._check_request(
            {"request": actual, "sent_ids": list(mapping)}, case, system_prompt
        )
        capture.observe(messages)

    bridge = b.PaperQA2Adapter(
        source_reader=no_retrieval,
        settings=settings,
        answer_llm_model=AnswerModel(name=MODEL),
        summary_llm_model=object(),
        embedding_model=object(),
    )
    gateway = b.Gateway(
        adapter=bridge,
        source_reader=no_retrieval,
        model_factory=bridge,
        clock=lambda: at,
        evaluation_binding=b.EvaluationCaseBinding(
            dataset_sha256=dataset_digest,
            case_id=case["id"],
            snapshot_id=snapshot.snapshot_id,
            question=material["question"],
            fixed_evidence=tuple(sources.items()),
            fixed_to_runtime=tuple(mapping.items()),
        ),
        request_observer=observe,
    )
    before = len(capture.evidence)
    try:
        outcome = generation.AnswerGenerationService(
            projections=projections,
            generation=gateway_adapter.BGatewayGenerationAdapter(gateway=gateway),
        ).run(
            generation.AnswerGenerationRequest(
                base=base,
                question_text=material["question"],
                selected_evidence_ids=tuple(mapping.values()),
                policy=generation.GenerationPolicySpec(provider=PROVIDER, model=MODEL),
            )
        )
    finally:
        if len(capture.evidence) > before:
            capture.evidence[-1].update(case_id=case["id"], repeat=repeat)
    if (
        len(capture.evidence) != before + 1
        or outcome.result is None
        or outcome.accounting is None
        or outcome.accounting.answer_model_attempts != 1
    ):
        raise ValueError("The product boundary did not observe exactly one provider response.")
    if outcome.draft is None or outcome.draft.status != "draft" or outcome.reason is not None:
        raise ValueError("The product did not produce a valid draft.")
    run = capture.evidence[-1]
    response = run["response"]
    if outcome.result.raw_output != response["content"]:
        raise ValueError("Provider response and B's raw output differ.")
    cited = [inverse[key] for key in outcome.draft.citation_evidence_ids]
    run.update(
        provider=PROVIDER,
        model=response["model"],
        model_version=response["model_version"],
        sent_ids=[inverse[key] for key in outcome.draft.sent_evidence_ids],
        cited_ids=cited,
        content=response["content"],
        finish_reason=response["finish_reason"],
        usage=response["usage"],
        input_sha256=sha256(semantic.canonical(material)).hexdigest(),
        prompt_sha256=sha256(semantic.canonical(run["request"])).hexdigest(),
    )
    if not set(cited) <= set(run["sent_ids"]):
        raise ValueError("Provider cited evidence outside the sent scope.")
    semantic._check_request(run, case, system_prompt)
    return run


def collect(
    ctx: Any,
    client: Any,
    *,
    pr_number: int,
    run_id: int,
    authorization_review_id: int,
    system_prompt_path: str = SYSTEM_PROMPT,
    transport: Callable[[tuple[tuple[str, str], ...]], Any] | None = None,
) -> None:
    """Collect through B/D, or probe the validated request envelopes offline."""
    semantic = _semantic()
    approved = preflight(
        ctx, client, pr_number=pr_number, run_id=run_id,
        authorization_review_id=authorization_review_id,
    )
    bound = _bound_context(semantic, ctx, client, pr_number, run_id)
    prompt = ctx.read(system_prompt_path, ref=approved["head_sha"])
    requests = prepare_requests(bound["dataset"], prompt)
    auth = approved["authorization"]
    if transport is not None:
        _require_no_raw_artifact(semantic, client, run_id)
        counter = load_approved_token_counter(provider=auth["provider"], model=auth["model"])
        for request in requests:
            messages = tuple((row["role"], row["content"]) for row in request["request"])
            count_final_request_tokens(messages, counter=counter)
            transport(messages)
        return

    report = {
        "schema_version": 3,
        "provenance": {"repository": REPOSITORY, "run_id": run_id},
        "target": {
            **_target(semantic, ctx, approved["dataset_sha256"]),
            "system_prompt_path": system_prompt_path,
        },
        "authorization": auth,
        "runtime_environment": semantic.capture_runtime_environment(),
    }
    semantic._check_runtime(report, ctx, approved["head_sha"])
    _check_environment(semantic, client, EXECUTION_ENVIRONMENT)
    _check_deployment(semantic, client, bound, run_id, EXECUTION_ENVIRONMENT)
    sys.path[:0] = [str(ROOT / "src"), str(ROOT / "packages/paper-qa-pypdf/src")]
    _collect(
        semantic, ctx, client, pr_number, run_id, authorization_review_id, bound, report, prompt,
    )


def _collect(
    semantic: ModuleType,
    ctx: Any,
    client: Any,
    pr: int,
    run_id: int,
    approval: int,
    bound: dict[str, Any],
    report: dict[str, Any],
    prompt: str,
) -> None:
    current = preflight(
        ctx, client, pr_number=pr, run_id=run_id, authorization_review_id=approval,
    )
    auth = report["authorization"]
    if current["authorization"] != auth:
        raise ValueError("Authorization changed before collection.")
    _require_no_raw_artifact(semantic, client, run_id)
    config = _provider_config(auth)
    # Keep the credential out of process environment before importing product code.
    credential = os.environ.pop("PAPERTRACE_PROVIDER_API_KEY", "")
    if not credential or credential.strip() != credential:
        raise ValueError("Protected provider credential is absent or malformed.")
    counter = load_approved_token_counter(provider=auth["provider"], model=auth["model"])
    capture = ProviderCapture(semantic, config, credential, counter)
    raw_dir = ROOT / "semantic-raw"
    raw_dir.mkdir()
    completed = False
    try:
        with tempfile.TemporaryDirectory(prefix="papertrace-semantic-") as temporary:
            work = Path(temporary)
            os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
            os.environ["PQA_HOME"] = str(work / "paperqa")
            at = _now()
            dataset = bound["dataset"]
            report["deterministic_results"] = [
                {"case_id": case["id"], "actual": _deterministic(case, at, work / case["id"])}
                for case in dataset["cases"]
                if case["kind"] == "deterministic"
            ]
            current = preflight(
                ctx, client, pr_number=pr, run_id=run_id, authorization_review_id=approval
            )
            if current["authorization"] != report["authorization"]:
                raise ValueError("Authorization changed before collection.")
            _require_no_raw_artifact(semantic, client, run_id)
            report["runs"] = capture.evidence
            for case in dataset["cases"]:
                if case["kind"] == "real-model-quality":
                    for repeat in range(1, 4):
                        _quality_run(
                            case,
                            repeat,
                            at,
                            work / f"{case['id']}-{repeat}",
                            capture,
                            bound["dataset_sha256"],
                            semantic,
                            prompt,
                        )
            # During a running Actions job, the API's updated_at can lag behind its steps.
            run = dict(bound["run"], updated_at=_now().isoformat())
            approval_review = next(row for row in bound["reviews"] if row["id"] == approval)
            approved_at = semantic.control._parse_time(approval_review["submitted_at"])
            semantic._check_runs(report, dataset, approved_at, run, prompt)
            completed = True
    finally:
        raw = _write_json(
            semantic,
            raw_dir / RAW_FILE,
            {
                "complete": completed,
                "captured_at": _now().isoformat(),
                "report": {**report, "runs": capture.evidence},
            },
        )
        (raw_dir / DIGEST_FILE).write_text(sha256(raw).hexdigest() + "\n", encoding="ascii")


def _raw_artifacts(semantic: ModuleType, client: Any, run_id: int) -> list[dict[str, Any]]:
    route = f"/repos/{REPOSITORY}/actions"
    control = semantic.control
    try:
        pages = control._api(client, f"{route}/runs/{run_id}/artifacts?per_page=100")
    except (control._EvidenceInvalid, control._EvidenceBlocked) as error:
        raise ValueError("Cannot verify raw artifact listing.") from error
    if isinstance(pages, dict):
        pages = [pages]
    if (
        not isinstance(pages, list)
        or not pages
        or len(pages) > MAX_ARTIFACT_PAGES
        or any(
            not isinstance(page, dict) or not isinstance(page.get("artifacts"), list)
            for page in pages
        )
    ):
        raise ValueError("Invalid raw artifact listing.")
    artifacts = [item for page in pages for item in page["artifacts"]]
    if any(not isinstance(item, dict) for item in artifacts) or any(
        page.get("total_count", len(artifacts)) != len(artifacts) for page in pages
    ):
        raise ValueError("Invalid or incomplete raw artifact listing.")
    return [item for item in artifacts if item.get("name") == RAW_ARTIFACT]


def _require_no_raw_artifact(semantic: ModuleType, client: Any, run_id: int) -> None:
    if _raw_artifacts(semantic, client, run_id):
        raise ValueError("Raw evaluation capture already exists for this run.")


def _download_raw(
    semantic: ModuleType,
    ctx: Any,
    client: Any,
    run_id: int,
) -> tuple[dict[str, Any], str]:
    route = f"/repos/{REPOSITORY}/actions"
    matches = _raw_artifacts(semantic, client, run_id)
    if len(matches) != 1:
        raise ValueError("Expected a unique raw capture from this run.")
    artifact_id = matches[0]["id"]
    metadata = semantic.control._api(client, f"{route}/artifacts/{artifact_id}")
    workflow_run = metadata.get("workflow_run") or {}
    if (
        metadata.get("id") != artifact_id
        or metadata.get("name") != RAW_ARTIFACT
        or metadata.get("expired") is not False
        or workflow_run.get("id") != run_id
        or workflow_run.get("head_sha") != ctx.head
    ):
        raise ValueError("Raw artifact provenance does not match evaluation.")
    archive = client.download_artifact(artifact_id)
    if (
        not isinstance(archive, bytes)
        or len(archive) > MAX_ARTIFACT_BYTES
        or metadata.get("digest") != "sha256:" + sha256(archive).hexdigest()
    ):
        raise ValueError("Raw archive digest or size mismatch.")
    with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
        if sorted(zipped.namelist()) != sorted((RAW_FILE, DIGEST_FILE)):
            raise ValueError("Unexpected raw artifact members.")
        if (
            zipped.getinfo(RAW_FILE).file_size > MAX_REPORT_BYTES
            or zipped.getinfo(DIGEST_FILE).file_size != DIGEST_LINE_BYTES
            or any(stat.S_ISLNK(info.external_attr >> 16) for info in zipped.infolist())
        ):
            raise ValueError("Invalid raw artifact size.")
        raw = zipped.read(RAW_FILE)
        digest = sha256(raw).hexdigest()
        if zipped.read(DIGEST_FILE) != (digest + "\n").encode("ascii"):
            raise ValueError("Raw artifact digest mismatch.")
    record = semantic._json(raw)
    if not isinstance(record, dict) or record.get("complete") is not True:
        raise ValueError("Raw capture was incomplete.")
    return record, digest


def _scores(
    ratings: list[dict[str, Any]],
    observed: list[dict[str, Any]],
    dataset: dict[str, Any],
) -> dict[str, Any]:
    actual = {item["case_id"]: item["actual"] for item in observed}
    escapes = sum(
        actual.get(case["id"]) != case["oracle"]
        for case in dataset["cases"]
        if case["kind"] == "deterministic"
    )

    def total(field: str) -> int:
        return sum(row[field] for row in ratings)

    return {
        "independent_ratings": ratings,
        "deterministic_safety_escapes": escapes + total("safety_escapes"),
        "citation_precision": float(
            Fraction(total("correct_citations"), total("citation_count"))
        ),
        "unsupported_claim_ratio": float(
            Fraction(total("unsupported_claims"), total("claim_count"))
        ),
        "rubric_completion_ratio": float(Fraction(total("rubric_met"), total("rubric_items"))),
        "mean_relevance_1_to_5": float(
            sum(Fraction(str(row["relevance"])) for row in ratings) / len(ratings)
        ),
        "injection_successes": total("injection_successes"),
    }


def _finalize(
    semantic: ModuleType,
    ctx: Any,
    client: Any,
    pr: int,
    run_id: int,
    approval: int,
    bound: dict[str, Any],
    expected_report: dict[str, Any],
    prompt: str,
) -> None:
    _check_first_attempt(bound["run"])
    raw, digest = _download_raw(semantic, ctx, client, run_id)
    report = raw["report"]
    if any(
        report.get(key) != value
        for key, value in expected_report.items()
        if key != "runtime_environment"
    ):
        raise ValueError("Capture identity or authorization differs from this run.")
    intake = accept_ratings(
        ctx,
        client,
        pr_number=pr,
        run_id=run_id,
        raw_sha256=digest,
        captured_at=raw["captured_at"],
    )
    dataset = bound["dataset"]
    report["scores"] = _scores(intake["ratings"], report["deterministic_results"], dataset)
    if not Draft202012Validator(bound["schema"]).is_valid(report):
        raise ValueError("Evaluation report failed its schema.")
    semantic._check_runtime(report, ctx, ctx.head)
    approval_review = next(row for row in bound["reviews"] if row["id"] == approval)
    approved_at = semantic.control._parse_time(approval_review["submitted_at"])
    run = dict(bound["run"], updated_at=_now().isoformat())
    cases, quality, _, _ = semantic._check_runs(report, dataset, approved_at, run, prompt)
    semantic._scores(report, dataset, cases, quality, intake["reviewer"])
    _write_json(semantic, ROOT / REPORT_FILE, report)


def _check_environment(semantic: ModuleType, client: Any, name: str) -> None:
    route = f"/repos/{REPOSITORY}/environments/{name}"
    if isinstance(client, semantic.control._LiveGitHub):
        # The shared transport discards HTTP status on errors. Request headers
        # here so only an actual 403 can defer to Actions deployment enforcement.
        process = subprocess.run(
            [
                "gh",
                "api",
                "--method",
                "GET",
                "--hostname",
                "github.com",
                "--include",
                "-H",
                "Accept: application/vnd.github+json",
                "-H",
                "X-GitHub-Api-Version: 2022-11-28",
                route,
            ],
            capture_output=True,
            timeout=60,
            check=False,
            env=semantic.control._github_environment(),
        )
        headers, separator, body = process.stdout.replace(b"\r\n", b"\n").partition(b"\n\n")
        status = re.match(rb"HTTP/[^ ]+ ([0-9]{3})(?:[ \n]|$)", headers)
        if status and status[1] == b"403":
            print(
                f"{name}: environment API returned 403 under read-only GITHUB_TOKEN. "
                "GitHub Actions enforces environment protection, and deployment approval "
                "is verified separately."
            )
            return
        if not status or status[1] != b"200" or not separator or process.returncode:
            raise ValueError("Cannot verify the evaluation environment.")
        environment = semantic._json(body)
    else:
        environment = semantic.control._api(client, route)
    reviewers_required = any(
        rule.get("type") == "required_reviewers"
        and rule.get("prevent_self_review") is True
        and rule.get("reviewers")
        for rule in environment.get("protection_rules", [])
    )
    policy = environment.get("deployment_branch_policy") or {}
    if (
        environment.get("name") != name
        or not reviewers_required
        or not (policy.get("protected_branches") or policy.get("custom_branch_policies"))
    ):
        raise ValueError(
            "Evaluation environment requires reviewers and deployment branch restrictions."
        )


def _check_deployment(
    semantic: ModuleType,
    client: Any,
    bound: dict[str, Any],
    run_id: int,
    environment: str,
) -> None:
    reviews = semantic.control._api_list(
        client,
        f"/repos/{REPOSITORY}/actions/runs/{run_id}/approvals",
    )
    initiators = {
        (bound["run"].get(field) or {}).get("login", "").casefold()
        for field in ("actor", "triggering_actor")
    }
    for review in reviews:
        reviewer = semantic.control._login(review)
        if (
            reviewer
            and reviewer not in bound["participants"] | initiators
            and (review.get("user") or {}).get("type") == "User"
            and review.get("state") == "approved"
            and environment in {item.get("name") for item in review.get("environments", [])}
        ):
            return
    raise ValueError("A separate human deployment approval is required.")


def _positive_env(name: str) -> int:
    text = os.environ.get(name, "")
    if re.fullmatch(r"[1-9][0-9]{0,15}", text) is None:
        raise ValueError("Missing or invalid workflow identifier.")
    return int(text)


def _workflow(stage: str) -> None:
    if os.environ.get("PAPERTRACE_RUN_ATTEMPT") != "1":
        raise ValueError("Evaluation requires a fresh dispatch with a fresh authorization.")
    pr = _positive_env("PAPERTRACE_TARGET_PR")
    run_id = _positive_env("PAPERTRACE_RUN_ID")
    approval = _positive_env("PAPERTRACE_AUTHORIZATION_REVIEW_ID")
    head = os.environ["PAPERTRACE_RUN_HEAD"]
    if head != os.environ["PAPERTRACE_TARGET_HEAD"]:
        raise ValueError("Input head does not match the server run head.")
    semantic = _semantic()
    head = semantic.control._require_sha(head, "workflow-head-invalid")
    client = semantic.control._LiveGitHub()
    current = semantic.control._api(client, f"/repos/{REPOSITORY}/pulls/{pr}")
    semantic.control._check_pr_repositories(current)
    if current["base"].get("ref") != "main":
        raise ValueError("Evaluation requires the trusted main base.")
    base = semantic.control._require_sha(current["base"]["sha"], "workflow-base-invalid")
    spec = importlib.util.spec_from_file_location(
        "papertrace_evaluation_gates", ROOT / "scripts/gates.py"
    )
    if spec is None or spec.loader is None:
        raise ValueError("Gate context unavailable.")
    gates = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = gates
    spec.loader.exec_module(gates)
    ctx = gates.GateContext(root=ROOT, base=base, head=head, scope="full")
    if ctx.git("rev-parse", "HEAD").decode().strip() != head or ctx.git(
        "diff", "--name-only", head, "--"
    ):
        raise ValueError("Checkout does not match clean evaluation target.")
    if stage == "collect":
        collect(ctx, client, pr_number=pr, run_id=run_id, authorization_review_id=approval)
        print("Semantic evaluation collect complete.")
        return
    if stage == "finalize":
        approved = _authorize(
            semantic, ctx, client, pr_number=pr, run_id=run_id, authorization_review_id=approval
        )
    else:
        approved = preflight(
            ctx, client, pr_number=pr, run_id=run_id, authorization_review_id=approval
        )
    bound = _bound_context(semantic, ctx, client, pr, run_id)
    report = {
        "schema_version": 3,
        "provenance": {"repository": REPOSITORY, "run_id": run_id},
        "target": _target(semantic, ctx, approved["dataset_sha256"]),
        "authorization": approved["authorization"],
        "runtime_environment": semantic.capture_runtime_environment(),
    }
    semantic._check_runtime(report, ctx, head)
    prompt = ctx.read(SYSTEM_PROMPT, ref=head)
    prepare_requests(bound["dataset"], prompt)
    if stage == "preflight":
        _provider_config(approved["authorization"])
        _check_environment(semantic, client, EXECUTION_ENVIRONMENT)
        _check_environment(semantic, client, RATING_ENVIRONMENT)
    elif stage == "finalize":
        _check_environment(semantic, client, RATING_ENVIRONMENT)
        _check_deployment(semantic, client, bound, run_id, RATING_ENVIRONMENT)
        _finalize(semantic, ctx, client, pr, run_id, approval, bound, report, prompt)
    print(f"Semantic evaluation {stage} complete.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("preflight", "collect", "finalize"))
    stage = parser.parse_args().stage
    try:
        _workflow(stage)
    except Exception as error:
        # Provider messages and exception chains may contain credentials or content.
        print(f"Semantic evaluation {stage} blocked ({type(error).__name__}).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
