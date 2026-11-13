# PaperTrace 共享数据契约 v1

状态：**共享接口与离线结构验证已实现；A–E 业务、真实人审账本与真实发布判断未实现。**

实现：`src/papertrace/contracts.py`。架构参照 ADR-001；需求 QA-01。INV-01 至 INV-05 仅有下述局部数据结构支持，不能据此宣称端到端不变量已经满足。初始化由 Hermes 执行，不是学生 OpenCode 开发贡献或课程 D5 Transcript。

## 1. 通用约定

- 七个模型均为 Pydantic v2：`frozen=True`、`extra="forbid"`、`revalidate_instances="always"`。集合在内存中为 tuple，JSON 中为 array；不保存可变 dict/list 字段。
- 每个对象，包括嵌套的 `DocumentVersion`、`SourceLocator`，都必须显式提供 `schema_version: 1`。缺失、其他版本、字符串 `"1"` 和布尔值 `true` 均拒绝，不静默迁移。
- 所有时间必须带时区，校验后统一转为 UTC；JSON 序列化使用 UTC。时间字段没有当前时间默认值，调用方必须明确传入。无时区时间拒绝。
- `NonBlank` 表示包含至少一个非空白字符的字符串；不自动 trim、不大小写转换、不进行 Unicode 归一化。
- SHA-256 必须是 **64 位小写十六进制**，正则 `^[0-9a-f]{64}$`。不接受大写、前后空白、非十六进制字符或自动修复。
- `PositiveInt` 为严格整数且 `>= 1`；不接受布尔值或数字字符串。
- `ReviewRevision` 为严格整数且 `>= 0`；0表示没有任何人工审核事件，只能记录拒答/失败或阻断，不能形成获准草稿或发布。真实ReviewDecision的revision仍从1开始。
- 冻结与合法 JSON 不等于真实性、权限或密码学签名。`model_construct()`、`model_copy(update=...)` 等 Pydantic 绕过接口不应用于不可信输入；调用 `model_validate()` / `model_validate_json()` 重新校验。不能把 Python 对象自身当作可信审批。

### 标识符规则

| 类型 / 字段 | 精确规则 | 意义 |
|---|---|---|
| `document_id` | `^doc-[a-z0-9][a-z0-9_-]{0,63}$` | 调用方分配的逻辑文献 ID，不是内容哈希 |
| `snapshot_id` | `^snap-[0-9a-f]{64}$` | 下文规范 JSON 的内容派生身份 |
| `evidence_id` | `^ev-[0-9a-f]{64}$` | 下文原文与来源定位派生身份 |
| `question_id` | `^q-[a-z0-9][a-z0-9_-]{0,63}$` | 调用方分配的问题 ID |
| `answer_id` | `^ans-[a-z0-9][a-z0-9_-]{0,63}$` | 调用方分配的草稿/运行 ID，不是答案内容哈希 |
| `reviewer_ref` | `^reviewer-[A-Z][A-Z0-9_-]{0,31}$` | 如 `reviewer-A` 的非姓名代号；不是签名或认证证明 |
| `reason_codes` 中的项 | `^[A-Z][A-Z0-9_]{0,63}$` | 稳定机器原因码，不使用任意自然语言代替 |
| `chunk_id` | `NonBlank` | 解析块的不透明标识；定位还必须有页或行范围 |

所有标识符原样验证，不把上游 `Context.id`、摘要、文献标题或引用显示名改成可授予权限的 ID。

## 2. 精确字段

以下模型均额外包含必填的 `schema_version: Literal[1]`，表格不重复列出。

### `DocumentVersion`（A → B/C/D/E）

| 字段 | 类型 / 必填性 | 约束 |
|---|---|---|
| `document_id` | `DocumentId`，必填 | 逻辑身份 |
| `version_sha256` | `Sha256`，必填 | 应由 A 对原始文件字节计算；契约只验证格式 |
| `title` | `NonBlank`，必填 | 展示用标题，允许 Unicode |
| `source_name` | `NonBlank`，必填 | 纯文件名，不是本机路径或 URI |
| `status` | `Literal["ready"]`，必填 | 进入共享快照的版本仅能为 ready |

`source_name` 拒绝 `/`、`\`、`:`、`.`、`..` 以及 U+0000–U+001F / U+007F 控制字符。该字段不是文件访问授权，也不是跨平台文件系统清洗器。A 的导入中、失败状态属于未来 A 内部业务，不在共享 ready 文献模型中伪造 ready。

同一 `document_id` 的内容变化应有新的 `version_sha256` 与新快照。不同逻辑文献拥有相同字节哈希不被本契约自动合并；去重与文件读取尚未实现。

### `CorpusSnapshot`（A → 全部模块）

| 字段 | 类型 / 必填性 | 约束 |
|---|---|---|
| `documents` | `tuple[DocumentVersion, ...]`，必填 | 仅 ready 文献；逻辑 ID 不得重复；存储时按 ID 升序 |
| `created_at` | UTC aware datetime，必填 | 记录捕获时间，不参与身份哈希 |
| `snapshot_id` | `SnapshotId`，可省略以生成 | 显式传入则必须与规范哈希完全一致 |

一个快照内不能出现同一逻辑 ID 的两个版本，也不能重复同一个版本。允许空文献元组，以表示空的 ready 语料；这不允许生成科学回答，也不证明 A 已实现历史追加存储。

### `SourceLocator`（嵌入证据）

| 字段 | 类型 / 默认值 | 约束 |
|---|---|---|
| `page_start` / `page_end` | `PositiveInt | None`，默认 `None` | 1 基、两端包含的页范围 |
| `line_start` / `line_end` | `PositiveInt | None`，默认 `None` | 1 基、两端包含的行范围 |
| `chunk_id` | `NonBlank`，必填 | 原始解析块标识 |
| `parser_name` | `NonBlank`，必填 | 定位所用解析器名称 |
| `parser_version` | `NonBlank`，必填 | 定位所用解析器版本 |

页或行至少有一组完整范围；有起点必须有终点，反之亦然；终点不得小于起点。允许同时有页和行。只有 `chunk_id` 或自由文字、没有范围的定位不合法。定位与真实源文件是否相符由后续 B/D 适配器核对，不在模型内读取文件。

### `EvidenceRecord`（B → C/D/E）

| 字段 | 类型 / 默认值 | 约束 |
|---|---|---|
| `snapshot_id` | `SnapshotId`，必填 | 所声明的来源快照 |
| `document_id` | `DocumentId`，必填 | 所声明的逻辑文献 |
| `version_sha256` | `Sha256`，必填 | 所声明的来源内容版本 |
| `locator` | `SourceLocator`，必填 | 结构化来源定位 |
| `excerpt` | `NonBlank`，必填 | 原文摘录，不是模型摘要 |
| `retrieved_at` | UTC aware datetime，必填 | 不参与证据身份 |
| `advisory_summary` | `str | None`，默认 `None` | 明确仅供参考，不授予审核权限 |
| `upstream_context_id` | `str | None`，默认 `None` | 上游不透明调试关联，不作团队证据身份 |
| `evidence_id` | `EvidenceId`，可省略以生成 | 显式传入时验证规范哈希 |

**没有 `accepted` 或 `status` 字段。没有对应的有效审核决定即按 pending 处理；不能从模型摘要、上游评分、`Context.id` 或 evidence 对象本身推断 accepted。** `excerpt` 不自动去空白/改写，任何原文字符变化都改变证据身份。

### `ReviewDecision`（C → D/E）

| 字段 | 类型 / 必填性 | 约束 |
|---|---|---|
| `evidence_id` | `EvidenceId`，必填 | 被审核证据 |
| `snapshot_id` | `SnapshotId`，必填 | 该决定作用的快照 |
| `question_id` | `QuestionId`，必填 | 该决定作用的问题 |
| `status` | `pending | accepted | excluded`，必填 | 唯一允许表达审核状态的共享模型 |
| `actor_kind` | `Literal["human"]`，必填 | 模型/agent 不能声明决定者类型 |
| `reviewer_ref` | `ReviewerRef`，必填 | 非姓名代号，不生成签名 |
| `revision` | `PositiveInt`，必填 | 声明的审核账本修订号 |
| `reason` | `NonBlank`，必填 | 包括 pending 事件也须记录原因 |
| `decided_at` | UTC aware datetime，必填 | 决定/重置为 pending 的事件时间 |

审核权威只应来自 C 中真实人类操作产生并保存在可信账本里的 `ReviewDecision`。`actor_kind="human"` 本身只是结构限制，不能认证操作者；C 仍须实现人机操作边界、追加式账本、修订推进与摘要计算。**本轮未实现这些业务，更没有真实审批。**

### `AnswerDraft`（D → E）

| 字段 | 类型 / 默认值 | 约束 |
|---|---|---|
| `answer_id` | `AnswerId`，必填 | 草稿/生成运行身份 |
| `snapshot_id` | `SnapshotId`，必填 | 生成所绑定的快照 |
| `question_id` | `QuestionId`，必填 | 生成所绑定的问题 |
| `review_revision` | `ReviewRevision`，必填 | 生成所绑定的审核修订；0仅用于abstained/failed |
| `review_digest` | `Sha256`，必填 | 生成所绑定的账本摘要；本模型只验证格式 |
| `approved_evidence_ids` | `tuple[EvidenceId, ...]`，必填 | 声明的获准集合，无重复 |
| `sent_evidence_ids` | `tuple[EvidenceId, ...]`，必填 | 声明本轮实际发送集合，无重复 |
| `citation_evidence_ids` | `tuple[EvidenceId, ...]`，必填 | 声明正文引用集合，无重复 |
| `status` | `draft | abstained | failed`，必填 | 不允许直接 `released` |
| `body` | `str`，必填 | 状态约束见下表 |
| `refusal_reason` | `str | None`，默认 `None` | 拒答/失败原因 |
| `generated_at` | UTC aware datetime，必填 | 明确的生成/失败事件时间 |

三个 ID 元组保持传入顺序，但分别必须唯一，且恒有 `citation_evidence_ids ⊆ sent_evidence_ids ⊆ approved_evidence_ids`。

| 状态 | approved / sent | body | citation | refusal_reason |
|---|---|---|---|---|
| `draft` | 二者都非空 | 必须包含非空白字符 | 可为空，但必须在 sent 内 | 必须为 `None` |
| `abstained` / `failed` | 可以为空；仍受子集约束 | 必须严格为 `""` | 必须为空 | 必须包含非空白字符 |

获准集合为空时只能产生空正文、空引用的 `abstained` / `failed`。失败时可保留此前已发送的获准 ID 以供追溯，但不能泄漏科学回答。是否实际没有进行生成调用，是未来 D 的运行时责任；此处只有数据约束。

**这些集合是声明，不是外部账本真实性验证。** 本轮不检查它们是否真的是当前 accepted 集合，不验证真实出站内容，不解析 `body` 里的引用标记，也不计算权威 `review_digest`。合法 AnswerDraft 不能独立获得发布资格。

### `ReleaseDecision`（D → E）

| 字段 | 类型 / 必填性 | 约束 |
|---|---|---|
| `answer_id` / `snapshot_id` / `question_id` | 相应 ID，必填 | 声明绑定对象 |
| `review_revision` / `review_digest` | `ReviewRevision` / `Sha256`，必填 | 声明绑定的审核版本；0仅用于blocked |
| `status` | `released | blocked`，必填 | 发布判断的记录形态 |
| `reason_codes` | `tuple[ReasonCode, ...]`，必填 | 唯一机器码；没有隐式默认值 |
| `snapshot_check_passed` | strict bool，必填 | 声明快照/文献版本检查结果 |
| `review_check_passed` | strict bool，必填 | 声明审核修订、摘要、作用域检查结果 |
| `evidence_check_passed` | strict bool，必填 | 声明实际发送与获准范围检查结果 |
| `citation_check_passed` | strict bool，必填 | 声明引用映射与来源检查结果 |
| `answer_check_passed` | strict bool，必填 | 声明草稿结构/状态检查结果 |
| `decided_at` | UTC aware datetime，必填 | 判断时间 |

`released` 必须五个检查全部为 `True`，且 `reason_codes` 为空。`blocked` 必须至少有一个原因码；可有全 true 的结构检查而因其他运行策略被阻断。布尔字段不接受 `1` 或 `"true"`。

这是**结果记录模型，不是发布引擎**。任意调用方构造五个 true 仍无法证明执行过检查；D 必须从可信运行状态重新检查，再构造决定。它不替代真实发布判断、竞态防护、语义质量评估或人工审批。

## 3. Canonical hashing：跨模块必须完全相同

定义 `canonical_json(x)`：

```python
json.dumps(
    x,
    ensure_ascii=False,
    sort_keys=True,
    separators=(",", ":"),
    allow_nan=False,
).encode("utf-8")
```

随后使用 `hashlib.sha256(...).hexdigest()`。没有尾随换行，没有空格分隔符；不去空白、不转大小写、不做 NFC/NFKC 等 Unicode 归一化。这是本项目针对下述限定字段的规范 JSON，不宣称实现完整 RFC 8785。

### 快照身份

```text
snapshot_id = "snap-" + SHA256(canonical_json({
  "schema_version": 1,
  "documents": [完整 DocumentVersion JSON，按 document_id 升序]
}))
```

每个文献项恰含 `schema_version`、`document_id`、`version_sha256`、`title`、`source_name`、`status`。`created_at`、`snapshot_id` 本身不参与哈希。标题/显示文件名变化会改变快照身份，即使内容 SHA 不变；文献重排和捕获时间变化不改变身份。缺省 ID 自动生成；显式 ID 不一致拒绝。

### 证据身份

```text
evidence_id = "ev-" + SHA256(canonical_json({
  "schema_version": 1,
  "snapshot_id": snapshot_id,
  "document_id": document_id,
  "version_sha256": version_sha256,
  "locator": 完整 SourceLocator JSON,
  "excerpt": 原样摘录
}))
```

完整 locator 含 `schema_version`、`page_start`、`page_end`、`line_start`、`line_end`、`chunk_id`、`parser_name`、`parser_version`。未提供的范围字段校验为 `None` 后也以 JSON `null` 参与哈希，不省略。上游 ID、摘要与 `retrieved_at` **不参与身份**。来源快照、文献、内容版本、定位/解析器或摘录变化，原 evidence ID 必须失效。

`review_digest` 的权威账本组装、排序、修订与核验协议仍由 C/D 在正式实现时确定并共同测试，本模型只约束 64hex 与显式绑定，不提前实现账本。合成 fixture 的摘要只是明确 synthetic 结构的哈希，不是运行时认可或签名。

## 4. 结构校验与业务权威分界

| 本轮模型已做 | 仍须学生模块实现、不能由契约自证 |
|---|---|
| 版本、ID、时间、定位、重复项、状态、子集形状校验 | A：真实文件字节哈希、ready 状态来源、持久化快照与历史不覆盖 |
| 从规范文献元数据派生并核验快照 ID | B/D：文献确实属于快照，定位与摘录匹配源文件，解析器可复现 |
| 从原文与定位派生并核验证据 ID | C：真实人工操作认证、审核事件追加、修订单调推进、可信 digest |
| 禁止 evidence 自带 accepted；review actor 必须 human | D：获准集合从可信 ledger 读取，实际 outbound 只使用该集合 |
| 空获准集合只能是空正文拒答/失败 | D：零获准证据时零模型调用、生成中语料/审核变化即阻断 |
| 引用声明只能来自声明 sent/approved 范围 | D：实际正文引用解析、版本映射、外部 ledger 与新鲜度核验 |
| released 声明必须五项 true 且无原因码 | D：真实发布判断和语义阈值；E：仅按可信决定显示/导出与保存历史 |

以上跨对象与外部状态验证**本轮未实现**。不要把单个合法对象或合成场景中的一致引用当作运行时授权测试通过。

## 5. 样例、Schema 与运行

- `test/fixtures/contracts/`：七个手写、明确 `synthetic: true` 的 wrapper，以及一份自写 TXT。wrapper 的 `data` 才是契约输入；元信息不可传入封闭模型。没有真实论文、付费模型回复、真人签名或审批。
- 本目录七个 `*.schema.json` 由真实 `model_json_schema()` 生成，测试核对无漂移。`uniqueItems` 已显式公开。规范哈希相等、定位范围关系、状态条件和跨字段子集等依赖 Pydantic validators，不能仅靠普通 JSON Schema 验证宣称已检查完毕。
- 测试覆盖七类的 JSON 往返与 Unicode；五个主类分别有负测；包括错版本、额外字段、重复身份、哈希不一致、非法 SHA、无定位、反向范围、伪造 actor、空获准集合、声明范围外引用、越权状态、不恰当 release、无时区时间及构造实例重校验。
- 测试只导入团队共享接口，不导入 PaperQA、不访问网络、不读取凭据、不调用模型。

独立验证命令（显式避开上游 pytest 配置）：

```sh
PYTHONPATH=src .venv/bin/python -m pytest -c /dev/null --disable-socket test/offline/test_contracts.py
```

真实逐项 RED→GREEN 与后续回归/静态检查输出保存在 `artifacts/verification/contracts-tdd.txt`。该文件是工程执行证据，不是测试事前人工批准记录或学生 OpenCode Transcript。
