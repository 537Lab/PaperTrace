"""OpenCode initialization configuration tests; ADR-001, INV-06, GOV-01/04."""

import json
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def support():
    """INV-06: fail explicitly if the safe launcher support is absent."""
    path = ROOT / "scripts" / "opencode_support.py"
    assert path.is_file(), "safe OpenCode support is not implemented"
    spec = spec_from_file_location("papertrace_opencode_support", path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_native_configuration_defaults_to_plan_with_model_use_disabled():
    """GOV-01/04: configuration is native v2, offline and not unattended Build."""
    path = ROOT / "opencode.jsonc"
    assert path.is_file(), "native OpenCode configuration is not created"
    config = json.loads(path.read_text(encoding="utf-8"))
    assert config["default_agent"] == "papertrace-plan"
    assert config["experimental"]["policies"] == [
        {"action": "provider.use", "resource": "*", "effect": "deny"}
    ]
    assert "permission" not in config and "instructions" not in config
    assert config["formatter"] is False and config["lsp"] is False
    assert config["plugins"] == [] and config["mcp"]["servers"] == {}


def test_rules_are_embedded_in_every_active_agent_system():
    """GOV-04: v2.0.12 instructions[] is inert; actual agent.system carries rules."""
    path = ROOT / ".opencode" / "rules.md"
    assert path.is_file(), "human-only rule proposal is not created"
    rules = path.read_text(encoding="utf-8")
    config = json.loads((ROOT / "opencode.jsonc").read_text(encoding="utf-8"))
    for name, agent in config["agents"].items():
        if not agent.get("disabled"):
            assert rules in agent["system"], name


def test_role_permissions_separate_course_manifest_from_engine_configuration():
    """INV-06: explicit read/write lists; plan is read only; module scopes are disjoint."""
    module = support()
    config, manifest = module.load_configuration()
    assert manifest["engine_configuration"] == "opencode.jsonc"
    assert manifest["not_auto_loaded_by_opencode"] is True
    assert set(manifest["roles"]) == set(config["agents"]) - {"build", "plan", "general"}
    assert manifest["roles"]["papertrace-plan"]["write_candidates"] == []
    for letter, directory in zip("ABCDE", ["library", "retrieval", "review", "answer", "reports"], strict=True):
        role = manifest["roles"][f"papertrace-build-{letter}"]
        assert f"src/papertrace/{directory}/service.py" in role["write_candidates"]
        assert "src/papertrace/contracts.py" not in role["write_candidates"]
        assert "src/paperqa/docs.py" not in role["write_candidates"]


def test_credential_environment_is_not_inherited(tmp_path, monkeypatch):
    """SEC-01/COST-01: only nonsecret process settings are forwarded."""
    module = support()
    monkeypatch.setenv("SYNTHETIC_PROVIDER_KEY", "not-a-real-secret")
    environment = module.safe_environment(tmp_path)
    assert "SYNTHETIC_PROVIDER_KEY" not in environment
    assert environment["HOME"] == str(tmp_path / "home")
    assert environment["OPENCODE_DISABLE_PROJECT_CONFIG"] == "1"
    assert environment["OPENCODE_CONFIG"] == str(ROOT / "opencode.jsonc")


def test_preflight_rejects_even_internal_symlinks(tmp_path):
    """INV-06: installed engine has lexical paths, so the launcher refuses symlinks."""
    module = support()
    (tmp_path / "real.txt").write_text("synthetic", encoding="utf-8")
    (tmp_path / "link.txt").symlink_to(tmp_path / "real.txt")
    assert module.unsafe_paths(tmp_path, ["real.txt"]) == []
    assert module.unsafe_paths(tmp_path, ["link.txt", "../outside.txt"])
