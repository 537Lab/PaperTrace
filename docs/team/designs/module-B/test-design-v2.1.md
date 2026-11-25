# B1 测试设计 v2.1

日期：2026-11-19（设计依据）；2026-11-20 状态更新。依据：已批准 Plan v2.1、现有 `contracts.py`、`integration-contract.md`、FR-B-01/02 与 FR-D-03。

状态：**测试已由 OpenCode 创建并处于 B1 RED；B2 NOT_STARTED；独立测试审批 NOT_REQUESTED / NOT_GRANTED**。

测试文件与 fixtures 已由 OpenCode 生成；Codex 仅编排本地验证与事实一致性核对，这些动作不能算作真实学生 Approve。没有修改共享契约或其他成员模块。测试文件与 fixtures 已实际存在，但业务实现尚未开始。

## 1. 测试对象与边界

- 测试文件：`test/offline/test_retrieval.py`（已创建）。
- 合成 fixtures：`test/fixtures/retrieval/` 下四个文件（已创建，见第 2 节）。
- B2 拟实现对象仍为已批准的 `src/papertrace/retrieval/{__init__,gateway,service,view}.py`；本阶段**不创建**这些文件。
- B 的内部结果可区分 SUCCESS、EMPTY_RESULT、TIMEOUT、PARSE_ERROR、UPSTREAM_ERROR；不能把这些状态添加到共享模型。
- B1 fake 记录输入、序列化结果和尝试次数，只测边界；B0 smoke 另测真实 PaperQA2 本地 API 接线。两者均不能代替 live 检索质量评估。
- 测试面向的具体 Python 形状以第 4 节为准；该节是 B1 提案，不是已实现或已由 A/D 同意的接口。

## 2. 合成数据与 fake 的实际情况

已创建的文件（均为自写合成内容，非真实论文或凭据）：

- `test/fixtures/retrieval/source-a.txt`：两段合成文本，用于完整行范围与回查。
- `test/fixtures/retrieval/source-b.txt`：另一合成来源，含 pending marker，用于跨来源、排除和 pending 文本不进入发送集。
- `test/fixtures/retrieval/fake_adapter.py`：仅离线 spy、异常注入及实际 payload 捕获；不加载 PaperQA2、不读凭据、不联网。其 AST 导入根不含 `papertrace` 或 `paperqa`，由测试断言固定。
- `test/fixtures/retrieval/README.md`：说明数据为合成、用途与 fake 限制。

document version 用源文件实际字节 SHA256；snapshot/evidence ID 由现有共享模型派生。不手写随机合法外观 ID 来绕过校验。固定合成时间采用带时区时间，不含成员身份。fixtures 不含绝对个人路径、邮箱样式或 credential-like 值，由测试断言固定。

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

## 4. 测试面向的 B1 API 提案（未批准）

以下签名**逐项来自当前 `test/offline/test_retrieval.py` 实际编码的形状**，仅用于说明测试期望什么。它们是 **B1 测试提案**，等待未参与测试实现的学生对具体测试 commit 独立批准，并在之后由 A/D 确认各自侧端口；**不是已实现代码，也不是已与 A/D 达成的接口**。未修改 `contracts.py`，也不据此创建 `src/`。

计划模块 `papertrace.retrieval.gateway`：

- `Gateway(*, adapter, source_reader, model_factory, index=None, clock)`，方法 `retrieve(request)` 与 `generate(request)`。`clock` 返回带时区时间。
- `RetrievalRequest(*, snapshot, question, config)`；`RetrievalConfig(*, provider, model, max_retries=0, parser_name, parser_version)`。
- `RetrievalStatus`：`SUCCESS`、`EMPTY_RESULT`、`TIMEOUT`、`PARSE_ERROR`、`UPSTREAM_ERROR`。
- 检索结果暴露 `status`、`evidence`（共享 `EvidenceRecord` 元组）、`attempts`（每次尝试含 `provider`、`model`、`stage`），失败时结果还有 `stage`。
- `GenerationRequest(*, snapshot, question, approved_evidence, selected_evidence_ids, policy, review_revision, review_digest)`。
- `GenerationPolicy(*, provider, model, max_input_tokens=12000, compress_at_tokens=9000, max_output_tokens=2000, max_sources=None, get_evidence_if_no_contexts=False, pre_prompt=None, post_prompt=None, autonomous_agent=False)`。
- `GenerationStatus`：`REFUSED`、`SUCCESS`、`AMBIGUOUS_CITATIONS`。
- 生成结果暴露 `status`、`refusal_reason`、`raw_output`、`sent_evidence_ids`、`citation_aliases`（alias→evidence ID）、`unknown_citation_keys`、`ambiguous_citation_keys`。
- 拒绝原因字符串（B 内部，不加入共享模型）：`EMPTY_APPROVED`、`SELECTED_OUTSIDE_APPROVED`、`INVALID_BUDGET`、`UNSAFE_SESSION_POLICY`、`EMPTY_SENT`、`EVIDENCE_OUTSIDE_SNAPSHOT`、`EVIDENCE_VERSION_MISMATCH`。
- `UnsafeIndexError`：在 loader 被调用前拒绝不可信索引。

受控来源读取（A 侧形状，待 A 确认）：

- `read_source(*, snapshot_id, document_id, version_sha256) -> bytes`，仅允许关键字调用；测试的 reader spy 按这三个键记录每次调用，并在读取后由 B 核对 SHA256。
- 测试 spy 形状：`FakeSourceReader(sources={(snapshot_id, document_id, version_sha256): bytes}, fail_with=None)`，暴露 `calls`（dict 列表，键为上述三项）。

adapter / factory / session spy 形状（仅测试用，不等于生产端口）：

- `FakeRetrievalAdapter(script=[FakeOutcome(...)])`，暴露 `search_calls` 与 `requests`；`FakeOutcome(contexts=(), failure=None)`；`FakeFailure(kind, stage, retryable)`；`FakeContext(document_id, version_sha256, excerpt, line_start, line_end, page_start, page_end, chunk_id, summary, score, upstream_context_id)`。
- `FakeModelFactory(scripted=[FakeGenerationOutput(...)])`，暴露 `create_calls`、`sdk_calls`、`http_calls`、`sessions`、`create_payloads`、`questions`、`ask_order`；`create_payloads` 每项含 `"policy"`，其 `get_evidence_if_no_contexts`、`pre_prompt`、`post_prompt`、`autonomous_agent` 可被断言。
- `FakeGenerationOutput(raw_output, citations, usage_tokens)`；`FakeCitationClaim(key, candidates)`；session 暴露 `contexts`（每项有 `evidence_id`、`text`）与 `reused`。
- `CountingUntrustedSource` 暴露 `load_calls`，用于证明未反序列化。
- 测试常量：provider `synthetic-provider`、model `synthetic-model`、parser `synthetic-parser` / `1.0`，仅用于合成断言。

view 模块 `papertrace.retrieval.view`：

- `project_retrieval_view(result) -> dict`，含 `status`（枚举 `value` 字符串）与 `evidence` 列表；每项至少含 `evidence_id`、`document_id`、`version_sha256`、`locator`、`excerpt`、`advisory_summary`，且不得含 `accepted`、`accepted_by`、`review_decision`、`release_decision`、`released`、`release_status`。

以上命名、默认值和返回结构若在独立测试批准或 A/D 确认时发生变化，必须先改测试提案并重新走审批，不得在实现阶段暗中放宽断言。

## 5. RED 必须能够说明什么

测试文件已能正常 collection。缺少业务模块时，用清晰断言报告目标公共接口尚未实现，而不是以 import 崩溃冒充业务负测已验证。测试在实现前 RED 是提案状态；获得实现后，每项断言必须真正执行，不能只测 fake 自己。

当前实测：`test/offline/test_retrieval.py` 收集 **48** 项；**3** 项 fixture/architecture 安全检查通过（fixtures 合成且无凭据/绝对路径、fake 不导入 `papertrace`/`paperqa`、团队新增源码仅 retrieval 可导入 paperqa）；**45** 项行为测试按设计失败，报错明确指向缺失的 `papertrace.retrieval.gateway`（B1 RED），而不是 collection error。45 项失败均为“目标接口未实现”，尚未证明任何业务行为；在独立测试批准与 B2 实现之前不得把 RED 描述为通过或已联调。

禁用 skip/xfail/弱化断言求绿。不把共享模型本身已经拒绝非法输入，当作 B 运行时边界已经验证。

## 6. 运行与交接

1. B0 已于 2026-11-19 在独立真实 Git 副本恢复并通过：1 passed，实际 socket 连接尝试为 0。原始恢复、smoke 与 BLOCKED 报告保留在本地历史证据中；为满足测试提案门禁的文件范围，不纳入 PR #9。
2. B1 测试与 fixtures 已由 OpenCode 在会话 `ses_e0b52e19cffeKNNWGvabD35xQ7` 与 `ses_e075ae192ffeqS0IgLofyGjpFw` 中创建；本次设计状态更新由 OpenCode 会话 `ses_e0745d58fffei0NNwkEjinDmtc` 完成。CityU 模型端点对包含 `reasoning_text` 的请求返回 HTTP 400，该限制使模型侧无法在相关会话继续迭代；随后由 **Codex 编排本地验证**（collection、离线 pytest、schema gate、Ruff），这不是 OpenCode 自动结果，也不构成人工审批。提交范围仍只包含 B1 测试、fixtures、设计记录与验证记录，不含业务源码。
3. 本地验证结果：`test/offline/test_retrieval.py` 收集 48、3 通过、45 个预期 B1 RED；schema gate 通过；补充 Ruff 通过；`test/offline` 全量为 **353 passed、51 failed**，其中 **45** 个是上述预期 B1 RED，另 **6** 个是无关的既有/环境失败，不计入 B1 证据，也不以修改 B1 测试掩盖。
4. 已核对文件清单：新增 `test/offline/test_retrieval.py`、四个 `test/fixtures/retrieval/` 文件，并更新计划、测试设计与 AI-use log；PR #9 不包含 `artifacts/verification/`、`src/`、共享契约、上游冻结、锁或 CI 改动。真实 OpenCode 会话与 Codex 事实一致性修正继续由 AI-use log 披露。
5. 测试提案应以真实 Git commit/PR 提交并保持 open、RED；请未参与测试实现的另一位学生对**精确测试 commit** 在 GitHub 实际 Approve。**当前尚未请求、也尚未获得任何测试批准**；角色选择、会话文字或工具权限都不证明批准。
6. 只有真实批准后，才从该测试 head 开始 B2，不预写业务实现。完整离线回归、Ruff/mypy/schema/frozen 与 live 状态分别如实报告。

## 7. 待确认而非已完成

- A 的受控源文本读取与文献版本端口的实际签名（第 4 节 `read_source` 仅为 B 侧提案）。
- D 的中立生成端口实际签名、预算策略输入、raw/actual-sent/alias-map 输出的对接；第 4 节 `GenerationPolicy`/`GenerationRequest` 仍待 D 确认。
- 测试提案 PR 的分支/commit 身份与独立审批人。
- 本轮 OpenCode 模型调用的数据、次数和费用边界；CityU 端点的 `reasoning_text` 400 限制及后续替代验证方式应记录在真实会话/PR 中。
- B2 未开始，任何 `src/papertrace/retrieval/` 文件均不存在。

这些事项不允许通过修改 `contracts.py`、人工规则或其他成员源码解决。

## 8. 2026-11-19 A/B 接口核对与 B 侧交接意见

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

## 9. 2026-11-19 D/B 生成接口交接意见

核对对象：PR #6 head `c3817ae676eb7c7a0ee8790b42c04232c19212e6` 及 D 设计记录。当前 D 第一切片没有 generation collaborator：eligible 仍返回 GENERATION_PATH_NOT_ENABLED，因此尚无可直接接线的已实现生成端口。

后续 B gateway 的输入/输出至少应满足下表；这是沿用 Plan v2.1 的语义交接清单，不新增 frozen contracts 字段，也不表示 D 已接受具体类名或方法签名。

| 交接 | 需要的数据/行为 | 权威归属 |
|---|---|---|
| D→B 输入 | 固定 snapshot、question/question_id、经本轮审核确定的非空 selected EvidenceRecord、review revision/digest、D 批准的 prompt/排序/裁剪/输入输出预算与配置身份 | D 决定获准集和策略；B 验证来源并机械执行 |
| B→D 输出 | 未静默清理的 raw 输出、最终序列化后 actual sent evidence IDs、一对一 citation alias→evidence ID、尝试/错误/实际用量信息 | B 记录实际执行；D 解析引用并判定是否发布 |
| 空 approved/sent | D 提前拒答；B 边界也在初始化模型工厂/SDK/HTTP 前拒绝 | 两侧均要负测，不能仅靠 UI |
| session/隐式调用 | 每次新建仅含选定 contexts 的 session；关闭空集补证、pre/post 和自主 Agent；不复用旧会话 | B 适配器 |
| 未知引用、版本变化 | raw 保留，明确错误/未知映射交 D；不删引用求通过、不取最新审核自动放行 | D 发布门及后续编排 |

第 4 节的 `GenerationRequest`/`GenerationPolicy`/结果字段是 B1 测试对这些语义的编码，**仍待 D 确认**；确认前 D 现有第一切片可继续独立开发，不能把本次 B0 smoke 或 B1 RED 当成 D/B 联调通过。

## 10. 本轮停止位置

B1 测试、fixtures 与本地验证已完成并保持 RED；B2 未开始，未创建任何业务实现；测试提案尚未提交到 GitHub，独立测试审批尚未请求、尚未获得。下一步是提交测试提案 commit/PR 并请求真实审批；在此之前不得继续 B2，也不得把本轮 Codex 编排的本地结果或角色配置写成学生批准。

## 11. 2026-11-21 PR #12 Review 后的测试增补提案

PR #12 对精确实现提交 `ea1bfed328528d11578980a757c80bef1c7a84b0`
收到 GitHub `REQUEST_CHANGES`（review
`PRR_kwDOVtJ17M8AAAABZeU9_g`）。评审指出原 48 项测试遗漏了两个实现阻塞：

1. page-only locator 的摘录只通过 `SourceLocator` 结构校验，未证明摘录真实存在于
   A 提供的受控源 bytes；
2. fake adapter 测试没有要求生产桥实际调用 PaperQA2 的 `Docs.aadd`、
   `Docs.aget_evidence` 与 `Docs.aquery`。

因此本测试提案新增两项、不修改或放宽原 48 项断言：

- `test_retrieval_rejects_forged_excerpt_with_page_only_locator`：构造结构合法但
  原文不存在的 page-only context，要求结果为 `PARSE_ERROR`、证据为空，并证明
  受控 reader 被调用；
- `test_concrete_paperqa2_adapter_calls_aadd_aget_evidence_and_aquery`：要求公共
  `PaperQA2Adapter` 在合成、无网络的 Docs API 记录器上，先为固定 snapshot 的
  每个文档调用 `aadd`，再调用 `aget_evidence`，并在只含获准 evidence 的新 session
  上调用 `aquery`；同时核对 raw 输出、actual sent 与 alias→evidence ID。

新增两项在缺少业务源码的测试分支上按预期 RED：`2 failed, 48 deselected`；
文件可编译、Ruff 通过、`git diff --check` 通过。该结果只证明新测试能捕获缺失实现，
不证明真实 PaperQA2 适配已经完成。新增测试版本必须在 PR #9 重新获得未参与测试编写
同学对精确 head 的 GitHub Approve；旧 head `7833527` 的批准不覆盖本次增补。

## 12. 2026-11-22 PR #12 第二轮 Review 回归提案

PR #12 对 clean-main 实现 head `a79ace7c72d9e53d62d21e61491a41b75f55c7a4`
收到第二轮正式 `REQUEST_CHANGES`（review `6007155751`）。本轮不扩大 Plan v2.1；
只把 §2、§3.1、§3.2 和 §5 已明确要求、但具体 PaperQA2 bridge 尚未覆盖的行为
编码成 synthetic RED：

1. 同一固定来源、摘录、行范围和 parser provenance 只改变 advisory summary 或
   upstream `Context.id` 时，`locator.chunk_id` 与 `evidence_id` 必须稳定；上游 ID
   只保存在 `upstream_context_id`。
2. 默认 serializer 过滤为空时，答案调用为零并返回 `EMPTY_SENT`；自定义 serializer
   只保留部分 contexts 时，`sent_evidence_ids` 与 alias 映射只包含最终实际集合。
3. D 的 provider/model 必须与 bridge 绑定模型一致；不一致时在创建 Docs/答案调用前
   `MODEL_POLICY_MISMATCH`。实际传给 `aquery` 的模型副本须使用请求的
   `max_output_tokens`，不得改写共享模型对象。
4. 最终 system/context/question prompt 经绑定模型的确定性 token counter 计数，超过
   `max_input_tokens` 时在答案调用前 `INPUT_BUDGET_EXCEEDED`。
5. concrete `aadd`/`aget_evidence` 的 timeout 保留真实 stage、按批准上限有界重试；
   普通 upstream failure 不重试；受控源 decode failure 为 `PARSE_ERROR/source_decode`。

本轮新增 8 个测试函数，其中两组参数化分别展开为 2 和 3 个节点，因此 pytest 实际
新增 11 个 collected cases；完整文件现有 41 个测试函数、61 个 collected cases。把测试
文件对 PR #12 当前修复源码 `e2c05a8` 做本地组合运行，结果为 `50 passed, 11 failed`；
11 个失败分别命中上述四类 Review blocker，
原 50 项仍通过。Ruff 0.17.5 检查测试文件通过。组合运行使用 synthetic doubles、无凭据、
无真实论文和无 provider 调用；本机补充 pytest 未加载 `pytest-socket`，因此该 RED 证据
不替代此前及独立 Review 中带 socket fence 的验证。

本轮只修改测试、设计记录和 AI-use log，不写任何 `src/`。新精确测试 head 必须由
未参与本次测试编写的同学在 PR #9 重新 Review/Approve；在该批准出现前，不继续实现
剩余四项修复，也不合并 PR #9 或 PR #12。
