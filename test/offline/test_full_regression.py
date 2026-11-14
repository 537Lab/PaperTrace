"""GOV-02: executable full-suite runner; fixture repositories are synthetic."""

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def runner():
    path = ROOT / "scripts/full_regression.py"
    assert path.is_file(), "GOV-02: full regression runner must be implemented"
    spec = importlib.util.spec_from_file_location("papertrace_full_regression", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def fixture_suite(tmp_path, source):
    (tmp_path / "test").mkdir()
    (tmp_path / "test/test_sample.py").write_text(source, encoding="utf-8")
    (tmp_path / "pytest.ini").write_text("[pytest]\nmarkers =\n    offline: offline\n    live_api: needs approved provider\n", encoding="utf-8")
    return runner().Suite("fixture", ("test",), sys.executable, "pytest.ini", ("pytest_socket",))


def test_unmarked_test_is_collected_executed_and_failure_blocks(tmp_path):
    """GOV-02: an unmarked test cannot disappear behind an offline selector."""
    suite = fixture_suite(tmp_path, "def test_unmarked():\n    assert False\n")
    report = runner().run_suite(tmp_path, suite, tmp_path / "evidence", timeout=20)
    assert report["status"] == "FAIL"
    assert report["collected"] == ["test/test_sample.py::test_unmarked"]
    assert report["outcomes"]["failed"] == 1
    assert Path(report["report_path"]).is_file()
    assert json.loads(Path(report["report_path"]).read_text())["collected"]


def test_live_items_remain_in_inventory_but_are_not_called_without_permission(tmp_path):
    """COST-01: absent live authorization blocks full, without hiding live items."""
    suite = fixture_suite(tmp_path, '''import pytest
@pytest.mark.offline
def test_offline():
    assert True

def test_unmarked():
    assert True

@pytest.mark.live_api
def test_live():
    raise AssertionError("must not run without explicit authorization")
''')
    report = runner().run_suite(tmp_path, suite, tmp_path / "evidence", timeout=20)
    assert report["status"] == "BLOCKED"
    assert len(report["collected"]) == 3
    assert report["pending_live"] == ["test/test_sample.py::test_live"]
    assert report["outcomes"] == {"passed": 2, "failed": 0, "skipped": 0, "xfailed": 0, "xpassed": 0}


def test_explicit_operator_live_authorization_can_complete_a_full_fixture_suite(tmp_path):
    """GOV-02: full is capable of PASS; synthetic fixture makes no API request."""
    suite = fixture_suite(tmp_path, '''import pytest
@pytest.mark.live_api
def test_live():
    assert True
''')
    report = runner().run_suite(tmp_path, suite, tmp_path / "evidence", timeout=20, run_live=True)
    assert report["status"] == "PASS"
    assert report["outcomes"]["passed"] == 1
    assert report["pending_live"] == []


def test_xpass_cannot_be_reported_as_zero_regression(tmp_path):
    """GOV-02: XPASS signals a changed expectation requiring human disposition."""
    suite = fixture_suite(tmp_path, '''import pytest
@pytest.mark.xfail(reason="synthetic historical issue")
def test_unexpected_pass():
    assert True
''')
    report = runner().run_suite(tmp_path, suite, tmp_path / "evidence", timeout=20)
    assert report["status"] == "FAIL"
    assert report["outcomes"]["xpassed"] == 1


def git(root, *args):
    import subprocess
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=True).stdout.strip()


def committed_fixture(tmp_path):
    suite = fixture_suite(tmp_path, "def test_first():\n    assert True\n\ndef test_second():\n    assert True\n")
    git(tmp_path, "init", "-q")
    git(tmp_path, "add", ".")
    git(tmp_path, "-c", "user.name=Synthetic fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "synthetic prior suite")
    return suite, git(tmp_path, "rev-parse", "HEAD")


def test_full_runner_can_pass_a_complete_prior_fixture_suite(tmp_path):
    """GOV-02: no unconditional BLOCKED when full evidence really exists."""
    suite, base = committed_fixture(tmp_path)
    report = runner().run_full(tmp_path, base, tmp_path / "evidence", suites=(suite,), timeout=20)
    assert report["status"] == "PASS"
    assert report["total_collected"] == 2
    assert report["total_passed"] == 2
    assert report["missing_prior"] == []


def test_prior_test_node_cannot_be_deleted_inside_an_existing_file(tmp_path):
    """GOV-02: comparing only filenames is not sufficient for all prior suites."""
    suite, base = committed_fixture(tmp_path)
    (tmp_path / "test/test_sample.py").write_text("def test_first():\n    assert True\n", encoding="utf-8")
    report = runner().run_full(tmp_path, base, tmp_path / "evidence", suites=(suite,), timeout=20)
    assert report["status"] == "FAIL"
    assert report["missing_prior"] == ["fixture:test/test_sample.py::test_second"]


def test_collection_cannot_open_sockets_even_in_conftest_import(tmp_path):
    """SEC-01: collection runs repository conftest before pytest_configure."""
    suite = fixture_suite(tmp_path, "def test_safe():\n    assert True\n")
    (tmp_path / "test/conftest.py").write_text("import socket\nsocket.socket()\n", encoding="utf-8")
    report = runner().run_suite(tmp_path, suite, tmp_path / "evidence", timeout=20)
    assert report["status"] != "PASS"
    stderr = (tmp_path / "evidence/stderr.txt").read_text()
    assert "SocketBlockedError" in stderr


def test_missing_import_is_reported_as_environment_blockage_not_test_pass(tmp_path):
    """GOV-02: the dependency gap remains visible, without renaming full to init."""
    suite = fixture_suite(tmp_path, "import deliberately_absent_papertrace_fixture\ndef test_unused():\n    assert True\n")
    report = runner().run_suite(tmp_path, suite, tmp_path / "evidence", timeout=20)
    assert report["status"] == "BLOCKED"
    assert report["collection_errors"][0]["kind"] == "missing-dependency"


def test_configured_deselection_is_not_silently_accepted(tmp_path):
    """GOV-02: a config-level -k cannot hide prior tests."""
    suite = fixture_suite(tmp_path, "def test_first():\n    assert True\n\ndef test_second():\n    assert False\n")
    with (tmp_path / "pytest.ini").open("a") as stream:
        stream.write("addopts = -k first\n")
    report = runner().run_suite(tmp_path, suite, tmp_path / "evidence", timeout=20)
    assert report["status"] == "FAIL"


def test_full_runner_preserves_relative_venv_interpreter_across_prior_cwd(tmp_path):
    """GOV-02: baseline collection must use the same interpreter as current tests."""
    import os
    from dataclasses import replace

    suite, base = committed_fixture(tmp_path)
    suite = replace(suite, python=os.path.relpath(sys.executable, tmp_path))
    report = runner().run_full(tmp_path, base, tmp_path / "evidence", suites=(suite,), timeout=20)
    assert report["status"] == "PASS"


def test_timeout_stops_owned_test_descendants(tmp_path):
    """GOV-02: a timed-out suite must not leave its spawned processes alive."""
    import os
    import subprocess
    import time

    child_pid = tmp_path / "child.pid"
    source = f'''import subprocess, sys, time
from pathlib import Path
def test_waiting_child():
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    Path({str(child_pid)!r}).write_text(str(child.pid))
    time.sleep(30)
'''
    suite = fixture_suite(tmp_path, source)
    report = runner().run_suite(tmp_path, suite, tmp_path / "evidence", timeout=0.8)
    assert report["status"] == "BLOCKED"
    assert child_pid.exists(), "fixture child did not start before timeout"
    pid = int(child_pid.read_text())
    try:
        time.sleep(0.1)
        state = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()
        assert not state or state.startswith("Z"), f"owned child remained running: {pid}"
    finally:
        try:
            os.kill(pid, 15)
        except ProcessLookupError:
            pass


def test_prior_live_marker_cannot_be_removed_to_execute_without_permission(tmp_path):
    """COST-01/GOV-02: prior live identity survives current marker removal."""
    sentinel = tmp_path / "forbidden-live-body"
    suite = fixture_suite(tmp_path, f'''import pytest
from pathlib import Path
@pytest.mark.live_api
def test_previously_live():
    Path({str(sentinel)!r}).write_text("body executed")
''')
    git(tmp_path, "init", "-q")
    git(tmp_path, "add", ".")
    git(tmp_path, "-c", "user.name=Synthetic fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "synthetic prior live test")
    base = git(tmp_path, "rev-parse", "HEAD")
    source = tmp_path / "test/test_sample.py"
    source.write_text(source.read_text().replace("@pytest.mark.live_api\n", ""), encoding="utf-8")
    report = runner().run_full(tmp_path, base, tmp_path / "evidence", suites=(suite,), timeout=20)
    assert report["status"] == "BLOCKED"
    assert not sentinel.exists(), "removing a marker must not execute a previously-live body"
    assert report["suites"][0]["pending_live"] == ["test/test_sample.py::test_previously_live"]


def test_runxfail_configuration_cannot_mask_an_expected_failure_marker(tmp_path):
    """GOV-02: --runxfail cannot turn changed expectations into zero-regression."""
    suite = fixture_suite(tmp_path, '''import pytest
@pytest.mark.xfail(reason="synthetic prior issue")
def test_now_passes():
    assert True
''')
    with (tmp_path / "pytest.ini").open("a") as stream:
        stream.write("addopts = --runxfail\n")
    report = runner().run_suite(tmp_path, suite, tmp_path / "evidence", timeout=20)
    assert report["status"] == "FAIL"
    assert report["configuration_errors"]


def test_offline_child_keeps_only_an_explicit_opencode_tool_locator(tmp_path, monkeypatch):
    """GOV-02: isolated HOME must not make a required installed tool disappear."""
    binary = tmp_path / "approved-tool"
    binary.write_text("synthetic executable locator only\n")
    monkeypatch.setenv("PAPERTRACE_OPENCODE_BINARY", str(binary))
    monkeypatch.setenv("UNRELATED_CREDENTIAL_SENTINEL", "not-forwarded")
    suite = fixture_suite(tmp_path, f'''import os
from pathlib import Path
def test_locator():
    assert os.environ.get("PAPERTRACE_OPENCODE_BINARY") == {str(binary)!r}
    assert "UNRELATED_CREDENTIAL_SENTINEL" not in os.environ
    assert Path(os.environ["PAPERTRACE_OPENCODE_BINARY"]).is_file()
''')
    assert runner().run_suite(tmp_path, suite, tmp_path / "evidence", timeout=20)["status"] == "PASS"


def test_prior_snapshot_reuses_real_build_generated_version_metadata(tmp_path):
    """GOV-02: Git archives omit ignored setuptools_scm files, not old tests."""
    suite = fixture_suite(tmp_path, '''from fixture_version import __version__
def test_import_generated_version():
    assert __version__.startswith("1.")
''')
    (tmp_path / "pytest.ini").write_text((tmp_path / "pytest.ini").read_text() + "pythonpath = src\n")
    (tmp_path / "pyproject.toml").write_text('[tool.setuptools_scm]\nversion_file = "src/fixture_version/version.py"\n')
    package = tmp_path / "src/fixture_version"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("from .version import __version__\n")
    (tmp_path / ".gitignore").write_text("src/fixture_version/version.py\n")
    (package / "version.py").write_text('__version__ = "1.0+synthetic-build-metadata"\n')
    git(tmp_path, "init", "-q")
    git(tmp_path, "add", ".")
    git(tmp_path, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "synthetic generated metadata fixture")
    base = git(tmp_path, "rev-parse", "HEAD")
    report = runner().run_full(tmp_path, base, tmp_path / "evidence", suites=(suite,), timeout=20)
    assert report["status"] == "PASS", report
    assert report["generated_metadata"][0]["path"] == "src/fixture_version/version.py"
    assert report["missing_prior"] == []


def test_timeout_keeps_collected_inventory_and_already_executed_outcomes(tmp_path):
    """GOV-02: timeout is not permission to discard real failure/pass evidence."""
    suite = fixture_suite(tmp_path, '''import time
def test_first_pass():
    assert True
def test_later_hang():
    time.sleep(20)
''')
    report = runner().run_suite(tmp_path, suite, tmp_path / "evidence", timeout=1)
    assert report["status"] == "BLOCKED"
    assert len(report["collected"]) == 2
    assert report["outcomes"]["passed"] == 1


def test_full_cli_rejects_a_malformed_literal_base(tmp_path, capsys):
    """GOV-02: reject tokens rather than normalizing a caller's invalid SHA."""
    code = runner().main(["--root", str(tmp_path), "--base", "A" * 40, "--output", str(tmp_path / "evidence")])
    assert code == 1
    assert json.loads(capsys.readouterr().out)["status"] == "FAIL"
