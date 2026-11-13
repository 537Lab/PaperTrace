# PaperTrace｜五人工作计划与协作规则

## 1. 产品目标、现状与事实来源

PaperTrace 是基于 PaperQA2 的 Evidence Review Workbench。研究者导入自己的论文，检索出候选证据，查看原文并人工接受或排除，再请求只使用获准证据的回答，最后保存问题、证据、审核、答案和版本的可追溯记录。

**本轮只做开发前基础：共享数据契约、合成测试及离线门禁，不预先实现五个成员的业务功能。**任务书中的源码目录、界面和业务验收是后续成员的交付范围，不表示现在已有可演示应用。初始化文件的创建、实际验证、外部授权和业务实现分开记账；最新实跑状态看 [docs/ci/gates.md](docs/ci/gates.md)，不能从文档存在推断测试通过。

固定上游：`https://github.com/Future-House/paper-qa`；源码基线：`c692d0dfeac4a0296599f7fe21a253a58b7ac12a`。上游只读，**团队 GitHub 仓库尚未创建，origin、仓库访问与 branch protection 待授权**。默认目标是新的私有团队仓库，不得擅自公开、推送上游或填写猜测的 owner/URL。

### 课程依据（已读原文提取全文）

| 来源 | 本项目采用的要求 | 仍须学生确认 |
|---|---|---|
| `CS5351-2026-2027-project.pdf` p3–4 | 真正 AI 组件、确定性安全边界；支持角色轮换 | 以固定功能 ownership 加流程角色轮换是否满足教师期望 |
| 同文件 p5–7，D1–D9 | 机器需求、架构、编码/验证治理、真实 transcript、过程报告、仓库、源码测试、静态启动 Prompt | p2“五份 annotated transcripts”和 p6 D5“一份 full raw transcript/from scratch”的口径；基于上游扩展与 from scratch 的协调 |
| 同文件 p8–10 | ZIP、目录结构、六类 blocking gates、分支保护 | 蓝图根目录与架构目录的表述差异；若教师更新，以最新原文为准 |
| `cs5351-2026-2027-introduction.pdf` p5、20 | 评核基于 OpenCode；学生监督生成、原则性干预；可选相近复杂度项目 | Hermes 初始化如何披露/复核；正式代码生成不得用本次初始化冒充 OpenCode 贡献 |
| 同文件 p7、23 | 暂定 Week 13 项目截止；ZIP 与独立 10 分钟演示视频，比较新增需求前后行为 | 确切日期、时区、入口以及是否有更新通知；视频不塞进项目 ZIP |

本次团队材料只使用 A–E 代号，无真实姓名、学号、个人账号或假定组长。**匿名只适用于这些启动材料**：D6 最终 `Report.md` 必须由学生本人按课程要求填写真实姓名、学号、相对贡献及每人的真实反思；不能因匿名要求漏交 D6 身份字段。课程 p6–7 同时要求报告不超过 10,000 词（不计图），12pt、单倍行距超过 15 页，每人一段约 300–500 词反思；Markdown 的最终排版口径须学生核实，不因本轮启动文档格式而宣称 D6 已合规。D5 的原始记录和身份命名要求由学生按教师最终口径处理，不能合成记录。

## 2. 固定的五功能 ownership

| 模块/任务书 | 必须拥有的用户功能与设计/测试责任 | 后续源码与界面范围 | 上下游 |
|---|---|---|---|
| [A](docs/team/module-A.md) | 文献库管理、导入状态、逻辑文献身份和版本、不可变快照 | `src/papertrace/library/`，本模块 view；首个轻量 app 装配 PR | 向 B 提供文库快照，向 C/D/E 提供版本核验 |
| [B](docs/team/module-B.md) | 本地文献到候选证据的检索与 PaperQA2 映射；隔离第三方 API | `src/papertrace/retrieval/`，本模块 view；唯一 `paperqa` import 边界 | 接 A，向 C 提供 EvidenceRecord；按 D 授权执行受控生成底层调用 |
| [C](docs/team/module-C.md) | 原文/摘要比较、人工接受或排除、追加式审核账本 | `src/papertrace/review/`，本模块 view | 接 B，向 D/E 提供指定 revision/digest 的审核记录 |
| [D](docs/team/module-D.md) | 构建获准/实际发送/实际引用三集，受控回答和发布门 | `src/papertrace/answer/`，本模块 view，模块专属版本化生成提示词 | 接 A/B/C，经 B 的中立端口调用底层模型，向 E 给出草稿和发布结论 |
| [E](docs/team/module-E.md) | 历史列表、完整研究记录、导出与来源追溯 | `src/papertrace/reports/`，本模块 view | 读 A/B/C/D 的不可变结果，不更改授权或重新生成答案 |

每人均对本模块的**需求 → 设计 → 监督 OpenCode → 正负测试 → PR → 演示**负责，并补 D1–D9 对应证据。不能把 A 改成只做集成、B 改成只装依赖、E 改成只写文档；本模块 UI 是本人的功能交付之一。

默认采用 Python、薄适配层和简单 Streamlit 本地界面。Streamlit/业务依赖另经计划审批安装；不引入大型前端、云平台、服务端数据库、多租户或新的自治 Agent。业务模块目录由成员的获批 Build 创建，本轮不创建五份空业务壳冒充功能。

## 3. 共同的需求与接口底线

需求的机器事实源是 `docs/req/requirements.yaml`，产品 PRD 为 `docs/req/prd.yaml`，字段/优先级/fit criterion 以 registry 为准；二者须共演化，不要在各任务书生成第二份 registry。长期功能 IDs 固定：

| 模块 | 功能需求 IDs | 应提供的观察结果 |
|---|---|---|
| A | `FR-A-01`、`FR-A-02` | 导入逐项状态；逻辑 ID、SHA256 文献版本及内容哈希快照 |
| B | `FR-B-01`、`FR-B-02` | 候选证据可定位原文；适配器不越过审核边界 |
| C | `FR-C-01`、`FR-C-02` | 原文比较和显式人工决定；可重放的审核 revision/digest |
| D | `FR-D-01`、`FR-D-02`、`FR-D-03` | 仅发送获准证据；核查实际引用与新鲜度；空获准拒绝调用 |
| E | `FR-E-01`、`FR-E-02` | 历史可恢复；导出保留证据/审核/版本/发布原因 |

所有成员同时遵守 `INV-01`–`INV-08` 和 `QA-01`、`PERF-01`、`COST-01`、`SEC-01`、`GOV-01`–`GOV-04`。具体阈值、责任与测试映射看 registry、`docs/architecture/invariants.md`、`docs/architecture/trace-matrix.md`；本工作计划不另设性能成绩或放宽零容忍不变量。

共享模型只有 `src/papertrace/contracts.py` 的 `CorpusSnapshot`、`EvidenceRecord`、`ReviewDecision`、`AnswerDraft`、`ReleaseDecision`。先用规范合成 fixtures 序列化/反序列化，不能自造不兼容模型、把字符串“accepted”藏进检索分数或 UI 状态充当授权。详细交接、应用编排和契约变更流程见[集成合同](docs/team/integration-contract.md)。

### 不可绕开的安全行为

- 文献逻辑 ID 与内容版本分开；同名替换不能沿用旧版本。历史结果绑定原快照，不自动切换到最新文件。
- EvidenceRecord 的摘要/相关度是建议，不是批准；没有 ReviewDecision 即 pending。只有真实 human 操作能写接受/排除，账本保存 revision/digest。
- D 先从指定快照及审核版本构建 `approved`，在预算内构建实际 `sent`，从原始生成结果解析 `cited`；必须 `cited ⊆ sent ⊆ approved`。三集相同不作为默认假设。
- 生成前后快照及审核版本须一致。中途替换文献、撤销审核、超时、未知引用、输出截断等情况保留草稿/失败原因，但不发布。
- 无获准证据或预算裁剪后无可发送证据时不调模型。检索失败不能降级为全库回答。
- 第三方 `Docs.aadd`/`aget_evidence`/`aquery` 都只在 B 适配器内部；D 决定输入与授权，不直接导入 `paperqa`。生成使用新的已过滤 session，关闭 `get_evidence_if_no_contexts`，`pre/post=None`，不用自治 Agent，不复用带旧 contexts 的 session。
- 不接收别人给的 pickle 索引，不扫描个人 `.pqa`、`.env` 或凭据目录。离线 fixture 不等于真实模型语义评估。

## 4. 相对检查点与可并行工作

**S0–S4 是团队建议顺序，不是教师 DDL。**每个 sprint 建议 1–2 个工作日；开始、结束、可投入时间与 Week 13 确切截止均待学生确认。若资源不足，先减非 Must 范围，不减不变量、人工审批或真实证据要求。

| 检查点 | 各人的可执行工作 | 必须留下的退出证据 |
|---|---|---|
| S0：阅读与认领 | 各自审核需求/任务书，确认工具与课程口径；跑共享离线测试；用 Plan 产出模块计划、端口和测试 | 功能认领，测试批准与计划批准的真实记录；未解决课程/授权项清单；无业务实现提前开始 |
| S1：fixture 纵切片 | A 做库/版本；B 做中立检索映射；C 做审核比较/ledger；D 做纯发布门和 fake backend 调用记录；E 做历史/导出；各自先交最小可测试功能 | 每模块正例、负例、回归；自己的 view；所有 fake 明示为合成，不写 live PASS |
| S2：离线集成 | 先合接口，再接 A→B→C→D→E；A 的首个装配 PR 只装配导航/依赖注入；后续装配由轮换集成人做小 PR | 端到端合成链；同名替换、审核撤销、串 snapshot、未知引用、空批准等跨模块阻断证据 |
| S3：获批 live 与语义评估 | 只有离线通过并单独批准 provider/model、数据、请求数/重试和金额后，由 B/D 协作试真实链，所有人提供其功能语义样例 | 原始请求/回复、模型与提示词版本、usage/费用、固定评估集与真实阈值结果；未授权则明确 BLOCKED，不造成功结果 |
| S4：交付演练 | 每人演示功能与一次人工干预，核查 D1–D9/六门禁；复跑最终包并准备报告和独立视频 | 每份 PR 交接、五份真实 annotated transcript 的准备情况、学生填写的最终身份/贡献、实测清单与剩余问题 |

### 不等上游的开发方式

A 用自写小文件和 fake import backend；B 用合同合法的快照与模拟 parser/检索结果；C 用有原文、有冲突的 EvidenceRecord；D 用固定审核 ledger 和能记录“实际发送内容”的 fake backend；E 用完整合成研究记录及被阻断草稿。共享样例在 `test/fixtures/contracts/`，模块专属材料拟放 `test/fixtures/<module>/`；每份标明 synthetic、版本、预期结果，具体文件须列入批准计划。wrapper 的 `data` 才是共享模型输入。

上游真实实现尚未合并，不是等待理由；但合同缺字段、批准模型/数据缺失、安全含义不明时必须登记并停止相应集成，不能补造事实。fixture 只验证结构与逻辑，不能把 fake backend 的固定答案称为 AI 质量达标。

## 5. 一份 PR 从 Plan 到合并

1. **作者准备：**列需求 IDs、受影响不变量、输入/输出/失败、可写路径、依赖及测试。OpenCode 首次只 Plan，不能先 Build 再补审批。
2. **测试事前批准：**非作者检查每个 fit criterion、至少一个负面用例/功能及不变量故意违反会失败的测试。记录批准人代号、计划/测试版本、允许路径与时间；聊天中的笼统“可以”不能代替可追溯审批。
3. **计划/权限批准：**确定每步可审查产物，单独确认本次 Build 写路径和工具权限。安全关键变更附 ADR 和人工批准。测试批准不自动授权读取凭据、联网或推送。
4. **监督 Build：**按批准步骤小批生成；人工在接口、风险或失败点中断并写理由。需求/合同/测试语义变化就回到审批，不让 Agent 通过放宽测试“修好”。
5. **Verify：**跑完整团队离线回归及门禁；live 按授权单独执行。保留命令、退出码、版本和原始输出；0 tests、skipped 和 BLOCKED 不算通过。
6. **独立审查：**非作者按 `docs/review-memo.md` 评规格、架构、代码、测试、效率/安全，给出 `APPROVE` / `CHANGES REQUIRED` / `REJECT`。作者不能自己审批或将 Agent 自评当人审。
7. **集成：**GitHub 授权前准备本地分支/diff 和证据，不捏造 PR 编号。授权后由轮换集成人核对 required checks、审批、ADR 与 AI-use log，再合并；合并后的全套回归失败立即停止继续集成。

已有 `AGENTS.md` 和 `Prompt.md` 是实际启动入口，不另起绕过它们的“一句话全自动开发”提示词。`.opencode/permissions.jsonc` 是课程提交 manifest，**不是 OpenCode 引擎实际生效权限的保证**；运行配置是当前版本对应的 `opencode.jsonc`。查看二者及实际权限验证证据，不修改为 `allow all` 解决权限错误。本轮 OpenCode 版本为 v2.0.12，升级也须重新验证配置。

## 6. 支持角色轮换：不改变功能 ownership

课程 p4 要求体验不同责任，本项目用“固定功能负责人 + 每轮非作者轮换支持职责”实现。一次 PR 的作者仍对本模块端到端负责；测试批准人、独立 reviewer、集成人都来自其他成员。若某人实际参与实现而成为共同作者，本轮不得再充当该 PR 的独立批准/审查者，需重新排人并记录。

第一轮采用下表（代号不是职务头衔）：

| PR 作者 | 测试/计划批准人 | 独立 reviewer | 集成人 |
|---|---|---|---|
| A | B | C | D |
| B | C | D | E |
| C | D | E | A |
| D | E | A | B |
| E | A | B | C |

下一轮沿 A→B→C→D→E 环依次顺移：第二轮相对作者取后第 2/3/4 位，第三轮取后第 3/4/1 位，第四轮取后第 4/1/2 位，再循环。三个角色彼此不同且都不是作者。每个新 PR 在讨论记录写明本轮安排；缺席可由其他非作者替补，但不能默认为某人永久负责 CI 或管理。若待合 PR 的集成人也是其作者，立即换非作者；多人合写的装配 PR 同样适用。

## 7. 可改路径、共享文件与沟通

- 成员的模块目录只是候选边界，不是整目录自动写白名单。Plan 必须列出拟读写的精确相对文件，包括新增 view 与 fixture，再取得本轮窄范围权限；实际权限以 `docs/architecture/permission-model.md` 和生效配置为准。新增函数/模块注明关联 ADR、需求/不变量。
- `src/papertrace/contracts.py`、共享 fixtures、`docs/req/requirements.yaml`、架构/治理文档、`docs/ai-use-log.yaml`、review/debt/bug 共享日志、`prompts/`、依赖锁、CI 和 app/应用编排入口属于共享敏感区。需要附精确 patch、预约同一轮编辑者和非作者审查；日志必须真实更新，不能因“共享”而漏记。
- 原版 `src/paperqa/`、`packages/`、`tests/`、`pyproject.toml`、`uv.lock` 默认冻结。需动核心先给必要性、替代方案、ADR、人审、许可/依赖分析，再单独 PR；不能混入业务 PR。
- A 首个装配 PR 只在批准的入口路径接导航与中立端口，其他人把 view 留在自己模块。应用 orchestration 的路径/持有者须在 Plan 明确并获批；不同时让五人改同一 `app.py`，也不让 UI 变成第二个审核/发布判定层。
- 每次短同步只讲：本轮目标、已完成且可复现的证据、阻塞、请求谁决定。合同疑问用问题记录，口头结论必须落到合同/需求/测试；同一问题不能在两个私聊形成不同接口。
- 缺陷先保留失败与根因再修；债务明确责任、触发条件和拟清偿检查点。不按行数、Agent 输出量或未经验证的工时奖励贡献；按可追溯交付与预先约定的工作量记账。

## 8. 测试、环境与六类门禁

初始化工具环境：CPython 3.14.6、Pydantic 2.14.3、pytest 9.2.0、Ruff 0.17.5、mypy 1.20.2；锁定入口是 `requirements-init.lock`。这些是初始化配置，不是 PaperQA2 业务已安装/全套上游已通过的声明。

以下第一行只用于新克隆；本地已有 `.venv` 时不要为跑测试重复创建。依赖同步/安装和具体验证命令仍须符合本次工具授权。

```sh
uv venv .venv --python 3.14
uv pip sync --python .venv/bin/python requirements-init.lock
.venv/bin/python -m pytest -c papertrace.pytest.ini test/offline
```

`test/offline/` 和 `test/live/` 是团队测试；上游 `tests/` 完整保留且默认冻结。不得直接将根目录 `pytest` 或上游套件称为上述离线命令：上游 collection/插件、`.env` 读取与联网依赖不同。业务依赖及解析器安装另经审批，尤其不得把可选解析器许可视为 Apache-2.0 自动覆盖。

| 教师门禁（project p10） | 团队交付/审查时必须核对 | 不能混淆的状态 |
|---|---|---|
| 测试事前批准 | 实现前的测试版本和真实非作者批准；变更后重新批准 | 本地记录检查≠GitHub 人工保护已生效 |
| 静态分析 | lint、type、依赖；安全路径的合同/安全/API/权限检查 | 文件名或脚本存在≠检查执行成功 |
| Schema | requirements 对 schema 校验；故意坏例应被阻断 | 合法 YAML≠需求语义完整 |
| 语义评估 | prompt/model 变化触发固定集、真实模型与阈值回放 | fixture 逻辑 PASS≠真实 AI 语义 PASS；无批准应 BLOCKED |
| 回归 | 每轮完整 prior suite；零新增回归，保留原结果 | skip/空集/只跑本模块不算全回归 |
| AI-use log | 代码/prompt 变化关联真实 AI-use 更新和 transcript | 事后虚构日志不算合规 |

所有具体 gate 命令、已做的负例阻断实验、返回码和未完成状态以 [docs/ci/gates.md](docs/ci/gates.md) 为准。本页不猜测 gate 脚本名称。GitHub 创建、管理员 required checks/安全路径保护和失败 PR 的真实阻断演练须另获授权，不可凭 `ci.yml` 宣布 D7 完成。

## 9. 每人交付与最终退出条件

每个模块完整验收按自己的任务书与[交接清单](docs/team/handover-checklist.md)。共同标准：有可操作功能与自己的 view；合同合法；正例/负例/历史回归覆盖；审批早于实现；真实 OpenCode transcript 有人工干预；需求、架构、源码、测试、运行策略和 AI-use log 共演化；独立审查通过。

D1–D9 是共享仓库交付，不意味着九项都由一个人写：每人提供本模块的需求与测试映射（D1）、设计/边界/失败策略（D2）、权限与约束证据（D3）、验证/review/bug/debt 记录（D4）、真实 annotated session（D5）、真实贡献/反思素材（D6）、PR/CI/保护证据（D7）、源码/测试/fixture/view（D8）、按同一 `Prompt.md` 启动的计划与人工批准（D9）。完整对应表见交接清单。

**不能放行的情况：**合同冲突未解决、可绕过的发布门、伪造人工决定或 transcript、空获准仍调用模型、历史记录漂移、凭据进入仓库、live 用 fake 冒充、保护未设却标完成。保留已完成产物，明确 BLOCKED 的范围和负责决定的学生环节，不用“整体已完成”掩盖这些缺口。
