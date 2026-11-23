# 共享 CI smoke 脚本 lint 修复计划

`origin/main` 上的 `scripts/paperqa_smoke.py:37:1` 触发 Ruff `I001`，导致包含 `scripts/` 的 `static-analysis` 检查失败。

后续实现仅按 `papertrace.ruff.toml` 排序第 37–45 行的九行 import 块。保留各导入的 `# noqa: E402`，以及先设置 `sys.path`、再赋值 `os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"`、随后加载上游依赖的初始化顺序。修复不改变运行时逻辑或固定 PaperQA2 基线。

| 离线测试 | 基线预期 | 修复后验收 |
| --- | --- | --- |
| `test_paperqa_smoke_passes_configured_ruff_lint` | Ruff 退出码 1，报告第 37 行的 `I001`，测试 RED | Ruff 退出码 0，stdout 和 stderr 均无 `I001` |
| `test_paperqa_smoke_preserves_env_and_sys_path_setup_before_upstream_imports` | PASS | AST 中两个初始化操作均存在，并严格早于所有 `aviary`、`lmi`、`paperqa` 导入。测试不执行 smoke 脚本 |

先检查新测试文件的 Ruff 结果并确认 pytest 恰好收集两项，再运行两项并保存 RED/PASS 回执。提案 PR 保持 open，待独立同学在 GitHub 批准具体测试 commit 后，从该 head 创建实现分支。实现 PR 正文写入 `Test approval PR: #N`，并重跑两项测试和全仓静态分析。
