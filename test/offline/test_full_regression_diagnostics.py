"""Shared full-regression diagnostics: bounded, advisory, offline RED contract.

This is test-preparation code only. Synthetic pytest repositories live under
``tmp_path``; no helper from ``test/offline`` is imported and no diagnostics
fallback is implemented here. The trusted runner is loaded at runtime so a
missing future feature is reported as availability RED instead of an import
error during collection.
"""

import copy
import importlib.util
import json
import re
import shlex
import subprocess
import sys
import textwrap
import tracemalloc
from dataclasses import replace
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]

EVENTS_LIMIT = 1_228_800
MANIFEST_LIMIT = 65_536
BUNDLE_LIMIT = 7_766_016
SUITES = ("team-offline", "team-runtime", "upstream")
SIX_ARTIFACT_PATHS = tuple(
    f"target/.local/full-regression/{suite}/diagnostics/{name}"
    for suite in SUITES
    for name in ("events.jsonl", "manifest.json")
)
SIX_ARTIFACT_PATHS_TEXT = "\n".join(SIX_ARTIFACT_PATHS)
TRANSPORT_MARKER_ATTRIBUTE = "DIAGNOSTICS_TRANSPORT_SCHEMA_VERSION"
TRANSPORT_QUALIFICATION_ATTRIBUTE = "qualify_diagnostics_artifacts"
QUALIFY_CONDITIONS = {
    "failure()",
    "failure() || cancelled()",
    "cancelled() || failure()",
}
TRUSTED_TARGET_REFS = {"$PAPERTRACE_HEAD", "${{ env.PAPERTRACE_HEAD }}"}
TRUSTED_CONTROL_REFS = {"${{ steps.control.outputs.sha }}"}
TRUSTED_BASE_REFS = {"${{ steps.control.outputs.base }}"}
FORBIDDEN_DIAGNOSTIC_KEYS = {
    "caplog",
    "captured",
    "environment",
    "locals",
    "longrepr",
    "longreprtext",
    "stderr",
    "stdout",
}


def runner():
    """Load the existing trusted runner without importing a missing API."""
    path = ROOT / "scripts/full_regression.py"
    assert path.is_file(), "GOV-02: trusted local full-regression runner is missing"
    spec = importlib.util.spec_from_file_location(
        "papertrace_shared_regression_diagnostics_runner", path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def require_runner_diagnostics(module):
    """Only the exact absent feature is availability RED; later errors stay visible."""
    marker = getattr(module, "DIAGNOSTICS_SCHEMA_VERSION", None)
    if marker is None:
        pytest.fail(
            "AVAILABILITY RED: scripts/full_regression.py does not yet expose "
            "DIAGNOSTICS_SCHEMA_VERSION; bounded advisory diagnostics are not implemented.",
            pytrace=False,
        )
    assert marker == 1


def require_transport_qualification(module):
    """The pre-upload qualification handoff is a separately gated proposed entry."""
    marker = getattr(module, TRANSPORT_MARKER_ATTRIBUTE, None)
    entry = getattr(module, TRANSPORT_QUALIFICATION_ATTRIBUTE, None)
    if marker is None or not callable(entry):
        pytest.fail(
            "AVAILABILITY RED: scripts/full_regression.py does not yet expose "
            f"{TRANSPORT_MARKER_ATTRIBUTE} and callable {TRANSPORT_QUALIFICATION_ATTRIBUTE}; "
            "pre-upload diagnostics qualification is not implemented.",
            pytrace=False,
        )
    assert marker == 1


def fixture_suite(module, tmp_path, source, *, plugins=("pytest_socket",), name="fixture"):
    (tmp_path / "test").mkdir(exist_ok=True)
    (tmp_path / "test/test_sample.py").write_text(source, encoding="utf-8")
    (tmp_path / "pytest.ini").write_text(
        "[pytest]\nmarkers =\n    offline: offline\n    live_api: needs approved provider\n",
        encoding="utf-8",
    )
    return module.Suite(name, ("test",), sys.executable, "pytest.ini", tuple(plugins))


def run_fixture(module, tmp_path, source, *, timeout=20, collect_only=False,
                run_live=False, output="evidence", name="fixture", plugins=("pytest_socket",)):
    suite = fixture_suite(module, tmp_path, source, plugins=plugins, name=name)
    report = module.run_suite(
        tmp_path, suite, tmp_path / output, timeout=timeout,
        run_live=run_live, collect_only=collect_only,
    )
    return report, tmp_path / output


def git(root, *args):
    return subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True,
        check=True, timeout=20,
    ).stdout.strip()


def commit_fixture(module, tmp_path, files):
    (tmp_path / "test").mkdir(exist_ok=True)
    for relative, source in files.items():
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding="utf-8")
    (tmp_path / "pytest.ini").write_text(
        "[pytest]\nmarkers =\n    offline: offline\n    live_api: needs approved provider\n",
        encoding="utf-8",
    )
    git(tmp_path, "init", "-q")
    git(tmp_path, "add", ".")
    git(
        tmp_path, "-c", "user.name=Synthetic fixture", "-c", "user.email=fixture@example.invalid",
        "commit", "-qm", "synthetic prior suite",
    )
    return git(tmp_path, "rev-parse", "HEAD")


def fake_python(tmp_path, name, body):
    path = tmp_path / name
    path.write_text(f"#!{sys.executable}\n{body}\n", encoding="utf-8")
    path.chmod(0o755)
    return path


def builtin_subtest_source(marker):
    return textwrap.dedent(
        f"""
        from pathlib import Path

        def test_subtests(subtests):
            Path({str(marker)!r}).write_text("ran", encoding="utf-8")
            for index in range(3):
                with subtests.test(msg=f"case {{index}}"):
                    assert index != 1, "subtest boom"
        """
    )


def read_manifest(output):
    path = Path(output) / "diagnostics/manifest.json"
    data = path.read_bytes()
    assert len(data) <= MANIFEST_LIMIT, "manifest.json exceeded its hard byte budget"
    return json.loads(data.decode("utf-8"))


def require_manifest(output):
    path = Path(output) / "diagnostics/manifest.json"
    assert path.is_file(), "BEHAVIOR RED: fresh diagnostics/manifest.json was not produced"
    return read_manifest(output)


def read_events(output):
    path = Path(output) / "diagnostics/events.jsonl"
    data = path.read_bytes()
    assert len(data) <= EVENTS_LIMIT, "events.jsonl exceeded its hard byte budget"
    return [json.loads(line) for line in data.decode("utf-8").splitlines() if line.strip()]


def event_data(output):
    return (Path(output) / "diagnostics/events.jsonl").read_bytes()


def read_events_tolerating_torn(output, manifest):
    """A killed child may leave one incomplete tail line, explicitly flagged."""
    data = event_data(output)
    assert len(data) <= EVENTS_LIMIT
    lines = data.splitlines()
    events = []
    for index, raw in enumerate(lines):
        if not raw.strip():
            continue
        try:
            events.append(json.loads(raw.decode("utf-8")))
        except (UnicodeDecodeError, json.JSONDecodeError):
            assert index == len(lines) - 1
            assert manifest["events"]["torn_tail_ignored"] is True
    return events


def walk_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key).lower()
            yield from walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_keys(child)


def assert_no_raw_report_material(value):
    keys = set(walk_keys(value))
    assert not (keys & FORBIDDEN_DIAGNOSTIC_KEYS), (
        "diagnostics must not embed longrepr/locals/environment/captured/raw output"
    )


def assert_explicit_identity(identity):
    for key, pattern in (
        ("target_sha", r"[0-9a-f]{40}"),
        ("control_sha", r"[0-9a-f]{40}"),
        ("base_sha", r"[0-9a-f]{40}"),
        ("source_tree_sha256", r"[0-9a-f]{64}"),
    ):
        assert key in identity, f"manifest identity must explicitly include {key}"
        value = identity[key]
        assert value is None or value == "unknown" or isinstance(value, str)
        if isinstance(value, str) and value != "unknown":
            assert re.fullmatch(pattern, value), f"{key} is not a literal trusted identity"
    job_key = identity.get("job_key")
    assert job_key is None or (isinstance(job_key, str) and not job_key.isdigit()), (
        "job_key must not be a numeric job_id"
    )


def assert_manifest_schema(manifest, *, suite=None, mode=None):
    assert manifest["schema_version"] == 1
    assert manifest["advisory"] is True
    assert manifest["trusted"] is False
    assert manifest["status"] in {"complete", "partial", "unavailable"}
    assert manifest["mode"] in {"execution", "inventory-only", "unknown"}
    if suite is not None:
        assert manifest["suite"] == suite
    if mode is not None:
        assert manifest["mode"] == mode
    assert manifest["limits"] == {
        "events_bytes": EVENTS_LIMIT,
        "manifest_bytes": MANIFEST_LIMIT,
        "bundle_bytes": BUNDLE_LIMIT,
    }
    events = manifest["events"]
    assert isinstance(events["bytes"], int) and 0 <= events["bytes"] <= EVENTS_LIMIT
    for key in ("terminal_present", "torn_tail_ignored", "truncated", "sampled"):
        assert isinstance(events[key], bool)
    counts = manifest["counts"]
    assert isinstance(counts["unique_nodes_retained"], int)
    assert isinstance(counts["unique_nodes_exact"], bool)
    assert isinstance(counts["pending_live"], int)
    assert isinstance(counts["collection_errors"], int)
    assert manifest["legacy"]["report"] in {
        "present", "missing", "malformed", "oversized", "not_started",
    }
    assert_no_raw_report_material(manifest)


def assert_error_record(error):
    if error is None:
        return
    assert error["type"]
    assert error["detail_state"] in {"available", "truncated", "unavailable"}
    if error["detail_state"] == "unavailable":
        assert error["detail"] is None
    else:
        detail = error["detail"]
        assert isinstance(detail, str)
        assert len(detail.encode("utf-8")) <= 512
        assert "\n" not in detail and "\r" not in detail and "\x1b" not in detail


def assert_report_event(event):
    assert event["schema_version"] == 1
    assert event["suite"]
    assert event["event"] == "report"
    assert event["when"] in {"setup", "call", "teardown"}
    assert event["nodeid"]
    assert event["outcome"] in {"passed", "failed", "skipped", "xfailed", "xpassed"}
    subtest = event.get("subtest")
    if subtest is not None:
        assert isinstance(subtest, str)
        assert 0 < len(subtest.encode("utf-8")) <= 512
        assert "\n" not in subtest and "\r" not in subtest and "\x1b" not in subtest
    assert_error_record(event.get("error"))


def load_workflows():
    directory = ROOT / ".github/workflows"
    return [
        (path, yaml.safe_load(path.read_text(encoding="utf-8")))
        for path in sorted(directory.glob("*.y*ml"))
        if path.is_file()
    ]


def artifact_paths(step):
    value = (step.get("with") or {}).get("path", "")
    lines = value if isinstance(value, list) else str(value).splitlines()
    return [str(line).strip() for line in lines if str(line).strip()]


class MissingDiagnosticsTransport(AssertionError):
    """The real workflow has no complete current-run diagnostics transport yet."""


def normalize_condition(value):
    text = str(value or "").strip()
    if text.startswith("${{") and text.endswith("}}"):
        text = text[3:-2].strip()
    text = text.replace('"', "'")
    for operator in ("||", "&&", "=="):
        text = re.sub(rf"\s*{re.escape(operator)}\s*", f" {operator} ", text)
    return " ".join(text.split())


def is_regression_gate(step):
    run = str(step.get("run", ""))
    return (
        ".control/scripts/gates.py" in run
        and "--gate regression" in run
        and "--scope full" in run
    )


def is_trusted_validation(step):
    run = str(step.get("run", ""))
    return (
        "BASE_VERIFIER_UPGRADE_REQUIRED" in run
        and ".control/scripts/full_regression.py" in run
    )


def is_qualification(step):
    run = str(step.get("run", ""))
    return ".control/scripts/full_regression.py" in run and "--qualify-diagnostics" in run


def all_upload_steps(workflow):
    found = []
    for job_name, job in (workflow.get("jobs") or {}).items():
        for index, step in enumerate(job.get("steps") or []):
            if not str(step.get("uses", "")).startswith("actions/upload-artifact@"):
                continue
            paths = artifact_paths(step)
            assert paths, f"artifact upload in {job_name} lacks an explicit path"
            found.append((job_name, index, step, paths))
    return found


def upload_overlaps_diagnostics(paths):
    for raw in paths:
        value = raw.strip().lower()
        if not value:
            continue
        if value.startswith(("target/.local", ".local")):
            return True
        if value in {"target", "target/", ".", "./", "*", "**"}:
            return True
        if any(
            token in value
            for token in (
                "diagnostics",
                "full-regression",
                "stdout.txt",
                "stderr.txt",
                "pytest-report.json",
            )
        ):
            return True
        if any(char in value for char in "*?[]") and (
            "target" in value or ".local" in value
        ):
            return True
    return False


def parse_supported_qualification_command(step):
    lines = []
    for raw in str(step.get("run", "")).splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        lines.append(line)
    assert lines, "qualification run has no executable command"
    assert lines[0] == "set -euo pipefail", "qualification must start with strict shell mode"
    commands = lines[1:]
    assert len(commands) == 1, (
        "qualification must be one explicit command; comments, echo/printf, exit and "
        "multi-line scripts are unsupported"
    )
    command = commands[0]
    for forbidden in (";", "&&", "||", "|", ">", "<", "`", "$(", "#"):
        assert forbidden not in command, f"unsupported shell token: {forbidden}"
    tokens = shlex.split(command)
    assert len(tokens) >= 2, "qualification command is incomplete"
    assert Path(tokens[0]).name in {"python", "python3"}, (
        "qualification must invoke the trusted Python entry"
    )
    assert tokens[1] == ".control/scripts/full_regression.py"
    assert tokens.count("--qualify-diagnostics") == 1
    allowed = {
        "--qualify-diagnostics",
        "--root",
        "--output",
        "--expected-target-sha",
        "--expected-control-sha",
        "--expected-base-sha",
    }
    flags = {}
    index = 2
    while index < len(tokens):
        argument = tokens[index]
        assert argument in allowed, f"unsupported qualification argument: {argument}"
        if argument == "--qualify-diagnostics":
            index += 1
            continue
        assert index + 1 < len(tokens), f"missing value for {argument}"
        flags[argument] = tokens[index + 1]
        index += 2
    assert flags.get("--root") == "$GITHUB_WORKSPACE/target", (
        "qualification must read the same target root as the upload"
    )
    assert flags.get("--output") == (
        "$GITHUB_WORKSPACE/target/.local/full-regression"
    ), "qualification must read the same output directory as the upload"
    assert flags.get("--expected-target-sha") in TRUSTED_TARGET_REFS
    assert flags.get("--expected-control-sha") in TRUSTED_CONTROL_REFS
    assert flags.get("--expected-base-sha") in TRUSTED_BASE_REFS
    for flag in (
        "--expected-target-sha",
        "--expected-control-sha",
        "--expected-base-sha",
    ):
        value = flags[flag].lower()
        assert "manifest" not in value
        assert ".json" not in value
        assert "target/.local" not in value
    return flags


def regression_gate_job(workflow):
    matches = []
    for job_name, job in (workflow.get("jobs") or {}).items():
        steps = job.get("steps") or []
        gates = [index for index, step in enumerate(steps) if is_regression_gate(step)]
        if gates:
            matches.append((job_name, job, steps, gates))
    assert len(matches) == 1, "exactly one job must contain the full regression gate"
    job_name, job, steps, gates = matches[0]
    assert len(gates) == 1, "exactly one regression gate step is supported"
    return job_name, job, steps, gates[0]


def validate_regression_diagnostics_workflow(workflow):
    """Validate the static ordered chain around the actual regression gate."""
    job_name, job, steps, gate_index = regression_gate_job(workflow)
    assert "if" not in job, "the regression job must not be conditionally skipped"
    gate = steps[gate_index]
    gate_id = gate.get("id")
    if not isinstance(gate_id, str) or not gate_id:
        raise MissingDiagnosticsTransport("regression gate has no referenced step id")
    assert "if" not in gate, (
        "the regression gate must be an unconditional ordinary step so its outcome "
        "proves this gate actually ran"
    )
    assert gate.get("continue-on-error") is not True
    gate_run = str(gate.get("run", ""))
    assert "set -euo pipefail" in gate_run
    for swallowed in ("|| true", "|| exit 0", "set +e"):
        assert swallowed not in gate_run

    trusted = [
        index for index in range(gate_index)
        if is_trusted_validation(steps[index])
    ]
    assert trusted, "trusted base-verifier validation must precede the regression gate"

    qualifications = [
        index for index in range(gate_index + 1, len(steps))
        if is_qualification(steps[index])
    ]
    if not qualifications:
        raise MissingDiagnosticsTransport("no pre-upload diagnostics qualification step")
    assert len(qualifications) == 1, "exactly one qualification step is supported"
    qualify_index = qualifications[0]
    qualify = steps[qualify_index]
    qualify_id = qualify.get("id")
    assert isinstance(qualify_id, str) and qualify_id
    assert normalize_condition(qualify.get("if", "")) in QUALIFY_CONDITIONS, (
        "qualification must run on failure and only explicitly supported cancellation policy"
    )
    parse_supported_qualification_command(qualify)

    related_uploads = [
        item for item in all_upload_steps(workflow)
        if upload_overlaps_diagnostics(item[3])
    ]
    if not related_uploads:
        raise MissingDiagnosticsTransport(
            "no diagnostics artifact upload after qualification"
        )
    assert len(related_uploads) == 1, (
        "exactly one diagnostics-overlapping upload is supported across the whole workflow"
    )
    upload_job, upload_index, upload, paths = related_uploads[0]
    assert upload_job == job_name, "diagnostics upload must stay in the regression job"
    assert upload_index > qualify_index, "diagnostics upload must follow qualification"
    upload_id = upload.get("id")
    assert isinstance(upload_id, str) and upload_id
    expected_conditions = {
        f"failure() && !cancelled() && steps.{gate_id}.outcome == 'failure' && "
        f"steps.{qualify_id}.outcome == 'success'",
        f"failure() && !cancelled() && (steps.{gate_id}.outcome == 'failure') && "
        f"steps.{qualify_id}.outcome == 'success'",
    }
    assert normalize_condition(upload.get("if", "")) in expected_conditions, (
        "upload must explicitly model failure()/cancelled() plus this gate's failure "
        "outcome and qualification success"
    )
    assert len(paths) == 6, "exactly six current-suite diagnostics files are supported"
    assert set(paths) == set(SIX_ARTIFACT_PATHS)
    for value in paths:
        assert value.startswith("target/.local/full-regression/")
        assert "/diagnostics/" in value
        assert value.endswith(("/events.jsonl", "/manifest.json"))
        assert not any(char in value for char in "*?[]")
        assert "-prior" not in value
        assert "rogue" not in value
    combined = "\n".join(paths).lower()
    for forbidden in (
        "stdout.txt", "stderr.txt", "pytest-report.json",
        "/home/", "tmp/", "cache", ".env", "credentials",
    ):
        assert forbidden not in combined
    assert (upload.get("with") or {}).get("if-no-files-found") in {
        None, "warn", "ignore",
    }
    hidden = (upload.get("with") or {}).get("include-hidden-files")
    assert hidden is True or hidden == "true", (
        "v4 hidden-file transport must be explicitly enabled for the .local paths"
    )

    summaries = [
        index for index in range(upload_index + 1, len(steps))
        if "GITHUB_STEP_SUMMARY" in str(steps[index].get("run", ""))
    ]
    if not summaries:
        raise MissingDiagnosticsTransport("no reachable summary after diagnostics upload")
    assert len(summaries) == 1, "exactly one diagnostics summary is supported"
    summary_index = summaries[0]
    summary = steps[summary_index]
    assert normalize_condition(summary.get("if", "")) == "always()"
    summary_run = str(summary.get("run", ""))
    for reference in (gate_id, qualify_id, upload_id):
        assert f"steps.{reference}.outcome" in summary_run
    assert "cancelled" in summary_run.lower() or "job.status" in summary_run
    assert summary.get("continue-on-error") is not True
    assert summary_index > upload_index > qualify_index > gate_index > trusted[-1]
    return {
        "job": job_name,
        "gate_index": gate_index,
        "qualify_index": qualify_index,
        "upload_index": upload_index,
        "summary_index": summary_index,
        "gate_id": gate_id,
        "qualify_id": qualify_id,
        "upload_id": upload_id,
    }


# ---------------------------------------------------------------------------
# Legacy controls: these pass before the diagnostics feature exists.
# ---------------------------------------------------------------------------


def test_legacy_success_verdict_and_raw_files_are_unchanged(tmp_path):
    module = runner()
    report, output = run_fixture(module, tmp_path, "def test_ok():\n    assert True\n")
    assert report["status"] == "PASS"
    assert report["outcomes"]["passed"] == 1
    assert report["collected"] == ["test/test_sample.py::test_ok"]
    for name in ("stdout.txt", "stderr.txt", "pytest-report.json"):
        assert (output / name).is_file(), f"existing raw local file {name} must remain"


def test_legacy_failure_phases_and_skip_verdicts_are_unchanged(tmp_path):
    module = runner()
    phases = textwrap.dedent(
        """
        import pytest

        @pytest.fixture
        def broken_setup():
            raise RuntimeError("setup boom")

        @pytest.fixture
        def broken_teardown():
            yield
            raise RuntimeError("teardown boom")

        def test_setup_failure(broken_setup):
            assert True

        def test_call_failure():
            assert 0 == 1, "call boom"

        def test_teardown_failure(broken_teardown):
            assert True
        """
    )
    report, _ = run_fixture(module, tmp_path, phases)
    assert report["status"] == "FAIL"
    assert report["outcomes"]["failed"] == 3
    assert report["outcomes"]["passed"] == 1

    skipped = "import pytest\n@pytest.mark.skip(reason='synthetic')\ndef test_skipped():\n    assert True\n"
    report, _ = run_fixture(module, tmp_path, skipped, output="skip-evidence")
    assert report["status"] == "FAIL"
    assert report["outcomes"]["skipped"] == 1

    xfail = "import pytest\n@pytest.mark.xfail(reason='synthetic')\ndef test_xfail():\n    assert False\n"
    report, _ = run_fixture(module, tmp_path, xfail, output="xfail-evidence")
    assert report["status"] == "FAIL"
    assert report["outcomes"]["xfailed"] == 1


def test_legacy_timeout_keeps_partial_inventory_and_outcomes(tmp_path):
    module = runner()
    source = "import time\ndef test_first_pass():\n    assert True\ndef test_later_hang():\n    time.sleep(30)\n"
    report, _ = run_fixture(module, tmp_path, source, timeout=1.5)
    assert report["status"] == "BLOCKED"
    assert len(report["collected"]) == 2
    assert report["outcomes"]["passed"] == 1
    assert "timeout" in report["reason"].lower()


def test_legacy_spawn_failure_is_blocked(tmp_path):
    module = runner()
    suite = fixture_suite(module, tmp_path, "def test_ok():\n    assert True\n")
    missing = replace(suite, python=str(tmp_path / "missing-interpreter"))
    report = module.run_suite(tmp_path, missing, tmp_path / "evidence", timeout=20)
    assert report["status"] == "BLOCKED"
    assert report["reason"] == "FileNotFoundError"


def test_legacy_missing_malformed_and_oversized_reports_are_classified(tmp_path):
    module = runner()
    cases = {
        "missing": "raise SystemExit(0)",
        "malformed": (
            "import os\nfrom pathlib import Path\n"
            "Path(os.environ['PAPERTRACE_SUITE_REPORT']).write_text("
            "'{\"collected\": [', encoding='utf-8')\n"
        ),
        "oversized": (
            "import os\nfrom pathlib import Path\n"
            "path = Path(os.environ['PAPERTRACE_SUITE_REPORT'])\n"
            "with path.open('wb') as stream:\n    stream.truncate(20_000_001)\n"
        ),
    }
    expected = {"missing": "BLOCKED", "malformed": "FAIL", "oversized": "BLOCKED"}
    for name, body in cases.items():
        interpreter = fake_python(tmp_path, f"fake-{name}", body)
        suite = fixture_suite(module, tmp_path, "def test_ok():\n    assert True\n")
        suite = replace(suite, python=str(interpreter))
        report = module.run_suite(tmp_path, suite, tmp_path / f"evidence-{name}", timeout=20)
        assert report["status"] == expected[name], (name, report)
        if name == "malformed":
            assert report["reason"] == "Malformed child report"
        else:
            assert report["reason"] == "No valid fresh pytest report; inspect dependency/collection logs"


def test_legacy_collection_dependency_and_collection_failure_are_distinct(tmp_path):
    module = runner()
    absent = "import deliberately_absent_shared_diagnostics\ndef test_unused():\n    assert True\n"
    report, _ = run_fixture(module, tmp_path, absent)
    assert report["status"] == "BLOCKED"
    assert report["collection_errors"][0]["kind"] == "missing-dependency"

    syntax = "def test_broken(:\n    pass\n"
    report, _ = run_fixture(module, tmp_path, syntax, output="syntax-evidence")
    assert report["status"] == "FAIL"
    assert report["collection_errors"][0]["kind"] == "collection-failure"


def test_legacy_pending_live_and_inventory_only_modes_are_unchanged(tmp_path):
    module = runner()
    sentinel = tmp_path / "live-body-ran"
    live = textwrap.dedent(
        f"""
        import pytest
        from pathlib import Path

        @pytest.mark.live_api
        def test_live_must_not_run():
            Path({str(sentinel)!r}).write_text("executed")

        @pytest.mark.offline
        def test_offline_ok():
            assert True
        """
    )
    report, _ = run_fixture(module, tmp_path, live)
    assert report["status"] == "BLOCKED"
    assert report["pending_live"] == ["test/test_sample.py::test_live_must_not_run"]
    assert report["outcomes"]["passed"] == 1
    assert not sentinel.exists()

    report, _ = run_fixture(
        module, tmp_path, "def test_ok():\n    assert True\n",
        collect_only=True, output="inventory-evidence",
    )
    assert report["status"] == "PASS"
    assert report["mode"] == "inventory-only"
    assert report["outcomes"]["passed"] == 0


def test_legacy_full_runner_can_still_pass_a_complete_prior_suite(tmp_path):
    module = runner()
    base = commit_fixture(
        module, tmp_path,
        {"test/test_first.py": "def test_first():\n    assert True\n",
         "test/test_second.py": "def test_second():\n    assert True\n"},
    )
    suites = (module.Suite("fixture", ("test",), sys.executable, "pytest.ini", ("pytest_socket",)),)
    report = module.run_full(tmp_path, base, tmp_path / "evidence", suites=suites, timeout=20)
    for item in report["suites"]:
        assert item["status"] != "BLOCKED", (
            item["suite"], item.get("reason"), item.get("collection_errors"), item.get("outcomes")
        )
    for item in report["prior_inventories"]:
        assert item["status"] != "BLOCKED", (
            item["suite"], item.get("reason"), item.get("collection_errors"), item.get("collected")
        )
    assert report["suites"][0]["status"] == "PASS", report["suites"][0]
    assert report["suites"][0]["collected"], report["suites"][0]
    assert report["status"] == "PASS", report["status"]
    assert report["total_collected"] == 2
    assert report["total_passed"] == 2
    assert report["missing_prior"] == []


# ---------------------------------------------------------------------------
# Diagnostics: availability RED until the runner marker exists; then behaviour.
# ---------------------------------------------------------------------------


def test_diagnostics_success_bundle_schema_identity_and_terminal(tmp_path):
    module = runner()
    source = textwrap.dedent(
        """
        import pytest

        @pytest.fixture
        def resource():
            yield "ready"

        def test_ok(resource):
            assert resource == "ready"
        """
    )
    report, output = run_fixture(module, tmp_path, source)
    assert report["status"] == "PASS"
    require_runner_diagnostics(module)
    manifest = require_manifest(output)
    assert_manifest_schema(manifest, suite="fixture", mode="execution")
    assert manifest["status"] == "complete"
    assert manifest["legacy"]["status"] == "PASS"
    assert manifest["legacy"]["report"] == "present"
    assert manifest["identity"]["target_sha"] is None
    assert manifest["identity"]["control_sha"] is None
    assert manifest["identity"]["base_sha"] is None
    assert_explicit_identity(manifest["identity"])
    events = read_events(output)
    assert manifest["events"]["bytes"] == (output / "diagnostics/events.jsonl").stat().st_size
    assert manifest["events"]["terminal_present"] is True
    assert manifest["counts"]["unique_nodes_retained"] == 1
    assert manifest["counts"]["unique_nodes_exact"] is True
    assert events[-1]["event"] == "terminal"
    report_events = [event for event in events if event["event"] == "report"]
    assert {event["when"] for event in report_events} == {"setup", "call", "teardown"}
    assert all(event["suite"] == "fixture" for event in events)
    for event in report_events:
        assert_report_event(event)
    serialized = (output / "diagnostics/manifest.json").read_text(encoding="utf-8")
    assert str(tmp_path) not in serialized
    assert "longrepr" not in serialized.lower()


def test_diagnostics_record_setup_call_and_teardown_failures(tmp_path):
    module = runner()
    source = textwrap.dedent(
        """
        import pytest

        @pytest.fixture
        def broken_setup():
            raise RuntimeError("setup boom")

        @pytest.fixture
        def broken_teardown():
            yield
            raise RuntimeError("teardown boom")

        def test_setup_failure(broken_setup):
            assert True

        def test_call_failure():
            assert 0 == 1, "call boom"

        def test_teardown_failure(broken_teardown):
            assert True
        """
    )
    report, output = run_fixture(module, tmp_path, source)
    assert report["status"] == "FAIL"
    assert report["outcomes"]["failed"] == 3
    require_runner_diagnostics(module)
    manifest = require_manifest(output)
    assert manifest["status"] in {"complete", "partial"}
    assert manifest["legacy"]["status"] == "FAIL"
    events = read_events(output)
    observed = {
        (event["nodeid"], event["when"]): event
        for event in events
        if event["event"] == "report" and event["outcome"] == "failed"
    }
    assert ("test/test_sample.py::test_setup_failure", "setup") in observed
    assert ("test/test_sample.py::test_call_failure", "call") in observed
    assert ("test/test_sample.py::test_teardown_failure", "teardown") in observed
    for event in observed.values():
        assert_report_event(event)
        error = event["error"]
        assert error["detail_state"] in {"available", "truncated", "unavailable"}
        if error["detail_state"] != "unavailable":
            assert "boom" in error["detail"]


def test_diagnostics_collection_dependency_and_collection_failure_are_explicit(tmp_path):
    module = runner()
    absent = "import deliberately_absent_shared_diagnostics\ndef test_unused():\n    assert True\n"
    report, output = run_fixture(module, tmp_path, absent)
    assert report["status"] == "BLOCKED"
    require_runner_diagnostics(module)
    manifest = require_manifest(output)
    assert manifest["legacy"]["status"] == "BLOCKED"
    assert manifest["counts"]["collection_errors"] >= 1
    events = read_events(output)
    missing = [event for event in events if event["event"] == "collection_error"]
    assert missing and missing[0]["kind"] == "missing-dependency"
    assert missing[0]["suite"] == "fixture"
    assert_no_raw_report_material(missing[0])

    syntax = "def test_broken(:\n    pass\n"
    report, output = run_fixture(module, tmp_path, syntax, output="syntax-evidence")
    assert report["status"] == "FAIL"
    manifest = require_manifest(output)
    assert manifest["legacy"]["status"] == "FAIL"
    events = read_events(output)
    broken = [event for event in events if event["event"] == "collection_error"]
    assert broken and broken[0]["kind"] == "collection-failure"


def test_diagnostics_pending_live_and_inventory_only_are_explicit(tmp_path):
    module = runner()
    sentinel = tmp_path / "live-body-ran"
    live = textwrap.dedent(
        f"""
        import pytest
        from pathlib import Path

        @pytest.mark.live_api
        def test_live_must_not_run():
            Path({str(sentinel)!r}).write_text("executed")

        @pytest.mark.offline
        def test_offline_ok():
            assert True
        """
    )
    report, output = run_fixture(module, tmp_path, live)
    assert report["status"] == "BLOCKED"
    assert not sentinel.exists()
    require_runner_diagnostics(module)
    manifest = require_manifest(output)
    assert manifest["legacy"]["status"] == "BLOCKED"
    assert manifest["counts"]["pending_live"] == 1
    events = read_events(output)
    live_nodes = {
        event["nodeid"] for event in events
        if event["event"] == "report" and event["nodeid"].endswith("test_live_must_not_run")
    }
    assert live_nodes == set(), "a pending-live body must not produce execution events"

    report, output = run_fixture(
        module, tmp_path, "def test_ok():\n    assert True\n",
        collect_only=True, output="inventory-evidence",
    )
    assert report["status"] == "PASS"
    manifest = require_manifest(output)
    assert_manifest_schema(manifest, suite="fixture", mode="inventory-only")
    events = read_events(output)
    assert not [event for event in events if event["event"] == "report"]


def test_diagnostics_timeout_keeps_completed_events_and_incomplete_status(tmp_path):
    module = runner()
    source = "import time\ndef test_first_pass():\n    assert True\ndef test_later_hang():\n    time.sleep(30)\n"
    report, output = run_fixture(module, tmp_path, source, timeout=1.5)
    assert report["status"] == "BLOCKED"
    assert report["outcomes"]["passed"] == 1
    require_runner_diagnostics(module)
    manifest = require_manifest(output)
    assert manifest["status"] in {"partial", "unavailable"}
    assert manifest["legacy"]["status"] == "BLOCKED"
    assert manifest["events"]["terminal_present"] is False
    assert manifest["counts"]["unique_nodes_exact"] is False
    events = read_events_tolerating_torn(output, manifest)
    completed = [
        event for event in events
        if event["event"] == "report"
        and event["nodeid"].endswith("test_first_pass")
        and event["outcome"] == "passed"
    ]
    assert completed, "a completed pass before timeout is legitimate and must remain"


def test_diagnostics_spawn_failure_is_packaged_as_advisory_unavailable(tmp_path):
    module = runner()
    suite = fixture_suite(module, tmp_path, "def test_ok():\n    assert True\n")
    missing = replace(suite, python=str(tmp_path / "missing-interpreter"))
    report = module.run_suite(tmp_path, missing, tmp_path / "evidence", timeout=20)
    assert report["status"] == "BLOCKED"
    require_runner_diagnostics(module)
    manifest = require_manifest(tmp_path / "evidence")
    assert_manifest_schema(manifest, suite="fixture")
    assert manifest["status"] == "unavailable"
    assert manifest["legacy"]["report"] == "not_started"
    assert manifest["legacy"]["status"] == "BLOCKED"
    assert manifest["events"]["terminal_present"] is False
    assert manifest["events"]["bytes"] == 0
    assert manifest["error"]


def test_diagnostics_missing_malformed_and_oversized_legacy_reports_are_classified(tmp_path):
    module = runner()
    cases = {
        "missing": ("raise SystemExit(0)", "BLOCKED", "missing"),
        "malformed": (
            "import os\nfrom pathlib import Path\n"
            "Path(os.environ['PAPERTRACE_SUITE_REPORT']).write_text("
            "'{\"collected\": [', encoding='utf-8')\n",
            "FAIL", "malformed",
        ),
        "oversized": (
            "import os\nfrom pathlib import Path\n"
            "path = Path(os.environ['PAPERTRACE_SUITE_REPORT'])\n"
            "with path.open('wb') as stream:\n    stream.truncate(20_000_001)\n",
            "BLOCKED", "oversized",
        ),
    }
    for name, (body, verdict, classification) in cases.items():
        interpreter = fake_python(tmp_path, f"fake-{name}", body)
        suite = fixture_suite(module, tmp_path, "def test_ok():\n    assert True\n")
        suite = replace(suite, python=str(interpreter))
        output = tmp_path / f"evidence-{name}"
        tracemalloc.start()
        try:
            tracemalloc.reset_peak()
            report = module.run_suite(tmp_path, suite, output, timeout=20)
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        assert report["status"] == verdict
        assert peak < 80_000_000, "an oversized legacy file must not be loaded wholesale"
        require_runner_diagnostics(module)
        manifest = require_manifest(output)
        assert manifest["legacy"]["status"] == verdict
        assert manifest["legacy"]["report"] == classification
        assert manifest["status"] in {"partial", "unavailable"}
        assert manifest["error"] is not None
        assert len((output / "diagnostics/manifest.json").read_bytes()) <= MANIFEST_LIMIT


def test_diagnostics_oversized_stale_event_file_is_not_loaded_wholesale(tmp_path):
    module = runner()
    output = tmp_path / "evidence"
    diagnostics = output / "diagnostics"
    diagnostics.mkdir(parents=True)
    with (diagnostics / "events.jsonl").open("wb") as stream:
        stream.truncate(200_000_000)
    (diagnostics / "manifest.json").write_text(
        '{"status": "complete", "stale": true}', encoding="utf-8"
    )
    tracemalloc.start()
    try:
        tracemalloc.reset_peak()
        report, output = run_fixture(module, tmp_path, "def test_ok():\n    assert True\n")
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert report["status"] == "PASS"
    assert peak < 80_000_000, "a stale oversized events file must be rejected before loading"
    require_runner_diagnostics(module)
    manifest = require_manifest(output)
    assert manifest["status"] == "complete"
    assert manifest["events"]["bytes"] <= EVENTS_LIMIT
    assert (output / "diagnostics/events.jsonl").stat().st_size <= EVENTS_LIMIT
    assert manifest.get("stale") is not True


def test_diagnostics_stale_and_repeated_runs_are_fresh_not_appended(tmp_path):
    module = runner()
    source = "def test_ok():\n    assert True\n"
    report, output = run_fixture(module, tmp_path, source)
    assert report["status"] == "PASS"
    require_runner_diagnostics(module)
    first = read_manifest(output)
    assert first["status"] == "complete"
    first_size = (output / "diagnostics/events.jsonl").stat().st_size

    (output / "diagnostics/events.jsonl").write_text(
        '{"schema_version": 1, "suite": "fixture", "stale": "PREVIOUS-RUN"}\n',
        encoding="utf-8",
    )
    (output / "diagnostics/manifest.json").write_text(
        '{"status": "complete", "stale": true}', encoding="utf-8"
    )
    report, output = run_fixture(module, tmp_path, source)
    assert report["status"] == "PASS"
    manifest = require_manifest(output)
    assert_manifest_schema(manifest, suite="fixture", mode="execution")
    assert manifest.get("stale") is not True
    events = event_data(output)
    assert b"PREVIOUS-RUN" not in events
    parsed = read_events(output)
    assert sum(event["event"] == "terminal" for event in parsed) == 1
    assert (output / "diagnostics/events.jsonl").stat().st_size < first_size * 2 + 4096

    report, _ = run_fixture(module, tmp_path, source)
    assert report["status"] == "PASS"
    manifest = require_manifest(output)
    assert manifest["status"] == "complete"
    assert b"PREVIOUS-RUN" not in event_data(output)


def test_diagnostics_symlink_paths_are_not_followed(tmp_path):
    module = runner()
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel"
    sentinel.write_text("outside", encoding="utf-8")

    output = tmp_path / "evidence-link"
    output.mkdir()
    diagnostics = output / "diagnostics"
    diagnostics.symlink_to(outside, target_is_directory=True)
    suite = fixture_suite(module, tmp_path, "def test_ok():\n    assert True\n")
    report = module.run_suite(tmp_path, suite, output, timeout=20)
    assert report["status"] == "PASS"
    require_runner_diagnostics(module)
    manifest = require_manifest(output)
    assert manifest["status"] == "complete"
    assert not diagnostics.is_symlink()
    assert (diagnostics / "events.jsonl").is_file()
    assert not (diagnostics / "events.jsonl").is_symlink()
    assert not (diagnostics / "manifest.json").is_symlink()
    assert sorted(path.name for path in outside.iterdir()) == ["sentinel"]
    assert sentinel.read_text(encoding="utf-8") == "outside"

    output = tmp_path / "evidence-files"
    diagnostics = output / "diagnostics"
    diagnostics.mkdir(parents=True)
    outside_events = outside / "outside-events.jsonl"
    outside_events.write_text("OUTSIDE", encoding="utf-8")
    (diagnostics / "events.jsonl").symlink_to(outside_events)
    (diagnostics / "manifest.json").symlink_to(outside / "outside-manifest.json")
    suite = fixture_suite(module, tmp_path, "def test_ok():\n    assert True\n")
    report = module.run_suite(tmp_path, suite, output, timeout=20)
    assert report["status"] == "PASS"
    manifest = require_manifest(output)
    assert manifest["status"] == "complete"
    assert outside_events.read_text(encoding="utf-8") == "OUTSIDE"
    assert not (outside / "outside-manifest.json").exists()
    assert (diagnostics / "events.jsonl").is_file()
    assert not (diagnostics / "events.jsonl").is_symlink()
    assert (diagnostics / "manifest.json").is_file()
    assert not (diagnostics / "manifest.json").is_symlink()


def test_diagnostics_directory_at_event_path_is_advisory_and_not_deleted(tmp_path):
    module = runner()
    output = tmp_path / "evidence"
    diagnostics = output / "diagnostics"
    diagnostics.mkdir(parents=True)
    trap = diagnostics / "events.jsonl"
    trap.mkdir()
    (trap / "keep").write_text("keep", encoding="utf-8")
    suite = fixture_suite(module, tmp_path, "def test_ok():\n    assert True\n")
    report = module.run_suite(tmp_path, suite, output, timeout=20)
    assert report["status"] == "PASS"
    require_runner_diagnostics(module)
    manifest = require_manifest(output)
    assert manifest["status"] in {"partial", "unavailable"}
    assert manifest["legacy"]["status"] == "PASS"
    assert manifest["events"]["terminal_present"] is False
    assert manifest["error"] is not None
    assert (trap / "keep").read_text(encoding="utf-8") == "keep"
    assert not trap.is_file()


def test_diagnostics_manifest_packaging_failure_is_advisory_and_preserves_verdict(tmp_path):
    module = runner()
    failing = "def test_fail():\n    assert False\n"
    sentinel = tmp_path / "live-body-ran"
    blocked = textwrap.dedent(
        f"""
        import pytest
        from pathlib import Path

        @pytest.mark.live_api
        def test_live_must_not_run():
            Path({str(sentinel)!r}).write_text("executed")
        """
    )
    for name, source, verdict in (
        ("fail", failing, "FAIL"),
        ("blocked", blocked, "BLOCKED"),
    ):
        output = tmp_path / f"evidence-{name}"
        diagnostics = output / "diagnostics"
        diagnostics.mkdir(parents=True)
        trap = diagnostics / "manifest.json"
        trap.mkdir()
        (trap / "keep").write_text("keep", encoding="utf-8")
        suite = fixture_suite(module, tmp_path, source)
        report = module.run_suite(tmp_path, suite, output, timeout=20)
        assert report["status"] == verdict
        assert not sentinel.exists()
        require_runner_diagnostics(module)
        advisory = report.get("diagnostics")
        assert isinstance(advisory, dict)
        assert advisory["status"] == "unavailable"
        assert advisory["trusted"] is False
        assert isinstance(advisory.get("reason"), str)
        assert len(advisory["reason"].encode("utf-8")) <= 200
        assert (trap / "keep").read_text(encoding="utf-8") == "keep"
        assert not trap.is_file()


def test_diagnostics_tamper_fault_is_bound_to_exact_current_run_paths(tmp_path):
    module = runner()
    require_runner_diagnostics(module)
    output = tmp_path / "evidence"
    expected_dir = output / "diagnostics"
    expected_events = expected_dir / "events.jsonl"
    expected_manifest = expected_dir / "manifest.json"
    proof_path = tmp_path / "tamper-proof.json"
    torn_sentinel = "TAMPER-SENTINEL-CURRENT-RUN"
    torn = f'{{"schema_version":1,"event":"report","tamper":"{torn_sentinel}"'.encode()
    source = textwrap.dedent(
        f"""
        import json
        import os
        from pathlib import Path

        def test_tamper():
            expected_dir = Path({str(expected_dir)!r}).resolve()
            expected_events = Path({str(expected_events)!r}).resolve()
            expected_manifest = Path({str(expected_manifest)!r}).resolve()
            candidates = {{
                key: value for key, value in os.environ.items()
                if "DIAGNOSTIC" in key.upper()
            }}
            assert len(candidates) == 1, candidates
            key, value = next(iter(candidates.items()))
            actual = Path(value)
            assert actual.is_absolute(), value
            actual = actual.resolve()
            assert actual in {{expected_dir, expected_events}}, (key, value)
            assert expected_dir.is_dir(), "the parent did not create the intended directory"
            with expected_events.open("ab") as stream:
                stream.write({torn!r})
            expected_manifest.write_text(
                '{{"schema_version":1,"status":"complete","trusted":true,'
                '"legacy":{{"status":"PASS"}}}}',
                encoding="utf-8",
            )
            proof = {{
                "env_key": key,
                "env_value": value,
                "expected_dir": str(expected_dir),
                "expected_events": str(expected_events),
                "expected_manifest": str(expected_manifest),
                "events_written": expected_events.is_file(),
                "manifest_written": expected_manifest.is_file(),
            }}
            Path({str(proof_path)!r}).write_text(
                json.dumps(proof, sort_keys=True), encoding="utf-8"
            )
            os._exit(0)
        """
    )
    suite = fixture_suite(module, tmp_path, source)
    report = module.run_suite(tmp_path, suite, output, timeout=20)
    assert proof_path.is_file(), "the tamper child did not reach the exact intended paths"
    proof = json.loads(proof_path.read_text(encoding="utf-8"))
    assert proof["env_key"]
    assert Path(proof["env_value"]).is_absolute()
    assert Path(proof["env_value"]).resolve() in {
        Path(proof["expected_dir"]), Path(proof["expected_events"]),
    }
    assert proof["events_written"] is True
    assert proof["manifest_written"] is True
    assert Path(proof["expected_events"]) == expected_events
    assert Path(proof["expected_manifest"]) == expected_manifest
    assert report["status"] == "FAIL", "candidate diagnostics cannot certify a PASS"
    assert report["outcomes"]["passed"] == 0
    assert torn_sentinel.encode() in expected_events.read_bytes()
    manifest = require_manifest(output)
    assert manifest["trusted"] is False
    assert manifest["legacy"]["status"] == "FAIL"
    assert manifest["status"] in {"partial", "unavailable"}
    assert manifest["events"]["terminal_present"] is False
    assert manifest["events"]["torn_tail_ignored"] or manifest["events"]["sampled"]
    assert '"trusted": true' not in expected_manifest.read_text(encoding="utf-8")
    lines = [line for line in expected_events.read_bytes().splitlines() if line]
    for index, line in enumerate(lines):
        try:
            json.loads(line.decode("utf-8"))
        except json.JSONDecodeError:
            assert manifest["events"]["torn_tail_ignored"] is True
            assert index == len(lines) - 1


def test_diagnostics_event_and_manifest_budgets_hold_for_large_inventory(tmp_path):
    module = runner()
    source = textwrap.dedent(
        """
        import pytest

        @pytest.mark.parametrize("i", range(6000), ids=lambda i: "x" * 180 + str(i))
        def test_many(i):
            assert True
        """
    )
    report, output = run_fixture(module, tmp_path, source, collect_only=True)
    assert report["status"] == "PASS"
    assert len(report["collected"]) == 6000
    require_runner_diagnostics(module)
    manifest = require_manifest(output)
    assert_manifest_schema(manifest, suite="fixture", mode="inventory-only")
    assert manifest["status"] in {"complete", "partial"}
    events_path = output / "diagnostics/events.jsonl"
    manifest_path = output / "diagnostics/manifest.json"
    assert events_path.stat().st_size <= EVENTS_LIMIT
    assert manifest_path.stat().st_size <= MANIFEST_LIMIT
    assert manifest["counts"]["unique_nodes_retained"] <= 6000
    if manifest["events"]["truncated"] or manifest["events"]["sampled"]:
        assert manifest["counts"]["unique_nodes_exact"] is False
    else:
        assert manifest["counts"]["unique_nodes_retained"] == 6000
        assert manifest["counts"]["unique_nodes_exact"] is True
    data = events_path.read_bytes()
    assert data.decode("utf-8")
    assert data.endswith(b"\n") or manifest["events"]["torn_tail_ignored"]
    for line in data.splitlines():
        if line:
            assert isinstance(json.loads(line.decode("utf-8")), dict)
    assert manifest["events"]["terminal_present"] is True


def test_diagnostics_six_current_and_prior_directories_fit_the_bundle_budget(tmp_path):
    module = runner()
    assert BUNDLE_LIMIT == 6 * (EVENTS_LIMIT + MANIFEST_LIMIT)
    base = commit_fixture(
        module, tmp_path, {"test/test_sample.py": "def test_ok():\n    assert True\n"}
    )
    suites = tuple(
        module.Suite(name, ("test",), sys.executable, "pytest.ini", ("pytest_socket",))
        for name in SUITES
    )
    output = tmp_path / "evidence"
    rogue = output / "rogue/diagnostics"
    rogue.mkdir(parents=True)
    with (rogue / "events.jsonl").open("wb") as stream:
        stream.truncate(9_000_000)
    (rogue / "manifest.json").write_text('{"status": "complete"}', encoding="utf-8")
    report = module.run_full(tmp_path, base, output, suites=suites, timeout=20)
    assert report["status"] == "PASS"
    require_runner_diagnostics(module)
    six_bytes = 0
    for suite in SUITES:
        for suffix, mode in (("", "execution"), ("-prior", "inventory-only")):
            directory = output / f"{suite}{suffix}/diagnostics"
            manifest = require_manifest(directory.parent)
            assert_manifest_schema(manifest, suite=suite, mode=mode)
            assert {path.name for path in directory.iterdir()} <= {
                "events.jsonl", "manifest.json",
            }
            six_bytes += sum(path.stat().st_size for path in directory.iterdir())
    assert six_bytes <= BUNDLE_LIMIT
    assert report["diagnostics"]["bundle_bytes"] == six_bytes
    assert report["diagnostics"]["bundle_bytes"] <= BUNDLE_LIMIT
    assert set(report["diagnostics"]["suites"]) == {
        f"{suite}{suffix}" for suite in SUITES for suffix in ("", "-prior")
    }
    assert (rogue / "events.jsonl").stat().st_size == 9_000_000
    assert "rogue" not in json.dumps(report["diagnostics"])
    summary = json.loads((output / "full-regression.json").read_text(encoding="utf-8"))
    assert summary["diagnostics"]["bundle_bytes"] == six_bytes


def transport_fixture(module, tmp_path, *, source="def test_ok():\n    assert True\n",
                      name="team-offline", verdict="PASS"):
    base = commit_fixture(
        module, tmp_path, {"test/test_sample.py": source}
    )
    suite = module.Suite(name, ("test",), sys.executable, "pytest.ini", ("pytest_socket",))
    output = tmp_path / "evidence"
    report = module.run_full(tmp_path, base, output, suites=(suite,), timeout=20)
    assert report["status"] == verdict
    expected = {
        "target_sha": git(tmp_path, "rev-parse", "HEAD"),
        "control_sha": None,
        "base_sha": base,
        "source_tree_sha256": report["source_tree_sha256"],
    }
    return report, output, expected


def test_transport_qualification_accepts_current_bounded_six_file_bundle(tmp_path):
    module = runner()
    require_transport_qualification(module)
    require_runner_diagnostics(module)
    base = commit_fixture(
        module, tmp_path, {"test/test_sample.py": "def test_ok():\n    assert True\n"}
    )
    suites = tuple(
        module.Suite(name, ("test",), sys.executable, "pytest.ini", ("pytest_socket",))
        for name in SUITES
    )
    output = tmp_path / "evidence"
    report = module.run_full(tmp_path, base, output, suites=suites, timeout=20)
    assert report["status"] == "PASS"
    expected = {
        "target_sha": git(tmp_path, "rev-parse", "HEAD"),
        "control_sha": None,
        "base_sha": base,
        "source_tree_sha256": report["source_tree_sha256"],
    }
    plan = module.qualify_diagnostics_artifacts(
        tmp_path, output, expected_identity=expected, suites=SUITES,
    )
    wanted = {
        f"{suite}/diagnostics/{name}" for suite in SUITES
        for name in ("events.jsonl", "manifest.json")
    }
    assert plan["status"] == "qualified"
    assert set(plan["files"]) == wanted
    for relative in plan["files"]:
        path = output / relative
        assert path.is_file()
        assert not path.is_symlink()
    assert not any("-prior" in item or "rogue" in item for item in plan["files"])
    assert (output / "team-offline/stdout.txt").is_file()
    assert not any("stdout.txt" in item for item in plan["files"])


@pytest.mark.parametrize("mutation", ["stale-base", "unknown-target"])
def test_transport_qualification_withholds_stale_or_unknown_provenance(tmp_path, mutation):
    module = runner()
    require_transport_qualification(module)
    require_runner_diagnostics(module)
    report, output, expected = transport_fixture(module, tmp_path)
    manifest_path = output / "team-offline/diagnostics/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if mutation == "stale-base":
        manifest["identity"]["base_sha"] = "0" * 40
    else:
        manifest["identity"]["target_sha"] = None
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    plan = module.qualify_diagnostics_artifacts(
        tmp_path, output, expected_identity=expected, suites=("team-offline",),
    )
    assert plan["status"] == "withheld"
    assert plan["files"] == []
    assert any("provenance" in reason.lower() for reason in plan["reasons"])
    assert report["status"] == "PASS"


def test_transport_qualification_withholds_symlink_or_escaping_material(tmp_path):
    module = runner()
    require_transport_qualification(module)
    require_runner_diagnostics(module)
    report, output, expected = transport_fixture(module, tmp_path)
    events = output / "team-offline/diagnostics/events.jsonl"
    outside = tmp_path / "outside-events.jsonl"
    outside.write_text("OUTSIDE", encoding="utf-8")
    events.unlink()
    events.symlink_to(outside)
    plan = module.qualify_diagnostics_artifacts(
        tmp_path, output, expected_identity=expected, suites=("team-offline",),
    )
    assert plan["status"] == "withheld"
    assert plan["files"] == []
    assert outside.read_text(encoding="utf-8") == "OUTSIDE"
    assert report["status"] == "PASS"


def test_transport_qualification_withholds_oversized_material(tmp_path):
    module = runner()
    require_transport_qualification(module)
    require_runner_diagnostics(module)
    report, output, expected = transport_fixture(module, tmp_path)
    events = output / "team-offline/diagnostics/events.jsonl"
    with events.open("wb") as stream:
        stream.truncate(200_000_000)
    tracemalloc.start()
    try:
        tracemalloc.reset_peak()
        plan = module.qualify_diagnostics_artifacts(
            tmp_path, output, expected_identity=expected, suites=("team-offline",),
        )
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert plan["status"] == "withheld"
    assert plan["files"] == []
    assert peak < 80_000_000
    assert report["status"] == "PASS"


def test_transport_qualification_allows_explicit_partial_bundle(tmp_path):
    module = runner()
    require_transport_qualification(module)
    require_runner_diagnostics(module)
    report, output, expected = transport_fixture(
        module, tmp_path, source="def test_fail():\n    assert False\n", verdict="FAIL",
    )
    manifest_path = output / "team-offline/diagnostics/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["status"] = "partial"
    manifest["events"]["terminal_present"] = False
    manifest["events"]["truncated"] = True
    manifest["counts"]["unique_nodes_exact"] = False
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    plan = module.qualify_diagnostics_artifacts(
        tmp_path, output, expected_identity=expected, suites=("team-offline",),
    )
    assert plan["status"] == "qualified"
    assert set(plan["files"]) == {
        "team-offline/diagnostics/events.jsonl",
        "team-offline/diagnostics/manifest.json",
    }
    assert report["status"] == "FAIL"


def write_six_diagnostic_files(output):
    for suite in SUITES:
        directory = Path(output) / suite / "diagnostics"
        directory.mkdir(parents=True, exist_ok=True)
        for name in ("events.jsonl", "manifest.json"):
            (directory / name).write_text("{}\n", encoding="utf-8")


def qualify_cli_args(root, output, *, include_control=True):
    args = [
        "--qualify-diagnostics",
        "--root", str(root),
        "--output", str(output),
        "--expected-target-sha", "a" * 40,
        "--expected-base-sha", "c" * 40,
    ]
    if include_control:
        args.extend(["--expected-control-sha", "b" * 40])
    return args


def test_transport_cli_qualified_exits_zero_and_forwards_trusted_identity(
    tmp_path, monkeypatch, capsys,
):
    module = runner()
    require_transport_qualification(module)
    require_runner_diagnostics(module)
    root = tmp_path / "target"
    output = root / ".local/full-regression"
    root.mkdir(parents=True)
    write_six_diagnostic_files(output)
    calls = []

    def stub(root_arg, output_arg, *, expected_identity, suites):
        calls.append((
            Path(root_arg).resolve(),
            Path(output_arg).resolve(),
            expected_identity,
            tuple(suites),
        ))
        return {
            "status": "qualified",
            "files": [
                f"{suite}/diagnostics/{name}"
                for suite in SUITES for name in ("events.jsonl", "manifest.json")
            ],
            "reasons": [],
        }

    monkeypatch.setattr(module, TRANSPORT_QUALIFICATION_ATTRIBUTE, stub)
    code = module.main(qualify_cli_args(root, output))
    capsys.readouterr()
    assert code == 0
    assert calls == [(
        root.resolve(),
        output.resolve(),
        {"target_sha": "a" * 40, "control_sha": "b" * 40, "base_sha": "c" * 40},
        SUITES,
    )]


def test_transport_cli_withheld_exits_one_and_keeps_six_physical_files(
    tmp_path, monkeypatch, capsys,
):
    module = runner()
    require_transport_qualification(module)
    require_runner_diagnostics(module)
    root = tmp_path / "target"
    output = root / ".local/full-regression"
    root.mkdir(parents=True)
    write_six_diagnostic_files(output)

    def stub(root_arg, output_arg, *, expected_identity, suites):
        assert Path(root_arg).resolve() == root.resolve()
        assert Path(output_arg).resolve() == output.resolve()
        return {
            "status": "withheld",
            "files": [],
            "reasons": ["provenance mismatch"],
        }

    monkeypatch.setattr(module, TRANSPORT_QUALIFICATION_ATTRIBUTE, stub)
    code = module.main(qualify_cli_args(root, output))
    capsys.readouterr()
    assert code == 1
    for suite in SUITES:
        for name in ("events.jsonl", "manifest.json"):
            assert (output / suite / "diagnostics" / name).is_file()


def test_transport_cli_validation_error_exits_two(tmp_path, monkeypatch, capsys):
    module = runner()
    require_transport_qualification(module)
    require_runner_diagnostics(module)
    root = tmp_path / "target"
    output = root / ".local/full-regression"
    root.mkdir(parents=True)

    def stub(root_arg, output_arg, *, expected_identity, suites):
        raise ValueError("synthetic qualification failure")

    monkeypatch.setattr(module, TRANSPORT_QUALIFICATION_ATTRIBUTE, stub)
    code = module.main(qualify_cli_args(root, output))
    capsys.readouterr()
    assert code == 2

    def unknown_status(root_arg, output_arg, *, expected_identity, suites):
        return {"status": "other", "files": [], "reasons": []}

    monkeypatch.setattr(module, TRANSPORT_QUALIFICATION_ATTRIBUTE, unknown_status)
    code = module.main(qualify_cli_args(root, output))
    capsys.readouterr()
    assert code == 2


def test_transport_cli_requires_independent_metadata_before_qualifying(
    tmp_path, monkeypatch, capsys,
):
    module = runner()
    require_transport_qualification(module)
    require_runner_diagnostics(module)
    root = tmp_path / "target"
    output = root / ".local/full-regression"
    root.mkdir(parents=True)
    calls = []

    def stub(root_arg, output_arg, *, expected_identity, suites):
        calls.append((root_arg, output_arg, expected_identity, suites))
        return {"status": "qualified", "files": [], "reasons": []}

    monkeypatch.setattr(module, TRANSPORT_QUALIFICATION_ATTRIBUTE, stub)
    try:
        code = module.main(qualify_cli_args(root, output, include_control=False))
    except SystemExit as error:
        code = error.code
    capsys.readouterr()
    assert code != 0
    assert calls == []


def test_transport_cli_does_not_hide_unexpected_exception(tmp_path, monkeypatch):
    module = runner()
    require_transport_qualification(module)
    require_runner_diagnostics(module)
    root = tmp_path / "target"
    output = root / ".local/full-regression"
    root.mkdir(parents=True)

    def stub(root_arg, output_arg, *, expected_identity, suites):
        raise RuntimeError("synthetic unexpected failure")

    monkeypatch.setattr(module, TRANSPORT_QUALIFICATION_ATTRIBUTE, stub)
    with pytest.raises(RuntimeError):
        module.main(qualify_cli_args(root, output))


def test_diagnostics_missing_provenance_is_null_and_identities_are_distinct(tmp_path):
    module = runner()
    report, output = run_fixture(module, tmp_path, "def test_ok():\n    assert True\n")
    assert report["status"] == "PASS"
    require_runner_diagnostics(module)
    manifest = require_manifest(output)
    identity = manifest["identity"]
    assert identity["target_sha"] is None
    assert identity["control_sha"] is None
    assert identity["base_sha"] is None
    assert identity["source_tree_sha256"] is None or re.fullmatch(
        r"[0-9a-f]{64}", identity["source_tree_sha256"]
    )
    assert_explicit_identity(identity)

    repo = tmp_path / "repo"
    repo.mkdir()
    base = commit_fixture(
        module, repo, {"test/test_sample.py": "def test_ok():\n    assert True\n"}
    )
    suites = (module.Suite("fixture", ("test",), sys.executable, "pytest.ini", ("pytest_socket",)),)
    full = module.run_full(repo, base, repo / "full-evidence", suites=suites, timeout=20)
    assert full["status"] == "PASS"
    current = require_manifest(repo / "full-evidence/fixture")
    prior = require_manifest(repo / "full-evidence/fixture-prior")
    for manifest in (current, prior):
        identity = manifest["identity"]
        assert identity["base_sha"] == base
        assert identity["control_sha"] is None
        assert_explicit_identity(identity)
        assert identity["source_tree_sha256"] == full["source_tree_sha256"] or re.fullmatch(
            r"[0-9a-f]{64}", identity["source_tree_sha256"]
        )
    assert current["identity"]["target_sha"] in {None, git(repo, "rev-parse", "HEAD")}
    assert current["identity"]["target_sha"] != current["identity"]["source_tree_sha256"]


def test_diagnostics_child_environment_adds_only_the_diagnostic_path(tmp_path, monkeypatch):
    module = runner()
    dump = tmp_path / "child-env.json"
    monkeypatch.setenv("PAPERTRACE_UNFORWARDED_SENTINEL", "must-not-reach-child")
    monkeypatch.setenv("PAPERTRACE_TARGET_SHA", "a" * 40)
    monkeypatch.setenv("GITHUB_TOKEN", "synthetic-not-a-credential")
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-not-a-credential")
    source = textwrap.dedent(
        f"""
        import json
        import os
        from pathlib import Path

        Path({str(dump)!r}).write_text(
            json.dumps(dict(os.environ), sort_keys=True), encoding="utf-8"
        )

        def test_env_dump():
            assert True
        """
    )
    report, output = run_fixture(module, tmp_path, source)
    assert report["status"] == "PASS"
    require_runner_diagnostics(module)
    environment = json.loads(dump.read_text(encoding="utf-8"))
    assert "PAPERTRACE_UNFORWARDED_SENTINEL" not in environment
    assert "PAPERTRACE_TARGET_SHA" not in environment
    assert "GITHUB_TOKEN" not in environment
    assert "OPENAI_API_KEY" not in environment
    candidates = {
        key: value for key, value in environment.items()
        if "DIAGNOSTIC" in key.upper() and "diagnostics" in value
    }
    assert len(candidates) == 1
    value = next(iter(candidates.values()))
    assert Path(value).is_absolute()
    assert Path(value).resolve().is_relative_to(output.resolve())


def test_diagnostics_untrusted_messages_are_bounded_and_not_evaluated(tmp_path):
    module = runner()
    sentinel = tmp_path / "eval-sentinel"
    payload = f"__import__('pathlib').Path({str(sentinel)!r}).write_text('evaluated')"
    source = (
        "def test_untrusted_message():\n"
        f"    payload = {payload!r} + '\\n\\x1b[31m' + 'A' * 8000 + '猫' * 4000\n"
        "    assert False, payload\n"
    )
    report, output = run_fixture(module, tmp_path, source)
    assert report["status"] == "FAIL"
    assert not sentinel.exists(), "diagnostic text must never be evaluated"
    require_runner_diagnostics(module)
    manifest = require_manifest(output)
    assert manifest["legacy"]["status"] == "FAIL"
    assert len((output / "diagnostics/manifest.json").read_bytes()) <= MANIFEST_LIMIT
    assert len((output / "diagnostics/events.jsonl").read_bytes()) <= EVENTS_LIMIT
    events = read_events(output)
    failed = [
        event for event in events
        if event["event"] == "report" and event["outcome"] == "failed"
    ]
    assert failed
    assert_error_record(failed[0]["error"])
    error = failed[0]["error"]
    if error["detail_state"] != "unavailable":
        assert "A" * 8000 not in error["detail"]
        assert "猫" * 4000 not in error["detail"]
    serialized = (output / "diagnostics/events.jsonl").read_text(encoding="utf-8")
    assert "longrepr" not in serialized.lower()
    assert "captured" not in serialized.lower()
    assert_no_raw_report_material(events)

    node_source = textwrap.dedent(
        f"""
        import pytest

        @pytest.mark.parametrize("value", [0], ids=[{payload!r}])
        def test_untrusted_nodeid(value):
            assert value == 0
        """
    )
    report, output = run_fixture(module, tmp_path, node_source, output="node-evidence")
    assert report["status"] == "PASS"
    assert not sentinel.exists(), "diagnostic node ids must never be evaluated"
    manifest = require_manifest(output)
    assert_manifest_schema(manifest, suite="fixture", mode="execution")
    events = read_events(output)
    collected = [event for event in events if event["event"] == "collection"]
    assert collected and isinstance(collected[0]["nodeid"], str)
    assert_no_raw_report_material(events)


def test_diagnostics_failure_does_not_stop_other_suites_and_summary_is_written(tmp_path):
    module = runner()
    base = commit_fixture(
        module, tmp_path,
        {
            "test/failing/test_failing.py": "def test_fail():\n    assert False\n",
            "test/passing/test_passing.py": "def test_pass():\n    assert True\n",
        },
    )
    failing = module.Suite("team-offline", ("test/failing",), sys.executable, "pytest.ini", ("pytest_socket",))
    passing = module.Suite("upstream", ("test/passing",), sys.executable, "pytest.ini", ("pytest_socket",))
    output = tmp_path / "evidence"
    trap = output / "team-offline/diagnostics/manifest.json"
    trap.mkdir(parents=True)
    (trap / "keep").write_text("keep", encoding="utf-8")
    report = module.run_full(tmp_path, base, output, suites=(failing, passing), timeout=20)
    assert report["status"] == "FAIL"
    assert len(report["suites"]) == 2
    by_suite = {item["suite"]: item for item in report["suites"]}
    assert by_suite["team-offline"]["outcomes"]["failed"] >= 1
    assert by_suite["upstream"]["outcomes"]["passed"] == 1
    require_runner_diagnostics(module)
    assert by_suite["team-offline"]["diagnostics"]["status"] == "unavailable"
    assert by_suite["upstream"]["diagnostics"]["status"] in {"complete", "partial"}
    assert report["missing_prior"] == []
    assert (trap / "keep").read_text(encoding="utf-8") == "keep"
    assert not trap.is_file()
    summary_path = output / "full-regression.json"
    assert summary_path.is_file()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["status"] == "FAIL"
    assert len(summary["suites"]) == 2
    assert summary["diagnostics"]["bundle_bytes"] <= BUNDLE_LIMIT


def test_legacy_builtin_subtests_fixture_runs_without_external_plugin(tmp_path):
    module = runner()
    marker = tmp_path / "subtest-body-ran"
    report, _ = run_fixture(module, tmp_path, builtin_subtest_source(marker))
    assert marker.is_file(), "the built-in subtests fixture did not execute the child"
    assert report["collection_errors"] == []
    assert report["outcomes"] == {
        "passed": 2, "failed": 2, "skipped": 0, "xfailed": 0, "xpassed": 0,
    }
    assert report["status"] == "FAIL"


def test_diagnostics_builtin_subtest_failure_is_visible_when_available(tmp_path):
    module = runner()
    marker = tmp_path / "subtest-body-ran"
    report, output = run_fixture(module, tmp_path, builtin_subtest_source(marker))
    assert marker.is_file(), "the built-in subtests fixture did not execute the child"
    assert report["collection_errors"] == []
    assert report["outcomes"] == {
        "passed": 2, "failed": 2, "skipped": 0, "xfailed": 0, "xpassed": 0,
    }
    assert report["status"] == "FAIL"
    require_runner_diagnostics(module)
    manifest = require_manifest(output)
    assert manifest["legacy"]["status"] == "FAIL"
    events = read_events(output)
    failures = [
        event for event in events
        if event["event"] == "report" and event["outcome"] == "failed"
    ]
    assert failures, "subtest failures must remain visible as reports"
    subtest_failures = [
        event for event in failures
        if event.get("subtest") and "case 1" in event["subtest"]
    ]
    assert subtest_failures, "the failed subcase must be visible as a subtest report"
    for event in subtest_failures:
        assert_report_event(event)
        assert event["error"] is not None


# ---------------------------------------------------------------------------
# Workflow contract: parsed YAML behaviour, never an actual Actions execution.
# ---------------------------------------------------------------------------


def test_regression_gate_step_keeps_its_original_failing_exit():
    workflow = yaml.safe_load(
        (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    )
    _job_name, _job, steps, gate_index = regression_gate_job(workflow)
    gate = steps[gate_index]
    assert gate.get("continue-on-error") is not True
    command = str(gate["run"])
    assert "set -euo pipefail" in command
    assert ".control/scripts/gates.py" in command
    assert "--gate regression" in command
    assert "--scope full" in command
    for swallowed in ("|| true", "|| exit 0", "set +e"):
        assert swallowed not in command


def workflow_with_transport(*, qualify_condition="failure() || cancelled()",
                            upload_condition=None, summary_condition="always()",
                            summary_run=None, include_qualify=True,
                            include_upload=True, include_summary=True,
                            upload_paths=None, if_no_files_found="warn",
                            include_hidden_files=True,
                            gate_id="regression-gate",
                            qualify_id="qualify-diagnostics",
                            upload_id="diagnostics-upload",
                            target_ref="$PAPERTRACE_HEAD",
                            qualify_run=None):
    workflow = copy.deepcopy(
        yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    )
    _job_name, _job, steps, gate_index = regression_gate_job(workflow)
    gate = steps[gate_index]
    gate["id"] = gate_id
    if upload_condition is None:
        upload_condition = (
            f"failure() && !cancelled() && steps.{gate_id}.outcome == 'failure' && "
            f"steps.{qualify_id}.outcome == 'success'"
        )
    if summary_run is None:
        summary_run = (
            "set -euo pipefail\n{\n"
            "  printf 'gate=%s\\n' \"${{ steps." + gate_id + ".outcome }}\"\n"
            "  printf 'qualify=%s\\n' \"${{ steps." + qualify_id + ".outcome }}\"\n"
            "  printf 'upload=%s\\n' \"${{ steps." + upload_id + ".outcome }}\"\n"
            "  printf 'job=%s\\n' \"${{ job.status }}\"\n"
            "} >> \"$GITHUB_STEP_SUMMARY\"\n"
        )
    if qualify_run is None:
        qualify_run = (
            "set -euo pipefail\n"
            ".venv/bin/python .control/scripts/full_regression.py "
            "--qualify-diagnostics "
            "--root \"$GITHUB_WORKSPACE/target\" "
            "--output \"$GITHUB_WORKSPACE/target/.local/full-regression\" "
            "--expected-target-sha \"" + target_ref + "\" "
            "--expected-control-sha \"${{ steps.control.outputs.sha }}\" "
            "--expected-base-sha \"${{ steps.control.outputs.base }}\"\n"
        )
    insert_at = gate_index + 1
    if include_qualify:
        steps.insert(insert_at, {
            "name": "Qualify current-run diagnostics for transport",
            "id": qualify_id,
            "if": qualify_condition,
            "shell": "bash",
            "run": qualify_run,
        })
        insert_at += 1
    if include_upload:
        upload_with = {
            "name": "full-regression-diagnostics",
            "if-no-files-found": if_no_files_found,
            "path": upload_paths or SIX_ARTIFACT_PATHS_TEXT,
        }
        if include_hidden_files is not None:
            upload_with["include-hidden-files"] = include_hidden_files
        steps.insert(insert_at, {
            "name": "Upload bounded failure diagnostics",
            "id": upload_id,
            "if": upload_condition,
            "uses": "actions/upload-artifact@v4",
            "with": upload_with,
        })
        insert_at += 1
    if include_summary:
        steps.insert(insert_at, {
            "name": "Summarize regression diagnostics",
            "if": summary_condition,
            "shell": "bash",
            "run": summary_run,
        })
    return workflow


@pytest.mark.parametrize(
    ("qualify_condition", "upload_condition"),
    [
        (
            "failure()",
            "failure() && !cancelled() && "
            "steps.regression-gate.outcome == 'failure' && "
            "steps.qualify-diagnostics.outcome == 'success'",
        ),
        (
            "failure() || cancelled()",
            "failure() && !cancelled() && "
            "steps.regression-gate.outcome == 'failure' && "
            "steps.qualify-diagnostics.outcome == 'success'",
        ),
        (
            "cancelled() || failure()",
            "failure() && !cancelled() && "
            "steps.regression-gate.outcome == 'failure' && "
            "steps.qualify-diagnostics.outcome == 'success'",
        ),
        (
            "failure()",
            "failure() && !cancelled() && "
            "(steps.regression-gate.outcome == 'failure') && "
            "steps.qualify-diagnostics.outcome == 'success'",
        ),
    ],
)
def test_workflow_transport_chain_accepts_supported_failure_policies(
    qualify_condition, upload_condition,
):
    workflow = workflow_with_transport(
        qualify_condition=qualify_condition, upload_condition=upload_condition,
    )
    plan = validate_regression_diagnostics_workflow(workflow)
    upload = workflow["jobs"]["regression"]["steps"][plan["upload_index"]]
    condition = normalize_condition(upload["if"])
    assert condition == normalize_condition(upload_condition)
    assert "failure()" in condition
    assert "!cancelled()" in condition
    assert "success()" not in condition
    assert "always()" not in condition
    assert f"steps.{plan['gate_id']}.outcome == 'failure'" in condition
    assert f"steps.{plan['qualify_id']}.outcome == 'success'" in condition
    assert (upload.get("with") or {}).get("if-no-files-found") in {"warn", "ignore"}
    assert (upload.get("with") or {}).get("include-hidden-files") is True
    summary = workflow["jobs"]["regression"]["steps"][plan["summary_index"]]
    for reference in (plan["gate_id"], plan["qualify_id"], plan["upload_id"]):
        assert f"steps.{reference}.outcome" in summary["run"]
    assert plan["summary_index"] > plan["upload_index"] > plan["qualify_index"] > plan["gate_index"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("upload_condition", "failure() || true"),
        ("upload_condition", "failure() && false"),
        ("upload_condition", "success()"),
        ("upload_condition", "failure()"),
        (
            "upload_condition",
            "steps.qualify-diagnostics.outcome == 'success'",
        ),
        (
            "upload_condition",
            "failure() && steps.regression-gate.outcome == 'failure' && "
            "steps.qualify-diagnostics.outcome == 'success'",
        ),
        (
            "upload_condition",
            "failure() && !cancelled() && "
            "steps.regression-gate.outcome == 'failure' && "
            "steps.qualify-diagnostics.outcome == 'success' || true",
        ),
        (
            "upload_condition",
            "failure() && !cancelled() && "
            "steps.regression-gate.outcome == 'success' && "
            "steps.qualify-diagnostics.outcome == 'success'",
        ),
        ("summary_condition", "always() && false"),
        ("summary_condition", "success()"),
    ],
)
def test_workflow_transport_chain_rejects_substring_condition_tricks(field, value):
    workflow = workflow_with_transport(**{field: value})
    with pytest.raises(AssertionError):
        validate_regression_diagnostics_workflow(workflow)


def test_workflow_rejects_outcome_only_upload_with_implicit_success():
    workflow = workflow_with_transport(
        upload_condition=(
            "steps.regression-gate.outcome == 'failure' && "
            "steps.qualify-diagnostics.outcome == 'success'"
        )
    )
    with pytest.raises(AssertionError):
        validate_regression_diagnostics_workflow(workflow)


def test_workflow_transport_chain_requires_ordered_regression_job_chain():
    workflow = workflow_with_transport()
    validate_regression_diagnostics_workflow(workflow)
    regression_steps = workflow["jobs"]["regression"]["steps"]
    workflow["jobs"]["regression"]["steps"] = [
        step for step in regression_steps
        if "BASE_VERIFIER_UPGRADE_REQUIRED" not in str(step.get("run", ""))
    ]
    with pytest.raises(AssertionError):
        validate_regression_diagnostics_workflow(workflow)

    workflow = workflow_with_transport()
    regression_steps = workflow["jobs"]["regression"]["steps"]
    moved = [
        step for step in regression_steps
        if step.get("id") in {"qualify-diagnostics", "diagnostics-upload"}
        or "GITHUB_STEP_SUMMARY" in str(step.get("run", ""))
    ]
    workflow["jobs"]["regression"]["steps"] = [
        step for step in regression_steps if step not in moved
    ]
    workflow["jobs"]["schema"]["steps"].extend(moved)
    with pytest.raises(AssertionError):
        validate_regression_diagnostics_workflow(workflow)

    workflow = workflow_with_transport()
    regression_steps = workflow["jobs"]["regression"]["steps"]
    qualify = next(step for step in regression_steps if step.get("id") == "qualify-diagnostics")
    regression_steps.remove(qualify)
    regression_steps.append(qualify)
    with pytest.raises(AssertionError):
        validate_regression_diagnostics_workflow(workflow)

    workflow = workflow_with_transport()
    gate = next(step for step in workflow["jobs"]["regression"]["steps"] if is_regression_gate(step))
    del gate["id"]
    with pytest.raises(MissingDiagnosticsTransport):
        validate_regression_diagnostics_workflow(workflow)


def test_workflow_rejects_comment_or_print_only_qualification():
    workflow = workflow_with_transport()
    steps = workflow["jobs"]["regression"]["steps"]
    qualify = next(step for step in steps if step.get("id") == "qualify-diagnostics")
    qualify["run"] = (
        "# .venv/bin/python .control/scripts/full_regression.py "
        "--qualify-diagnostics --root \"$GITHUB_WORKSPACE/target\"\n"
        "printf '{\"status\":\"withheld\",\"files\":[]}\\n'\n"
        "exit 0\n"
    )
    with pytest.raises(AssertionError):
        validate_regression_diagnostics_workflow(workflow)


def test_workflow_rejects_wrong_root_output_or_self_described_metadata():
    workflow = workflow_with_transport()
    steps = workflow["jobs"]["regression"]["steps"]
    qualify = next(step for step in steps if step.get("id") == "qualify-diagnostics")
    qualify["run"] = qualify["run"].replace(
        '--root "$GITHUB_WORKSPACE/target"',
        '--root "$GITHUB_WORKSPACE/other-tree"',
    )
    with pytest.raises(AssertionError):
        validate_regression_diagnostics_workflow(workflow)

    workflow = workflow_with_transport()
    steps = workflow["jobs"]["regression"]["steps"]
    qualify = next(step for step in steps if step.get("id") == "qualify-diagnostics")
    qualify["run"] = qualify["run"].replace(
        '--output "$GITHUB_WORKSPACE/target/.local/full-regression"',
        '--output "$GITHUB_WORKSPACE/other-output"',
    )
    with pytest.raises(AssertionError):
        validate_regression_diagnostics_workflow(workflow)

    workflow = workflow_with_transport()
    steps = workflow["jobs"]["regression"]["steps"]
    qualify = next(step for step in steps if step.get("id") == "qualify-diagnostics")
    qualify["run"] = qualify["run"].replace(
        '--expected-target-sha "$PAPERTRACE_HEAD"',
        '--expected-target-sha '
        '"$GITHUB_WORKSPACE/target/.local/full-regression/manifest.json"',
    )
    with pytest.raises(AssertionError):
        validate_regression_diagnostics_workflow(workflow)


def test_workflow_rejects_pre_gate_other_job_or_broader_raw_uploads():
    workflow = workflow_with_transport()
    steps = workflow["jobs"]["regression"]["steps"]
    gate_index = next(index for index, step in enumerate(steps) if is_regression_gate(step))
    steps.insert(gate_index, {
        "id": "pre-gate-upload",
        "if": "always()",
        "uses": "actions/upload-artifact@v4",
        "with": {"path": SIX_ARTIFACT_PATHS_TEXT},
    })
    with pytest.raises(AssertionError):
        validate_regression_diagnostics_workflow(workflow)

    workflow = workflow_with_transport()
    workflow["jobs"]["schema"]["steps"].append({
        "id": "other-job-upload",
        "if": "always()",
        "uses": "actions/upload-artifact@v4",
        "with": {"path": SIX_ARTIFACT_PATHS_TEXT},
    })
    with pytest.raises(AssertionError):
        validate_regression_diagnostics_workflow(workflow)

    workflow = workflow_with_transport()
    workflow["jobs"]["schema"]["steps"].append({
        "id": "raw-upload",
        "uses": "actions/upload-artifact@v4",
        "with": {"path": "target/.local"},
    })
    with pytest.raises(AssertionError):
        validate_regression_diagnostics_workflow(workflow)


def test_workflow_rejects_skipped_gate_or_job_conditions():
    workflow = workflow_with_transport()
    workflow["jobs"]["regression"]["if"] = "failure()"
    gate = next(step for step in workflow["jobs"]["regression"]["steps"] if is_regression_gate(step))
    gate["if"] = False
    with pytest.raises(AssertionError):
        validate_regression_diagnostics_workflow(workflow)

    workflow = workflow_with_transport()
    gate = next(step for step in workflow["jobs"]["regression"]["steps"] if is_regression_gate(step))
    gate["if"] = False
    with pytest.raises(AssertionError):
        validate_regression_diagnostics_workflow(workflow)

    workflow = workflow_with_transport()
    gate = next(step for step in workflow["jobs"]["regression"]["steps"] if is_regression_gate(step))
    gate["if"] = "always()"
    with pytest.raises(AssertionError):
        validate_regression_diagnostics_workflow(workflow)


def test_workflow_accepts_renamed_ids_and_trusted_metadata_variant():
    workflow = workflow_with_transport(
        gate_id="gate-custom",
        qualify_id="qualify-custom",
        upload_id="artifact-custom",
        target_ref="${{ env.PAPERTRACE_HEAD }}",
    )
    plan = validate_regression_diagnostics_workflow(workflow)
    assert plan["gate_id"] == "gate-custom"
    assert plan["qualify_id"] == "qualify-custom"
    assert plan["upload_id"] == "artifact-custom"
    upload = workflow["jobs"]["regression"]["steps"][plan["upload_index"]]
    condition = normalize_condition(upload["if"])
    assert "failure()" in condition
    assert "!cancelled()" in condition
    assert "steps.gate-custom.outcome == 'failure'" in condition
    assert "steps.qualify-custom.outcome == 'success'" in condition
    assert (upload.get("with") or {}).get("include-hidden-files") is True
    summary = workflow["jobs"]["regression"]["steps"][plan["summary_index"]]
    for reference in ("gate-custom", "qualify-custom", "artifact-custom"):
        assert f"steps.{reference}.outcome" in summary["run"]


def test_workflow_allows_unrelated_non_overlapping_upload():
    workflow = workflow_with_transport()
    workflow["jobs"]["schema"]["steps"].append({
        "id": "coverage-upload",
        "uses": "actions/upload-artifact@v4",
        "with": {"path": "target/coverage.xml"},
    })
    validate_regression_diagnostics_workflow(workflow)


def test_workflow_transport_requires_hidden_file_opt_in():
    workflow = workflow_with_transport()
    validate_regression_diagnostics_workflow(workflow)
    for value in (None, False, "false"):
        workflow = workflow_with_transport(include_hidden_files=value)
        with pytest.raises(AssertionError):
            validate_regression_diagnostics_workflow(workflow)
    workflow = workflow_with_transport(include_hidden_files="true")
    validate_regression_diagnostics_workflow(workflow)


def test_workflow_state_table_binds_upload_to_gate_and_qualification():
    workflow = workflow_with_transport(
        gate_id="gate-state",
        qualify_id="qualify-state",
        upload_id="upload-state",
    )
    plan = validate_regression_diagnostics_workflow(workflow)
    upload = workflow["jobs"]["regression"]["steps"][plan["upload_index"]]
    condition = normalize_condition(upload["if"])
    assert condition == (
        "failure() && !cancelled() && steps.gate-state.outcome == 'failure' && "
        "steps.qualify-state.outcome == 'success'"
    )
    states = [
        ("pass", False, False, "success", "success", False),
        ("gate-fail-qualified", True, False, "failure", "success", True),
        ("cancelled-after-gate-fail", True, True, "failure", "success", False),
        ("gate-fail-withheld", True, False, "failure", "failure", False),
        ("gate-fail-missing", True, False, "failure", "skipped", False),
        ("pre-gate-fail-skipped", True, False, "skipped", "success", False),
    ]
    for scenario, failure_status, cancelled, gate_outcome, qualify_outcome, allowed in states:
        eligible = (
            failure_status
            and not cancelled
            and gate_outcome == "failure"
            and qualify_outcome == "success"
        )
        assert eligible is allowed, scenario
    summary = workflow["jobs"]["regression"]["steps"][plan["summary_index"]]
    assert normalize_condition(summary["if"]) == "always()"
    for reference in ("gate-state", "qualify-state", "upload-state"):
        assert f"steps.{reference}.outcome" in summary["run"]
    assert "job.status" in summary["run"] or "cancelled" in summary["run"].lower()


@pytest.mark.parametrize(
    "upload_paths",
    [
        SIX_ARTIFACT_PATHS_TEXT + "\ntarget/.local/full-regression/rogue/diagnostics/events.jsonl",
        SIX_ARTIFACT_PATHS_TEXT.replace(
            "team-offline/diagnostics/events.jsonl",
            "team-offline-prior/diagnostics/events.jsonl",
        ),
        SIX_ARTIFACT_PATHS_TEXT.replace(
            "team-offline/diagnostics/events.jsonl",
            "team-offline/diagnostics/stdout.txt",
        ),
        SIX_ARTIFACT_PATHS_TEXT + "\ntarget/.local/full-regression/*/diagnostics/*.jsonl",
    ],
)
def test_workflow_transport_allowlist_rejects_prior_rogue_raw_or_wildcard(upload_paths):
    workflow = workflow_with_transport(upload_paths=upload_paths)
    with pytest.raises(AssertionError):
        validate_regression_diagnostics_workflow(workflow)
    workflow = workflow_with_transport(if_no_files_found="error")
    with pytest.raises(AssertionError):
        validate_regression_diagnostics_workflow(workflow)


def test_workflow_summary_records_actual_outcome_and_cancellation():
    workflow = workflow_with_transport()
    plan = validate_regression_diagnostics_workflow(workflow)
    summary = workflow["jobs"]["regression"]["steps"][plan["summary_index"]]
    run = str(summary["run"])
    assert "GITHUB_STEP_SUMMARY" in run
    for reference in (plan["gate_id"], plan["qualify_id"], plan["upload_id"]):
        assert f"steps.{reference}.outcome" in run
    assert "job.status" in run or "cancelled" in run.lower()

    bad = workflow_with_transport(
        summary_run=(
            "set -euo pipefail\n{\n"
            "  printf 'gate=%s\\n' \"${{ steps.regression-gate.outcome }}\"\n"
            "  printf 'qualify=%s\\n' \"${{ steps.qualify-diagnostics.outcome }}\"\n"
            "  printf 'upload=%s\\n' \"${{ steps.diagnostics-upload.conclusion }}\"\n"
            "  printf 'job=%s\\n' \"${{ job.status }}\"\n"
            "} >> \"$GITHUB_STEP_SUMMARY\"\n"
        )
    )
    with pytest.raises(AssertionError):
        validate_regression_diagnostics_workflow(bad)
    bad = workflow_with_transport(
        summary_run=(
            "set -euo pipefail\n{\n"
            "  printf 'gate=%s\\n' \"${{ steps.regression-gate.outcome }}\"\n"
            "  printf 'qualify=%s\\n' \"${{ steps.qualify-diagnostics.outcome }}\"\n"
            "  printf 'upload=%s\\n' \"${{ steps.diagnostics-upload.outcome }}\"\n"
            "} >> \"$GITHUB_STEP_SUMMARY\"\n"
        )
    )
    with pytest.raises(AssertionError):
        validate_regression_diagnostics_workflow(bad)


def test_real_workflow_exposes_qualified_failure_transport_chain():
    workflow = yaml.safe_load(
        (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    )
    missing = None
    try:
        validate_regression_diagnostics_workflow(workflow)
    except MissingDiagnosticsTransport as error:
        missing = str(error)
    if missing is not None:
        pytest.fail(f"AVAILABILITY RED: {missing}", pytrace=False)
