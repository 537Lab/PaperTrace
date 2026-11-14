# 模块 C｜原文比较、人工审核与追加式账本

> **Owner C：**端到端负责 review 功能、自己的 view、需求/设计、监督 OpenCode、测试与 PR。此任务书不是授权记录；业务仍待成员实现。
>
> 统一从[团队启动入口](../../TEAM_START_HERE.md)进入；字段事实源是 [`integration-contract.md`](integration-contract.md) 和真实 contracts。

## 用户结果与责任

研究者能对同一问题/快照比较至少两条独立来源，清楚看到原文、AI 摘要、版本/定位和审核理由；只能通过明确的人类操作接受、排除或重置；决定可重放，旧事件不覆盖。没有有效决定就是 pending。

C 唯一负责人工审核权威及追加 ledger。`actor_kind="human"`、匿名 `reviewer_ref` 等 schema 字段只是形状，不证明真人身份；本产品是本机单人流程，不承诺对抗恶意本机管理员。任何 fake/model/import/UI cache 均不能写权威 accepted。

## Must 与可验收结果

| 需求/不变量 | 必须行为与验收 |
|---|---|
| `FR-C-01`, `INV-03/05` | 明确 human 命令追加 `accepted/excluded/pending` 决定；理由非空、scope 对应 question/snapshot/evidence；revision 单调递增、digest 可重算；冲突/伪造/损坏拒绝且 fail closed。重置追加 pending，不删除旧事件。 |
| `FR-C-02`, `INV-02` | 同时比较 ≥2 来源；文献版本、locator、原文、摘要和理由均可见；相似/相反 evidence 保持不同身份；展示/排序/刷新不改 ledger。 |
| `INV-04/06`, `QA-01`, `SEC-01` | 决定绑定固定 snapshot/question；旧决定不迁移到新文献；绕过 view 调服务仍受同一 human/scope/revision 校验；匿名材料不记真实身份。 |

空账本 revision 为 0、没有 accepted；具体 digest/重放/幂等/原子写策略须在 Plan 设计并批准，不从 UI 缓存补权限。

## 边界与拟议改动范围

- 接 B/A 的 `EvidenceRecord`、`CorpusSnapshot` 与受限原文读取；向 D/E 提供指定 question/snapshot 的可重放投影和 token。D 是发布权威；C 不决定 release，不直接改 A/B/E 文件。
- **常规模块范围（在 Plan 一次确认；范围内日常编辑/新增文件不逐次批准）：**`src/papertrace/review/`（ledger 服务与 view）、`test/offline/test_review.py`、`test/fixtures/review/`。共享合同/fixture、需求/trace、app 编排、依赖/CI 与治理日志另批。
- `.opencode/rules.md` 是 human-only，AI 不得修改；不读真实 `.env`、论文、历史或个人目录，不调用模型/网络。

## 不等 B/D 的 fake 开发与验收

用共享规范 `EvidenceRecord`/`CorpusSnapshot` 和自写两条相反观点加一条无关观点的 synthetic evidence；fake candidate feed 只能产生候选，永不返回有权威的 accepted。先实现纯服务/重放，再由 view 调同一服务，避免复制状态机。

至少验证：无决定/模型建议都 pending；human 接受/排除/重置产生正确事件与 revision/digest；重复提交/排序/刷新不重复授权；伪造 human/import accepted 拒绝；旧 revision 冲突不覆盖；坏 digest/跨 question/snapshot 拒绝；相似内容不合并；service 直调不能绕过；新决定会让旧 D draft 失效。全程零模型调用，合成操作不能伪装真实审批记录。

## D1–D9：C 应留下的模块证据

| 项 | 本模块证据 |
|---|---|
| D1 | `FR-C-01/02`、`INV-03/04/05` 的 fit criterion、测试与 trace。 |
| D2 | Human-only 权威、ledger 追加/重放、revision/digest、冲突/幂等/坏账本策略与必要 ADR。 |
| D3 | 本轮精确路径/工具权限及服务层 human/scope 边界；不把客户端字符串当身份认证。 |
| D4 | 事前批准负测、service/UI 一致、全回归、独立 review memo 与真实 bug/debt。 |
| D5 | 学生监督 OpenCode 的真实完整原始会话和干预理由；不得用 Hermes 初始化充数。课程份数口径待确认。 |
| D6 | 本模块真实功能/协作贡献、发现与反思素材；最终身份由本人填写。 |
| D7 | 本地 diff/PR、真实 CI/独立审查；先前远端保护 403 未生效，最终须核实。 |
| D8 | ledger/投影、比较 view、synthetic fixture 及正负/回归复现。 |
| D9 | 根 `Prompt.md` 的 Plan 停点、测试/计划/路径批准和监督执行记录。 |

验收要求真人交互边界的真实服务测试；按钮 disabled、手写 accepted JSON 或模型建议均不算通过。