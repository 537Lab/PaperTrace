# PaperTrace｜全组从这里开始

**我们做什么：**在现有 PaperQA2 上增加“导入论文 → 检索证据 → 人工审核 → 仅用获准证据回答 → 留存与导出”的本地工作台。不是重写 PaperQA2，也不是自动判定论文真伪。

## 先认领一个完整功能

| 成员代号 | 长期负责的功能（包括需求、设计、监督 OpenCode、测试、PR 和本模块界面） | 任务书 |
|---|---|---|
| A | 文献库、导入状态、文献版本；首个界面装配 PR | [模块 A](docs/team/module-A.md) |
| B | 检索及 PaperQA2 薄适配；团队代码中唯一允许导入 `paperqa` 的模块 | [模块 B](docs/team/module-B.md) |
| C | 原文比较、人工接受/排除、审核账本 | [模块 C](docs/team/module-C.md) |
| D | 获准集生成、引用核查、确定性发布门 | [模块 D](docs/team/module-D.md) |
| E | 研究历史、可追溯报告、导出 | [模块 E](docs/team/module-E.md) |

没有“只写文档”或“只管 CI”的成员。测试批准、独立审查和集成职责按 PR 轮换，不能批准自己的实现；具体安排见[工作计划](TEAM_WORK_PLAN.md)。

## 拿到仓库后的启动顺序

0. **先按[新人启动流程](docs/team/startup.md)接通仓库与环境**：被邀请 → 克隆 → 建 Python 3.14 初始化环境 → 实跑 170 项离线测试。任何人这一步都可以立即做，不需要模型或凭据。
1. 阅读已有 `AGENTS.md`、`Prompt.md`，按其中顺序读架构与治理文件；再读[接口约定](docs/team/integration-contract.md)和自己的任务书。
2. 核对本模块需求及测试，先用合成 fixtures。启动 OpenCode **Plan**，要求输出改动路径、接口、正负测试和步骤，**停下等待人工批准**。
3. 非作者批准测试和计划，且确认本次 Build 的写权限后，才进入 **Build → Verify → 独立 PR 审查**。一次启动不等于获准无人监督开发。
4. 交付前逐项完成[交接清单](docs/team/handover-checklist.md)，保留真实 transcript 和人工干预理由。

新克隆先用 Python 3.14 建环境（已有 `.venv` 不重复创建），再同步/测试。初始化锁**不代表 PaperQA2 或 Streamlit 已安装**：

```sh
uv venv .venv --python 3.14
uv pip sync --python .venv/bin/python requirements-init.lock
.venv/bin/python -m pytest -c papertrace.pytest.ini test/offline
```

首次同步须按网络/安装权限执行；其他门禁、live 的授权条件与真实结果以 [docs/ci/gates.md](docs/ci/gates.md) 为准。不自行运行上游整个 `tests/`，不读取 `.env` 或调用真实模型。

## 当前边界与待确认事项

- **本轮范围：**基线、共享契约、合成测试和离线门禁；业务待成员开发，需求/架构/计划待学生审核，不是已实现或已获批准。
- **禁止随意改：**`src/paperqa/`、`packages/`、上游 `tests/`、`pyproject.toml`、`uv.lock`。跨模块通过应用编排合同连接；各人的 view 留在自己模块，不争改同一个 app 入口。
- **安全底线：**没有人工决定即 pending；没有获准证据不调模型；回答必须满足 `cited ⊆ sent ⊆ approved`，且生成前后文库快照、审核版本一致。界面不能另建授权逻辑。
- **GitHub 团队仓库已建立（私有）：https://github.com/537Lab/PaperTrace**，分支 `main`，完整上游历史与基线 `c692d0d` 保留，仅 3 个 `papertrace-*` 标签。私有仓库须先把自己的 GitHub 用户名发给所有者获得邀请才能打开；详细接入与安装见[新人启动流程](docs/team/startup.md)。`upstream` 仍是只读上游，不是团队 origin。
- **CI 已真实运行**：`static-analysis`/`schema`/`ai-use-log` 通过；`test-approval`/`semantic-evaluation`/`regression` 为 BLOCKED（fail-closed，非故障，未伪造通过）。**分支保护与 required checks 仍未生效**（免费套餐私有仓库 403，需 Pro/Team/Enterprise），所以 CI 检查目前不强制拦截合并；最小落地方案见 [docs/ci/minimal-gates.md](docs/ci/minimal-gates.md)。六类门禁全部保留，不能虚构链接、审批或通过记录。
- **学生确认：**课程材料对工具、D5 transcript 口径与复用既有代码的边界须核实；初始化由 Hermes 协助，不能冒充任何成员的 OpenCode 开发贡献。正式成果由学生监督 OpenCode 形成真实记录。
- S0–S4 是相对检查点，不是教师截止日。介绍课只给出暂定 Week 13；确切时间与最终提交方式须学生核对。团队页匿名；最终 D6 要求的真实身份由学生本人填写。
