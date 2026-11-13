# PaperTrace 初始化交付状态

核验日期：2026-11-13。本轮是开发前准备，不是最终课程提交，也不是五人功能已经实现。**GitHub团队仓库尚未创建；远端门禁和分支保护尚未生效。**

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

| 门禁 | 本地真实状态 | 课程完整/远端状态 |
|---|---|---|
| 1 事前测试批准 | 入口明确fail-closed；PR自写approved不能自证 | **BLOCKED**：可信审批人/版本/时序通道未部署，没有学生事前批准 |
| 2 静态分析 | 初始化lint/type/锁一致/冻结/AST/API表面/敏感启发式PASS；故意失败已验证 | **部分完成**：完整依赖漏洞/来源、真实适配集成、安全路径人审仍待完成；远端未启用 |
| 3 需求Schema | **本地PASS**，重复键/重复ID/远端$ref等负例阻断 | GitHub未执行、未设为required check |
| 4 语义评估 | 固定集合/报告合同就绪；无真实证据时BLOCKED，不接受PR自造PASS | **BLOCKED**：真实业务适配器、批准模型/数据/预算与可信评估通道未具备 |
| 5 回归 | 全部团队初始化离线suite PASS；会拒绝failed/skip/空suite | **BLOCKED**：完整上游prior suites与所需live范围未执行 |
| 6 AI-use log | **本地PASS**，缺真实新增日志会阻断 | GitHub未执行、required check未生效 |

`--gate all --scope initialization`实际返回exit2/BLOCKED；其中局部static/schema/regression/ai-log通过不应抹掉1/4与完整5的缺口。GitHub Actions尚无运行URL；文件已创建不等于远端CI执行。管理员授权后还须部署不可由PR随意绕过的可信工作流、人审及ADR要求，并用六类单点违规PR和合法对照实证。

## 待授权或学生本人确认

1. 私有团队GitHub的目标所有者、仓库创建/推送权限与成员访问；不得默认推到现有个人项目。原基线夹带论文/录制资料的再分发许可须先审，私有不等于免许可。
2. 由学生采纳架构/共享接口/阈值、认领功能并确认时间投入；测试及计划必须真实事前批准。本轮没有代签批准。
3. `.opencode/rules.md`为AI辅助初始化提案，不能假称由学生人工编写；采纳后只允许人工修改。根AGENTS写入工具曾返回确认超时，但只读回查文件实际存在；没有重试绕过，也未把文件存在视为学生审批。
4. Introduction要求OpenCode真实监督；本轮Hermes初始化不能冒充学生OpenCode贡献。教师对共享起点的使用边界、D5五份/一份/from-scratch差异、角色轮换与功能ownership安排，需要学生确认。
5. 最终D6的真实姓名/学号、相对贡献、每人反思，以及10分钟demo由学生完成/确认。本轮团队材料匿名，不代填。
6. 精确截止时间未从当前材料核实，只知介绍课暂定Week13；不得将S0–S4建议检查点当教师DDL。
7. 任何模型/embedding/metadata真实调用须另批provider/model、数据、次数、金额及重试；配置目前provider.use全deny。未读个人凭据、未进行PaperQA2模型调用。

## 待成员开发及工程未决项

A–E全部正式业务、Streamlit界面、PaperQA2真实导入/检索/回答端口、审核账本与当前投影、受控出站预算/上下文压缩/约束重注入、发布前新鲜度与引用检查、不可变历史和导出都待成员开发；已有契约不替代这些实现。

初始化venv未安装PaperQA2完整业务/可选extra，未来要在独立锁环境核实解析及本机兼容性；默认parser需固定。OpenCode完整官方Bun工具suite、本轮模型驱动工具正负E2E未执行；v2.0.12路径为lexical且有symlink风险，预检查拒绝symlink只是一层，不能等同永久OS隔离。普通全局环境启动OpenCode不受本轮一次性sandbox保证。

**本轮可用性结论：**五份任务书与统一架构/共享契约/离线验证基础已能用于认领和审核计划；取得访问权及真实批准、配置获准模型后再开发。它不是“课程全部完成”或“无条件可合并/提交”。
