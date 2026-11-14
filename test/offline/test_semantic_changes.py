"""Gate4 configuration trigger tests using disposable real Git histories."""

import importlib.util
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("papertrace_semantic_changes", ROOT / "scripts/semantic_changes.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("semantic_changes helper cannot be loaded")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
configuration_changed = MODULE.configuration_changed

PROJECT = '''[project]
name = "fixture-app"
version = "1.0"
authors = [{ name = "Synthetic Author" }]
description = "Synthetic fixture"
requires-python = ">=3.11"
dependencies = ["litellm>=1"]
[project.optional-dependencies]
dev = ["pytest>=8"]
vision = ["renderer[gpu]>=1"]
[tool.ruff]
line-length = 88
[tool.pytest.ini_options]
addopts = "-q"
[tool.uv.sources]
litellm = { index = "fixture" }
'''

LOCK = '''version = 1
revision = 3
requires-python = ">=3.11"
resolution-markers = ["python_full_version < '3.12'"]

[[package]]
name = "fixture-app"
source = { editable = "." }
dependencies = [{ name = "litellm" }]
[package.optional-dependencies]
dev = [{ name = "pytest" }]
vision = [{ name = "renderer", extra = ["gpu"] }]
[package.dev-dependencies]
dev = [{ name = "pytest" }]

[[package]]
name = "litellm"
version = "1.2.0"
source = { registry = "https://pypi.org/simple" }
dependencies = [{ name = "anyio", marker = "sys_platform == 'linux'" }]
sdist = { hash = "sha256:litellm-hash" }

[[package]]
name = "anyio"
version = "4.5.0"
source = { registry = "https://pypi.org/simple" }
sdist = { hash = "sha256:anyio-hash" }

[[package]]
name = "pytest"
version = "8.0.0"
source = { registry = "https://pypi.org/simple" }

[[package]]
name = "renderer"
version = "2.0.0"
source = { registry = "https://pypi.org/simple" }
[package.optional-dependencies]
gpu = [{ name = "gpu-plugin" }]

[[package]]
name = "gpu-plugin"
version = "1.0.0"
source = { registry = "https://pypi.org/simple" }

[[package]]
name = "unrelated"
version = "1.0.0"
source = { registry = "https://pypi.org/simple" }
'''

PACKAGE_PROJECT = '''[project]
name = "fixture-package"
authors = [{ name = "Synthetic Author" }]
dependencies = ["anyio"]
'''

PACKAGE_LOCK = '''version = 1
revision = 3
requires-python = ">=3.11"

[[package]]
name = "fixture-package"
source = { editable = "." }
dependencies = [{ name = "anyio" }]

[[package]]
name = "anyio"
version = "4.5.0"
source = { registry = "https://pypi.org/simple" }
'''


class GitContext:
    def __init__(self, root):
        self.root = root
        self.head = None
        self.baseline = None
        self.base = ""

    def git(self, *args):
        result = subprocess.run(["git", "-C", str(self.root), *args], capture_output=True, check=True)
        return result.stdout

    def read(self, path, ref=None):
        if ref is not None:
            return self.git("show", f"{ref}:{path}").decode("utf-8")
        return (self.root / path).read_text(encoding="utf-8")

    def changes(self):
        return self.git("diff", "--name-only", self.base, "--").decode().splitlines()


def put(ctx, path, text):
    target = ctx.root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


@pytest.fixture
def repo(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    ctx = GitContext(tmp_path)
    ctx.git("config", "user.name", "Synthetic Fixture")
    ctx.git("config", "user.email", "fixture@example.invalid")
    put(ctx, "pyproject.toml", PROJECT)
    put(ctx, "uv.lock", LOCK)
    put(ctx, "requirements-runtime.in", "litellm==1.2.0  # synthetic pin\n")
    put(ctx, "requirements-runtime.lock", "litellm==1.2.0 --hash=sha256:fixture\n")
    put(ctx, "packages/fixture/pyproject.toml", PACKAGE_PROJECT)
    put(ctx, "packages/fixture/uv.lock", PACKAGE_LOCK)
    ctx.git("add", ".")
    ctx.git("commit", "-qm", "synthetic base")
    ctx.base = ctx.git("rev-parse", "HEAD").decode().strip()
    return ctx


@pytest.mark.parametrize(("old", "new"), [
    ('line-length = 88', 'line-length = 100'),
    ('addopts = "-q"', 'addopts = "-q -ra"'),
    ('Synthetic Author', 'Another Synthetic Author'),
    ('Synthetic fixture', 'Changed descriptive metadata'),
])
def test_static_tools_and_author_description_metadata_do_not_trigger(repo, old, new):
    put(repo, "pyproject.toml", repo.read("pyproject.toml").replace(old, new))
    assert configuration_changed(repo, "pyproject.toml") is False


@pytest.mark.parametrize(("old", "new"), [
    ('litellm>=1', 'litellm>=2'),
    ('requires-python = ">=3.11"', 'requires-python = ">=3.12"'),
    ('index = "fixture"', 'index = "another-fixture"'),
])
def test_runtime_dependencies_python_and_uv_sources_trigger(repo, old, new):
    put(repo, "pyproject.toml", repo.read("pyproject.toml").replace(old, new))
    assert configuration_changed(repo, "pyproject.toml") is True


def test_unknown_model_tool_configuration_triggers(repo):
    put(repo, "pyproject.toml", repo.read("pyproject.toml") + '\n[tool.model_runtime]\nmodel = "fixture-model"\n')
    assert configuration_changed(repo, "pyproject.toml") is True


def test_package_local_project_and_lock_are_scoped_as_configuration(repo):
    manifest = repo.read("packages/fixture/pyproject.toml")
    put(repo, "packages/fixture/pyproject.toml", manifest.replace("Synthetic Author", "Other Author"))
    assert configuration_changed(repo, "packages/fixture/pyproject.toml") is False
    lock = repo.read("packages/fixture/uv.lock").replace("4.5.0", "4.6.0")
    put(repo, "packages/fixture/uv.lock", lock)
    assert configuration_changed(repo, "packages/fixture/uv.lock") is True


@pytest.mark.parametrize("path", ["requirements-runtime.in", "requirements-runtime.lock"])
def test_runtime_requirements_comments_and_blank_lines_are_ignored(repo, path):
    content = repo.read(path)
    put(repo, path, "# harmless comment\n\n" + content.replace("# synthetic pin", "# edited comment"))
    assert configuration_changed(repo, path) is False


@pytest.mark.parametrize(("path", "new"), [
    ("requirements-runtime.in", "litellm==2.0.0  # synthetic pin\n"),
    ("requirements-runtime.lock", "litellm==1.2.0 --hash=sha256:changed\n"),
])
def test_runtime_requirement_pin_or_hash_change_triggers(repo, path, new):
    put(repo, path, new)
    assert configuration_changed(repo, path) is True


def test_uv_lock_ignores_dev_only_and_unreachable_package_versions(repo):
    lock = repo.read("uv.lock").replace('name = "pytest"\nversion = "8.0.0"', 'name = "pytest"\nversion = "9.0.0"')
    lock = lock.replace('name = "unrelated"\nversion = "1.0.0"', 'name = "unrelated"\nversion = "2.0.0"')
    put(repo, "uv.lock", lock)
    assert configuration_changed(repo, "uv.lock") is False


@pytest.mark.parametrize(("old", "new"), [
    ('name = "litellm"\nversion = "1.2.0"', 'name = "litellm"\nversion = "1.3.0"'),
    ('name = "anyio"\nversion = "4.5.0"', 'name = "anyio"\nversion = "4.6.0"'),
    ('registry = "https://pypi.org/simple" }\ndependencies = [{ name = "anyio"', 'registry = "https://fixture.invalid/simple" }\ndependencies = [{ name = "anyio"'),
    ('sha256:litellm-hash', 'sha256:changed-litellm-hash'),
    ("sys_platform == 'linux'", "sys_platform == 'darwin'"),
    ('name = "gpu-plugin"\nversion = "1.0.0"', 'name = "gpu-plugin"\nversion = "2.0.0"'),
])
def test_uv_lock_production_and_activated_extra_changes_trigger(repo, old, new):
    lock = repo.read("uv.lock")
    assert old in lock
    put(repo, "uv.lock", lock.replace(old, new))
    assert configuration_changed(repo, "uv.lock") is True


@pytest.mark.parametrize(("path", "content"), [
    ("pyproject.toml", "[project\nname = 'broken'\n"),
    ("uv.lock", "[package\nname = 'broken'\n"),
])
def test_malformed_toml_fails_closed(repo, path, content):
    put(repo, path, content)
    assert configuration_changed(repo, path) is True


def test_new_or_missing_runtime_configuration_fails_closed(repo):
    put(repo, "packages/new-package/pyproject.toml", PROJECT)
    assert configuration_changed(repo, "packages/new-package/pyproject.toml") is True
    put(repo, "requirements-runtime.in", "")
    assert configuration_changed(repo, "requirements-runtime.in") is True


def test_uv_lock_dev_metadata_does_not_trigger(repo):
    metadata = '\n[package.metadata]\nrequires-dist = [{name = "litellm", specifier = ">=1"}, {name = "pytest", specifier = ">=8", marker = "extra == \'dev\'"}]\nprovides-extras = ["dev", "vision"]\n[package.metadata.requires-dev]\ndev = [{name = "pytest", specifier = ">=8"}]\n'
    lock = LOCK.replace('\n[[package]]\nname = "litellm"', metadata + '\n[[package]]\nname = "litellm"')
    put(repo, "uv.lock", lock)
    repo.git("add", ".")
    repo.git("commit", "-qm", "synthetic prior resolver metadata")
    repo.base = repo.git("rev-parse", "HEAD").decode().strip()
    put(repo, "uv.lock", lock.replace('specifier = ">=8"', 'specifier = ">=9"'))
    assert configuration_changed(repo, "uv.lock") is False


def test_or_extra_marker_cannot_hide_a_production_dependency(repo):
    lock = LOCK.replace("sys_platform == 'linux'", "extra == 'dev' or sys_platform == 'linux'")
    put(repo, "uv.lock", lock)
    repo.git("add", ".")
    repo.git("commit", "-qm", "synthetic mixed extra and production marker")
    repo.base = repo.git("rev-parse", "HEAD").decode().strip()
    put(repo, "uv.lock", lock.replace('name = "anyio"\nversion = "4.5.0"', 'name = "anyio"\nversion = "4.6.0"'))
    assert configuration_changed(repo, "uv.lock") is True


def gate_verifier():
    spec = importlib.util.spec_from_file_location("papertrace_semantic_gate_integration", ROOT / "scripts/semantic_evidence.py")
    assert spec is not None and spec.loader is not None
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)
    return verifier


@pytest.mark.parametrize(("old", "new", "expected"), [
    ('line-length = 88', 'line-length = 100', "NOT_REQUIRED"),
    ('addopts = "-q"', 'addopts = "-q -ra"', "NOT_REQUIRED"),
    ('litellm>=1', 'litellm>=2', "BLOCKED"),
    ('index = "fixture"', 'index = "another-fixture"', "BLOCKED"),
])
def test_real_gate_uses_content_classification_without_a_live_call(repo, old, new, expected):
    put(repo, "pyproject.toml", repo.read("pyproject.toml").replace(old, new))
    assert gate_verifier().verify_semantic(repo)["status"] == expected


def test_unrelated_path_is_not_a_configuration_trigger(repo):
    assert configuration_changed(repo, "src/papertrace/service.py") is False
