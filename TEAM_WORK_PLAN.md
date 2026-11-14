# PaperTrace｜工作计划与协作规则

> 新成员从[团队唯一入口](TEAM_START_HERE.md)开始。本文件集中说明 ownership、角色轮换、课程证据和门禁；模块技术验收在各自任务书中。

## 1. 目标和当前范围

PaperTrace 是本地科研证据审核台：导入授权文献、检索候选、由人审核、仅用获准证据回答，再保存可追溯研究历史。本轮建立的共享契约/测试/治理基础不是五模块业务，也不证明已有可运行的 Streamlit 正式应用。所有实现、审批、OpenCode 会话、模型评估和远端保护须分别以实际证据记录。

固定上游为 `Future-House/paper-qa@c692d0dfeac4a0296599f7fe21a253a58b7ac12a`。普通功能 PR 不改其 `src/paperqa/`、`packages/`、原 `tests/`、`pyproject.toml`、`uv.lock`；这不是永久禁止必要修复。例外须走 [ADR-002](docs/architecture/adr/002-development-readiness.md) 的受审 patch 流程，不裸改、不绕过任何测试/权限门。

## 2. 五项功能 ownership 与并行接口

| Owner | 端到端 Must 功能 | 边界与交接 |
|---|---|---|
| A | 文献导入状态、逻辑身份、内容 SHA256 版本、不可变快照 | 输出 ready-only `CorpusSnapshot`；不 import `paperqa`，不替 C 审核 |
| B | 检索候选、原文定位、PaperQA2 薄适配、受控调用/中立端口 | 团队唯一 `paperqa` import；不授予人审或发布权 |
| C | 原文与摘要比较、明确人工接受/排除/重置、追加审核账本 | 输出可重放决定与 revision/digest；模型和 UI 状态不授权 |
| D | 获准/实际发送/实际引用三集、受控回答、确定性发布门 | 自己拥有回答和 release；通过 B 端口执行，零获准时零工厂/SDK/HTTP 调用 |
| E | 研究历史、来源追溯、JSON/Markdown 导出 | 读回原 snapshot/审核/回答/发布状态；不覆写历史、不升级授权 |

共享模型唯一事实源是 `src/papertrace/contracts.py`。接口细节和错误语义见 [`docs/team/integration-contract.md`](docs/team/integration-contract.md)，需求/阈值见 `docs/req/requirements.yaml`，不要在任务书造第二份 registry。

### 可并行的 fake 开发路径

先用 `test/fixtures/contracts/` 规范对象和各模块自写的 synthetic fixtures；共享 wrapper 的 `data` 才是模型输入。每个模块的关键 fake 及其可观察断言已列在任务书中：A fake parser/import port；B fake parser/retrieval/generation adapter；C fake candidate feed（不能返回权威 accepted）；D 记录最终输入和 attempt 计数的 fake generation port，且不依赖 B 完工；E 合法/blocked/abstained/failed 合成研究包。

所有 fake 和材料都标记 synthetic，仅证明确定性接口、授权、失败和输入边界，不证明真实模型质量、许可或性能。B/D 真实 PaperQA2 离线集成与依赖、provider/model live 调用分别审批。D 可在其 Plan 精确列出的只读路径内审阅上游 API 行为，但不能直接导入 `paperqa`。

## 3. 最小工作流与权限

每个功能作者对需求、设计、监督 OpenCode、正负测试、自己的 view、PR 和演示负责；无“只写文档”成员。

1. **Plan：**按唯一入口中的最小阅读集，列真实 FR/INV、输入/输出/失败、精确相对路径、fake 测试、依赖及副作用；停止等待审批。
2. **先审后写：**监督学生批准计划后，OpenCode 仅准备模块测试/fixtures/设计记录，不写业务源码；测试提案 PR 可保持 open/RED。另一名未参与实现的同学在 GitHub 批准具体测试 commit 后，才写业务实现；一次确认本轮模块范围（可含明确目录规则及其新文件）和常用离线工具。范围内不逐文件/逐命令再批；扩到共享、其他模块、依赖、网络或费用时才重新确认。配置仍默认 `R=deny, W=deny`，显式白名单限定范围，不配置无条件 allow-all。
3. **监督 Build：**学生本人使用课程要求的 OpenCode，逐步检查、干预并记录理由。需求、接口或安全语义改变，回到审批；不能先实现后补批准。
4. **Verify：**保存真实命令、版本、退出码、范围与原始结果；跑相关负测、团队 offline 全 suite 与完整 prior regression。初始化 `.venv` 的 `test/offline` 只属于第一类，不是 full regression；三来源/collection parity/live BLOCKED 规则见 [`verification-constraints.md`](docs/code-governance/verification-constraints.md) 和 [`full-regression.md`](docs/ci/full-regression.md)。真实适用状态以 `docs/ci/gates.md` 与验证证据为准。
5. **独立 PR：**非作者 reviewer 核查 diff、测试、权限、AI-use log、bug/debt、ADR 和 D1–D9。真实 GitHub 合并与保护另行验证。

**每个 feature 都要有可定位的 requirement/invariant trace 和至少一个能在边界被破坏时失败的负测。**审核权威、来源身份、生成/发布、预算、权限、上游补丁、历史状态等安全关键改动须 ADR、负测、受影响 owner 和学生本人审查。人审后的规则变化须在一个 sprint 内同步；`.opencode/rules.md` 为 human-only，代理不可自改。

## 4. D1–D9 个人证据

每位成员仅提供自己模块实际发生的证据；规划内容不算已完成项。课程原文与待确认口径见 [`docs/sources/course-compliance.md`](docs/sources/course-compliance.md)。

| 交付 | 每个模块作者要留下的真实证据 |
|---|---|
| D1 需求 | Must FR、registry fit criterion、关联 INV/质量项、来源与测试追踪；不得另造需求表 |
| D2 架构 | 本模块职责、接口/失败/状态/预算影响及必要 ADR；安全关键决策须人审 |
| D3 编码治理 | 本轮精确路径/权限/工具、human-only 规则和边界验证；不宣称未执行的权限强制 |
| D4 验证治理 | 事前批准版本、正负/回归结果、独立 review memo、真实 bug/debt |
| D5 OpenCode 会话 | 学生监督形成的原始完整会话及真实人工干预。课程 p2“五份 annotated”与 p6 “一份 full raw/from scratch”口径须学生/教师核实；Hermes 初始化不能冒充 |
| D6 过程报告 | 本人真实功能、可核对贡献和反思素材；最终身份由学生填。原文要求平均贡献 1.0、最多 10,000 词（不计图）、12pt 单倍行距超过 15 页；排版/交付由学生核实 |
| D7 仓库/门禁 | 真实本地 diff、PR/CI、人审及保护阻断证据。私有仓库分支保护此前因 403 未生效；最终须重新回读和演练，不能标已完成 |
| D8 源码/测试 | 本模块业务源码、自己的 view、合成 fixtures、正负/回归测试与可复现命令 |
| D9 静态 Prompt | 从同一根 `Prompt.md` 真实启动，Plan 停止并等待测试/计划/权限批准，保留执行记录；不复制冲突 prompt |

**10 分钟 demo 单独提交，不放进 ZIP。**Introduction p20 要求学生真实监督 OpenCode；教师确切截止时间仍须查最新课程通知。不要虚构身份、贡献、批准、transcript、模型结果或 CI 结论。

## 5. 过程角色轮换（不转移功能 ownership）

作者/共同实现者不能批准自己的测试或独立审查自己的 PR。事前测试批准者与最终 reviewer 可以是同一名非实现者；集成人可按实际空闲轮值，不要求每个小 PR 召集四名同学。下表是可选的首轮分担，不是额外门禁。

| 功能作者 | 首轮测试/计划批准 | 独立 reviewer | 集成人 |
|---|---|---|---|
| A | B | C | D |
| B | C | D | E |
| C | D | E | A |
| D | E | A | B |
| E | A | B | C |

后续可沿 A→B→C→D→E 顺移，缺席时由其他非实现者替补批准/审查；仅在独立性冲突时另排。不能把某人永久设为 CI/管理负责人。

## 6. 六类课程门禁（完整保留）

教师 Project p10 的六类门禁不可删、降级、用假结果替代，或因本轮未实现而标绿。每轮按真实适用条件分别报告：

1. 实现前测试批准；
2. 静态分析、类型/依赖及安全路径检查；
3. 需求 schema；
4. prompt/model 变化的真实语义评估；
5. 完整 prior regression；
6. 代码/prompt 变化对应的真实 AI-use log。

`NOT_REQUIRED`、skip、fake、文档中有 gate 名称或本地检查 ≠ 课程门禁通过；真实模型评估未获批/未执行须 BLOCKED。GitHub required checks/安全路径保护只有完成授权配置、读回并通过违规/合法对照 PR 演练后才可称生效。当前运行状态不在本文件复制，统一读 `docs/ci/gates.md`。

## 7. 可裁剪范围与未决事项

资源不足时先裁剪非 Must 的 UI 润色、自动化、多用户、云端、复杂报告平台，不减 D1–D9、六门禁、人工审批、确定性安全边界或真实证据。

仍需学生确认：OpenCode/复用 PaperQA2 的边界、D5 transcript 口径、Week 13 的确切日期/时区及正式提交要求。课程介绍另要求 10 分钟 demo，单独于 ZIP；不得猜日期。
