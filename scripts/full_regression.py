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
import stat
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

DIAGNOSTICS_SCHEMA_VERSION = 1
DIAGNOSTICS_TRANSPORT_SCHEMA_VERSION = 1
_EVENT_LIMIT = 1_228_800
_MANIFEST_LIMIT = 65_536
_BUNDLE_LIMIT = 7_766_016
_DIAGNOSTICS = {}


def _safe_text(value, limit=512):
    """Bound untrusted display text; remove host paths and control characters."""
    text = str(value)
    text = re.sub(r"[A-Za-z]:[\\/][^\s'\"<>]*", "[path]", text)
    text = re.sub(r"\\\\[^\s'\"<>]+", "[path]", text)
    text = re.sub(r"(?<![\w:])/(?:[^\s'\"<>]+)", "[path]", text)
    text = re.sub(r"(?:gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,})", "[credential]", text)
    text = " ".join("".join(c if c >= " " and c != "\x7f" else " " for c in text).split())
    return text.encode("utf-8")[:limit].decode("utf-8", errors="ignore")


def _diagnostic_error(error):
    # Deliberately omit arbitrary exception bodies. Pytest errors use only its
    # concise crash message, never captured streams, locals or full tracebacks.
    return {"type": _safe_text(type(error).__name__, 100),
            "detail_state": "unavailable", "detail": None}


def _report_error(report):
    crash = getattr(getattr(report, "longrepr", None), "reprcrash", None)
    message = getattr(crash, "message", None)
    if not isinstance(message, str):
        return {"type": "PytestFailure", "detail_state": "unavailable", "detail": None}
    # Exception messages can contain credentials or document text without any
    # recognizable syntax. Export only the exception class; raw local logs stay
    # local. Missing bodies are explicit rather than a claim of full redaction.
    match = re.match(r"(?:E\s+)?([A-Za-z][A-Za-z0-9_]*(?:Error|Exception))\b", message)
    return {"type": match.group(1) if match else "PytestFailure", "detail_state": "unavailable", "detail": None}


def _emit_diagnostic(event, **fields):
    """Child-only append. Diagnostics errors never change the legacy outcome."""
    destination = os.environ.get("PAPERTRACE_DIAGNOSTIC_PATH")
    if not destination:
        return
    try:
        path = Path(destination)
        if path.is_symlink() or not path.is_file():
            return
        if not _DIAGNOSTICS:
            seed = path.with_name("manifest.json")
            if seed.is_symlink() or seed.stat().st_size > _MANIFEST_LIMIT:
                return
            suite = json.loads(seed.read_text(encoding="utf-8"))["suite"]
            _DIAGNOSTICS.update(suite=_safe_text(suite, 100), truncated=False)
        data = {"schema_version": 1, "suite": _DIAGNOSTICS["suite"], "event": event, **fields}
        if event == "terminal":
            data["truncated"] = _DIAGNOSTICS["truncated"]
        raw = (json.dumps(data, ensure_ascii=True, separators=(",", ":")) + "\n").encode()
        bound = _EVENT_LIMIT if event == "terminal" else _EVENT_LIMIT - 2048
        if path.stat().st_size + len(raw) > bound:
            _DIAGNOSTICS["truncated"] = True
            return
        flags = os.O_WRONLY | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        try:
            if stat.S_ISREG(os.fstat(descriptor).st_mode):
                os.write(descriptor, raw)
        finally:
            os.close(descriptor)
    except (OSError, ValueError, KeyError, TypeError):
        return


def _prepare_diagnostics(output, suite):
    directory = output / "diagnostics"
    try:
        if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
            directory.unlink()
        directory.mkdir(exist_ok=True)
        problem = None
        for name in ("events.jsonl", "manifest.json"):
            path = directory / name
            if path.is_symlink() or path.is_file():
                path.unlink()
            elif path.exists():
                problem = ValueError("Non-regular diagnostics entry")
        if problem is None:
            (directory / "events.jsonl").write_bytes(b"")
        # The seed carries only an advisory suite name, no trusted provenance.
        path = directory / "manifest.json"
        if not path.exists():
            path.write_text(json.dumps({"suite": _safe_text(suite, 100)}), encoding="utf-8")
        return problem
    except (OSError, ValueError) as error:
        return error


def _package_diagnostics(output, suite, report, mode, error=None, identity=None):
    directory = output / "diagnostics"
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("Unsafe diagnostics directory")
    path = directory / "events.jsonl"
    events, size, torn, truncated, terminal = [], 0, False, False, False
    try:
        # Explicit post-child stat seam; bounds are checked before reading.
        metadata = path.stat()
        if path.is_symlink() or not stat.S_ISREG(metadata.st_mode) or metadata.st_size > _EVENT_LIMIT:
            raise ValueError("Unsafe or oversized events artifact")
        size = metadata.st_size
        lines = path.read_bytes().splitlines()
        for index, raw in enumerate(lines):
            if not raw.strip():
                continue
            try:
                item = json.loads(raw)
                if not isinstance(item, dict):
                    raise ValueError("Non-object event")
                events.append(item)
            except (ValueError, UnicodeError):
                if index != len(lines) - 1:
                    raise ValueError("Malformed diagnostic event") from None
                torn = True
        terminal = bool(events and events[-1].get("event") == "terminal" and not torn)
        truncated = any(e.get("truncated") is True for e in events)
    except (OSError, ValueError) as problem:
        error = error or problem
        # A failed inspection cannot certify bytes. Omit only a regular file,
        # never recursively remove an unexpected directory or follow a link.
        if path.is_symlink() or path.is_file():
            path.unlink(missing_ok=True)
        events, size, terminal = [], 0, False
    legacy = output / "pytest-report.json"
    try:
        if "returncode" not in report:
            classification = "not_started"
        elif not legacy.is_file():
            classification = "missing"
        elif legacy.stat().st_size > 20_000_000:
            classification = "oversized"
        else:
            json.loads(legacy.read_text(encoding="utf-8"))
            classification = "present"
    except (OSError, ValueError):
        classification = "malformed"
    if classification != "present":
        error = error or ValueError("Legacy report unavailable")
    nodes = {e.get("nodeid") for e in events if isinstance(e.get("nodeid"), str)}
    complete = terminal and not error and not torn and not truncated
    state = "complete" if complete else "partial" if events else "unavailable"
    identity = {key: (identity or {}).get(key) for key in ("target_sha", "control_sha", "base_sha", "source_tree_sha256", "job_key")}
    manifest = {
        "schema_version": 1, "suite": _safe_text(suite, 100), "mode": mode,
        "advisory": True, "trusted": False, "status": state, "identity": identity,
        "legacy": {"status": report["status"], "report": classification},
        "events": {"bytes": size, "terminal_present": terminal, "torn_tail_ignored": torn, "truncated": truncated, "sampled": False},
        "counts": {"unique_nodes_retained": len(nodes), "unique_nodes_exact": complete,
                   "pending_live": len(report.get("pending_live", [])), "collection_errors": len(report.get("collection_errors", []))},
        "limits": {"events_bytes": _EVENT_LIMIT, "manifest_bytes": _MANIFEST_LIMIT, "bundle_bytes": _BUNDLE_LIMIT},
        "error": _diagnostic_error(error) if error else None,
    }
    destination = directory / "manifest.json"
    if directory.is_symlink() or destination.is_symlink() or (destination.exists() and not destination.is_file()):
        raise ValueError("Unsafe diagnostics manifest path")
    raw = json.dumps(manifest, sort_keys=True).encode()
    if len(raw) > _MANIFEST_LIMIT:
        raise ValueError("Manifest budget exceeded")
    destination.write_bytes(raw)
    return {"status": state, "trusted": False, "bundle_bytes": size + len(raw)}


def run_suite(root, suite, output, timeout=300, run_live=False, collect_only=False, prior_live=(), diagnostic_identity=None):
    """Keep legacy certification authoritative; diagnostics are advisory only."""
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    problem = _prepare_diagnostics(output, suite.name)
    report = _run_suite_legacy(root, suite, output, timeout, run_live, collect_only, prior_live,
                               diagnostic_path=None if problem else output / "diagnostics/events.jsonl")
    try:
        report["diagnostics"] = _package_diagnostics(output, suite.name, report,
                                                    "inventory-only" if collect_only else "execution", problem, diagnostic_identity)
    except (OSError, ValueError, KeyError, TypeError):
        report["diagnostics"] = {"status": "unavailable", "trusted": False, "reason": "Diagnostic packaging unavailable"}
    return report


def qualify_diagnostics_artifacts(root, output, *, expected_identity, suites=("team-offline", "team-runtime", "upstream")):
    """Withhold unsafe, oversized or stale artifacts; never certify test success."""
    root, output = Path(root).resolve(), Path(output)
    if (output.is_symlink() or not output.absolute().is_relative_to(root)
            or not output.resolve().is_relative_to(root)
            or any(parent.is_symlink() for parent in output.absolute().parents if parent.is_relative_to(root))):
        return {"status": "withheld", "files": [], "reasons": ["Unsafe artifact root"]}
    expected = dict(expected_identity)
    for key in ("target_sha", "control_sha", "base_sha"):
        if key not in expected or not (expected[key] in (None, "unknown") or isinstance(expected[key], str) and re.fullmatch(r"[0-9a-f]{40}", expected[key])):
            raise ValueError("Independent diagnostics identity required")
    actual_tree = tree_digest(root)
    if expected.get("source_tree_sha256", actual_tree) != actual_tree:
        return {"status": "withheld", "files": [], "reasons": ["Source tree provenance mismatch"]}
    expected["source_tree_sha256"] = actual_tree
    files, total = [], 0
    try:
        for suite in suites:
            if suite not in {"team-offline", "team-runtime", "upstream"}:
                raise ValueError("Unknown diagnostics suite")
            directory = output / suite / "diagnostics"
            if any(p.is_symlink() for p in (output / suite, directory)):
                raise ValueError("Unsafe diagnostic path")
            for name, limit in (("events.jsonl", _EVENT_LIMIT), ("manifest.json", _MANIFEST_LIMIT)):
                path = directory / name
                metadata = path.stat()
                if path.is_symlink() or not stat.S_ISREG(metadata.st_mode) or metadata.st_size > limit or not path.resolve().is_relative_to(output.resolve()):
                    raise ValueError("Unsafe or oversized diagnostics")
                total += metadata.st_size
                files.append(path.relative_to(output).as_posix())
            manifest = json.loads((directory / "manifest.json").read_bytes())
            if not all(manifest.get("identity", {}).get(key) == value for key, value in expected.items()):
                raise ValueError("Diagnostics provenance mismatch")
            if manifest.get("schema_version") != 1 or manifest.get("suite") != suite or manifest.get("advisory") is not True or manifest.get("trusted") is not False or manifest.get("status") not in {"complete", "partial"}:
                raise ValueError("Invalid advisory manifest")
        if total > _BUNDLE_LIMIT:
            raise ValueError("Diagnostics bundle budget exceeded")
    except (OSError, ValueError, KeyError, TypeError):
        return {"status": "withheld", "files": [], "reasons": ["Diagnostics provenance, path or budget validation failed"]}
    return {"status": "qualified", "files": files, "reasons": []}


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
    _DIAGNOSTICS.clear()
    _STATE.update(collected=[], pending_live=[], selected=[], deselected=[], configuration_errors=[],
                  outcomes={"passed": 0, "failed": 0, "skipped": 0, "xfailed": 0, "xpassed": 0}, collection_errors=[])
    if config.getoption("runxfail", default=False):
        _STATE["configuration_errors"].append("--runxfail masks expected-failure outcomes")


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(session, config, items):
    """GOV-02: inventory includes unmarked and parametrized cases."""
    _STATE["collected"] = [item.nodeid for item in items]
    for item in items:
        _emit_diagnostic("collection", nodeid=_safe_text(item.nodeid, 1024))
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
        _emit_diagnostic("collection_error", nodeid=_safe_text(report.nodeid, 1024), kind=kind, error=_report_error(report))


def pytest_runtest_logreport(report):
    """GOV-02: setup/teardown errors also block the gate."""
    outcome = ("xfailed" if report.skipped else "xpassed") if getattr(report, "wasxfail", None) else report.outcome
    fields = {"nodeid": _safe_text(report.nodeid, 1024), "when": report.when,
              "outcome": outcome, "error": _report_error(report) if report.failed else None}
    context = getattr(report, "context", None)
    if context is not None:
        fields["subtest"] = _safe_text(getattr(context, "msg", None) or str(context))
    _emit_diagnostic("report", **fields)
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
    _emit_diagnostic("terminal")
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


def _run_suite_legacy(root, suite, output, timeout=300, run_live=False, collect_only=False, prior_live=(), diagnostic_path=None):
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
    if diagnostic_path is not None:
        environment["PAPERTRACE_DIAGNOSTIC_PATH"] = str(diagnostic_path)
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
    target = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, check=False)
    target_sha = target.stdout.decode(errors="replace").strip()
    control_sha = os.environ.get("PAPERTRACE_CONTROL_SHA")
    identity = dict(target_sha=target_sha if re.fullmatch(r"[0-9a-f]{40}", target_sha) else None,
                    control_sha=control_sha if control_sha and re.fullmatch(r"[0-9a-f]{40}", control_sha) else None,
                    base_sha=base, source_tree_sha256=before, job_key=None)
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
                inventory = run_suite(baseline, suite, output / (suite.name + "-prior"), timeout, collect_only=True,
                                      diagnostic_identity=identity)
                prior.append(inventory)
            else:
                inventory = {"status": "PASS", "collected": []}
            if current_files:
                current = run_suite(root, suite, output / suite.name, timeout, run_live,
                                    prior_live=inventory.get("pending_live", []), diagnostic_identity=identity)
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
    diagnostics = {}
    bundle_bytes = 0
    for item, suffix in [(item, "") for item in reports] + [(item, "-prior") for item in prior]:
        name = item["suite"] + suffix
        diagnostics[name] = item.get("diagnostics", {"status": "unavailable", "trusted": False})
        bundle_bytes += diagnostics[name].get("bundle_bytes", 0)
    summary["diagnostics"] = {"bundle_bytes": bundle_bytes, "suites": diagnostics}
    (output / "full-regression.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main(argv=None):
    """GOV-02: explicit full runner; exit 2 is unmet evidence, not success."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--base", help="Exact full SHA of the prior accepted round")
    parser.add_argument("--qualify-diagnostics", action="store_true")
    parser.add_argument("--expected-target-sha")
    parser.add_argument("--expected-control-sha")
    parser.add_argument("--expected-base-sha")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--team-python", default=sys.executable)
    parser.add_argument("--runtime-python", default=None)
    parser.add_argument("--upstream-python", default=None)
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--run-live", action="store_true", help="Explicit operator action AFTER real human approval of data, model, budget and calls; may incur charges")
    args = parser.parse_args(argv)
    if args.qualify_diagnostics:
        try:
            expected = {"target_sha": args.expected_target_sha, "control_sha": args.expected_control_sha,
                        "base_sha": args.expected_base_sha}
            if not all(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value) for value in expected.values()) or args.output is None:
                raise ValueError("Missing independent provenance")
            plan = qualify_diagnostics_artifacts(args.root.resolve(), args.output.absolute(), expected_identity=expected,
                                                 suites=("team-offline", "team-runtime", "upstream"))
            if plan.get("status") not in {"qualified", "withheld"}:
                raise ValueError("Unknown qualification result")
            code = 0 if plan["status"] == "qualified" else 1
        except (OSError, ValueError, KeyError, TypeError):
            plan, code = {"status": "withheld", "files": [], "reasons": ["Qualification validation unavailable"]}, 2
        print(json.dumps(plan, sort_keys=True))
        return code
    try:
        if not isinstance(args.base, str) or not re.fullmatch(r"[0-9a-f]{40}", args.base) or not 0 < args.timeout <= 1800:
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
