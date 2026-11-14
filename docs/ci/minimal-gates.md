# 五人团队最小门禁路线

本页是短索引，不另设认证平台、重复批准合同或永久 BLOCKED 规则。六类课程门禁全部保留，工程实现和使用入口见 [README](README.md)。

- **测试批准**：计划先获监督学生批准 → OpenCode 仅准备模块测试 → 非实现者 GitHub Approve 具体测试 SHA → 才开发实现。测试提案可以 open/RED，不强制把红测试合并 main；实现 PR 引用 `Test approval PR: #N`。同一非实现者可批准测试并做最终 review，不强制四人齐到。详见 [test-approval](test-approval.md)。
- **语义质量**：只有产品 AI/prompt/model 相关差异适用；真实数据/模型/预算批准后跑固定集并独立逐项评分，以 GitHub run/artifact/review 绑定，不接受本地自写 PASS。详见 [evaluation](../../test/evaluation/README.md)。
- **完整回归**：新增离线、runtime、上游 `tests/`+`packages/` 三来源，未标记也收集，live 未获准就列清单并 BLOCKED；缺依赖/skip/超时都不等于通过。不用 `-m offline` 漏掉其他测试。详见 [full-regression](full-regression.md)。
- **静态/Schema/披露**：运行实际验证器，静态/结构通过不代表安全认证、功能完成或学生人审完成。

## 私有仓库保护的最简现实路线

2026-11-14 对 `537Lab/PaperTrace` 的经典保护 API 实测 403（要求 Pro 或公开）。保持私有，不升级付费、不迁移仓库、不自建认证。先按可见 CI + 一名非作者 review 手工管理合并，**不声称强制拦截生效**。学生检查自己 Education benefits 是否实际提供可用权益；也可请教师核实 GitHub Education/Team 资格。取得权限后再设六门 required checks、独立批准、撤销旧审查、禁止强推，回读并用真实对照 PR 验收。

官方依据（2026-11-14 核查）：[Protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)、[GitHub plans](https://docs.github.com/en/get-started/learning-about-github/githubs-plans)、[Education benefits](https://github.com/settings/education/benefits)。资格页面存在不等于本账号已取得权益。

首次工程修复没有真实学生事前批准，不倒签；由真人审查修复方案，教师决定共享起点复用是否满足课程要求。成员可认领、做需求/Plan/fake 模块开发；正式实现仍按真实审批顺序，最终合并不能用初始化绿灯冒充 full。
