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
    source.unlink()
    other.unlink()
    assert module.regression_gate(ctx)["status"] == "FAIL"
    put(root, "test/offline/test_fixture.py", "def test_first():\n    assert True\n")
    assert module.regression_gate(context(repository, scope="full"))["status"] == "BLOCKED"


def test_static_aggregate_and_cli_fail_closed(repository, monkeypatch):
    """GOV-02: real CLI never turns missing trust or full scope into success."""
    root, base = repository
    module = gates_module()
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
    assert module.static_gate(context(repository, scope="full"))["status"] == "BLOCKED"
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
    assert set(workflow["on"]) == {"push", "pull_request"}
    assert workflow["permissions"] == {"contents": "read"}
    for job in workflow["jobs"].values():
        assert "if" not in job and "continue-on-error" not in job
        assert all("if" not in step and "continue-on-error" not in step for step in job["steps"])
    assert "secrets." not in json.dumps(workflow)
