# ADR-002：单入口、独立 fake 开发与受审上游修复

- **状态：proposed-awaiting-human**；不是学生已批准的决定。
- **范围：**澄清开发启动、A–E 并行边界与 PaperQA2 基线例外流程；不改变 FR/INV、共享模型字段、六类门禁或功能 ownership。
- **权威入口：**[团队启动入口](../../../TEAM_START_HERE.md)；接口以 [`integration-contract.md`](../../team/integration-contract.md) 和真实 `src/papertrace/contracts.py` 为准。

## 问题

旧任务书重复列启动命令、阅读顺序、审批流程和集成细节；B 的上游 adapter 容易被误读成 D 的先决条件；“冻结上游”又可能被解释为即使存在必要缺陷也永不修复。这会增加启动负担、造成模块串行，并使安全例外含混。

## 决定提案

1. **一个启动入口。**`TEAM_START_HERE.md` 是唯一团队入口；README、工作计划和任务书都链接回它。`docs/team/startup.md` 仅作克隆/初始化命令参考。Plan 读根启动规则、本人任务书、相关 registry/contract 与接口合同；架构材料按需查，不设无限串行阅读清单。
2. **拆分 B 的机制与 D 的策略。**B 维护唯一 PaperQA2 adapter 与中立检索/生成端口；D 拥有授权集合、上下文/预算、引用核验和发布门。D 通过能记录最终 payload、调用与 freshness 的 fake port 独立开发，不等 B 完工，也不直接 import `paperqa`。获批 Plan 可列精确只读上游源码路径供 D 核实行为。
3. **fake-first，不把 fake 当 live。**A–E 都可用共享合法合同和自写 synthetic fixtures 开发。fake 必须暴露实际输入、状态、计数与故障；只能验证确定性逻辑，不能证明模型质量、论文许可或远端保护。
4. **普通功能变更保持基线。**固定 tag/commit 是审计基线，由现有 `frozen_check` 保护。一般模块 PR 不改 `src/paperqa/`、`packages/`、原上游测试或依赖锁。必要兼容修复不是永久禁止，但须另开 ADR + 人工 PR，明文更新 `frozen_check` 的 fitness rule/比较口径，提供复现问题、最小 diff、许可/依赖影响、受影响 owner、正负测与受影响回归；只有口头批准不能让当前 CI 通过。不得把修复混进业务 PR 或新增旁路授权平台。
5. **权限仍默认拒绝。**未列路径默认不可读、不可写；白名单按角色与本轮批准计划限定，可使用明确模块目录规则；一次批准范围后，日常编辑、新文件与常用离线命令不逐次审批。必要目录 glob 必须写明边界并验证路径 resolve 后仍在仓库内。没有无条件 allow-all 例外。

## 后果与验收

A/C/E 可在不安装真实 PaperQA2 的情况下推进；D 可先验证零调用、三集合和 freshness；B 仍对唯一上游调用边界负责。接口/安全变化仍按集成合同、需求追踪与 ADR 审核。此 ADR 不预先授权 Build、依赖安装、模型调用、外部网络、权限修改或上游写入。学生接受前不把提案当作批准；无实测时保持 proposed/blocked，不填 PASS。
