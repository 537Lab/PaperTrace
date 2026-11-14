"""GOV-02 full prior-suite execution. No marker filter silently drops tests.

Also a pytest plugin: invoked only in isolated child interpreters. This runner
never loads a .env, a private model credential, or a user pytest configuration.
"""

import io
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import tomllib
from dataclasses import dataclass, replace
from hashlib import sha256
from pathlib import Path

import pytest

# pytest imports explicitly requested plugins before loading conftest.py.
# Activation is child-only: importing this module in unit tests changes no sockets.
if os.environ.get("PAPERTRACE_SUITE_REPORT") and os.environ.get("PAPERTRACE_RUN_LIVE") != "1":
    from pytest_socket import disable_socket

    disable_socket(allow_unix_socket=True)


@dataclass(frozen=True)
class Suite:
    """GOV-02: explicit interpreter/configuration for a complete test origin."""

    name: str
    paths: tuple[str, ...]
    python: str
    config: str
    plugins: tuple[str, ...] = ("pytest_socket",)
    ignore: tuple[str, ...] = ()


_STATE = {}


def _save_state():
    destination = os.environ.get("PAPERTRACE_SUITE_REPORT")
    if destination:
        Path(destination).write_text(json.dumps(_STATE, sort_keys=True), encoding="utf-8")


def pytest_configure(config):
    """INV-06: block sockets before collection, not only before a test body."""
    from pytest_socket import disable_socket

    if os.environ.get("PAPERTRACE_RUN_LIVE") != "1":
        disable_socket(allow_unix_socket=True)
    _STATE.clear()
    _STATE.update(collected=[], pending_live=[], selected=[], deselected=[], configuration_errors=[],
                  outcomes={"passed": 0, "failed": 0, "skipped": 0, "xfailed": 0, "xpassed": 0}, collection_errors=[])
    if config.getoption("runxfail", default=False):
        _STATE["configuration_errors"].append("--runxfail masks expected-failure outcomes")


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(session, config, items):
    """GOV-02: inventory includes unmarked and parametrized cases."""
    _STATE["collected"] = [item.nodeid for item in items]
    if os.environ.get("PAPERTRACE_RUN_LIVE") != "1":
        prior_live = set(json.loads(os.environ.get("PAPERTRACE_PRIOR_LIVE", "[]")))
        pending = [item for item in items if item.nodeid in prior_live or any(item.get_closest_marker(mark) for mark in ("live", "live_api"))]
        _STATE["pending_live"] = [item.nodeid for item in pending]
        items[:] = [item for item in items if item not in pending]
        if pending:
            config.hook.pytest_deselected(items=pending)
    _STATE["selected"] = [item.nodeid for item in items]
    _save_state()


def pytest_deselected(items):
    """GOV-02: any deselection other than explicitly pending live tests fails."""
    _STATE["deselected"].extend(item.nodeid for item in items)


def pytest_collectreport(report):
    """GOV-02: import failures and skipped modules are not an empty green suite."""
    if report.failed or report.skipped:
        kind = "missing-dependency" if "ModuleNotFoundError" in str(report.longrepr) else "collection-failure"
        _STATE["collection_errors"].append({"nodeid": report.nodeid, "outcome": report.outcome, "kind": kind})


def pytest_runtest_logreport(report):
    """GOV-02: setup/teardown errors also block the gate."""
    if getattr(report, "wasxfail", None):
        _STATE["outcomes"]["xfailed" if report.skipped else "xpassed"] += 1
    elif report.failed:
        _STATE["outcomes"]["failed"] += 1
    elif report.skipped:
        _STATE["outcomes"]["skipped"] += 1
    elif report.when == "call" and report.passed:
        _STATE["outcomes"]["passed"] += 1
    _save_state()


def pytest_sessionfinish(session, exitstatus):
    """GOV-02: the parent consumes a freshly written bounded child report."""
    destination = os.environ.get("PAPERTRACE_SUITE_REPORT")
    if destination:
        Path(destination).write_text(json.dumps(_STATE, sort_keys=True), encoding="utf-8")


def isolated_environment(root, output):
    """SEC-01/COST-01: no inherited credentials, dotenv, plugins or user caches."""
    home = output / "home"
    temporary = output / "tmp"
    home.mkdir(parents=True, exist_ok=True)
    temporary.mkdir(parents=True, exist_ok=True)
    environment = {
        "PATH": os.defpath, "HOME": str(home), "TMPDIR": str(temporary),
        "PYTHONNOUSERSITE": "1", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "PYTEST_ADDOPTS": "", "PYTHON_DOTENV_DISABLED": "1", "PYTHONPATH": os.pathsep.join([str(Path(__file__).resolve().parent), str(root / "src")]),
        "PQA_HOME": str(home / "pqa"), "PQA_OFFLINE_TESTS": "true",
        "LITELLM_LOCAL_MODEL_COST_MAP": "True", "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1", "TOKENIZERS_PARALLELISM": "false",
        "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0", "LANG": "C.UTF-8",
    }
    tool = os.environ.get("PAPERTRACE_OPENCODE_BINARY") or shutil.which("opencode")
    fallback = Path.home() / ".opencode/bin/opencode"
    if not tool and fallback.is_file():
        tool = str(fallback)
    if tool and Path(tool).is_absolute() and Path(tool).is_file():
        environment["PAPERTRACE_OPENCODE_BINARY"] = tool
    return environment


def run_suite(root, suite, output, timeout=300, run_live=False, collect_only=False, prior_live=()):
    """GOV-02: run a whole origin, preserving exact collection and all failures."""
    root, output = Path(root).resolve(), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "pytest-report.json"
    report_path.unlink(missing_ok=True)
    command = [str(suite.python), "-m", "pytest", "-c", suite.config, "--import-mode=importlib", "-ra", "-q"]
    for plugin in suite.plugins:
        command += ["-p", plugin]
    command += ["-p", "full_regression"]
    if collect_only:
        command += ["--collect-only"]
    command += ["--force-enable-socket"] if run_live else ["--disable-socket", "--allow-unix-socket"]
    command += [f"--ignore={path}" for path in suite.ignore]
    command += list(suite.paths)
    environment = isolated_environment(root, output)
    environment["PATH"] = str(Path(suite.python).absolute().parent) + os.pathsep + os.defpath
    if run_live:
        # Explicit operator action only, after human plan/data/budget approval.
        # Never discover/load a credential file. CI does not enable this flag.
        environment["PAPERTRACE_RUN_LIVE"] = "1"
        environment["PQA_OFFLINE_TESTS"] = "false"
        for name in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "SEMANTIC_SCHOLAR_API_KEY", "CROSSREF_API_KEY", "NVIDIA_API_KEY"):
            if name in os.environ:
                environment[name] = os.environ[name]
    environment["PAPERTRACE_SUITE_REPORT"] = str(report_path)
    environment["PAPERTRACE_PRIOR_LIVE"] = json.dumps(list(prior_live))
    details = {"suite": suite.name, "command": command, "report_path": str(report_path),
               "collected": [], "outcomes": {"passed": 0, "failed": 0, "skipped": 0}}
    try:
        process = subprocess.Popen(command, cwd=root, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   start_new_session=os.name != "nt",
                                   creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0)
    except OSError as error:
        return dict(details, status="BLOCKED", reason=type(error).__name__)
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, check=False)
        else:
            os.killpg(process.pid, signal.SIGTERM)
        try:
            stdout, stderr = process.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            if os.name != "nt":
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
            stdout, stderr = process.communicate()
    (output / "stdout.txt").write_bytes(stdout)
    (output / "stderr.txt").write_bytes(stderr)
    details.update(returncode=process.returncode, stdout_sha256=sha256(stdout).hexdigest(),
                   stderr_sha256=sha256(stderr).hexdigest())
    if timed_out:
        if report_path.is_file() and report_path.stat().st_size <= 20_000_000:
            try:
                details.update(json.loads(report_path.read_text(encoding="utf-8")))
            except (ValueError, OSError):
                pass
        state = "FAIL" if details["outcomes"].get("failed", 0) else "BLOCKED"
        return dict(details, status=state, reason="Suite timeout; partial inventory/outcomes retained; owned process group stopped")
    if not report_path.is_file() or report_path.stat().st_size > 20_000_000:
        return dict(details, status="BLOCKED", reason="No valid fresh pytest report; inspect dependency/collection logs")
    try:
        details.update(json.loads(report_path.read_text(encoding="utf-8")))
    except (ValueError, OSError):
        return dict(details, status="FAIL", reason="Malformed child report")
    if details["collection_errors"] and all(item["kind"] == "missing-dependency" for item in details["collection_errors"]):
        return dict(details, status="BLOCKED", reason="Missing collection dependencies; no full-suite certification")
    if details["configuration_errors"]:
        return dict(details, status="FAIL", reason="Pytest configuration masks expected outcomes")
    if process.returncode not in (0, 5) or details["collection_errors"] or not details["collected"] or any(details["outcomes"][key] for key in ("failed", "skipped", "xfailed", "xpassed")):
        return dict(details, status="FAIL", reason="Empty, failed, errored or skipped suite")
    if collect_only:
        return dict(details, status="PASS", mode="inventory-only", reason="Complete inventory; not a test execution")
    if set(details["deselected"]) != set(details["pending_live"]):
        return dict(details, status="FAIL", reason="Unexpected deselection outside pending live cases")
    if details["outcomes"]["passed"] != len(details["selected"]):
        return dict(details, status="FAIL", reason="Execution did not account for every selected test")
    if details["pending_live"]:
        return dict(details, status="BLOCKED", reason="Live cases inventoried but not authorized/executed")
    return dict(details, status="PASS", reason="Every collected test executed and passed")


def test_files(root, suite):
    """GOV-02: discover test files, including new and unmarked suites."""
    found = set()
    for origin in suite.paths:
        path = root / origin
        candidates = [path] if path.is_file() else path.rglob("*.py")
        for candidate in candidates:
            name = candidate.relative_to(root).as_posix()
            if any(name == ignored or name.startswith(ignored.rstrip("/") + "/") for ignored in suite.ignore):
                continue
            if candidate.name.startswith("test") or candidate.name.endswith("_test.py"):
                found.add(name)
    return sorted(found)


def default_suites(root, team_python=None, runtime_python=None, upstream_python=None):
    """GOV-02: three origins; upstream uses its own unchanged pytest config."""
    suffix = "Scripts/python.exe" if os.name == "nt" else "bin/python"
    runtime = runtime_python or str(root / ".venv-runtime" / suffix)
    upstream = upstream_python or str(root / ".venv-upstream" / suffix)
    return (
        Suite("team-offline", ("test/offline",), team_python or sys.executable, "papertrace.pytest.ini"),
        Suite("team-runtime", ("test",), runtime, "papertrace.pytest.ini", ("pytest_socket", "pytest_asyncio.plugin"), ("test/offline",)),
        Suite("upstream", ("tests", "packages"), upstream, "pyproject.toml",
              ("pytest_socket", "pytest_asyncio.plugin", "pytest_recording.plugin", "pytest_subtests", "pytest_timeout", "typeguard._pytest_plugin")),
    )


def snapshot_base(root, base, destination, timeout):
    """GOV-02/INV-06: immutable Git base, no worktree/reset or symlink extraction."""
    if not re.fullmatch(r"[0-9a-f]{40}", base):
        raise ValueError("full lowercase Git SHA required")
    process = subprocess.run(["git", "-C", str(root), "archive", "--format=tar", base],
                             env=isolated_environment(root, destination.parent / "archive-state"),
                             capture_output=True, timeout=timeout, check=False)
    if process.returncode or len(process.stdout) > 500_000_000:
        raise ValueError("baseline archive unavailable or too large")
    with tarfile.open(fileobj=io.BytesIO(process.stdout)) as archive:
        for member in archive.getmembers():
            target = destination / member.name
            if not target.resolve().is_relative_to(destination.resolve()) or not (member.isfile() or member.isdir()):
                raise ValueError("non-regular or escaping baseline member")
        archive.extractall(destination, filter="data")


def tree_digest(root):
    """GOV-02: bind inputs and detect files changing during verification."""
    digest = sha256()
    names = set()
    for folder in ("src", "test", "tests", "packages", "prompts", "scripts"):
        for path in (root / folder).rglob("*"):
            if path.is_file() and not any(p in {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"} or p.endswith(".egg-info") for p in path.relative_to(root).parts):
                names.add(path.relative_to(root).as_posix())
    for path in root.iterdir():
        if path.is_file() and (path.suffix in {".ini", ".toml", ".lock", ".in"} or path.name in {"AGENTS.md", "Prompt.md", "opencode.jsonc"}):
            names.add(path.name)
    for name in sorted(names):
        path = root / name
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError("symlink input cannot certify regression")
        digest.update(name.encode() + b"\0" + sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def prepare_generated_metadata(root, baseline):
    """GOV-02: reuse actual SCM build metadata omitted by git archive (not tests/code)."""
    records = []
    for config in [baseline / "pyproject.toml", *(baseline / "packages").glob("*/pyproject.toml")]:
        if not config.is_file():
            continue
        relative = tomllib.loads(config.read_text()).get("tool", {}).get("setuptools_scm", {}).get("version_file")
        if not isinstance(relative, str) or not relative.startswith("src/") or not relative.endswith("/version.py") or ".." in Path(relative).parts:
            continue
        target = config.parent / relative
        name = target.relative_to(baseline)
        source = root / name
        if not target.exists() and source.is_file() and not source.is_symlink():
            target.parent.mkdir(parents=True, exist_ok=True)
            data = source.read_bytes()
            if len(data) > 32_768:
                raise ValueError("generated version metadata is unexpectedly large")
            target.write_bytes(data)
            records.append({"path": name.as_posix(), "sha256": sha256(data).hexdigest(),
                            "source": "actual local setuptools_scm build; reused only for prior collection"})
    return records


def run_full(root, base, output, suites=None, timeout=300, run_live=False,
             team_python=None, runtime_python=None, upstream_python=None):
    """GOV-02: full can PASS only when all origins and every prior node pass."""
    root, output = Path(root).resolve(), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    suites = suites or default_suites(root, team_python, runtime_python, upstream_python)
    # Keep the venv launcher path (do not realpath its Python symlink). Baseline
    # collection changes cwd and must not reinterpret a relative launcher there.
    suites = tuple(replace(suite, python=(suite.python if Path(suite.python).is_absolute() else
                   (shutil.which(suite.python) or suite.python) if not any(char in suite.python for char in ("/", "\\")) else
                   os.path.abspath(root / suite.python))) for suite in suites)
    before = tree_digest(root)
    reports, prior, missing = [], [], []
    with tempfile.TemporaryDirectory(prefix="prior-", dir=output) as temporary:
        baseline = Path(temporary)
        try:
            snapshot_base(root, base, baseline, timeout)
            generated_metadata = prepare_generated_metadata(root, baseline)
        except (ValueError, OSError, subprocess.TimeoutExpired) as error:
            return {"status": "BLOCKED", "reason": "Prior inventory unavailable", "error_type": type(error).__name__,
                    "suites": reports, "missing_prior": [], "total_collected": 0, "total_passed": 0}
        for suite in suites:
            current_files, prior_files = test_files(root, suite), test_files(baseline, suite)
            if not current_files and not prior_files:
                reports.append({"suite": suite.name, "status": "NOT_REQUIRED", "collected": [], "reason": "No test files in either tree"})
                continue
            if prior_files:
                inventory = run_suite(baseline, suite, output / (suite.name + "-prior"), timeout, collect_only=True)
                prior.append(inventory)
            else:
                inventory = {"status": "PASS", "collected": []}
            if current_files:
                current = run_suite(root, suite, output / suite.name, timeout, run_live,
                                    prior_live=inventory.get("pending_live", []))
            else:
                current = {"suite": suite.name, "status": "FAIL", "collected": [], "reason": "Prior test files removed"}
            if not current.get("collection_errors") and current["status"] != "BLOCKED":
                missing.extend(suite.name + ":" + node for node in sorted(set(inventory["collected"]) - set(current["collected"])))
            reports.append(current)
    after = tree_digest(root)
    states = [item["status"] for item in reports + prior]
    status = "FAIL" if missing or before != after or "FAIL" in states else "BLOCKED" if "BLOCKED" in states else "PASS"
    if not any(item.get("collected") for item in reports):
        status = "BLOCKED"
    summary = {"status": status, "base": base, "source_tree_sha256": before,
               "generated_metadata": generated_metadata,
               "inputs_unchanged": before == after, "missing_prior": missing,
               "total_collected": sum(len(item.get("collected", [])) for item in reports),
               "total_passed": sum(item.get("outcomes", {}).get("passed", 0) for item in reports),
               "suites": reports, "prior_inventories": prior, "live_authorized_by_operator": run_live,
               "limits": ["Offline socket guard is not an OS sandbox", "Collection-only is not a passed prior suite",
                          "--run-live is an explicit operator action, requiring prior data/model/budget approval"]}
    (output / "full-regression.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main(argv=None):
    """GOV-02: explicit full runner; exit 2 is unmet evidence, not success."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--base", required=True, help="Exact full SHA of the prior accepted round")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--team-python", default=sys.executable)
    parser.add_argument("--runtime-python", default=None)
    parser.add_argument("--upstream-python", default=None)
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--run-live", action="store_true", help="Explicit operator action AFTER real human approval of data, model, budget and calls; may incur charges")
    args = parser.parse_args(argv)
    try:
        if not re.fullmatch(r"[0-9a-f]{40}", args.base) or not 0 < args.timeout <= 1800:
            raise ValueError("invalid literal SHA or timeout")
        root = args.root.resolve()
        output = (args.output or root / ".local/full-regression").resolve()
        report = run_full(root, args.base, output, timeout=args.timeout, run_live=args.run_live,
                          team_python=args.team_python, runtime_python=args.runtime_python,
                          upstream_python=args.upstream_python)
    except (OSError, ValueError, KeyError, TypeError) as error:
        report = {"status": "FAIL", "error_type": type(error).__name__, "reason": "Invalid inputs or unavailable full regression"}
    code = {"PASS": 0, "FAIL": 1, "BLOCKED": 2}[report["status"]]
    print(json.dumps(dict(report, scope="full", exit_code=code), sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
