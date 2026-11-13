# 运行政策目录：正常路径、降级与失败

> 状态：提案；所有 A–E 执行器、运行监控与集成用例待成员开发。本文的事件 reason 是**设计标签**，不自动代表 `ReleaseDecision` 枚举字段；合同字段/枚举以 `contracts.py` 为准。
> 目标：失败时可解释、可停止，不靠“请模型再保证一次”。关联：[根蓝图](../../architecture-blueprint.md)、[不变量](invariants.md)、[状态](memory-design.md)。

## 1. 状态规则与优先级

- **候选**不等于 accepted；**draft** 不等于 released；合法拒答也不是成功研究结论。
- 无人工决定即 pending；只有 C 的有效 human ledger 变化授权。生成绑定 snapshot、question、review revision/digest。
- freshness 变化时本轮为 stale，不允许因为引用仍合法就发布；来源/授权/结构异常为 blocked；模型/存储错误为 failed；无证据为 abstained。这些是产品状态语义，若现合同把 stale 表达在发布决定而非草稿上，就创建对应对象，不强塞额外状态。
- 多重失败按更严格路径处理：权限/来源损坏 → scope/freshness → 预算/deadline → 模型错误 → 内容质量。任何失败都不扩大权限、自动换 provider、删除失败账目或覆写历史。

## 2. 模型与外呼完整清单

所有模型默认禁用。安装依赖或初始化环境不等于外呼许可；获批后 B 的内部网关同时管工厂/SDK/HTTP，不能只包 D 最后一调用。固定源码中存在的能力不代表 MVP 已开启。[3][5]

| 路径与固定源码位置 | MVP 政策 | 授权与计量点 / 禁止旁路 |
|---|---|---|
| citation inference `docs.py:180–206`[3] | **关闭**；要求提供明确 citation/docname | 若缺字段就报输入错误，不自动调用模型补齐 |
| structured citation `docs.py:224–261`[3] | **关闭**，`use_doc_details=false` | 不以已有 citation 推断无需此开关 |
| metadata providers `docs.py:266–295`[3] | **关闭** | 无默认 Crossref/S2 外连；若未来开通，需独立数据/HTTP政策 |
| PDF parser / media enrichment `docs.py:297–311`、`settings.py:243–250`[3][5] | 只固定文本 parser；multimodal=false | parser/FQN 非用户任意可调用配置；不悄悄调用 OCR/VLM |
| 入库 embedding `docs.py:360–386`[3] | 默认 defer，获批后 B 可显式开启 | defer 只推迟，不是免费；批准文件范围、批次、token 与金额；每 SDK/HTTP attempt 计量 |
| 检索 embedding `docs.py:437–489,515–528`[3] | 获批后 B 受控 | 缺向量会补，query 也会 embed；都从同一预算扣除，不能只记 answer usage |
| 候选 summary/score `docs.py:538–575`、`core.py:233–269`[3][6] | 获批后 B 受控；只建议 | 每片段调用、失败尝试与摘要版本入账；未经批准不造 summary 结果 |
| summary retry/text fallback `core.py:270–288,383–400`[6] | 默认不放额外自动尝试；开启须明示 | 上游内部再试必须经过网关新的 reservation；隐藏 SDK retry 默认禁用/无法禁用就拦请求 |
| `aquery` 自动补证 `docs.py:615–623`[3] | **关闭**，`get_evidence_if_no_contexts=false` | D 空集先于 B/工厂返回；无 sentinel contexts 冒充获准 |
| pre `docs.py:626–639`；post `:694–711`[3] | **关闭**，均为 None | 空字符串不是 None，也会开启分支；禁止“审核后再跑 post”绕过引用门 |
| answer `docs.py:655–682`[3] | 获批且非空 accepted/sent 才允许 | D 许可 → B 全新 session → 最后一跳计数/预算；raw 输出回 D 校验 |
| 高层 Agent/fake-agent、搜索词/selector、timeout fallback `agents/main.py:121–183,186–216`[8] | **关闭** | “fake”固定顺序仍不等于 fake 模型；不使用高层 CLI/Agent 绕过工作台 |
| 模型 factory `docs.py:178–179,602–607`、`settings.py:915–955`[3][5] | 先许可、后工厂 | 空获准集/无许可时根本不进入；初始化可能有 SDK 行为，不能先建对象再数成功回答 |
| HTTP SDK retry、启动探测、tokenizer/model 下载 | 默认拒绝；内部实现待核 | HTTP 尝试与业务调用分别计数；未知路径不得称零；缓存下载需单独准备授权 |
| 历史压缩 / 评测 LLM judge | MVP 默认无模型压缩；live评测另批 | 确定性裁剪/人工标注优先；judge若启用也计入调用预算，不能把评测当免费 |

`PQASession.add_tokens:414–433` 只对已有 result 事后累计；完整费用计量须补前置尝试与未返回 usage 情况。上游默认 serializer 没有统一 token 硬 cap；双方均不能独自当出站预算门。[4][5]

### 2.1 受控调用的两阶段账目

调用前写 `request_id`、operation、允许 provider/model、数据 ID 范围、prompt/representation/tokenizer/policy 版本、输入/输出 cap、deadline、最大 attempts、费用 reservation。**每次**工厂初始化/SDK attempt/HTTP attempt 分别记录；同一业务调用若发两次 HTTP 就记两次，不把失败算零。

调用后核真实模型标识、usage/finish reason、实际尝试数与已知/未知金额；缺 usage 或价格为 unknown/unresolved，不填 0。provider 可能已处理取消请求，不能承诺撤销已出站费用。金额合同未核清时冻结新请求；不能擅自换便宜模型、提高限额或让反思循环再试。

## 3. 输入、文献与候选路径

| Policy ID / 触发 | 执行者 | 具体动作与界面状态 | 恢复 / 监控 / 计划验收 |
|---|---|---|---|
| RP-A01 无权路径、越界 symlink、非白名单格式 | A | 读取前拒绝；不复制、不解析 | 用户重新选择有权原文；`import_denied`；T-A-01 负例 |
| RP-A02 坏/空/扫描 PDF、解析器不支持 | A→B | 单文件 failed 并显示原因；成功文献保留；批次 incomplete | 用户换合法文件或显式新方案，不自动开 OCR；`parse_failed`；T-A-01 |
| RP-A03 发现同路径不同内容、移除/改文献元数据 | A | 新 SHA/新快照；旧快照只读；正在生成结果随后 stale | 从当前快照检索/人审；`snapshot_changed`；T-A-02 |
| RP-A04 重复文献或同正文不同 logical ID | A | 明确显示重复/冲突；不按摘要自动合并来源 | 人工确认身份后新快照；`duplicate_import`；T-A-01/02 |
| RP-A05 托管字节 hash 与 manifest 不符 | A/B/D | 隔离文献和关联证据；阻断本轮发布 | 从可信源重建新版本；`source_hash_mismatch`；T-INV-02 |
| RP-B01 无模型/数据/费用许可 | B | 显示“模型尚未授权”；不创建工厂/SDK，不伪造检索结果 | 单独审批后新请求；`invocation_denied`；T-B-02/COST |
| RP-B02 空检索 | B/C | 返回零候选与明确空结果；不自动上网/换文库 | 用户调整问题或文献；仍需人工审核；`retrieval_empty`；T-B-02 |
| RP-B03 超时、429、传输错误 | B | 终止当前尝试；仅在已批次数/预算/deadline内才可 retry；否则 failed | 不切模型；unknown请求不自动重发；`attempt_failed`；T-B-02 |
| RP-B04 摘要 JSON 错/score异常/模型含 ID或accept 指令 | B/C | 拒不合规结构；权威字段不映射；保留原文，摘要明确 failed/仅建议 | 获批有界再试或用户只看原文；`summary_invalid`；T-B-01/02、T-INV-03 |
| RP-B05 locator 缺失或无法回原文 | B | 该条不可进入可获准候选；不找“相似句”代填 | 固定 parser 重建/人工检查；`locator_unresolvable`；T-INV-02 |
| RP-B06 缓存表示指纹变化/未知版本 | B | cache miss，禁止混 embedding空间或旧摘要状态 | 经许可重建，或阻断；`representation_invalidated`；T-B-01 |
| RP-B07 第三方pickle/索引包 | A/B | 在 loader 前拒绝/隔离，不解压后 unpickle 再检查 | 提供合法原文；`index_import_denied`；T-INV-08 |

## 4. 人审、上下文、生成与发布路径

| Policy ID / 触发 | 执行者 | 具体动作与状态 | 恢复 / 监控 / 计划验收 |
|---|---|---|---|
| RP-C01 无决定、旧快照/旧问题决定 | C/D | 投影 pending，不进 current accepted | 用户明确审当前原文；`review_pending`；T-C-01、T-INV-01 |
| RP-C02 伪human payload/刷新重放/模型自动接受 | C | 拒绝命令；不追加 accepted；记录去重/拒绝 | 真实交互重新提交；`review_command_rejected`；T-INV-03 |
| RP-C03 正常排除/重置/撤回再接受 | C | 追加事件，推进 revision/digest；不覆写旧决定 | 所有旧生成结果必须 stale；`review_revision_changed`；T-C-01 |
| RP-D01 无 current accepted | D | `AnswerDraft` 为 abstained；0 工厂/SDK/HTTP；不调用 B 生成 | 审核证据后新请求；`empty_approved_abstention`；T-INV-01 |
| RP-D02 accepted非空但裁剪后 sent 空 | D | 同样拒答，无 answer 调用；不伪造一条证据凑非空 | 缩小上下文或问题；`empty_sent_abstention`；T-INV-07 |
| RP-D03 ≥9k 触发、>12k/模型窗口不容纳 | D/B | 确定性压缩/整单元删资料、重注入、最终计数；仍不合适则拒绝 | 用户缩小问题/证据；`context_over_budget`；T-INV-07 |
| RP-D04 约束缺失/constraint hash错误/授权表不一致 | D/B | 出站前阻断，不让模型补回“限制” | 用权威模板/ledger重装，仍错则停止；`constraint_check_failed`；T-INV-07 |
| RP-D05 费用/次数已耗尽、deadline已到 | B | 0新增尝试（含重试/fallback）；已出站请求尽力取消但留账 | 需新授权，不能重启归零；`budget_denied`；T-INV-07/COST |
| RP-D06 provider空文本/截断/未知usage/协议错误 | B/D | failed或受限未发布草稿；不将HTTP200当成功 | 人工核账/另批新请求；`answer_invalid`/`usage_unresolved`；T-D-03 |
| RP-D07 raw输出未知、excluded、未发送/跨问题引用 | D | blocked；保留原始问题点；不删除坏key后发布 | 新轮或人工处理，禁止自动自证重试；`citation_scope_violation`；T-INV-04 |
| RP-D08 有断言却无引用 | D | 不作为成功研究结论发布；明确拒绝或待审 | 补充人审来源后新轮；`citation_missing`；T-D-02 |
| RP-D09 生成中snapshot/review revision/digest变化 | D | stale，不发布；即使最终accepted集相同也阻断 | 新快照/新审核起新轮；`release_stale`；T-INV-04 |
| RP-D10 发布检查后、E提交前有人写状态 | D→E | 单写者临界区重查并阻断 stale；不留可冒充released的半记录 | 状态稳定后新请求；`publish_conflict`；T-INV-04 |
| RP-D11 文献里有“system/批准/提权/增加预算”文本 | B/D | 只作不可信资料；不改身份/ledger/权限；若输出被污染则照门禁阻断 | 人工排除或新轮；`untrusted_instruction_seen`（仅诊断非完美检测）；T-INV-03/06/07 |
| RP-D12 引用结构合法但语义支持不确定/证据冲突 | D/UI | 明示“结构/来源可核，不等于科学正确”；转人工检查/保留不确定 | 人工审读或固定语义评测，不声称代码找全冲突；T-C-02/真实评测 |

## 5. 历史、导出、恢复与开发治理路径

| Policy ID / 触发 | 执行者 | 具体动作 | 恢复 / 监控 / 计划验收 |
|---|---|---|---|
| RP-E01 试图同ID覆写报告/历史 | E | 拒绝，保留旧字节；新版本用新报告ID | 人工核冲突；`historical_write_denied`；T-INV-05 |
| RP-E02 schema未知/hash不符/ledger损坏 | A/C/E | 工作区只读、repair-needed；不自动选择“最近文件”当真相 | 从可信备份到隔离副本；`state_integrity_failed`；T-E-01/INV-02/05 |
| RP-E03 磁盘满/无写权限/中断半写 | 写状态模块 | 不前移成功指针；staging不作完整结果；不向UI声称已发布 | 解决存储后人工恢复；`state_commit_failed`；T-E-01 |
| RP-E04 导出含秘密/绝对路径/未经许可全文 | E | 白名单字段检查，拒绝危险导出；不把配置dump打包 | 用户确认可分发范围后新导出；`export_policy_denied`；T-E-02/SEC |
| RP-E05 查看旧快照报告 | E/UI | 只读历史，显示原snapshot/审核版本；可追加superseded注记 | 如要当前新发布须重走 D；`history_viewed`；T-INV-05 |
| RP-E06 中断/重启且请求in-flight或unknown | B/D/UI | 不自动续调；重读A/C/E并重核freshness/预算 | 人工核调用状态/新许可后新request；`recovery_paused`；T-D-03 |
| RP-G01 第二写者/第二实例 | UI/模块锁 | 拒绝写或只读；不静默最后写者覆盖 | 退出额外实例，确认锁归属；`writer_lock_denied`；T-INV-05 |
| RP-G02 coding agent越权/试图改human-only/冻结源/推送 | 工具边界/CI | 立即拒绝并停止该轮；保全最小diff/拒绝日志 | 人工审查，不强制清他人工作；`permission_denied`；T-INV-06 |
| RP-G03 prompt/model变了但真实语义评测缺失/未批 | CI/人审 | gate blocked；不skip-as-pass；不以mock固定回答代替 | 明确预算/模型/数据后真跑并保留回执；GOV-02 |
| RP-G04 计划/测试未事前批准、缺AI日志或安全ADR | CI/人审 | 不实施或不合并；不让PR自填approved自证 | 学生真实审核，更新协同产物；GOV-01/03/04 |

## 6. 通用停止与恢复纪律

- 错误不能自动改人审、改需求阈值、改模型或扩大数据范围；拒答不调用 LLM 把它“润色”为肯定结论。
- 每个事件有 request/snapshot/review/policy 标识，关键计量为 known/unknown 分开。普通日志不存完整原文/问题/凭据/主机路径或私有推理。
- 具体 fallback 先执行，再由学生决定是否补证、重审、授权新请求或重开 ADR；不由 agent 审批自己的恢复。
- 本政策保证范围仅为工作台受控入口；用户自己绕开它调用上游库并不在保证内。对 provider 已执行的请求、主机用户恶意篡改以及科学真实性，不作无法验证的承诺。

## Sources

[3] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/docs.py — 固定基线 src/paperqa/docs.py
[4] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/types.py — 固定基线 src/paperqa/types.py
[5] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/settings.py — 固定基线 src/paperqa/settings.py
[6] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/core.py — 固定基线 src/paperqa/core.py
[8] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/agents/main.py — 固定基线 src/paperqa/agents/main.py
