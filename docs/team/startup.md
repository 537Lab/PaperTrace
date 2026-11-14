# 新人启动流程（唯一入口）

更新：2026-11-14。本文只讲**怎么把环境跑起来**；功能分工看 [TEAM_START_HERE.md](../../TEAM_START_HERE.md) 和自己的 `module-X.md`，门禁看 [../ci/minimal-gates.md](../ci/minimal-gates.md)。

私有仓库：**https://github.com/537Lab/PaperTrace**（分支 `main`）。**私有仓库必须先被邀请**：把你的 GitHub 用户名发给仓库所有者 `537Lab`，收到邀请后再打开链接，否则是 404。

> `requirements-init.lock` 只锁 25 个**初始化工具**包（pytest/ruff/mypy/pydantic/jsonschema…）。它**不含** PaperQA2 运行依赖，也不含 Streamlit。把「离线测试能跑」误当成「业务能跑」是本项目最常见的误解。

## 第 0 层：所有人，被邀请后立即可做（无需模型、无需凭据）

```sh
git clone https://github.com/537Lab/PaperTrace.git
cd PaperTrace
```

**Python 3.14**（上游 `requires-python >=3.11,<3.15`，本轮实测 3.14.6）。安装 `uv`（<https://docs.astral.sh/uv/getting-started/installation/>）后：

```sh
# macOS / Linux
uv venv .venv --python 3.14
uv pip sync --python .venv/bin/python requirements-init.lock
.venv/bin/python -m pytest -c papertrace.pytest.ini test/offline
.venv/bin/python -m ruff check --config papertrace.ruff.toml src/papertrace test/offline scripts
.venv/bin/python -m mypy --config-file mypy.ini src/papertrace
.venv/bin/python scripts/gates.py --gate schema
```

```powershell
# Windows PowerShell（同一套锁，只是 venv 路径与激活方式不同）
uv venv .venv --python 3.14
uv pip sync --python .venv\Scripts\python.exe requirements-init.lock
.venv\Scripts\python.exe -m pytest -c papertrace.pytest.ini test/offline
.venv\Scripts\python.exe -m ruff check --config papertrace.ruff.toml src/papertrace test/offline scripts
.venv\Scripts\python.exe -m mypy --config-file mypy.ini src/papertrace
.venv\Scripts\python.exe scripts/gates.py --gate schema
```

预期：`170 passed`、ruff `All checks passed!`、mypy `no issues found in 2 source files`、schema `PASS`。这四步在**本机 2026-11-13 已实测通过**，并在 GitHub Actions 首次运行中再次验证（[run 43434164875](https://github.com/537Lab/PaperTrace/actions/runs/43434164875)）。

**已实测 / 未实测见文末表。** 若你的机器复跑失败，先记下命令、退出码和 Python/`uv` 版本，不要改阈值或删测试来让它变绿。

## 第 1 层：B / D 开始真实 PaperQA2 工作前（需单独批准）

A / C / E 用合成 fixtures 和共享契约即可推进，**不需要**安装完整 PaperQA2。B（唯一允许 `import paperqa` 的模块）和 D（经 B 的受控端口调用）在写真实适配器之前需要：

1. **另建业务环境，不要污染 `.venv`，也不要改冻结文件**：`src/paperqa/`、`packages/`、`tests/`、`pyproject.toml`、`uv.lock` 一律不改；新增依赖须走计划审批并单独记录。
2. **上游运行依赖**（来自冻结的 `pyproject.toml` `[project].dependencies`）：`fhaviary[llm]`、`fhlmi`（提供导入链上的 `lmi` 模块）、`litellm`、`tantivy`、`tiktoken`、`pydantic-settings`、`pybtex`、`html2text`、`httpx-aiohttp`、`rich`、`numpy`、`tenacity`、`setuptools`、`anyio`，以及 `paper-qa-pypdf`。默认 parser 需固定并写进计划。
3. **安装方式**：在独立环境中按冻结的 `uv.lock` 用 `uv sync --frozen` 或 `uv pip install -e .`（本地源码可编辑安装）。本机 `uv` 不在 PATH，但项目自带的可执行文件在 `~/.hermes/tools/uv-0.13.5-darwin-arm64/uv`；组员请装官方 uv。
4. **真实调用再分两关**：先批准业务依赖与**离线**上游集成；再批准 provider/model、数据范围、请求次数/重试、金额上限与 deadline，才允许 live。工厂初始化 / SDK attempt / HTTP attempt / usage 分开记录；缺 usage 记为 unknown，不补 0。
5. **许可**：`paper-qa-pypdf` 及其依赖、PyMuPDF（AGPL/商业双许可）、可选 extra 与模型权重需逐项审查，见 [../licenses/license-review.md](../licenses/license-review.md)。根 Apache-2.0 不自动覆盖这些。

推荐的最小离线联通性自检（**不调用任何模型**、不读取 `.env`）：

```sh
# 在业务环境里；仅验证导入与确定性对象，不触发 LLM/embedding
python -c "from paperqa import Settings, Doc, Text; s=Settings(); print('paperqa import OK', s.embedding)"
```

> 本次在隔离 venv（Python 3.14.6）中：`streamlit 1.67.0` 安装并导入**成功**；`from paperqa ...` 因缺少 `lmi` 等运行依赖**失败**。完整 PaperQA2 editable 安装在本机会话受临时目录限制**未能完成验证**，因此这里给的是依据冻结 `pyproject.toml` 与依赖探测得出的清单，**不是已验证的一键安装命令**。B 首次在自己的机器上跑通后，请把实际命令、版本与环境回写到本文（这是真实证据，不能由他人代填）。

**Streamlit（E 及各人自己的 view）**：初始化锁不含它。隔离 venv 已实测 `uv pip install streamlit` / `pip install streamlit` 得到 1.67.0 并可 `import streamlit`。版本需锁定并审许可证后再写入共享依赖，见 `license-review.md`。

## 第 2 层：OpenCode 默认无模型，获准后怎么配置

`opencode.jsonc` 当前是**刻意离线**的：

- `default_agent` = `papertrace-plan`（只读，不能写）；
- `experimental.policies` 中 `provider.use` 对 `*` 为 **deny** —— 任何模型请求默认被拒绝；
- 无 `provider`、无 `model`、无 `mcp.servers`、`plugins: []`、`formatter/lsp: false`；
- 规则嵌在每个 agent 的 `system` 中（v2.0.12 的 `instructions[]` 不生效），`.opencode/rules.md` 为人工专属，只能由人改。

**学生获准后**（provider/model、数据范围、次数、金额、期限由学生本人批准并记录）：

1. 由**学生本人**在自己的受控环境里为所需 provider 配置凭据，用环境变量/系统密钥环注入，**绝不写进仓库、`.env`、`opencode.jsonc` 或任何提交**；本轮及本说明都不读取、不展示凭据。
2. 在人工审查后调整 `experimental.policies` 中 `provider.use` 的作用域（按批准的确切 provider/model 收窄，不要直接改成全局 allow），并指定 agent 的 `model`。这属于共享配置变更，须按 `TEAM_WORK_PLAN.md` 预约编辑者并单独批准。
3. 先跑一个零凭据负例确认 deny 仍生效，再做一次获准的最小真实调用，保留 usage/版本/时间记录；无批准就保持 deny。
4. Introduction 要求**学生本人监督** OpenCode 并形成真实 D5 会话（`transcripts/` 目前只有 README，没有任何会话）。初始化由 AI 辅助，不能冒充学生贡献；也不要把本页当成已完成的配置。

## 第 3 层：macOS / Windows 实际差异

| 项 | macOS / Linux | Windows |
|---|---|---|
| venv 可执行文件 | `.venv/bin/python` | `.venv\Scripts\python.exe` |
| Shell | zsh / bash | PowerShell（或 Git Bash）；`&&`、引号、路径斜杠写法不同 |
| 激活 | `source .venv/bin/activate` | `.venv\Scripts\Activate.ps1`（可能需 `Set-ExecutionPolicy -Scope Process RemoteSigned`） |
| uv 安装 | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 \| iex"` |
| 路径 / 行尾 | `/`、`LF` | `\`、`CRLF`；以 `.gitattributes` 为准，不要批量转换行尾 |
| `paper-qa-pypdf` / `tantivy` 等原生轮子 | 本轮 Streamlit 与初始化锁的 macOS arm64 轮子实测可装 | **未在 Windows 实测**；若缺预编译轮子需装 Rust/MSVC 构建工具，或改用纯 Python parser 并在计划中说明 |
| `uv.lock` / `pyproject.toml` | 冻结，勿改 | 同左；不要因本机解析失败就重生成锁 |
| 长路径 | 一般无碍 | 建议把仓库放在短路径（如 `C:\src\PaperTrace`），避免 MAX_PATH |

> 本轮全部实测都在 **macOS + Python 3.14.6** 上完成。Windows 步骤是依据官方 uv/venv 行为给出的**未经本机验证**的指引，需 Windows 组员实跑后补充真实结果；不能把「应该能跑」写成「已通过」。

## 已实测 / 未实测（2026-11-14）

| 项目 | 状态 | 依据 |
|---|---|---|
| 170 项离线测试、ruff、mypy、schema 门禁 | **已实测通过**（2026-11-13 本机 + GitHub Actions 首跑） | `artifacts/verification/`，[CI run](https://github.com/537Lab/PaperTrace/actions/runs/43434164875) |
| `schema` / `ai-log` 门禁进程内复跑 | **已实测 PASS**（2026-11-14） | 本次会话 |
| `streamlit` 安装 + `import streamlit` + headless 启动 | **已实测成功**（隔离 venv，1.67.0） | 本次会话；日志显示 Uvicorn 在 8501 启动 |
| 初始化环境不含 `paperqa` / `lmi` 等 | **已实测确认** | 导入探测返回 `ModuleNotFoundError: lmi` |
| `static` / `regression` 门禁本次复跑 | **未完成**（本机临时目录被会话沙箱拦截，子进程无法创建临时文件；非门禁逻辑失败） | 2026-11-13 及远端 CI 均已通过，证据保留 |
| 完整 PaperQA2 editable 安装 + 真实业务导入 | **未验证**（本机沙箱临时目录限制；pip/uv 构建阶段被拦截） | 需 B 在自己的机器上验证并回写 |
| Windows 全部步骤、真实模型调用、完整上游 prior suite | **未验证 / 未授权** | 见 `../ci/minimal-gates.md` 与 `../licenses/license-review.md` |

## 启动顺序一句话

被邀请 → clone → 第 0 层跑通 → 读 `AGENTS.md`/`Prompt.md`/自己的任务书 → **OpenCode Plan，停下等非作者批准测试与计划** → 才进 Build → Verify → 独立 PR。B/D 在动真实 PaperQA2 之前先完成第 1 层审批；任何模型调用先完成第 2 层批准。
