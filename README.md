# PaperTrace

**Evidence Review Workbench**：在本地整理获准文献，检索候选证据，由人审核后受控生成回答，并保留可追溯历史。PaperTrace 扩展固定的 PaperQA2 基线，不重新实现检索引擎，也不把模型输出当作人工批准或科学事实证明。

## 开始

新成员、协作者和贡献者统一从 **[团队启动入口](TEAM_START_HERE.md)** 开始。仓库为私有，须先由所有者邀请。启动命令、环境边界和待单独批准的 PaperQA2 运行依赖见入口链接的命令页。

## 五个功能

A 文献库与版本 → B 检索与 PaperQA2 适配 → C 原文比较与人工审核 → D 获准证据回答与确定性发布门 → E 研究历史与导出。每个功能由成员完整负责需求、设计、受监督开发、正负测试、自己的界面与 PR；过程审查/集成角色轮换。分工和计划从[统一入口](TEAM_START_HERE.md)进入。

## 当前工程边界

- 五个业务模块尚待成员实现；文档、契约或测试通过不能当作可运行的正式 Streamlit 应用。
- 唯一上游 PaperQA2 集成边界归 B；D 通过中立端口和 fake 先独立开发自身授权、预算、引用与发布逻辑。
- 没有人审决定时证据为 pending；无获准证据时生成调用数必须为零；可发布回答要求 `cited ⊆ sent ⊆ approved`，并通过快照/审核版本新鲜度检查。
- 默认按路径拒绝读写。任务书里的候选目录不是自动授权；每轮 Plan 须列出精确文件和工具权限并由非作者批准。
- 上游核心由现有 `frozen_check` 固定基线保护，普通模块 PR 不改。必要兼容修复须独立 ADR + 人工 PR，明确更新 `frozen_check` fitness rule/比较口径并跑受影响回归；口头批准不能让当前 CI 通过，不新增旁路授权平台。
- 六类课程门禁不删减、不降级、不以 `skip` 或文档存在冒充通过。真实状态以 `docs/ci/gates.md` 和验证证据为准；远端强制保护须经真实配置和阻断演练验证。

## 目录索引

- [五人工作计划](TEAM_WORK_PLAN.md)：固定 ownership、协作轮换、D1–D9 与六类门禁。
- `docs/team/module-A.md` … `module-E.md`：五份可认领、可 fake 独立开发的功能任务书。
- `docs/team/integration-contract.md`：共享模型、模块交接和契约变更规则。
- `docs/architecture/`、`docs/req/`、`docs/code-governance/`：架构、需求和治理事实源。
- `docs/ci/gates.md`、`INITIALIZATION_STATUS.md`：真实验证状态，不从 README 推断状态。
