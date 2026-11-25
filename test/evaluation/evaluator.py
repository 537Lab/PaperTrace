"""Offline fixed-set request planning. No provider transport or authorization."""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Any


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
