# PaperTrace — Evidence Review Workbench

基于固定PaperQA2的本地科研证据审核工作台。目标流程是：导入论文 → AI检索候选 → **人工接受/排除** → 仅据本轮获准证据生成草稿 → 确定性核查后保存可追溯报告。模型不决定授权、不自动证明科学结论正确。

**当前交付：开发前初始化；不是五模块已经实现的应用。** 先读[团队一页入口](TEAM_START_HERE.md)、[完整任务书](TEAM_WORK_PLAN.md)与[真实状态](INITIALIZATION_STATUS.md)。GitHub团队仓库：**尚未创建**；未设置团队origin，未上传、未配置分支保护。本轮没有PaperQA2模型调用/真实语义PASS，也没有学生人工审批或个人OpenCode会话。

## 架构和文件

A `library/`：导入/状态/文献版本；B `retrieval/`：唯一PaperQA2薄适配及出站端口；C `review/`：人审/比较/追加决定；D `answer/`：获准集/受控上下文/生成/发布门；E `reports/`：历史/来源/导出。五模块由各成员后续开发，本轮只实现共享契约和初始化验证基础。Streamlit为薄本地界面，不部署大型前端、数据库或云服务。

- `src/paperqa/`、`packages/`、`tests/`、`pyproject.toml`、`uv.lock`：原上游冻结基线，不能随意改。
- `src/papertrace/contracts.py`：共用不可变模型，契约说明见`docs/contracts/schema.md`。
- `test/offline/`：初始化确定性测试；`test/live/`：真实模型运行合同，尚未有业务实现/授权。
- 根`architecture-blueprint.md`：架构唯一正文；`docs/architecture/`：ADR、不变量、状态/权限/上下文/失败政策、追踪与选择记录。
- `docs/req/`：YAML PRD、registry及schema；`docs/code-governance/`：结构、验证、工具约束。
- `AGENTS.md`、`Prompt.md`、`opencode.jsonc`：编码代理入口、先计划后批准、实际项目配置；课程要求的`.opencode/permissions.jsonc`不是引擎自动入口。
- `docs/team/module-A.md`至`module-E.md`：五份可认领任务书；集成与交付清单同目录。
- `docs/ci/`和`scripts/gates.py`：六类门禁的真实状态/可执行入口；`artifacts/verification/`：实际证据。
- `docs/upstream/README.paperqa.md`与`workflows/*.disabled`：原README/工作流原字节保全。旧自动发布工作流已从活动路径移出。
- `Report.md`、`transcripts/README.md`：明确尚未完成的学生报告/真实会话责任，不填虚假贡献。

## 从零建立初始化环境

本轮实测CPython3.14.6。先安装官方Python和uv；已有环境只执行下面同步。本仓库根pyproject属于上游，不用裸`uv sync`把所有extra装进来。

```sh
uv venv .venv --python 3.14
uv pip sync --python .venv/bin/python requirements-init.lock
.venv/bin/python -m pytest -c papertrace.pytest.ini test/offline
.venv/bin/python -m ruff check --config papertrace.ruff.toml src/papertrace test/offline scripts
.venv/bin/python -m mypy --config-file mypy.ini src/papertrace
.venv/bin/python scripts/gates.py --gate schema
```

初始化环境不安装PaperQA2业务依赖、不下载模型。锁是本轮已解析版本快照；其他平台重新同步后实跑核查，不把本机验证推断为全平台通过。

## Offline / Live / Full suite

- **Offline initialization**：上面pytest命令，pytest-socket禁用测试中的socket；这是受控新测试，不是OS全局网络沙箱。测试运行只用合成样例，不读取真实凭据。
- **Live**：本轮不可运行真实模型。先按`test/live/README.md`和`docs/ci/`确认模型、数据、费用、次数、适配器和可信评估通道；没有批准则BLOCKED。没有假模型固定回答伪装真实连通。
- **Full prior regression**：保留原`tests/`及`packages/*/tests/`，使用单独锁定的完整上游依赖环境执行，包含既往需要的live范围。初始化suite绿灯不能代替它；缺依赖/预算/可信结果时full gate必须BLOCKED。完整命令与依赖前置见`docs/ci/gates.md`。

## 六类Blocking Gates

1. 实现前测试批准；2. lint/类型/依赖及安全路径结构检查；3. 需求schema；4. prompt/model变更真实语义评估；5. 完整既往回归；6. 代码/prompt变更更新AI-use log。本地基础命令和故障注入只是下层证据；远端required checks、独立人审及安全路径ADR必须由获授权管理员部署并用违规PR验证，**当前未生效**。

课程原文核对、OpenCode工具要求及个人会话/角色/最终报告待学生确认事项见`docs/sources/course-compliance.md`。本轮Hermes辅助初始化如实披露，不冒充学生OpenCode贡献或事前批准。

## 来源与许可

上游：https://github.com/Future-House/paper-qa；基线`c692d0dfeac4a0296599f7fe21a253a58b7ac12a`。保留完整Git历史及根`LICENSE`、各包许可证。根Apache-2.0不覆盖所有extra、模型或论文数据；PyMuPDF相关AGPL和论文再分发必须单独审查。详见`docs/licenses/license-review.md`。团队材料包仅含本轮新增基础，不含上游论文、原课程资料或凭据。
