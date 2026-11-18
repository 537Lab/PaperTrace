# D 设计记录：获准资格门与生成前拒答（切片 1）

| 项 | 内容 |
|---|---|
| 日期 | 2026-11-17 |
| 阶段 | **仅测试准备（test-only）**；未写任何 `src/` |
| 状态 | 测试与 fixtures 已准备并在本地实测：单文件 32 failed / 1 passed（全部止于缺失的 D 模块）；等待非实现者对本测试 commit 的 GitHub 真实批准 |
| 模块 | D `answer` |
| 切片 | approved 资格判定 + 生成前拒答；**不存在 generation collaborator** |

## 1. 授权边界

本轮范围来自学生 **2026-11-17 的自包含消息**，该消息明确说明它取代此前的附件，且是「本次范围的当前批准，不是对更早批准的重建，也不是对测试 commit 或源码实现的批准」。

被批准的写路径（仅此四项）：

- `test/offline/test_answer.py`
- `test/fixtures/answer/synthetic-corpus-a.txt`
- `test/fixtures/answer/synthetic-corpus-b.txt`
- `docs/team/designs/module-D/20261117-d-abstain-pre-generation-gate.md`

明确**未**被本记录或该消息授予的事项：

- 未批准任何 `src/` 实现；本轮 D 行为规则禁止写 `src/`，工具 permission 不改变这一点。
- 未批准任何具体测试 commit；需另一位未参与本测试实现的学生在 GitHub 对具体 commit 实际 Approve。
- 未批准依赖安装、产品模型/网络调用、commit、push、merge。
- 未修改共享契约、依赖、lockfile、配置、权限、CI、共享 fixtures 或共享 AI-use log。

## 2. 切片的目标结果

研究者针对固定 `CorpusSnapshot` 与问题请求回答时，D 先用只读审核投影判断「是否存在人工获准且可核验归属的证据」：

- 没有获准证据 → 返回 contract 合法的 `abstained` 草稿，并且**根本不进入生成**（本切片没有生成端口可进入）。
- 有获准证据 → 纯规则门判定 eligible，但服务返回 `failed`（`GENERATION_PATH_NOT_ENABLED`），因为生成路径尚未接线。
- 审核状态不可读 / 投影形状坏 / 请求作用域不匹配 / 获准证据不属于本轮快照 → 抛 D 本地类型化错误，**不构造任何草稿**。

本切片不做的事：不检索、不生成、不做 token 预算、不做发布门、不重放 C 的 ledger、不证明任何语义忠实度。

## 3. 需求与不变量追踪

| ID | 本切片的可测部分 | 未覆盖部分（不得宣称完成） |
|---|---|---|
| `FR-D-01` | 空获准集 → `abstained`，无草稿泄漏、无生成入口 | 真实 factory/SDK/HTTP 层计数为 0（需 B 适配器与外呼 spy，属集成切片） |
| `FR-D-02` | 引用集在本切片恒为空；获准 ID 必须属于本轮快照与文档版本 | 真实 raw 引用解析、生成中/落盘前 freshness 竞态 |
| `FR-D-03` | eligible 也不产生成功草稿；D 包静态不 import `paperqa`/供应商 SDK/HTTP 栈（补充观察） | `aquery` 参数、pre/post、自动补证、Agent 禁用（B 适配器职责） |
| `INV-01` | 空获准集零生成 | 同上，本切片没有可计数的出站层 |
| `INV-04` | `cited ⊆ sent ⊆ approved` 的三个集合在本切片退化为全空或 `sent=cited=∅` | 真实引用映射与发布门 |
| `COST-01` | 测试不使用产品模型、凭据或网络；`--disable-socket` 生效 | — |

## 4. 提议接口（实现必须与此一致，否则测试应继续 RED）

以下名字是**本模块提议的 D-local 接口**，当前均未实现。它们不是对 C/共享契约的修改。

### 4.1 `papertrace.answer.model`

```python
class AnswerRequest(BaseModel):          # frozen=True, extra="forbid"
    snapshot: CorpusSnapshot
    question_id: QuestionId
    answer_id: AnswerId
    requested_at: UTCTimestamp
    evidence: tuple[EvidenceRecord, ...]


class ReviewProjectionView(Protocol):    # 结构型；不做 isinstance 判定
    snapshot_id: str
    question_id: str
    revision: int
    digest: str
    accepted_evidence_ids: Sequence[str]
    events: Sequence[object]


class ReviewProjectionPort(Protocol):
    def read_projection(self, question_id: str) -> ReviewProjectionView: ...


@dataclass(frozen=True)
class EligibilityDecision:
    eligible: bool
    approved_evidence_ids: tuple[EvidenceId, ...]
    reason: str | None


REFUSAL_NO_APPROVED_EVIDENCE = "NO_APPROVED_EVIDENCE"
REFUSAL_GENERATION_PATH_NOT_ENABLED = "GENERATION_PATH_NOT_ENABLED"
```

`QuestionId`、`AnswerId`、`UTCTimestamp`、`EvidenceId` 复用 `papertrace.contracts` 的公开类型别名，不新增共享定义。

### 4.2 `papertrace.answer.errors`

```text
AnswerPreparationError(Exception)
├── ReviewStateUnavailableError
└── ReviewProjectionInvalidError
    ├── ProjectionShapeError
    ├── ProjectionScopeMismatchError
    ├── UnknownAcceptedEvidenceError
    └── EvidenceProvenanceError
```

### 4.3 `papertrace.answer.eligibility`

```python
def evaluate_eligibility(
    *, projection: object, request: AnswerRequest
) -> EligibilityDecision: ...
```

纯函数，无 I/O、无时钟、无随机、无模型。

### 4.4 `papertrace.answer.service`

```python
class AnswerService:
    def __init__(self, *, projections: ReviewProjectionPort) -> None: ...
    def prepare(self, request: AnswerRequest) -> AnswerDraft: ...
```

**不约束实现细节：** 本切片不要求 `AnswerDraft` 从哪个模块导入，也不要求可 monkeypatch 的内部结构。「审核状态不可读」只按可观察行为断言：抛出类型化错误、不返回草稿（见 §9）。

### 4.5 `papertrace.answer.__init__`

顶层重新导出 4.1–4.4 的全部公开名字（测试通过 `papertrace.answer.<name>` 解析）。缺失任一名字时测试以断言失败，而不是导入堆栈。

## 5. 校验流水线（顺序固定）

`evaluate_eligibility` 与 `AnswerService.prepare` 共用同一顺序；第一个失败步骤决定错误类型，后续步骤不再执行。

| # | 检查 | 规则 | 失败类型 |
|---|---|---|---|
| 1 | 投影可读形状 | 必需属性存在且非 `None` | `ProjectionShapeError` |
| 1a | `revision` | `type(value) is int`（显式拒绝 `bool`）且 `>= 0` | `ProjectionShapeError` |
| 1b | `digest` | 匹配 `^[0-9a-f]{64}$` | `ProjectionShapeError` |
| 1c | `accepted_evidence_ids` | 序列；每项匹配 `^ev-[0-9a-f]{64}$`；无重复 | `ProjectionShapeError` |
| 1d | 头部 ID | `question_id` 匹配 `^q-[a-z0-9][a-z0-9_-]{0,63}$`；`snapshot_id` 匹配 `^snap-[0-9a-f]{64}$` | `ProjectionShapeError` |
| 1e | 空账本一致性（临时） | `revision == 0` ⇒ `accepted_evidence_ids` 与 `events` 均为空 | `ProjectionShapeError` |
| 2 | 头部作用域 | `projection.snapshot_id == request.snapshot.snapshot_id` 且 `projection.question_id == request.question_id` | `ProjectionScopeMismatchError` |
| 3 | 成员资格 | 每个 accepted ID 必须出现在 `request.evidence[*].evidence_id` | `UnknownAcceptedEvidenceError` |
| 4 | 证据归属 | 对每个 accepted 对应记录：`record.snapshot_id` 相符；`record.document_id` 属于该快照；`record.version_sha256` 等于该文档版本 | `EvidenceProvenanceError` |
| 5 | 决策 | `approved` 非空 ⇒ `eligible=True, reason=None`；否则 `eligible=False, reason=REFUSAL_NO_APPROVED_EVIDENCE` | — |

本切片**不**做的校验（属 C 的权威）：不根据 `events` 推导 accepted、不重算 ledger digest、不校验 `actor_kind`/`reviewer_ref`、不做 revision 单调性重放。`digest` 只查形状，信任其来自 C；这一点是未决集成问题（见 §12）。

同一组检查必须能由纯函数 `evaluate_eligibility` 直接触发：测试既走服务（检查包装层），也直接调用门（检查门本身）。服务层的检查不能掩盖纯门里的作用域/成员/归属缺陷。

## 6. 服务行为与草稿构造

1. 调用 `projections.read_projection(request.question_id)` **恰好一次**。
2. 端口抛出的异常**原样传播**，不包装、不降级为草稿。字典型/属性字典型投影的读取错误映射仍是未决问题。
3. `evaluate_eligibility(...)`。
4. 非 eligible → `AnswerDraft(status="abstained", approved=(), sent=(), citation=(), body="", refusal_reason=REFUSAL_NO_APPROVED_EVIDENCE, ...)`。
5. eligible → `AnswerDraft(status="failed", approved=decision.approved_evidence_ids, sent=(), citation=(), body="", refusal_reason=REFUSAL_GENERATION_PATH_NOT_ENABLED, ...)`。
6. 两种路径都必须：`review_revision = projection.revision`、`review_digest = projection.digest`（**不得**补造）、`answer_id = request.answer_id`、`snapshot_id = request.snapshot.snapshot_id`、`question_id = request.question_id`、`generated_at = request.requested_at`。
7. 永不设置 `sent_evidence_ids` / `citation_evidence_ids`；本切片没有生成，因此 `sent` 与 `cited` 必须为空。
8. 不新增 `stale` 等枚举；`stale` 只是未来的阻断原因/标签。

## 7. 与 C 提案（PR #2）的临时映射

C 的提案（`ledger.projection(question_id)`，字段含 `snapshot_id/question_id/revision/digest/accepted_evidence_ids/events`）**是测试提案，不是已批准或已实现的接口**。D 本轮：

- 不 import C，不访问网络，不依赖其模块路径。
- 测试内的 `FakeProjection` 是显式临时的 duck-typed 替身，字段名与提案同形，便于将来重新映射。
- 不假设返回值是 dataclass 还是 dict；D 只做属性访问。若 C 最终返回 `Mapping`，需要新增一个适配步骤（未决问题）。

## 8. 合成材料

两个文件均为自写、非真实论文、非模型输出、非人工审批：

| 文件 | 字节数 | SHA-256（测试运行时由真实字节计算） | 第 2 行原文（用作 excerpt） |
|---|---|---|---|
| `synthetic-corpus-a.txt` | 139 | `c0f9f0280ad186d9e78ffe5d9c5905ce5d4bdb02c275a81c025deb30190646eb` | The synthetic resonance cell stores 12 units of daylight energy. |
| `synthetic-corpus-b.txt` | 150 | `0477e2e63c958ded9db678e78fe56e470d4b0bdf0b43b16ce1cb01299541b833` | The synthetic resonance cell releases 3 units of daylight energy per cycle. |

`DocumentVersion.version_sha256` 由测试对文件字节现算；`CorpusSnapshot`、`EvidenceRecord`、`SourceLocator` 一律通过真实共享契约构造，不手填随机 hash。fixture 的 `created_at`/`retrieved_at` 固定为 `2026-11-17T00:00:00Z`，保证离线确定性。

## 9. 测试清单（`test/offline/test_answer.py`）

共 14 个测试函数、33 个用例（含参数化展开）。

| 测试 | 覆盖 | 关键断言 |
|---|---|---|
| `test_projection_without_accepted_evidence_abstains`（revision 0 / revision 3+event） | FR-D-01、INV-01 | `abstained`；三集全空；`body==""`；refusal reason 常量；`review_revision`/`review_digest` 与投影一致；`generated_at` 取请求时间 |
| `test_pure_gate_marks_accepted_evidence_eligible` | FR-D-02、INV-04 | 决策 `eligible=True`、approved ID 精确、`reason is None`、决策对象不携带 `sent` |
| `test_pure_gate_rejects_mismatched_scope_membership_and_provenance`（6 例） | 检查 2–4 | **直接调用 `evaluate_eligibility`**；先验证同输入可 `eligible=True`，再分别断言 `ProjectionScopeMismatchError` / `UnknownAcceptedEvidenceError` / `EvidenceProvenanceError` |
| `test_eligible_evidence_is_not_generated_in_this_slice` | FR-D-03（部分） | `failed`；approved 保留；sent/cited 空；reason `GENERATION_PATH_NOT_ENABLED` |
| `test_service_reads_the_projection_once_for_the_requested_question` | FR-D-01 | `reader.reads == [question_id]` |
| `test_proposed_refusal_reasons_are_stable_strings` | 契约稳定性 | 两个常量的字面值 |
| `test_unavailable_review_state_raises_without_returning_a_draft` | FR-D-01、INV-01 | 抛 `ReviewStateUnavailableError`；错误消息原样传播；不锁定 `AnswerDraft` 的导入位置 |
| `test_malformed_projection_raises_shape_error`（11 例） | 检查 1 | 每个坏形状都先有「合法投影 → abstained」对照，再断言 `ProjectionShapeError` |
| `test_projection_header_scope_mismatch_raises`（2 例） | 检查 2 | 对照为 `failed`；错问题/错快照断言 `ProjectionScopeMismatchError` |
| `test_unknown_accepted_evidence_raises` | 检查 4 | 对照为 `failed`；未知 ID 断言 `UnknownAcceptedEvidenceError` |
| `test_evidence_provenance_mismatch_raises`（foreign snapshot / unknown doc / wrong version） | 检查 3、4 | 对照为 `failed`；三种归属错误断言 `EvidenceProvenanceError` |
| `test_returned_drafts_round_trip_through_shared_contracts` | QA-01、INV-04 | `AnswerDraft.model_validate_json(model_dump_json()) == draft` |
| `test_static_import_scanner_flags_provider_and_network_imports` | 补充（反空转） | 对已知坏样例断言扫描器返回精确命中列表，防止扫描器空转通过 |
| `test_answer_package_has_no_direct_upstream_provider_or_network_imports` | FR-D-03（补充） | AST 扫描 `papertrace/answer/*.py`：无 `paperqa`、无供应商 SDK、无直接 HTTP/网络栈导入 |

## 10. 负测为什么能抓到「检查被删掉」

- 每个负测先跑一个**同构造、仅修正目标字段**的对照，证明该输入本来可以走到 `abstained`/`failed`；因此失败只能由目标检查造成，而不是夹具本身坏了。
- 断言的是**具体错误类型**（如 `UnknownAcceptedEvidenceError`）或**具体决策**（`eligible is True`、approved ID 元组），不断言宽泛的 `failed` 状态。若删掉作用域或成员检查，代码会落到 `failed`/`abstained` 草稿，`pytest.raises` 立即失败。
- 门级负测与 service 级负测**并存**：即使 `AnswerService` 包装层保留了正确检查，纯门 `evaluate_eligibility` 自身的成员/归属检查被删，也会被 `test_pure_gate_rejects_mismatched_scope_membership_and_provenance` 的 6 个用例抓到。
- 「不可读状态」只断言类型化错误向外传播（并核对错误消息），不锁定实现从哪里导入 `AnswerDraft`；若实现吞掉该错误并返回草稿，`pytest.raises` 立即失败。

## 11. 明确不证明的内容

- **不**证明 factory/SDK/HTTP 出站尝试为 0，也**不**完成 `FR-D-01`、`FR-D-02`、`FR-D-03`。本切片根本没有生成 collaborator，`sent=∅` 是结构事实而非外呼观测。
- `--disable-socket` 与 AST 导入扫描只是**补充观察**，不是外呼证明，也不是沙箱。静态扫描覆盖 `paperqa`、直接供应商 SDK（`openai`/`anthropic`/`cohere`/`mistralai`/`litellm`/`fhlmi`/`google`）与 HTTP/网络栈（`httpx`/`requests`/`aiohttp`/`urllib3`/`socket`/`http.client`/`urllib.request`），但它只证明「源码文本里没有这些导入」，不证明运行时无出站。
- 不证明 C 的 ledger/authority 真实性；`digest` 仅形状校验。
- 不证明答案忠实度、相关性或任何模型质量；本轮零产品模型调用。
- 测试通过也不等于学生测试批准或实现批准。

## 12. 未决接口问题

1. **C 投影的返回类型**：`ledger.projection(question_id)` 返回对象还是 `Mapping`？本轮按属性访问写测试；若为映射需增加一层适配，届时应先改本记录与测试。
2. **读取错误语义**：D 是原样传播 C 的异常，还是要求 C 统一抛 `ReviewStateUnavailableError`？本轮测试的 fake 直接抛 D 错误，避免假设 C 的实现。
3. **`events` 的校验深度**：本轮只要求「序列」且 `revision == 0` 时为空；是否要校验事件与 accepted 的一致性属于 C 的重放职责。
4. **`revision == 0 ⇔ 空账本`**：本切片把它当作形状一致性；若 C 允许 revision 0 携带事件，需要重新批准该规则。
5. **`digest` 算法**：D 不重算；若将来 D 要独立验证 digest，需要 C 提供可复现定义（契约级变更）。
6. **`request.evidence` 为空**：当前允许；此时任何 accepted ID 都会触发 `UnknownAcceptedEvidenceError`。是否需要更早的显式错误待定。
7. **请求内重复 `evidence_id`**：当前未拒绝（共享契约的身份算法使真正重复只可能来自完全相同来源）。是否加严待定。
8. **`answer_id` 唯一性/冲突**：由 D 还是编排层负责，未定。
9. **`generated_at` 来源**：本切片取 `request.requested_at`；将来若引入独立时钟，需要新的批准。
10. **`requested_at` 的用途**：目前只用于 `generated_at`，不参与 freshness；freshness 属后续切片。

## 13. AI-use log（提议条目，仅置于本记录）

共享 `docs/ai-use-log.yaml` **未被修改**；本条仅为提议，状态为 **awaiting shared-log editor**，需由共享日志编辑者决定是否合入。

```yaml
- entry_id: D1-TESTPREP-20261117-01
  timestamp: '2026-11-17T06:07:18Z'
  tool: OpenCode desktop session, agent role papertrace-build-D (test-preparation stage)
  model: deepseek-flash (provider deepseek; runtime label "DeepSeek V4.1 Flash 1017", not independently verified)
  purpose: 模块D切片1（获准资格门与生成前拒答）的离线测试、合成fixtures与设计记录；不实现src
  scope:
  - test/offline/test_answer.py
  - test/fixtures/answer/synthetic-corpus-a.txt
  - test/fixtures/answer/synthetic-corpus-b.txt
  - docs/team/designs/module-D/20261117-d-abstain-pre-generation-gate.md
  status: test-preparation-complete-awaiting-independent-test-commit-approval
  approvals:
  - 学生2026-11-17自包含消息批准“仅模块D测试准备”范围；不构成测试commit批准或源码实现批准
  verification:
  - 本地实测（.venv, CPython 3.14.8, requirements-init.lock）：单文件 32 failed / 1 passed；全套离线 32 failed / 331 passed / 2 skipped
  - 32 个失败全部是“proposed module papertrace.answer is not implemented”的预期缺失实现断言，无 collection error
  - ruff 1 个既有错误位于未修改的 scripts/paperqa_smoke.py（I001）；mypy 0；schema PASS
  limitations:
  - 不是非实现者的GitHub Approve，不证明测试已被人工批准
  - 未写src/，未改共享契约/依赖/CI/权限/共享fixture/共享日志
  - 下游断言在实现前仍未验证；共享 AI-use log 合入待共享日志编辑者处理
```

## 14. 实际验证结果（2026-11-17）

### 14.1 环境（经学生单独批准后搭建）

| 项 | 值 |
|---|---|
| 解释器 | uv 受管 CPython **3.14.8**（下载 25.4 MiB） |
| venv | `.venv`（gitignored）；`uv venv --python 3.14 --no-project` |
| 依赖 | `uv --no-config pip sync --python .venv/bin/python --no-build requirements-init.lock`，exit 0，25 个锁定包 |
| 离线干跑 | 缓存缺 `librt==0.16.0`（信息性，未阻断批准后的安装） |
| tracked 文件 | 搭建前后 `git status` 一致；`git diff` 为空 |

### 14.2 五条获批离线命令

| 命令 | 退出码 | 实际计数 |
|---|---|---|
| `.venv/bin/python -m pytest -c papertrace.pytest.ini test/offline/test_answer.py` | **1** | 收集 **33**；**32 failed, 1 passed** |
| `.venv/bin/python -m pytest -c papertrace.pytest.ini test/offline` | **1** | **32 failed, 331 passed, 2 skipped**（53.04s） |
| `.venv/bin/python -m ruff check --config papertrace.ruff.toml src/papertrace test/offline scripts` | **1** | 1 个错误：`scripts/paperqa_smoke.py:37:1 I001`（既有且未修改的文件）；`test_answer.py` 干净 |
| `.venv/bin/python -m mypy --config-file mypy.ini src/papertrace` | **0** | `Success: no issues found in 2 source files` |
| `.venv/bin/python scripts/gates.py --gate schema` | **0** | `PASS`；`remote_enforcement: NOT_DEPLOYED_OR_VERIFIED` |

### 14.3 失败分类

- **预期缺失实现：32 个**（31 个 `AssertionError` + 1 个 `pytest.fail`），消息全部为 `proposed module papertrace.answer is not implemented`；pytest 正常收集 33 个用例，**不是 collection error**。
- **通过：1 个** `test_static_import_scanner_flags_provider_and_network_imports`（不依赖 D 模块）。
- **环境失败：0**。
- **无关**：2 个 skip（`OpenCode executable is not installed`）；ruff 的 `I001` 位于未修改的 `scripts/paperqa_smoke.py`，本切片不修复。
- **仍未验证**：下游断言（具体错误类型、门槛决策、草稿往返）要等实现后才会真正执行；当前 RED 只证明缺失实现，不证明测试语义正确。

## 15. 提议「独立环境准备命令」前必须核对的信息

1. `.python-version` 当前为 `3.13`；`requires-python` 为 `>=3.11,<3.15`。需要学生确认使用 3.13 还是 3.14（`ruff`/`mypy` 的 `target-version`/`python_version` 写的是 3.14）。
2. 离线团队测试的最小依赖集看起来是 `requirements-init.lock`（含 `pytest==9.2.0`、`pytest-socket==0.8.1`、`pydantic==2.14.3`、`mypy==1.20.2`、`ruff==0.17.5`、`jsonschema`），而不是完整的 `requirements-runtime.lock` / upstream extras。需确认是否有意如此。
3. 该 lock 是否与 `uv.lock`/`pyproject.toml` 保持一致性；安装必须 `--frozen`/`--no-deps` 类只读复现，不得改写任何 lockfile（这些文件在冻结区）。
4. 网络是否可用、是否允许从 PyPI 拉取（含 wheel 缓存）；若不允许，需要学生提供离线 wheel 目录。
5. `.venv` 是本地未跟踪目录（`git status` 当前不显示），建立它不得产生受跟踪文件。
6. `pytest-socket` 提供的 `--disable-socket` 必须在离线套件中生效；`papertrace.pytest.ini` 已开启，但需实测确认。
7. 是否需要为 `test/offline/test_full_regression.py` 的 runtime 子套件准备额外依赖；本切片只要求 `test/offline/test_answer.py` 与 `test/offline`。

在上述 1–7 得到学生确认前，不提议、不执行任何安装命令。

## 16. 修订记录（2026-11-17，学生指示的三项更正）

1. 静态依赖检查从 `paperqa` 扩展到直接供应商 SDK 与 HTTP/网络栈，并增加「扫描器反空转」自测；仍不声称证明零出站尝试。
2. 新增**直接调用 `evaluate_eligibility`** 的负测（作用域、未知获准、文档/版本归属各 1–2 例），避免 service 层检查掩盖纯门缺陷。
3. 移除「`service` 必须在模块顶层导入 `AnswerDraft`」的可 monkeypatch 约束；「不可读状态」只断言类型化错误向外传播。

三项更正不改变 §4 的接口名、§5 的校验顺序与 §6 的草稿构造规则；用例计数更新为 14 个测试函数 / 33 个用例。


## 17. C 接口核对与协作状态（2026-11-18）

本节是 Codex 只读核对腾讯协作板与 GitHub 后形成的补充记录，不是 OpenCode 开发会话、审批证明、接口变更批准或集成通过记录。§7、§12 保留此前提案形成时的历史状态；涉及 C 当前候选实现的信息以本节补充为准。未修改本轮测试、源码或共享契约。

### 17.1 已核实的来源

- 腾讯共享文档第18节任务板，李宇轩行“需要协调”中的“回复D”：ComparisonView 字段；无审核记录时 revision=0、pending；损坏账本抛 ReviewLedgerCorrupted。
- 文档：https://docs.qq.com/aio/DRkZieXhmaFZUc0xy
- C 实现 PR：https://github.com/537Lab/PaperTrace/pull/4
- 核对源码版本：3f32f9aea3d64ef844d74b2cc2cac51e7f614d6d，src/papertrace/review/service.py。该 PR 尚为 open，不是 main 已有实现；本轮未独立重跑 C 测试。

### 17.2 对齐结论与未决边界

| 项目 | C 当前候选实现 | 对 D 的含义 |
| --- | --- | --- |
| 状态读取 | ReviewLedger.projection(question_id) -> ReviewProjection；ledger 构造时绑定 snapshot | D 拟议 read_projection 需经获批的中立适配接到 projection；D 不直接依赖 C 私有实现 |
| 返回类型 | frozen dataclass 对象，属性含 snapshot_id、question_id、revision、digest、accepted_evidence_ids、events | 与现有 FakeProjection 基本同形，不再将“对象还是字典”列为当前候选源码未知项；仍待 owner 确认稳定接口 |
| 无账本文件 | 空事件、revision=0、accepted为空、按 C 算法计算 digest | 合法空审核状态，应拒答；D 转交 digest，不自行重算或填零 |
| 损坏账本 | ReviewLedgerCorrupted | 不得捕获后转换为空 approved；传播或映射方案仍待双方确认 |
| 其他读取故障 | 普通文件读可能抛 OSError 等 | 不得将 I/O 失败冒充“无人审核”；错误适配需在后续批准范围明确 |
| 版本检查 | verify_current(question_id, revision, digest)，失败为 ReviewTokenStale / ReviewDigestMismatch | 留待后续新鲜度/发布切片，不提前加入本轮实现 |
| 比较视图 | ComparisonView，含原文、摘要、状态、定位等 | 用于展示，不从展示结果另造审核权威；D 使用可信 ReviewProjection |

本次仅记录映射提案，不改 §4/§5/§6 对应测试语义。当前源码读取端口异常原样传播；如将来需要映射为 D 的 ReviewStateUnavailableError，必须明确适配层、保留原因、同步审查相关测试，不能静默修改。

### 17.3 审批核对（仍待明细确认）

- D PR #3 当前 head 仍为 29b2133829666c25b42688ae7e5b42ac6130cbd8。
- GitHub reviewDecision 显示 APPROVED，页面显示“1 approval received”。但 REST reviews、GraphQL latestReviews 与页面展开未提供批准人和绑定提交明细；本记录不据此断言无批准，也不编造批准人/commit。
- 需由实际批准同学提供其已提交 review 的账号和记录入口/截图，核对独立性及精确测试版本后再开始源码实现；不要求为了记录差异直接重复批准。
- C PR #4 正文与腾讯任务板仍引用 92498e7，最新 head 为 3f32f9a。建议 C owner 更新审查目标，D 不代改其任务行。
- D 共享 AI-use log 条目整合仍待处理；本次只更新设计记录，不修改共享日志、PR、审批或工作流。

### 17.4 学生确认与可核验状态（2026-11-18，OpenCode 会话记录）

- 学生在本轮消息中确认：李亚飞（Li Yafei）已批准测试提案 PR #3，并要求本条按“学生转述的确认”记录，不补造 GitHub review URL、截图或其他审批证据。
- 只读核对（`gh pr view 3`）：`state=OPEN`、`reviewDecision=APPROVED`、`headRefOid=29b2133829666c25b42688ae7e5b42ac6130cbd8`，与待批准的测试 commit 完全一致；但 `reviews` 与 `latestReviews` 均为空，API 未提供批准人账号或逐条 review 记录。
- 记录口径：审批的**存在性**由 GitHub 聚合状态与学生转述共同支持；**批准人账号与独立性未经 API 独立核验**。本记录不写成“GitHub 已核实的具名 Approve”，也不声称持有截图。
- 实现仅按该确认推进切片 1；若后续需要把批准人与 commit 绑定写成可审计记录，仍由该同学补充 review 入口或截图。

## 18. 实现会话 AI-use log 提议条目（2026-11-18）

共享 `docs/ai-use-log.yaml` 的编辑入口/所有权仍未解决，因此本条**只**记录在本设计记录，状态为 **awaiting shared-log editor**；共享日志未被修改。本条与 §13 的测试准备条目是两次不同会话，不合并、不互相替代。

```yaml
- entry_id: D1-IMPL-20261118-01
  timestamp: '2026-11-17T16:47:39Z'  # 本机时间 2026-11-18 (UTC+8)
  tool: OpenCode desktop session, agent role papertrace-build-D (source implementation stage)
  model: deepseek-flash (provider deepseek; runtime label "DeepSeek V4.1 Flash 1017", not independently verified)
  purpose: 实现模块D切片1：读取审核投影、资格校验与生成前拒答；不实现生成/发布
  scope:
  - src/papertrace/answer/__init__.py
  - src/papertrace/answer/model.py
  - src/papertrace/answer/errors.py
  - src/papertrace/answer/eligibility.py
  - src/papertrace/answer/service.py
  - docs/team/designs/module-D/20261117-d-abstain-pre-generation-gate.md
  status: implementation-complete-awaiting-pr-review-not-merged
  student_decisions:
  - 学生批准本模块测试准备范围（2026-11-17），随后批准 CPython 3.14 venv 与 requirements-init.lock 安装
  - 学生确认李亚飞已批准测试提案 PR #3；本条只按学生转述记录，未补造 review URL/截图
  - 学生批准切片1实现范围，并要求保留未提交的 .DS_Store 删除、不纳入提交
  approvals:
  - 测试commit批准：学生转述的李亚飞批准 + GitHub reviewDecision=APPROVED 绑定 29b2133；逐条review不可得（§17.4）
  - 实现范围：学生2026-11-18消息；不构成 merge 批准
  verification:
  - '.venv/bin/python -m pytest ... test/offline/test_answer.py → exit 0；33 passed'
  - '.venv/bin/python -m pytest ... test/offline → exit 0；363 passed, 2 skipped（skip 为既有 OpenCode 可执行文件缺失）'
  - 'ruff（D 文件单独运行）→ exit 0；全局运行仍因未修改的 scripts/paperqa_smoke.py I001 失败'
  - 'mypy src/papertrace → exit 0，7 source files'
  - 'scripts/gates.py --gate schema → exit 0，PASS'
  limitations:
  - 未调用产品模型；未新增网络调用（仅先前获批的解释器/依赖下载）
  - 真实 C 集成未验证：C PR #4 仍 open，投影映射为候选接口
  - 生成、引用解析、freshness/token、预算与发布门均未实现
  - 静态导入扫描只是补充观察，不证明零出站尝试
  - 共享 AI-use log 合入待共享日志编辑者处理；本条不是共享日志记录
```
