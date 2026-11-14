# Gate 1：事前测试批准（已实现验证器）

实现：`scripts/gate_evidence.py`，由可信 base 的 `gates.py --gate test-approval` 调用。缺真实证据为 BLOCKED，矛盾/自批/撤销/错 SHA 为 FAIL；本地 `approved:true` 无效。

## 学生实际操作

1. 监督学生批准 Plan 和一次模块/离线工具范围；用 OpenCode **仅生成模块测试、合成 fixtures、设计计划**，此时禁止业务源码实现。
2. 将这些内容推为测试提案 PR；可以保持 open 且 RED，**不要为了审批合并红测试**。计划放 `docs/team/designs/module-X/`，或 PR 正文独立一行 `Plan: <具体计划说明>`。每个 PR 如实追加 AI-use log。
3. 另一位非实现者检查具体测试并在 GitHub `Approve`，批准必须指向提案当前 head。测试变了就重新批准。
4. 从测试 head 开实现分支，批准之后才写业务代码并新建实现 PR。实现 PR 描述独立一行：
   ```text
   Test approval PR: #123
   ```
   用真实编号替换；不要照抄。测试/计划 blobs 保持相同，可以存在其他同学已合入的无关测试。实现 PR 合并后关闭未合并的测试提案，避免再次合并旧分支。
5. 若测试 PR 本来就是全绿，也支持它先合并、再从更新后的 main 实现；不是强制合并测试 PR。

## 机器核查与诚实边界

只读 GitHub API 核对同一私有仓库、实际 PR files、作者/commit 参与者、reviewer 的 write/maintain/admin 权限、当前有效 APPROVED、SHA 和撤销事件。GitHub 服务器 approve/PR created/merged 时间确认发布顺序；API commit 时间与本地 Git 对象相同且不早于审批作为附加检查。**Git 日期可伪造，不能单独证明第一次写代码的时间**；独立学生必须审查真实 OpenCode 过程。机器人/作者/共同实现者不能替代学生批准；无需自建账号服务或强制 allowlist。

安全路径还需实现 PR 正文 `Architecture decision: docs/architecture/adr/002-development-readiness.md`（改成实际适用 ADR）和当前 head 的独立人工 APPROVE。普通模块细节不逐项新建 ADR。批准者与最终 reviewer 可以是同一个非实现者。

门禁/工作流自改必须由**未变的 base verifier**核查，候选代码不可自证。首次引入验证器的这份工程修复没有可追溯的学生事前批准，保持 BLOCKED 并交真人采纳；不倒签、不伪造 bootstrap PASS。

本地复核命令（精确 40 位 SHA、真实 PR 号）：
```sh
.venv/bin/python scripts/gates.py --gate test-approval --scope full --base <baseSHA> --head <headSHA> --pr-number <实现PR号>
```
不含 token 的离线 API fixtures 只是验证器正负测试，不是学生审批。

## 合并后的main检查不是另一轮事前批准

PR事件核对open PR；main push由`ci_events.py`从真实commit关联记录找到唯一merged PR，绑定事件before、merge SHA、原base/head和相同文件tree，再把原head交给同一批准验证器重验。不会只相信一个绿色check名称，也不会因为环境无PR编号而跳过。撤销/错SHA/未批准测试、未审合并冲突或无来源push仍拒绝。静态/Schema/完整回归/披露检查实际新main，语义报告仍绑定获批的原PR head。

实现合并后，可关闭仍open的旧RED测试提案；回放只接受`closed_at`不早于实现`merged_at`，且原批准/测试blobs仍一致。合并前关闭或撤销提案仍无效。推荐维护者等待main检查回执再关闭测试提案，以减少API时序混淆。

首次工程采纳只执行[一次性人工步骤](minimal-gates.md#pr-1-的一次性首次采纳bootstrap)，不以它代替普通模块事前批准；新的main检查会保留首次修复原本缺少的真实证据，而非报`missing-pr-number`。
