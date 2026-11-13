# 模块 D｜获准证据回答与确定性发布门

> 可独立认领：成员 D。你是 answer 功能 owner，负责调用授权、上下文、引用核查、发布门和自己的 view；B 仅执行第三方底层适配。这里是待实施任务，不是已运行安全系统。先审核测试与 OpenCode Plan。

## 1. 目标用户与用户流程

研究者在 C 完成某问题/快照的人工审核 → 看到当前获准证据 → 发起回答 → 系统在预算内只发送获准子集 → 展示草稿及引用/新鲜度核查结果 → 仅当确定性门通过才允许作为发布结果交 E。没有获准证据时直接说明不能回答，**不为生成拒答说明而调模型**。

界面里的“生成”“发布”按钮不是授权边界；直接调用服务仍执行相同门禁。模型自报“成功/有证据/可以发布”没有权威。

## 2. Must 需求、三集与不做项

| ID | 必须实现 | 可检验语义 |
|---|---|---|
| `FR-D-01`、`INV-01` | 无人工获准证据不进入任何生成路径 | B 生成端口、模型工厂初始化、SDK attempt、HTTP attempt 均为零；不是只断言成功响应零 |
| `FR-D-02`、`INV-04` | 引用必须属于实际发送且仍有效获准集；生成前后/提交前核对新鲜度 | 无未经授权/未发送/未知引用发布；snapshot 或 ledger revision/digest 改变即 blocked |
| `FR-D-03` | 受控适配路线，禁自动补证/pre/post/自主 Agent，保原始引用映射 | 经 B 全新过滤 session 调 aquery；截获 payload 和 raw 引用，而非只查清理后的正文 |
| `INV-03` | 仅人审授予 approved | 不从摘要、高分、UI 缓存、模型输出恢复授权；按指定 question/snapshot ledger 投影 |
| `INV-07` | 分层上下文、预算/压缩、关键约束重注入 | registry 拟议输入 cap 12,000 tokens、9,000 开始压缩、输出最多 2,000；最终真实 payload 计数符合模型窗口，规则不被资料覆盖 |
| 共同约束 | `INV-02/05/06/08`、`QA-01`、`PERF-01`、`COST-01`、`SEC-01`、`GOV-01`–`GOV-04` | 来源/历史/权限/许可与真实 registry 阈值一致；零默认模型请求；真实审批/回归/评估 |

- **approved**：该 question、该 snapshot、该 ledger revision/digest 下有效 human accepted 的来源 ID 全集。
- **sent**：预算、排序、裁剪和最终序列化后，真正进入本次请求的来源 ID 集合，不是候选全集。
- **cited**：从模型原始输出可靠解析并映射到完整 evidence ID 的实际引用集合。

硬规则：`cited ⊆ sent ⊆ approved`，三集不能假定相等。成功非拒答还须有可追溯引用（见蓝图）；结构关系不能证明每项自然语言主张被原文语义支持。

**不做：**直接 import `paperqa`、再检索未审核资料、自治 Agent、多轮自由搜索、改 C 决定、自动判真、改 E 历史、独立建第二套模型工厂。模型/提示词变化须真实固定集评估；不得用 fake 固定答案证明 faithfulness 达标。

## 3. 输入输出、异常与失败合同

| 边界 | 输入 | 输出/责任 | 失败时必须做 |
|---|---|---|---|
| A/C/编排 → D | question、固定 CorpusSnapshot、EvidenceRecord、可重放审核投影及 revision/digest、当前 token 读取端口 | 校验来源与人审，再构建 approved | 缺失/损坏/串 question/snapshot 即停止；不从 UI 补批准 |
| D → B 中立生成端口 | 仅选定获准证据、明确策略/提示词版本、最终预算与调用许可 | B 按批准策略序列化、新建过滤 session、aquery；返回 raw、actual sent、key 映射与元数据 | empty approved/sent 不进入端口；失败无自动换模型/无批准重试 |
| B → D | 最终实际 payload 的来源 ID/指纹、raw 输出与 key 映射、usage/finish 状态 | D 验原始引用、内容/截断、新鲜度，构造 AnswerDraft 与 ReleaseDecision | 未知 key、映射歧义、输出错误或 token 改变都 blocked，保全诊断 |
| D → E/编排 | 冻结 draft/release 与关联来源/ledger/调用记录 | 只有该版本门通过才作为发布候选；最终一致性检查后保存 | 保存前 token 变了不能沿用先前放行；草稿可保留但明确未发布 |

真实 v1：AnswerDraft 包含 `approved_evidence_ids`、`sent_evidence_ids`、`citation_evidence_ids`、snapshot/question、`review_revision/review_digest`，status 为 `draft/abstained/failed`；ReleaseDecision 为 `released/blocked`，带各检查布尔值和 reason_codes。`stale` 是 blocked 的原因/展示标签，不擅加为枚举。

**模型字段不是核查证据：**客户端给三集或所有 `*_check_passed=true` 不能自证安全。D 必须用可信 ledger、原始来源、真实发送记录和 raw 输出独立计算；schema validator 只验证声明的一致性，不替代业务发布门。

不合法引用集合可能连 AnswerDraft 的结构校验也通不过：应保留原始无效输出在受控诊断记录，创建符合合同的 `failed` 结果（空 body、无 citations、明确 refusal_reason）及 blocked 决策，而不是删坏引用后构造“成功”草稿。`abstained/failed` 的用户说明在 refusal_reason，不把说明文字塞进要求空的 body。附属 raw/usage/指纹记录的版本化封装在获批 Plan 与 B/E 约定，不能加未知 extra 字段。

空审核 ledger 的初始 `review_revision=0`，对应零人工事件、零获准证据；共享模型已允许它用于 `abstained/failed` 和 `blocked`，不允许 `draft/released`。真实审核事件从revision=1开始，不能为满足字段捏造一次human审核。digest由C从获批的空账本规范计算，D只消费其可信投影；空账本仍须通过独立零模型调用拒答测试。

## 4. 必须实现的受控调用与一致性设计

1. **先零调用检查，再建 backend：**无批准时不初始化上游模型/SDK，不能靠 PaperQA2 自带空上下文拒答，因为 aquery 在拒答前就可能构造模型或补证。
2. **分层上下文：**身份 → 站立约束 → 可信代码生成的授权摘要 → 证据 → 必要历史 → 恢复状态 → 当前问题。原文内的“忽略规则”是资料，不是指令；旧历史不能夹带未获准来源。
3. **确定性预算：**去重/优先级/计数→达到阈值压缩或裁剪→重新注入约束与授权 ID→最终计数。不要用额外未授权模型压缩；不能压缩掉完整身份、human-only、拒答与引用约束。仍超限/裁剪后为空则拒绝调用；输入加输出预留适配批准模型窗口。
4. **B 的执行约束：**每轮全新 PQASession，仅含 sent 对应 contexts；`answer.get_evidence_if_no_contexts=false`、`prompts.pre=None`、`prompts.post=None`，不用自主/fake agent、不带 prior answer/旧 contexts。D 不 import paperqa；B 不决定 approved 或发布。
5. **原始引用优先：**B 本轮别名一对一映射完整 ID；D 从 raw 解析并检查未知/重复歧义，不依赖上游清理后答案。未发送但已批准的引用也不能过门。
6. **新鲜度与提交：**开始捕获 snapshot/review revision/digest；生成不持锁等待模型，A/C 可继续变更；结束重新读 token。最终 D 核查与 E 保存发布在同一单写者临界区内，提交前再比较。撤销再接受即使集合一样，revision 改变仍阻断。
7. **失败封闭：**超时、截断、空答、配置/来源/ledger 损坏、预算不足、unknown usage/未经批准请求等按运行策略停止新增调用并保留明确结果；不得假设失败免费、也不得自动换 provider/model。

该临界区由应用编排协调，D 保持唯一发布判断；UI 不再写一个 `if accepted` 放行。涉及锁/编排共享路径须单独批准。

## 5. 可改路径与无阻塞开发

后续候选写范围：`src/papertrace/answer/`（纯规则、上下文/生成控制、自己的 view）、`test/offline/test_answer.py`（测试/spy）、`test/fixtures/answer/`（合成材料）、`docs/team/module-D.md`。Plan 须把源码、`view.py`、测试及每份 fixture 展开为精确相对文件，经人工确认当轮权限，不因目录 ownership 自动有权；共享 fixture wrapper 只把 `data` 传入模型。模块专属版本化 runtime prompt 放获批的 `prompts/` 子路径；prompt 是共享安全敏感区，必须单列批准、AI-use 与语义评估状态。

共享合同、A/C token 端口、B adapter、E 保存端口、顶层入口/编排、registry/architecture/trace/logs、CI/依赖/锁都不能擅改；用精确提案/独立 PR。冻结 `src/paperqa/`、`packages/`、上游 `tests/`、`pyproject.toml`、`uv.lock`。不读取 secrets/个人目录、不擅自联网或 push。

不等 A/B/C/E：使用合同合法的固定 snapshot、三条证据（accepted/excluded/pending）、追加式 synthetic ledger，以及能记录输入/初始化/尝试次数的 fake backend；fake A/C token provider 可在生成中间切换版本。这些均是自写合成 fixture，fake 只证明输入/门禁，不证明模型质量。

初始化 `.venv`/`requirements-init.lock` 不代表 PaperQA2/Streamlit 已安装。先纯逻辑离线开发，业务依赖/live 分别获批。真实模型默认禁用；provider/model、数据、金额/次数/重试、窗口/输出和 deadline 都需单独批准，不自动沿用源码默认模型。

## 6. 正负/回归与语义测试

| 场景 | 精确断言 | 关联 |
|---|---|---|
| 正常一条获准 | payload 只有该来源；三集可从实际记录重建；raw 引用映射一致；门通过才交 E 发布 | FR-D-02/03、INV-04 |
| 无决定/全排除/只有 AI 建议 | approved 空，backend 入口/工厂/SDK/HTTP 计数全零；abstained/blocked 原因清楚 | FR-D-01、INV-01/03 |
| approved 多于 sent | 裁剪记录准确；引用已批准但未发送项时 blocked；绝不把 sent 伪填为 approved | FR-D-02、INV-04/07 |
| 未知/排除/pending 引用 | raw 保全，blocked；删除坏 key 后不能变为成功；非 UI 入口同样拒绝 | FR-D-02/03、INV-03/04 |
| 模型中途换库/撤销再接受 | snapshot/review 任一 token 改变，旧 draft 即 blocked；最终提交前改 token 也不能写 released | FR-D-02、INV-04 |
| 旧 session/自动补证/pre/post | spy 截获全新 contexts 与配置，旧/未审原文不在 payload；额外请求尝试为零 | FR-D-03、COST-01 |
| 预算边界/压缩重注入 | 低于/达到/超过阈值均覆盖；最终计数含 system/模板，关键约束和身份不丢；超限/空 sent 零调用 | INV-07、COST-01 |
| 恶意证据/旧历史污染 | 原文注入不能改授权或规则；payload 无未获准来源，UI/cache 不能伪造批准 | INV-03/04、SEC-01 |
| 超时/截断/空答/坏 ledger | 无 released；失败 body/状态符合合同；原始诊断可追溯，重试/费用不冒充零 | FR-D-02/03、QA-01 |
| 全回归与真实语义 | 所有历史 offline suites 重跑；live 固定集分开评 faithfulness/relevance/zero safety escapes | GOV-02 |

真实语义评估必须看原文是否支持主张、是否相关、有无授权逃逸，不能仅“有引用”。固定集包括相反/无关/缺证据/注入/陈旧/预算裁剪等，阈值与 gate 依真实 [../ci/gates.md](../ci/gates.md) 和 evaluation 方案，未授权/未执行为 BLOCKED，不填 PASS。

## 7. 可审核执行计划与验收

1. **Plan-1：**读已有 AGENTS/Prompt、蓝图/ADR/registry/contracts；给三集算法、原始引用解析、一致性提交、失败状态/空 ledger、分层上下文/预算设计和可写路径；列 B/C/E 端口，停等审核。
2. **Plan-2：**先提交全部正负 fixture、payload/attempt spy、可控并发与越界测试。非作者批准测试/计划，确认本轮 Build 路径和工具权限；安全判断变更须 ADR。
3. **Build-1：**监督 OpenCode 做纯确定性门/零调用分支/上下文和自己的 answer view；用 fake backend 的实际输入验证，不等待真实模型。
4. **Build-2：**与 B 接受控 aquery，和 A/C/E 接 token/临界区；逐步审查 session、raw 与调用账目，不能为“跑通”放宽引用或自动批准。
5. **Verify：**`.venv/bin/python -m pytest -c papertrace.pytest.ini test/offline` 及真实 gate 命令；获批后才 live，保原请求/回复/模型/prompt/usage/费用与失败。零初始化模型请求不等于业务 live 已测。
6. **独立 PR：**演示“无获准零调用→正常获准回答→未发送引用阻断→中途撤销阻断”；附 D1–D9、真实人审和剩余评估债务。

只有完整回答/门禁功能、自己的 view、负例能阻断、完整回归、人审/真实 transcript 和独立 verdict 齐全才算模块完成。模型很流畅或只通过 schema 不算安全验收。

## 8. D1–D9 与同伴轮换

| 项 | D 的真实证据 |
|---|---|
| D1 | FR-D-01/02/03、INV-01/03/04/07 与共同要求的 fit/测试映射 |
| D2 | 三集/authority、新鲜度/提交、上下文层级/压缩预算、失败策略与安全 ADR |
| D3 | answer 与 prompt 路径白名单、唯一 B import 边界、实际权限/出站控制证据 |
| D4 | 事前测试批准、输入/尝试 spy、并发负例、全回归、真实语义状态、memo/bug/debt |
| D5 | 真实 OpenCode 原始会话及对授权/引用/失败的人工中断/批准理由；非 Hermes 初始化冒名 |
| D6 | 实际功能与风险发现、协作贡献及本人反思素材，最终身份本人填 |
| D7 | 本地 diff/获授权后真实 PR/CI/独立 review 与安全路径 ADR；保护未设不标完成 |
| D8 | answer 服务/view、synthetic fixtures、spy/并发/正负回归测试；live 隔离且原始结果真实 |
| D9 | 根 Prompt 的 Plan 停止点、测试/计划/权限批准及 Build/Verify 记录 |

第一轮：**E 批准测试/计划，A 独立 review，B 集成**；以后依 [工作计划](../../TEAM_WORK_PLAN.md) 非作者轮换，共同实现者回避。按 [交接清单](handover-checklist.md) 交付；安全/接口变化按 [集成合同](integration-contract.md) 审批。

S0–S4 仅相对检查点，每 sprint 建议 1–2 工作日，不是教师 DDL。确切时间、OpenCode/复用/D5 口径由学生确认；GitHub 尚未创建，不编造地址/审批。本任务书不授权模型、凭据或无人监督开发。
