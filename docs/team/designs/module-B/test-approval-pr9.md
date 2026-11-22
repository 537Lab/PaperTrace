# 模块 B B1 测试审批证据：PR #9

- 同步日期：2026-11-21（Asia/Hong_Kong）
- 测试提案 PR：https://github.com/537Lab/PaperTrace/pull/9
- PR 状态：`OPEN`，保持 RED，未合并
- 获批精确 head：`1b9b5a0e6f6b6716de303b6de3891ed6a695f9f3`
- Review ID：`6005637987`（GitHub 随后返回同账号重复 APPROVE `6005640134`）
- Reviewer：`ziqilin669`；与测试/实现作者账号 `ldk13856478627-cell` 不同
- Review 状态：`APPROVED`
- GitHub submittedAt：`2026-11-21T13:47:20Z`

## 审批边界

该 review 明确只批准上述精确 B1 测试设计和 commit，不批准合并 RED 测试 PR，不证明 B2 实现正确，也不代表全部 CI gate 通过。测试或获批 commit 如发生变化，必须重新审核新的精确 head。

旧 APPROVE `5995017817` 绑定 `7833527e2fd069fe61c0c56900949de03d6e3e8f`，不覆盖 review 后新增的 page-only 与具体 PaperQA2 bridge 测试；不能用旧批准替代上述当前 head 的 APPROVED review。

## 实现分支绑定

为避免实现 PR 合并时夹带仍开放的测试 PR，修复实现分支从当前 `main` 创建，并在临时验证 worktree 将实现源码叠到获批测试 head 上运行：

- 实现 base：`6235c33d460b48d1ff11a10624d1bcd5919ea4f0`（当前 `main`）
- 获批测试 head：`1b9b5a0e6f6b6716de303b6de3891ed6a695f9f3`
- 临时组合验证：四个实现源码 + 获批测试得到 `50 passed`
- 实现 PR diff 不包含 `test/offline/test_retrieval.py` 或 `test/fixtures/retrieval/`

因此 Plan v2.1 的 B2 人工 checkpoint 已满足。后续仅可实现四个获准源码文件；实现 PR 必须包含精确行：

```text
Test approval PR: #9
```

## 证据来源与限制

以上 GitHub状态由 Codex 通过 REST reviews API 只读核验，返回 reviewer、精确 `commit_id`、`APPROVED` 与时间。该记录是事实同步，不是 Codex、OpenCode 或角色配置自行生成审批。
