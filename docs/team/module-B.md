# 模块 B｜检索、PaperQA2 适配与中立端口

> **Owner B：**端到端负责检索功能、薄适配、错误呈现、自己的 view、监督开发、测试与 PR。B 独占团队新增代码中的 `import paperqa`，不是只给 D 写调用工具。
>
> 统一从[团队启动入口](../../TEAM_START_HERE.md)进入；共享接口以 [`integration-contract.md`](integration-contract.md) 与真实 contracts 为准。

## 用户结果与责任

研究者选固定文库快照并提问，看到绑定原文、版本、locator 和明确状态的候选证据；空结果、解析错误、超时和调用失败可区分。B 提供 `EvidenceRecord` 和 D 授权的机械生成端口，**不授予人工接受或发布权**。

B 维护 PaperQA2 适配、检索/生成 port、上游调用选项与真实发送/尝试观测。A 的摄取状态归 A；`approved`、prompt/预算/裁剪策略和 release 归 D。B 不把 `Context.id` 当团队身份，不给 D 传递可变 `Docs`/`PQASession`。

## Must 与可验收结果

| 需求/不变量 | 必须行为与验收 |
|---|---|
| `FR-B-01`, `INV-02` | 每条候选绑定 snapshot/doc/version；原文与 advisory summary 分开；locator 为可核的 1-based inclusive 页/行范围，并有 chunk/parser 名称与版本；身份用共享实现。 |
| `FR-B-02`, `INV-08` | 空集与执行失败分开；超时/解析错误/尝试数有记录；重试有界且经批，不静默切模型；拒绝不可信第三方 pickle 索引并逐项审查许可。 |
| `FR-D-03`, `INV-01/03/04/07`（与 D 协作） | 只按 D 批准的证据/配置执行；返回最终实际 sent、raw 输出与无歧义别名映射；不自动补证、不作审核、不发布。D 的空批准分支不进入 B 生成端口。 |
| `COST-01`, `SEC-01`, `QA-01` | 默认不触发模型/网络；真实依赖、parser、embedding 和 live 请求分别批准与计量；无凭据/个人目录/未许可全文。 |

当前 contracts 要求 `EvidenceRecord` 无 accepted/status 字段；上游 `Context.id` 不是来源身份。拿不到真实可验证 locator 时明确失败，不猜行号或 offset。

## 边界与拟议改动范围

- 新增业务代码中只有 B import `paperqa`，调用经 adapter/port 集中；A 的受控摄取与 D 的生成均不得另开旁路。底层上游源码默认只读；必要修复走 ADR-002，不属于一般 adapter PR。
- **常规模块范围（在 Plan 一次确认；范围内日常编辑/新增文件不逐次批准）：**`src/papertrace/retrieval/`（adapter、port、调用账目与 view）、`test/offline/test_retrieval.py`、`test/fixtures/retrieval/`。共享 contract、CI、锁/依赖、prompt、入口编排及其他模块目录另批。
- PaperQA2 真实依赖/许可与离线适配为独立门；provider/model、数据、请求次数、重试、费用和 deadline 又须单独批准。不能把初始化工具环境说成业务环境。

## Fake-first 与 PaperQA2 特有风险

D 无须等待 B：D 通过 fake generation port 测自己的最终 payload 和调用计数；B 的 fake adapter 测 synthetic source/Context 到 `EvidenceRecord` 的映射。fake 必须记录其实际输入与尝试，不返回一个固定 `"OK"` 逃避边界检查。

至少验证：跨 snapshot/版本/定位错误被拒；摘要变化不改变身份；原文/locator 可回查；空集、超时、解析错误区分；模型高分或恶意 excerpt 不写审核账本；未知引用 raw 输出及映射交 D；D empty-approved 调用前工厂/SDK/HTTP 计数均为零。

真实上游 Plan 须核实且测试 `Docs.aadd`、`aget_evidence`、`aquery` 及隐式 citation inference/enrichment、embedding、空 contexts 补证、pre/post 和 session 复用风险。生成 adapter 必须使用新建且仅含 D 所选 contexts 的 session，显式关闭自动补证与 `pre/post`，返回 raw 及最终 serializer 后的真实 sent。依赖集成没跑就标未验证；fake 不代表模型质量。

## D1–D9：B 应留下的模块证据

| 项 | 本模块证据 |
|---|---|
| D1 | `FR-B-01/02`、`INV-02/08` 与 D 协作项的 fit/测试映射。 |
| D2 | 唯一 adapter/port、locator/身份映射、隐式调用清单、预算/失败策略与必要 ADR。 |
| D3 | B 的精确写路径及上游只读清单、依赖/许可和实际工具权限证据。 |
| D4 | 事前测试批准、异常/输入截获/调用计数负测、真实上游离线集成范围和 review memo。 |
| D5 | 学生监督形成的 OpenCode 原始完整会话与人工干预；Hermes 初始化不能冒充。Transcript 口径由学生/教师确认。 |
| D6 | 本人真实 adapter、功能与协作贡献及反思素材；身份由本人填写。 |
| D7 | 本地 diff/PR、真实 CI 和独立审查；分支保护先前 403 未生效，最终状态须重查。 |
| D8 | retrieval 服务/view、synthetic fixtures、spy/异常/正负回归及真实依赖集成记录。 |
| D9 | 从根 `Prompt.md` 的 Plan 停止点开始，保留测试/计划/权限批准和监督执行记录。 |

不把 adapter 类存在、包安装成功或 fake 回答称为功能验收或真实语义 PASS。