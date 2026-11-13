"""OpenCode v2.0.12 offline configuration verifier; ADR-001, INV-06, GOV-01/04.

Never invokes a model. Permission API probes exercise the engine, not tools.
The macOS sandbox is limited to this short verification process, not a promise
that unwrapped OpenCode launches are isolated.
"""

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_configuration():
    """GOV-04: the actual engine entry and course manifest are separate objects."""
    config = json.loads((ROOT / "opencode.jsonc").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / ".opencode/permissions.jsonc").read_text(encoding="utf-8"))
    return config, manifest


def unsafe_paths(root, paths):
    """INV-06: reject traversal and all symlinks, including in-location aliases."""
    root = Path(root).resolve()
    unsafe = []
    for name in paths:
        path = Path(name)
        if path.is_absolute() or ".." in path.parts or "\\" in name:
            unsafe.append(name)
            continue
        target = root / path
        if not target.resolve().is_relative_to(root):
            unsafe.append(name)
            continue
        if any(item.is_symlink() for item in [target, *target.parents] if item != root):
            unsafe.append(name)
    return unsafe


def safe_environment(state):
    """COST-01/SEC-01: do not forward credentials or read global user state."""
    state = Path(state).resolve()
    return {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(state / "home"),
        "OPENCODE_TEST_HOME": str(state / "home"),
        "XDG_CONFIG_HOME": str(state / "xdg/config"),
        "XDG_DATA_HOME": str(state / "xdg/data"),
        "XDG_CACHE_HOME": str(state / "xdg/cache"),
        "XDG_STATE_HOME": str(state / "xdg/state"),
        "OPENCODE_CONFIG_DIR": str(state / "config"),
        "TMPDIR": str(state / "tmp"),
        "OPENCODE_CONFIG": str(ROOT / "opencode.jsonc"),
        "OPENCODE_DISABLE_PROJECT_CONFIG": "1",
        "OPENCODE_DISABLE_MODELS_FETCH": "1",
        "OPENCODE_DISABLE_FILEWATCHER": "1",
        "OPENCODE_DISABLE_FFF": "1",
    }


def sandbox_profile(state, binary):
    """INV-06: verification-only writes and loopback; exclude other home paths."""
    quote = json.dumps
    return (
        "(version 1)(allow default)(deny network*)"
        '(allow network-inbound (local ip "localhost:*"))'
        '(allow network-outbound (remote ip "localhost:*"))'
        "(deny file-write*)"
        f'(allow file-write* (subpath {quote(str(state))}) (literal "/dev/null"))'
        f"(deny file-read* (subpath {quote(str(Path.home()))}))"
        f"(allow file-read* (subpath {quote(str(ROOT))}) "
        f"(literal {quote(str(binary))}) (literal {quote(str(Path.home()))}))"
    )


def run_api(binary, state, method, path, payload=None):
    """GOV-04: run one bounded standalone API request, with no provider operation."""
    command = ["/usr/bin/sandbox-exec", "-f", str(state / "offline.sb"), str(binary),
               "api", "--standalone", method, path]
    if payload is not None:
        command += ["--data", json.dumps(payload)]
    process = subprocess.Popen(command, cwd=ROOT, env=safe_environment(state),
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, start_new_session=True)
    try:
        stdout, _stderr = process.communicate(timeout=50)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
        raise RuntimeError("OpenCode isolated API timeout; owned group stopped") from None
    if process.returncode:
        raise RuntimeError(f"OpenCode isolated API failed: return code {process.returncode}")
    return json.loads(stdout)


def verify(binary, state):
    """INV-06/GOV-04: native config readback and real engine allow/ask/deny probes."""
    if sys.platform != "darwin":
        raise RuntimeError("This runtime probe requires macOS sandbox-exec; configuration tests are portable")
    config, manifest = load_configuration()
    all_paths = list(manifest["read_common"])
    for role in manifest["roles"].values():
        all_paths += role["read_additions"] + role["write_candidates"]
    if unsafe_paths(ROOT, all_paths):
        raise RuntimeError("Permission whitelist contains a symlink or escaping path")
    for value in safe_environment(state).values():
        if value.startswith(str(state)):
            Path(value).mkdir(parents=True, exist_ok=True)
    state.mkdir(parents=True, exist_ok=True)
    (state / "offline.sb").write_text(sandbox_profile(state, binary), encoding="utf-8")
    entries = run_api(binary, state, "GET", "/api/config")
    documents = [item["info"] for item in entries if item.get("type") == "document"]
    matching = [item for item in documents if item.get("default_agent") == "papertrace-plan"]
    if len(matching) != 1:
        raise RuntimeError("Actual project configuration was not read exactly once")
    loaded = matching[0]
    if loaded["permissions"] != config["permissions"]:
        raise RuntimeError("Effective configuration permissions differ")
    rules = (ROOT / ".opencode/rules.md").read_text(encoding="utf-8")
    for name in manifest["roles"]:
        if rules not in loaded["agents"][name]["system"]:
            raise RuntimeError("Effective agent rules mirror differs")
    cases = [
        ("papertrace-plan", "read", "docs/req/requirements.yaml", "allow"),
        ("papertrace-plan", "edit", "src/papertrace/library/service.py", "deny"),
        ("papertrace-build-A", "edit", "src/papertrace/library/service.py", "ask"),
        ("papertrace-build-A", "edit", "src/papertrace/review/service.py", "deny"),
        ("papertrace-build-B", "read", "src/paperqa/docs.py", "allow"),
        ("papertrace-build-B", "edit", "src/paperqa/docs.py", "deny"),
        ("papertrace-build-D", "edit", "src/papertrace/contracts.py", "deny"),
        ("papertrace-build-A", "edit", ".opencode/rules.md", "deny"),
        ("papertrace-plan", "read", ".env", "deny"),
        ("papertrace-plan", "read", "../synthetic-private.txt", "deny"),
        ("papertrace-plan", "external_directory", "/synthetic-private/*", "deny"),
        ("papertrace-build-A", "shell", "git push", "deny"),
        ("papertrace-build-A", "shell", "python -c synthetic-no-op", "deny"),
    ]
    sessions = {}
    observations = []
    for role, action, resource, expected in cases:
        if role not in sessions:
            permissions = config["permissions"] + config["agents"][role]["permissions"]
            created = run_api(binary, state, "POST", "/api/session", {
                "title": "PaperTrace no-model permission-engine verification",
                "agent": role, "location": {"directory": str(ROOT)}, "permissions": permissions,
            })
            sessions[role] = created["data"]["id"]
        response = run_api(binary, state, "POST", f"/api/session/{sessions[role]}/permission", {
            "action": action, "resources": [resource], "agent": role, "save": [],
        })
        observed = response["data"]["effect"]
        if observed != expected:
            raise RuntimeError(f"Permission effect mismatch for {role}/{action}")
        observations.append({"role": role, "action": action, "resource": resource,
                             "expected": expected, "actual": observed})
    for session_id in sessions.values():
        session = run_api(binary, state, "GET", f"/api/session/{session_id}")["data"]
        messages = run_api(binary, state, "GET", f"/api/session/{session_id}/message")["data"]
        if messages or session["cost"] != 0:
            raise RuntimeError("Verification session unexpectedly contains model activity")
    return {"version": "2.0.12", "configuration_readback": "PASS",
            "native_system_rules_mirror": "PASS", "permission_engine_tests": observations,
            "passed": len(observations), "sessions_with_no_messages": len(sessions),
            "limits": ["Permission API engine probes, not model-driven tool execution",
                       "No provider requests; no claim of full official Bun tool suites",
                       "Sandbox applies to this verifier only; unwrapped launches are not isolated"]}


def main():
    """GOV-04: local checks only; no command enables provider use or runs an agent."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-runtime", action="store_true")
    parser.add_argument("--binary", default=shutil.which("opencode"))
    args = parser.parse_args()
    if args.verify_runtime:
        if not args.binary:
            parser.error("OpenCode binary not found")
        output = verify(Path(args.binary).resolve(), ROOT / ".local/opencode-verification")
        destination = ROOT / "artifacts/verification/opencode-runtime.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        config, manifest = load_configuration()
        paths = manifest["read_common"] + [p for role in manifest["roles"].values()
                                           for p in role["read_additions"] + role["write_candidates"]]
        if unsafe_paths(ROOT, paths):
            parser.error("Unsafe whitelist path")
        print(json.dumps({"status": "PASS", "scope": "static preflight only",
                          "default_agent": config["default_agent"],
                          "provider_use": "denied; activation requires student approval"}))


if __name__ == "__main__":
    main()
