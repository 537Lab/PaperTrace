# PaperTrace｜团队唯一启动入口

本文件是新成员、模块作者和协作者的唯一入口。其他文档只解释单项命令、设计或交付规则，不要求按一条无限阅读链通读整个仓库。

PaperTrace 是本地科研证据审核台：**A 文库 → B 检索 → C 人审 → D 受控回答/发布 → E 历史/导出**。业务功能尚待学生分别开发，不要把初始化契约或假数据当成正式应用。

## 1. 加入并验证初始化环境

团队仓库为私有：先请所有者邀请你的 GitHub 账号。克隆、Python/uv 环境及可直接运行的初始化测试命令见[启动命令页](docs/team/startup.md)。初始化依赖不等于 PaperQA2 或 Streamlit 业务环境；安装和 live 调用须另行批准。

## 2. 认领一个完整功能

| 成员 | 长期功能 ownership | 任务书 |
|---|---|---|
| A | 文献库、逐项导入状态、内容版本和不可变快照 | [模块 A](docs/team/module-A.md) |
| B | 候选检索、PaperQA2 唯一适配边界与受控调用端口 | [模块 B](docs/team/module-B.md) |
| C | 原文/摘要比较、人工决定、可重放审核账本 | [模块 C](docs/team/module-C.md) |
| D | 获准/发送/引用集合、预算与确定性发布门 | [模块 D](docs/team/module-D.md) |
| E | 不可变研究历史、来源追溯与 JSON/Markdown 导出 | [模块 E](docs/team/module-E.md) |

任务书是功能验收与无阻塞 fake 路径，不是实现授权。五人工作安排、角色轮换和课程交付见[工作计划](TEAM_WORK_PLAN.md)；共享对象及边界见[集成合同](docs/team/integration-contract.md)。

## 3. 做最小必要阅读，然后停在 Plan

开始模块 Plan 前只读：

1. 根目录 `AGENTS.md` 与 `Prompt.md`（按其中入口执行；不得改写或绕过）。
2. 自己的 `docs/team/module-X.md`、本模块相关的 `docs/req/requirements.yaml` 条目与 `src/papertrace/contracts.py`。
3. `docs/team/integration-contract.md` 中与该模块接口/安全边界相关的部分。

只在问题涉及某条架构决策、权限或验证时，读对应 ADR / `permission-model.md` / `verification-constraints.md`。无需为了启动而通读所有文档、上游测试或个人目录。冲突时记录问题并停下，不自行选宽松解释。

用课程要求的 **OpenCode** 从根 `Prompt.md` 启动 Plan。Plan 必须列需求 ID、数据流/失败策略、正负测试、精确读写路径、工具/依赖/网络需求及 fake 验证方式，然后停止。**监督学生批准计划与一次模块/离线工具范围 → OpenCode 仅准备本模块测试（此时严禁业务实现）→ 非实现者在 GitHub 批准具体测试 commit → 受限业务 Build → Verify。测试提案 PR 可以保持 open/RED；不得合入红测试，也不逐文件反复审批。**

## 4. 独立开发、监督与验证

- 每个模块都有自己的合成合同对象和 fake 适配路径；可先完成服务、视图、边界测试，不等其他模块，也不需要模型。fake 只能证明接口、授权和输入观察，不证明真实模型质量。
- B 独占新增团队代码中的 `import paperqa`，维护上游调用和中立端口；这不是禁止 A/D 在获批 Plan 明列的精确只读路径内审阅上游源码。D 用记录最终 payload 的 fake 端口并行开发自身授权、预算、引用与发布逻辑，不必等待 B 完工，也不能直接导入/调用 PaperQA2。
- 有业务依赖、外呼、prompt、安全语义或共享合同变化时，按任务书/集成合同单独提案审批。安全关键变更须 ADR、至少一个会失败的负测和学生本人审核。
- Build 必须由学生监督 OpenCode，保留真实完整会话和人工干预理由；Hermes 本轮初始化不是学生 OpenCode 贡献或 D5 会话。
- Verify 按真实适用范围运行离线回归和全部六类课程门禁；不能删门、降级、以 `skip` / `NOT_REQUIRED` / fake / 文档存在冒充通过。实时结果见 [`docs/ci/gates.md`](docs/ci/gates.md)。
- 独立审查者不能是作者或共同实现者；PR 与 D1–D9 证据按[交接清单](docs/team/handover-checklist.md)核对。

## 5. 不可妥协的确定性边界

1. 文献逻辑身份、SHA256 内容版本、快照与证据来源身份不可混用；历史不以同名新文件替换。
2. 没有有效 human `ReviewDecision` 即 pending；模型建议、UI 缓存或 `actor_kind="human"` 字段本身不构成真实审批。
3. 无获准证据时，在模型工厂/SDK/HTTP 之前拒绝；不得为生成拒答理由调用模型或让 B 自动补证。
4. 回答的 `cited ⊆ sent ⊆ approved`，且发布前后核对 snapshot 与 review revision/digest；任何变化都阻断旧草稿。
5. 第三方索引、凭据、`.env`、个人目录、未许可论文内容和未经批准网络/模型调用均不进入开发流程。
6. 上游核心由现有 `frozen_check` 固定基线保护，普通模块 PR 不改。确需兼容修复时，须独立 ADR + 人工 PR，明确更新 `frozen_check` fitness rule/比较口径并跑受影响回归；仅口头批准不能让当前 CI 通过。不新增旁路授权平台。

课程尚待学生核实的事项包括 D5“五份 annotated”与“一份完整 raw/from-scratch”口径、基线复用边界、确切截止时间及最终交付格式。D6 身份、相对贡献（平均 1.0）和真实反思由学生本人填写；10 分钟 demo 与 ZIP 分开。不要替学生补写或宣称课程已完成。
