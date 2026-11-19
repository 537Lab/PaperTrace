# B1 测试设计 v2.1

日期：2026-11-19。依据：已批准 Plan v2.1、现有 `contracts.py`、`integration-contract.md`、FR-B-01/02 与 FR-D-03。

状态：**设计草稿已完成；测试代码 NOT_CREATED；OpenCode Build NOT_RUN；独立测试审批 NOT_REQUESTED；B2 NOT_STARTED**。

本文件由 Codex 辅助整理，不能算作 OpenCode 已生成测试或真实学生 Approve。没有修改共享契约或其他成员模块。

## 1. 测试对象与边界

- 测试文件：`test/offline/test_retrieval.py`。
- B2 拟实现对象仍为已批准的 `src/papertrace/retrieval/{__init__,gateway,service,view}.py`；本阶段不创建这些文件。
- B 的内部结果可区分 SUCCESS、EMPTY_RESULT、TIMEOUT、PARSE_ERROR、UPSTREAM_ERROR；不能把这些状态添加到共享模型。
- B1 fake 记录输入、序列化结果和尝试次数，只测边界；B0 smoke 另测真实 PaperQA2 本地 API 接线。两者均不能代替 live 检索质量评估。
- 具体 Python 函数签名需在 OpenCode 生成测试时明确记录，并与 A/D 的公开端口核对。本文不宣称现有 A/D 已实现或同意任何新签名。

## 2. 合成数据与 fake 的精确候选路径

下列是供 OpenCode 展开的候选清单，尚未创建或批准为新的范围扩展；若实际权限/原计划要求逐文件审批，须先由学生确认清单。

- `test/fixtures/retrieval/source-a.txt`：自写两段合成文本，可验证完整行范围。
- `test/fixtures/retrieval/source-b.txt`：另一来源，测试跨来源、排除和 pending marker。
- `test/fixtures/retrieval/fake_adapter.py`：仅离线 spy、异常注入及实际 payload 捕获，不加载 PaperQA2 或凭据。
- `test/fixtures/retrieval/README.md`：说明数据非真实论文、用途与 fake 限制。

document version 用源文件实际字节 SHA256；snapshot/evidence ID 由现有共享模型派生。不得手写随机合法外观 ID 来绕过校验。固定合成时间采用有时区时间，不含成员身份。

## 3. 测试矩阵

| 测试组 | 正向断言 | 负向断言与故障后的动作 | 追踪 |
|---|---|---|---|
| 来源与身份 | 输出真实 `EvidenceRecord`；snapshot/document/version/excerpt/locator 对应输入 | 外来 snapshot、错误版本、未知文献一律失败，整次不返回部分伪造证据 | FR-B-01、INV-02、QA-01 |
| 原文定位 | 行或页范围完整、1-based inclusive，含 chunk/parser 名称与版本；回查能找到原文 | 缺端点、反向范围、越界、无法回查均拒绝；不得猜页码/行号 | FR-B-01、INV-02 |
| 稳定与去重 | 摘要、upstream context ID、检索时间变化不改变 evidence ID；重复相同来源去重 | 内容、locator、版本或 snapshot 改变须产生新身份；身份冲突 fail closed | FR-B-01、INV-02 |
| 空集与失败 | 无相关证据是 EMPTY_RESULT | 注入超时、解析错误、上游失败，分别返回明确状态及阶段；不冒充空集或成功 | FR-B-02 |
| 尝试策略 | max_retries=0 仍允许一次初始调用；获准重试上限明确 | 不超上限、不切 provider/model；不可重试错误仅一次；如实记录尝试 | FR-B-02、COST-01 |
| 不可信索引 | 仅走获准受控来源入口 | pickle/joblib/torch/NumPy pickle 索引在 loader 被调用前拒绝；不得真实反序列化攻击数据 | INV-08、SEC-01 |
| 人工决定边界 | 原文和 advisory summary 分开；只输出候选 | 高分、恶意 excerpt、伪 human/accepted 字段均不能产生 ReviewDecision 或 ReleaseDecision | INV-03、SEC-01 |
| 生成前拒绝 | 合法非空输入按 D 给出的配置机械执行 | 空 approved/sent、sent 越界、来源不符、预算超限时，factory/SDK/HTTP/adapter 计数全部 0 | FR-D-03、INV-01/04/07 |
| 新 session 与实际发送 | 每次生成新 session；记录 serializer 后 actual sent、raw 输出与一对一 alias | 已排除/pending 原文不得进入最终 payload；禁止自动补证、pre/post、自主 Agent、旧 session 复用 | FR-D-03、INV-04 |
| 未知与歧义引用 | alias 正确映射回团队 evidence ID，raw 文本保留 | 未知 key 保留给 D；重复/歧义 alias 明确失败，不静默删除、不任意映射、不自行发布 | FR-D-03、INV-04 |
| view 与结构 | 仅投影检索状态、来源及建议字段 | view 不授予接受/发布；团队新增代码仅 B 可 import paperqa | QA-01、INV-03/04 |
| 默认离线 | 测试 synthetic 输入，socket 禁用 | 不读 .env/Key/个人目录、不外连；未执行的计数或 live 评估不能写 PASS/0 | COST-01、SEC-01 |

12000 输入硬上限、9000 策略触发点、2000 输出上限依 Plan v2.1。需分别测试临界值、超过上限和真实装配后的计数；B 按 D 策略执行，不自行决定获准集合或修改预算政策。

## 4. RED 必须能够说明什么

测试文件必须可以正常 collection。缺少业务模块时，用清晰断言报告目标公共接口尚未实现，而不是以 import 崩溃冒充业务负测已验证。测试在实现前 RED 是提案状态；获得实现后，每项断言必须真正执行，不能只测 fake 自己。

禁用 skip/xfail/弱化断言求绿。不把共享模型本身已经拒绝非法输入，当作 B 运行时边界已经验证。

## 5. 运行与交接

1. B0 已于 2026-11-19 在独立真实 Git 副本恢复并通过：1 passed，实际 socket 连接尝试为 0。新证据见 `artifacts/verification/module-B-recovery-and-pr5-review-2026-11-19.md` 与 `module-B-paperqa-smoke-recovered-2026-11-19.json`；原 BLOCKED 报告保留为历史。恢复基线与准备 B1 的状态分别记录。
2. 学生确认精确 fixtures 清单及开发助手调用边界后，使用 `papertrace-build-B` 新会话附上 Plan v2.1 与真实批准记录；只生成测试、fixtures 和本设计记录，不写 src。
3. 使用第 7.1 节批准的离线测试命令；若实际 Python 路径需适配隔离环境，记录真实命令。保存 collection、预期 RED 与共享合同回归的真实退出码；未运行则 NOT_RUN。
4. 核对最终文件清单和内容 hash，确认无 src/共享/上游/锁/CI 改动；保留真实 OpenCode 原始会话与人工干预，准确披露 Codex 的设计辅助。
5. 从真实 Git checkout 创建测试提案 commit/PR，注明所有失败原因。请未参与测试实现的另一位学生对精确 commit 在 GitHub Approve；测试提案可保持 RED/open。
6. 真实批准后，从该测试 head 开始 B2，不预写业务实现。完整离线回归、Ruff/mypy/schema/frozen 与 live 状态分别如实报告。

## 6. 待确认而非已完成

- A 的受控源文本读取与文献版本端口的实际签名。
- D 的中立生成端口实际签名、预算策略输入、raw/actual-sent/alias-map 输出的对接。
- Git checkout 的分支/commit 身份；当前 ZIP 无法独立产生可审查的 Git commit。
- 本轮 OpenCode 模型调用的数据、次数和费用边界。此前成功的 Plan 会话不能自动视作后续 Build 模型调用的无限许可。

这些事项不允许通过修改 `contracts.py`、人工规则或其他成员源码解决。

## 7. 2026-11-19 A/B 接口核对与 B 侧交接意见

核对来源：腾讯任务板当前 A 行、PR #5 精确 head `310ebb3b7b781288308d2b2e15d5574c10b80878` 的计划/测试/设计、现有共享 contracts 与 integration-contract。以下是 B 侧设计意见，尚未发送给其他 owner，也不是已完成联调；其他 owner 的批准不可由本文代填。

### 文献身份与受控读取：可按现有合同衔接

- A 负责分配 `document_id`；B 原样保留，不由文件名、DOI、PaperQA dockey 或 Context.id 替代。
- `version_sha256` 必须对应 A 提供的原始托管 bytes；B 在接收时重新核对 SHA256。解析文本的 hash 不能替代源文件版本。
- B 只接收 A 固定的 `CorpusSnapshot`，逐条核对其中 document/version；不读取 A 私有 sources/manifests 目录。
- B 可使用 A 提案中的 `read_source(*, snapshot_id, document_id, version_sha256) -> bytes` 作为受控读取边界。A 检查成员与完整性，B 再核对版本；读取失败明确停止，不将当前最新版替代历史源。
- B 形成 `EvidenceRecord` 时带回同一 snapshot/document/version，原文与 advisory summary 分开；locator 必须可回查，不能猜页码。C/E 从共享证据记录获得这些信息。

### A→B 摄取回执：B 接受作为候选形状，正式签名仍需双方确认

A 当前 Fake 传入 request dict：`document_id`、`version_sha256`、安全 `source_name`、实际 `source_bytes`、人工 `metadata`、显式 `policy_ref`。回执 dict：原样 ID/version、明确 `status`、`stage`、`reason_code`、B 管理的 `representation_ref`。

B 侧意见：该最小形状足以作为后续薄适配端口的设计依据；不能回传可变 Docs/PQASession，也不能把 representation_ref 当成可加载的外部 pickle。成功须代表当前源版本的解析/表示确已完成，未知/缺失/不匹配回执不能 ready；不得在未批准真实 embedding/API 时将 fake receipt 冒称真实摄取成功。

当前 A 测试假设同步 callable；PaperQA 原方法为 async。正式装配前，A/B 必须约定同步包装或异步调用方式及异常边界。当前 B2 规划没有精确列出摄取方法，此功能须在后续 B 测试设计/计划中明确后再实现；本文只给交接意见，不把它暗中加入已获独立审批的实现范围。

### 部分库、失败换版与 freshness：区分职责

- B 支持消费 ready-only snapshot；`complete` 保留在 A-local 批次结果，不加到共享快照。是否允许用户基于部分库发起本次研究，仍由批准的 A/D/编排策略明确，B 不自行选择。
- B 检索严格使用传入的固定快照；换版失败时旧版是否退出 current，由 A 与相关 owner 确认。B 不把旧版标成新版本成功。
- A-local `(snapshot_id, corpus_revision)` 可供后续 freshness 检查，避免移除后恢复同一 snapshot 的 ABA；B 可传递运行 token，不裁定发布。D/最终编排还须确认发布提交的一致性机制；不宣称仅两次读取即可消除竞态。
- A 的文件大小上限、磁盘布局及恢复策略归 A；本次 B 协调不替负责人批准这些策略。

## 8. 2026-11-19 D/B 生成接口交接意见

核对对象：PR #6 head `c3817ae676eb7c7a0ee8790b42c04232c19212e6` 及 D 设计记录。当前 D 第一切片没有 generation collaborator：eligible 仍返回 GENERATION_PATH_NOT_ENABLED，因此尚无可直接接线的已实现生成端口。

后续 B gateway 的输入/输出至少应满足下表；这是沿用 Plan v2.1 的语义交接清单，不新增 frozen contracts 字段，也不表示 D 已接受具体类名或方法签名。

| 交接 | 需要的数据/行为 | 权威归属 |
|---|---|---|
| D→B 输入 | 固定 snapshot、question/question_id、经本轮审核确定的非空 selected EvidenceRecord、review revision/digest、D 批准的 prompt/排序/裁剪/输入输出预算与配置身份 | D 决定获准集和策略；B 验证来源并机械执行 |
| B→D 输出 | 未静默清理的 raw 输出、最终序列化后 actual sent evidence IDs、一对一 citation alias→evidence ID、尝试/错误/实际用量信息 | B 记录实际执行；D 解析引用并判定是否发布 |
| 空 approved/sent | D 提前拒答；B 边界也在初始化模型工厂/SDK/HTTP 前拒绝 | 两侧均要负测，不能仅靠 UI |
| session/隐式调用 | 每次新建仅含选定 contexts 的 session；关闭空集补证、pre/post 和自主 Agent；不复用旧会话 | B 适配器 |
| 未知引用、版本变化 | raw 保留，明确错误/未知映射交 D；不删引用求通过、不取最新审核自动放行 | D 发布门及后续编排 |

请 D 在下个生成切片确认具体调用签名、配置/预算表示与实际序列化观测点；B1 将据双方确认的最小签名测试 fake generation port。该确认前 D 现有第一切片可继续独立开发，不能把本次 B0 smoke 当成 D/B 联调通过。

## 9. 本轮停止位置

用户在 2026-11-19 明确选择“先完成审核和接口交接，暂不调用模型”。本轮不启动 OpenCode Build，不生成 B1 测试，不编写 B2 源码。B0 已通过；A/B 与 D/B 的上述意见可由 B 负责人转发，只有对方真实回应后才记录双方确认完成。
