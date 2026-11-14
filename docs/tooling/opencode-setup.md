# OpenCode v2.0.12：受限开发流程

本指南对应仓库内 `$schema` 所指定的 OpenCode native v2 配置。权限键是 `permissions: [{action, resource, effect}]` 与 agent 局部同结构列表；不要套用 v1 `permission`/`instructions` 配置。校验清单 `.opencode/permissions.jsonc` 只是被静态检查的 manifest，不会被 OpenCode 自动加载；引擎实际读取 `opencode.jsonc`，项目指令以 OpenCode 对根 `AGENTS.md` 的发现机制为准。

## 模型与凭据由学生单独决定

`opencode.jsonc` 有意不设置 `model`、`provider` 或 `provider.use` deny 策略：此配置不阻断学生另行配置的获准 coding model，也不擅自选择或调用模型。学生应自己在 OpenCode 中完成授权，并确认模型、数据发送、费用、次数和重试。不要把 API key、`.env`、私有 auth 数据写入项目、测试输出或本指南。

开发助手 coding model 与 PaperTrace 产品运行时对论文/文档调用的 LLM 是两条不同路径。开发助手的 provider 配置不授予产品调用权限，也不改变产品的人工审批/引用/预算治理。离线验证只用本地 fake OpenAI-compatible endpoint 和显式合成 token；没有触碰真实 provider 或付费模型。

## Plan → test preparation → GitHub test approval → source Build → Verify

1. 在 PaperTrace 根目录检查 `.opencode/rules.md`、`AGENTS.md`、`.agent/rules.md` 和 `Prompt.md`。直接运行 `opencode` 默认使用 `papertrace-plan`；Plan 只读，输出单模块精确计划并停止。
2. 学生本人先审查并批准精确计划。之后由同一模块 `papertrace-build-A`…`papertrace-build-E` 角色只生成该模块独立 tests/、fixtures/和本模块设计记录；严禁写任何 `src/`，即使 native 工具权限此时允许源码路径。运行获准离线测试时可看到 RED。
3. 测试提案 PR 可以保持 open 且 RED，不需要为审批而合并。另一位未参与测试实现的学生必须在 GitHub 对绑定具体测试 commit 的 PR 真实 Approve。真实批准前，Build 不得行为上写任何本模块 src。
4. 获批后实现 PR 从测试 head 分支创建，描述包含精确字段 `Test approval PR: #N`；同一模块 Build 角色才继续源码实现，再由 Verify 独立核对。拒绝、沉默、假 review 或仅有角色/permission 都不授权。
5. 学生一次确认模块范围和精确常用离线命令后，范围内日常编辑不必逐文件重复授权；GitHub 对具体测试 commit 的独立审批仍是必需步骤。共享契约、跨模块、依赖、收费/费用、安全路径或预算越界仍立即停止。

角色权限只界定工具可触及的角色/路径范围，不证明真人身份或审批。测试准备阶段不写 src 是行为规则，不是新增角色、机器阶段门禁、OS sandbox 或身份服务。OpenCode 的路径匹配是 lexical；preflight 可拒绝当时存在的 symlink，但不能阻止后来替换或声称永久隔离。

命令行 one-shot 示例（把 `已获准的provider/model-id` 替换成学生自己已批准、已配置的 coding model 标识；不提供凭据）：

```sh
opencode run --agent papertrace-plan --model 已获准的provider/model-id \
  "读取 Prompt.md 与 AGENTS.md；仅为我指定的一个模块列出计划，停止等待人工审查。"

# 计划批准后，仅进入测试准备；具体测试commit经另一位学生GitHub批准后，才进行源码Build。
opencode run --agent papertrace-build-A --model 已获准的provider/model-id \
  "附上已批准计划；只生成A的测试/fixtures/设计记录，禁止写src。"

opencode run --agent papertrace-verify --model 已获准的provider/model-id \
  "只读检查diff与验证结果；指出负例、未验证项和限制，不做批准。"
```

这些命令不会自动检查真人身份或审批；`papertrace-build-A` 等角色也不是绕过 Human Review 的授权。请勿在命令行历史中粘贴密钥/私有审批材料。确需把审批材料传给 agent 时，仅附无秘密的版本号/范围/状态引用。

## 静态 preflight 与真实引擎探针

```sh
# 默认：可移植、只读的静态检查；不启动 OpenCode、模型或网络请求。
.venv/bin/python scripts/opencode_support.py

# CI 应由可信 base 脚本调用，并显式检查目标 checkout，而不是脚本所在目录。
.venv/bin/python scripts/opencode_support.py --root "$TARGET_CHECKOUT"

# macOS 可选：读回 OpenCode v2 配置并查询权限引擎；仍不启动模型或工具。
.venv/bin/python scripts/opencode_support.py --verify-runtime \
  --binary "$HOME/.opencode/bin/opencode" --root "$PWD"
```

`--root PATH` 在指定 checkout 内核验 `opencode.jsonc`、`.opencode/permissions.jsonc`、`.opencode/rules.md`、`AGENTS.md` 的治理标记/同步，以及 agent/manifest 角色、读写候选、protected/sensitive 路径、命令 allowlist 和 symlink/traversal。它只读配置/规则、不读取环境凭据，不启动模型；失败时 stdout 返回 JSON `status: FAIL` 并以非零退出。CI 可把可信脚本放在 checkout 之外，例如：

```sh
python "$CI_CONTROL/scripts/opencode_support.py" --root "$TARGET_CHECKOUT"
```

不要从不可信目标 checkout 执行 gate 脚本本身。`--verify-runtime` 是不同层级：它运行实际已安装 OpenCode 的 `/api/config` 与 `/api/session/.../permission` 探针，不调用模型或文件工具；不能冒充工具 E2E。

## 可复现离线测试

```sh
.venv/bin/python -m pytest -c papertrace.pytest.ini -q \
  test/offline/test_opencode_configuration.py

.venv/bin/python -m pytest -c papertrace.pytest.ini -q \
  test/offline/test_opencode_workflow.py

.venv/bin/python -m pytest -c papertrace.pytest.ini -q test/offline
.venv/bin/python -m ruff check --config papertrace.ruff.toml src/papertrace test/offline scripts
.venv/bin/python -m mypy --config-file mypy.ini src/papertrace
.venv/bin/python scripts/gates.py --gate schema
```

`test_opencode_workflow.py` 启动 loopback-only 确定性 fake，在 disposable checkout 通过 OpenCode v2.0.12 实际调用 Plan、同一 Build 角色的 test-only preparation、模拟测试审核后的源码 Build 和 Verify；fake 工具先只改测试并观察 RED，断言源码未变，再模拟审核，随后验证本模块源码写成功、跨模块写被拒和测试 GREEN。测试审核对象是模拟 fixture，不是真实学生/GitHub approval，也不证明模型服从性、身份或源码阶段的机器门禁。Native path permissions 仍允许该模块 src；禁止提前写 src 是行为规则。路径匹配是 lexical，symlink preflight 只是时点检查；macOS `sandbox-exec` 仅限制这次验证进程。公开 JSON 把个人绝对路径改为 `<repo>`/`$HOME`；准确 argv 仅保留于 `.local/unblock/opencode/workflow-commands.json`，不写进程环境/key。无 OpenCode/macOS 时 E2E 会 skip；skip 不等于通过。
