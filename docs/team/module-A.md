# 模块 A｜文献库、导入状态与版本快照

> **Owner A：**端到端负责文库功能、需求、设计、监督 OpenCode、测试、自己的 view 与 PR。此任务书给出可审核验收，不代表功能已实现或本轮 Build 已获批。
>
> 统一从[团队启动入口](../../TEAM_START_HERE.md)进入；接口事实源为 [`integration-contract.md`](integration-contract.md) 与真实 `src/papertrace/contracts.py`。

## 用户结果与责任

研究者明确选择获授权的本地 PDF/TXT；每个文件都有可解释的导入状态；可用文献组成固定快照；换版或移除只改变新快照，旧快照仍可追溯。

A 负责 logical document identity、源字节 SHA256 version、托管来源、逐文件状态和 ready-only `CorpusSnapshot`。B 负责受控解析/表示调用；A 保留导入事实，不能把 B 返回的错误记成 ready。A 不做检索、人审或答案发布。

## Must 与可验收结果

| 需求/不变量 | 必须行为与验收 |
|---|---|
| `FR-A-01` | 仅处理用户明确选择的 PDF/TXT；逐项报告成功/失败及阶段/原因。逻辑文献 ID 与内容 SHA256 分离；同名换字节产生新版本；无效、空、越界路径或解析失败不能伪装 ready。 |
| `FR-A-02`, `INV-02`, `INV-05` | 内容/成员变化生成新快照；旧快照与历史记录字节不变。快照只含 ready 的 `DocumentVersion`，源文件/hash 不匹配时拒绝下游使用。移除不宣称物理擦除上游向量。 |
| `INV-06`, `QA-01`, `SEC-01` | 服务层和 view 共用路径/类型/身份校验；合同使用真实模型/哈希实现；无路径外读写、绝对路径泄漏或个人资料。 |

Fit criterion/优先级以 `docs/req/requirements.yaml` 为准，不在任务书复制或放宽阈值。

## 边界与拟议改动范围

- **交给 B：**受控文件、人工元数据、显式配置；接收成功/失败阶段。默认假设任何解析/embedding 可能外呼，不能把本地导入称为离线。
- **交给 C/D/E：**固定 snapshot 和版本核验/受限来源读取接口；不交可变 PaperQA 对象，也不允许模块直接改 A 的文件。
- **常规模块范围（在 Plan 一次确认；范围内日常编辑/新增文件不逐次批准）：**`src/papertrace/library/`（服务与自己的 view）、`test/offline/test_library.py`、`test/fixtures/library/`。批准本轮范围后沿用对应 Build 角色权限；共享 contracts/fixtures、入口/编排、需求、依赖/锁、CI、日志与上游基线均另批。
- 上游修复依 ADR-002 受审 patch 流程；不得在模块 PR 裸改固定基线。不能读取 `.env`、`~/.pqa`、密钥或未获许可论文目录。

## 不等 B 的 fake 开发与验收

用规范 `CorpusSnapshot` / `DocumentVersion` 与自写 synthetic TXT/小 PDF；注入 fake parser/import port，能返回成功、解析失败、超时并记录输入。fake 不初始化模型、网络或真实上游。

最少验证：合法导入和逐项状态；同字节重复策略、同名不同字节换版；坏/空文件、路径穿越、部分失败；源 hash 变化/读回丢失；旧快照不变；服务直调绕过 view 仍拒绝越界。校验快照只含 ready，failure 不丢失不伪装；身份通过共享模型计算，不手填随机 hash。完整离线团队回归及 gate 状态以真实执行证据为准，任务书用例不是 PASS。

## D1–D9：A 应留下的模块证据

| 项 | 本模块证据 |
|---|---|
| D1 | `FR-A-01/02`、`INV-02/05` 的 registry fit → 用例/trace 映射及变更来源。 |
| D2 | 状态机、版本/快照/移除、B 摄取 port、异常与历史策略；安全语义改动的 ADR。 |
| D3 | 本轮精确路径/工具授权、受限来源存储及冻结基线/例外审计证据。 |
| D4 | 事前批准测试版本、路径/换版/失败负测、团队回归、真实 review memo 与 bug/debt。 |
| D5 | 学生真实监督 OpenCode 的完整原始会话和人工干预理由；不得把 Hermes 初始化算作成员开发。课程 transcript 数量口径待学生/教师确认。 |
| D6 | A 的真实功能/协作贡献与反思素材；身份和贡献由本人填写，禁止预写。 |
| D7 | 本地 diff、真实 PR/CI/独立审查及分支保护的实际读回；当前已知保护 403 未生效，最终须复核。 |
| D8 | 文库服务/view、synthetic fixtures、正负/回归和可复现命令。 |
| D9 | 根 `Prompt.md` 启动、Plan 停止及测试/计划/路径批准、监督 Build/Verify 记录。 |

模块验收还须证明端到端用户结果、人工审批先于实现、真实独立审查；不以任务书或空壳视为完成。