import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SMOKE_SCRIPT = ROOT / "scripts" / "paperqa_smoke.py"


def test_paperqa_smoke_passes_configured_ruff_lint():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "--config",
            str(ROOT / "papertrace.ruff.toml"),
            str(SMOKE_SCRIPT),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "I001" not in output, output


def test_paperqa_smoke_preserves_env_and_sys_path_setup_before_upstream_imports():
    tree = ast.parse(SMOKE_SCRIPT.read_text(encoding="utf-8"))
    upstream = {"aviary", "lmi", "paperqa"}
    import_lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name.split(".")[0] in upstream for alias in node.names):
                import_lines.append(node.lineno)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            if node.module.split(".")[0] in upstream:
                import_lines.append(node.lineno)

    path_lines = [
        statement.lineno
        for loop in tree.body
        if isinstance(loop, ast.For)
        for statement in loop.body
        if isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Call)
        and ast.unparse(statement.value.func) == "sys.path.insert"
    ]
    env_lines = [
        node.lineno
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            ast.unparse(target) == "os.environ['LITELLM_LOCAL_MODEL_COST_MAP']"
            for target in node.targets
        )
        and isinstance(node.value, ast.Constant)
        and node.value.value == "True"
    ]

    assert import_lines, "Expected upstream imports"
    assert path_lines, "Expected sys.path setup"
    assert env_lines, "Expected the bundled LiteLLM model-cost map setup"
    assert max(path_lines + env_lines) < min(import_lines)
