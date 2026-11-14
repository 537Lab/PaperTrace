"""PaperTrace local/CI gate entry point; GOV-01..04, ADR-001, INV-06.

PASS is scoped evidence, never proof of GitHub protection or model quality.
No credentials, provider requests, shell interpolation, or mutable approval trust.
"""

import argparse
import ast
import importlib.util
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from importlib import metadata
from pathlib import Path, PurePosixPath

import yaml
from jsonschema import Draft202012Validator
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

BASELINE = "c692d0dfeac4a0296599f7fe21a253a58b7ac12a"


class UniqueSafeLoader(yaml.SafeLoader):
    """D1 / GOV-03: ambiguous duplicate mapping keys are invalid input."""

    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        mapping = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in mapping:
                raise ValueError("duplicate YAML mapping key")
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


def load_yaml(text):
    """D1 / GOV-03: SafeLoader with duplicate rejection, no object constructors."""
    loader = UniqueSafeLoader(text)
    try:
        return loader.get_single_data()
    finally:
        loader.dispose()


def result(gate, status, summary, **details):
    """GOV-02: stable JSON result envelope."""
    return {"gate": gate, "status": status, "summary": summary, "details": details}


def support_module(name):
    """GOV-02: load helpers beside this verifier, never from the target PR tree."""
    spec = importlib.util.spec_from_file_location("papertrace_gate_support_" + name, Path(__file__).with_name(name + ".py"))
    if spec is None or spec.loader is None:
        raise ValueError("Verifier support module unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@dataclass(frozen=True)
class GateContext:
    """GOV-02: explicit target; absent head means the current working tree."""

    root: Path
    base: str = BASELINE
    head: str | None = None
    scope: str = "initialization"
    baseline: str = BASELINE
    timeout: float = 120
    runtime_python: str | None = None
    upstream_python: str | None = None
    run_live: bool = False
    repository: str = "537Lab/PaperTrace"
    pr_number: int | None = None

    def path(self, relative):
        """INV-06: refuse traversal and links outside the repository."""
        value = PurePosixPath(relative)
        if value.is_absolute() or ".." in value.parts or "\\" in relative:
            raise ValueError("repository-relative path required")
        path = self.root / relative
        if not path.resolve().is_relative_to(self.root.resolve()):
            raise ValueError("path escapes repository")
        return path

    def git(self, *args):
        """GOV-02: bounded, shell-free Git lookup, never include raw stderr."""
        if args and args[0] == "diff":
            args = ("diff", "--no-ext-diff", "--no-textconv", *args[1:])
        process = subprocess.run(
            ["git", "-C", str(self.root), *args], env=clean_environment(self),
            capture_output=True, timeout=self.timeout, check=False,
        )
        if process.returncode:
            raise ValueError("Git lookup failed")
        return process.stdout

    def read(self, relative, ref=None):
        """GOV-02: read a validated path from the selected tree, or a base ref."""
        path = self.path(relative)
        selected = ref or self.head
        if selected:
            return self.git("show", f"{selected}:{relative}").decode("utf-8")
        return path.read_text(encoding="utf-8")

    def changes(self):
        """GOV-03: include staged, unstaged, deleted, and untracked new files."""
        for reference in (self.base, self.head, self.baseline):
            if reference is not None and not re.fullmatch(r"[0-9a-f]{40}", reference):
                raise ValueError("full lowercase 40-character Git SHA required")
        target = [self.head] if self.head else []
        raw = self.git("diff", "--name-only", "-z", self.base, *target, "--")
        if not self.head:
            raw += self.git("ls-files", "--others", "--exclude-standard", "-z")
        return sorted({item.decode("utf-8") for item in raw.split(b"\0") if item})


def code_or_prompt(path):
    """p10 gate6: tests and agent instructions count as code/prompt changes."""
    value = path.lower()
    return (
        value.startswith(("src/", "packages/", "scripts/", "test/", "tests/", "prompts/", ".github/workflows/", ".github/actions/", ".opencode/"))
        or value in {"prompt.md", "agents.md", "opencode.jsonc", ".agent/rules.md", "pyproject.toml", "uv.lock", "papertrace.pytest.ini", "papertrace.ruff.toml", "mypy.ini", ".python-version"}
        or (value.startswith("requirements") and value.endswith((".lock", ".in")))
        or value.endswith((".py", ".js", ".ts", ".tsx", ".sh"))
    )


def log_entries(text):
    """GOV-03: validate meaningful log structure, not approval truth."""
    document = load_yaml(text)
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        raise ValueError("AI-use log schema_version must be 1")
    entries = document.get("entries")
    if not isinstance(entries, list):
        raise ValueError("AI-use log entries must be an array")
    parsed = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("AI-use entry must be an object")
        for key in ("entry_id", "tool", "model", "purpose", "status"):
            if not isinstance(entry.get(key), str) or not entry[key].strip():
                raise ValueError("AI-use entry lacks a required string")
        for key in ("approvals", "verification", "limitations"):
            if not isinstance(entry.get(key), list):
                raise ValueError("AI-use entry lacks a required array")
        scope = entry.get("scope")
        if not isinstance(scope, (str, list)) or not scope:
            raise ValueError("AI-use entry lacks scope")
        timestamp = entry.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if not isinstance(timestamp, datetime) or timestamp.tzinfo is None:
            raise ValueError("AI-use timestamp must include timezone")
        identifier = entry["entry_id"]
        if identifier in parsed:
            raise ValueError("duplicate AI-use entry ID")
        # Canonical parsed objects ignore YAML formatting and key/entry ordering.
        normalized = dict(entry, timestamp=timestamp.isoformat())
        parsed[identifier] = json.dumps(normalized, sort_keys=True, default=str)
    return parsed


def ai_log_gate(ctx):
    """p10 gate6: changed code/prompt needs a genuinely new appended entry."""
    try:
        changes = [path for path in ctx.changes() if code_or_prompt(path)]
        if not changes:
            return result("ai-log", "NOT_REQUIRED", "No code or prompt changes", changed_paths=[])
        current = log_entries(ctx.read("docs/ai-use-log.yaml"))
        try:
            previous_text = ctx.read("docs/ai-use-log.yaml", ref=ctx.base)
        except ValueError:
            # Prove absence; a corrupt Git/base lookup must not count as empty history.
            names = ctx.git("ls-tree", "-r", "--name-only", ctx.base).decode("utf-8").splitlines()
            if "docs/ai-use-log.yaml" in names:
                raise
            previous_text = "schema_version: 1\nentries: []\n"
        previous = log_entries(previous_text)
        new = set(current) - set(previous)
        def semantic_content(value):
            parsed = json.loads(value)
            parsed.pop("entry_id", None)
            return json.dumps(parsed, sort_keys=True)
        old_content = {semantic_content(value) for value in previous.values()}
        new = {key for key in new if semantic_content(current[key]) not in old_content}
        preserved = all(current.get(key) == value for key, value in previous.items())
        if not new or not preserved:
            return result("ai-log", "FAIL", "Append a new disclosure; do not reorder-only or rewrite history", new_entries=len(new))
        return result("ai-log", "PASS", "New semantic AI-use disclosure found", new_entries=len(new), changed_paths=changes,
                      limitation="Structural disclosure evidence, not proof of authorship or genuine human approval")
    except (OSError, ValueError, TypeError, KeyError, yaml.YAMLError) as error:
        return result("ai-log", "FAIL", "Missing, invalid or inaccessible AI-use log/diff", error_type=type(error).__name__)


FROZEN = ("src/paperqa", "packages", "tests", "pyproject.toml", "uv.lock", "LICENSE")
B_IMPORT_PATH = "src/papertrace/retrieval/"


def build_metadata_path(ctx, relative):
    """GOV-02: narrowly recognize ignored SCM/egg-info output, never source changes."""
    path = ctx.path(relative)
    if path.is_symlink():
        return False
    scm = bool(re.fullmatch(r"src/paperqa/version\.py|packages/paper-qa-[^/]+/src/paperqa_[^/]+/version\.py", relative))
    metadata = Path(relative).name in {"PKG-INFO", "SOURCES.txt", "dependency_links.txt", "requires.txt", "top_level.txt", "entry_points.txt", "scm_file_list.json", "scm_version.json"} and any(part.endswith(".egg-info") for part in Path(relative).parts)
    if not (scm or metadata):
        return False
    # check-ignore's nonzero means not ignored: do not exempt an arbitrary input.
    process = subprocess.run(["git", "-C", str(ctx.root), "check-ignore", "-q", "--", relative], capture_output=True, check=False)
    return process.returncode == 0


def frozen_check(ctx):
    """GOV-02: preserve baseline bytes, upstream tests and lock, including deletes."""
    try:
        target = [ctx.head] if ctx.head else []
        dirty = ctx.git("diff", "--name-only", "-z", ctx.baseline, *target, "--", *FROZEN)
        changed = [item.decode("utf-8") for item in dirty.split(b"\0") if item]
        if not ctx.head:
            baseline_paths = set(ctx.git("ls-tree", "-r", "--name-only", ctx.baseline).decode("utf-8").splitlines())
            for folder in FROZEN[:3]:
                for path in ctx.path(folder).rglob("*"):
                    relative = path.relative_to(ctx.root).as_posix()
                    if any(part in {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"} for part in path.parts):
                        continue
                    if path.is_file() and relative not in baseline_paths and not build_metadata_path(ctx, relative):
                        changed.append(relative)
        return result("frozen-baseline", "FAIL" if changed else "PASS", "Upstream baseline byte integrity", changed_paths=sorted(set(changed)), baseline=ctx.baseline)
    except (OSError, ValueError) as error:
        return result("frozen-baseline", "FAIL", "Unable to establish baseline integrity", error_type=type(error).__name__)


def architecture_check(ctx):
    """ADR-001 / GOV-02: static imports and dynamic import escape outside B."""
    errors = []
    try:
        for path in ctx.path("src/papertrace").rglob("*.py"):
            relative = path.relative_to(ctx.root).as_posix()
            tree = ast.parse(ctx.read(relative), filename=relative)
            is_b = relative.startswith(B_IMPORT_PATH)
            loaders = {"__import__"}
            importlib_aliases = {"importlib"}
            for node in ast.walk(tree):
                imported = []
                if isinstance(node, ast.Import):
                    imported = [name.name for name in node.names]
                    for name in node.names:
                        if name.name == "importlib":
                            importlib_aliases.add(name.asname or name.name)
                elif isinstance(node, ast.ImportFrom):
                    imported = [node.module or ""]
                    if node.module == "importlib":
                        loaders.update(name.asname or name.name for name in node.names if name.name == "import_module")
                if not is_b and any(name == "paperqa" or name.startswith("paperqa.") for name in imported):
                    errors.append(f"{relative}:{node.lineno}: upstream import outside module B")
            if not is_b:
                for node in ast.walk(tree):
                    if not isinstance(node, ast.Call):
                        continue
                    function = node.func
                    dynamic = (
                        isinstance(function, ast.Name) and function.id in loaders | {"eval", "exec", "compile"}
                    ) or (
                        isinstance(function, ast.Attribute) and function.attr == "import_module"
                        and isinstance(function.value, ast.Name) and function.value.id in importlib_aliases
                    )
                    if dynamic:
                        errors.append(f"{relative}:{node.lineno}: dynamic loading outside module B")
        return result("architecture", "FAIL" if errors else "PASS", "AST import boundary", errors=errors,
                      limitation="AST fitness function, not a Python sandbox; live adapter spy/integration still required")
    except (OSError, SyntaxError, ValueError) as error:
        return result("architecture", "FAIL", "Cannot parse team source", error_type=type(error).__name__)


def clean_environment(ctx):
    """COST-01 / SEC-01: subprocesses inherit no provider keys or private HOME."""
    temporary = ctx.path(".local/gate-tmp")
    home = ctx.path(".local/gate-home")
    temporary.mkdir(parents=True, exist_ok=True)
    home.mkdir(parents=True, exist_ok=True)
    return {
        "PATH": str(Path(sys.executable).parent) + os.pathsep + os.defpath,
        "HOME": str(home), "TMPDIR": str(temporary), "LANG": "C.UTF-8",
        "PYTHONPATH": str(ctx.path("src")), "PYTHONNOUSERSITE": "1",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTEST_ADDOPTS": "",
        "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0", "GIT_PAGER": "cat",
    }


def run_command(ctx, command):
    """GOV-02: execute real offline tools, bounded; never echo possible secrets."""
    try:
        process = subprocess.run(
            command, cwd=ctx.root, env=clean_environment(ctx),
            capture_output=True, timeout=ctx.timeout, check=False,
        )
        return result(
            "command", "PASS" if process.returncode == 0 else "FAIL",
            "Command completed", returncode=process.returncode,
            stdout_sha256=sha256(process.stdout).hexdigest(),
            stderr_sha256=sha256(process.stderr).hexdigest(),
            output_bytes=len(process.stdout) + len(process.stderr),
        )
    except subprocess.TimeoutExpired:
        return result("command", "BLOCKED", "Command exceeded timeout", timeout_seconds=ctx.timeout)
    except OSError as error:
        return result("command", "BLOCKED", "Command unavailable", error_type=type(error).__name__)


def tool_check(ctx, tool):
    """p10 gate2: lint only team code; type-check only the team package."""
    commands = {
        "lint": [sys.executable, "-m", "ruff", "check", "--config", "papertrace.ruff.toml", "src/papertrace", "test/offline", "scripts"],
        "types": [sys.executable, "-m", "mypy", "--config-file", "mypy.ini", "src/papertrace"],
    }
    report = run_command(ctx, commands[tool])
    report["gate"] = tool
    return report


def dependencies_check(ctx):
    """p10 gate2: exact installed metadata/closure consistency, not CVE audit."""
    try:
        pins = {}
        errors = []
        for line in ctx.read("requirements-init.lock").splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            requirement = Requirement(line)
            specs = list(requirement.specifier)
            if requirement.url or requirement.marker or requirement.extras or len(specs) != 1 or specs[0].operator != "==" or "*" in specs[0].version:
                raise ValueError("dependency must have an unconditional exact version pin")
            name = canonicalize_name(requirement.name)
            if name in pins:
                raise ValueError("duplicate dependency pin")
            pins[name] = specs[0].version
            if metadata.version(name) != specs[0].version:
                errors.append("installed version differs from lock: " + name)
        if not pins:
            raise ValueError("empty dependency lock")
        for name in pins:
            for text in metadata.requires(name) or []:
                dependency = Requirement(text)
                if dependency.marker and not dependency.marker.evaluate({"extra": ""}):
                    continue
                target = canonicalize_name(dependency.name)
                if target not in pins:
                    errors.append("dependency missing from lock: " + target)
                elif not dependency.specifier.contains(pins[target], prereleases=True):
                    errors.append("locked transitive version is incompatible: " + target)
        return result("dependencies", "FAIL" if errors else "PASS", "Initialization environment matches exact pins", locked_packages=len(pins), errors=sorted(set(errors)),
                      limitation="Version/metadata consistency only; no online advisory scan, hash/provenance or full upstream environment certification")
    except (OSError, ValueError, metadata.PackageNotFoundError) as error:
        return result("dependencies", "FAIL", "Missing or invalid dependency lock/environment", error_type=type(error).__name__)


def contract_check(ctx):
    """QA-01 / p10 gate2: five shared API names exist, without executing source."""
    try:
        tree = ast.parse(ctx.read("src/papertrace/contracts.py"))
        declared = {node.name for node in tree.body if isinstance(node, ast.ClassDef)}
        required = {"CorpusSnapshot", "EvidenceRecord", "ReviewDecision", "AnswerDraft", "ReleaseDecision"}
        missing = sorted(required - declared)
        return result("contract-api", "FAIL" if missing else "PASS", "Shared five-contract API presence", missing=missing,
                      limitation="AST surface presence only; round-trip/negative tests run in initialization regression, not module integration")
    except (OSError, ValueError, SyntaxError) as error:
        return result("contract-api", "FAIL", "Shared contracts absent or invalid", error_type=type(error).__name__)


SECRET_PATTERNS = (
    re.compile(r"sk-(?:proj-)?[A-Za-z0-9_-]{20,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{25,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{25,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r'''(?i)(?:api[_-]?key|password|secret|access[_-]?token)\s*[:=]\s*["'][A-Za-z0-9+/_.-]{20,}["']'''),
)


def secret_check(ctx):
    """SEC-01: scan only changed team text; never open local credentials."""
    findings = []
    try:
        available = None
        if ctx.head:
            available = set(ctx.git("ls-tree", "-r", "--name-only", ctx.head).decode("utf-8").splitlines())
        for relative in ctx.changes():
            name = PurePosixPath(relative).name.lower()
            if name.startswith(".env") or name in {"id_rsa", "id_ed25519", "credentials.json"}:
                findings.append({"path": relative, "rule": "credential-file-forbidden"})
                continue
            if not relative.startswith(("src/papertrace/", "scripts/", "test/", "docs/", "prompts/", ".opencode/", ".agent/", ".github/")) and "/" in relative:
                continue
            if PurePosixPath(relative).suffix.lower() not in {".py", ".md", ".yaml", ".yml", ".json", ".jsonc", ".toml", ".txt", ".ini"}:
                continue
            if (available is not None and relative not in available) or (available is None and not ctx.path(relative).is_file()):
                continue
            for line_number, line in enumerate(ctx.read(relative).splitlines(), 1):
                if any(pattern.search(line) for pattern in SECRET_PATTERNS):
                    findings.append({"path": relative, "line": line_number, "rule": "potential-secret-redacted"})
        return result("secrets", "FAIL" if findings else "PASS", "Changed-team-file secret heuristic", findings=findings,
                      limitation="Heuristics are incomplete; no private environment or whole upstream scan, no guarantee of absence")
    except (OSError, ValueError) as error:
        return result("secrets", "FAIL", "Unable to scan changed team files safely", error_type=type(error).__name__)


def schema_gate(ctx):
    """D1 / GOV-02: JSON Schema plus identity, invariant and source fitness."""
    try:
        schema = json.loads(ctx.read("docs/req/req-schema.json"))
        registry = load_yaml(ctx.read("docs/req/requirements.yaml"))
        pending = [schema]
        while pending:
            value = pending.pop()
            if isinstance(value, dict):
                for key, target in value.items():
                    if key in {"$ref", "$dynamicRef"} and (not isinstance(target, str) or not target.startswith("#")):
                        return result("schema", "FAIL", "External schema references are forbidden")
                    pending.append(target)
            elif isinstance(value, list):
                pending.extend(value)
        Draft202012Validator.check_schema(schema)
        errors = [
            "schema violation at " + "/".join(map(str, error.absolute_path))
            for error in Draft202012Validator(schema).iter_errors(registry)
        ]
        if errors:
            return result("schema", "FAIL", "Requirements do not validate", errors=errors)
        identifiers = set()
        for row in registry["requirements"]:
            identifier = row["id"]
            if identifier in identifiers:
                errors.append("duplicate requirement ID: " + identifier)
            identifiers.add(identifier)
            fit = row["fit_criterion"]
            if row["type"] == "invariant" and (
                fit["operator"] != "==" or fit["threshold"] != 0
            ):
                errors.append("invariant must use == 0: " + identifier)
            for source in row["sources"]:
                if source.startswith("paperqa:"):
                    match = re.fullmatch(r"paperqa:([^:]+):(\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*)", source)
                    if not match:
                        errors.append("invalid upstream source reference: " + identifier)
                        continue
                    relative, ranges = match.groups()
                    line_count = len(ctx.read(relative).splitlines())
                    if not relative.startswith(("src/paperqa/", "packages/")):
                        errors.append("source outside upstream paths: " + identifier)
                    for span in ranges.split(","):
                        numbers = list(map(int, span.split("-")))
                        if min(numbers) < 1 or max(numbers) > line_count or numbers != sorted(numbers):
                            errors.append("source line range out of bounds: " + identifier)
                elif not re.fullmatch(r"(?:course-project:p[\d,:A-Za-z-]+|audit:[A-Z0-9-]+)", source):
                    # Local references must resolve inside the repository; no private paths.
                    relative = source.split("#", 1)[0]
                    ctx.read(relative)
        return result(
            "schema", "FAIL" if errors else "PASS", "Registry structural validation",
            requirement_count=len(registry["requirements"]), errors=errors,
            limitation="Does not prove implementation of fit criteria or human approval",
        )
    except (OSError, ValueError, TypeError, KeyError, yaml.YAMLError) as error:
        return result("schema", "FAIL", "Missing or malformed requirements input", error_type=type(error).__name__)


def exit_code(reports):
    """GOV-02: failure beats blockage; missing evidence never becomes success."""
    if any(report["status"] == "FAIL" for report in reports):
        return 1
    if any(report["status"] == "BLOCKED" for report in reports):
        return 2
    return 0


def permissions_check(ctx):
    """ADR-002 / INV-06: validate target permission config without a model/binary."""
    report = run_command(ctx, [sys.executable, str(Path(__file__).with_name("opencode_support.py")), "--root", str(ctx.root)])
    report["gate"] = "permissions"
    report["details"]["limitation"] = "Portable configuration check; not OS isolation or model-driven runtime enforcement"
    return report


def static_gate(ctx):
    """p10 gate2: executable static checks, not a permanent scope placeholder."""
    reports = [tool_check(ctx, "lint"), tool_check(ctx, "types"), dependencies_check(ctx),
               frozen_check(ctx), architecture_check(ctx), contract_check(ctx), secret_check(ctx), permissions_check(ctx)]
    status = {0: "PASS", 1: "FAIL", 2: "BLOCKED"}[exit_code(reports)]
    return result("static", status, "Lint/type/dependency/contract/security/API/permission fitness checks", checks=reports,
                  limitation="Static fitness and exact initialization pins; not a vulnerability certification or proof of live AI behavior")


def test_approval_gate(ctx):
    """p10 gate1: real API reviews and immutable tests; no local approval booleans."""
    return support_module("gate_evidence").verify_test_approval(ctx)


def semantic_gate(ctx):
    """p10 gate4: actual fixed-set evidence, or NOT_REQUIRED for non-AI changes."""
    return support_module("semantic_evidence").verify_semantic(ctx)


def regression_gate(ctx):
    """p10 gate5: actually run all team offline tests; never rename it full prior."""
    if ctx.scope == "full":
        report = support_module("full_regression").run_full(
            ctx.root, ctx.base, ctx.path(".local/full-regression"), timeout=ctx.timeout,
            runtime_python=ctx.runtime_python, upstream_python=ctx.upstream_python, run_live=ctx.run_live,
        )
        return result("regression", report["status"], "Full prior-origin execution with baseline node inventory",
                      scope="all-prior-origins", full_course_regression=report["status"], **{key: value for key, value in report.items() if key != "status"})
    runner = support_module("full_regression")
    suite = runner.Suite("team-offline", ("test/offline",), sys.executable, "papertrace.pytest.ini")
    execution = runner.run_suite(ctx.root, suite, ctx.path(".local/initialization-regression"), timeout=ctx.timeout)
    outcomes = execution["outcomes"]
    return result("regression", execution["status"], "All team offline tests; no full prior-suite claim",
                  scope="all-team-offline", full_course_regression="BLOCKED", tests=len(execution["collected"]),
                  failures=outcomes.get("failed", 0), skipped=outcomes.get("skipped", 0),
                  xfailed=outcomes.get("xfailed", 0), xpassed=outcomes.get("xpassed", 0), execution=execution,
                  pending_suites=["team runtime/live", "upstream tests/ and packages/"],
                  limitation="Initialization is never substituted for the full-origin gate")


def source_tree_check(ctx):
    """GOV-02: tools must execute exactly the requested head's inputs."""
    if not ctx.head:
        return
    inputs = ["src", "test", "tests", "packages", "scripts", "papertrace.pytest.ini", "papertrace.ruff.toml", "mypy.ini", "requirements*.lock", "requirements*.in", "pyproject.toml", "uv.lock", "AGENTS.md", "Prompt.md", "opencode.jsonc", ".opencode", ".agent", "prompts"]
    dirty = ctx.git("diff", "--name-only", ctx.head, "--", *inputs)
    extra = ctx.git("ls-files", "--others", "--exclude-standard", "--", *inputs)
    if dirty.strip() or extra.strip():
        raise ValueError("requested head differs from executable worktree inputs")


def main(argv=None):
    """GOV-02: six stable CLI gates; a partial all run cannot return zero."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate", required=True, choices=["schema", "static", "ai-log", "test-approval", "semantic", "regression", "all"])
    parser.add_argument("--base", default=BASELINE)
    parser.add_argument("--head", default=None, help="Full SHA; omit for initialization working-tree comparison")
    parser.add_argument("--scope", choices=["initialization", "full"], default="initialization")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--runtime-python", default=None)
    parser.add_argument("--upstream-python", default=None)
    parser.add_argument("--run-live", action="store_true", help="Only after explicit human data/provider/budget approval; never enabled by default CI")
    parser.add_argument("--repository", default=os.environ.get("PAPERTRACE_REPOSITORY", "537Lab/PaperTrace"))
    parser.add_argument("--pr-number", type=int, default=os.environ.get("PAPERTRACE_PR_NUMBER") or None)
    args = parser.parse_args(argv)
    reports = []
    try:
        if not 0 < args.timeout <= 1800:
            raise ValueError("timeout must be positive and bounded")
        ctx = GateContext(root=args.root.resolve(), base=args.base, head=args.head, scope=args.scope, baseline=BASELINE, timeout=args.timeout,
                          runtime_python=args.runtime_python, upstream_python=args.upstream_python, run_live=args.run_live,
                          repository=args.repository, pr_number=args.pr_number)
        ctx.changes()  # Validate literal SHAs and Git lookup before any gate executes.
        merge_base = ctx.git("merge-base", ctx.base, ctx.head or "HEAD").decode("utf-8").strip()
        if merge_base != ctx.base:
            print(json.dumps({"schema_version": 1, "scope": args.scope, "status": "BLOCKED", "exit_code": 2,
                              "reason": "BASE_NOT_IN_TARGET_HISTORY", "merge_base": merge_base,
                              "target": {"base": ctx.base, "head": ctx.head or "WORKTREE", "upstream_baseline": ctx.baseline},
                              "results": [], "summary": "Base advanced: synchronize the feature branch before full integration; local module development may continue",
                              "remote_enforcement": "NOT_DEPLOYED_OR_VERIFIED"}, sort_keys=True))
            return 2
        if args.gate in {"static", "regression", "all"}:
            source_tree_check(ctx)
        gates = {"test-approval": test_approval_gate, "static": static_gate, "schema": schema_gate,
                 "semantic": semantic_gate, "regression": regression_gate, "ai-log": ai_log_gate}
        selected = list(gates) if args.gate == "all" else [args.gate]
        for name in selected:
            reports.append(gates[name](ctx))
        code = exit_code(reports)
        payload = {
            "schema_version": 1, "scope": args.scope,
            "target": {"base": ctx.base, "head": ctx.head or "WORKTREE", "upstream_baseline": ctx.baseline},
            "status": {0: "PASS", 1: "FAIL", 2: "BLOCKED"}[code], "exit_code": code, "results": reports,
            "full_course_status": {name: next((r["details"].get("full_course_regression", r["status"]) if name == "regression" else r["status"] for r in reports if r["gate"] == name), "NOT_RUN") for name in gates},
            "remote_enforcement": "NOT_DEPLOYED_OR_VERIFIED",
        }
    except Exception as error:  # Fail closed; never print exception values containing user data.
        code = 1
        payload = {"schema_version": 1, "status": "FAIL", "exit_code": code, "scope": args.scope,
                   "results": reports, "error": "Gate input/execution error", "error_type": type(error).__name__}
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
