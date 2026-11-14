# 模块 E｜研究历史、来源追溯与导出

> **Owner E：**端到端负责 reports/history/export 用户功能、自己的 view、需求/设计、监督 OpenCode、测试与 PR；不是只写课程材料。此任务书不是业务实现或授权记录。
>
> 统一从[团队启动入口](../../TEAM_START_HERE.md)进入；合同细节见 [`integration-contract.md`](integration-contract.md) 与真实 `src/papertrace/contracts.py`。

## 用户结果与责任

研究者可保存一次成功、被阻断、拒答或失败的研究过程；关闭重开后仍能定位当时的 snapshot、来源、审核与发布状态；导出 JSON 和 Markdown。文献后来换版时，旧研究保留原内容并标记 superseded，而不是用当前库回填。

E 负责版本化研究记录封装、不可变历史、回读和导出。共享的五种模型保持唯一字段/枚举事实源；E 不重生答案、不改 C ledger、不依据外来 bool/按钮把 blocked 升级为 released。缺原件要显示缺失，不用同名文件替换。

## Must 与可验收结果

| 需求/不变量 | 必须行为与验收 |
|---|---|
| `FR-E-01`, `INV-02/04` | 保存/跨会话回读问题、snapshot、证据/定位、人审记录与 token、approved/sent/cited、AnswerDraft 和 ReleaseDecision；JSON 能重新解析；Markdown 与 JSON 表达同一来源和状态。 |
| `FR-E-02`, `INV-05/08` | 历史只追加；换版只显示 superseded，不改旧记录。默认导出不含凭据、本机绝对路径、未经许可全文或模型私有推理；路径越界/符号链接逃逸/写失败不损坏历史。 |
| `QA-01`, `SEC-01` | 使用真实模型字段和枚举；schema 版本/未知字段策略明确；合成敏感 sentinel 可测脱敏，不扫描私人目录。 |

历史包是后续版本化封装，须在 Plan 和相关生产者/消费者共同审核后确定，不往 frozen 模型加私有字段。当前 AnswerDraft 仅有 `draft/abstained/failed`，ReleaseDecision 仅有 `released/blocked`；`stale/superseded/incomplete` 是封装/展示语义，不擅改传输枚举。缺 usage/费用记 unknown，不补零。

## 边界与拟议改动范围

- 接 A/B/C/D 的原版本对象与审核 ledger；最终一致性提交由获批应用编排/D/E 共同设计，E 负责存储/读回/导出，不另造发布门。
- **常规模块范围（在 Plan 一次确认；范围内日常编辑/新增文件不逐次批准）：**`src/papertrace/reports/`（存储、读取、exporter 与 view）、`test/offline/test_reports.py`、`test/fixtures/reports/`。record envelope 对外接口、共享模型、A/C/D 端口、入口/锁/编排、依赖/CI 和治理日志另批。
- 不写 A 文库/C ledger/D 发布门，不读取 `.env`、密钥、真实私人论文/历史，不擅自联网或引入大型数据库/云服务。

## 不等 A–D 的 fake 开发与验收

用规范五模型和自写 synthetic 完整 released、blocked、abstained、failed 记录；fixture 明示 synthetic，不假装真实人审、OpenCode 会话或模型输出。假数据只在测试临时输出目录内读写。

至少验证：保存/关闭重开/JSON roundtrip；JSON/Markdown 必要字段与 evidence/locator 无错配；换版后旧内容 hash 不变；blocked/abstained/failed 保持未发布；缺对象/错关联/坏 digest/未知 schema 不补齐成成功；路径穿越、symlink、冲突、写中断/磁盘失败无范围外写、无破坏旧包；合成敏感值、绝对路径、未许可全文标记不进入导出。外部读取/导出许可要分开验证，不因 Apache-2.0 根许可证而假设论文可分享。

## D1–D9：E 应留下的模块证据

| 项 | 本模块证据 |
|---|---|
| D1 | `FR-E-01/02`、`INV-02/04/05/08` 的导出/历史 fit、测试与 trace。 |
| D2 | 版本化封装、不可变存储/恢复、许可字段白名单、与 D 的最终提交边界及必要 ADR。 |
| D3 | reports 与导出目标精确路径/工具授权、路径保护与冻结基线/例外证据。 |
| D4 | 事前批准、跨会话/脱敏/路径/中断负测、团队回归和独立 review memo。 |
| D5 | 学生监督 OpenCode 的真实完整原始会话与历史/许可干预；Hermes 初始化不算成员开发。Transcript 口径待核实。 |
| D6 | E 的真实业务/协作贡献和反思素材；正式身份/贡献由本人填写，不能以课程文档替代功能。 |
| D7 | 本地 diff、真实 PR/CI/独立审查及分支保护读回；之前保护 403 未生效，须重查。 |
| D8 | history/export 服务/view、合成研究包、正负/回读测试和复现步骤。 |
| D9 | 根 `Prompt.md` 的 Plan 停点、事前测试/计划/路径批准及监督 Verify 记录。 |

验收从最终导出件读回核字段/状态；不能只检查“导出成功”提示或生成几份 Markdown 示例。