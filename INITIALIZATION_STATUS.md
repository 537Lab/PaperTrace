# PaperTrace 开发就绪状态（2026-11-14 工程解阻）

**结论：有条件开工。** A–E 可独立推进需求/Plan/测试准备/fake 模块；业务实现前必须有真实非实现者测试批准。完整上游回归、真实模型质量、学生采纳和远端保护没有被伪造完成。正式业务/完整 Streamlit 应用尚未实现。

本轮从 `e6ab25299a9b962099bd22edeba2dd745428b39d` 建 `fix/development-unblock`，保留上游 `c692d0dfeac4a0296599f7fe21a253a58b7ac12a` 与原历史，核心/包/原测试/pyproject/uv.lock/LICENSE 的受跟踪字节无差异。修复分支/PR 的最新 hash 以 GitHub 为准，不在文件中伪造循环 SHA。

## 实际验证与边界

| 范围 | 实际结果 | 不能据此宣称 |
|---|---|---|
| 全部团队离线测试 | **332 passed，0 skip**；保留上一轮299项，本轮新增33项PR/main事件及审批回放检查 | 不是完整上游/API/真实模型通过 |
| OpenCode v2.0.12 | 真实 loopback fake + 工具循环2用例通过：Plan写拒绝、仅测试准备RED、模拟审查后自有源码写成功、跨模块写拒绝、Verify GREEN | 模拟审查不是学生批准、D5贡献或真实模型质量 |
| 静态/Schema/披露 | 本轮真实static、schema、ai-log均PASS；见 artifacts/verification/final-ci-events.json，原closeout/unblock证据保留 | 静态分析不是供应链安全认证 |
| PaperQA2 | 83包隔离runtime；真实 aadd→aget_evidence→aquery，三来源同索引仅获准1项送新会话；排除/pending未重入prompt；零获准且仍有文献时零检索/模型调用；1 integration passed | embedding/summary/answer均为明确fake，不是正式B/D模块或真实模型评估 |
| 完整上游 | 原uv.lock实际安装261包，另用独立hash锁补pytest-socket；base/current均收集 **377** 节点，9个live待授权，无prior节点丢失；默认禁网执行有真实失败且限时停止 | **完整回归 FAIL/未通过**，不降成初始化、不删未标记项、不隐去失败 |

完整回归原始汇总见 `artifacts/verification/unblock-full-regression.json`。首个故障 `tests/test_agents.py::test_get_directory_index` 实测尝试OpenAI调用，被socket guard拒绝；即使未标记live也没有漏掉或放行。真实API/付费/私密数据未获准，本轮不解除边界、不读私人模型密钥、不重试收费调用。全部失败不应归因为唯一这一原因；完整API结果仍缺。

### 本轮收尾范围（续接931cea6，不重初始化）

仅修复独立复审的三项语义门禁问题：请求必须对应固定问题/获准证据正文/发送ID及版本化system prompt；v3报告绑定runtime锁、配置输入及同一evaluator解释器实际Python/安装版本；Gate4按配置内容与生产依赖闭包触发，不再对Ruff/pytest等无关改动要求付费评估。B/D界面和上游模型源码仍受触发及摘要绑定保护。实际83包runtime核对通过；固定数据/阈值、六门禁、A–E功能职责不变。

这次增量只修验证器/测试/合同，局部Gate4为NOT_REQUIRED；不等于整个修复分支、未来B/D业务或真实质量评估获批。新报告仍须真实Actions artifact、预算和独立人审；无有效真实证据时不放行。

## 六类门禁真实状态

1. **test-approval：验证器已实现，当前 BLOCKED**，没有真实学生事前批准；synthetic API正负例不是批准。
2. **static：本地 PASS**，含实际OpenCode配置与精确锁/固定字节检查；只豁免Git ignored的标准SCM/egg-info构建元数据，任意新增上游源码仍FAIL。
3. **schema：本地执行校验**，27条registry不重定义、不冒称业务实现。
4. **semantic：验证器已实现；适用改动无真实artifact/批准/评分则 BLOCKED**。固定4安全+6质量×3=18真实质量调用及原阈值不变；报告绑定真实GitHub run/artifact/digest/current head/review，普通文档/编码助手规则不做虚假评估。业务evaluator由B/D在接口实现后单独受审落入base，本轮不提前代写。
5. **regression：实际full FAIL**（上游禁网失败/限时，且live待授权）；团队332+runtime1通过不能代替full。
6. **ai-log：按真实新增披露验证**；Hermes工程修复与学生正式OpenCode过程分开。

### 最终事件验收（续接552d918）

已通过最小真实代码路径复现旧push无PR编号的问题。PR仍用base验证open PR；main push核对唯一原生merged PR、before/base/merge SHA/相同tree后回放测试批准与适用语义证据，其他质量检查直接检查新main。撤销批准、未批准测试、错来源/事件、无PR直接push均拒绝；同一问题不改成无条件skip。测试提案只可在实现合并后关闭而不破坏合法追溯。真实bash选择器与CLI线路也有离线正负验证。当前332离线、Ruff/mypy和PaperQA2 smoke1均通过；不是已在真实main完成合并后CI验证（本轮不合并）。

首次采纳是[有限且一次的人审动作](docs/ci/minimal-gates.md#pr-1-的一次性首次采纳bootstrap)，没有新增批准服务/开关。当前PR #1仍待真人，不把候选自证或AI复核冒充人审；若课程不允许共享工程/已知失败基线，就不擅自合并。邀请成员后可认领/Plan/准备测试，正式业务实现仍按真实批准顺序；不再继续完善初始化设施。

## 远端与首次采纳

私有仓库保护 API 403；可见CI不是强制required checks。保持私有，不升级套餐、不公开、不改main历史。PR在target取候选、精确base取控制程序；main push使用已合入的控制程序且追溯实际merged PR，token仅元数据步骤；首次修复base仍是旧验证器时明确 `BASE_VERIFIER_UPGRADE_REQUIRED`，由真人审查采纳，不倒签事前批准。macOS原生工具回归消耗已有Actions配额，不开新付费套餐。远端实际运行须按PR checks读回，不能用历史首跑充当本轮结果。

## 学生本人仍必须完成

- 五名成员认领功能、批准并理解架构/共享合同/本轮提案；计划由监督学生批准，非实现者在实现前批准具体测试版本。
- 自己监督OpenCode、保留真实完整会话及干预，不把本轮fake会话或Hermes初始化冒充D5/个人贡献。
- 真实模型/provider/数据/预算授权、固定集评估与独立评分；完整prior/API回归的真实结果。
- GitHub账号/邀请、资格与保护回读/对照PR；D5五份annotated与一份raw/from-scratch口径、基线复用、确切DDL向教师确认。
- D1–D9正式交付、D6身份/相对贡献平均1.0/真实反思、10分钟demo与ZIP分开。均没有代填或标完成。

从 [TEAM_START_HERE.md](TEAM_START_HERE.md) 进入；唯一命令参考在 [startup](docs/team/startup.md)。不存在“先等五个模块全实现才能开发”的要求；但本轮不是无条件可合并、可发布或最终课程提交。
