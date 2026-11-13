# 权限模型：按角色、文件、工具和数据默认拒绝

> 状态：**计划约束，待实际配置与正负验证**。本文不声称 OpenCode 的权限已强制执行；权限文件存在、schema 可解析、Agent 读了规则，都不是越权被阻止的证明。
> 约束来源：INV-06、INV-08、SEC-01、GOV-01、GOV-04；[根蓝图](../../architecture-blueprint.md)、[不变量](invariants.md)。课程项目第 5 页要求 file-level default-no-read/no-write，第 6 页另列 `.opencode/permissions.jsonc` 和 human-only rules。[1]

## 1. 两套权限，不可混淆

- **开发权限**：OpenCode / coding agent 能读取哪些代码、改哪些文件、运行哪些命令，由获批角色和真实工具边界限制。任务书里的“负责 D”不自动授予整个仓库写权限。
- **产品权限**：本机用户选择数据、C 接收明确人工决定、D 判断可否调用和发布。模型仅拿到允许的文本，不能调用 shell/文件工具，也不能自己批准 evidence、费用或发布。
- **初始化授权**：本轮只建契约、文档和工具；不等于已批准 A–E 实现、模型调用、远端建仓/推送或个人目录访问。架构起草角色不得代填任何学生批准。

## 2. 当前工具版本与配置职责

本轮主控环境发现 OpenCode **v2.0.12**；权限配置应按该版 **`permissions` 数组**核对，不沿用旧教程的 `permission` map。本架构子任务没有运行 OpenCode、加载凭据或验证该配置，因此实际 version/schema/规则加载与允许/拒绝的回执以主控交付为准，不在这里伪造 PASS。

| 文件 | 作用 | 不代表什么 |
|---|---|---|
| `.opencode/permissions.jsonc` | 课程要求提交的项目权限说明/机器可读合同 | 不能仅靠文件名认定当前 OpenCode 自动加载并执行 |
| `opencode.jsonc` | 当前已安装版本实际识别的项目配置入口；应映射本表与获批角色/工具规则 | 配置解析成功不等于 shell/插件/OS 任意 I/O 都被约束 |
| `.opencode/rules.md` | 课程指定 human-only always-on 规则 | 代理不能修改它来批准自己的越权 |
| `.agent/rules.md` | 课程 covenant、测试独立性、架构和上下文新鲜度 | 不是 OS 文件系统沙箱 |
| `AGENTS.md` / `Prompt.md` | 单入口、阅读顺序、先计划后人审的流程 | 不能用自然语言代替机器权限与人审证据 |

本文件不给未核实的配置片段；实际配置作者须用当前版本官方 schema/帮助核对数组字段、匹配优先级、角色选择和 always-on rules，并用受控无害 fixture 实测。**如果本表比实际机器配置更严格，以收紧为目标；不得把未执行的约束宣传成已有安全保证。**

## 3. 路径原则和公共只读集合

项目根记为 `<repo>`；所有路径相对此根。默认任何未列路径 **R=否、W=否**。批准目录 ownership 不等于批准目录全部文件；执行计划必须展开成**精确相对文件清单**，允许创建的新文件也要逐个列出。路径 resolve 后再验 root，拒绝 `..`、绝对路径与 symlink 逃逸；同一规则要覆盖 read/edit/apply_patch/write、终端、脚本和插件旁路。

公共只读集 **R-common**（所有获批角色可读，不可随意写）：

- `AGENTS.md`、`Prompt.md`、`architecture-blueprint.md`。
- `docs/req/prd.yaml`、`docs/req/requirements.yaml`、`docs/req/req-schema.json`。
- `docs/architecture/architecture-blueprint.md`、`adr/001-architecture.md`、`invariants.md`、`trace-matrix.md`、`memory-design.md`、`permission-model.md`、`runtime-policy-catalog.md`、`evaluation-table.md`、`evaluation-logbook.md`、`risk-list.md`、`option-ledger.md`、`source-register.md`（`adr/` 路径相对架构目录）。
- `src/papertrace/contracts.py`、`src/papertrace/__init__.py`、`docs/contracts/schema.md`。
- `docs/code-governance/structural-constraints.md`、`verification-constraints.md`、`mcp-tool-manifest.md`（后两者同处 code-governance）。
- `.opencode/permissions.jsonc`、`.opencode/rules.md`、`.agent/rules.md`、`opencode.jsonc`：仅在已确认不含秘密的项目版本中只读，禁止读取 home 全局配置。

路径写成简称的条目在机器配置中必须展开为完整相对路径。这里列的是**项目计划清单**；文件未存在时不可据此说已完成或从其他目录找同名私人文件替代。

## 4. coding agent 角色 × 文件级授权

R=只读；P=可起草提案但不能批准；W=只在批准计划的精确文件清单内写。下表中的 `service.py`、测试文件等为拟议落点，**不要求现在生成业务实现**；模块如需其他文件，先把精确路径加入计划、审查后再授权。禁止把示例路径扩成 `src/**` 写权限。

| 逻辑角色 | 增加的可读文件 | 可写文件（经单次获批计划） | 永远不能由该角色自授的动作 |
|---|---|---|---|
| Plan / 需求分析 | R-common、当前 `docs/team/module-X.md`、公开 baseline 定位摘要、当前变更 diff | P：`docs/plans/module-X-plan.md`、`docs/plans/module-X-test-plan.md` | 修改实现、批准自己的计划/测试、编辑 human-only 规则 |
| A Build | R-common、`docs/team/module-A.md`、`docs/team/integration-contract.md` | W：`src/papertrace/library/__init__.py`、`src/papertrace/library/service.py`、`test/offline/test_library.py`、`test/live/test_library.py` | 改 B–E、直接导入 paperqa、读取真实 home 文献/凭据 |
| B Build | R-common、module-B、integration-contract；下面列的冻结源码只读 | W：`src/papertrace/retrieval/__init__.py`、`src/papertrace/retrieval/service.py`、`src/papertrace/retrieval/gateway.py`、`test/offline/test_retrieval.py`、`test/live/test_retrieval.py` | 修改上游、导入第三方 pickle、未批模型/metadata 外呼、写审核账本 |
| C Build | R-common、module-C、integration-contract | W：`src/papertrace/review/__init__.py`、`src/papertrace/review/service.py`、`test/offline/test_review.py`、`test/live/test_review.py` | 自己伪造 human 操作、写已接受业务数据、直接修改历史事件 |
| D Build | R-common、module-D、integration-contract、B 公开接口文件（获批版本） | W：`src/papertrace/answer/__init__.py`、`src/papertrace/answer/service.py`、`test/offline/test_answer.py`、`test/live/test_answer.py` | 直接 import paperqa、放宽 accepted、改来源/人审、开启自动补证 |
| E Build | R-common、module-E、integration-contract | W：`src/papertrace/reports/__init__.py`、`src/papertrace/reports/service.py`、`test/offline/test_reports.py`、`test/live/test_reports.py` | 覆写旧报告、删除审核/来源、伪造 released 或成员信息 |
| 契约维护 / 集成 | R-common、所有模块获批公开接口、`test/offline/test_contracts.py` | P/W：`src/papertrace/contracts.py`、`docs/contracts/schema.md`、契约 tests/fixtures；`src/papertrace/app.py` 仅另批 UI 集成计划后 | 单方修改安全合同、借集成任务提前实现 A–E、改 human-only 规则 |
| 架构起草 | R-common、经授权的课程原文提取/审计材料与冻结源码 | P：根蓝图和 `docs/architecture/` 中逐个批准的 Markdown | 标记学生已批准、替教师解释课程歧义、写业务代码 |
| Verify / 独立测试 | R-common、对应模块及冻结版本 tests、受控合成 fixtures、最小运行结果 | 独立验证记录、批准清单内新负测；不得改实现或事前批准测试基准求绿 | 自签批准、删失败断言、用 live 代替无预算离线验证 |
| PR Review | R-common、该 PR diff/测试结果、受控报告 | P：`docs/review-memo.md` 中真实审查草稿；必要 debt/bug 条目按实际事实追加 | GitHub 人工 approve、merge、推送、覆盖历史 memo |

表中 module-X 表示完整路径 `docs/team/module-X.md`。过程角色可轮换，A–E 功能 ownership 不变；轮换不叠加前一角色写权限，切换后撤销旧许可。课程项目第 4 页要求轮换责任，不能把功能 ownership 误解为永久管理职务。[1]

**B 与架构只读 baseline 白名单**：`src/paperqa/docs.py`、`types.py`、`settings.py`、`core.py`、`readers.py`、`llms.py`、`prompts.py`、`agents/main.py`、`agents/env.py`、`agents/search.py`、`agents/tools.py`、`agents/models.py`、`agents/__init__.py`（后续条目均相对 `src/paperqa/`）；`pyproject.toml`、`uv.lock`、`LICENSE`；所需 parser 的精确 reader 文件与测试 node 来源。运行前展开文件名；额外源码只读需求也先加清单。上游写权限对所有 AI 角色均否。

## 5. 无条件禁区与需要单独授权的区域

| 区域 / 行为 | 默认权限 | 原因与例外流程 |
|---|---|---|
| `src/paperqa/**`、`packages/**`、原 `tests/**` | 已列文件可 R，所有 W 否 | 冻结 baseline；发现缺陷先 ADR+人工明确重开，不静默修改 |
| `.opencode/rules.md` | 已授权项目副本 R，W 否 | 课程 human-only；AI 可提供建议差异，不代改或自签 |
| 任何真实 key/token/cookie/.env、钥匙串、SSH、浏览器 profile、全局 provider 配置 | R/W 均否 | 不能为“检查有没有 key”读取；凭据由持有人通过安全边界注入获批 live 进程 |
| 仓库外个人目录、无关项目、用户历史 | R/W 均否 | 不以默认工作目录或工具可达性推断授权 |
| `.git/**` 写入、`git add/commit/push`、remote/branch protection 修改 | 否 | 编码代理不 commit/push；初始化主控按本轮委托只做本地初始化提交，后续推送由另获授权的人执行，AI 不私自变 remote |
| `.papertrace/**` 真实运行数据、原论文和历史 | coding agent 默认 R/W 否 | 只可用获批脱敏副本/精确对象，不让测试便利变成数据读取许可 |
| `test/fixtures/**` 合成样例 | 只列明具体样例才可 R/W | 禁止加入真实成员身份/密钥/未经许可论文全文 |
| 真实模型、embedding、metadata、OCR HTTP 或 tokenizer 下载 | 否 | 先单独批准 provider/model/数据/金额/次数/配置；安装依赖许可不等于模型许可 |
| 工作流/依赖/权限/规则/发布门修改 | 仅提案，正式写需受控计划 | 安全路径要 ADR+学生审查；不得改默认权限来绕过本表 |

## 6. 工具与命令

默认允许的是最小只读文件工具、获批精确文件编辑、受限 Git 只读状态/diff、隔离环境中的已审脚本/测试。网络浏览/外部搜索仅在任务另许且不上传私有数据时开放；运行时模型没有这些工具。

终端是重点旁路：批准 `python`、`sh`、`curl` 或任意脚本，可能绕过编辑工具的路径规则。不能只限制 `edit` 就宣称 no-read/no-write。若执行器无 OS 级隔离，应拒绝通用 shell，只白名单**脚本路径+内容版本+参数+工作目录+输出目录**，剥离真实凭据并限定网络。脚本变化后重审；测试 `-m offline`/socket monkeypatch 是局部证据，不是整机出站沙箱。

禁止安装/升级工具或依赖以悄悄修过测试；安装须另批范围与许可，网络获取和模型调用分别计量。所有自动修复命令可能写文件，不可在只读验证中默认运行。

## 7. 产品侧文件与授权矩阵

| 主体 | 可读 | 可写 / 可决定 | 不可决定 |
|---|---|---|---|
| 本机用户（明确选择） | 其有权处理的文献、当前/历史证据和报告 | 导入、接受/排除/重置、明确预算授权、导出 | 不因本机可读就获得论文再分发许可 |
| A | 托管来源、当前/旧快照 | 新文献版本、新快照、current 指针 | accepted 与发布 |
| B | 指定快照来源、候选/获准证据、获批许可 | 可重建表示、候选记录、调用账目 | 人审与 release |
| C | 本问题候选与原文、其审核历史 | 真实人机交互产生的追加决定/revision/digest | 模型事实与预算 |
| D | 当前 A/C 投影、本轮 B 原始输出/调用账目 | context scope、AnswerDraft、ReleaseDecision | 重写人审/来源、给模型工具或扩大预算 |
| E | 已核的报告包与许可范围内来源 | 新报告、追加 superseded 注记、导出副本 | 将 blocked/stale 当当前 released |
| 模型/provider | 仅本轮最终 payload 内文本 | 返回建议草稿/摘要 | 文件、工具、ledger、policy、身份、预算与发布 |

## 8. 必须取得的真实验证证据

1. 记录实际 OpenCode 版本、schema、规则加载来源、角色选择与展开后的精确白名单，不读取全局秘密配置。
2. 用自建无敏感 fixture 验证：允许范围可读写；未列路径/其他模块/冻结副本/规则文件/仓库外 sentinel 不可读写；路径穿越和 symlink 同样拒绝。
3. 用无害命令验证禁止 git push、通用 shell、网络/模型；不用真实 key 测拒绝，不真的尝试远端破坏。
4. 检查实际文件字节与工具拒绝回执，区分“规则生成”“配置识别”“工具拦截”“OS 隔离”四层；无法证明的一层标未验证。
5. 将结果给独立 reviewer 与学生审查；没有远端保护管理员授权时，只能标“待授权”，不宣称 required checks 生效。

未通过上述验证时：停在计划/只读分析，不开始正式业务开发；真实权限修复由主控/持有人批准后执行。本文件不预填验证结果。

## Sources

[1] urn:sha256:6af742d3cbc0973b056a084ba54ff413a5885b1bb4d6a97b0b08b93f64f2ef7e — CS5351-2026-2027-project.pdf（本地原文提取，10页）
