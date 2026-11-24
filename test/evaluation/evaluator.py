"""Offline fixed-set request planning. No provider transport or authorization."""

from __future__ import annotations

import json
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
