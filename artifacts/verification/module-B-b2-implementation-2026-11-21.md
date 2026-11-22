# 模块 B B2 实现与验证记录

- 日期：2026-11-21（Asia/Hong_Kong）
- 实现分支：`fix/B-retrieval-pr12`，从当前 `main` `6235c33d460b48d1ff11a10624d1bcd5919ea4f0` 创建
- 获批 B1 head：`1b9b5a0e6f6b6716de303b6de3891ed6a695f9f3`
- 测试批准：GitHub PR #9，review `6005637987`（同账号随后重复提交 `6005640134`），状态 `APPROVED`
- Reviewer：`ziqilin669`；实现/测试提交作者账号为 `ldk13856478627-cell`
- 测试 PR：保持 open、RED、未合并

## 实现来源与人工干预

CityU `CS5351/DeepSeek-V4-Flash` 在多轮工具调用中持续出现 `reasoning_text` 400 或 transport reset。经学生逐次授权，尝试后台服务、临时 `reasoningField` 和 `no-thinking` variant；临时配置均在各次尝试后删除且未提交。`openai/gpt-4.1` 尝试在发送文件前被团队权限拒绝，没有模型执行。

审批记录同步后，OpenCode v2.0.12 会话 `ses_e03048ce7ffeaYabKuKCoO5oON` 使用 `papertrace-build-B`，在禁止工具调用的单轮响应中生成完整四文件 `apply_patch`。Codex 按学生授权原样应用补丁；第一次 Ruff 只报 `src/papertrace/retrieval/service.py` 的未使用 `Mapping` import，Codex 机械删除该 import，没有修改行为逻辑或测试。

初版 PR #12 收到正式 `REQUEST_CHANGES` 后，Codex 按 review 先在 PR #9 增补两个 RED：page-only 伪造摘录拒绝及具体 PaperQA2 bridge 调用。新测试 head `1b9b5a0` 获独立 APPROVE 后，Codex 才修正实现：

- 从当前 `main` 重建干净实现分支，不携带 PR #9 测试/fixtures/计划提交；
- 增加具体 `PaperQA2Adapter`，真实调用 `Docs.aadd`、`Docs.aget_evidence`、`Docs.aquery`；
- 对 page-only excerpt 至少验证其真实存在于受控 UTF-8 source bytes；
- 真实 bridge 仅接受本轮获准的受控 UTF-8 text，PDF/OCR 无可验证 page reader 时显式失败。

源码仍仅为：

- `src/papertrace/retrieval/__init__.py`
- `src/papertrace/retrieval/gateway.py`
- `src/papertrace/retrieval/service.py`
- `src/papertrace/retrieval/view.py`

## 批准测试

实际命令：

```text
../PaperTrace-plan-B-liyafei/.local/unblock/runtime/.venv/bin/python -m pytest -c papertrace.pytest.ini test/offline/test_retrieval.py -q
```

结果：`50 passed in 0.33s`。原 48 项保持通过，新增两项 review 回归也通过。没有在实现分支修改、skip、xfail 或放宽已批准测试。

## 真实 PaperQA2 离线 bridge smoke

在临时验证 worktree 中复用已批准 runtime、synthetic `.txt`、确定性 fake embedding/summary/answer 和 socket fence，实际调用具体 bridge。结果：

```json
{"answer_calls":1,"evidence_count":1,"generation_status":"SUCCESS","network_connect_attempts":0,"retrieval_status":"SUCCESS","source_reads":2,"status":"PASS","summary_calls":1}
```

临时 worktree 只为固定上游提供已有构建生成的 `paperqa/version.py`；未跟踪、未修改或提交冻结上游文件。该 smoke 证明真实本地 API 接线，不证明真实模型质量或 PDF/OCR 支持。

## 静态与 schema

使用已有本地 Ruff 检查 `src/papertrace/retrieval`、B 测试与 fake：`PASS`；检查测试组合 worktree 的 `src/papertrace test/offline scripts` 为 `PASS`。clean-main 实现分支的 B 源码通过，但全范围仍报告本分支未修改的 `scripts/paperqa_smoke.py:37:1 I001`。clean-main schema gate：`PASS`，27 条需求结构验证通过；AI-use-log gate：`PASS`，识别 1 条新增披露。

批准 runtime 与现有补充环境均无 mypy 可执行文件，因此 mypy 为 `BLOCKED/NOT_RUN`；未下载依赖或修改锁。

## 完整离线回归

实际命令：

```text
../PaperTrace-plan-B-liyafei/.local/unblock/runtime/.venv/bin/python -m pytest -c papertrace.pytest.ini test/offline -q
```

结果：`400 passed, 6 failed in 73.91s`。6 项失败均不是 B2 新增失败：

1. 共享 `EvidenceRecord` 缺少 `schema_version` 时既有 `KeyError`。
2. 沙箱禁止测试调用 `ps`。
3. 两个 gate 自测因该 runtime 缺 Ruff/mypy 而失败。
4. 两个 OpenCode workflow 自测因沙箱禁止 loopback bind 而失败。

不修改共享契约、gate、环境测试或 B 测试来掩盖这些失败。

## 范围与限制

- 冻结上游、共享契约、其他成员模块、依赖、锁、CI 和测试：无改动。
- 新源码敏感信息扫描：无凭据、私钥、邮箱或个人绝对路径。
- 真实产品模型、真实论文、live 检索质量与 D 真实业务联调：`NOT_RUN`。
- 当前 bridge 只支持受控 UTF-8 text；真实 PDF/OCR/page reader 属单独批准范围。
- PR #12 将更新为新的 clean-main head；仍须独立实现审核，禁止自动合并或作者自审。

## 2026-11-22 PR #12 CI 跟进

对 GitHub Actions run `44919741896` 做只读核对后，`static-analysis` 的两个失败已分别复现：

- 全范围 Ruff 仅报告未被本 PR 修改的 `scripts/paperqa_smoke.py:37:1 I001`；B 模块 scoped Ruff 通过。
- 固定 `mypy==1.20.2` 对 `src/papertrace` 报告 `service.py` 四个严格类型错误：两个注入协程返回值缺少泛型约束、一个局部变量复用导致赋值类型冲突、一个失败类型字典查询未先收窄 key。修复只增加类型约束和显式收窄，不改变公开接口、控制流或测试。

修复后验证：

```text
ruff 0.17.5, src/papertrace/retrieval: All checks passed!
mypy 1.20.2, src/papertrace: Success: no issues found in 9 source files
PR #9 exact head 1b9b5a0 tests: 50 passed in 0.09s
```

Ruff/mypy 通过 `uv run --isolated --no-project` 使用 `/private/tmp` 缓存和已有 Python 3.12 执行；未修改项目环境、依赖或锁。50 项测试从 PR #9 精确 head 的 Git blob 提取，使用当前源码运行，未修改、skip、xfail 或放宽测试。由于本轮临时下载 `pytest-socket` 的授权检查未执行，该次 50-pass 是补充回归，不替代上文已经完成的带 socket fence 的 `50 passed in 0.33s`。

`test-approval` 的当前失败不是 B 业务代码问题：PR #9 包含验证 artifacts，而 base verifier 只允许测试、fixtures、团队计划和 AI log；同一 verifier 又要求实现 head 保留获批测试/计划 blob 及祖先关系，而 PR #12 的正式 Review 要求 clean-main diff 不携带 PR #9。两项要求需维护者明确处理路径；本轮没有修改 gate、测试 PR、共享文件或合并顺序来规避冲突。
