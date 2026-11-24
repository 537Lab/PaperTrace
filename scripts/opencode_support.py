"""Portable OpenCode v2.0.12 preflight and isolated no-model runtime probes.

Static preflight validates a supplied checkout without launching OpenCode. The
runtime API probe exercises permission evaluation only, not agent tool execution.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import signal
import subprocess
import sys
import uuid
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ROLES = {
    "papertrace-plan", "papertrace-verify", "papertrace-build-A", "papertrace-build-B",
    "papertrace-build-C", "papertrace-build-D", "papertrace-build-E",
}
MODULES = {"A": "library", "B": "retrieval", "C": "review", "D": "answer", "E": "reports"}
SENSITIVE_RESOURCES = (
    ".env", ".env.local", ".local/unblock/opencode/key.json", ".git/config",
    ".venv/pyvenv.cfg", "src/papertrace/library/.env", "src/papertrace/library/token.pem",
)


def load_configuration(root: Path | str = ROOT):
    """Load the active native configuration and the explicitly separate manifest."""
    root = Path(root).resolve()
    config = json.loads((root / "opencode.jsonc").read_text(encoding="utf-8"))
    manifest = json.loads((root / ".opencode/permissions.jsonc").read_text(encoding="utf-8"))
    return config, manifest


def _matches(value: str, pattern: str) -> bool:
    """Match v2's whole-resource wildcards, including shell's trailing ` *` rule."""
    value = value.replace("\\", "/")
    pattern = pattern.replace("\\", "/")
    if pattern.endswith(" *"):
        prefix = pattern[:-2]
        return value == prefix or value.startswith(prefix + " ")
    return fnmatch.fnmatchcase(value, pattern)


def permission_effect(config: dict, role: str, action: str, resource: str) -> str:
    """Evaluate ordered native v2 rules using config rules followed by agent rules."""
    rules = list(config.get("permissions", []))
    rules.extend(config.get("agents", {}).get(role, {}).get("permissions", []))
    effect = "ask"
    for rule in rules:
        if _matches(action, rule["action"]) and _matches(resource, rule["resource"]):
            effect = rule["effect"]
    return effect


def unsafe_paths(root: Path | str, paths) -> list[str]:
    """Reject traversal, absolute paths, and existing symlinks in exact/glob paths."""
    input_root = Path(root)
    if input_root.is_symlink():
        return ["<root-is-symlink>"]
    root = input_root.resolve()
    unsafe = []
    for name in paths:
        if not isinstance(name, str) or not name or "\\" in name:
            unsafe.append(str(name))
            continue
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts:
            unsafe.append(name)
            continue
        current = root
        invalid = False
        for part in path.parts:
            if "*" in part or "?" in part:
                break
            current = current / part
            if current.is_symlink() or not current.resolve().is_relative_to(root):
                invalid = True
                break
        if invalid:
            unsafe.append(name)
    return sorted(set(unsafe))


def safe_environment(state: Path | str, *, root: Path | str = ROOT, config_path: Path | str | None = None):
    """Build an allowlisted environment; never forward auth, proxy, or user config state."""
    state = Path(state).resolve()
    root = Path(root).resolve()
    return {
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
        "HOME": str(state / "home"),
        "OPENCODE_TEST_HOME": str(state / "home"),
        "XDG_CONFIG_HOME": str(state / "xdg/config"),
        "XDG_DATA_HOME": str(state / "xdg/data"),
        "XDG_CACHE_HOME": str(state / "xdg/cache"),
        "XDG_STATE_HOME": str(state / "xdg/state"),
        "OPENCODE_CONFIG_DIR": str(state / "config"),
        "TMPDIR": str(state / "tmp"),
        "OPENCODE_CONFIG": str(Path(config_path).resolve() if config_path else root / "opencode.jsonc"),
        "OPENCODE_DISABLE_PROJECT_CONFIG": "1",
        "OPENCODE_DISABLE_MODELS_FETCH": "1",
        "OPENCODE_DISABLE_FILEWATCHER": "1",
        "OPENCODE_DISABLE_FFF": "1",
    }


def sandbox_profile(state: Path | str, binary: Path | str, *, root: Path | str = ROOT,
                    workdir: Path | str | None = None) -> str:
    """Restrict the verifier to loopback and explicit scratch/config/project paths."""
    state = Path(state).resolve()
    root = Path(root).resolve()
    binary = Path(binary).resolve()
    quote = json.dumps
    allow_read = [f"(subpath {quote(str(root))})", f"(subpath {quote(str(state))})",
                  f"(literal {quote(str(binary))})"]
    allow_write = [f"(subpath {quote(str(state))})", '(literal "/dev/null")']
    if workdir is not None:
        workdir = Path(workdir).resolve()
        allow_read.append(f"(subpath {quote(str(workdir))})")
        allow_write.append(f"(subpath {quote(str(workdir))})")
    local_exclusions = [root / ".local", root / ".git", root / ".venv"]
    deny_private = "".join(f"(deny file-read* (subpath {quote(str(path))}))" for path in local_exclusions)
    allow_exceptions = "".join(f"(allow file-read* (subpath {quote(str(path))}))" for path in [state, *([workdir] if workdir else [])])
    return (
        "(version 1)(allow default)(deny network*)"
        '(allow network-inbound (local ip "localhost:*"))'
        '(allow network-outbound (remote ip "localhost:*"))'
        "(deny file-write*)"
        f"(allow file-write* {' '.join(allow_write)})"
        f'(deny file-read* (subpath {quote(str(Path.home().resolve()))}))'
        f"(allow file-read* {' '.join(allow_read)})"
        f"{deny_private}{allow_exceptions}"
    )


def _preflight_error(report: dict, message: str):
    report["errors"].append(message)


def preflight(root: Path | str = ROOT) -> dict:
    """Portable static safety check for a checkout; never starts OpenCode or a model."""
    input_root = Path(root)
    report = {
        "status": "PASS", "scope": "portable static preflight", "model_started": False,
        "root": str(input_root.resolve()), "checked_paths": [], "errors": [],
    }
    if input_root.is_symlink() or not input_root.is_dir():
        _preflight_error(report, "root must be an existing non-symlink directory")
        report["status"] = "FAIL"
        return report
    try:
        config, manifest = load_configuration(input_root)
        rules_path = input_root / ".opencode/rules.md"
        agents_path = input_root / "AGENTS.md"
        rules = rules_path.read_text(encoding="utf-8").strip()
        agents_text = agents_path.read_text(encoding="utf-8")
    except (OSError, json.JSONDecodeError, TypeError) as error:
        _preflight_error(report, f"required configuration/rules cannot be loaded ({type(error).__name__})")
        report["status"] = "FAIL"
        return report

    expected = {"$schema": "https://opencode.ai/config.json"}
    if config.get("$schema") != expected["$schema"]:
        _preflight_error(report, "native v2 JSON schema reference is missing")
    if config.get("default_agent") != "papertrace-plan":
        _preflight_error(report, "default_agent must be papertrace-plan")
    if config.get("model") or config.get("providers"):
        _preflight_error(report, "repository must not select a model or configure a provider")
    if "policies" in config or "experimental" in config:
        _preflight_error(report, "legacy/global policy fields are not accepted")
    if any(rule.get("action") == "provider.use" for rule in config.get("permissions", [])):
        _preflight_error(report, "provider.use permission is a global coding-model blocker")
    if not config.get("permissions") or config["permissions"][0] != {
        "action": "*", "resource": "*", "effect": "deny"
    }:
        _preflight_error(report, "first native permission rule must be catch-all deny")
    if permission_effect(config, "papertrace-build-A", "shell", "unlisted command") != "ask":
        _preflight_error(report, "unlisted shell commands must ask")
    if permission_effect(config, "papertrace-build-A", "shell", "git push origin main") != "deny":
        _preflight_error(report, "git push must be denied")
    if permission_effect(config, "papertrace-build-A", "shell", "python -c print('x')") != "ask":
        _preflight_error(report, "arbitrary Python shell commands must ask")

    if manifest.get("engine_configuration") != "opencode.jsonc" or manifest.get("not_auto_loaded_by_opencode") is not True:
        _preflight_error(report, "permissions manifest must name the engine config and remain explicitly non-native")
    if manifest.get("status") != "initialization-proposal-awaiting-human-review":
        _preflight_error(report, "human governance proposal status must remain pending")
    if set(config.get("agents", {})) != EXPECTED_ROLES or set(manifest.get("roles", {})) != EXPECTED_ROLES:
        _preflight_error(report, "native agents and permission manifest roles differ from the approved A-E workflow")
    governance_markers = ("student", "non-implementer", "credentials", "approval")
    if not rules.strip():
        _preflight_error(report, "human-only proposal rules are empty")
    for marker in governance_markers:
        if marker not in rules or marker not in agents_text:
            _preflight_error(report, f"human-only rule source and discovered AGENTS.md are not synchronized: {marker}")

    checked = list(manifest.get("read_common", []))
    for role_name, role in manifest.get("roles", {}).items():
        checked.extend(role.get("read_additions", []))
        checked.extend(role.get("write_candidates", []))
        if role_name not in config.get("agents", {}):
            continue
        for path in role.get("read_additions", []):
            if permission_effect(config, role_name, "read", path) == "deny":
                _preflight_error(report, f"manifest read addition denied for {role_name}: {path}")
        candidates = role.get("write_candidates", [])
        if role_name in ("papertrace-plan", "papertrace-verify") and candidates:
            _preflight_error(report, f"read-only role has write candidates: {role_name}")
        if role_name.startswith("papertrace-build-"):
            for path in candidates:
                if permission_effect(config, role_name, "edit", path) != "allow":
                    _preflight_error(report, f"owned write candidate is not allowed: {role_name}/{path}")
    checked.extend(manifest.get("protected_paths", []))
    checked.extend(SENSITIVE_RESOURCES)
    unsafe = unsafe_paths(input_root, checked)
    if unsafe:
        _preflight_error(report, "manifest contains traversal or symlinked paths")
    report["checked_paths"] = sorted(set(checked))

    for path in manifest.get("read_common", []):
        if permission_effect(config, "papertrace-plan", "read", path) != "allow":
            _preflight_error(report, f"common read path is not allowed to Plan: {path}")
    for role_name in EXPECTED_ROLES:
        for path in manifest.get("protected_paths", []):
            if permission_effect(config, role_name, "edit", path) != "deny":
                _preflight_error(report, f"protected write is not denied for {role_name}: {path}")
        for resource in SENSITIVE_RESOURCES:
            for action in ("read", "edit"):
                if permission_effect(config, role_name, action, resource) != "deny":
                    _preflight_error(report, f"sensitive path is not denied: {role_name}/{action}/{resource}")
    for command in manifest.get("safe_shell_allowlist", []):
        for role_name in EXPECTED_ROLES - {"papertrace-plan"}:
            if permission_effect(config, role_name, "shell", command) != "allow":
                _preflight_error(report, f"approved offline shell check is not allowed: {role_name}/{command}")
    if permission_effect(config, "papertrace-plan", "edit", "src/papertrace/library/service.py") != "deny":
        _preflight_error(report, "Plan must remain read-only")
    if permission_effect(config, "papertrace-verify", "edit", "test/offline/test_library.py") != "deny":
        _preflight_error(report, "Verify must remain read-only")

    if report["errors"]:
        report["status"] = "FAIL"
    return report


def run_api(binary: Path, state: Path, method: str, path: str, payload=None, *, root: Path = ROOT):
    """Run one bounded native API request in a private process group and loopback sandbox."""
    command = ["/usr/bin/sandbox-exec", "-f", str(state / "offline.sb"), str(binary),
               "api", "--standalone", method, path]
    if payload is not None:
        command += ["--data", json.dumps(payload)]
    process = subprocess.Popen(command, cwd=root, env=safe_environment(state, root=root),
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                               start_new_session=True)
    try:
        stdout, _stderr = process.communicate(timeout=50)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
        raise RuntimeError("OpenCode isolated API timeout; task process group stopped") from None
    if process.returncode:
        raise RuntimeError(f"OpenCode isolated API failed: return code {process.returncode}")
    return json.loads(stdout)


def verify_runtime(binary: Path | str, root: Path | str = ROOT, state: Path | str | None = None) -> dict:
    """Read back config and probe the real no-model permission engine; no tools are invoked."""
    root, binary = Path(root).resolve(), Path(binary).resolve()
    if sys.platform != "darwin" or not Path("/usr/bin/sandbox-exec").is_file():
        raise RuntimeError("runtime probe requires macOS sandbox-exec; portable preflight remains available")
    config, manifest = load_configuration(root)
    paths = list(manifest["read_common"])
    for role in manifest["roles"].values():
        paths.extend(role.get("read_additions", []))
        paths.extend(role.get("write_candidates", []))
    if unsafe_paths(root, paths):
        raise RuntimeError("permission manifest contains symlink or escaping path")
    if state is None:
        state = root / ".local/unblock/opencode" / ("runtime-" + uuid.uuid4().hex)
    state = Path(state).resolve()
    for name in ("home", "xdg/config", "xdg/data", "xdg/cache", "xdg/state", "config", "tmp"):
        (state / name).mkdir(parents=True, exist_ok=True)
    profile = state / "offline.sb"
    profile.write_text(sandbox_profile(state, binary, root=root), encoding="utf-8")

    entries = run_api(binary, state, "GET", "/api/config", root=root)
    documents = [item["info"] for item in entries if item.get("type") == "document"]
    matching = [item for item in documents if item.get("default_agent") == "papertrace-plan"]
    if len(matching) != 1:
        raise RuntimeError("actual native configuration was not loaded exactly once")
    loaded = matching[0]
    if loaded.get("permissions") != config.get("permissions"):
        raise RuntimeError("effective native permission rules differ from checked file")
    for name, agent in config["agents"].items():
        if loaded.get("agents", {}).get(name) != agent:
            raise RuntimeError("effective agent definition differs from checked file")

    cases = [
        ("papertrace-plan", "read", "docs/req/requirements.yaml", "allow"),
        ("papertrace-plan", "edit", "src/papertrace/library/service.py", "deny"),
        ("papertrace-plan", "shell", "git status --short", "deny"),
        ("papertrace-build-A", "edit", "src/papertrace/library/service.py", "allow"),
        ("papertrace-build-A", "edit", "src/papertrace/review/service.py", "deny"),
        ("papertrace-build-A", "edit", "src/papertrace/contracts.py", "deny"),
        ("papertrace-build-B", "read", "src/paperqa/docs.py", "allow"),
        ("papertrace-build-B", "edit", "src/paperqa/docs.py", "deny"),
        ("papertrace-build-B", "read", "packages/paper-qa-pypdf/src/paperqa_pypdf/reader.py", "ask"),
        ("papertrace-build-A", "edit", ".opencode/rules.md", "deny"),
        ("papertrace-build-A", "read", ".env", "deny"),
        ("papertrace-build-A", "read", "../synthetic-private.txt", "deny"),
        ("papertrace-build-A", "external_directory", "/synthetic-private/*", "deny"),
        ("papertrace-build-A", "shell", "git status --short", "allow"),
        ("papertrace-build-A", "shell", "python -c synthetic-no-op", "ask"),
        ("papertrace-build-A", "shell", "git push origin main", "deny"),
    ]
    sessions, observations = {}, []
    for role, action, resource, expected in cases:
        if role not in sessions:
            created = run_api(binary, state, "POST", "/api/session", {
                "title": "PaperTrace no-model permission engine probe", "agent": role,
                "location": {"directory": str(root)},
                "permissions": config["permissions"] + config["agents"][role].get("permissions", []),
            }, root=root)
            sessions[role] = created["data"]["id"]
        response = run_api(binary, state, "POST", f"/api/session/{sessions[role]}/permission", {
            "action": action, "resources": [resource], "agent": role, "save": [],
        }, root=root)
        actual = response["data"]["effect"]
        if actual != expected:
            raise RuntimeError(f"permission effect mismatch for {role}/{action}/{resource}")
        observations.append({"role": role, "action": action, "resource": resource,
                            "expected": expected, "actual": actual})
    for session_id in sessions.values():
        session = run_api(binary, state, "GET", f"/api/session/{session_id}", root=root)["data"]
        messages = run_api(binary, state, "GET", f"/api/session/{session_id}/message", root=root)["data"]
        if messages or session["cost"] != 0:
            raise RuntimeError("no-model permission session unexpectedly contains model activity")
    return {
        "status": "PASS", "version": "2.0.12", "configuration_readback": "PASS",
        "permission_engine_tests": observations, "passed": len(observations),
        "sessions_with_no_messages": len(sessions), "model_started": False,
        "limits": ["permission API probes exercise the engine, not read/edit/shell tools",
                   "no provider requests; no claim of full upstream tool suite",
                   "sandbox applies to this verifier process only"],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT,
                        help="checkout whose config, manifest, safety paths and rules to validate")
    parser.add_argument("--verify-runtime", action="store_true",
                        help="also read back v2.0.12 config and probe its permission engine without a model")
    parser.add_argument("--binary", default=str(Path.home() / ".opencode/bin/opencode"),
                        help="explicit OpenCode v2.0.12 executable for --verify-runtime")
    args = parser.parse_args(argv)
    report = preflight(args.root)
    if report["status"] != "PASS":
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1
    if args.verify_runtime:
        if not args.binary or not Path(args.binary).is_file():
            report.update(status="FAIL", errors=["OpenCode executable not found; portable preflight passed"])
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1
        try:
            report["runtime"] = verify_runtime(args.binary, args.root)
        except (OSError, RuntimeError, KeyError, ValueError) as error:
            report.update(status="FAIL", runtime_error=f"{type(error).__name__}: {error}")
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
