# 模块 E｜研究历史、可追溯报告与导出

> 可独立认领：成员 E。你负责可使用的 reports/history/export 业务、自己的 view、需求/设计/监督 OpenCode/测试/PR；不是只写课程文档。本轮业务未实现，先审核与 Plan。

> **动手前先按 [新人启动流程](startup.md) 接通私有仓库与环境**：被邀请 → clone → Python 3.14 初始化环境 → 实跑 170 项离线测试。任何人都能立即做，不需要模型或凭据；B/D 的真实 PaperQA2 依赖与 OpenCode 获准配置见该文档第 1/2 层。门禁真实状态与最小落地方案见 [../ci/minimal-gates.md](../ci/minimal-gates.md)。

## 1. 目标用户与完整用户流程

研究者完成一次问题研究（也可能被阻断）→ 保存问题、版本、证据、人工审核、回答和发布结论 → 关闭/重新打开应用仍能查历史 → 从历史定位当时原文与审核理由 → 导出 JSON 和 Markdown → 文献后来换版时旧研究仍显示原版本，并明确它不代表当前新发布。

**应用研究报告 ≠ 课程 `Report.md`（D6 过程报告）。**你要交的是用户可操作的历史/导出功能；仍需像其他成员一样为 D6 提供本人真实过程素材，但不能用写 D6 替代功能。

## 2. Must 需求与不做项

| ID | 必须实现 | 可检查的验收语义 |
|---|---|---|
| `FR-E-01` | 保存/跨会话加载研究链，导出 JSON 与 Markdown | 必需内容覆盖率满足 registry：问题、snapshot、获准/实际发送证据、审核决定、答案/拒答、发布结果、来源定位；JSON 读回与 Markdown 语义一致 |
| `FR-E-02` | 历史只读；换版标明旧 snapshot 已被替代；默认导出脱敏且守许可 | 不泄露 credentials、本机绝对路径或未经授权论文全文；旧记录不变，通过新视图/追加注记表达 superseded |
| `INV-05` | 历史追加而不覆盖，保留原版本与决定 | 被覆盖历史记录数量为零；同问题新运行是新记录，旧内容 hash 不变 |
| `INV-02/03/04`（协作） | 追溯链不能漂移或升级授权 | 不以最新库替旧库；不把 pending/excluded/blocked 改为 accepted/released；发布前提交仍核 token |
| 共同约束 | `QA-01`、`PERF-01`、`COST-01`、`SEC-01`、`GOV-01`–`GOV-04`、`INV-06/08` | 真实 registry 的 fit/阈值；零默认模型请求；路径/许可/治理合规 |

**不做：**重新生成/润色答案、运行 PaperQA2、批量下载论文、多用户云同步、复杂数据库、PDF/Word 排版器、自动补丢失原文、编辑旧报告、把 model 自评升级为发布。默认先 JSON/Markdown，不擅自扩成大型报告平台。

## 3. 输入、输出、异常和交接

| 边界 | 输入 | 输出/责任 | 异常处理 |
|---|---|---|---|
| 编排/A/B/C/D → E | 同一研究范围的问题、CorpusSnapshot、EvidenceRecord、ReviewDecision 原始 ledger 与 revision/digest、AnswerDraft、ReleaseDecision，以及获批运行元数据 | 版本化、不可变研究记录；保存时核相互关联的 question/snapshot/answer/审核 token | 缺对象/错版本/错关联/坏摘要：拒绝作为完整发布保存，显式 incomplete/blocked，不用当前库补齐 |
| D/编排 → E 最终提交 | 对应版本的发布核查与预期 snapshot/review token | 同一单写者临界区内核对后写入；返回可读回记录标识 | 核查后落盘前 token 变化或写失败：不能显示已发布，保留错误，不自造另一个发布判定 |
| E → 用户 | 历史列表/详情、明确版本和状态、受限来源链接 | 旧证据/人工理由/答案/拒答/阻断原因可追溯 | 原件已不可用则标明缺失，不通过同名新文件替代 |
| E → 导出目标 | 明确选择的本地安全路径与格式 | JSON + Markdown，显示当时状态、版本、来源定位与必要说明 | 路径穿越/符号链接逃逸/同名冲突/磁盘写失败：拒绝或显式用户确认安全覆盖，原历史不可损坏 |

五模型的字段/枚举读真实 `src/papertrace/contracts.py`，尤其 AnswerDraft `draft/abstained/failed`，ReleaseDecision `released/blocked`；`stale/superseded/incomplete` 是记录/展示语义，不能偷偷加进这两个枚举。`schema_version=1` 显式且未知字段拒绝。

研究记录包是 E 后续设计的**版本化封装**：引用/嵌入这五类标准对象，另外保存问题文本、运行标识、原始结果/表示与提示词版本等获批元数据；不是再造五个私有同名模型，也不向 frozen 模型塞 extra 字段。封装字段、最小必需项、raw 诊断私有留存、兼容/缺失策略在 Plan 中让生产者/消费者共同审阅后实施。不存在的 usage/费用标 unknown，不推测 0。

### 历史/导出不能越过的语义

- 历史内保存“当时”的 snapshot 与完整身份、ledger revision/digest、approved/sent/cited、D 的决策及原因；新版本只追加记录/注记或改变列表投影，不能修改旧序列化内容。
- `blocked` 草稿和拒答可以保存供追溯，但详情/导出清楚标为未发布；历史 released 表示当时通过，不自动成为当前研究的新发布。当前新报告必须重新经过 D。
- D 是唯一发布权威。E 校验引用关联与存储条件但不把 bool 全 true 的外来 JSON 当可信发布命令，不直接根据 UI 按钮或 stored status 升级状态。
- 原始无效引用/模型诊断可能不适合有效 AnswerDraft body，由 D/B 交给受控诊断区；E 不删掉坏引用后导出成成功答案，也不默认把 raw 输出/完整论文打进分享包。
- 默认导出允许用于追溯的授权短 excerpt/locator 与必要元数据，不导出未经许可全文、密钥、绝对路径、模型私有推理或个人身份。数据许可/敏感字段白名单必须可测，不因根 Apache-2.0 就捆绑论文。

## 4. 可改路径与禁止范围

后续候选写范围：`src/papertrace/reports/`（历史存储/读取、JSON/Markdown exporter、自己的 view）、`test/offline/test_reports.py`（测试）、`test/fixtures/reports/`（合成材料）、`docs/team/module-E.md`。由获批 Build 创建业务目录；Plan 须把源码、`view.py`、测试及每份 fixture 展开为精确相对文件，经人工确认当轮权限，不因 ownership 自动有权。共享 fixture wrapper 只把 `data` 传入封闭模型。

共享 contracts/fixtures、record envelope 对外接口、A/C/D 端口、registry/architecture/trace、AI-use/review/bug/debt、app/应用编排/锁、依赖/CI 需独立范围批准与预约编辑者。不能直接写 A 库文件、C ledger、D gate，不能在共享入口堆报告业务逻辑。

冻结：`src/paperqa/`、`packages/`、上游 `tests/`、`pyproject.toml`、`uv.lock`。不 import `paperqa`、不读 `.env`/keys/个人文献/真实历史、不擅自联网或推送。默认不引入云存储和大型数据库，先单机本地受控文件。

## 5. 依赖与无阻塞 fixture 开发

不等 A–D：用规范合成模型组合出完整 released 研究、blocked 未发送引用研究、abstained 无批准研究、failed 超时研究；全部由 fixture 明示 synthetic，不伪造真正人审或模型会话。

再准备：相同问题两次运行、同名文献换版、旧原件丢失、错误 snapshot/question/answer 关联、ledger digest 不符、未知 schema/字段、导出中断/路径穿越/文件冲突、含“本机路径/模拟敏感值/全文标记”的脱敏 fixture（只自写假数据，不读取真实 secrets）。

报告内容的 expected 应检查实际字段与语义，不只快照文件存在。JSON 读回使用真实共享模型校验；Markdown 的列表/标题/代码围栏/特殊字符要保证引用不会串到另一证据。默认工具环境只保初始化工具/合同，Streamlit 等依赖另经批准；E 无须模型调用即可开发和验收核心功能。

## 6. 正负、回归与行为测试

| 场景 | 精确断言 | 关联 |
|---|---|---|
| 正常保存/跨会话加载 | question、snapshot/doc/version、evidence/locator、ledger、三集、draft/release 读回相同；关闭重开仍能追溯 | FR-E-01、QA-01 |
| JSON + Markdown 导出 | 两格式包含必需字段与同一状态/来源；JSON 可重解析，Markdown 引用映射无错配 | FR-E-01 |
| 历史换版/重复问题新运行 | 旧记录 hash/内容不变，新运行新记录；superseded 只投影/追加，不写旧包 | FR-E-02、INV-05 |
| blocked/abstained/failed | 未发布提示与原因清楚，不把失败输出当正文或成功；未知引用诊断不被洗成 released | FR-E-01/02、INV-04 |
| 错关联/坏摘要/缺历史 | 拒绝完整发布或明示不完整；不以最新库/同名文件回填、不丢坏记录后称全部完成 | INV-02/04/05 |
| 最终提交前变更 | D 核查后 A/C token 改变，发布保存不成功；I/O 失败不能显示已发布 | INV-04，与 D/编排集成 |
| 导出脱敏/许可 | 无 credentials、本机绝对路径、未经许可全文/私有推理；只检自写 fixture，不扫描私域 | FR-E-02、SEC-01、INV-08 |
| 路径与写入失败 | 穿越/链接逃逸/非允许目录拒绝，无范围外写；冲突确认/原子写策略明确，中断不损坏旧记录 | SEC-01、INV-05/06 |
| 版本兼容/未知字段 | 当前合同 roundtrip；未知版本/字段拒绝或显式只读不支持，不静默修成通过 | QA-01 |
| view/服务一致 | 用户清楚看当时/当前、草稿/发布/阻断；绕过 UI 也不能把 blocked 改 released | INV-04/05 |

行为评估重点是“普通研究者能追溯来源和审核、不会把旧报告/失败草稿当当前结论”；可用固定合成案例和人工操作验收。E 不宣称检索/模型忠实度达标。每轮完整 prior suite 回归，未运行项不填 PASS；live 验证仍看全组授权与 [../ci/gates.md](../ci/gates.md)。

## 7. 可审核计划与模块验收

1. **Plan-1：**读已有 AGENTS/Prompt、蓝图、registry/contracts；列研究记录封装/必要字段、历史不可变、状态展示、导出白名单/许可、路径与原子写策略、兼容/缺失失败动作，停等批准。
2. **Plan-2：**提交上表 fixtures/断言与 D 临界区交接；非作者批准测试/计划，确认 Build 路径/工具权限。涉及共享封装/接口先按集成合同审查。
3. **Build-1：**监督 OpenCode 先做纯本地保存/加载与 reports view，使用 synthetic 完整/blocked 记录，验证跨会话读回。
4. **Build-2：**做 JSON/Markdown 导出、历史换版提示、脱敏/路径保护/中断恢复；与 D/编排接一致性保存，不另写发布 gate。
5. **Verify：**`.venv/bin/python -m pytest -c papertrace.pytest.ini test/offline` 及真实 gate 命令，保留输出/返回码/版本；从最终导出件读回核实全部字段及例外状态，而不是只看导出成功提示。
6. **独立 PR：**演示“保存正常/阻断研究→重开查历史→文献换版旧报告不变→两格式导出→越界路径被拒”；附 D1–D9、独立 verdict、剩余缺口，不伪造 GitHub 链接。

完整历史/导出与自己的 view、正负/全回归、人审先于实现、真实 OpenCode transcript 及独立审查齐全才算完成。只写几份 Markdown 示例报告或课程文档不算功能交付。

## 8. D1–D9 与轮换交接

| 项 | E 应提供的真实证据 |
|---|---|
| D1 | FR-E-01/02、INV-05 与来源/发布/安全协作 fit/测试映射 |
| D2 | 版本化研究包、不可变存储/保留/恢复、导出白名单/兼容、D 临界区端口与必要 ADR |
| D3 | reports 路径/工具白名单，受控导出、冻结核心未改证据 |
| D4 | 事前测试批准、跨会话/脱敏/路径/失败负例、全回归、memo、真实 bug/debt |
| D5 | 本人原始 OpenCode session，历史/状态/许可风险处的人工干预/批准理由；非 Hermes 初始化冒名 |
| D6 | 实际功能/协作贡献、本人发现的问题及反思素材；课程 Report 真实身份本人填，不把应用报告混为 D6 |
| D7 | 本地 diff/实际 PR/CI/独立 review；分支保护未生效，明确标注待处理 |
| D8 | history/export 服务、自己的 view、synthetic fixtures、正负/回归与最终导出读回测试 |
| D9 | 根 Prompt 的 Plan 停等、测试/计划/权限批准及分步 Build/Verify 的真实记录 |

第一轮：**A 批准测试/计划，B 独立 review，C 集成**；后续按 [工作计划](../../TEAM_WORK_PLAN.md) 非作者轮换，共同实现者回避。按 [交接清单](handover-checklist.md) 提供实际证据；合同变化按 [集成合同](integration-contract.md) 审批。

S0–S4 是相对检查点，每 sprint 建议 1–2 工作日，不是教师 DDL。Week 13 确切时间、工具/复用/D5 最终口径由学生确认；团队私有仓库 https://github.com/537Lab/PaperTrace 已建立，须先被邀请才能访问；分支保护未生效，不虚构人审或通过记录。本书不授权模型、凭据访问或无人监督开发。
