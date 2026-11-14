"""GOV-02: synthetic GitHub/artifact fixtures, NEVER real model or student evidence."""

import importlib.util
import io
import json
import subprocess
import zipfile
from hashlib import sha256
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def module():
    path = ROOT / "scripts/semantic_evidence.py"
    assert path.exists(), "GOV-02: executable semantic evidence verifier is missing"
    spec = importlib.util.spec_from_file_location("papertrace_semantic_fixture", path)
    assert spec is not None and spec.loader is not None
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=True).stdout


class Context:
    repository = "537Lab/PaperTrace"

    def __init__(self, root, base=None, head=None, changed=None):
        self.root, self.base, self.head = root, base, head
        self.changed = changed or []

    def git(self, *args):
        return git(self.root, *args)

    def changes(self):
        return self.changed

    def read(self, path, ref=None):
        return self.git("show", f"{ref or self.head}:{path}").decode()


class SyntheticGitHub:
    def __init__(self, responses, report):
        self.responses, self.report, self.calls = responses, report, []
        self.pack()

    def get(self, route):
        self.calls.append(route)
        assert route in self.responses, f"Unexpected fixture route: {route}"
        return self.responses[route]

    def pack(self):
        self.raw = json.dumps(self.report, ensure_ascii=False, sort_keys=True).encode()
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("evaluation-report.json", self.raw)
        self.archive = stream.getvalue()
        artifact = self.responses["/repos/537Lab/PaperTrace/actions/artifacts/501"]
        artifact["digest"] = "sha256:" + sha256(self.archive).hexdigest()
        self.responses["/repos/537Lab/PaperTrace/pulls/20/reviews?per_page=100"][-1]["body"] = "Semantic report SHA256: " + sha256(self.raw).hexdigest()

    def download_artifact(self, artifact_id):
        assert artifact_id == 501
        return self.archive


def fixture(tmp_path):
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.name", "Synthetic semantic fixture")
    git(tmp_path, "config", "user.email", "fixture@example.invalid")
    for name in ("test/evaluation/cases.json", "test/evaluation/report-schema.json"):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / name).read_bytes())
    for name, content in {".github/workflows/evaluate.yml": "# Synthetic workflow text, not an actual evaluation\n", "test/evaluation/evaluator.py": "# Synthetic evaluator blob, not executed\n", "prompts/runtime.txt": "old synthetic prompt\n", "src/example.py": "VALUE = 1\n"}.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "synthetic trusted control base")
    base = git(tmp_path, "rev-parse", "HEAD").decode().strip()
    (tmp_path / "prompts/runtime.txt").write_text("new synthetic prompt\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "synthetic prompt change")
    head = git(tmp_path, "rev-parse", "HEAD").decode().strip()
    ctx = Context(tmp_path, base, head, ["prompts/runtime.txt"])
    dataset_bytes = (tmp_path / "test/evaluation/cases.json").read_bytes()
    dataset = json.loads(dataset_bytes)
    auth = {"review_id": 301, "provider": "provider-a", "model": "model-a", "model_version": "version-a", "data_scope": "fixed self-authored synthetic cases", "max_calls": 18, "max_cost": 1.0, "currency": "USD", "timeout_seconds": 30}
    report = {
        "schema_version": 2,
        "provenance": {"repository": "537Lab/PaperTrace", "run_id": 401, "artifact_id": 501},
        "target": {"head_sha": head, "source_tree_sha": git(tmp_path, "rev-parse", f"{head}:src").decode().strip(), "test_tree_sha": git(tmp_path, "rev-parse", f"{head}:test").decode().strip(), "evaluator_path": "test/evaluation/evaluator.py", "evaluator_sha": git(tmp_path, "rev-parse", f"{head}:test/evaluation/evaluator.py").decode().strip(), "dataset_sha256": sha256(dataset_bytes).hexdigest(), "prompt_sha256": sha256(git(tmp_path, "ls-tree", "-r", head, "--", "prompts")).hexdigest(), "model_config_sha256": sha256(git(tmp_path, "ls-tree", "-r", head, "--", "src/papertrace/retrieval", "src/papertrace/answer", "src/paperqa", "pyproject.toml", "uv.lock")).hexdigest()},
        "authorization": auth,
        "deterministic_results": [], "runs": [],
        "scores": {"deterministic_safety_escapes": 0, "citation_precision": 1.0, "unsupported_claim_ratio": 0.0, "rubric_completion_ratio": 1.0, "mean_relevance_1_to_5": 4.5, "injection_successes": 0, "independent_ratings": []},
    }
    for case in dataset["cases"]:
        if case["kind"] == "deterministic":
            report["deterministic_results"].append({"case_id": case["id"], "actual": case["oracle"]})
            continue
        for repeat in range(1, 4):
            sent = [item["id"] for item in case["input"]["approved_evidence"]]
            request = [{"role": "system", "content": "Synthetic request for verifier tests, not a real provider call"}, {"role": "user", "content": json.dumps({"question": case["input"]["question"], "approved_evidence": case["input"]["approved_evidence"]}, ensure_ascii=False)}]
            response = {"request_id": f"fixture-{case['id']}-{repeat}", "model": auth["model"], "model_version": auth["model_version"], "content": "Synthetic validator fixture reply " + " ".join(f"[{item}]" for item in sent), "finish_reason": "stop", "usage": {"input_tokens": 20, "output_tokens": 10, "total_tokens": 30}}
            report["runs"].append({"case_id": case["id"], "repeat": repeat, "provider": auth["provider"], "model": auth["model"], "model_version": auth["model_version"], "input_sha256": sha256(canonical(case["input"])).hexdigest(), "prompt_sha256": sha256(canonical(request)).hexdigest(), "request": request, "sent_ids": sent, "cited_ids": sent, "started_at": "2026-11-13T10:21:00Z", "finished_at": "2026-11-13T10:21:01Z", "content": response["content"], "finish_reason": "stop", "usage": response["usage"], "attempts": 1, "cost": 0.01, "response": response, "response_sha256": sha256(canonical(response)).hexdigest()})
            rubric_items = len(case["rubric"].get("must_include", [])) + len(case["rubric"].get("must_not_include", []))
            report["scores"]["independent_ratings"].append({"case_id": case["id"], "repeat": repeat, "reviewer": "independent-student", "citation_count": len(sent), "correct_citations": len(sent), "claim_count": 2, "unsupported_claims": 0, "rubric_items": rubric_items, "rubric_met": rubric_items, "relevance": 4.5, "safety_escapes": 0, "injection_successes": 0, "rationale": "Synthetic fixture rationale, not an actual human rating"})
    current = {"number": 20, "state": "open", "merged": False, "created_at": "2026-11-13T10:10:00Z", "user": {"login": "implementer"}, "body": "Semantic evaluation run: 401\nSemantic evaluation artifact: 501", "base": {"sha": base, "repo": {"full_name": "537Lab/PaperTrace"}}, "head": {"sha": head, "repo": {"full_name": "537Lab/PaperTrace"}}}
    responses = {
        "/repos/537Lab/PaperTrace/pulls/20": current,
        "/repos/537Lab/PaperTrace/pulls/20/reviews?per_page=100": [
            {"id": 301, "state": "APPROVED", "commit_id": head, "submitted_at": "2026-11-13T10:20:00Z", "user": {"login": "independent-student", "type": "User"}, "body": "Evaluation authorization: " + json.dumps(dict(auth, dataset_sha256=report["target"]["dataset_sha256"]))},
            {"id": 302, "state": "APPROVED", "commit_id": head, "submitted_at": "2026-11-13T10:30:00Z", "user": {"login": "independent-student", "type": "User"}, "body": "filled by pack"},
        ],
        "/repos/537Lab/PaperTrace/issues/20/events?per_page=100": [],
        "/repos/537Lab/PaperTrace/pulls/20/commits?per_page=100": [{"author": {"login": "implementer", "type": "User"}, "committer": {"login": "implementer", "type": "User"}}],
        "/repos/537Lab/PaperTrace/collaborators/independent-student/permission": {"permission": "write"},
        "/repos/537Lab/PaperTrace/actions/runs/401": {"id": 401, "event": "workflow_dispatch", "status": "completed", "conclusion": "success", "head_sha": head, "path": ".github/workflows/evaluate.yml", "created_at": "2026-11-13T10:20:30Z", "updated_at": "2026-11-13T10:25:00Z", "repository": {"full_name": "537Lab/PaperTrace"}},
        "/repos/537Lab/PaperTrace/actions/artifacts/501": {"id": 501, "name": "papertrace-semantic", "expired": False, "workflow_run": {"id": 401, "head_sha": head}},
    }
    return ctx, SyntheticGitHub(responses, report)


def test_docs_coding_rules_and_deterministic_export_changes_need_no_fake_llm_evaluation():
    for changed in (["docs/readme.md"], ["AGENTS.md", "Prompt.md", "opencode.jsonc"], ["src/papertrace/reports/view.py"]):
        assert module().verify_semantic(Context(ROOT, changed=changed))["status"] == "NOT_REQUIRED"


def test_prompt_change_without_live_pr_is_blocked():
    assert module().verify_semantic(Context(ROOT, changed=["prompts/runtime.txt"]))["status"] == "BLOCKED"


def test_complete_verified_artifact_and_independent_ratings_can_pass(tmp_path):
    ctx, github = fixture(tmp_path)
    report = module().verify_semantic(ctx, github=github, pr_number=20)
    assert report["status"] == "PASS", report
    assert report["details"]["real_model_runs"] == 18
    assert report["details"]["independent_reviewer"] == "independent-student"


@pytest.mark.parametrize("fault", ["wrong-head", "missing-case", "duplicate-case", "citation-threshold", "unsupported-threshold", "rubric-threshold", "relevance-threshold", "safety-escape", "injection-success", "truncated", "expired", "digest", "self-review", "late-budget", "wrong-review-hash", "coauthor-review"])
def test_invalid_real_evaluation_evidence_is_rejected(tmp_path, fault):
    """GOV-02: fixtures test evidence logic, not fake a real evaluation result."""
    ctx, github = fixture(tmp_path)
    report = github.report
    ratings = report["scores"]["independent_ratings"]
    first = report["runs"][0]
    if fault == "wrong-head":
        report["target"]["head_sha"] = "f" * 40
    elif fault == "missing-case":
        report["runs"].pop()
    elif fault == "duplicate-case":
        report["runs"][-1]["case_id"], report["runs"][-1]["repeat"] = first["case_id"], first["repeat"]
    elif fault == "citation-threshold":
        ratings[0]["correct_citations"] = 0
        report["scores"]["citation_precision"] = sum(item["correct_citations"] for item in ratings) / sum(item["citation_count"] for item in ratings)
    elif fault == "unsupported-threshold":
        ratings[0]["unsupported_claims"] = ratings[0]["claim_count"]
        report["scores"]["unsupported_claim_ratio"] = sum(item["unsupported_claims"] for item in ratings) / sum(item["claim_count"] for item in ratings)
    elif fault == "rubric-threshold":
        for rating in ratings:
            rating["rubric_met"] = 0
        report["scores"]["rubric_completion_ratio"] = 0
    elif fault == "relevance-threshold":
        for rating in ratings:
            rating["relevance"] = 3.5
        report["scores"]["mean_relevance_1_to_5"] = 3.5
    elif fault == "safety-escape":
        ratings[0]["safety_escapes"] = 1
        report["scores"]["deterministic_safety_escapes"] = 1
    elif fault == "injection-success":
        ratings[0]["injection_successes"] = 1
        report["scores"]["injection_successes"] = 1
    elif fault == "truncated":
        first["finish_reason"] = first["response"]["finish_reason"] = "length"
        first["response_sha256"] = sha256(canonical(first["response"])).hexdigest()
    elif fault == "expired":
        github.responses["/repos/537Lab/PaperTrace/actions/artifacts/501"]["expired"] = True
    elif fault == "self-review":
        github.responses["/repos/537Lab/PaperTrace/pulls/20/reviews?per_page=100"][-1]["user"]["login"] = "implementer"
    elif fault == "coauthor-review":
        github.responses["/repos/537Lab/PaperTrace/pulls/20/commits?per_page=100"][0]["author"]["login"] = "independent-student"
    elif fault == "late-budget":
        github.responses["/repos/537Lab/PaperTrace/pulls/20/reviews?per_page=100"][0]["submitted_at"] = "2026-11-13T10:22:00Z"
    github.pack()
    if fault == "digest":
        github.responses["/repos/537Lab/PaperTrace/actions/artifacts/501"]["digest"] = "sha256:" + "0" * 64
    if fault == "wrong-review-hash":
        github.responses["/repos/537Lab/PaperTrace/pulls/20/reviews?per_page=100"][-1]["body"] = "Semantic report SHA256: " + "0" * 64
    checked = module().verify_semantic(ctx, github=github, pr_number=20)
    assert checked["status"] == "FAIL", checked
    if fault.endswith("threshold") or fault in {"safety-escape", "injection-success"}:
        assert checked["details"]["reason"] == "frozen-quality-threshold-failed"


def test_candidate_evaluation_workflow_cannot_certify_itself(tmp_path):
    ctx, github = fixture(tmp_path)
    (tmp_path / ".github/workflows/evaluate.yml").write_text("# Changed candidate workflow\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "synthetic candidate changed evaluator workflow")
    ctx.head = git(tmp_path, "rev-parse", "HEAD").decode().strip()
    github.responses["/repos/537Lab/PaperTrace/pulls/20"]["head"]["sha"] = ctx.head
    github.responses["/repos/537Lab/PaperTrace/actions/runs/401"]["head_sha"] = ctx.head
    checked = module().verify_semantic(ctx, github=github, pr_number=20)
    assert checked["status"] == "FAIL"
    assert checked["details"]["reason"] == "evaluation-workflow-not-pinned-to-trusted-base"
