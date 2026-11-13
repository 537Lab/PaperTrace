# 模块 C｜原文比较、人工审核与审核账本

> 可独立认领：成员 C。你负责 review 功能的需求、设计、监督 OpenCode、测试、PR 和自己的 view；不是只给其他人做人工测试。本轮业务未实现，先审核与 Plan。

## 1. 目标用户与用户流程

研究者收到 B 的候选证据 → 看到“来源原文”和“AI 摘要”明确分栏 → 同时比较至少两条来源/版本/观点 → 对每条明确接受、排除或重置待审并说明理由 → 得到可重放的审核历史 → D 使用该问题、该快照、该审核版本的有效获准集回答。

“用户看过”“模型分数高”“与另一条相似”都不是人工批准。**没有 ReviewDecision 就是 pending**；页面刷新、排序、比较选择不能写审核 ledger。

## 2. Must 需求与不做项

| ID | 必须实现 | 验收语义 |
|---|---|---|
| `FR-C-01` | 只有明确真实 human 操作能接受/排除/重置；决定追加且推进 revision/digest | 未授权 accepted 为零；旧决定保留；当前投影按作用域重放；并发旧 revision 不覆盖 |
| `FR-C-02` | 至少两条证据比较，显示文献、版本、原文定位、摘要和审核理由 | 必需字段全显示；相似/相反来源仍保持独立身份；比较不修改 ledger |
| `INV-03` | 人审是授权唯一来源 | AI 字段、suggestion、缓存标签、导入文件都不能创建有效接受；无决定默认 pending |
| `INV-02/04/05`（协作） | 审核绑定来源/问题/快照；更改审核让在途回答失效；历史不覆盖 | 旧作用域不能迁移批准；撤销再接受即使集合相同，revision 已变也阻断旧生成 |
| 共同约束 | `QA-01`、`PERF-01`、`COST-01`、`SEC-01`、`GOV-01`–`GOV-04`、`INV-06` | 按真实 registry fit criterion；零默认模型请求；批准早于实现，证据无个人信息 |

**不做：**模型自动审核、科学事实自动判真、把同义内容合并成同证据、多用户权限/协作系统、改原文/文献版本、运行 PaperQA2、回答生成/发布、修改旧历史报告。human-only 指本地单人流程的真实操作边界，不承诺防恶意本机管理员的身份认证。

## 3. 输入、输出、异常与交接

| 边界 | 输入 | 输出 | 失败时怎么办 |
|---|---|---|---|
| B/A → C | CorpusSnapshot、当前问题 ID、该快照的 EvidenceRecord、受限来源读取 | 原文/摘要分栏与至少两条比较；状态从 ledger 投影得来 | 版本/hash/定位不符即不能批准；来源缺失提示错误，不拿最新版本替代 |
| 人工操作 → C | evidence ID、问题 ID、snapshot、动作/理由、预期 revision、匿名 reviewer_ref | 合法 ReviewDecision 追加；新 revision 与可重算 digest；读回结果 | 非 human/空理由/越界作用域/旧 revision：拒绝，保留用户输入并要求刷新确认 |
| C → D/E/编排 | 一致读取请求与所需版本 | 指定 snapshot/question 的有效投影、原始事件、revision/digest | 无法重放/摘要不符则 fail closed，不用 UI 缓存补批准 |

**真实 v1 合同：**ReviewDecision 有 `evidence_id`、`snapshot_id`、`question_id`、`status`（`pending/accepted/excluded`）、`actor_kind="human"`、`reviewer_ref`、正整数 `revision`、非空 `reason`、带时区 `decided_at`，显式 `schema_version=1`。`actor_kind="human"` 与 reviewer_ref 只是结构字段，**不能单靠客户端传这两个字符串就认定批准真实**。批准计划需明确服务命令如何只从当前真实人工操作产生决定，测试防模型/批量导入绕过。

ledger 的存储/作用域/摘要规范化/事件顺序/重复提交幂等/读写一致性必须在 Plan 提案并获批；初始空账本revision固定为0，真实人工事件从1递增。当前五模型不自动实现ledger，也没有一个字符串digest能证明真人审批。digest由可信代码按获批规范从原始事件算，与revision一起读回；空账本的规范digest由C给出。共享AnswerDraft/ReleaseDecision已允许revision=0仅记录abstained/failed或blocked，不能捏造human审核或生成draft/released。

重置是追加 `pending` 事件，不删除原接受；撤销后旧版本决定仍在历史，但不在当前 approved。另一 question/snapshot 下的接受不能直接移用。相似摘要或相同引文标题不代表同 evidence；比较界面不去重身份。

与 D 协作提供“读取审核 token/投影”的中立端口，在生成前后和最终发布提交时可核验。A 换 snapshot 或 C 新写决定后，旧草稿必须由 D 阻断；C 只提供事实，不另做发布门。应用编排单写者临界区内处理最终核对，不能跨模块直接写状态文件。

## 4. 可改路径与禁止范围

后续候选写范围：`src/papertrace/review/`（review 服务、ledger、自己的 view）、`test/offline/test_review.py`（测试）、`test/fixtures/review/`（合成材料）、`docs/team/module-C.md`；由获批 Build 创建，不预先造功能空壳。Plan 须把源码、`view.py`、测试及每份 fixture 展开为精确相对文件，经人工确认当轮权限，不因目录 ownership 自动有权。共享 fixture wrapper 只把 `data` 传入模型。

共享 models/fixtures、requirements/architecture/trace、AI-use/review/bug/debt、顶层入口/编排/锁/依赖/CI 需单独申请/预约。审核 safety 语义改变须 ADR+人工审批；不能修改 AGENTS/规则放宽 human-only，也不能为测试“先导入一组 accepted”。

冻结：`src/paperqa/`、`packages/`、上游 `tests/`、`pyproject.toml`、`uv.lock`。不 import `paperqa`、不读取 `.env`/keys/真实私人论文或历史；不调模型、不擅自联网/推送。reviewer_ref 用匿名代号，不在团队材料放姓名/学号/个人账号。

## 5. 依赖与无阻塞 fixture 开发

不等 B/A：用共享规范 CorpusSnapshot/EvidenceRecord，造自己写的两个相反事实和一个无关事实，均有真实可验证 locator、不同来源 ID。界面数据与服务数据走同一投影，fake provider 只能提供候选，不能提供“已审批”。所有材料是自写合成 fixture，不是实际人工审批记录。

准备：无决定、human 接受、排除、接受后重置、同 evidence 不同 question、相似内容不同 doc/version、模型/文件冒充 human、旧 revision 冲突、损坏 ledger/digest、页面重复提交/刷新、在途生成时撤销再接受。fixtures 明示 synthetic，带规范预期，不写未来审批人已经同意。

初始化 `.venv`/`requirements-init.lock` 只保工具/合同环境；Streamlit 业务依赖安装另经计划。C 的核心功能可纯离线验证，不应为比较/审核而请求 LLM。

## 6. 测试与行为评估

| 场景 | 断言（不是只检查 accepted 字符串） | 关联 |
|---|---|---|
| 初始/仅模型建议 | 全部 pending；ledger 无新增 human 事件；D approved 空且无调用 | FR-C-01、INV-03/01 |
| human 接受/排除/重置 | 合法新事件追加，reason/actor/作用域正确，revision/digest 读回且可重放；旧事件不变 | FR-C-01、INV-03/05 |
| 两条原文比较 | 文献/version/locator/excerpt/summary/reason 全部可见；相反/相似内容保独立 identity | FR-C-02、INV-02 |
| 刷新/排序/切换比较 | 展示变但 ledger/revision/digest 不变；重复提交策略无重复授权副作用 | FR-C-01/02 |
| 伪造 human/导入 accepted | 服务命令拒绝模型与文件绕过；schema shape 合法也不能充当审批真实性 | INV-03、SEC-01 |
| 旧 revision/坏 digest/越界 question | 写冲突不覆盖、读取损坏不授权；另一作用域的 accepted 不计入本轮 | FR-C-01、INV-04 |
| 改原文/换 snapshot | 旧决定保历史但不能批准新 evidence，不能静默迁移 | INV-02/04/05 |
| 撤销再接受/中途修改 | 即使 approved 最终一样，revision 变化仍使旧 draft 被 D 阻断 | INV-04，与 D 集成 |
| 服务直调 | 绕过 UI 仍执行 human 操作/作用域校验；session state 不是真相 | INV-03/06 |

行为评估关注研究者能识别“原文 vs AI 摘要”“当前审核 vs 历史决定”“相反论据”，不可用自动判真准确率替代。无须真实模型也能验证人工审核完整性；若新增 AI 辅助比较建议，属于额外范围，须重新批准且不得变权威来源。

每轮跑完整团队离线 prior suite；当前表是待实现语义，不填 PASS。安全不变量要故意破坏后测试失败；不能只靠按钮 disabled 的截图。

## 7. 可审核步骤与验收

1. **Plan-1：**读已有 AGENTS/Prompt、蓝图、registry、合同；画人审动作/ledger/投影流程，明确 question/snapshot scope、空账本、重置/冲突/幂等、digest 规范、可改范围，停等人审。
2. **Plan-2：**给正负 fixture、真实性边界与非 UI 服务测试；和 D/E 确认 token 读回。非作者先批准测试/计划，确认本次 Build 权限。
3. **Build-1：**监督 OpenCode 先做纯服务/追加 ledger/重放，再做 review view 的原文对照和双来源比较，UI 不复制状态机。
4. **Build-2：**加入重置、并发冲突/损坏账本 fail closed、与 D/E 的 fake 集成；失败先留原记录再修，不覆盖历史求绿。
5. **Verify：**`.venv/bin/python -m pytest -c papertrace.pytest.ini test/offline` 及 [../ci/gates.md](../ci/gates.md) 的实际 gates；保存命令/退出码、case 结果、版本，零模型请求。
6. **独立 PR：**演示“比较两证据→一接受一排除→重置→历史仍在→旧 draft 失效”；提交 D1–D9、独立 verdict 和未解决项。

验收须有完整审核功能和自己的 view、真实监督/事前批准、正负与完整回归、不可绕过边界；仅画审核页面或手写 accepted JSON 不能交付。

## 8. D1–D9 与非作者轮换

| 项 | C 应交的真实证据 |
|---|---|
| D1 | FR-C-01/02、INV-03 与协作不变量的 fit/测试映射、范围变化记录 |
| D2 | 人审 authority、ledger/token/投影/空账本设计，失败/幂等/冲突政策与必要 ADR |
| D3 | review 路径与工具白名单、human-only 命令边界、冻结源码未改 |
| D4 | 事前测试批准、非 UI 负例/全回归、memo、真实 bug/debt 与修复证据 |
| D5 | 自己真实 OpenCode 原始会话，审核权威/冲突处的人工干预理由；非 Hermes 初始化冒名 |
| D6 | 实际功能/协作贡献、本人发现的代理遗漏、真实反思素材；最终身份本人填 |
| D7 | 本地 diff/后续授权后真实 PR/CI/独立人审；未建仓与保护不写完成 |
| D8 | ledger/投影服务、双证据比较 view、synthetic fixtures、正负/回归测试 |
| D9 | 读取根 Prompt、Plan 停止、测试/计划/权限批准和分步执行记录 |

第一轮：**D 批准测试/计划，E 独立 review，A 集成**；后续依 [工作计划](../../TEAM_WORK_PLAN.md) 非作者轮换，共同实现者回避。用 [交接清单](handover-checklist.md) 交付；合同冲突先按 [集成合同](integration-contract.md) 审批。

S0–S4 仅相对检查点，建议 sprint 1–2 工作日但不是教师 DDL；确切时间、工具/复用/D5 口径由学生确认。GitHub 尚未创建，不虚构 URL/审批。本书允许开始审核与 Plan，不授权模型/秘密读取或无人监督开发。
