# 五人团队最小门禁路线

本页是短索引，不另设认证平台、重复批准合同或永久 BLOCKED 规则。六类课程门禁全部保留，工程实现和使用入口见 [README](README.md)。

- **测试批准**：计划先获监督学生批准 → OpenCode 仅准备模块测试 → 非实现者 GitHub Approve 具体测试 SHA → 才开发实现。测试提案可以 open/RED，不强制把红测试合并 main；实现 PR 引用 `Test approval PR: #N`。同一非实现者可批准测试并做最终 review，不强制四人齐到。详见 [test-approval](test-approval.md)。
- **语义质量**：只有产品 AI/prompt/model 相关差异适用；真实数据/模型/预算批准后跑固定集并独立逐项评分，以 GitHub run/artifact/review 绑定，不接受本地自写 PASS。详见 [evaluation](../../test/evaluation/README.md)。
- **完整回归**：新增离线、runtime、上游 `tests/`+`packages/` 三来源，未标记也收集，live 未获准就列清单并 BLOCKED；缺依赖/skip/超时都不等于通过。不用 `-m offline` 漏掉其他测试。详见 [full-regression](full-regression.md)。
- **静态/Schema/披露**：运行实际验证器，静态/结构通过不代表安全认证、功能完成或学生人审完成。

## 私有仓库保护的最简现实路线

2026-11-14 对 `537Lab/PaperTrace` 的经典保护 API 实测 403（要求 Pro 或公开）。保持私有，不升级付费、不迁移仓库、不自建认证。先按可见 CI + 一名非作者 review 手工管理合并，**不声称强制拦截生效**。学生检查自己 Education benefits 是否实际提供可用权益；也可请教师核实 GitHub Education/Team 资格。取得权限后再设六门 required checks、独立批准、撤销旧审查、禁止强推，回读并用真实对照 PR 验收。

官方依据（2026-11-14 核查）：[Protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)、[GitHub plans](https://docs.github.com/en/get-started/learning-about-github/githubs-plans)、[Education benefits](https://github.com/settings/education/benefits)。资格页面存在不等于本账号已取得权益。

## PR #1 的一次性首次采纳（bootstrap）

Bootstrap 指**首次受审引入工程基线**，不是第七类门禁、自动批准开关或六门禁豁免。新验证器不可能先出现在旧 base，所以 PR #1 的 `BASE_VERIFIER_UPGRADE_REQUIRED` 仍真实保留；不修改它为 success。教师原文要求真实监督及六门禁，未找到允许本轮 Hermes 工程修复倒签为学生事前批准的条款。**若课程不接受这份共享初始化/已知失败基线，先向教师确认，不合并 PR #1，也不声称已符合最终考核。**这不妨碍认领、需求、Plan 和测试准备。

### 真人现在具体做什么

1. **固定审查对象。**打开 [PR #1](https://github.com/537Lab/PaperTrace/pull/1)，在 Commits 复制最新完整40位 head SHA；同时确认 base 仍为团队预期 main、没有后续未审提交。不要批准旧摘要对应的过期版本。
2. **检查有限范围。**在 Files changed 查看六门禁与事件/令牌边界、OpenCode默认拒绝和模块范围、共享合同/五份任务书、原上游未改及AI披露；核对 `artifacts/verification/` 真实执行回执。重点确认请求材料/运行依赖绑定、真实审批顺序，以及 main push 会重验合并来源而不是无编号跳过。确认A–E业务仍留给成员。
3. **核实能与不能。**复跑受影响离线检查，或核对与当前文件SHA相符的回执；明确完整上游仍FAIL/限时、9 live未授权、真实语义评估未跑、保护API403、学生D5尚未发生。不能要求未经批准的收费调用来凑绿灯。课程共享起点/已知失败基线的接受边界由真实学生/教师确认并在PR留下来源；未确认时不要填“教师已批准”。
4. **真实独立审核。**由未参与本次实现、有仓库write权限的真人，在 PR → Files changed → Review changes → **Approve** 提交。正文写清最新完整head、实际检查内容、只接受工程起点及上述剩余条件，不把AI复核当自己检查，不补写事前批准。可用下列提示，必须自行填实情：
   ```text
   首次工程基线采纳：PR #1，head <完整SHA>。
   我实际检查了：<具体diff/运行或核对的证据>。
   接受范围：共享开发起点，不是A–E业务实现或学生D5贡献。
   未补造事前测试批准；上游FAIL/未授权live/真实模型评估/保护限制按原状态保留。
   课程共享起点与失败基线的适用依据：<真实来源；尚未确认则暂不建议合并>。
   结论：<同意在该明确边界下采纳，或要求修改>。
   ```
5. **首次合并仍由人操作。**确认上一步是真人当前head的独立APPROVE、课程接受边界已解决、没有变更/冲突，再由维护者在同一PR使用 **Create a merge commit → Confirm merge**。优先保留历史，不rebase/强推；若需修改冲突，先在分支同步main、复验并重新审查，不能在合并时夹带未审内容。**本轮代理不合并、不启用auto-merge。**在套餐无法强制保护时，这个手工采纳必须明示为一次性初始工程决定，不是假称六个红灯已通过；若课程要求此时也必须全绿，就停在第4步并请教师决定，不自行豁免。
6. **检查第一次main push。**已合入main的代码成为受审控制程序，静态/Schema/full回归/披露会实际重跑；审批与语义检查从原生合并PR回放证据，不再报`missing-pr-number`。**PR #1缺失的真实事前批准/评估仍会BLOCKED/FAIL，full仍可能失败，不自动转绿。**这些欠缺不是本流程修补的课程事实。后续正常PR使用已经采纳的base验证器，提供真实证据即可通过，不再重复初次引入的循环。

## 今后事件的明确职责

- **PR / review事件：**从精确base读取控制程序；核对该open PR的测试批准、适用语义评估、静态、Schema、完整回归和新增披露。测试提案可open/RED，不能因为提案红灯就代签批准或提前实现。
- **main push：**只监听main，避免每个功能push与PR重复运行。已采纳main控制程序核对事件before/after，审批/语义由GitHub commit→merged PR→原base/head及同一tree追溯并重新验证原证据；静态/Schema/完整回归/披露直接检查新main。无来源/多义PR、撤销批准、未批准测试、错repo/SHA/tree、强推/删除/新建main事件都会拒绝，不以缺PR号无条件通过。
- **手动重跑：**`workflow_dispatch`仅支持main，仍须找回对应真实合并PR；不是直接push或缺证据的逃生口。团队优先使用Create a merge commit，先同步main再获批，避免多PR批量推进或冲突编辑使合并tree与受审head不同。
- **信任边界：**main上的运行表示已采纳代码，不代表其质量已通过；远端review权限及缺少强制分支保护仍需真人管理。候选可修改workflow本身，所以base钉住并非不可篡改认证系统；必须审查workflow diff，绝不把令牌交给候选测试或真实模型。
