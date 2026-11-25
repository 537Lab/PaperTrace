"""Offline contract for preflight and authenticated rating intake; never model calls."""

import json
import re
import sys
from importlib import import_module
from inspect import signature
from pathlib import Path
from types import ModuleType

import pytest
import yaml
from test_semantic_evidence import fixture, git

ROOT = Path(__file__).resolve().parents[2]
PREFIX = "/repos/537Lab/PaperTrace"
RAW_HASH = "a" * 64
DISPATCH_RUNS = f"{PREFIX}/actions/runs?event=workflow_dispatch&per_page=100"
REVIEW_LIST = f"{PREFIX}/pulls/20/reviews?per_page=100"
RUN_ATTEMPT_ENV = "PAPERTRACE_RUN_ATTEMPT"
RUN_ARTIFACTS = f"{PREFIX}/actions/runs/401/artifacts?per_page=100"
INPUT_CAP = 12_000
DEFAULT_SYSTEM_PROMPT = "prompts/answer-system-v1.0.txt"
TOKENIZER_PROVIDER = "openai"
TOKENIZER_MODEL = "gpt-4o-2024-08-06"
TARIFF_ENV = (
    "PAPERTRACE_LLM_INPUT_COST_PER_MILLION",
    "PAPERTRACE_LLM_OUTPUT_COST_PER_MILLION",
)


def evaluator_module(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "test/evaluation"))
    try:
        evaluator = import_module("evaluator")
    except ModuleNotFoundError as error:
        if error.name == "evaluator":
            pytest.fail("IMPLEMENTATION_MISSING: evaluator")
        raise
    assert callable(getattr(evaluator, "preflight", None)), "IMPLEMENTATION_MISSING: preflight"
    assert callable(getattr(evaluator, "accept_ratings", None)), "IMPLEMENTATION_MISSING: intake"
    return evaluator


def workflow_fixture(tmp_path, monkeypatch):
    for name in TARIFF_ENV:
        monkeypatch.setenv(name, "0")
    monkeypatch.setenv(RUN_ATTEMPT_ENV, "1")
    ctx, github = fixture(tmp_path)
    # The legacy synthetic fixture uses evaluate.yml. Build an equivalent
    # synthetic history with the exact dedicated workflow path under test.
    prompt = ctx.read("prompts/runtime.txt", ref=ctx.head)
    git(tmp_path, "checkout", "--detach", ctx.base)
    git(
        tmp_path, "mv", ".github/workflows/evaluate.yml",
        ".github/workflows/semantic-evaluation.yml",
    )
    git(tmp_path, "commit", "-qm", "synthetic dedicated evaluation workflow")
    ctx.base = git(tmp_path, "rev-parse", "HEAD").decode().strip()
    (tmp_path / "prompts/runtime.txt").write_text(prompt, encoding="utf-8")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "synthetic candidate prompt")
    ctx.head = git(tmp_path, "rev-parse", "HEAD").decode().strip()
    pr = github.responses[f"{PREFIX}/pulls/20"]
    pr["base"]["sha"], pr["head"]["sha"] = ctx.base, ctx.head
    github.report["target"]["head_sha"] = ctx.head
    for review in github.responses[f"{PREFIX}/pulls/20/reviews?per_page=100"]:
        review["commit_id"] = ctx.head
    run = github.responses[f"{PREFIX}/actions/runs/401"]
    run.update(
        status="in_progress", conclusion=None, updated_at="2026-11-13T10:21:00Z",
        head_sha=ctx.head, path=".github/workflows/semantic-evaluation.yml",
        display_title="auth-301", run_attempt=1,
    )
    github.responses[DISPATCH_RUNS] = {"total_count": 1, "workflow_runs": [run]}
    github.responses[RUN_ARTIFACTS] = {"total_count": 0, "artifacts": []}
    github.responses[f"{PREFIX}/actions/artifacts/501"]["workflow_run"]["head_sha"] = ctx.head
    return ctx, github


def preflight(evaluator, ctx, github):
    return evaluator.preflight(
        ctx, github, pr_number=20, run_id=401, authorization_review_id=301,
    )


def test_live_preflight_requires_exact_server_context(tmp_path, monkeypatch):
    evaluator = evaluator_module(monkeypatch)
    ctx, github = workflow_fixture(tmp_path, monkeypatch)
    approved = preflight(evaluator, ctx, github)
    assert approved["head_sha"] == ctx.head
    assert approved["authorization"] == github.report["authorization"]
    assert approved["dataset_sha256"] == github.report["target"]["dataset_sha256"]


@pytest.mark.parametrize(
    "fault",
    (
        "wrong-head", "wrong-event", "wrong-workflow", "self-auth", "no-auth",
        "wrong-dataset", "read-only", "late-auth", "call-budget", "cost-budget",
        "timeout-budget", "mock-provider",
    ),
)
def test_preflight_rejects_invalid_authorization_before_provider_stage(tmp_path, monkeypatch, fault):
    evaluator = evaluator_module(monkeypatch)
    ctx, github = workflow_fixture(tmp_path, monkeypatch)
    run = github.responses[f"{PREFIX}/actions/runs/401"]
    reviews = github.responses[f"{PREFIX}/pulls/20/reviews?per_page=100"]
    if fault == "wrong-head":
        run["head_sha"] = "f" * 40
    elif fault == "wrong-event":
        run["event"] = "pull_request"
    elif fault == "wrong-workflow":
        run["path"] = ".github/workflows/evaluate.yml"
    elif fault == "late-auth":
        reviews[0]["submitted_at"] = "2026-11-13T10:20:45Z"
    elif fault in {"call-budget", "cost-budget", "timeout-budget", "mock-provider"}:
        authorization = json.loads(reviews[0]["body"].split(": ", 1)[1])
        field, value = {
            "call-budget": ("max_calls", 17),
            "cost-budget": ("max_cost", -1),
            "timeout-budget": ("timeout_seconds", 0),
            "mock-provider": ("provider", "mock"),
        }[fault]
        authorization[field] = value
        reviews[0]["body"] = "Evaluation authorization: " + json.dumps(authorization)
    elif fault == "self-auth":
        reviews[0]["user"]["login"] = "implementer"
    elif fault == "no-auth":
        reviews.pop(0)
    elif fault == "wrong-dataset":
        authorization = json.loads(reviews[0]["body"].split(": ", 1)[1])
        authorization["dataset_sha256"] = "f" * 64
        reviews[0]["body"] = "Evaluation authorization: " + json.dumps(authorization)
    elif fault == "read-only":
        github.responses[f"{PREFIX}/collaborators/independent-student/permission"] = {
            "permission": "read",
        }
    with pytest.raises(ValueError):
        preflight(evaluator, ctx, github)


def set_authorization(github, review_id, **changes):
    review = next(item for item in github.responses[REVIEW_LIST] if item["id"] == review_id)
    authorization = {
        **github.report["authorization"],
        "dataset_sha256": github.report["target"]["dataset_sha256"],
        "review_id": review_id,
        **changes,
    }
    review["body"] = "Evaluation authorization: " + json.dumps(authorization)


@pytest.mark.parametrize("name", TARIFF_ENV, ids=("input", "output"))
@pytest.mark.parametrize("value", (None, "", "   "), ids=("unset", "empty", "whitespace"))
def test_preflight_rejects_unknown_tariff_even_with_zero_budget(tmp_path, monkeypatch, name, value):
    ctx, github = workflow_fixture(tmp_path, monkeypatch)
    set_authorization(github, 301, max_cost=0)
    if value is None:
        monkeypatch.delenv(name)
    else:
        monkeypatch.setenv(name, value)
    evaluator = evaluator_module(monkeypatch)
    with pytest.raises(ValueError):
        preflight(evaluator, ctx, github)


@pytest.mark.parametrize(
    ("tariffs", "max_cost", "accepted"),
    (
        pytest.param(("0", "0"), 0, True, id="explicit-zero"),
        # 18 attempts at the B boundary caps of 12,000 input and 2,000 output tokens.
        pytest.param(("0.50", "1.50"), 0.162, True, id="positive-at-ceiling"),
        pytest.param(("0.50", "1.50"), 1.0, True, id="positive-within-budget"),
        pytest.param(("0.50", "1.50"), 0, False, id="positive-over-budget"),
        pytest.param(("0.50", "0"), 0, False, id="input-only-over-budget"),
        pytest.param(("0", "1.50"), 0, False, id="output-only-over-budget"),
    ),
)
def test_preflight_checks_explicit_tariffs_against_budget(
    tmp_path, monkeypatch, tariffs, max_cost, accepted,
):
    ctx, github = workflow_fixture(tmp_path, monkeypatch)
    set_authorization(github, 301, max_cost=max_cost)
    for name, tariff in zip(TARIFF_ENV, tariffs, strict=True):
        monkeypatch.setenv(name, tariff)
    evaluator = evaluator_module(monkeypatch)
    if accepted:
        assert preflight(evaluator, ctx, github)["authorization"]["max_cost"] == max_cost
    else:
        with pytest.raises(ValueError):
            preflight(evaluator, ctx, github)


def add_fresh_dispatch(github, review_id, *, prior_conclusion):
    prior = github.responses[f"{PREFIX}/actions/runs/401"]
    if prior_conclusion is not None:
        prior.update(
            status="completed", conclusion=prior_conclusion, updated_at="2026-11-13T10:25:00Z",
        )
    fresh = dict(
        prior, id=402, display_title=f"auth-{review_id}", status="in_progress", conclusion=None,
        created_at="2026-11-13T10:31:00Z", updated_at="2026-11-13T10:31:01Z",
    )
    if prior_conclusion is None:
        fresh.update(created_at=prior["created_at"], updated_at=prior["updated_at"])
    github.responses[f"{PREFIX}/actions/runs/402"] = fresh
    github.responses[DISPATCH_RUNS] = {"total_count": 2, "workflow_runs": [fresh, prior]}


@pytest.mark.parametrize("conclusion", ("success", "failure", "cancelled"))
def test_preflight_rejects_reuse_after_completed_dispatch(tmp_path, monkeypatch, conclusion):
    evaluator = evaluator_module(monkeypatch)
    ctx, github = workflow_fixture(tmp_path, monkeypatch)
    assert preflight(evaluator, ctx, github)["authorization"]["review_id"] == 301
    add_fresh_dispatch(github, 301, prior_conclusion=conclusion)
    github.calls.clear()
    with pytest.raises(ValueError):
        evaluator.preflight(ctx, github, pr_number=20, run_id=402, authorization_review_id=301)
    assert DISPATCH_RUNS in github.calls


def test_preflight_cannot_authorize_both_concurrent_dispatches(tmp_path, monkeypatch):
    evaluator = evaluator_module(monkeypatch)
    ctx, github = workflow_fixture(tmp_path, monkeypatch)
    add_fresh_dispatch(github, 301, prior_conclusion=None)
    rejected = []
    for run_id in (401, 402):
        github.calls.clear()
        try:
            evaluator.preflight(ctx, github, pr_number=20, run_id=run_id, authorization_review_id=301)
        except ValueError:
            rejected.append(run_id)
        assert DISPATCH_RUNS in github.calls
    assert rejected, "Both visible concurrent dispatches were authorized by review 301"


def test_preflight_accepts_new_independent_review_after_prior_dispatch(tmp_path, monkeypatch):
    evaluator = evaluator_module(monkeypatch)
    ctx, github = workflow_fixture(tmp_path, monkeypatch)
    assert preflight(evaluator, ctx, github)["authorization"]["review_id"] == 301
    set_authorization(github, 302)
    add_fresh_dispatch(github, 302, prior_conclusion="success")
    github.calls.clear()
    approved = evaluator.preflight(ctx, github, pr_number=20, run_id=402, authorization_review_id=302)
    assert approved["head_sha"] == ctx.head
    assert approved["authorization"]["review_id"] == 302
    assert DISPATCH_RUNS in github.calls


@pytest.mark.parametrize(
    "title", ({}, {"display_title": None}, {"display_title": ""}, {"display_title": "   "},
              {"display_title": "manual dispatch"}),
    ids=("missing", "null", "empty", "whitespace", "unmarked"),
)
def test_preflight_rejects_untagged_prior_dispatch_on_same_head(tmp_path, monkeypatch, title):
    ctx, github = workflow_fixture(tmp_path, monkeypatch)
    set_authorization(github, 302)
    add_fresh_dispatch(github, 302, prior_conclusion="success")
    evaluator = evaluator_module(monkeypatch)
    assert evaluator.preflight(
        ctx, github, pr_number=20, run_id=402, authorization_review_id=302,
    )["authorization"]["review_id"] == 302
    prior = github.responses[f"{PREFIX}/actions/runs/401"]
    prior.pop("display_title")
    prior.update(title)
    github.calls.clear()
    with pytest.raises(ValueError):
        evaluator.preflight(ctx, github, pr_number=20, run_id=402, authorization_review_id=302)
    assert DISPATCH_RUNS in github.calls


INVALID_ATTEMPTS = (
    pytest.param(2, "2", id="matched-rerun"),
    pytest.param(2, "1", id="server-rerun"),
    pytest.param(1, "2", id="env-rerun"),
    pytest.param(1, None, id="missing-env"),
    pytest.param(1, "", id="blank-env"),
    pytest.param(1, "   ", id="whitespace-env"),
    pytest.param(1, "invalid", id="invalid-env"),
    pytest.param(1, "0", id="zero-env"),
    pytest.param(None, "1", id="missing-server"),
    pytest.param(True, "1", id="boolean-server"),
    pytest.param("1", "1", id="string-server"),
)


def set_run_attempt(github, monkeypatch, server, env):
    run = github.responses[f"{PREFIX}/actions/runs/401"]
    if server is None:
        run.pop("run_attempt")
    else:
        run["run_attempt"] = server
    if env is None:
        monkeypatch.delenv(RUN_ATTEMPT_ENV)
    else:
        monkeypatch.setenv(RUN_ATTEMPT_ENV, env)


@pytest.mark.parametrize(("server", "env"), INVALID_ATTEMPTS)
def test_preflight_rejects_unverified_first_attempt(tmp_path, monkeypatch, server, env):
    ctx, github = workflow_fixture(tmp_path, monkeypatch)
    set_run_attempt(github, monkeypatch, server, env)
    evaluator = evaluator_module(monkeypatch)
    with pytest.raises(ValueError):
        preflight(evaluator, ctx, github)


class ProviderEntryReached(BaseException):
    """End the positive probe at the first transport entry."""


class ProviderProbe:
    def __init__(self):
        self.requests = []

    @property
    def provider_calls(self):
        return len(self.requests)

    def __call__(self, messages):
        self.requests.append(tuple(messages))
        raise ProviderEntryReached


def collect(
    evaluator, ctx, github, provider, *, run_id=401, review_id=301, system_prompt_path=None,
):
    assert callable(getattr(evaluator, "collect", None)), "IMPLEMENTATION_MISSING: collect"
    if system_prompt_path is None:
        system_prompt_path = github.report["target"]["system_prompt_path"]
    return evaluator.collect(
        ctx, github, pr_number=20, run_id=run_id, authorization_review_id=review_id,
        system_prompt_path=system_prompt_path, transport=provider,
    )


def approved_tokenizer_loader(evaluator):
    assert callable(getattr(evaluator, "load_approved_token_counter", None)), (
        "IMPLEMENTATION_MISSING: approved tokenizer loader"
    )
    return evaluator.load_approved_token_counter


def stub_tokenizer(evaluator, monkeypatch, github, loader, *, review_id=301):
    approved_tokenizer_loader(evaluator)
    review = next(item for item in github.responses[REVIEW_LIST] if item["id"] == review_id)
    authorization = json.loads(review["body"].split(": ", 1)[1])

    def checked_loader(*, provider, model):
        assert provider == authorization["provider"]
        assert model == authorization["model"]
        return loader()

    monkeypatch.setattr(evaluator, "load_approved_token_counter", checked_loader)


@pytest.mark.parametrize(("server", "env"), INVALID_ATTEMPTS)
def test_collect_rejects_unverified_first_attempt_before_provider(tmp_path, monkeypatch, server, env):
    ctx, github = workflow_fixture(tmp_path, monkeypatch)
    set_run_attempt(github, monkeypatch, server, env)
    evaluator = evaluator_module(monkeypatch)
    stub_tokenizer(evaluator, monkeypatch, github, lambda: lambda messages: INPUT_CAP)
    provider = ProviderProbe()
    with pytest.raises(ValueError):
        collect(evaluator, ctx, github, provider)
    assert provider.provider_calls == 0


@pytest.mark.parametrize("expired", (False, True), ids=("available", "expired"))
def test_collect_rejects_existing_raw_artifact_before_provider(tmp_path, monkeypatch, expired):
    ctx, github = workflow_fixture(tmp_path, monkeypatch)
    github.responses[RUN_ARTIFACTS] = {
        "total_count": 1,
        "artifacts": [{"id": 502, "name": "papertrace-semantic-raw", "expired": expired}],
    }
    evaluator = evaluator_module(monkeypatch)
    stub_tokenizer(evaluator, monkeypatch, github, lambda: lambda messages: INPUT_CAP)
    provider = ProviderProbe()
    with pytest.raises(ValueError):
        collect(evaluator, ctx, github, provider)
    assert RUN_ARTIFACTS in github.calls
    assert provider.provider_calls == 0


@pytest.mark.parametrize("name", TARIFF_ENV, ids=("input", "output"))
def test_collect_rechecks_tariff_after_preflight_before_provider(tmp_path, monkeypatch, name):
    ctx, github = workflow_fixture(tmp_path, monkeypatch)
    set_authorization(github, 301, max_cost=0)
    evaluator = evaluator_module(monkeypatch)
    stub_tokenizer(evaluator, monkeypatch, github, lambda: lambda messages: INPUT_CAP)
    assert preflight(evaluator, ctx, github)["authorization"]["max_cost"] == 0
    monkeypatch.setenv(name, "   ")
    provider = ProviderProbe()
    with pytest.raises(ValueError):
        collect(evaluator, ctx, github, provider)
    assert provider.provider_calls == 0


def test_final_request_token_count_uses_approved_counter_with_framing(monkeypatch):
    messages = (("system", "规"), ("user", "hi"))
    framing_tokens = 7
    content_tokens = {"规": 1, "hi": 1}

    def approved_counter(final_messages):
        assert tuple(final_messages) == messages
        return framing_tokens + sum(content_tokens[text] for _, text in final_messages)

    evaluator = evaluator_module(monkeypatch)
    count = getattr(evaluator, "count_final_request_tokens", None)
    assert callable(count), "IMPLEMENTATION_MISSING: final request token count"
    assert count(messages, counter=approved_counter) == 9
    assert 9 != sum(len(text.encode("utf-8")) for _, text in messages)


@pytest.mark.parametrize("tokens", (INPUT_CAP - 1, INPUT_CAP), ids=("under-cap", "at-cap"))
def test_collect_counts_exact_final_messages_before_transport(tmp_path, monkeypatch, tokens):
    ctx, github = workflow_fixture(tmp_path, monkeypatch)
    evaluator = evaluator_module(monkeypatch)
    counted = []

    def approved_counter(messages):
        counted.append(tuple(messages))
        return tokens

    stub_tokenizer(evaluator, monkeypatch, github, lambda: approved_counter)
    provider = ProviderProbe()

    def transport(messages):
        assert tuple(messages) in counted
        provider(messages)

    system_prompt_path = github.report["target"]["system_prompt_path"]
    with pytest.raises(ProviderEntryReached):
        collect(evaluator, ctx, github, transport, system_prompt_path=system_prompt_path)
    assert provider.provider_calls == 1
    assert RUN_ARTIFACTS in github.calls
    final_messages = provider.requests[0]
    assert tuple(role for role, _ in final_messages) == ("system", "user")
    assert final_messages[0][1] == ctx.read(system_prompt_path)
    payload = json.loads(final_messages[1][1])
    assert payload["question"]
    assert payload["approved_evidence"]


@pytest.mark.parametrize(
    "tokens", (INPUT_CAP + 1, 0, -1, None, True, "42", 12.0),
    ids=("over-cap", "zero", "negative", "missing", "boolean", "string", "float"),
)
def test_collect_refuses_unsafe_token_count_before_provider(tmp_path, monkeypatch, tokens):
    ctx, github = workflow_fixture(tmp_path, monkeypatch)
    evaluator = evaluator_module(monkeypatch)
    counted = []

    def approved_counter(messages):
        counted.append(tuple(messages))
        return tokens

    stub_tokenizer(evaluator, monkeypatch, github, lambda: approved_counter)
    provider = ProviderProbe()
    with pytest.raises(ValueError):
        collect(evaluator, ctx, github, provider)
    assert counted
    assert tuple(role for role, _ in counted[0]) == ("system", "user")
    assert provider.provider_calls == 0


@pytest.mark.parametrize("error", (ImportError, RuntimeError, OSError))
@pytest.mark.parametrize("location", ("loader", "counter"))
def test_collect_never_falls_back_when_tokenizer_is_unavailable(
    tmp_path, monkeypatch, error, location,
):
    ctx, github = workflow_fixture(tmp_path, monkeypatch)
    evaluator = evaluator_module(monkeypatch)
    failures = []

    def unavailable(*args):
        failures.append(location)
        raise error("synthetic approved tokenizer unavailable")

    loader = unavailable if location == "loader" else lambda: unavailable
    stub_tokenizer(evaluator, monkeypatch, github, loader)
    provider = ProviderProbe()
    with pytest.raises((ValueError, error)):
        collect(evaluator, ctx, github, provider)
    assert failures
    assert provider.provider_calls == 0


def install_offline_tiktoken(monkeypatch, get_encoding):
    tiktoken = ModuleType("tiktoken")
    tiktoken.get_encoding = get_encoding

    def encoding_for_model(model):
        assert model == TOKENIZER_MODEL
        return tiktoken.get_encoding("o200k_base")

    tiktoken.encoding_for_model = encoding_for_model
    monkeypatch.setitem(sys.modules, "tiktoken", tiktoken)


@pytest.mark.parametrize("entry", ("loader", "collect"))
@pytest.mark.parametrize(
    "error", (ImportError, OSError, RuntimeError), ids=("missing-module", "offline", "load-error"),
)
def test_real_tokenizer_loader_and_collect_reject_tokenizer_failure(
    tmp_path, monkeypatch, entry, error,
):
    ctx, github = workflow_fixture(tmp_path, monkeypatch)
    set_authorization(github, 301, provider=TOKENIZER_PROVIDER, model=TOKENIZER_MODEL)
    encoding_requests = []

    def broken_encoding(name):
        encoding_requests.append(name)
        raise error("synthetic tokenizer encoding unavailable")

    if error is ImportError:
        monkeypatch.setitem(sys.modules, "tiktoken", None)
    else:
        install_offline_tiktoken(monkeypatch, broken_encoding)

    evaluator = evaluator_module(monkeypatch)
    load = approved_tokenizer_loader(evaluator)
    provider = ProviderProbe()
    with pytest.raises((ValueError, error)):
        if entry == "loader":
            load(provider=TOKENIZER_PROVIDER, model=TOKENIZER_MODEL)
        else:
            collect(evaluator, ctx, github, provider)
    if error is not ImportError:
        assert encoding_requests
    assert provider.provider_calls == 0


def test_real_tokenizer_loader_counts_through_encoding_and_includes_framing(tmp_path, monkeypatch):
    ctx, github = workflow_fixture(tmp_path, monkeypatch)
    set_authorization(github, 301, provider=TOKENIZER_PROVIDER, model=TOKENIZER_MODEL)
    system_text, user_text = "规则" * 64, "请回答" * 64
    messages = (("system", system_text), ("user", user_text))
    encoded = []
    encoding_requests = []

    class OfflineEncoding:
        def encode(self, text, **kwargs):
            encoded.append(text)
            return list(range({system_text: 2, user_text: 3}.get(text, 1)))

    def get_encoding(name):
        encoding_requests.append(name)
        return OfflineEncoding()

    install_offline_tiktoken(monkeypatch, get_encoding)
    evaluator = evaluator_module(monkeypatch)
    load = approved_tokenizer_loader(evaluator)
    count = getattr(evaluator, "count_final_request_tokens", None)
    assert callable(count), "IMPLEMENTATION_MISSING: final request token count"
    counter = load(provider=TOKENIZER_PROVIDER, model=TOKENIZER_MODEL)
    tokens = count(messages, counter=counter)
    # Two roles, two contents, three framing tokens per message and a three-token primer.
    assert tokens == 1 + 1 + 2 + 3 + 3 * len(messages) + 3
    assert tokens != sum(len(text.encode("utf-8")) for _, text in messages)
    assert {system_text, user_text} <= set(encoded)
    assert encoding_requests
    encoded.clear()
    provider = ProviderProbe()
    with pytest.raises(ProviderEntryReached):
        collect(evaluator, ctx, github, provider)
    assert provider.provider_calls == 1
    assert all(content in encoded for _, content in provider.requests[0])


def test_collect_defaults_to_repo_system_prompt(monkeypatch):
    evaluator = evaluator_module(monkeypatch)
    collect_stage = getattr(evaluator, "collect", None)
    assert callable(collect_stage), "IMPLEMENTATION_MISSING: collect"
    assert signature(collect_stage).parameters["system_prompt_path"].default == DEFAULT_SYSTEM_PROMPT
    assert (ROOT / DEFAULT_SYSTEM_PROMPT).is_file()


@pytest.mark.parametrize("fault", ("wrong-head", "consumed-review", "untagged-prior-dispatch"))
def test_collect_rechecks_authorization_and_dispatch_history_before_provider(
    tmp_path, monkeypatch, fault,
):
    ctx, github = workflow_fixture(tmp_path, monkeypatch)
    evaluator = evaluator_module(monkeypatch)
    run_id, review_id = 401, 301
    if fault == "untagged-prior-dispatch":
        run_id, review_id = 402, 302
        set_authorization(github, review_id)
        add_fresh_dispatch(github, review_id, prior_conclusion="success")
    stub_tokenizer(
        evaluator, monkeypatch, github, lambda: lambda messages: INPUT_CAP, review_id=review_id,
    )
    assert evaluator.preflight(
        ctx, github, pr_number=20, run_id=run_id, authorization_review_id=review_id,
    )["authorization"]["review_id"] == review_id

    if fault == "wrong-head":
        github.responses[f"{PREFIX}/actions/runs/401"]["head_sha"] = "f" * 40
    elif fault == "consumed-review":
        run_id = 402
        add_fresh_dispatch(github, review_id, prior_conclusion="success")
    else:
        github.responses[f"{PREFIX}/actions/runs/401"]["display_title"] = "manual dispatch"
    github.responses[f"{PREFIX}/actions/runs/{run_id}/artifacts?per_page=100"] = {
        "total_count": 0, "artifacts": [],
    }
    github.calls.clear()

    provider = ProviderProbe()
    with pytest.raises(ValueError):
        collect(evaluator, ctx, github, provider, run_id=run_id, review_id=review_id)
    assert f"{PREFIX}/actions/runs/{run_id}" in github.calls
    if fault != "wrong-head":
        assert DISPATCH_RUNS in github.calls
    assert provider.provider_calls == 0


def rating_fixture(tmp_path, monkeypatch):
    ctx, github = workflow_fixture(tmp_path, monkeypatch)
    ratings = github.report["scores"]["independent_ratings"]
    reviews = github.responses[f"{PREFIX}/pulls/20/reviews?per_page=100"]
    reviews[-1].update(
        state="COMMENTED",
        body="Semantic ratings: " + json.dumps({
            "run_id": 401, "head_sha": ctx.head, "raw_sha256": RAW_HASH, "ratings": ratings,
        }),
    )
    return ctx, github, ratings


def intake(evaluator, ctx, github):
    return evaluator.accept_ratings(
        ctx, github, pr_number=20, run_id=401, raw_sha256=RAW_HASH,
        captured_at="2026-11-13T10:25:00Z",
    )


def test_rating_intake_uses_actual_independent_review(tmp_path, monkeypatch):
    evaluator = evaluator_module(monkeypatch)
    ctx, github, ratings = rating_fixture(tmp_path, monkeypatch)
    adopted = intake(evaluator, ctx, github)
    assert adopted["review_id"] == 302
    assert adopted["reviewer"] == "independent-student"
    assert adopted["ratings"] == ratings


@pytest.mark.parametrize(
    "fault",
    (
        "wrong-hash", "wrong-head", "wrong-run", "self-review", "early",
        "missing", "duplicate", "wrong-rating-identity", "read-only",
    ),
)
def test_intake_rejects_invalid_or_incomplete_human_review(tmp_path, monkeypatch, fault):
    evaluator = evaluator_module(monkeypatch)
    ctx, github, _ = rating_fixture(tmp_path, monkeypatch)
    review = github.responses[f"{PREFIX}/pulls/20/reviews?per_page=100"][-1]
    body = json.loads(review["body"].split(": ", 1)[1])
    if fault == "wrong-hash":
        body["raw_sha256"] = "b" * 64
    elif fault == "wrong-head":
        review["commit_id"] = "f" * 40
    elif fault == "wrong-run":
        body["run_id"] = 402
    elif fault == "duplicate":
        body["ratings"][-1] = body["ratings"][0]
    elif fault == "wrong-rating-identity":
        body["ratings"][0]["reviewer"] = "other-student"
    elif fault == "read-only":
        github.responses[f"{PREFIX}/collaborators/independent-student/permission"] = {
            "permission": "read",
        }
    elif fault == "self-review":
        review["user"]["login"] = "implementer"
    elif fault == "early":
        review["submitted_at"] = "2026-11-13T10:24:00Z"
    elif fault == "missing":
        body["ratings"].pop()
    review["body"] = "Semantic ratings: " + json.dumps(body)
    with pytest.raises(ValueError):
        intake(evaluator, ctx, github)


def test_evaluation_workflow_has_only_manual_dispatch_and_separate_review_stage():
    path = ROOT / ".github/workflows/semantic-evaluation.yml"
    assert path.is_file(), "IMPLEMENTATION_MISSING: evaluation workflow"
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    events = workflow.get("on", workflow.get(True))
    assert isinstance(events, dict)
    assert set(events) == {"workflow_dispatch"}
    assert set(events["workflow_dispatch"]["inputs"]) == {
        "target_pr", "target_head", "authorization_review_id",
    }
    jobs = workflow["jobs"]
    assert set(jobs) == {"preflight", "collect", "finalize"}
    assert jobs["collect"]["needs"] == "preflight"
    assert jobs["finalize"]["needs"] == "collect"
    assert jobs["collect"]["environment"] == "papertrace-evaluation-execution"
    assert jobs["finalize"]["environment"] == "papertrace-independent-rating"
    for job in jobs.values():
        for permission, value in job.get("permissions", workflow.get("permissions", {})).items():
            assert value in {"read", "none"}, permission

    assert_credential_isolation(workflow)
    for name in ("preflight", "finalize"):
        assert "secrets." not in json.dumps(jobs[name])
    for job in jobs.values():
        for step in job["steps"]:
            if "uses" in step:
                assert re.fullmatch(r"[^@]+@[0-9a-f]{40}", step["uses"])
                if step["uses"].startswith("actions/checkout@"):
                    assert step["with"]["persist-credentials"] is False

# The structural validator is itself exercised with synthetic positive and
# mutated workflows, so a missing real workflow cannot hide weak assertions.
def expression(value):
    return "$" + "{{ " + value + " }}"


READ_PERMISSIONS = {
    "contents": "read", "actions": "read", "pull-requests": "read", "issues": "read",
}
STAGE_ENV = {
    "PAPERTRACE_TARGET_PR": expression("inputs.target_pr"),
    "PAPERTRACE_TARGET_HEAD": expression("inputs.target_head"),
    "PAPERTRACE_AUTHORIZATION_REVIEW_ID": expression("inputs.authorization_review_id"),
    "PAPERTRACE_RUN_ID": expression("github.run_id"),
    "PAPERTRACE_RUN_HEAD": expression("github.sha"),
    RUN_ATTEMPT_ENV: expression("github.run_attempt"),
    "GH_TOKEN": expression("github.token"),
}
STAGE_COMMANDS = {
    stage: f"python test/evaluation/evaluator.py {stage}"
    for stage in ("preflight", "collect", "finalize")
}


def assert_workflow_wiring(workflow):
    assert_credential_isolation(workflow)
    jobs = workflow["jobs"]
    assert set(jobs) == set(STAGE_COMMANDS)
    assert jobs["collect"]["needs"] == "preflight"
    assert jobs["finalize"]["needs"] == "collect"
    # Default successful dependency semantics, not always()/failure() bypasses.
    assert "if" not in workflow
    for name, job in jobs.items():
        assert "if" not in job
        assert job.get("continue-on-error", False) is False
        assert job.get("permissions", workflow.get("permissions")) == READ_PERMISSIONS
        steps = job["steps"]
        checkouts = [
            (index, step) for index, step in enumerate(steps)
            if step.get("uses", "").startswith("actions/checkout@")
        ]
        assert len(checkouts) == 1
        checkout_index, checkout = checkouts[0]
        assert checkout["with"].get("ref") == expression("github.sha")
        assert checkout["with"]["persist-credentials"] is False
        assert "repository" not in checkout["with"]
        assert "path" not in checkout["with"]
        stage_steps = [
            (index, step) for index, step in enumerate(steps)
            if step.get("run") == STAGE_COMMANDS[name]
        ]
        assert len(stage_steps) == 1, name
        stage_index, stage_step = stage_steps[0]
        assert checkout_index < stage_index
        assert stage_step.get("if") is None
        assert stage_step.get("continue-on-error", False) is False
        assert "working-directory" not in stage_step
        assert not job.get("defaults", {}).get("run", {}).get("working-directory")
        assert not workflow.get("defaults", {}).get("run", {}).get("working-directory")
        assert all(stage_step.get("env", {}).get(key) == value for key, value in STAGE_ENV.items())
        for step in steps:
            # No Actions expression is allowed in shell source (including
            # alternate contexts); untrusted inputs enter only via env.
            assert "$" + "{{" not in step.get("run", "")
            assert step.get("continue-on-error", False) is False
            if "uses" in step:
                assert re.fullmatch(r"[^@]+@[0-9a-f]{40}", step["uses"])
    assert jobs["collect"]["environment"] == "papertrace-evaluation-execution"
    assert jobs["finalize"]["environment"] == "papertrace-independent-rating"


def synthetic_wired_workflow():
    workflow = {"permissions": dict(READ_PERMISSIONS), "jobs": {}}
    for stage, command in STAGE_COMMANDS.items():
        workflow["jobs"][stage] = {
            "steps": [
                {
                    "uses": "actions/checkout@" + "a" * 40,
                    "with": {"ref": expression("github.sha"), "persist-credentials": False},
                },
                {"run": command, "env": dict(STAGE_ENV)},
            ],
        }
    workflow["jobs"]["collect"].update(
        needs="preflight", environment="papertrace-evaluation-execution",
    )
    workflow["jobs"]["finalize"].update(
        needs="collect", environment="papertrace-independent-rating",
    )
    return workflow


def test_structural_contract_accepts_synthetic_exact_wiring():
    assert_workflow_wiring(synthetic_wired_workflow())


@pytest.mark.parametrize("stage", tuple(STAGE_COMMANDS))
@pytest.mark.parametrize("binding", (None, "1"), ids=("omitted", "hardcoded"))
def test_structural_contract_rejects_untrusted_run_attempt(stage, binding):
    workflow = synthetic_wired_workflow()
    env = workflow["jobs"][stage]["steps"][-1]["env"]
    if binding is None:
        del env[RUN_ATTEMPT_ENV]
    else:
        env[RUN_ATTEMPT_ENV] = binding
    with pytest.raises(AssertionError):
        assert_workflow_wiring(workflow)


def assert_budget_guard_wiring(workflow):
    assert re.search(
        r"\$\{\{\s*inputs\.authorization_review_id\s*\}\}", workflow.get("run-name", ""),
    ), "Workflow run-name must bind the authorization review ID"
    for stage in ("preflight", "collect"):
        steps = [
            step for step in workflow["jobs"][stage]["steps"]
            if step.get("run") == STAGE_COMMANDS[stage]
        ]
        assert len(steps) == 1, stage
        for name in TARIFF_ENV:
            assert steps[0].get("env", {}).get(name) == expression(f"vars.{name}"), (stage, name)


def synthetic_budget_guard_workflow():
    workflow = synthetic_wired_workflow()
    workflow["run-name"] = "auth-" + expression("inputs.authorization_review_id")
    for stage in ("preflight", "collect"):
        workflow["jobs"][stage]["steps"][-1]["env"].update({
            name: expression(f"vars.{name}") for name in TARIFF_ENV
        })
    return workflow


def test_workflow_budget_guard_accepts_synthetic_wiring():
    workflow = synthetic_budget_guard_workflow()
    assert_workflow_wiring(workflow)
    assert_budget_guard_wiring(workflow)


@pytest.mark.parametrize("run_name", (None, "auth-301", "auth-" + expression("inputs.target_pr")))
def test_workflow_budget_guard_rejects_unbound_run_name(run_name):
    workflow = synthetic_budget_guard_workflow()
    if run_name is None:
        del workflow["run-name"]
    else:
        workflow["run-name"] = run_name
    with pytest.raises(AssertionError, match="run-name"):
        assert_budget_guard_wiring(workflow)


@pytest.mark.parametrize("stage", ("preflight", "collect"))
@pytest.mark.parametrize("name", TARIFF_ENV, ids=("input", "output"))
def test_workflow_budget_guard_rejects_missing_tariff_binding(stage, name):
    workflow = synthetic_budget_guard_workflow()
    del workflow["jobs"][stage]["steps"][-1]["env"][name]
    with pytest.raises(AssertionError, match=name):
        assert_budget_guard_wiring(workflow)


def test_actual_workflow_wires_budget_guards():
    path = ROOT / ".github/workflows/semantic-evaluation.yml"
    assert path.is_file(), "IMPLEMENTATION_MISSING: evaluation workflow"
    assert_budget_guard_wiring(yaml.safe_load(path.read_text(encoding="utf-8")))


@pytest.mark.parametrize(
    "fault",
    (
        "missing-permissions", "write-permissions", "empty-permissions",
        "missing-checkout", "branch-checkout", "missing-ref", "wrong-repo",
        "missing-preflight", "missing-collect", "missing-finalize",
        "missing-authorization-env", "wrong-head-env", "shell-input",
        "shell-event-input", "bypass-dependency", "ignore-stage-failure",
        "skip-stage", "wrong-directory",
    ),
)
def test_structural_contract_rejects_unsafe_synthetic_wiring(fault):
    workflow = synthetic_wired_workflow()
    jobs = workflow["jobs"]
    stage = jobs["collect"]["steps"][-1]
    checkout = jobs["collect"]["steps"][0]
    if fault == "missing-permissions":
        del workflow["permissions"]
    elif fault == "write-permissions":
        jobs["collect"]["permissions"] = {"contents": "write"}
    elif fault == "empty-permissions":
        jobs["collect"]["permissions"] = {}
    elif fault == "missing-checkout":
        jobs["collect"]["steps"].pop(0)
    elif fault == "branch-checkout":
        checkout["with"]["ref"] = "main"
    elif fault == "missing-ref":
        del checkout["with"]["ref"]
    elif fault == "wrong-repo":
        checkout["with"]["repository"] = "other/repository"
    elif fault.startswith("missing-") and fault[8:] in jobs:
        jobs[fault[8:]]["steps"].pop()
    elif fault == "missing-authorization-env":
        del stage["env"]["PAPERTRACE_AUTHORIZATION_REVIEW_ID"]
    elif fault == "wrong-head-env":
        stage["env"]["PAPERTRACE_TARGET_HEAD"] = "main"
    elif fault == "shell-input":
        jobs["collect"]["steps"].append({"run": "echo " + expression("inputs.target_head")})
    elif fault == "shell-event-input":
        jobs["collect"]["steps"].append({
            "run": "echo " + expression("github.event.inputs.target_pr"),
        })
    elif fault == "bypass-dependency":
        jobs["collect"]["if"] = expression("always()")
    elif fault == "ignore-stage-failure":
        stage["continue-on-error"] = True
    elif fault == "skip-stage":
        stage["if"] = False
    elif fault == "wrong-directory":
        stage["working-directory"] = "untrusted"
    else:
        pytest.fail(f"Unknown synthetic mutation: {fault}")
    with pytest.raises(AssertionError):
        assert_workflow_wiring(workflow)


def test_real_workflow_uses_exact_authorization_and_rating_cli_wiring():
    path = ROOT / ".github/workflows/semantic-evaluation.yml"
    assert path.is_file(), "IMPLEMENTATION_MISSING: evaluation workflow"
    assert_workflow_wiring(yaml.safe_load(path.read_text(encoding="utf-8")))


# Only the fixed collect command may receive a provider credential. Inspect
# the whole YAML tree, not just job-local env; global env is inherited.
PROVIDER_ENV = "PAPERTRACE_PROVIDER_API_KEY"
PROVIDER_SECRET = expression("secrets.PAPERTRACE_EVALUATION_API_KEY")


def assert_credential_isolation(workflow):
    collect = workflow["jobs"]["collect"]
    assert collect["environment"] == "papertrace-evaluation-execution"
    collect_steps = collect["steps"]
    allowed = [
        index for index, step in enumerate(collect_steps)
        if step.get("run") == STAGE_COMMANDS["collect"]
    ]
    # A missing stage is rejected by the wiring assertion; no secret may
    # appear anywhere when no unique approved collect command exists.
    allowed_path = (
        ("jobs", "collect", "steps", allowed[0], "env", PROVIDER_ENV)
        if len(allowed) == 1 else None
    )

    def visit(value, path=()):
        if isinstance(value, dict):
            for key, child in value.items():
                assert not (
                    isinstance(key, str) and "$" + "{{" in key
                ), "Dynamic YAML keys cannot establish credential isolation"
                if key == PROVIDER_ENV:
                    assert (*path, key) == allowed_path, "Provider env outside collect command"
                    assert child == PROVIDER_SECRET, "Unapproved provider credential binding"
                visit(child, (*path, key))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, (*path, index))
        elif isinstance(value, str):
            # Conservatively reject any secrets-context expression (including
            # bracket syntax, mixed case and toJSON) outside the exact leaf.
            if "$" + "{{" in value and re.search(r"\bsecrets\b", value, re.IGNORECASE):
                assert path == allowed_path, "Secret reference outside collect command"
                assert value == PROVIDER_SECRET, "Unapproved provider credential binding"

    visit(workflow)


def test_collect_only_provider_credential_is_valid():
    workflow = synthetic_wired_workflow()
    workflow["jobs"]["collect"]["steps"][-1]["env"][PROVIDER_ENV] = PROVIDER_SECRET
    assert_workflow_wiring(workflow)


@pytest.mark.parametrize(
    "fault",
    (
        "global-env", "global-bracket", "global-secrets-object",
        "preflight-job-env", "finalize-job-env", "preflight-step-env",
        "finalize-action-input", "collect-job-env", "collect-checkout-input",
        "collect-other-step", "collect-output", "wrong-secret",
        "provider-env-global", "provider-env-finalize",
    ),
)
def test_provider_credentials_cannot_escape_collect_command(fault):
    workflow = synthetic_wired_workflow()
    jobs = workflow["jobs"]
    stage = jobs["collect"]["steps"][-1]
    stage["env"][PROVIDER_ENV] = PROVIDER_SECRET
    diagnostic = expression("secrets.DIAGNOSTIC_PROVIDER_KEY")
    if fault == "global-env":
        workflow["env"] = {"DIAGNOSTIC_PROVIDER_KEY": diagnostic}
    elif fault == "global-bracket":
        workflow["env"] = {"LEAK": expression("secrets['DIAGNOSTIC_PROVIDER_KEY']")}
    elif fault == "global-secrets-object":
        workflow["env"] = {"LEAK": expression("toJSON(SeCrEtS)")}
    elif fault == "preflight-job-env":
        jobs["preflight"]["env"] = {"LEAK": diagnostic}
    elif fault == "finalize-job-env":
        jobs["finalize"]["env"] = {"LEAK": diagnostic}
    elif fault == "preflight-step-env":
        jobs["preflight"]["steps"][-1]["env"]["LEAK"] = diagnostic
    elif fault == "finalize-action-input":
        jobs["finalize"]["steps"][0]["with"]["token"] = diagnostic
    elif fault == "collect-job-env":
        jobs["collect"]["env"] = {"LEAK": diagnostic}
    elif fault == "collect-checkout-input":
        jobs["collect"]["steps"][0]["with"]["token"] = diagnostic
    elif fault == "collect-other-step":
        jobs["collect"]["steps"].append({"run": "echo safe", "env": {"LEAK": diagnostic}})
    elif fault == "collect-output":
        jobs["collect"]["outputs"] = {"leak": diagnostic}
    elif fault == "wrong-secret":
        stage["env"][PROVIDER_ENV] = diagnostic
    elif fault == "provider-env-global":
        workflow["env"] = {PROVIDER_ENV: "synthetic-not-a-real-key"}
    elif fault == "provider-env-finalize":
        jobs["finalize"]["steps"][-1]["env"][PROVIDER_ENV] = "synthetic-not-a-real-key"
    else:
        pytest.fail(f"Unknown synthetic mutation: {fault}")
    with pytest.raises(AssertionError):
        assert_workflow_wiring(workflow)
