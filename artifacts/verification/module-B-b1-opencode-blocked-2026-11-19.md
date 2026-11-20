# B1 OpenCode 测试准备阻塞记录

- 日期：2026-11-19（Asia/Hong_Kong）。
- 阶段：模块 B 的 B1 测试准备；尚未进入 B2 源码实现。
- 分支：本地 `test/B-retrieval`，起点为已推送的 Plan v2.1 提交 `6fd25d0`。
- 授权：学生明确允许将 Plan v2.1、本人批准记录和 B1 测试设计发送到学校托管的 OpenCode 模型，用于生成离线测试及 synthetic fixtures。

## 实际结果

按已批准范围启动新的 `papertrace-build-B` 会话，指定学校模型
`cityu/CS5351/DeepSeek-V4-Flash`，未使用 `--auto`。请求在建立会话前失败：

```text
{"type":"error","sessionID":"","error":{"type":"unknown","message":"UnexpectedStatus"}}
```

随后只读探测 OpenCode 模型列表，两次均返回：

```text
ClientError: UnexpectedStatus
cause: {"status":502}
```

## 边界与当前状态

- 没有 OpenCode session ID；不能把本轮登记成成功开发会话。
- `test/offline/test_retrieval.py` 和 `test/fixtures/retrieval/` 尚未创建。
- 没有修改任何 `src/`、共享 contract、其他模块、上游、依赖、CI 或规则。
- 没有切换模型/provider，也没有对实际生成请求做自动重试。
- 本地 Git 工作树在写入本记录前保持干净；GitHub 未创建 B 测试 PR，也未进行评论、重复审批或其他批量操作。
- 下一次实际模型请求须由学生明确批准受控重试；若学校 provider 仍不可用，继续保持 BLOCKED，不能由 Codex 手写测试冒充 OpenCode 过程。

## 2026-11-20 受控重试与部分生成

学生于 2026-11-20 明确要求继续，并随后逐项授权把共享契约、B 集成说明、需求、现有离线测试范例和 pytest 配置发送到同一学校托管模型。恢复同一 OpenCode 会话 `ses_e0b52e19cffeKNNWGvabD35xQ7`，未使用 `--auto`，未切换模型/provider。

本次会话先因非交互 shell 权限被自动拒绝；随后改为禁止 shell，只允许已授权文件的逐文件读取和 B1 白名单路径写入。OpenCode 成功创建以下 synthetic fixtures：

- `test/fixtures/retrieval/source-a.txt`
- `test/fixtures/retrieval/source-b.txt`
- `test/fixtures/retrieval/fake_adapter.py`
- `test/fixtures/retrieval/README.md`

在继续创建 `test/offline/test_retrieval.py` 前，学校 provider 返回 HTTP 400：

```text
The `reasoning_text` in the thinking mode must be passed back to the API.
```

因此当前仍为 **PARTIAL / BLOCKED**：主测试文件尚未创建，测试设计尚未由该会话更新，未运行 B1 pytest，未创建 commit/PR。已生成 fake adapter 通过本地 Python 语法编译；fixture 与本记录的敏感字符串/个人绝对路径扫描无命中；工作树无 `src/`、共享契约、其他模块、依赖、CI 或治理配置变化。模型失败后没有自动再次请求，也没有 GitHub 操作。

## 2026-11-20 单轮新会话与首次 RED

学生再次明确批准一次新 OpenCode 会话。新会话 `ses_e075ae192ffeqS0IgLofyGjpFw` 使用相同 CityU 模型和 `papertrace-build-B`，通过已授权附件在首轮成功创建 `test/offline/test_retrieval.py`；未使用 `--auto`，其后未经批准的 shell 请求被规则自动拒绝。

主测试文件与 fake adapter 均通过 Python 语法编译。使用批准 runtime 的实际命令：

```text
../PaperTrace-plan-B-liyafei/.local/unblock/runtime/.venv/bin/python -m pytest -c papertrace.pytest.ini test/offline/test_retrieval.py -q
```

结果为 `3 passed, 45 failed`。collection 成功，但 45 项首先暴露测试夹具加载错误：动态加载 `fake_adapter.py` 时未在 `exec_module` 前把模块登记到 `sys.modules`，导致 dataclass 解析字符串注解时抛出 `AttributeError`；这不是计划要求的“明确报告 B gateway 尚未实现”的 RED。

同一会话按窄范围修正时成功加入 `import sys`，但在写入 `sys.modules[spec.name] = module` 前再次遭遇学校 provider 的 `reasoning_text` HTTP 400。当前仍为 **PARTIAL / BLOCKED**，不提交、不创建 PR；没有 `src/` 或 GitHub 变化。下一次模型请求需学生再次明确批准，仅完成这一行机械修正并重新运行 RED。

## 2026-11-20 B1 RED 就绪与正确基线

学生再次明确批准单行修正；同一 OpenCode 会话成功写入 `sys.modules[spec.name] = module`。随后模块测试正常收集 48 项，结果为 `3 passed, 45 failed`；45 项均以清晰的 `B1 RED: approved Module B gateway is not implemented yet` 失败，符合 B1 尚无业务源码的预期，不再由 fake 初始化错误遮挡。

原本地测试分支来自独立 `plan/B-liyafei` 历史，与固定 gate 基线无共同祖先。没有放宽 gate；改为只读获取当前 `main`，从 `main` head `1b03c491628d39b6b3f881356424afb1e18d3bd8` 创建本地 `test/B-retrieval-proposal`，并把已批准 Plan/B0 文档提交以正确身份迁入，当前文档提交为 `dcc0401`。该过程未推送、未创建 PR、未评论或审批。

验证结果：

- 模块测试：`3 passed, 45 failed`，失败均为预期 gateway 未实现 RED。
- 完整 `test/offline`：`353 passed, 51 failed`；其中 45 项为上述预期 RED，另外 6 项为主分支共享契约 `KeyError`、沙箱禁止 `ps`、runtime 缺 Ruff/mypy 导致的 gate 自测，以及 OpenCode 环境工作流自测，不修改 B 测试来掩盖。
- 共享契约单测：`148 passed, 1 failed`；唯一失败是现有 `EvidenceRecord` 在缺少 `schema_version` 时抛 `KeyError`，B 不得修改共享契约。
- schema gate：`PASS`，27 条需求结构验证通过。
- 新增 Python 文件语法编译：`PASS`。
- 补充 Ruff 0.17.5 对 `test_retrieval.py` 和 `fake_adapter.py`：`PASS`。批准 runtime 本身没有 Ruff/mypy，因此批准命令中的 Ruff/mypy 标为 `BLOCKED/NOT_RUN`，没有下载或改锁。
- 敏感信息/个人绝对路径扫描：无真实命中；测试中仅有用于拒绝绝对路径的字面量断言。
- `src/`、共享契约、其他成员模块、依赖、CI 和治理配置：无改动。

当前剩余 B1 工作是把 OpenCode 生成的具体测试接口与真实状态回写 `test-design-v2.1.md`，随后重新核对、创建测试提案 commit，并等待非测试作者对精确 commit 的 GitHub Approve；B2 仍未开始。

## 2026-11-20 设计状态更新与事实一致性修正

OpenCode 会话 `ses_e0745d58fffei0NNwkEjinDmtc` 已把实际 B1 API 提案、RED 结果和未批准边界回写 `docs/team/designs/module-B/test-design-v2.1.md`，没有修改其他路径。人工核对随后发现四处仅涉及事实准确性的表述：OpenCode/Codex 分工、`FakeCitationClaim` 的实际字段名、验证记录文件清单，以及本次设计会话 ID。

尝试恢复同一会话进行窄范围更正时，本机 `opencode` 在模型调用前拒绝项目的 V2 权限配置，并提示使用当前环境并不存在的 `opencode2`；因此没有发生新的模型请求。为避免重复请求，Codex 只对上述四处做机械事实修正。测试、fixtures、测试断言和任何 `src/` 文件均未改变；这些修正不构成学生批准，B1 仍为 RED，B2 仍为 NOT_STARTED。

## 2026-11-20 PR #9 COMMENT 后的门禁归因

PR #9 对提交 `4e88d04d7c35b92cf665e1f5be025e9d5584a1db` 收到的是技术 **COMMENT**，不是独立学生 **APPROVE**。评论确认 B1 测试范围与 3 passed / 45 expected RED 合理，同时指出 AI-use log 尚无本轮新增记录，以及仓库级 static-analysis 的 Ruff 子检查失败。

本轮按 append-only 规则在 `docs/ai-use-log.yaml` 新增 `B-TEST-20261120-01`，如实列出三个 OpenCode 会话、学生授权与非审批边界、Codex 干预、验证结果、provider 400 和本机 OpenCode 权限版本限制。

使用现有本地 Ruff 0.17.5 执行与 gate 相同的范围：

```text
ruff check --config papertrace.ruff.toml src/papertrace test/offline scripts
```

精确结果只有一项：`scripts/paperqa_smoke.py:37:1 I001 Import block is un-sorted or un-formatted`，退出码 1。该文件不在 PR #9 改动中；此前 `C-SRC-20261117-01` 已记录同一既有问题。B 的 `test/offline/test_retrieval.py` 与 `test/fixtures/retrieval/fake_adapter.py` 单独 Ruff 仍通过，因此不越权修改无关脚本，也不放宽 gate。

`test-approval` 的 `test-proposal-only-do-not-merge-red-tests` 阻塞是 B1 阶段预期状态；不为此提前编写 B2 或合并 RED PR。新增披露将产生新的精确 head，须由未参与 B1 测试编写的学生重新审核并在 GitHub 正式 Approve。
