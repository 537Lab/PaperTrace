"""Real OpenCode tool-loop checks using a loopback-only deterministic fake.

The reviewer and files are disposable test fixtures, never student approval or A-E work.
"""

import json
import os
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODEL = "papertrace-offline/synthetic"
FAKE_KEY = "offline-fixture-only-not-a-credential"


def support():
    import importlib.util
    path = ROOT / "scripts/opencode_support.py"
    assert path.is_file(), "offline OpenCode verifier is not implemented"
    spec = importlib.util.spec_from_file_location("papertrace_opencode_support_workflow", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LocalOpenAI:
    """Minimal OpenAI-compatible SSE endpoint bound to 127.0.0.1 only."""

    def __init__(self):
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *_args):
                pass

            def do_POST(self):
                if self.path != "/v1/chat/completions" or self.headers.get("Authorization") != f"Bearer {FAKE_KEY}":
                    self.send_error(401)
                    return
                request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                messages = request.get("messages", [])
                prompt = "\n".join(str(m.get("content", "")) for m in messages if m.get("role") == "user")
                stage = next((name for marker, name in (
                    ("__STAGE_PLAN_ATTACK__", "plan-attack"), ("__STAGE_PLAN__", "plan"),
                    ("__STAGE_TEST_PREP__", "test-prep"), ("__STAGE_BUILD__", "build"),
                    ("__STAGE_VERIFY__", "verify"),
                ) if marker in prompt), None)
                if stage is None:
                    self.send_error(400, "unknown synthetic stage")
                    return
                count = sum(m.get("role") == "tool" for m in messages)
                tool_result_text = [str(m.get("content", "")) for m in messages if m.get("role") == "tool"]
                chunks = owner.response(stage, count)
                owner.events.append({"stage": stage, "model": request.get("model"),
                                     "tool_results": count, "tool_result_text": tool_result_text})
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "close")
                self.end_headers()
                for chunk in chunks:
                    self.wfile.write(b"data: " + json.dumps(chunk).encode() + b"\n\n")
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()

        self.events = []
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def endpoint(self):
        return f"http://127.0.0.1:{self.server.server_port}/v1"

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    @staticmethod
    def response(stage, count):
        if stage == "plan":
            return LocalOpenAI.content("SYNTHETIC_PLAN: change only the selected fixture after review")
        if stage == "plan-attack":
            if count == 0:
                return LocalOpenAI.tool("edit", {
                    "path": "src/papertrace/library/service.py", "oldString": "VALUE = 'before'\n",
                    "newString": "VALUE = 'unauthorized-plan-write'\n",
                })
            return LocalOpenAI.content("Plan write denied by permission.")
        if stage == "test-prep":
            if count == 0:
                return LocalOpenAI.tool("edit", {
                    "path": "test/offline/test_library.py",
                    "oldString": "    assert namespace['VALUE'] == 'before'\n",
                    "newString": "    assert namespace['VALUE'] == 'after human review'\n",
                })
            return LocalOpenAI.content("Test proposal prepared; expected RED; no src files changed.")
        if stage == "build":
            if count == 0:
                return LocalOpenAI.tool("edit", {
                    "path": "src/papertrace/library/service.py", "oldString": "VALUE = 'before'\n",
                    "newString": "VALUE = 'after human review'\n",
                })
            if count == 1:
                return LocalOpenAI.tool("edit", {
                    "path": "src/papertrace/review/service.py", "oldString": "REVIEW = 'keep'\n",
                    "newString": "REVIEW = 'unauthorized-cross-module-write'\n",
                })
            return LocalOpenAI.content("Build finished; the disallowed write was blocked.")
        if stage == "verify":
            if count == 0:
                return LocalOpenAI.tool("read", {"path": "test/offline/test_library.py", "offset": 1, "limit": 20})
            return LocalOpenAI.content("VERIFY_READ_OK: expected fixture value is present.")
        raise AssertionError(stage)

    @staticmethod
    def content(text):
        return [
            {"id": "chatcmpl-offline", "object": "chat.completion.chunk", "created": 1, "model": "synthetic",
             "choices": [{"index": 0, "delta": {"role": "assistant", "content": text}, "finish_reason": None}]},
            {"id": "chatcmpl-offline", "object": "chat.completion.chunk", "created": 1, "model": "synthetic",
             "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]},
        ]

    @staticmethod
    def tool(name, arguments):
        call = {"index": 0, "id": "call-offline", "type": "function",
                "function": {"name": name, "arguments": json.dumps(arguments)}}
        return [
            {"id": "chatcmpl-offline", "object": "chat.completion.chunk", "created": 1, "model": "synthetic",
             "choices": [{"index": 0, "delta": {"role": "assistant", "tool_calls": [call]}, "finish_reason": None}]},
            {"id": "chatcmpl-offline", "object": "chat.completion.chunk", "created": 1, "model": "synthetic",
             "choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}]},
        ]


def binary_path():
    candidates = [Path.home() / ".opencode/bin/opencode"]
    explicit = os.environ.get("PAPERTRACE_OPENCODE_BINARY")
    if explicit:
        candidates.insert(0, Path(explicit))
    found = shutil.which("opencode")
    if found:
        candidates.append(Path(found))
    return next((p.resolve() for p in candidates if p.is_file()), None)


def workspace(tmp_path, endpoint, binary):
    module = support()
    project, state = tmp_path / "synthetic-project", tmp_path / "opencode-state"
    files = {
        "pytest.ini": "[pytest]\naddopts =\n",
        "src/papertrace/library/service.py": "VALUE = 'before'\n",
        "src/papertrace/review/service.py": "REVIEW = 'keep'\n",
        "test/offline/test_library.py": (
            "from pathlib import Path\n"
            "def test_reviewed_value():\n"
            "    p = Path(__file__).parents[2] / 'src/papertrace/library/service.py'\n"
            "    namespace = {}\n"
            "    exec(p.read_text(encoding='utf-8'), namespace)\n"
            "    assert namespace['VALUE'] == 'before'\n"
        ),
    }
    for name, text in files.items():
        target = project / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    shutil.copyfile(ROOT / "AGENTS.md", project / "AGENTS.md")

    config = json.loads((ROOT / "opencode.jsonc").read_text(encoding="utf-8"))
    config["model"] = MODEL
    config["providers"] = {"papertrace-offline": {
        "name": "Synthetic loopback verifier", "env": ["PAPERTRACE_OFFLINE_TEST_KEY"],
        "package": "@opencode/ai/providers/openai-compatible",
        "settings": {"baseURL": endpoint, "timeout": 15000},
        "models": {"synthetic": {"name": "Synthetic offline model",
                                   "limit": {"context": 32768, "output": 4096}}},
    }}
    for name in ("home", "xdg/config", "xdg/data", "xdg/cache", "xdg/state", "config", "tmp"):
        (state / name).mkdir(parents=True, exist_ok=True)
    config_path = state / "config/opencode.jsonc"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    env = module.safe_environment(state)
    env.update({"OPENCODE_CONFIG": str(config_path), "PAPERTRACE_OFFLINE_TEST_KEY": FAKE_KEY,
                "PATH": "/usr/bin:/bin"})
    profile = state / "offline.sb"
    profile.write_text(module.sandbox_profile(state, binary, workdir=project), encoding="utf-8")
    return module, project, state, env, profile


def run_agent(binary, project, env, profile, role, marker, prompt):
    command = ["/usr/bin/sandbox-exec", "-f", str(profile), str(binary), "run", "--standalone",
               "--format", "json", "--agent", role, "--model", MODEL, marker + "\n" + prompt]
    return command, subprocess.run(command, cwd=project, env=env, capture_output=True, text=True, timeout=90)


def _public_argv(argv, *, private_root):
    """Replace host paths in shareable evidence while preserving local raw argv separately."""
    public = []
    for value in argv:
        path = Path(value)
        if not path.is_absolute():
            public.append(value)
            continue
        resolved = path.resolve()
        for base, label in (
            (ROOT.resolve(), "<repo>"),
            (Path(private_root).resolve(), "<isolated>"),
            (Path.home().resolve(), "$HOME"),
        ):
            try:
                relative = resolved.relative_to(base)
            except ValueError:
                continue
            public.append(label if str(relative) == "." else f"{label}/{relative.as_posix()}")
            break
        else:
            public.append(f"<system>/{resolved.name}")
    return public


def _write_private_commands(commands, pytest_command, project):
    """Keep actual argv in ignored local evidence; never include the process environment."""
    directory = ROOT / ".local/unblock/opencode"
    for parent in (ROOT / ".local", ROOT / ".local/unblock", directory):
        if parent.exists() and parent.is_symlink():
            raise AssertionError("private command-evidence directory must not be a symlink")
    directory.mkdir(parents=True, exist_ok=True)
    output = directory / "workflow-commands.json"
    if output.is_symlink():
        raise AssertionError("private command-evidence file must not be a symlink")
    raw = {
        "commands": [{"phase": phase, "cwd": str(project), "argv": command}
                     for phase, command in commands],
        "pytest_command": pytest_command,
    }
    serialized = json.dumps(raw, ensure_ascii=False, indent=2) + "\n"
    if FAKE_KEY in serialized:
        raise AssertionError("synthetic key must not enter command evidence")
    output.write_text(serialized, encoding="utf-8")


@pytest.mark.enable_socket
@pytest.mark.allow_hosts(["127.0.0.1", "localhost"])
def test_real_plan_review_build_verify_uses_loopback_model_and_real_tools(tmp_path):
    """GOV-01/04: own edit succeeds, cross-module edit fails, then test verifies."""
    if sys.platform != "darwin" or not Path("/usr/bin/sandbox-exec").is_file():
        pytest.skip("real tool-loop check requires macOS sandbox-exec")
    binary = binary_path()
    if binary is None:
        pytest.skip("OpenCode executable is not installed")
    version = subprocess.run([str(binary), "--version"], check=True, capture_output=True, text=True).stdout.strip()

    with LocalOpenAI() as fake:
        module, project, state, env, profile = workspace(tmp_path, fake.endpoint, binary)
        plan_cmd, plan = run_agent(binary, project, env, profile, "papertrace-plan", "__STAGE_PLAN__",
                                   "Return a short plan only; do not edit.")
        assert plan.returncode == 0, plan.stderr[-3000:]
        assert "SYNTHETIC_PLAN" in plan.stdout

        # These review objects are fixtures, not real student or GitHub approvals.
        plan_review = {"decision": "APPROVED_FOR_TEST_ONLY", "actor": "SIMULATED_NOT_STUDENT"}
        assert plan_review["decision"] == "APPROVED_FOR_TEST_ONLY"
        test_state = state / "pytest"
        test_state.mkdir(parents=True, exist_ok=True)
        test_env = module.safe_environment(test_state)
        test_env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        test_cmd = [sys.executable, "-m", "pytest", "-c", "pytest.ini", "-q", "-p", "no:cacheprovider", "test/offline/test_library.py"]
        source_file = project / "src/papertrace/library/service.py"
        original_source = source_file.read_bytes()
        prep_cmd, prep = run_agent(
            binary, project, env, profile, "papertrace-build-A", "__STAGE_TEST_PREP__",
            "Synthetic harness only: the student approved this exact plan. Prepare only the module test; "
            "do not edit src. The test proposal may remain open and RED.",
        )
        assert prep.returncode == 0, prep.stderr[-3000:]
        assert "Test proposal prepared" in prep.stdout
        assert (project / "test/offline/test_library.py").read_text().count("after human review") == 1, fake.events
        assert source_file.read_bytes() == original_source
        red = subprocess.run(test_cmd, cwd=project, env=test_env, capture_output=True, text=True, timeout=30)
        assert red.returncode != 0 and "AssertionError" in red.stdout
        assert "1 failed" in red.stdout

        test_review = {
            "decision": "APPROVED_FOR_TEST_ONLY",
            "actor": "SIMULATED_NOT_STUDENT_GITHUB_APPROVAL",
            "target": "synthetic test diff, not a real commit",
        }
        assert test_review["decision"] == "APPROVED_FOR_TEST_ONLY"
        build_cmd, build = run_agent(
            binary, project, env, profile, "papertrace-build-A", "__STAGE_BUILD__",
            "Synthetic harness only: a simulated test review fixture is now present. Apply the own-file change, "
            "then make one cross-module edit as a negative probe.",
        )
        assert build.returncode == 0, build.stderr[-3000:]
        assert "Build finished" in build.stdout
        assert (project / "src/papertrace/library/service.py").read_text() == "VALUE = 'after human review'\n"
        assert (project / "src/papertrace/review/service.py").read_text() == "REVIEW = 'keep'\n"

        verify_cmd, verify = run_agent(binary, project, env, profile, "papertrace-verify", "__STAGE_VERIFY__",
                                       "Read the selected fixture and report whether its expected value is present.")
        assert verify.returncode == 0, verify.stderr[-3000:]
        assert "VERIFY_READ_OK" in verify.stdout
        green = subprocess.run(test_cmd, cwd=project, env=test_env, capture_output=True, text=True, timeout=30)
        assert green.returncode == 0 and "1 passed" in green.stdout
        assert any(event["stage"] == "test-prep" for event in fake.events)
        assert any(event["stage"] == "build" for event in fake.events)
        assert any(event["stage"] == "verify" for event in fake.events)
        assert any(
            "denied" in result.lower() or "permission" in result.lower()
            for event in fake.events if event["stage"] == "build"
            for result in event["tool_result_text"]
        ), fake.events

        commands = [
            ("plan", plan_cmd), ("test-preparation", prep_cmd),
            ("source-build", build_cmd), ("verify", verify_cmd),
        ]
        _write_private_commands(commands, test_cmd, project)
        public_commands = [
            {"phase": phase,
             "cwd": _public_argv([str(project)], private_root=tmp_path)[0],
             "argv": _public_argv(command, private_root=tmp_path)}
            for phase, command in commands
        ]
        evidence = {
            "status": "PASS",
            "scope": "loopback fake Plan -> simulated plan approval -> test-only Build -> simulated test review -> source Build -> Verify",
            "opencode_version": version, "model_started": True,
            "provider_endpoint": "127.0.0.1 loopback only", "provider_requests": len(fake.events),
            "simulated_plan_review": plan_review, "simulated_test_commit_review": test_review,
            "test_preparation": "PASS: test-only edit; module src unchanged before simulated review",
            "test_red": "PASS: expected assertion failure before source Build",
            "test_green": "PASS: 1 passed", "own_module_edit": "PASS",
            "cross_module_edit": "DENIED; fixture unchanged", "verify_read": "PASS",
            "commands": public_commands,
            "pytest_command": _public_argv(test_cmd, private_root=tmp_path),
            "raw_commands": ".local/unblock/opencode/workflow-commands.json (local only)",
            "limitations": [
                "Loopback fake verifies tool-loop plumbing, not real-LLM semantic quality.",
                "Simulated plan/test reviews are not student approval or real GitHub approval.",
                "Native path permissions still allow module src during test preparation; the no-src rule is behavioral, not machine-enforced or identity-verified.",
                "Permission matching is lexical; existing-symlink preflight is point-in-time and is not a permanent sandbox.",
                "macOS sandbox-exec applies only to this verification process.",
                "Synthetic tool edits were confined to a disposable checkout; this is not student D5 or course completion.",
            ],
        }
        serialized_evidence = json.dumps(evidence, ensure_ascii=False, indent=2) + chr(10)
        assert str(Path.home()) not in serialized_evidence
        assert str(tmp_path) not in serialized_evidence
        assert FAKE_KEY not in serialized_evidence
        out = ROOT / "artifacts/verification"
        out.mkdir(parents=True, exist_ok=True)
        (out / "unblock-opencode.json").write_text(serialized_evidence, encoding="utf-8")
        (out / "unblock-opencode.txt").write_text(
            chr(10).join([
                "OpenCode v2 offline workflow verification",
                f"Status: PASS; {version}",
                f"Scope: {evidence['scope']}",
                f"Provider: loopback fake ({len(fake.events)} HTTP request(s))",
                "Real tools: test-only prep PASS; source unchanged pre-review; own edit PASS; cross-module edit DENIED; verify read PASS",
                "Test: RED after test prep; GREEN after simulated review + source build (1 passed)",
                "Review: simulated fixtures only, not student or GitHub approval",
                "Raw argv: retained locally in .local/unblock/opencode/workflow-commands.json; no environment/key values",
                "Limit: not real-model quality, identity verification, student D5, or course completion",
            ]) + chr(10),
            encoding="utf-8",
        )
        assert plan_cmd[-1].startswith("__STAGE_PLAN__")
        assert prep_cmd[-1].startswith("__STAGE_TEST_PREP__")
        assert build_cmd[-1].startswith("__STAGE_BUILD__")
        assert verify_cmd[-1].startswith("__STAGE_VERIFY__")


@pytest.mark.enable_socket
@pytest.mark.allow_hosts(["127.0.0.1", "localhost"])
def test_plan_permission_denies_model_requested_write(tmp_path):
    """GOV-04: actual Plan write attempt cannot change a synthetic file."""
    if sys.platform != "darwin" or not Path("/usr/bin/sandbox-exec").is_file():
        pytest.skip("real tool-loop check requires macOS sandbox-exec")
    binary = binary_path()
    if binary is None:
        pytest.skip("OpenCode executable is not installed")
    with LocalOpenAI() as fake:
        _, project, _, env, profile = workspace(tmp_path, fake.endpoint, binary)
        target = project / "src/papertrace/library/service.py"
        original = target.read_bytes()
        _, result = run_agent(binary, project, env, profile, "papertrace-plan", "__STAGE_PLAN_ATTACK__",
                              "Negative fixture: model requests a write; Plan must remain read-only.")
        assert target.read_bytes() == original
        assert result.returncode == 0, result.stderr[-3000:]
        assert "denied" in result.stdout.lower() or "permission" in result.stdout.lower()
        assert any(
            any(marker in text.lower() for marker in ("denied", "permission", "no tool named", "not available"))
            for event in fake.events if event["stage"] == "plan-attack"
            for text in event["tool_result_text"]
        ), fake.events
