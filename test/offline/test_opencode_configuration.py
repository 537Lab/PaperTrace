"""OpenCode v2.0.12 configuration contracts; ADR-001, INV-06, GOV-01/04."""

import json
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def support():
    """Fail explicitly if the verifier and isolated runtime helpers are absent."""
    path = ROOT / "scripts" / "opencode_support.py"
    assert path.is_file(), "safe OpenCode support is not implemented"
    spec = spec_from_file_location("papertrace_opencode_support", path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_native_configuration_is_plan_first_without_blocking_provider_selection():
    """GOV-01/04: native v2; Plan default; no global provider ban or model call."""
    config = json.loads((ROOT / "opencode.jsonc").read_text(encoding="utf-8"))
    assert config["default_agent"] == "papertrace-plan"
    assert "model" not in config
    assert config.get("providers", {}) == {}
    assert "policies" not in config and "experimental" not in config
    assert config["permissions"][0] == {
        "action": "*", "resource": "*", "effect": "deny"
    }
    assert "permission" not in config and "instructions" not in config
    assert config["formatter"] is False and config["lsp"] is False
    assert config["plugins"] == [] and config["mcp"]["servers"] == {}
    assert set(config["agents"]) == {
        "papertrace-plan", "papertrace-verify",
        "papertrace-build-A", "papertrace-build-B", "papertrace-build-C",
        "papertrace-build-D", "papertrace-build-E",
    }


def test_human_only_rules_are_present_in_the_discovered_project_instructions():
    """GOV-01/04: both rule source and actual AGENTS instructions preserve key human gates."""
    rules = (ROOT / ".opencode" / "rules.md").read_text(encoding="utf-8")
    instructions = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    for marker in ("学生", "非实现者", "凭据", "批准"):
        assert marker in rules
        assert marker in instructions
    config = json.loads((ROOT / "opencode.jsonc").read_text(encoding="utf-8"))
    module = support()
    assert all(agent.get("system") for agent in config["agents"].values())
    for letter, module_name in {
        "A": "library", "B": "retrieval", "C": "review",
        "D": "answer", "E": "reports",
    }.items():
        role = f"papertrace-build-{letter}"
        system = config["agents"][role]["system"]
        assert "测试准备阶段" in system, role
        assert "严禁写入任何 src/" in system, role
        assert "通过 GitHub 对具体测试 commit 实际批准" in system, role
        assert "即使工具 permission 允许" in system, role
        assert "此行为规则不是身份认证或 OS sandbox" in system, role
        # Native permissions deliberately remain a role/path scope, not an approval service.
        assert module.permission_effect(
            config, role, "edit", f"src/papertrace/{module_name}/service.py"
        ) == "allow"
    assert "instructions" not in config


def test_role_permissions_allow_owned_work_and_restrict_shared_or_sensitive_paths():
    """INV-06: Plan read-only; Build A-E own files only; boundary paths fail closed."""
    module = support()
    config, manifest = module.load_configuration()
    assert manifest["engine_configuration"] == "opencode.jsonc"
    assert manifest["not_auto_loaded_by_opencode"] is True
    assert set(manifest["roles"]) == set(config["agents"])
    assert manifest["roles"]["papertrace-plan"]["write_candidates"] == []
    assert manifest["roles"]["papertrace-verify"]["write_candidates"] == []

    module_names = {
        "A": "library", "B": "retrieval", "C": "review",
        "D": "answer", "E": "reports",
    }
    for letter, module_name in module_names.items():
        role_name = f"papertrace-build-{letter}"
        role = manifest["roles"][role_name]
        expected = {
            f"src/papertrace/{module_name}/*",
            f"test/offline/test_{module_name}.py",
            f"test/live/test_{module_name}.py",
            f"test/fixtures/{module_name}/*",
            f"docs/team/designs/module-{letter}/*",
        }
        assert expected <= set(role["write_candidates"])
        sample_paths = {
            f"src/papertrace/{module_name}/service.py",
            f"test/offline/test_{module_name}.py",
            f"test/live/test_{module_name}.py",
            f"test/fixtures/{module_name}/sample.json",
            f"docs/team/designs/module-{letter}/decision.md",
        }
        for path in sample_paths:
            assert module.permission_effect(config, role_name, "edit", path) == "allow"
            assert module.permission_effect(config, role_name, "read", path) == "allow"

        other_module = "review" if module_name != "review" else "library"
        assert module.permission_effect(
            config, role_name, "read", f"src/papertrace/{other_module}/service.py"
        ) == "ask"
        assert module.permission_effect(
            config, role_name, "edit", f"src/papertrace/{other_module}/service.py"
        ) == "deny"
        for path in (
            "src/papertrace/contracts.py", "docs/architecture/adr/001-architecture.md",
            "docs/code-governance/verification-constraints.md", "AGENTS.md",
            "opencode.jsonc", ".opencode/rules.md", "src/paperqa/docs.py",
            "packages/paper-qa/src/package.py", "pyproject.toml", "uv.lock",
            ".env", ".local/unblock/opencode/runtime.json", "../outside.txt",
        ):
            assert module.permission_effect(config, role_name, "edit", path) == "deny", path
        for path in (".env", ".env.local", ".local/unblock/opencode/key.json", "../outside.txt"):
            assert module.permission_effect(config, role_name, "read", path) == "deny", path

    assert module.permission_effect(
        config, "papertrace-plan", "read", "docs/req/requirements.yaml"
    ) == "allow"
    assert module.permission_effect(
        config, "papertrace-plan", "edit", "src/papertrace/library/service.py"
    ) == "deny"
    assert module.permission_effect(
        config, "papertrace-plan", "shell", "git status --short"
    ) == "deny"
    assert module.permission_effect(
        config, "papertrace-verify", "edit", "test/offline/test_library.py"
    ) == "deny"


def test_shell_requires_approval_except_narrow_offline_checks():
    """GOV-04/COST-01: no arbitrary Python; safe local checks are exact commands."""
    module = support()
    config, _ = module.load_configuration()
    assert module.permission_effect(config, "papertrace-build-A", "shell", "git status --short") == "allow"
    assert module.permission_effect(config, "papertrace-build-A", "shell", "git diff --check") == "allow"
    assert module.permission_effect(
        config, "papertrace-build-A", "shell",
        ".venv/bin/python -m pytest -c papertrace.pytest.ini test/offline",
    ) == "allow"
    assert module.permission_effect(
        config, "papertrace-build-A", "shell", "python -c print('bypass')"
    ) == "ask"
    assert module.permission_effect(
        config, "papertrace-build-A", "shell", "git push origin main"
    ) == "deny"


def test_preflight_cli_checks_an_arbitrary_checkout_without_starting_opencode(tmp_path):
    """GOV-02/04: CI can point a portable config/path gate at an untrusted checkout."""
    import shutil
    import subprocess
    import sys

    module = support()
    fixture = tmp_path / "checkout"
    for relative in (
        "opencode.jsonc", ".opencode/permissions.jsonc", ".opencode/rules.md", "AGENTS.md",
    ):
        source = ROOT / relative
        target = fixture / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    env = {"PATH": "/usr/bin:/bin", "HOME": str(tmp_path / "home")}
    Path(env["HOME"]).mkdir()
    command = [sys.executable, str(ROOT / "scripts/opencode_support.py"), "--root", str(fixture)]
    result = subprocess.run(command, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=20)
    report = json.loads(result.stdout)
    assert result.returncode == 0
    assert report["status"] == "PASS"
    assert report["scope"] == "portable static preflight"
    assert report["root"] == str(fixture.resolve())
    assert report["model_started"] is False
    assert module.unsafe_paths(fixture, report["checked_paths"]) == []

    config_path = fixture / "opencode.jsonc"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["agents"].pop("papertrace-build-A")
    config_path.write_text(json.dumps(config), encoding="utf-8")
    rejected = subprocess.run(command, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=20)
    failure = json.loads(rejected.stdout)
    assert rejected.returncode != 0
    assert failure["status"] == "FAIL"
    assert failure["model_started"] is False


def test_credential_environment_is_not_inherited(tmp_path, monkeypatch):
    """SEC-01/COST-01: only nonsecret process settings are forwarded."""
    module = support()
    monkeypatch.setenv("SYNTHETIC_PROVIDER_KEY", "not-a-real-secret")
    environment = module.safe_environment(tmp_path)
    assert "SYNTHETIC_PROVIDER_KEY" not in environment
    assert environment["HOME"] == str(tmp_path / "home")
    assert environment["OPENCODE_DISABLE_PROJECT_CONFIG"] == "1"
    assert environment["OPENCODE_CONFIG"] == str(ROOT / "opencode.jsonc")


def test_native_configuration_defaults_to_plan_with_model_use_disabled():
    """GOV-04: retained prior node; ADR-002 removes only the broken coding-provider ban.

    No automatic model is configured; product calls still need explicit consent.
    Legacy node name is kept so prior inventory cannot silently lose coverage.
    """
    test_native_configuration_is_plan_first_without_blocking_provider_selection()


def test_role_permissions_separate_course_manifest_from_engine_configuration():
    """INV-06: retained prior node, still validates both actual v2 scopes/manifest."""
    test_role_permissions_allow_owned_work_and_restrict_shared_or_sensitive_paths()


def test_rules_are_embedded_in_every_active_agent_system():
    """GOV-04: retained prior node; actual system rules include human-only/test phases."""
    test_human_only_rules_are_present_in_the_discovered_project_instructions()


def test_preflight_rejects_even_internal_symlinks(tmp_path):
    """INV-06: lexical engine paths require preflight rejection of symlink aliases."""
    module = support()
    (tmp_path / "real.txt").write_text("synthetic", encoding="utf-8")
    (tmp_path / "link.txt").symlink_to(tmp_path / "real.txt")
    assert module.unsafe_paths(tmp_path, ["real.txt"]) == []
    assert module.unsafe_paths(tmp_path, ["link.txt", "../outside.txt"])
