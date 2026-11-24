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
    assert "No module named ruff" not in result.stderr, f"TOOL_MISSING: ruff\n{result.stderr}"
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "I001" not in output, output


def test_paperqa_smoke_preserves_env_and_sys_path_setup_before_upstream_imports():
    tree = ast.parse(SMOKE_SCRIPT.read_text(encoding="utf-8"))
    upstream = {"litellm", "aviary", "lmi", "paperqa"}
    import_lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name.split(".")[0] in upstream for alias in node.names):
                import_lines.append(node.lineno)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            if node.module.split(".")[0] in upstream:
                import_lines.append(node.lineno)
        elif isinstance(node, ast.Call) and ast.unparse(node.func) == "importlib.import_module":
            module_args = node.args[:1] + [kw.value for kw in node.keywords if kw.arg == "name"]
            if any(
                isinstance(arg, ast.Constant)
                and isinstance(arg.value, str)
                and arg.value.split(".")[0] in upstream
                for arg in module_args
            ):
                import_lines.append(node.lineno)

    assert import_lines, "Expected upstream imports"
    first_import = min(import_lines)

    required_paths = {"ROOT / 'src'", "ROOT / 'packages' / 'paper-qa-pypdf' / 'src'"}
    path_lines = [
        statement.lineno
        for loop in tree.body
        if isinstance(loop, ast.For)
        and isinstance(loop.target, ast.Name)
        and isinstance(loop.iter, (ast.Tuple, ast.List))
        and required_paths <= {ast.unparse(path) for path in loop.iter.elts}
        for statement in loop.body
        if isinstance(statement, ast.Expr)
        and ast.unparse(statement.value) == f"sys.path.insert(0, str({loop.target.id}))"
    ]
    env_target = "os.environ['LITELLM_LOCAL_MODEL_COST_MAP']"
    env_lines = [
        node.lineno
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(ast.unparse(target) == env_target for target in node.targets)
        and isinstance(node.value, ast.Constant)
        and node.value.value == "True"
    ]
    env_writes = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Subscript)
        and isinstance(node.ctx, (ast.Store, ast.Del))
        and ast.unparse(node) == env_target
        and node.lineno <= first_import
    ]

    assert path_lines, "Expected sys.path setup to insert both source paths"
    assert max(path_lines) < first_import, "Expected sys.path setup before upstream imports"
    assert env_lines and min(env_lines) < first_import, "Expected bundled map before upstream imports"
    assert env_writes == [min(env_lines)], "Unexpected LiteLLM model-cost environment overwrite"
