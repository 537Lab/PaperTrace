# 模块 B Plan v2.1 本人批准记录

- 日期：2026-11-18
- 批准人：李亚飞（模块 B 负责人）
- 对象：`docs/team/designs/module-B/plan-v2.1.md`
- 记录来源：本人监督的当前 Codex 聊天
- 结论：**APPROVED FOR B0/B1**

本人原文：

> 我批准 Plan v2.1 的 B0/B1/B2 范围和精确路径；批准第 7.1 节离线命令；批准第 7.2 节仅为锁定依赖下载和离线 PaperQA2 smoke 使用有限网络；确认不修改共享 contracts、上游和其他成员模块；同意 Streamlit 总入口另走集成计划。

## 生效边界

- 本批准允许执行 B0 离线 smoke，并允许随后使用 `papertrace-build-B` 只准备 B1 的设计记录、测试和 synthetic fixtures。
- 本批准确认 B2 的规划范围，但**不授权现在编写 B2 源码**。
- B2 只有在未参与 B1 测试实现的另一名学生，对 B1 的精确测试 commit 在 GitHub 真实 Approve 后才生效。
- 本批准不允许真实 LLM/provider 调用、真实论文外发、修改共享 contracts、修改 PaperQA2 上游、修改依赖锁、CI 或其他模块。
