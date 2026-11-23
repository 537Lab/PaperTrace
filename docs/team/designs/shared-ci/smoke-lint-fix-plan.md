# 共享 CI smoke 脚本 lint 修复计划

`origin/main` 上的 `scripts/paperqa_smoke.py:37:1` 触发 Ruff `I001`，导致包含 `scripts/` 的 `static-analysis` 检查失败。

后续实现仅按 `papertrace.ruff.toml` 排序第 37–45 行的九行 import 块。保留各导入的 `# noqa: E402`，以及先设置 `sys.path`、再赋值 `os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"`、随后加载上游依赖的初始化顺序。修复不改变运行时逻辑或固定 PaperQA2 基线。

| 离线测试 | 基线预期 | 修复后验收 |
| --- | --- | --- |
| `test_paperqa_smoke_passes_configured_ruff_lint` | Ruff 退出码 1，报告第 37 行的 `I001`，测试 RED。若 stderr 含 `No module named ruff`，优先报 `TOOL_MISSING: ruff` | Ruff 退出码 0，stdout 和 stderr 均无 `I001` |
| `test_paperqa_smoke_preserves_env_and_sys_path_setup_before_upstream_imports` | PASS | AST 以 `litellm`、`aviary`、`lmi`、`paperqa` 的最早静态导入或字面模块名 `importlib.import_module` 调用为界。此前必须在顶层将环境变量键设为字符串 `"True"`，截至该导入行只允许这一处直接下标写入或删除。顶层循环须显式遍历 `ROOT / "src"` 和 `ROOT / "packages" / "paper-qa-pypdf" / "src"`，并在导入前通过 `sys.path.insert` 插入循环变量对应的路径。测试仅解析 AST |

PR #45 在 `44b10dfd` 上的独立审计要求加强导入顺序与路径循环检查（P1）、区分 Ruff 缺失和 `I001`（P2-1），并同步计划及 AI-use log（P2-2）。本轮验收使用指定虚拟环境检查测试文件的 Ruff、两项 pytest 收集及详细 RED/PASS 结果，再运行 `git diff --check`。两项测试的实际退出码和诊断记录在 AI-use log。

先检查新测试文件的 Ruff 结果并确认 pytest 恰好收集两项，再运行两项并保存 RED/PASS 回执。提案 PR 保持 open，待独立同学在 GitHub 批准具体测试 commit 后，从该 head 创建实现分支。实现 PR 正文写入 `Test approval PR: #N`，并重跑两项测试和全仓静态分析。
