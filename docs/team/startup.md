# 启动命令页

> **入口只有 [`TEAM_START_HERE.md`](../../TEAM_START_HERE.md)。** 本页只保存克隆与初始化环境命令，不是第二套 onboarding，也不代替模块 Plan/审批。

## 加入仓库

PaperTrace 团队仓库为私有。先请仓库所有者邀请你的 GitHub 账号，接受邀请后：

```sh
git clone https://github.com/537Lab/PaperTrace.git
cd PaperTrace
```

当前main尚未采纳PR #1时，不要从旧main开始业务代码。先按[团队入口的当前阶段](../../TEAM_START_HERE.md#0-当前可做与唯一一次采纳)认领/做Plan；维护者完成受审采纳后，从最新main分别建测试分支。仅需提前准备时，可在GitHub Desktop中选中已审查的`fix/development-unblock`后新建个人`plan/<模块>-<姓名>`分支；不是授权直接修改共享修复分支。

安装 Python 3.14 和官方 `uv`。若已有可用 `.venv`，跳过建环境，仅按需要同步锁文件。

## 初始化离线环境

macOS / Linux：

```sh
uv venv .venv --python 3.14
uv pip sync --python .venv/bin/python requirements-init.lock
.venv/bin/python -m pytest -c papertrace.pytest.ini test/offline
```

Windows PowerShell：

```powershell
uv venv .venv --python 3.14
uv pip sync --python .venv\Scripts\python.exe requirements-init.lock
.venv\Scripts\python.exe -m pytest -c papertrace.pytest.ini test/offline
```

这是初始化/共享契约环境；`requirements-init.lock` 不表示 PaperQA2、Streamlit 或业务解析器已安装。命令结果要看真实终端与 [`docs/ci/gates.md`](../ci/gates.md)，不要把示例输出当本机通过。不要用根 `uv sync` 安装上游全部 extras，也不要运行上游 `tests/` 替代团队离线 suite。

## 后续动作

1. 回到[团队唯一入口](../../TEAM_START_HERE.md)，认领一个模块并按根 `AGENTS.md` / `Prompt.md` 进入 Plan。
2. Plan 明列正负测试、fake 端口、模块相对路径范围、工具/网络/依赖需求；监督学生批准计划、非实现者事前批准测试，一次确认本轮范围后 Build，不逐次审批日常编辑与离线命令。
3. B/D 的 PaperQA2 业务依赖和离线真实适配需独立计划/许可审查；provider/model、数据、尝试次数、重试、费用与 deadline 又需单独 live 批准。A/C/D/E 可先用 synthetic fixtures/fakes 并行，不等真实模型。
4. OpenCode 版本/配置说明见 [`docs/tooling/opencode-setup.md`](../tooling/opencode-setup.md)；PaperQA2 smoke 命令及实际运行回执以主控合入的运行文档为准。B/D 的当前候选运行依赖见 [`requirements-runtime.in`](../../requirements-runtime.in) 与 [`requirements-runtime.lock`](../../requirements-runtime.lock)，仅列清单不证明安装/集成通过。许可与 live 条件见 [`docs/licenses/license-review.md`](../licenses/license-review.md) 和 [`test/live/README.md`](../../test/live/README.md)。配置/脚本存在不代表工具端到端通过、学生已监督 Build 或真实模型语义通过。

`.opencode/rules.md` 是课程要求的 human-only 规则；编码代理不得修改它来批准自己。默认 provider 无模型调用；凭据只由学生本人通过受控方式注入获批运行环境，不写入仓库或聊天。六类课程门禁保持全部有效，实时状态见 [`docs/ci/gates.md`](../ci/gates.md)。
