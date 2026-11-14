# 模块 D｜获准证据回答与确定性发布门

> **Owner D：**端到端负责 answer 功能、调用授权、上下文/预算、引用核查、发布门、自己的 view、监督开发、测试与 PR。B 维护唯一 PaperQA2 底层 adapter；D 仍拥有回答和发布策略。
>
> 统一从[团队启动入口](../../TEAM_START_HERE.md)进入；共享模型/交接以 [`integration-contract.md`](integration-contract.md) 与 `src/papertrace/contracts.py` 为准。

## 用户结果与责任

研究者针对指定问题、文库快照和 C 的人审版本请求回答。D 从真实 ledger 投影计算 `approved`，确定预算/顺序/裁剪并记录最终 payload 的 `sent`，从 B 返回的 raw output 解析 `cited`；只有 freshness 和确定性发布门都通过，才作为发布候选。无获准证据时解释拒答，但**不调用模型来生成拒答**。

| 集合 | 定义与权威 |
|---|---|
| `approved` | 对指定 question/snapshot/revision 有效的人审 accepted 全集；来源 C 的可信投影，不取自模型或 UI。 |
| `sent` | 裁剪、序列化后实际进入本轮请求的证据；必须由最终 payload/调用记录重建。 |
| `cited` | 从原始输出可靠解析并映射的真实引用；未知 key 不得被格式化器静默清除。 |

硬约束：`cited ⊆ sent ⊆ approved`。集合关系不是语义支持证明；answer 被引用不等于科学主张已被原文证实。

## Must 与可验收结果

| 需求/不变量 | 必须行为与验收 |
|---|---|
| `FR-D-01`, `INV-01/03` | approved 为空时不进入 B 生成 port、模型工厂、SDK 或 HTTP；四层 attempt 计数均为零。不得先建模型再让上游拒答，也不得为拒答说明调用模型。 |
| `FR-D-02`, `INV-04/05` | 引用只能来自本轮实际 sent 且仍有效 approved；开始/返回/提交前核对 snapshot 与 review revision/digest，变化即 blocked。坏引用保留诊断，不删掉后伪装 released。 |
| `FR-D-03` | 受控 B port 仅执行经 D 筛选输入的机械调用；新 session、禁自动补证/pre/post/Agent；raw output、最终 sent 和引用 key 映射可查。D 本身不 import `paperqa`。 |
| `INV-07`, `COST-01` | 按 registry 的拟议 cap 12,000 输入、9,000 触发压缩、2,000 输出处理；最终计数包含模板/系统信息并适配获批模型窗口。重注入身份/约束；超限或裁剪后无 sent 则零调用。 |

真实 v1 contracts 只允许 AnswerDraft `draft/abstained/failed` 与 ReleaseDecision `released/blocked`；`stale` 是 blocked 原因/标签，不自行加枚举。revision 0 只用于合约允许的 abstained/failed 与 blocked，不伪造审核事件。

## 边界与拟议改动范围

- D 决定授权输入、预算/上下文、prompt 版本、回答与发布；B 执行受控 adapter，提供 raw/sent/mapping/调用账目；C 提供人审投影；A/E/应用编排为 freshness 与最终写入提供获批接口。D 不写 C ledger、不调用 A 私有文件、不决定 E 的历史内容。
- **常规模块范围（在 Plan 一次确认；范围内日常编辑/新增文件不逐次批准）：**`src/papertrace/answer/`（纯规则、控制服务与 view）、`test/offline/test_answer.py`、`test/fixtures/answer/`。模块 prompt、共享 contract、app 编排/临界区、CI、依赖/锁涉及范围扩大时审批；已批准模块范围内不重复索取逐文件授权。
- 可在获批计划中只读检查精确 `src/paperqa/` 源文件以核实 `aquery`/序列化行为；不得直接 import/调用 PaperQA2。上游修复不属于普通 D PR，走 ADR-002。

## 不等 B 的 fake 开发与验收

先用合法 snapshot/evidence 和 synthetic C ledger，注入**会记录 payload、初始化、SDK/HTTP attempt、返回 raw 与可控 freshness token**的 fake generation port。该路径允许 D 独立实现和测试；不需真实 PaperQA2、provider 或模型。fake 不得只返回固定“OK”。

至少验证：无决定/仅 AI 建议/全排除 → 各层调用零；一条合法 accepted → sent 精确；approved 多于 sent、引用未发送但已批准、排除/pending/未知 key 均阻断；raw 未知引用保留；自动补证/pre/post/旧 session 不出现；压缩/裁剪边界和重注入；生成中及最终保存前改变 snapshot/revision 都阻断；超时/截断/空答/坏 ledger 无 released；服务直调也执行相同边界。未通过真实 fixed evaluation 不宣称 faithfulness/relevance PASS。

## D1–D9：D 应留下的模块证据

| 项 | 本模块证据 |
|---|---|
| D1 | `FR-D-01/02/03`、`INV-01/03/04/07` 的集合、预算与错误 fit/测试映射。 |
| D2 | 三集来源、上下文/压缩与新鲜度/提交策略；安全关键决定的 ADR。 |
| D3 | answer/prompt 的精确写路径、上游精确只读清单、B 唯一 import 边界与实测权限。 |
| D4 | 事前批准、payload/attempt spy、引用/竞态负测、团队回归、真实语义状态与 review memo。 |
| D5 | 学生监督的完整原始 OpenCode 会话及授权/引用干预理由；Hermes 初始化不是 D5。份数口径待学生/教师确认。 |
| D6 | D 的真实功能/协作贡献与反思素材；身份/比例由学生填写。 |
| D7 | 本地 diff/真实 PR/CI/独立审查及远端保护读回；之前 403 未生效，须重查。 |
| D8 | answer service/view、synthetic fixture、payload/竞态 spy、正负/回归及可复现步骤。 |
| D9 | 根 `Prompt.md` 的 Plan 停止、测试/计划/路径批准与监督执行记录。 |

验收必须有非 UI 的零调用负测、真实 payload 观察和最终 freshness；schema 自身通过、UI 按钮隐藏、模型自报成功都不构成发布安全证明。