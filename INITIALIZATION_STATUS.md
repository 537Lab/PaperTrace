# PaperTrace 初始化交付状态

核验日期：2026-11-13 初始化，2026-11-14 启动修正。本轮是开发前准备，不是最终课程提交，也不是五人功能已经实现。

**当前真实状态（2026-11-14）：** 私有团队仓库 **https://github.com/537Lab/PaperTrace** 已建立并推送，分支 `main`；远端与本地提交、树哈希、289 个文件一致，仅推送 3 个 `papertrace-*` 标签，完整上游 Git 历史与基线 `c692d0d` 保留。GitHub Actions 已**真实运行**六类检查（[首次运行](https://github.com/537Lab/PaperTrace/actions/runs/43434164875)）：`static-analysis` / `schema` / `ai-use-log` = success；`test-approval` / `semantic-evaluation` / `regression` = failure，均为 **BLOCKED（fail-closed，exit 2）**，不是配置错误，也未伪造通过。**分支保护与 required checks 尚未生效**：免费套餐的私有仓库调用两类保护 API 均返回 `403 Upgrade to GitHub Pro or make this repository public`；仓库按要求保持私有，未升级套餐、未公开。组员尚未被邀请（私有仓库需 GitHub 用户名，见 [启动流程](docs/team/startup.md)）。

> 门禁落地的最小可行方案与「现在可做 / 必须等真实证据」的区分见 [docs/ci/minimal-gates.md](docs/ci/minimal-gates.md)；六类门禁全部保留，无一被放宽。

## 已创建

- 独立Git仓库，继承PaperQA2完整历史及固定基线`c692d0dfeac4a0296599f7fe21a253a58b7ac12a`；tag `papertrace-upstream-baseline`。本地初始化提交由主控完成后以`papertrace-initialization`标签定位；不在文件中填自己的循环SHA。
- 根蓝图及架构目录：ADR、8项不变量、27条需求追踪、状态/权限/上下文/降级政策、选择表与风险记录。均为工程提案，待学生正式采纳。
- YAML PRD、27条机器可读registry及Schema；D3/D4治理、Prompt、AI日志、review/debt/bug基础。
- 5项主契约及DocumentVersion、SourceLocator辅助模型，7份JSON Schema及7份合成JSON样例。只有共享数据验证，没有A–E业务。
- OpenCode2.0.12原生`opencode.jsonc`、课程权限manifest、human-only规则提案、角色边界与无模型验证脚本。
- 六类门禁入口、离线故障注入、固定合成评估集与真实评估/完整回归合同、GitHub工作流。
- `TEAM_START_HERE.md`、`TEAM_WORK_PLAN.md`、`docs/team/module-A.md`至`module-E.md`、集成合同及交接清单。

## 已验证

| 项目 | 实际结果 | 边界 |
|---|---|---|
| 课程原件/交接包 | Project10页、Introduction27页；handover及嵌套包CRC有效；hash见sources manifest | 本地快照，未实时核对Canvas修订 |
| 上游基线 | 原核心/解析子包/测试/pyproject/uv.lock/LICENSE无diff；原README及两份workflow归档字节相等 | 没有运行整个PaperQA2 |
| 团队离线测试 | **170 passed**，0failed，正常/负面/故障注入；命令及真实日志见artifacts | 不等于产品功能/完整上游suite或live通过 |
| 静态 | Ruff通过；mypy在2个团队source文件无问题；25个初始化锁包版本一致；AST导入/契约表面/改动路径敏感启发式通过 | 不等于全供应链无漏洞、安全认证或动态import沙箱 |
| Schema | 27条registry通过schema及补充结构检查 | fit criterion实现仍待成员 |
| AI-use log | 代码/prompt差异触发，真实新增披露有效；仅换ID/改格式/删除历史的负例会失败 | 不能证明人工审批真实性 |
| OpenCode | 实际项目配置回读、native agent.system规则镜像一致；13项真实引擎allow/ask/deny探针通过，4个测试session无消息 | 不是read/edit/shell工具端到端；未调用任何模型 |
| 快照初始边界 | revision=0可记录拒答/失败和blocked，不可draft/released；RED→GREEN已保留 | C账本真实性及D真实出站尚未实现 |
| 低层性能 | 100个小型合成AnswerDraft JSON往返低于2秒，精确值见delivery-audit.json | 不推断PaperQA性能提升或真实问答SLA |

## 六类GitHub Blocking Gates

**两次真实 CI 运行要分开读，不要混为一谈：**

| 运行 | 提交 | 变更性质 | test-approval | semantic-evaluation | regression | static / schema / ai-log |
|---|---|---|---|---|---|---|
| [首跑 43434164875](https://github.com/537Lab/PaperTrace/actions/runs/43434164875) | `9d7e985`（初始化，含代码/prompt） | 有代码与 prompt 变更 | failure（BLOCKED, exit 2） | failure（BLOCKED, exit 2） | failure（BLOCKED, exit 2） | 全部 success |
| [修正 43582067150](https://github.com/537Lab/PaperTrace/actions/runs/43582067150) | `4656a8d`（仅文档） | 无代码/prompt/source 变更 | **NOT_REQUIRED**（job 绿，但课程状态仍 BLOCKED） | **NOT_REQUIRED**（job 绿，但课程状态仍 BLOCKED） | failure（BLOCKED, exit 2） | 全部 success |

`NOT_REQUIRED` 的正确含义是「差异证明本次没有适用的变更」，**不是门禁通过**：两个 job 的 `full_course_status` 仍写着 `test-approval: BLOCKED`、`semantic: BLOCKED`。整体 workflow 在两次运行中都是 `failure`，因为 `regression` 在 `--scope full` 下始终 BLOCKED（其 `details` 显示 170 项团队离线测试实际执行且 0 失败，但完整上游 prior suites 未跑）。这是预期的 fail-closed，不是配置错误。

| 门禁 | 本地真实状态 | 远端真实状态（首跑 `9d7e985`） | 课程完整状态 |
|---|---|---|---|
| 1 事前测试批准 | 入口 fail-closed；PR 自写 approved 不能自证 | `test-approval` = failure（BLOCKED, exit 2） | **BLOCKED**：无学生事前批准；最小路线见 `docs/ci/minimal-gates.md` |
| 2 静态分析 | lint/type/锁一致/冻结/AST/API表面/敏感启发式 PASS；故意失败已验证 | `static-analysis` = **success** | **部分完成**：完整漏洞/来源审计、真实适配集成、安全路径人审仍待完成 |
| 3 需求Schema | **PASS**，重复键/重复ID/远端$ref等负例阻断 | `schema` = **success** | 远端已真实执行；**未设为 required check** |
| 4 语义评估 | 固定集合/报告合同就绪；无真实证据时 BLOCKED | `semantic-evaluation` = failure（BLOCKED, exit 2） | **BLOCKED**：无真实适配器、批准模型/预算与独立人工评分 |
| 5 回归 | 全部团队离线 suite PASS；拒绝 failed/skip/空 suite | `regression` = failure（**BLOCKED**, exit 2；`--scope full` 下 170 项本身通过） | **BLOCKED**：L2 上游 prior suites 与 L3 live 范围未执行 |
| 6 AI-use log | **PASS**，缺真实新增日志会阻断 | `ai-use-log` = **success** | 远端已真实执行；**未设为 required check** |

`--gate all --scope initialization` 实际返回 exit2/BLOCKED；局部 static/schema/regression/ai-log 通过不应抹掉 1/4 与完整 5 的缺口。GitHub Actions **已真实运行**（不再是「尚无运行 URL」），整体 conclusion 为 failure，属预期 fail-closed。

**分支保护与 required checks 仍未生效**：经典保护 API 与 Rulesets API（含最小规则）在免费套餐私有仓库均返回 `403 Upgrade to GitHub Pro or make this repository public`。仓库按要求保持私有，未升级套餐、未公开。教师申请免费 GitHub Team 组织是最贴合五人团队的解法；学生包官方页面**未明确列出 GitHub Pro**，须学生本人在 Education benefits 页核实。详见 `docs/ci/minimal-gates.md`。

本轮启动修正**没有改动 `scripts/gates.py` 判定逻辑、没有改 `.github/workflows/ci.yml` 的六个 job 与 scope**；新增 `.github/pull_request_template.md` 作为免费仓库也能立即生效的证据清单（**非强制拦截**）。启用保护后仍须回读规则并用六类单点违规 PR 与合法对照实证。

## 待授权或学生本人确认

1. ~~私有仓库创建/推送授权~~ **已完成**（`537Lab/PaperTrace`，2026-11-13）。**仍待办**：提供五名组员的 GitHub 用户名以发出邀请（私有仓库未邀请会 404）；上游基线夹带论文/录制资料的再分发许可仍须逐件审查，私有不等于免许可；决定是否由教师申请免费 GitHub Team 组织以启用分支保护。
2. 由学生采纳架构/共享接口/阈值、认领功能并确认时间投入；测试及计划必须真实事前批准。本轮没有代签批准。
3. `.opencode/rules.md`为AI辅助初始化提案，不能假称由学生人工编写；采纳后只允许人工修改。根AGENTS写入工具曾返回确认超时，但只读回查文件实际存在；没有重试绕过，也未把文件存在视为学生审批。
4. Introduction要求OpenCode真实监督；本轮Hermes初始化不能冒充学生OpenCode贡献。教师对共享起点的使用边界、D5五份/一份/from-scratch差异、角色轮换与功能ownership安排，需要学生确认。
5. 最终D6的真实姓名/学号、相对贡献、每人反思，以及10分钟demo由学生完成/确认。本轮团队材料匿名，不代填。
6. 精确截止时间未从当前材料核实，只知介绍课暂定Week13；不得将S0–S4建议检查点当教师DDL。
7. 任何模型/embedding/metadata真实调用须另批provider/model、数据、次数、金额及重试；配置目前provider.use全deny。未读个人凭据、未进行PaperQA2模型调用。

## 待成员开发及工程未决项

A–E全部正式业务、Streamlit界面、PaperQA2真实导入/检索/回答端口、审核账本与当前投影、受控出站预算/上下文压缩/约束重注入、发布前新鲜度与引用检查、不可变历史和导出都待成员开发；已有契约不替代这些实现。

初始化venv未安装PaperQA2完整业务/可选extra与Streamlit；隔离环境已实测`streamlit 1.67.0`可装可导入，完整PaperQA2安装因本机会话临时目录限制未验证。分层的启动命令、B/D额外依赖、OpenCode获准配置与macOS/Windows差异见`docs/team/startup.md`；默认parser需固定。OpenCode完整官方Bun工具suite、本轮模型驱动工具正负E2E未执行；v2.0.12路径为lexical且有symlink风险，预检查拒绝symlink只是一层，不能等同永久OS隔离。普通全局环境启动OpenCode不受本轮一次性sandbox保证。

**本轮可用性结论：**五份任务书与统一架构/共享契约/离线验证基础已能用于认领和审核计划；取得访问权及真实批准、配置获准模型后再开发。它不是“课程全部完成”或“无条件可合并/提交”。
