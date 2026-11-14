# PaperTrace｜集成合同与契约变更流程

## 0. 本文件的效力与当前阶段

先按 [新人启动流程](startup.md) 接通私有仓库与初始化环境（被邀请 → clone → 170 项离线测试）；六类门禁的最小落地方案见 [../ci/minimal-gates.md](../ci/minimal-gates.md)。

这是五模块共同遵守的**语义交接合同**，用于现在的需求/测试批准和后续实现。本轮只建立共享契约、合成 fixtures 和离线 gate，**下面的业务调用与编排尚未实现**。本文件不制造一套新的 Pydantic 模型或假装端口已可调用。

- 类型、字段、枚举、序列化与身份算法的事实源：`src/papertrace/contracts.py` 及其共享测试/规范 fixtures。
- 需求与不变量的事实源：`docs/req/requirements.yaml`、`docs/architecture/invariants.md`；架构/权限以 `architecture-blueprint.md`、ADR、permission-model 为准。
- 文字与真实共享契约不一致时，以**已批准的真实 contracts 文件**作为程序接口依据，立刻登记冲突；这不是削弱不变量的许可。缺少实现安全规则所需字段时，阻止相关集成/发布，走本页第 8 节变更流程，不在模块里偷偷补兼容字段或默认批准。
- `INV-01`–`INV-08`、`QA-01`、`PERF-01`、`COST-01`、`SEC-01`、`GOV-01`–`GOV-04` 的编号/含义不在本页重排。模块测试用这些真实 ID 与 registry 对齐。

## 1. 模块所有权、允许依赖与 UI 边界

| 模块 | 权威所有权 | 向外只提供 | 绝不能做 |
|---|---|---|---|
| A `library` | 文献逻辑身份、内容版本、导入状态、快照 | 版本固定的 CorpusSnapshot；受限文件访问/状态信息 | 直接导入 `paperqa`；把部分失败称为完整库；替 C 批准证据 |
| B `retrieval` | PaperQA2 映射、检索执行、受控生成的底层适配 | EvidenceRecord；中立生成端口的原始结果/实际发送及引用映射 | 产生人工 accepted；发布答案；返回跨模块可变 Docs/PQASession |
| C `review` | 人工决定与追加式审核 ledger | ReviewDecision 集合；可重放 revision/digest；有效决定投影 | 以 AI 分数自动批准；原地覆盖历史决定；修改文献版本 |
| D `answer` | 获准集/发送集/引用集；调用授权、上下文策略与确定性发布门 | AnswerDraft、ReleaseDecision 及核查原因 | 直接导入 `paperqa`；取回未审核证据；用模型自评代替门禁 |
| E `reports` | 研究历史、追溯存储与导出 | 绑定原快照/ledger/draft/release 的研究记录与导出件 | 重新生成答案；将 blocked 草稿升级为 released；回写审核 |

**只有 B 可以在团队新增源码中 import `paperqa`。**固定上游核心自己的 import 不受这条新增代码限制；不能为了结构检查去修改上游。D 是回答功能 owner，B 只是第三方机械适配者：D 决定获准输入、预算、提示词和发布，B 不获得批准/放行权。

各模块不通过 import 邻居的私有实现调用。后续应用 orchestration 以依赖注入/中立端口传递共享模型，负责安排顺序与一致性读取；端口由相应业务 owner 提案并在 Plan 获批，**不是本轮预先实现一个跨模块大服务**。例如 D 的离线测试可注入 fake 生成端口，不依赖 B 完工。

UI 仅展示状态、收集操作、调用应用编排：

- 各人 view 位于自己的模块目录，接受中立输入/命令，不各写一套审批状态机。
- A 的首个装配 PR 连接导航和依赖注入；入口/编排的实际路径在该 PR 的批准计划中明确，其他人不同时改同一入口。
- “按钮不可点击”不是安全控制；绕过 UI 直接调服务，审核和发布约束仍须生效。
- Streamlit session state 只能缓存展示状态，不能成为权威 ledger、快照或 ReleaseDecision。

## 2. 五个共享模型的语义责任

本表描述语义，不是另一份字段定义；实现时直接读 contracts 的字段名和校验器。

| 模型 | 生产者 → 消费者 | 必须保持的语义 | 拒绝/失效条件 |
|---|---|---|---|
| `CorpusSnapshot` | A → B/C/D/E | 逻辑文献 ID 与 SHA256 内容版本分开；快照内容 hash 稳定；`documents` 只含 `status="ready"` 的 DocumentVersion，不随当前库原地变化；失败/处理中信息留在 A 的导入记录而非塞进快照 | 文件内容与版本不符、来源不可访问、批次不完整且流程不允许、无法核验身份 |
| `EvidenceRecord` | B → C/D/E | 绑定 snapshot、doc、version、locator、原文；摘要/相关度为建议；稳定 evidence ID 由这五项按共享算法计算 | 外来快照、版本不存在、原文/定位缺失或无法核验、身份 hash 不符 |
| `ReviewDecision` | C（仅 human 操作）→ D/E | 按 snapshot、question、evidence 作用域追加接受/排除/重置 pending；不抹掉旧记录；ledger revision/digest 可重放。没有决定是 pending，不是 accepted；`actor_kind="human"` 的字段校验本身不证明操作真实性 | 非 human 来源、越界 evidence/问题、旧 revision 写入冲突、重放摘要不一致 |
| `AnswerDraft` | D（经 B 底层调用）→ 发布核查/E | 绑定问题、snapshot、审核版本、实际输入证据与原始引用映射；草稿不自动有发布资格 | 未知引用、上下文污染、生成错误/截断、关联状态变化 |
| `ReleaseDecision` | D 的确定性门 → UI/E | 明示能否发布及原因；与被判定的特定 draft、快照和审核版本绑定；非模型自评 | 不能重现三集关系、新鲜度/身份核验失败、未授权调用等均 fail closed |

业务状态的**显示标签**可以是“等待/导入中/可用/失败”“待审/接受/排除”“草稿/阻断/可发布”，但传输枚举一律使用 contracts 的真实定义，不把中文 UI 标签当 schema 值。

当前 v1 的关键实际值：ReviewDecision 为 `pending/accepted/excluded` 且 `actor_kind="human"`；AnswerDraft 为 `draft/abstained/failed`；ReleaseDecision 为 `released/blocked`。`stale` 是阻断原因/展示状态，不是可擅加的 ReleaseDecision 枚举。所有五模型显式 `schema_version=1`、未知字段拒绝。原始模型回复、usage、表示指纹、导入失败清单等不在五模型里的信息，应由 owner 在获批端口/版本化记录包中另存，不往 frozen 模型加 extra 字段。

### 身份与摘要规则

1. 逻辑文献 ID 代表同一文献条目；SHA256 代表文件内容版本。文件名、标题、DOI、上游 MD5 和 `dockey` 都不能单独替代内容版本。
2. snapshot 身份来自共享合同规定的内容 hash，不拿当前时间、随机数或列表显示序号替代。文件顺序、规范化和编码规则调用共享实现；不得各模块各写一个哈希算法。
3. evidence 身份来自 `(snapshot, doc, version, locator, 原文)` 的共享 hash 算法。原文是来源文本，不是模型摘要；改变其中任何有意义的来源内容应产生新身份。不要截取摘要前缀充当稳定 ID。
4. `SourceLocator` 必须有完整的 1-based inclusive 页范围或行范围，同时带 `chunk_id`、`parser_name`、`parser_version`；只有 chunk 名还不满足当前合同。只有页范围就不能捏造精确句子 offset；上游不能提供可验证行范围时，B 应从受控源文本建立映射，无法做到则显式失败/先审合同，不伪造行号。
5. 相同内容的重复导入行为由 A 的策略明确区分幂等复用与新逻辑条目；绝不静默覆盖旧历史。已保存的研究记录只读原版本，不自动迁移到最新 snapshot。

## 3. 后续应用编排的六次交接

下列为**设计交互**，不是已实现函数签名。批准计划须把它们映射到最小端口、输入/输出、错误与可测试的调用计数；不要让 UI 直接拼接五套可变对象。

| 次序 | 调用方 / owner | 输入 | 输出与必须检查 | 失败后的动作 |
|---|---|---|---|---|
| 1 文库准备 | 编排 → A；A 经中立摄取端口调用 B | 用户明确选定的本地允许文件、人工元数据、预期版本 | 各文件导入结果和固定 snapshot；A 决定库状态，B 只报告解析/索引结果 | 保留失败清单，禁止暗中扩大到用户目录；未完成不可标完整 |
| 2 候选检索 | 编排 → B | 固定 snapshot、问题、批准的检索配置 | 合法 EvidenceRecord 集合，来源均属于 snapshot，原文/摘要分开 | 空集正常返回“无证据”；错误显式失败，不自动请求全库回答 |
| 3 人工审核 | view → 编排 → C | evidence ID、human 选择/理由、预期 ledger revision | 新 ReviewDecision 和新 revision/digest；读回确认 | 旧 revision 冲突不覆盖；保留表单并要求刷新确认 |
| 4 受控生成 | 编排 → D → B 的中立生成端口 | 固定 snapshot、该版本人工 ledger、问题、获准证据、上下文/预算策略 | D 记录 approved；记录最终序列化后 sent；B 新建过滤 session，仅执行 aquery 并回传原始结果 | 空 approved/sent 时端口调用数为零；未知/过期/预算错误均停止，不能再搜证据 |
| 5 发布核查 | 编排 → D，向 A/C 读当前 token | 草稿、实际输入/原始引用、开始与结束的 snapshot/review token | 确定性 ReleaseDecision；通过才作为发布候选 | 保留草稿及具体阻断原因，不删除未知引用后假称通过 |
| 6 保存/导出 | 编排 → E | 不可变 snapshot、evidence、ledger、draft、release 及必要运行元数据 | 历史可回读；导出保持同一版本/状态/引用映射，发布提交与 token 比较处于一致性边界 | 缺原版本则显式 incomplete/blocked，不用当前库替代，不把 blocked 冒充 released |

B 的解析/索引准备与检索可能有独立错误或费用；A 的“导入”操作不因此被视为免费离线。默认仍使用 fake 摄取/检索端口，批准业务依赖和 live 前不能真实调用。

## 4. B/D 之间最重要的调用约束

固定上游源码在 `src/paperqa/docs.py` 已核对：`aquery` 在 contexts 为空时可能再次 `aget_evidence`；`pre/post` 可能额外请求模型；session 可复用旧 contexts；格式化会处理未知引用但不证明语义支持。因此不能只写“提示词要求只用获准证据”。

后续 B 适配器必须在 D 的授权边界内执行：

- 摄取/检索路线采用 `Docs.aadd` 与 `Docs.aget_evidence`；不用 `agents.ask`、`run_agent`、CLI 自治流程或“fake agent”。fake agent 仍可能请求真实模型。
- 生成路线采用 `Docs.aquery`，**每次新建仅含 D 选定证据的 session**，不接收/复用旧 session 或 B 检索时的全量 contexts。
- 显式 `answer.get_evidence_if_no_contexts=false`、`prompts.pre=None`、`prompts.post=None`；不附带旧答案、未审核会话历史或隐藏背景来源。其他模型角色与客户端初始化同样要受网络/预算边界控制，不能因为某角色“应当不用”就默认它无外连。
- 由 D 决定层级上下文、预算/裁剪、约束再注入和提示词版本；B 按批准策略序列化并记录**最终实际送出的**来源 ID 与引用 key 映射。serializer 的排序、cutoff、`answer_max_sources` 可能使 sent 小于 approved，不能只记录过滤前列表。
- B 返回模型原始输出及引用映射，D 在格式化清理未知引用之前完成解析/核查。未知 key 不能先静默删除再当作“未引用”；上游 `has_successful_answer` 不是 ReleaseDecision。
- B/D 的测试要能截获发送内容，证明排除与 pending 原文没有流入请求。测试 fake 不能只返回“OK”而不观察输入。

## 5. 三个集合、ledger token 与并发失效

- `approved`：属于所选 snapshot 和 question 作用域，且在指定 ledger revision/digest 下由 human 有效接受的证据 ID 集合。排除和无决定均不在其中；另一问题的决定不能直接挪用。
- `sent`：经过本次预算、排序、过滤、序列化后实际发送的证据 ID 集合；正文里若混入其他证据来源，即使没有显式 ID 也属于泄漏，须阻断。
- `cited`：从原始生成结果解析并可靠映射的实际引用 ID 集合；未知引用不能映射为任意获准 ID。

发布至少要求 `cited ⊆ sent ⊆ approved`，并满足 registry 的其他 fit criteria。三集关系只能证明来源授权/结构，**不能证明每项自然语言主张被原文支持**；忠实度、相关性和安全逃逸还需固定集语义评估与人工核查。

生成开始捕获 `(snapshot 内容身份, ledger revision, ledger digest)`，生成完成与最终保存/发布时重新核对。revision/digest 都须与原始 ledger 可重放一致；“只是另一条证据被改了”也不能擅自忽略整体审核版本变化。

为避免“核对之后、保存之前”又被修改，批准的编排设计须为最终发布提交选择一个一致性机制（如单进程锁内比较后提交，或带预期 token 的 compare-and-swap），用可控并发 fixture 验证。此设计不能只做两次没有提交保护的普通读。A/C/E 提供必要端口，D 保持唯一发布判断；UI 不能补一个 `if accepted` 替代它。

任何 token 改变、文献撤销、来源丢失、ledger 冲突或解析失败：本次 draft 保留但不发布，要求用户在新版本重新审核/生成；不自动把旧批准迁到新 snapshot。历史发布记录保留当时有效状态与版本，可显示“与当前版本不同”，不能篡改历史。

## 6. 错误、离线隔离与可观测信息

| 情况 | 必须向调用方/用户呈现 | 禁止的 fallback |
|---|---|---|
| 部分导入失败、文件被替换 | 哪些项失败、当前版本/完整性、允许的显式重试 | 沿用同名缓存并宣称全库完成 |
| 检索无结果/解析错误 | 区分空集与执行失败，保留来源和阶段 | 开启自治 Agent 到网上寻找答案 |
| ledger 写冲突/非 human 决定 | 刷新后重新确认；拒绝无效写 | 覆盖最新决定、把模型建议当确认 |
| approved/sent 为空 | 不可回答及原因，模型调用数零 | 调用模型“说明为什么没证据” |
| 请求超时/限流/金额耗尽 | 失败阶段、真实尝试和成本，草稿不发布 | 无批准重试、换 provider、换模型 |
| 未知引用/生成中 token 变化 | 具体阻断原因、保留原草稿与版本 | 删掉引用、取最新 ledger 自动放行 |
| 历史文件丢失/导出目标不安全 | 记录不完整或拒绝路径，原记录不受影响 | 读取个人目录补原文、覆盖不相关文件 |

日志仅记录允许的 ID、状态、阶段、版本、计数与脱敏错误。原文/问题/答案可能有隐私，完整运行证据放受控研究记录，不默认打印全量 settings、绝对个人路径或 credentials。禁止导入外来的 pickle 缓存；不从真实 `~/.pqa` 继承状态。

## 7. 共享 fixtures 与集成验收

先使用 `test/fixtures/contracts/` 的规范 fixtures；其 wrapper 的 `data` 才是共享模型输入，synthetic 元信息不能传入 `extra="forbid"` 模型。模块测试拟放 `test/offline/test_library.py`、`test_retrieval.py`、`test_review.py`、`test_answer.py`、`test_reports.py`（后四项同目录），模块专属合成材料拟放 `test/fixtures/<module>/`；须在 Plan 列出精确文件并经权限批准，不因本页示例就自动可写。不要修改共享 fixture 的预期迁就实现；身份由真实模型/共享算法算，不能手填看似合法的随机 hash。

最低跨模块场景：

1. 正常链：同一 snapshot 的两条候选，一条 human 接受、一条排除；只发送/引用获准项，E 读回同一版本。
2. 默认 pending：全无审核或仅有模型高分；D 调用计数为零，E 可保存失败原因但无 released。
3. 预算裁剪：approved 多于 sent；模型引用未发送但已批准的证据仍须阻断。
4. 未知引用：保存原始输出，不能依赖上游清理后的答案做唯一检查。
5. 中途撤销/替换：在请求执行时换文献或写新审核 revision；旧草稿不得发布，历史不覆盖。
6. 身份篡改/串快照：同名不同内容、不同 snapshot 复用 evidence、错误 locator/原文 hash、冲突 ledger 均被拒绝。
7. 失败与恢复：一项导入失败、检索错误、模型超时、导出路径穿越/已有文件冲突；无隐式成功、无非预期覆盖。
8. 不经过 UI 调服务仍执行同样的授权/发布门；全程 synthetic 且外部模型调用为零。

每个用例写真实 requirement/invariant ID、断言和违反该规则时测试会失败的证据。离线 fixture 集成不是 live 模型质量测评。运行入口与实际 gate 状态见 [../ci/gates.md](../ci/gates.md)。

## 8. 契约变更：提出 → 批准 → 同步 → 复验

任何字段/枚举、hash/规范化算法、默认状态、审核 authority、集合关系、端口或异常语义改变，都不能口头决定：

1. **提出人建变更记录/后续 issue：**写当前合同版本或提交、需求 IDs、问题复现、旧/新序列化样例、受影响消费者、兼容/迁移方案、失败风险。尚无 GitHub 时保留本地讨论和 diff，不伪造 issue URL。
2. **通知所有受影响 owner：**至少生产者和每个消费者确认；快照、审核或发布安全含义变化须 ADR、真实人工批准，批准人不能是本变更作者。指明冻结期间哪些工作可继续 fixture 开发、哪些集成暂停。
3. **先批准测试再实现：**给旧/新规范 fixture、兼容/拒绝旧格式测试、至少一个负例和跨模块回归；按工作计划轮换安排事前测试批准、独立 reviewer 和集成人。
4. **独立共享契约 PR：**最小修改 contracts、schema/fixtures/测试、受影响 requirements、ADR、invariants、trace matrix、运行策略及本页；显式写新版本和旧记录处理，不混入大批业务功能。
5. **按依赖同步：**契约先合并，再由 A–E 各自同步映射/测试；安全不兼容旧结果默认 blocked，不自动转换 accepted/released。共享文件指定一位临时编辑者，其他 owner 给补丁，避免互相覆盖。
6. **复验并解除冻结：**完整离线回归和门禁；prompt/model 受影响时追加经授权 live 固定集评估。读回真实接口与记录，非作者审查批准后才解除对应集成冻结。记录谁批准什么版本及证据，不用“大家默认同意”。

契约变更不会转移长期功能 ownership；支持角色轮换也不会允许集成人未经作者/审批修改别人的业务边界。
