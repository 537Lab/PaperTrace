"""Contract tests for evaluator intake from B's pre-dispatch request observer."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from runpy import run_path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = ROOT / "test/evaluation/cases.json"
SYSTEM_PATH = ROOT / "prompts/answer-system-v1.0.txt"
EVALUATOR_PATH = ROOT / "test/evaluation/evaluator.py"
CASE_ID = "QUAL-02"
RUNTIME_A = "ev-" + "a" * 64
RUNTIME_B = "ev-" + "b" * 64


def digest(value):
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return sha256(encoded).hexdigest()


@pytest.fixture
def fixed_case():
    raw = DATASET_PATH.read_bytes()
    case = next(case for case in json.loads(raw)["cases"] if case["id"] == CASE_ID)
    return sha256(raw).hexdigest(), case, SYSTEM_PATH.read_bytes().decode("utf-8")


@pytest.fixture
def collect_attempt():
    def invoke(**kwargs):
        if not EVALUATOR_PATH.is_file():
            pytest.fail("Evaluator capture entry point is pending: evaluator.py is absent")
        implementation = run_path(str(EVALUATOR_PATH)).get("collect_attempt")
        if not callable(implementation):
            pytest.fail("Evaluator capture entry point is pending: collect_attempt is absent")
        return implementation(**kwargs)

    return invoke


def request_messages(case, system, sent, *, indent=2):
    evidence = {item["id"]: item for item in case["input"]["approved_evidence"]}
    body = {
        "question": case["input"]["question"],
        "approved_evidence": [evidence[identifier] for identifier in sent],
    }
    return (("system", system), ("user", json.dumps(body, indent=indent, ensure_ascii=False)))


class OfflineBoundary:
    """Expose the checked messages and raw response via the proposed driver seam."""

    def __init__(self, messages, citations=(), *, attempts=1, rejected=False, repeat=1):
        self.messages = messages
        self.events = []
        self.attempts = attempts
        self.rejected = rejected
        self.result = SimpleNamespace(citation_evidence_ids=citations)
        self.response = {
            "request_id": f"offline-{repeat}",
            "model": "offline-model",
            "model_version": "synthetic",
            "content": f"Synthetic answer {repeat}",
            "finish_reason": "stop",
            "usage": {"input_tokens": 8, "output_tokens": 2, "total_tokens": 10},
        }

    def generate(self, *, request_observer):
        self.events.append("driver")
        if self.messages is None:
            return SimpleNamespace(result=None, accounting=None), None
        self.events.append("capture")
        try:
            request_observer(self.messages)
        except ValueError:
            # B refuses before call_single if the observer rejects the request.
            return SimpleNamespace(result=None, accounting=None), None
        self.events.append("model")
        accounting = SimpleNamespace(answer_model_attempts=self.attempts)
        outcome = SimpleNamespace(result=None if self.rejected else self.result, accounting=accounting)
        return outcome, self.response


def run(collect_attempt, fixed_case, driver, *, repeat=1, bindings=None):
    dataset_sha256, case, system = fixed_case
    if bindings is None:
        bindings = {(dataset_sha256, CASE_ID): {"ev-a": RUNTIME_A, "ev-b": RUNTIME_B}}
    return collect_attempt(
        dataset_sha256=dataset_sha256,
        case=case,
        repeat=repeat,
        system_prompt=system,
        bindings=bindings,
        drive=driver.generate,
    )


@pytest.mark.parametrize("sent", [("ev-a", "ev-b"), ("ev-b", "ev-a"), ("ev-b",)])
def test_qual02_fixture_passes_existing_request_gate(fixed_case, sent):
    _, case, system = fixed_case
    boundary = run_path(str(ROOT / "scripts/semantic_evidence.py"))
    request = [
        {"role": role, "content": content}
        for role, content in request_messages(case, system, sent)
    ]
    boundary["_check_request"]({"request": request, "sent_ids": sent}, case, system)


@pytest.mark.parametrize(
    ("sent", "runtime_citation", "fixed_citation"),
    [
        (("ev-a", "ev-b"), RUNTIME_A, "ev-a"),
        (("ev-b", "ev-a"), RUNTIME_B, "ev-b"),
        (("ev-b",), RUNTIME_B, "ev-b"),
    ],
    ids=("forward", "reverse", "cropped"),
)
def test_record_uses_actual_request_and_mapped_citations(
    collect_attempt, fixed_case, sent, runtime_citation, fixed_citation,
):
    _, case, system = fixed_case
    messages = request_messages(case, system, sent)
    driver = OfflineBoundary(messages, (runtime_citation,))
    outcome = run(collect_attempt, fixed_case, driver)
    assert driver.events == ["driver", "capture", "model"]
    row = outcome["record"]
    expected = [{"role": role, "content": content} for role, content in messages]
    assert row["request"] == expected
    assert row["sent_ids"] == list(sent)
    assert row["cited_ids"] == [fixed_citation]
    assert row["input_sha256"] == digest(case["input"])
    assert row["prompt_sha256"] == digest(expected)
    assert row["response"] == driver.response
    assert row["response_sha256"] == digest(driver.response)
    assert outcome["accounting_present"] is True
    assert outcome["answer_model_attempts"] == 1


def test_empty_approved_set_has_no_report_or_model_call(collect_attempt, fixed_case):
    driver = OfflineBoundary(None)
    outcome = run(collect_attempt, fixed_case, driver)
    assert driver.events == ["driver"]
    assert outcome["record"] is None
    assert outcome["accounting_present"] is False
    assert outcome["answer_model_attempts"] is None


@pytest.mark.parametrize("fault", ["system", "malformed-user", "unknown-fixed-id"])
def test_rejected_capture_prevents_model_call(collect_attempt, fixed_case, fault):
    _, case, system = fixed_case
    system_entry, user_entry = request_messages(case, system, ("ev-b",))
    if fault == "system":
        system_entry = ("system", system + "\n")
    if fault == "malformed-user":
        user_entry = ("user", "unexpected question template")
    if fault == "unknown-fixed-id":
        payload = json.loads(user_entry[1])
        payload["approved_evidence"][0]["id"] = "ev-pending"
        user_entry = ("user", json.dumps(payload))
    driver = OfflineBoundary((system_entry, user_entry))
    outcome = run(collect_attempt, fixed_case, driver)
    assert driver.events == ["driver", "capture"]
    assert outcome["record"] is None
    assert outcome["accounting_present"] is False
    assert outcome["answer_model_attempts"] is None


@pytest.mark.parametrize("fault", ["different-case", "different-dataset", "non-bijective"])
def test_invalid_binding_fails_before_driver(collect_attempt, fixed_case, fault):
    dataset_sha256, case, system = fixed_case
    wrong_bindings = {
        "different-case": {(dataset_sha256, "QUAL-01"): {"ev-a": RUNTIME_A, "ev-b": RUNTIME_B}},
        "different-dataset": {("0" * 64, CASE_ID): {"ev-a": RUNTIME_A, "ev-b": RUNTIME_B}},
        "non-bijective": {(dataset_sha256, CASE_ID): {"ev-a": RUNTIME_A, "ev-b": RUNTIME_A}},
    }
    driver = OfflineBoundary(request_messages(case, system, ("ev-a",)))
    with pytest.raises(ValueError):
        run(collect_attempt, fixed_case, driver, bindings=wrong_bindings[fault])
    assert driver.events == []


@pytest.mark.parametrize("citation", [RUNTIME_A, "ev-" + "c" * 64], ids=("cropped", "unknown"))
def test_out_of_scope_citation_cannot_produce_report_row(collect_attempt, fixed_case, citation):
    _, case, system = fixed_case
    driver = OfflineBoundary(request_messages(case, system, ("ev-b",)), (citation,))
    outcome = run(collect_attempt, fixed_case, driver)
    assert driver.events == ["driver", "capture", "model"]
    assert outcome["record"] is None
    assert outcome["accounting_present"] is True
    assert outcome["answer_model_attempts"] == 1


@pytest.mark.parametrize("attempts", [0, None, 1], ids=("zero", "unknown", "one"))
def test_preserves_d_outcome_accounting_when_drops_result(
    collect_attempt, fixed_case, attempts,
):
    _, case, system = fixed_case
    driver = OfflineBoundary(request_messages(case, system, ("ev-b",)), attempts=attempts, rejected=True)
    outcome = run(collect_attempt, fixed_case, driver)
    assert outcome["record"] is None
    assert outcome["accounting_present"] is True
    assert outcome["answer_model_attempts"] == attempts


def test_repeat_never_reuses_prior_capture(collect_attempt, fixed_case):
    _, case, system = fixed_case
    first = OfflineBoundary(request_messages(case, system, ("ev-b",), indent=2), repeat=1)
    second = OfflineBoundary(request_messages(case, system, ("ev-b",), indent=None), repeat=2)
    empty = OfflineBoundary(None)
    first_row = run(collect_attempt, fixed_case, first, repeat=1)["record"]
    second_row = run(collect_attempt, fixed_case, second, repeat=2)["record"]
    third = run(collect_attempt, fixed_case, empty, repeat=3)
    assert (first_row["case_id"], first_row["repeat"]) == (CASE_ID, 1)
    assert (second_row["case_id"], second_row["repeat"]) == (CASE_ID, 2)
    assert first_row["request"][1]["content"] != second_row["request"][1]["content"]
    assert first_row["prompt_sha256"] != second_row["prompt_sha256"]
    assert first_row["response_sha256"] != second_row["response_sha256"]
    assert third["record"] is None
    assert empty.events == ["driver"]
