# PaperTrace｜模块交接与合并检查清单

用途：每位成员在自己的模块 PR/本地交接中逐项提供**真实证据**。本页给出检查语义，不预填任何审批或 PASS。`[ ]` 表示待实际核验，不是空白结论模板。团队私有仓库 https://github.com/537Lab/PaperTrace 已建立，PR 链接须真实；分支保护与 required checks 仍未生效（403），该项明确标注待处理，不能虚构 PR、审批或通过记录。

## 1. 先判断能不能开始审查

- [ ] 认领的是 A/B/C/D/E 中一个完整功能；有本模块业务、自己的 view、需求/设计/测试，不是只有 CI 或文档。
- [ ] 交接说明列出实际改动路径、基线/分支/提交或当前 diff、已做与未做、可复现命令、已知风险，不把任务书中的规划写成已实现。
- [ ] 本次作者、事前测试/计划批准人、独立 reviewer、集成人按轮换安排且不自审；共同实现者不作为该 PR 的独立批准人。
- [ ] 人工批准的计划/测试版本、时间和允许写路径存在，且早于实现；需求或测试语义变化后重新批准。
- [ ] OpenCode 的真实 Plan → 人工批准 → 已确认 Build 权限 → Build → Verify 记录完整；不是无人监督一键完成。

没有这些证据，给出 `CHANGES REQUIRED` 或明确 BLOCKED 的部分，不用完成代码量抵消流程缺失。

## 2. 每个模块的功能交接重点

| 模块 | 至少演示的正向行为 | 必须能复现的阻断/负向行为 | 交给下游的确切对象 |
|---|---|---|---|
| A | 明确选文件、逐项导入状态、生成固定版本 snapshot；同版本可重放 | 同名替换产生新版本；部分失败不称完整；历史不漂移；路径越界拒绝 | CorpusSnapshot、版本/状态核验端口；非可变 PaperQA Docs |
| B | 绑定 snapshot 的 evidence；原文/摘要/locator 分开；第三方映射可观测 | 旧/外来版本拒绝；错误不回退全库回答；无人工 accepted；不导入外来 pickle | EvidenceRecord；按 D 授权的中立生成结果/原始引用/实际发送映射 |
| C | 比较来源，human 接受/排除，ledger 追加、revision/digest 重放 | 无决定是 pending；AI 不可批准；旧 revision 冲突；原文变化不复用旧审 | ReviewDecision 与固定 revision/digest 的一致读取 |
| D | 仅用获准证据，记录 approved/sent/cited，确定性 ReleaseDecision | 空批准零调用；未发证据/未知引用阻断；生成中状态变化阻断；UI 绕过仍有效 | AnswerDraft、ReleaseDecision、关联三集/版本/运行元数据 |
| E | 保存/读回研究链；导出保留来源、审核、状态、版本 | 旧 snapshot 不换最新；blocked 不冒充发布；缺依赖显式不完整；路径穿越不写出 | 不可变历史记录、可核验导出件及其内容摘要 |

所有传输使用真实 `src/papertrace/contracts.py`；发生冲突按 [integration-contract.md](integration-contract.md) 的变更流程处理，不在本模块塞私有 accepted/released 标记兼容。

## 3. D1–D9：每个人必须提供什么

共享仓库负责汇总，但每位成员都要贡献本模块证据；不是把九个交付物分别交给九种角色。

| 交付项 | 模块作者实际提供的内容 | 审查落点 |
|---|---|---|
| D1 需求 | 自己 FR IDs、优先级、可机器检查 fit criterion，关联 `INV-01`–`INV-08`/非功能项；说明需求变化和来源 | `docs/req/requirements.yaml`、schema、trace matrix 的具体条目；不另造 registry |
| D2 架构 | 模块职责、输入输出/失败、依赖/authority、状态寿命、上下文与预算影响；必要 ADR | 蓝图、ADR、invariants、memory、permission、runtime-policy、evaluation/trace 的具体更新；不能只画图 |
| D3 编码治理 | 读过真实 AGENTS/规则的记录、批准路径与工具；新增依赖/核心例外的审批 | `AGENTS.md`、structural-constraints、manifest、`.opencode`/`.agent` 规则；实际引擎权限证据另核对 |
| D4 验证治理 | 事前测试批准；结构/负面/回归/行为结果；真实 bug、debt；独立 verdict | verification-constraints、`docs/review-memo.md`、bug/debt 条目及原始日志；无 bug 不编造 bug |
| D5 真实 session | 原始完整 OpenCode transcript、学生干预标注及理由、计划批准/拒绝/重定向；可定位到本模块实现 | `transcripts/`；不得用 Hermes 初始化记录冒充或事后编写逐字对话；最终数量/命名遵教师确认 |
| D6 过程报告素材 | 实际完成工作、可核对贡献量、遇到的歧义/缺陷/人类发现问题、个人真实反思素材 | 最终 `Report.md` 由学生本人填真实身份/贡献/反思；本页和任务书仍匿名，不虚构相同贡献权重 |
| D7 仓库与门禁 | 实际 PR/commit/CI，失败案例阻断和人审证据；保护未生效如实标注 | https://github.com/537Lab/PaperTrace（非 upstream）；分支保护/required checks 未生效（403），不能拿 workflow 代替 |
| D8 源码与测试 | 模块源码、view、规范合成 fixtures、正负测试、回归、复现输入与依赖 | `src/papertrace/<module>/`、`test/offline/test_<module>.py`、获批 `test/fixtures/<module>/` 精确文件；live 另隔离，上游 `tests/` 不删除 |
| D9 静态启动 Prompt | 从已有根 `Prompt.md` 开始、Plan 停止等待、人工批准版本和后续执行的真实记录 | 不复制成五个互相冲突的启动 prompt；模块专属任务补充不能绕过根规则 |

## 4. 测试与运行证据的最低内容

- [ ] 每个功能至少一个正例和一个负例；每条不变量有故意违反会失败的断言；每个测试标注真实 requirement/invariant ID。
- [ ] 用例断言实际语义：来源版本、集合关系、状态不漂移、输入内容、调用次数、错误原因；不是只检查文件存在、函数返回非空或固定 fake 文本。
- [ ] 对 UI 直接调用、无 UI 服务调用及跨模块数据串用都有边界测试；UI 不拥有第二套授权逻辑。
- [ ] 已运行完整团队离线回归，命令为 `.venv/bin/python -m pytest -c papertrace.pytest.ini test/offline`；保留退出码、实际通过/失败/skipped/收集数及版本。结果看真实输出，不在这里预填数字。
- [ ] 其余 schema/static/dependency/API/permission/log gates 的命令和结果按 [../ci/gates.md](../ci/gates.md) 核查；未执行项标未执行，失败项保留失败原始输出。
- [ ] 确认网络和真实模型在 offline 中被禁用；mock/fake 明示 synthetic。未跑 live 不填 PASS，不用 fake 证明 faithfulness/relevance 达标。
- [ ] prompt/model 变化时，提供固定评估集、批准 provider/model、数据许可、请求/重试与金额上限，以及真实回放结果；没有批准则相应语义 gate BLOCKED。
- [ ] 不把初始化 `.venv`/`requirements-init.lock` 当成已安装 PaperQA2 业务栈；业务依赖与 parser 版本/许可变更有单独审批。

## 5. 接口、状态与安全逐项读回

- [ ] 文献 logical ID、SHA256 version、snapshot 内容 hash 都来自共享算法；没有手改身份、以文件名代版本或复用过期 snapshot。
- [ ] evidence ID/locator/原文与源文献一致；摘要/相关度非权威；无 ReviewDecision 等于 pending。
- [ ] human-only 审核、ledger revision/digest、冲突拒绝与历史重放均验证；前端 session state 不能伪造批准。
- [ ] D 的 approved/sent/cited 来自指定审核投影、实际请求、原始引用；`cited ⊆ sent ⊆ approved`，开始/结束及最终提交的 snapshot/review token 一致。
- [ ] B 每次受控生成新建过滤 session，`get_evidence_if_no_contexts=false`、`pre/post=None`，未复用旧上下文/旧答案、未运行自治 Agent；D 未直接 import `paperqa`。
- [ ] 空获准、预算裁剪后空输入、未知引用、中途撤销/替换、模型失败均不能发布；未发但已批准的引用同样阻断。
- [ ] E 的历史/导出可读回特定原版本与发布原因；blocked draft 清楚标识，未用最新库回填缺失历史。
- [ ] 原版核心/包/tests/pyproject/uv.lock 无未经批准改动；共享合同/入口/锁/治理变更有单独范围批准。
- [ ] 未读取/提交凭据、个人路径、第三方 pickle 索引；输出目录校验、脱敏日志、数据/依赖许可已核查。

## 6. 共享文件、日志与独立 verdict

交接时提供一个短说明，逐条指向以下**真实条目或文件位置**，不用粘贴一大段过程复述：

1. 本次需求 IDs 与原批准计划/测试版本。
2. 修改路径和接口差异；若改合同，附第 8 节变更审批与迁移/兼容证据。
3. 正常操作与最小负例的复现步骤，完整 suite/门禁的原始结果位置。
4. AI-use log 条目、OpenCode transcript、人工干预位置与理由；Hermes 初始化与成员开发贡献清楚分开。
5. 新增 bug/debt/ADR、未解决问题、禁止误认为已完成的项目及下一位需处理的输入。
6. 独立 reviewer 的 `APPROVE` / `CHANGES REQUIRED` / `REJECT` 及阻断理由；集成人核对批准版本与当前 diff 一致。

共享日志由该轮预约编辑者合入各作者的真实条目；不得以避免冲突为由不更新，也不得由集成人编造别人工作。review 发现问题后修复、复跑并保留旧失败，不能删除负例、改阈值或伪造“已审核”。

## 7. 合并/最终提交前的最后一道检查

- [ ] 当前 diff 与批准范围一致，新增外部副作用/工具权限再次获批。
- [ ] 本地证据、六个 CI 检查、非作者人审与安全路径 ADR 对应同一版本；**required checks 尚未启用**（免费套餐私有仓库 403），此项保持未完成并如实标注，不能写成已通过。
- [ ] 集成后的团队完整 prior suite 零回归；live 与真实质量状态没有被离线结果覆盖。
- [ ] 最终包不含 keys、个人缓存、外来索引或未经许可的论文原件；保留上游 attribution/许可证。
- [ ] D1–D9、真实身份/贡献/反思和 transcript 口径由学生本人核对；10 分钟视频与 ZIP 分开准备，教师确切截止已查证再填写。

任何安全 escape、未经审核引用、旧版本冒充当前、伪造审批/transcript 或敏感信息泄露都必须停止合并/发布。已创建文件、已跑离线测试、live 达标、GitHub 保护生效、课程已提交是五种不同事实，最终交接分别报告。
