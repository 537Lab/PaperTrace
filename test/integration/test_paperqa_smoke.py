from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SMOKE = ROOT / "scripts" / "paperqa_smoke.py"
RUNTIME = ROOT / ".local" / "unblock" / "runtime"


def test_offline_paperqa_smoke_proves_positive_and_empty_cases() -> None:
    """Exercise the fixed upstream Docs path without credentials or networking."""
    home = RUNTIME / "home"
    temp = RUNTIME / "tmp"
    cache = RUNTIME / "cache"
    for directory in (home, temp, cache):
        directory.mkdir(parents=True, exist_ok=True)

    # A whitelist environment prevents dotenv/user-site/API-key inheritance.
    env = {
        "PATH": os.pathsep.join((str(Path(sys.executable).parent), "/usr/bin", "/bin")),
        "HOME": str(home),
        "TMPDIR": str(temp),
        "XDG_CACHE_HOME": str(cache),
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    result = subprocess.run(
        [sys.executable, str(SMOKE), "--json"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    report = json.loads(result.stdout)

    assert "Failed to fetch remote model cost map" not in result.stderr
    assert report["status"] == "PASS"
    assert report["upstream_commit"] == "c692d0dfeac4a0296599f7fe21a253a58b7ac12a"
    assert report["positive"]["context_count"] == 1
    assert report["positive"]["candidate_context_count"] == 3
    assert report["positive"]["excluded_available_in_docs"] is True
    assert report["positive"]["pending_available_in_docs"] is True
    assert report["positive"]["generation_session_is_new"] is True
    assert report["negative"]["documents_available"] == 3
    assert report["positive"]["approved_fact_in_final_prompt"] is True
    assert report["positive"]["excluded_marker_in_final_prompt"] is False
    assert report["positive"]["pending_marker_in_final_prompt"] is False
    assert report["positive"]["answer_is_simulated"] is True
    assert report["negative"]["context_count"] == 0
    assert report["negative"]["embedding_calls"] == 0
    assert report["negative"]["summary_calls"] == 0
    assert report["negative"]["answer_calls"] == 0
    assert report["negative"]["lazy_retrieval_calls"] == 0
    assert report["negative"]["session_is_fresh"] is True
    assert report["negative"]["answer_contains_cannot_answer"] is True
    assert report["network_connect_attempts"] == 0
    assert report["litellm_model_cost_map"]["source"] == "local"
    assert report["litellm_model_cost_map"]["is_env_forced"] is True
    assert report["litellm_model_cost_map"]["url"] is None
    assert report["prompt_pre_enabled"] is False
    assert report["prompt_post_enabled"] is False
