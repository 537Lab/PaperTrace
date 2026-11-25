# A 测试提案 v1｜最终隔离验证已完成 / 待独立学生审核

本文件记录实际测试，不重新提交待批架构计划。学生批准仅限 8 文件的测试准备，
不是具体测试 commit 的独立 GitHub Approve；没有任何源码实现授权。
19 个 `test_` 函数，实际已收集 **33 nodes**，其中 2 个基础检查、
31 个因 A 实现缺失而前置失败；业务断言未到达。无自定义 marker、
skip、XFAIL、importorskip、替代 A 的占位业务类或远端调用。

## 1. A-local 拟议 API（测试用精确形状，不是共享合同）

延迟查找 `papertrace.library.service.CorpusService`；逐级 `find_spec` 明确断言
缺模块，再查类。只把“缺模块/类”报告为 IMPLEMENTATION_MISSING，其他导入异常
正常暴露，不吞错。没有 A 实现时可正常收集，行为测试前置 FAIL，业务断言
ASSERTIONS_NOT_REACHED。若环境导致 collection/import ERROR，仍不是行为 RED。

### 构造

```python
CorpusService(
    storage_root: Path,
    allowed_root: Path,
    selected_files: tuple[Path, ...],
    ingest: callable,                 # FakeIngest(request_dict) -> receipt_dict | None
    policy_ref: str,                  # 本测试显式传入 "offline-test"，非产品默认值
    max_bytes: int = 20 * 1024 * 1024,
    fault_hook: callable | None = None,
)
```

allowed_root 为受控来源根，selected_files 是明确授权选择的精确文件清单，
不自动扫描根。构造器可保存清单，但实际导入必须服务层重新校验词法穿越、
解析路径和 symlink 链。测试要求危险路径在 `import_files` 抛拒绝，不在构造
时读取危险源；构造不摄取，支持从 current 加载现存库且不重放 ingest。
默认 max_bytes=20 MiB 是原 Plan 待确认值，不冻结产品限制。

### 方法及返回值

| 调用 | 精确输入 / 返回 |
|---|---|
| `import_files(paths, replacements=None)` | Path 序列；可选 `{Path: document_id}` 明确换版；返回 batch 字典 |
| `retry_failed(document_ids)` | ID 序列；仅失败项追加尝试；返回 batch；ready 请求抛 `ValueError("NOT_FAILED")` |
| `current_snapshot()` | 返回真实 `CorpusSnapshot` |
| `attempts(document_id)` | 有序 list[dict]；每条至少包含 item 同名字段，失败/ready 追加，历史不原地修改 |
| `read_source(*, snapshot_id, document_id, version_sha256)` | 精确成员+源完整性校验后返回托管 bytes；不返回外部源路径 |
| `freshness()` | A-local `(snapshot_id: str, corpus_revision: int)` |
| `remove(document_ids)` | 只更新当前成员，保留历史/字节，返回真实 snapshot |
| `restore(document_ids)` | 恢复已 ready 的历史成员，不重新 ingest，返回真实 snapshot |

batch 是 `{"items": list[item], "snapshot": CorpusSnapshot, "complete": bool}`。
items 按本次请求顺序，每个 item 为字典，至少有：
`source_name: str`（安全 basename）、`document_id: str`、`version_sha256: str`、
`status: "ready"|"failed"`、`stage: str`、`reason_code: str|None`。
ready SHA 为真实托管源字节 SHA；失败记录也保留已读源的实际 SHA（有效源情况下）。
重复输入返回同样 items、同一快照身份，不添加尝试或摄取调用；同批部分成功
complete=false，成功的三项只投影三个 ready。成功 retry 后返回新当前快照。
items 不要求与 snapshot 的排序相同，后者遵守共享模型规范排序。

安全越权抛 `ValueError` 包含 `SOURCE_NOT_AUTHORIZED`，零摄取且不创建 current。
选中但缺失/空/不支持/超限返回 failed item，原因分别为
`SOURCE_MISSING / EMPTY_SOURCE / UNSUPPORTED_TYPE / SOURCE_TOO_LARGE`。
读托管缺失/损坏抛含 `SOURCE_INTEGRITY` 的 ValueError；成员不符抛含
`SNAPSHOT_MEMBERSHIP` 的 ValueError。无法持久化抛含 `PERSISTENCE_FAILED`
的 ValueError，不假称已保存新失败证据。公开异常/记录不含绝对来源路径或原始异常。

### 本地存储可观测约定（仅 A 内部测试提案）

- `storage_root/sources/<version_sha256>`：真实托管原字节；read 必须重新核验。
- `storage_root/snapshots/<snapshot_id>.json`：真实共享模型 JSON、不可覆写。
- `storage_root/manifests/`：版本化记录；已存在的文件不可覆写。
- `storage_root/current`：最后原子替换的小指针。
- `fault_hook(stage: str)`：在 `copy_source`、`write_manifest`、`replace_current`
  操作生效前调用；测试闭包仅在指定阶段抛 OSError，不模拟磁盘成功。
  中断后 current 和内存当前投影不前移；重启读取旧指针，不摄取/挑最新暂存。

不引入额外未定义生产类型，方法返回只用 Python 基本类型和现有共享模型。
存储布局/注入钩子也是 A-local 提案，不赋予 B/C/D/E 直接读取 A 磁盘的权力。

## 2. Fake 端口与共享模型分离

**PROPOSED_INTEGRATION**：FakeIngest 只替外部摄取调用，其形状待 A/B owner 确认。
调用 request dict 必含：

```text
document_id: str
version_sha256: str
source_name: str (safe basename)
source_bytes: bytes (actual controlled bytes)
metadata: dict                       # 本测试未传人工元数据，预期请求值为 {}
policy_ref: str                      # 来自构造注入，本测试显式值为 "offline-test"
```

make_service 构造 CorpusService 时显式传入 policy_ref="offline-test"，
请求须保留这个注入值；这不是产品默认值，不要求业务实现硬编码测试策略。
metadata 空字典是当前未传人工元数据的测试输入，不代表实际产品政策。
这些都是 A-local 测试提案，不冻结 B 接口，也不变更共享配置。
Fake 保存 deepcopy 实际请求到 calls（可计算次数），按安全文件名脚本依次返回。
默认 delta 首次 parse_failed，其余 ready；脚本支持 timeout、exception、missing、
wrong_id、wrong_version、unknown_status。返回字典：document_id、version_sha256、
status、stage、reason_code、representation_ref。正常表示引用为
`fake:synthetic-representation`；parse_failed 为 failed/parse/PARSE_FAILED。
缺失/不匹配/未知状态必须映射 INVALID_RECEIPT；timeout 为 INGEST_TIMEOUT，
exception 为 INGEST_ERROR，无自动重试。注入异常中的 synthetic-private 等
合成哨兵不能出现在公开 batch/attempts 中。

Fake 不计算或伪造 A 的 ID、SHA、快照、托管磁盘、历史、current 或业务结果。
实际请求字节与临时源逐字节比对，实际 SHA256 用 hashlib 独立校验；
共享模型直接导入真实 `DocumentVersion`/`CorpusSnapshot`，不手写快照哈希算法。
`complete`、attempts、revision 只存在 A-local，真实 snapshot 拒绝 extra。
PDF 自检验证指定 634 字节、SHA、xref 451、stream 长度 91，不冒充真实解析。

## 3. 测试名 → FR / INV 映射与具体断言

下列名称均指 `test/offline/test_library.py` 的实际函数。PI 表示
**PROPOSED_INTEGRATION**，是测试中的待确认假设，不是冻结共享 B API。

| 测试名（`test_` 前缀省略） | nodes | 映射 | 实质断言 / 集成标识 |
|---|---:|---|---|
| synthetic_pdf_integrity | 1 | QA-01 | fixture SHA/长度/stream/xref，仅基础 |
| real_snapshot_contract_rejects_batch_complete | 1 | QA-01, INV-02 | 实字节 DocumentVersion、真实 roundtrip、complete extra 拒绝，仅基础 |
| four_inputs_partial_ready_snapshot_and_real_requests | 1 | FR-A-01, INV-02 | 4结果/4真实请求、3ready、三成员、SHA/ID/字节，PI 回执/部分库 |
| duplicate_batch_reuses_success_and_does_not_retry_failure | 1 | FR-A-01, INV-05 | 总调用仍4、items/历史不变，PI 重复/失败策略 |
| explicit_retry_only_failed_appends_attempt | 1 | FR-A-01, INV-05 | 新增1、旧失败保留、新ready、四成员，PI retry |
| ready_cannot_be_retried_as_failed | 1 | FR-A-01 | NOT_FAILED、无新调用、快照不变 |
| same_path_changed_bytes_keeps_id_changes_version | 1 | FR-A-02, INV-02/05 | 明确换版保留ID、新SHA/快照、两次调用 |
| same_basename_other_selected_source_does_not_overwrite | 1 | FR-A-01, INV-02 | 同名第二来源不同ID、两成员、历史仍可读 |
| failed_replacement_excludes_old_current_but_keeps_history | 1 | FR-A-02, INV-05 | 新failed/current空/旧源旧尝试保留，PI 失败换版 |
| old_snapshot_disk_bytes_and_source_survive_external_mutation | 1 | FR-A-02, INV-05 | 实际旧JSON字节不变、真实模型校验、历史源不回写 |
| managed_source_missing_or_corrupted_read_refuses | 2 | INV-02/06 | 实际unlink/写坏托管，read拒绝 |
| selected_legal_absolute_path_is_accepted | 1 | FR-A-01, INV-06 | 合法selected绝对路径ready、源可读 |
| direct_service_path_authorization_refuses_unsafe_sources | 5 | FR-A-01, INV-06, SEC-01 | 根内未选中/越根/穿越/文件link/目录link均拒绝，无调用/current，sentinel不变 |
| selected_invalid_file_never_reaches_ingest | 4 | FR-A-01 | 空/类型/超限/缺失独立拒绝，零调用 |
| invalid_receipt_cannot_become_ready | 4 | FR-A-01, INV-02 | 缺失/错ID/错SHA/未知状态失败，邻项成功，PI 回执 |
| ingest_exception_isolated_sanitized_and_not_retried | 2 | FR-A-01, SEC-01 | 超时/异常原因映射、隔离、脱敏、恰2调用，PI 异常策略 |
| persistence_interruption_does_not_advance_or_overwrite | 3 | FR-A-02, INV-05 | 三阶段中断、真实current/旧文件/旧尝试不变、重启无摄取 |
| read_rejects_document_or_version_not_in_snapshot | 1 | INV-02/06 | 后加入文献/错误version在旧snapshot下均拒绝 |
| freshness_revision_detects_aba_without_changing_shared_snapshot | 1 | FR-A-02, INV-02 | 移除恢复snapshot ID复原但revision递增，不改共享模型，PI freshness |

COST-01 是所有用例的运行边界：无产品模型/API 调用；A 用例不能单独证明全项目
成本、SEC-01、QA-01 验收。未经执行不宣称任何上述行为成立。

## 4. 路径授权正负例与限制

正例：tmp_path 内受控根中明确选择的合法绝对路径；不能一概拒绝 absolute。
负例均直接调用服务，不靠 UI：根内未选择的合法 TXT；明确选择但根外绝对路径；
词法含 `..` 的路径；已选择但指向根外的文件 symlink；目录链 symlink 指向根外。
负例断言 Fake 无请求、current 不存在、外部合成 sentinel 字节不变。
测试不是 OS sandbox，也不证明没有任何瞬时读取系统调用；不新增身份服务、
全根扫描、真实论文目录或凭据访问。所有动态文件只在监督隔离测试的 tmp_path。

## 5. 待团队确认事项（集成确认前暂停相应连接）

| 项目 | owner / 状态 | 本测试假设，非对外承诺 |
|---|---|---|
| A→B request/receipt | A/B；待确认 | dict可调用端口、实际身份/阶段/表示引用、不可信回执拒绝 |
| 部分库 | A/B，发布相关D；待确认 | ready-only snapshot，complete仅批次 |
| 失败换版current | A/B，发布相关D；待确认 | 旧版从current排除、历史仍可读 |
| retry/重复与异常映射 | A/B；待确认 | 显式失败重试，不自动retry，历史追加 |
| freshness/ABA | A/B/D及相关C/E；待确认 | A-local revision，shared snapshot不扩字段 |
| 文件上限 | A；待确认 | 可配置，原初值20 MiB，小阈值测试不变更依赖 |
| A-local方法、布局及fault hook | A；测试提案待审 | 无额外生产类型，不冻结共享端口 |

普通 A Fake 测试准备无需等 B 实现。若将来需要变更共享契约、权限或安全边界，
停止并请求窄授权及适用ADR/受影响owner人审；不在本轮自填编号或代审批。

## 6. 验证记录与证据解释

**显式 policy_ref 修正后的最终隔离验证已由监督端完成。**以下结果均归属监督端
实际执行并在当前聊天提供，不是本助手执行 Shell 或自行读取外部日志所得。
本会话只 native read/patch，未运行验证命令、查询 Git/远端或 commit/push/PR/merge。
监督端报告：在全英文 scratch 运行路径、相同 main 基线的三个无凭据隔离 checkout
中执行最终六项检查，验证时的8文件与工作区逐字节一致。
最终验证对应 test_library.py SHA256：
`e056958793f7661f52075f8b0baffe2628ed36a50b3d47fe407e7c04cf0e3037`。
本次仅更新结果文档，不改测试或四个 fixture 字节。

原获准命令如下；无凭据 runner 使用的插件参数及每次实际 argv 由监督端外部
执行记录提供，此处不猜写或将原命令冒充完整实际 argv：

```sh
.venv/bin/python -m pytest -c papertrace.pytest.ini test/offline/test_library.py
.venv/bin/python -m pytest -c papertrace.pytest.ini test/offline
.venv/bin/python -m ruff check --config papertrace.ruff.toml src/papertrace test/offline scripts
.venv/bin/python -m mypy --config-file mypy.ini src/papertrace
.venv/bin/python scripts/gates.py --gate schema
.venv/bin/python scripts/opencode_support.py
```

| 检查 | validation-final：监督端实际结果 |
|---|---|
| 单模块 pytest | 33 collected/selected，2 passed / 31 failed，exit=1；collection_errors=[]、configuration_errors=[]，skip/xfail/xpass均0 |
| 全部 offline | 365 collected/selected，334 passed / 31 failed，exit=1；collection/config errors=[]，skip/xfail/xpass均0；31个失败节点均在test_library.py |
| Ruff | exit=0，PASS |
| mypy src/papertrace | exit=0，PASS；仅既有src，不覆盖不存在的A实现 |
| schema gate | exit=0，PASS |
| 默认静态 preflight | exit=0，PASS，model_started=false；未运行--verify-runtime |
| 监督端另用系统sips渲染PDF为PNG | exit=0；PDF仍634字节，SHA256为970046dfe2ba98dcfde18be259a7d72fc2554c9b92fd8cb1b62d15c75b966ed6，与原生patch payload逐字节相同；仅证明该系统可打开，不是PaperQA解析测试 |
| 产品真实模型/embedding/OCR/metadata | NOT_RUN；预算0 |
| 独立学生 GitHub 测试commit Approve | 尚无证据，源码实现禁止 |

最终全offline中既有332项均通过，加上2个新基础自检共334通过；不能称全套PASS，
更不能称完整上游回归PASS。31个A行为nodes仍全部停在 service_class 的
`IMPLEMENTATION_MISSING: papertrace.library; ASSERTIONS_NOT_REACHED` 前置断言，
这是 precondition FAIL，不是已观察到的业务RED，也没有A业务通过证明。
基础2项PASS仅证明fixture/真实共享契约自检。

初始失败经过必须保留：初版测试SHA256为
`d2f91e711b9f35d4c19f63d3a29a8b195b26b4d4fa79afcf0afc5a48c173f8bd`；
初版单模块33项为2 passed/31 failed，exit=1，无collection/configuration error或skip/XFAIL。
validation-01第一遍全suite为332 passed/33 failed，exit=1，其中31项A缺实现，
另外2个既有OpenCode sandbox loopback测试因非ASCII临时路径下EPERM mkdir log失败。
未改共享测试或权限，仅将HOME/TMP和报告目录换为ASCII，validation-02-ascii
成为334 passed/31 failed，exit=1；显式policy_ref修正后当前源码的validation-final
再次为334 passed/31 failed。旧失败真实发生，日志不会删除，不伪装从未发生。

监督端说明完整日志在仓库外 `test-preparation evidence/validation-final`，最终审核ZIP
将附stdout/stderr、执行JSON、pytest-report及原生会话；本助手未读取该位置，也未
新建报告路径或共享AI日志。这些静态检查不证明A行为实现或完整上游回归通过。
若发生语法错误、真实共享模型用法错误或环境collection错误，单独报告为测试自身/
环境问题，不能冒充业务RED；仅在授权8文件内修正测试自身错误并保留日志。
未来有实现且业务断言真正到达时，才可报告观察到的行为RED/PASS。
禁止吞错误、动态移除、改失败断言求绿或跳过用例。

## 7. 审批与后续停止点

监督端最终验证已完成，现等待测试提案发布后由另一未参与实现学生审核最新测试commit。
本轮不填写真人Approve、不假填PR/ADR，
不改共享AI-use log/review memo，不写成员姓名邮箱。
另一位未参与测试实现的学生须通过GitHub批准具体测试commit；proposal PR可保持
open且RED，不为审批合并。实现须从该测试head分支创建，PR描述届时含真实
`Test approval PR: #N`。权限/会话/角色不证明这项实际批准。

## 后续测试覆盖建议（不阻塞首次测试提案）

- 正常重启后，核验 ready 版本、历史快照、attempts 与托管源的持久性，且不重复摄取。
- current/manifest 丢失、损坏或 schema/hash 错误时，验证拒绝错误恢复，不扫描最新记录、
  静默回退或伪装 ready。

以上仅为后续覆盖建议，当前不新增测试、不实现恢复逻辑，也不是新增教师门禁。
