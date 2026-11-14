"""GOV-01..04 / INV-06: real local fault injection, not production approval.

Git histories below are synthetic disposable fixtures, never student records.
"""

import json
import subprocess
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]


def gates_module():
    """A missing gate is an intentional assertion in the first RED cycle."""
    path = ROOT / "scripts/gates.py"
    assert path.is_file(), "GOV-02: executable gates implementation is missing"
    spec = spec_from_file_location("papertrace_gates", path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def git(root, *args):
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
        env={"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": str(root)},
    )
    return result.stdout.strip()


def put(root, name, text):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def repository(tmp_path):
    """Use our actual registry/schema in an isolated, credential-free Git tree."""
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.name", "Synthetic CI fixture")
    git(tmp_path, "config", "user.email", "fixture@example.invalid")
    for name in (
        "docs/req/requirements.yaml", "docs/req/req-schema.json",
        "src/paperqa/docs.py", "src/paperqa/types.py",
    ):
        put(tmp_path, name, (ROOT / name).read_text(encoding="utf-8"))
    put(tmp_path, "src/paperqa/frozen.py", '"""Synthetic upstream byte fixture."""\n')
    put(tmp_path, "tests/frozen.txt", "upstream suite placeholder, not executed\n")
    put(tmp_path, "packages/frozen.txt", "upstream package placeholder\n")
    put(tmp_path, "pyproject.toml", "[project]\nname = 'synthetic-fixture'\n")
    put(tmp_path, "uv.lock", "version = 1\n")
    put(tmp_path, "LICENSE", "Synthetic baseline license\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "Synthetic test baseline only")
    return tmp_path, git(tmp_path, "rev-parse", "HEAD")


def context(repository, **kwargs):
    root, base = repository
    return gates_module().GateContext(root=root, base=base, baseline=base, **kwargs)


def test_schema_accepts_real_registry_and_rejects_injected_errors(repository):
    """GOV-02 / D1: schema, duplicate identity and zero-tolerance invariants."""
    root, _ = repository
    module = gates_module()
    ctx = context(repository)
    assert module.schema_gate(ctx)["status"] == "PASS"
    path = root / "docs/req/requirements.yaml"
    original = yaml.safe_load(path.read_text(encoding="utf-8"))
    broken = json.loads(json.dumps(original))
    broken["requirements"][0]["priority"] = "unbounded"
    path.write_text(yaml.safe_dump(broken, allow_unicode=True), encoding="utf-8")
    assert module.schema_gate(ctx)["status"] == "FAIL"
    broken = json.loads(json.dumps(original))
    broken["requirements"][1]["id"] = broken["requirements"][0]["id"]
    path.write_text(yaml.safe_dump(broken, allow_unicode=True), encoding="utf-8")
    assert module.schema_gate(ctx)["status"] == "FAIL"
    broken = json.loads(json.dumps(original))
    invariant = next(row for row in broken["requirements"] if row["type"] == "invariant")
    invariant["fit_criterion"].update(operator="<=", threshold=1)
    path.write_text(yaml.safe_dump(broken, allow_unicode=True), encoding="utf-8")
    assert module.schema_gate(ctx)["status"] == "FAIL"


def ai_entry(entry_id="synthetic-test-entry"):
    """GOV-03: synthetic disclosure fixture, never an approval assertion."""
    return {
        "entry_id": entry_id, "timestamp": "2026-01-01T00:00:00Z",
        "tool": "synthetic-fixture", "model": "none", "purpose": "test the log gate " + entry_id,
        "scope": ["src/papertrace/example.py"], "status": "fixture-only",
        "approvals": [], "verification": ["unit-test"], "limitations": ["not real AI use"],
    }


def write_log(root, entries):
    return put(root, "docs/ai-use-log.yaml", yaml.safe_dump({"schema_version": 1, "entries": entries}))


def test_ai_log_requires_new_semantic_entry_for_code_or_prompt_change(repository):
    """GOV-03 / p10 gate6: absence, same log, reordering, then a legal new entry."""
    root, _ = repository
    module = gates_module()
    put(root, "src/papertrace/example.py", 'VALUE = "synthetic"\n')
    assert module.ai_log_gate(context(repository))["status"] == "FAIL"
    first, second = ai_entry("fixture-1"), ai_entry("fixture-2")
    write_log(root, [first, second])
    git(root, "add", ".")
    git(root, "commit", "-qm", "Synthetic disclosure baseline")
    base = git(root, "rev-parse", "HEAD")
    ctx = context((root, base))
    put(root, "src/papertrace/example.py", 'VALUE = "changed synthetic"\n')
    assert module.ai_log_gate(ctx)["status"] == "FAIL"
    write_log(root, [second, first])
    assert module.ai_log_gate(ctx)["status"] == "FAIL"
    write_log(root, [second, first, ai_entry("fixture-3")])
    assert module.ai_log_gate(ctx)["status"] == "PASS"
    put(root, "Prompt.md", "Synthetic changed prompt, not a real agent instruction.\n")
    write_log(root, [first, second])
    assert module.ai_log_gate(ctx)["status"] == "FAIL"
    write_log(root, [first, second, ai_entry("fixture-3")])
    assert module.ai_log_gate(ctx)["status"] == "PASS"
    git(root, "add", ".")
    git(root, "commit", "-qm", "Synthetic head")
    head = git(root, "rev-parse", "HEAD")
    write_log(root, [])
    assert module.ai_log_gate(context((root, base), head=head))["status"] == "PASS"
    assert module.ai_log_gate(ctx)["status"] == "FAIL"


def test_architecture_and_frozen_tree_faults(repository):
    """INV-06 / GOV-02: imports cannot escape B; preserve original suite bytes."""
    root, _ = repository
    module = gates_module()
    ctx = context(repository)
    assert module.frozen_check(ctx)["status"] == "PASS"
    put(root, "src/paperqa/frozen.py", "UPSTREAM_MUTATED = True\n")
    assert module.frozen_check(ctx)["status"] == "FAIL"
    git(root, "restore", "src/paperqa/frozen.py")
    (root / "tests/frozen.txt").unlink()
    assert module.frozen_check(ctx)["status"] == "FAIL"
    git(root, "restore", "tests/frozen.txt")
    put(root, "src/paperqa/extra.py", "EXTRA = True\n")
    assert module.frozen_check(ctx)["status"] == "FAIL"
    (root / "src/paperqa/extra.py").unlink()
    assert module.architecture_check(ctx)["status"] == "PASS"
    for source in (
        "import paperqa\n", "from paperqa.docs import Docs\n",
        'import importlib as loader\nloader.import_module("paperqa")\n',
        'from importlib import import_module as load\nload("paper" + "qa")\n',
        '__import__("paperqa")\n',
    ):
        put(root, "src/papertrace/review.py", source)
        assert module.architecture_check(ctx)["status"] == "FAIL", source
    (root / "src/papertrace/review.py").unlink()
    put(root, "src/papertrace/retrieval/adapter.py", "from paperqa.docs import Docs\n")
    assert module.architecture_check(ctx)["status"] == "PASS"
    put(root, "LICENSE", "Synthetic unauthorized license replacement\n")
    assert module.frozen_check(ctx)["status"] == "FAIL"


def test_real_build_metadata_does_not_break_frozen_source_integrity(repository):
    """GOV-02: build artifacts are not upstream source changes; arbitrary files still fail."""
    root, _ = repository
    put(root, ".gitignore", "src/paperqa/version.py\n*.egg-info/\n")
    put(root, "src/paperqa/version.py", '__version__ = "1.0+synthetic-build"\n')
    put(root, "packages/paper-qa-pypdf/src/paper_qa_pypdf.egg-info/PKG-INFO", "Synthetic metadata\n")
    assert gates_module().frozen_check(context(repository))["status"] == "PASS"
    put(root, "packages/paper-qa-pypdf/src/paper_qa_pypdf.egg-info/sneaky.py", "UNAPPROVED = True\n")
    assert gates_module().frozen_check(context(repository))["status"] == "FAIL"


def test_real_lint_type_dependency_and_timeout_faults(repository):
    """GOV-02: installed tools catch real syntax/types/pin drift, with bounded work."""
    root, _ = repository
    module = gates_module()
    ctx = context(repository)
    put(root, "papertrace.ruff.toml", '[lint]\nselect = ["E4", "E7", "E9", "F"]\n')
    put(root, "mypy.ini", "[mypy]\ncheck_untyped_defs = True\n")
    put(root, "test/offline/test_fixture.py", "def test_fixture():\n    assert True\n")
    put(root, "scripts/fixture.py", "VALUE = 1\n")
    source = put(root, "src/papertrace/example.py", "VALUE: int = 1\n")
    assert module.tool_check(ctx, "lint")["status"] == "PASS"
    source.write_text("import os\nVALUE: int = 1\n", encoding="utf-8")
    assert module.tool_check(ctx, "lint")["status"] == "FAIL"
    source.write_text('VALUE: int = "wrong"\n', encoding="utf-8")
    assert module.tool_check(ctx, "types")["status"] == "FAIL"
    source.write_text("VALUE: int = 1\n", encoding="utf-8")
    assert module.tool_check(ctx, "types")["status"] == "PASS"
    lock = put(root, "requirements-init.lock", (ROOT / "requirements-init.lock").read_text(encoding="utf-8"))
    assert module.dependencies_check(ctx)["status"] == "PASS"
    lock.write_text("pytest==0.0.0\n", encoding="utf-8")
    assert module.dependencies_check(ctx)["status"] == "FAIL"
    timed = module.run_command(context(repository, timeout=0.05), [sys.executable, "-c", "import time; time.sleep(2)"])
    assert timed["status"] == "BLOCKED"
    assert module.run_command(ctx, [sys.executable, "-c", "raise SystemExit(7)"])["status"] == "FAIL"
    assert module.run_command(ctx, [sys.executable, "-c", "pass"])["status"] == "PASS"


def test_contract_surface_and_scoped_secret_faults(repository):
    """SEC-01 / GOV-02: five contract classes; diagnostics never echo secrets."""
    root, _ = repository
    module = gates_module()
    ctx = context(repository)
    assert module.contract_check(ctx)["status"] == "FAIL"
    models = ("CorpusSnapshot", "EvidenceRecord", "ReviewDecision", "AnswerDraft", "ReleaseDecision")
    put(root, "src/papertrace/contracts.py", "\n".join(f"class {name}:\n    pass\n" for name in models))
    assert module.contract_check(ctx)["status"] == "PASS"
    assert module.secret_check(ctx)["status"] == "PASS"
    synthetic = "sk-" + "SYNTHETIC" * 5
    put(root, "src/papertrace/synthetic_secret.py", 'api_key = "' + synthetic + '"\n')
    report = module.secret_check(ctx)
    assert report["status"] == "FAIL"
    assert synthetic not in json.dumps(report)


def test_approval_and_semantic_reports_cannot_self_authorize(repository):
    """GOV-01..02: PR-owned approved fields and local reports are not trusted."""
    root, _ = repository
    module = gates_module()
    ctx = context(repository)
    put(root, "src/papertrace/example.py", "VALUE = 1\n")
    for name in ("docs/test-approval.json", "test/evaluation/report.json"):
        put(root, name, '{"approved": true, "status": "PASS", "signature": "synthetic-untrusted"}\n')
    assert module.test_approval_gate(ctx)["status"] == "BLOCKED"
    put(root, "prompts/runtime.yaml", "model: unapproved-synthetic-model\n")
    assert module.semantic_gate(ctx)["status"] == "BLOCKED"
    (root / "src/papertrace/example.py").unlink()
    (root / "prompts/runtime.yaml").unlink()
    (root / "docs/test-approval.json").unlink()
    (root / "test/evaluation/report.json").unlink()
    put(root, "docs/readme.md", "Documentation-only fixture.\n")
    assert module.semantic_gate(ctx)["status"] == "NOT_REQUIRED"
    assert module.test_approval_gate(ctx)["status"] == "NOT_REQUIRED"


def test_regression_executes_every_team_offline_test_and_rejects_fail_skip_empty(repository):
    """p10 gate5: no selective rerun, skip-as-pass or claims of upstream success."""
    root, _ = repository
    module = gates_module()
    ctx = context(repository)
    put(root, "papertrace.pytest.ini", "[pytest]\ntestpaths = test/offline\n")
    source = put(root, "test/offline/test_fixture.py", "def test_first():\n    assert True\n")
    other = put(root, "test/offline/test_second.py", "def test_second():\n    assert True\n")
    report = module.regression_gate(ctx)
    assert report["status"] == "PASS"
    assert report["details"]["tests"] == 2
    assert report["details"]["full_course_regression"] == "BLOCKED"
    other.write_text("def test_second():\n    assert False\n", encoding="utf-8")
    assert module.regression_gate(ctx)["status"] == "FAIL"
    other.write_text('import pytest\n@pytest.mark.skip(reason="synthetic")\ndef test_second():\n    assert True\n', encoding="utf-8")
    assert module.regression_gate(ctx)["status"] == "FAIL"
    other.write_text('import pytest\n@pytest.mark.xfail(reason="synthetic")\ndef test_second():\n    assert True\n', encoding="utf-8")
    assert module.regression_gate(ctx)["status"] == "FAIL"
    source.unlink()
    other.unlink()
    assert module.regression_gate(ctx)["status"] == "FAIL"
    put(root, "test/offline/test_fixture.py", "def test_first():\n    assert True\n")
    # This tiny synthetic repository has no upstream Python tests or live cases.
    # A full runner must be able to succeed when every actual origin is complete.
    assert module.regression_gate(context(repository, scope="full"))["status"] == "PASS"


def test_static_aggregate_and_cli_fail_closed(repository, monkeypatch):
    """GOV-02: real CLI never turns missing trust or full scope into success."""
    root, base = repository
    module = gates_module()
    monkeypatch.setattr(module, "permissions_check", lambda ctx: module.result("permissions", "PASS", "synthetic aggregate input; actual configuration tested separately"))
    monkeypatch.setattr(module, "BASELINE", base)
    put(root, "papertrace.ruff.toml", '[lint]\nselect = ["E4", "E7", "E9", "F"]\n')
    put(root, "mypy.ini", "[mypy]\ncheck_untyped_defs = True\n")
    put(root, "papertrace.pytest.ini", "[pytest]\ntestpaths = test/offline\n")
    put(root, "test/offline/test_fixture.py", "def test_fixture():\n    assert True\n")
    put(root, "scripts/fixture.py", "VALUE = 1\n")
    put(root, "requirements-init.lock", (ROOT / "requirements-init.lock").read_text(encoding="utf-8"))
    models = ("CorpusSnapshot", "EvidenceRecord", "ReviewDecision", "AnswerDraft", "ReleaseDecision")
    put(root, "src/papertrace/contracts.py", "\n".join(f"class {name}:\n    pass\n" for name in models))
    write_log(root, [ai_entry()])
    put(root, "Prompt.md", "Synthetic prompt under test only.\n")
    assert module.static_gate(context(repository))["status"] == "PASS"
    assert module.static_gate(context(repository, scope="full"))["status"] == "PASS"
    code = module.main(["--root", str(root), "--gate", "all", "--base", base, "--scope", "initialization"])
    assert code == 2
    assert module.main(["--root", str(root), "--gate", "schema", "--base", base]) == 0
    assert module.main(["--root", str(root), "--gate", "schema", "--base", base.upper()]) == 1


def test_schema_rejects_duplicate_yaml_keys_and_remote_refs(repository):
    """D1 / SEC-01: reject ambiguous YAML and external schema retrieval."""
    root, _ = repository
    module = gates_module()
    ctx = context(repository)
    path = root / "docs/req/requirements.yaml"
    original = path.read_text(encoding="utf-8")
    path.write_text(original + "\nstatus: approved\n", encoding="utf-8")
    assert module.schema_gate(ctx)["status"] == "FAIL"
    path.write_text(original, encoding="utf-8")
    put(root, "docs/req/req-schema.json", '{"$ref":"https://example.invalid/schema.json"}')
    assert module.schema_gate(ctx)["status"] == "FAIL"


def test_log_new_id_only_is_not_new_semantic_disclosure(repository):
    """GOV-03: copied content with a different ID is not a new use record."""
    root, _ = repository
    module = gates_module()
    old = ai_entry("fixture-original")
    write_log(root, [old])
    git(root, "add", ".")
    git(root, "commit", "-qm", "Synthetic log baseline")
    base = git(root, "rev-parse", "HEAD")
    put(root, "src/papertrace/changed.py", "VALUE = 2\n")
    write_log(root, [old, dict(old, entry_id="only-an-id-change")])
    assert module.ai_log_gate(context((root, base)))["status"] == "FAIL"


@pytest.mark.parametrize("name", ["opencode.jsonc", ".opencode/permissions.jsonc", "requirements-runtime.lock", "requirements-upstream-test.lock"])
def test_explicit_head_cannot_verify_different_executable_configuration(repository, name):
    """GOV-02: execution inputs, not only Python files, must match selected head."""
    root, base = repository
    put(root, name, "synthetic changed execution configuration\n")
    with pytest.raises(ValueError, match="worktree"):
        gates_module().source_tree_check(context(repository, head=base))


def test_full_regression_gate_can_execute_all_origins_without_a_permanent_block(repository):
    """GOV-02: complete synthetic origin succeeds; this is not real upstream evidence."""
    root, _ = repository
    put(root, "papertrace.pytest.ini", "[pytest]\n")
    put(root, "test/offline/test_first.py", "def test_first():\n    assert True\n")
    report = gates_module().regression_gate(context(repository, scope="full"))
    assert report["status"] == "PASS"
    assert report["details"]["scope"] == "all-prior-origins"
    assert report["details"]["full_course_regression"] == "PASS"


def test_outdated_branch_is_an_explicit_sync_block_not_malformed_input(repository, monkeypatch, capsys):
    """GOV-02: branches can develop in parallel; full integration needs current base."""
    root, fork = repository
    git(root, "checkout", "-qb", "fixture-feature")
    put(root, "docs/feature.md", "synthetic feature branch\n")
    git(root, "add", ".")
    git(root, "commit", "-qm", "synthetic feature")
    head = git(root, "rev-parse", "HEAD")
    git(root, "checkout", "-qb", "fixture-main", fork)
    put(root, "docs/main.md", "synthetic new main commit\n")
    git(root, "add", ".")
    git(root, "commit", "-qm", "synthetic base advanced")
    advanced_base = git(root, "rev-parse", "HEAD")
    git(root, "checkout", "-q", "fixture-feature")
    module = gates_module()
    monkeypatch.setattr(module, "BASELINE", fork)
    code = module.main(["--root", str(root), "--gate", "schema", "--base", advanced_base, "--head", head, "--scope", "full"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 2
    assert payload["status"] == "BLOCKED"
    assert payload["reason"] == "BASE_NOT_IN_TARGET_HISTORY"
    assert payload["merge_base"] == fork


def test_ci_pr_number_environment_reaches_the_live_verifier(repository, monkeypatch, capsys):
    """GOV-01: metadata CI must not silently lose its real PR context."""
    target = gates_module()
    observed = []
    monkeypatch.setenv("PAPERTRACE_PR_NUMBER", "20")
    monkeypatch.setattr(target, "schema_gate", lambda ctx: observed.append(ctx.pr_number) or target.result("schema", "PASS", "context wiring only"))
    code = target.main(["--root", str(repository[0]), "--gate", "schema", "--base", repository[1]])
    capsys.readouterr()
    assert code == 0
    assert observed == [20]


def test_metadata_facades_delegate_to_executable_verifiers(repository, monkeypatch):
    """GOV-01/02: facade must not retain an unconditional BLOCKED placeholder."""
    from types import SimpleNamespace
    target = gates_module()
    called = []
    def verifier(ctx):
        called.append(ctx)
        return target.result("synthetic-unit-input", "PASS", "Facade wiring only; real evidence tested separately")
    monkeypatch.setattr(target, "support_module", lambda name: SimpleNamespace(verify_test_approval=verifier, verify_semantic=verifier))
    put(repository[0], "src/papertrace/service.py", "VALUE = 'synthetic facade input'\n")
    ctx = context(repository)
    assert target.test_approval_gate(ctx)["status"] == "PASS"
    assert target.semantic_gate(ctx)["status"] == "PASS"
    assert called == [ctx, ctx]


def test_all_aggregate_can_pass_only_when_every_selected_gate_passes(repository, monkeypatch, capsys):
    """GOV-02: aggregation cannot permanently block a genuinely complete run."""
    module = gates_module()
    root, base = repository
    monkeypatch.setattr(module, "BASELINE", base)
    names = {"test_approval_gate": "test-approval", "static_gate": "static", "schema_gate": "schema", "semantic_gate": "semantic", "regression_gate": "regression", "ai_log_gate": "ai-log"}
    for function, name in names.items():
        monkeypatch.setattr(module, function, lambda ctx, name=name: module.result(name, "PASS", "synthetic aggregate input, not real course evidence"))
    assert module.main(["--root", str(root), "--gate", "all", "--base", base, "--scope", "full"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["full_course_status"] == {name: "PASS" for name in names.values()}


@pytest.mark.parametrize("name", [".github/workflows/ci.yml", ".opencode/permissions.jsonc", "requirements-runtime.lock", "papertrace.pytest.ini"])
def test_ci_and_execution_policy_changes_require_fresh_disclosure(repository, name):
    """GOV-01/03: workflow and permission changes are executable governance, not prose."""
    root, _ = repository
    put(root, name, "synthetic execution-policy change\n")
    assert gates_module().ai_log_gate(context(repository))["status"] == "FAIL"


def test_metadata_ci_uses_trusted_base_without_running_target_code_with_token():
    """GOV-02/SEC-01: approval trust cannot come from the PR's own verifier."""
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    assert "pull_request_review" in workflow["on"]
    for name in ("test-approval", "semantic-evaluation"):
        job = workflow["jobs"][name]
        checkouts = [step["with"] for step in job["steps"] if step.get("uses", "").startswith("actions/checkout@")]
        assert checkouts[1]["path"] == ".control"
        assert checkouts[1]["ref"] == "${{ steps.control.outputs.sha }}"
        selector = next(step for step in job["steps"] if step.get("id") == "control")
        assert 'BASE="$PAPERTRACE_BASE"' in selector["run"]
        assert "[0-9a-f]{40}" in selector["run"]
        assert checkouts[0]["path"] == "target"
        token_steps = [step for step in job["steps"] if "GITHUB_TOKEN" in step.get("env", {})]
        assert len(token_steps) == 1
        command = token_steps[0]["run"]
        assert ".control/scripts/gates.py" in command
        assert "--root" in command and "target" in command
        assert "pytest" not in command
    assert "--scope full" in workflow["jobs"]["regression"]["steps"][-1]["run"]


def test_all_ci_gates_use_the_exact_base_verifier_not_candidate_self_certification():
    """GOV-02: changing the candidate runner cannot certify its own full result."""
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    assert workflow["jobs"]["semantic-evaluation"]["permissions"].get("actions") == "read"
    regression = workflow["jobs"]["regression"]
    assert regression["runs-on"].startswith("macos-")  # Real sandboxed OpenCode tool tests must run, never skip on Linux.
    assert any("@opencode/cli@2.0.12" in step.get("run", "") for step in regression["steps"])
    assert regression["env"]["PAPERTRACE_OPENCODE_BINARY"].endswith("/node_modules/.bin/opencode")
    for job in workflow["jobs"].values():
        checkouts = [step["with"] for step in job["steps"] if step.get("uses", "").startswith("actions/checkout@")]
        assert checkouts[1]["path"] == ".control"
        assert checkouts[1]["ref"] == "${{ steps.control.outputs.sha }}"
        assert ".control/scripts/gates.py" in job["steps"][-1]["run"]
        assert "--scope full" in job["steps"][-1]["run"]


def test_fixed_evaluation_and_workflow_contracts():
    """GOV-02: data/CI contracts are present without fabricated quality results."""
    dataset = json.loads((ROOT / "test/evaluation/cases.json").read_text(encoding="utf-8"))
    cases = dataset["cases"]
    assert len(cases) >= 8
    assert len({case["id"] for case in cases}) == len(cases)
    assert {case["kind"] for case in cases} == {"deterministic", "real-model-quality"}
    for case in cases:
        assert case["requirements"] and case["input"]
        assert "output" not in case
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    assert set(workflow["jobs"]) == {"test-approval", "static-analysis", "schema", "semantic-evaluation", "regression", "ai-use-log"}
    assert set(workflow["on"]) == {"push", "pull_request", "pull_request_review", "workflow_dispatch"}
    assert workflow["permissions"] == {"contents": "read"}
    for job in workflow["jobs"].values():
        assert "if" not in job and "continue-on-error" not in job
        assert all("if" not in step and "continue-on-error" not in step for step in job["steps"])
    assert "secrets." not in json.dumps(workflow)
