# 结构约束（D3）

依据：ADR-001、提案 ADR-002（均待学生批准）；`INV-01`–`INV-08`；课程 Project p5–6。本文规定目标结构，不声称业务模块或工具权限已经实现/强制。

## 模块职责

- A `library/`：导入状态、逻辑身份、SHA256 版本与不可变快照；只含 ready 文献进入共享快照。
- B `retrieval/`：唯一 PaperQA2 适配、检索/生成中立端口及受控调用计量。
- C `review/`：真实人工命令、追加账本与 revision/digest；结构字段不能自证 human。
- D `answer/`：approved/sent/cited、确定性上下文/预算、引用与 freshness 检查及唯一发布判断；依赖可观察的 fake B port，不能直接导入 `paperqa`。
- E `reports/`：不可变研究历史与许可范围内的导出，不改 A/C/D 权威状态。
- `contracts.py` 是唯一共享数据边界，不成为第六个业务模块；薄 view 只展示/收集操作，入口不复制授权规则。

叶子模块不得循环 import，不直接 import 邻居的私有实现。各模块通过获批的中立端口和五个共享模型交接。只有 B 可在团队新增业务代码中 import `paperqa`。用户界面或 `session_state` 不是人审账本、当前快照或 release 的权威。

## 可追踪结构

每项 Must 功能与安全关键约束需关联真实 `FR-*` / `INV-*`、至少一项可定位测试以及模块任务书/trace。每个 feature 至少一个负测；破坏目标边界时测试必须失败。安全关键语义（审批权威、来源身份、模型出站/预算、发布门、权限、历史）变化须 ADR、受影响 owner 与学生本人审核，不能只靠改实现或测试变更生效。人审通过的需求/规则变更须在一个 sprint 内同步到相关需求、架构、测试、权限和 prompt。

## 基线与例外

上游 `src/paperqa/`、`packages/`、原 `tests/`、`pyproject.toml` 与 `uv.lock` 在普通功能 PR 中保持固定基线，由现有 `frozen_check` 保护；不是永久不可修。必要兼容修复须独立 ADR + 人工 PR，明文更新该 fitness rule/比较口径，列问题、最小差异、许可/依赖与受影响范围，并运行负测和受影响回归。仅口头批准不应使当前 CI 通过，也不增设旁路授权平台。

**权限默认拒绝：**每条未批准路径均 `R=deny, W=deny`。功能 ownership 或任务书候选目录不是写授权；本轮 Plan 必须列精确相对文件、工具及创建文件，并经非作者批准。权限边界见 [`permission-model.md`](../architecture/permission-model.md)，实际工具/版本证据另行记录；结构检查不等于 OS 沙箱。
