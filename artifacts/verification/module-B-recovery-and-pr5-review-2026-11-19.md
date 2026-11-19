# B0 恢复与 PR #5 技术复核

日期：2026-11-19，Asia/Hong_Kong。执行：Codex 辅助；不是学生独立审批记录。

## 1. B0 恢复结果

用户在当前聊天批准独立 Git 副本、隔离构建工具及生成版本文件。完整/普通浅克隆多次被连接重置，最终使用 `--filter=tree:0 --no-checkout --depth=1` 获取真实提交，再补齐历史与标签。

- 独立副本：工作区 `PaperTrace-git-minimal/`。
- HEAD：`310ebb3b7b781288308d2b2e15d5574c10b80878`，分支 `test/A-corpus-management`；不是 B 的提交分支。
- Git 历史：非 shallow，949 个提交；原始 HEAD 由 Git 传输取得。
- GitHub 精确提交归档的 333 个 blob 全部与 API 返回的 Git blob SHA 一致；397 个 blob/tree 对象按真实内容还原并逐个核对 SHA，随后用 Git 恢复工作树。未制造提交、标签或学生历史。
- 固定上游 `c692d0dfeac4a0296599f7fe21a253a58b7ac12a` 的 166 个冻结文件与当前树及磁盘字节一致，没有新增受跟踪上游改动。
- runtime 锁、smoke 脚本和 smoke 集成测试与原 B ZIP 副本逐字节相同。

隔离构建环境固定为 setuptools 80.9.0、setuptools-scm 8.3.1、packaging 25.0，下载哈希见 `module-B-build-tools-2026-11-19.lock`。调用原 `setuptools.build_meta.prepare_metadata_for_build_wheel`，由原配置生成被 Git 忽略的 `src/paperqa/version.py`；未手写版本、修改 pyproject 或项目依赖锁。

实际生成版本是 `0.1.dev949+g310ebb3`。这是当前 fork 仅有团队标签时 setuptools-scm 从真实历史计算的开发版本，不代表 PaperQA 官方发行版号；上游源码身份以固定 commit 和逐文件 Git 哈希为准。`git status --short` 为空，生成版本文件未纳入 Git。

真实测试：使用原锁 runtime 的 Python 3.14.6，以白名单环境执行：

```sh
<original-runtime>/bin/python -m pytest -c papertrace.pytest.ini test/integration/test_paperqa_smoke.py -q
```

结果：`1 passed in 6.77s`。另执行原样 `scripts/paperqa_smoke.py --json --report ...`，真实 JSON 见 `module-B-paperqa-smoke-recovered-2026-11-19.json`：

- status=PASS，network_connect_attempts=0，LiteLLM 使用本地 cost map。
- 正向检索得到三个候选，生成新 session 只发送一个所选 context；排除/pending marker 未进入最终 prompt。
- 空 context 下 embedding、summary、answer、lazy retrieval 调用均为 0。
- 模型方法使用本地 deterministic test double；未使用学校 Key。真实模型质量、正式 B adapter、A–E 联调均未验证。

## 2. PR #5 审核对象与结论

- PR：https://github.com/537Lab/PaperTrace/pull/5
- 最新 head：`310ebb3b7b781288308d2b2e15d5574c10b80878`，本轮复查仍 open，head 未变化。
- 共九个改动文件：A 测试/四份合成材料/README/两份设计记录，以及追加式 AI 使用日志。没有业务源码、共享模型、依赖、CI 或权限改动。
- 技术结论：**未发现阻止接受当前 A 测试提案的新增问题；可供未参与 A 测试编写的学生审阅后批准。不能据此合并红测试或宣称 A 功能完成。**

核对覆盖：真实请求字节及 SHA、逻辑身份、只含 ready 的真实快照、历史不覆盖、显式失败重试、源路径授权、丢失/损坏托管源、非法回执、错误脱敏、持久化中断、串快照读取及 ABA revision。Fake 只替摄取依赖，没有替代 A 服务；测试没有 skip/xfail 或为通过而删除业务断言。A→B 回执及部分库/freshness 明确标为待 owner 确认，未偷偷冻结共享接口。

### 本轮实际复跑及限制

| 检查 | 本轮结果 |
|---|---|
| A 专属测试 | 2 passed、31 failed，0.48s；31 项均 IMPLEMENTATION_MISSING，业务断言尚未到达 |
| 全 offline（原 runtime 环境） | 328 passed、35 failed、2 skipped，40.90s；不能当作 init 锁环境的完整复现 |
| Ruff 0.15.1 | scripts/paperqa_smoke.py:37 I001；不是仓库 init 锁要求的 Ruff 0.17.5 |
| 当前远端 Checks | schema / semantic-evaluation / ai-use-log success；regression / static-analysis / test-approval failure |

全 offline 的额外四项为：共享 EvidenceRecord 在缺 schema_version 的输入下抛 KeyError；系统 sandbox 禁止 ps；两项 gate 工具环境检查失败。共享 contracts.py、smoke.py 及相关既有测试与 PR base `7b5549ced8b5c9c1c1eb35576da95bc1381e858a` 的 blob SHA 相同，PR #5 未引入这些文件的变化。runtime 的 Pydantic 2.12.5 与 init 锁的 2.14.3 不同，因此不将本次额外失败直接诊断为所有正式环境均可重现的产品缺陷；未改契约/测试求绿。

远端 test-approval 真实原因包含 `test-proposal-only-do-not-merge-red-tests`。当前提案可保持 open/RED；Approve 不会使 A 业务功能自动通过，也不要求现在合并。后续正常重启持久性及损坏 current/manifest 恢复测试仍是已披露的补充建议。

### 真人审核状态

本轮**尚未提交 GitHub Approve、评论或合并**。本报告是技术辅助复核；独立学生应阅读结论、确认自己未参与 A 测试实现，再批准上述精确 head。不得把本报告或模型生成的文字登记为已经发生的学生审批。若 head 变化，应复核新差异。

### 后续事件（同日追加）

上述“尚未提交”描述的是本技术复核完成时的状态。之后，B 模块负责人使用新账号
`ldk13856478627-cell` 在 GitHub 对 PR #5 的精确 head
`310ebb3b7b781288308d2b2e15d5574c10b80878` 提交了真实 Approve；页面显示
`Approvals 1/1`，且无后续 head 变化。该批准只允许 A 负责人按仓库流程进入实现阶段，
不表示 A 功能、红测试或完整回归已经通过，也没有合并 PR #5。
