# PaperTrace 模块 B 开发计划 v2.1（已获本人审批）

> 负责人：李亚飞  
> 模块：B｜证据检索、PaperQA2 适配与中立生成端口  
> 日期：2026-11-17  
> 状态：2026-11-18 已获模块负责人本人批准 B0/B1 范围与命令；B2 仍须测试 commit 的独立 GitHub Approve

## 1. 目标、范围与阶段

模块 B 接收固定 `CorpusSnapshot`、研究问题及获批配置，经唯一 PaperQA2 适配边界取得候选证据，转换为现有共享契约 `EvidenceRecord`；同时向 D 提供中立生成端口，返回实际发送集合、raw 输出、引用映射和调用观测。B 不决定证据是否被接受，也不决定答案是否发布。

本轮分三阶段：

1. **阶段 B0：计划批准后的离线基线复现。**读取获准上游文件，在隔离 runtime 中复现仓库已有 `Docs.aadd → Docs.aget_evidence → Docs.aquery` smoke；不写 `src/`，不使用真实模型、真实论文或 API Key。
2. **阶段 B1：测试准备。**只创建 B 的设计记录、synthetic fixtures、fake adapter 和 `test/offline/test_retrieval.py`，形成预期 RED 的测试提案 commit；仍不得写任何 `src/`。
3. **阶段 B2：业务实现。**只有未参与测试实现的组员在 GitHub 对 B1 的精确测试 commit 真实 Approve 后，才实现 `src/papertrace/retrieval/`。

不在本轮范围：真实 LLM/provider 调用、真实论文、PDF/OCR 质量、模型语义质量评估、Streamlit 总入口、多用户/云部署、共享 contract 修改和上游 PaperQA2 修复。

## 2. 需求、不变量与验收标准

| ID | B 必须实现/验证 | 可测量标准 |
|---|---|---|
| `FR-B-01`, `INV-02` | 候选绑定 snapshot/document/version、原文和可回查 locator；摘要/相关度仅供参考 | 合格候选来源字段比例 `1.0`；身份/版本不匹配 `0`；每条记录通过 `EvidenceRecord` 现有校验 |
| `FR-B-02`, `INV-08` | 区分空集、超时、解析错误和上游失败；拒绝不可信 pickle/index；重试有界且不换模型 | 未报告失败 `0`；四类状态可区分；默认 `max_retries=0`（仍允许一次初始调用） |
| `FR-D-03`, `INV-01/03/04/07` | 只按 D 给出的获准证据/配置执行；返回 serializer 后实际 `sent`、raw 输出和无歧义 alias 映射 | `sent ⊆ approved`；空 approved 时模型工厂、SDK、HTTP、adapter 调用均为 `0`；输入上限 12000、9000 触发上游策略提示、输出上限 2000 |
| `COST-01`, `SEC-01` | 默认离线、无真实模型/凭据/未许可数据 | B0/B1 模型请求 `0`、外部连接 `0`、凭据读取 `0`、费用 `$0` |
| `QA-01` | 不修改共享模型来迁就实现；保持团队契约回归 | `test/offline/test_contracts.py` 与团队离线回归真实通过，未运行则记 `NOT_RUN` |
| `GOV-01`–`GOV-04` | 计划、测试批准、实现、验证和 AI 使用记录真实留存 | 未批准实现合并 `0`；审批绑定精确 commit；安全/共享变更另走 ADR |

`EMPTY_RESULT`、`TIMEOUT`、`PARSE_ERROR`、`UPSTREAM_ERROR` 等仅是 B 私有结果/原因码，不新增到共享 contracts。`EvidenceRecord` 不增加 `accepted/status`；`Context.id` 和 dockey 不作为团队证据身份。

## 3. 数据流与职责边界

### 3.1 检索

1. 输入为 A 的不可变 snapshot、非空问题和获准检索配置。
2. B 经受控源文本端口核对 `document_id/version_sha256`，不把 `source_name` 当文件路径。
3. `gateway.py` 是 B 对外公共接口；PaperQA2 调用只在 B 内部发生，固定使用 `Docs.aadd` 与 `Docs.aget_evidence`。
4. B 将上游 dockey/Context 映射回 snapshot/document/version，构造带完整 1-based 页范围或行范围、chunk/parser 名称和版本的 `SourceLocator`。
5. 由现有 `EvidenceRecord` 共享算法生成 `evidence_id`；相同 ID 去重，身份冲突或 locator 无法回查时整次 fail closed，不猜页码/行号。
6. 输出明确区分成功、空集和失败；失败不得返回伪造证据。

### 3.2 D→B 中立生成端口

1. D 提供固定 snapshot、问题、当前获准 evidence/contexts、预算策略和审核版本标识。
2. 空 approved、空 sent、`sent ⊄ approved`、版本不符或预算越界时，在模型工厂/SDK/HTTP 前拒绝。
3. 每次新建只含 D 选定 contexts 的 session；不复用旧 `PQASession`。
4. 显式关闭空 contexts 自动补证、`pre`、`post` 和自主 Agent；仅执行 `Docs.aquery`。
5. 返回 serializer 后实际 sent ID、raw 输出、alias→evidence 映射及未知引用；未知或歧义引用不得静默删除。
6. B 不创建 `ReviewDecision`、不写 C 的人工审核账本、不产生 `ReleaseDecision`、不发布答案。

### 3.3 UI 边界

`src/papertrace/retrieval/view.py` 只提供 B 自己的状态投影/显示数据，不复制授权逻辑。最终薄 Streamlit 总入口 `src/papertrace/app.py` 属后续单独的集成计划；本计划不是取消项目 UI。

## 4. 失败与重试策略

| 情况 | B 的处理 | 重试 |
|---|---|---|
| 空结果 | 返回私有 `EMPTY_RESULT`，不伪造成错误或证据 | 否 |
| 超时/获批瞬态上游错误 | 记录 stage、attempt、elapsed、固定 provider/model | 仅按获批上限；默认零重试 |
| 解析错误、身份/版本/locator 错误 | 明确失败并 fail closed | 否 |
| 不可信 pickle/index | 加载前拒绝 | 否 |
| 空 approved、sent 越界、预算越界 | 调用前拒绝，所有出站计数为零 | 否 |
| 未知引用 | 保留 raw 与 unknown key 交给 D | 否 |
| 歧义 alias | 明确失败，不任意映射 | 否 |

不自动扩大检索、不自动换 provider/model、不因失败生成“解释性”模型调用。每次尝试真实入账，已发生费用不能记录为零。

## 5. 测试计划

### 正向

- Context→`EvidenceRecord` 保留 snapshot/document/version/excerpt/locator，ID 重算一致。
- 页范围和行范围均按 1-based inclusive 校验。
- 改变 advisory summary/score/upstream context ID 不改变证据身份。
- 空结果与执行失败分开。
- fake adapter 记录真实输入、调用顺序和尝试，不返回固定 `"OK"`。
- 生成端口记录 serializer 后 actual sent、raw 输出和正确 alias 映射。
- B view 只投影状态，不产生 accepted/released。

### 负向

- 跨 snapshot、version hash 不符、locator 缺端点/反向/不可回查均拒绝。
- 不可信索引在加载前拒绝；B 新增代码不得加载 pickle/joblib/torch/NumPy pickle。
- 空集、超时、解析错误、上游失败分别注入并断言不同结果。
- 重试不超上限且 provider/model 不变。
- 空 approved、sent 越界、预算越界时 factory/SDK/HTTP/adapter 计数全部为零。
- session 必须新建；自动补证、pre/post 和自主 Agent 均关闭。
- 未知引用保留；重复/歧义 alias 不任意映射。
- 模型高分、恶意 excerpt 或伪 human 字段不能产生审核决定。
- fixtures 不含真实论文、密钥、成员身份或个人绝对路径。
- `src/papertrace` 中只有 `retrieval/` 可新增 `import paperqa`。

### 回归

- B 模块测试、完整 `test/offline`、Ruff、mypy、schema gate、frozen 检查。
- 不以 skip/xfail、删除断言或修改共享 fixture 迁就实现。
- 未执行的真实上游、live 或语义测试必须标记 `NOT_RUN/BLOCKED`。

## 6. 精确路径范围

以下均为仓库相对路径。

### 只读

- `AGENTS.md`、`Prompt.md`、`TEAM_START_HERE.md`
- `docs/team/module-B.md`、`docs/team/integration-contract.md`
- `docs/req/requirements.yaml`、`src/papertrace/contracts.py`
- `docs/architecture/permission-model.md`
- `docs/tooling/paperqa-runtime.md`、`docs/licenses/license-review.md`、`test/live/README.md`
- `requirements-runtime.in`、`requirements-runtime.lock`
- `src/paperqa/docs.py`、`src/paperqa/types.py`、`src/paperqa/settings.py`、`src/paperqa/core.py`
- `packages/paper-qa-pypdf/src/paperqa_pypdf/reader.py`（仅核实 parser/locator）

### B0/B1 可写；不得写任何 `src/`

- `docs/team/designs/module-B/plan-v2.1.md`
- `docs/team/designs/module-B/test-design-v2.1.md`
- `test/offline/test_retrieval.py`
- `test/fixtures/retrieval/` 下本计划列明的 synthetic 文件和 fake adapter
- `artifacts/verification/` 下本次真实运行报告

### 测试 commit 获非实现者真实批准后，B2 才可写

- `src/papertrace/retrieval/__init__.py`
- `src/papertrace/retrieval/gateway.py`：B→D 唯一公共端口和公开结果类型
- `src/papertrace/retrieval/service.py`：检索、映射、错误和尝试记录的内部实现
- `src/papertrace/retrieval/view.py`：B 自己的状态投影

若确需增加其他 B 内部源码文件，必须先更新精确计划并重新审查；D 只依赖 `gateway.py/service.py` 的获批公开部分。

### 禁止修改

- `src/paperqa/`、`packages/`、上游原 `tests/`
- `src/papertrace/contracts.py`、共享 fixtures、其他成员模块
- `pyproject.toml`、`uv.lock`、`requirements-runtime.*`、CI/工作流
- `Prompt.md`、`.opencode/rules.md`、`.agent/rules.md`、共享需求和架构规则
- 凭据、`.env`、个人目录、未许可论文内容

## 7. 获准命令、依赖和网络边界

### 7.1 B 模块日常离线命令

```sh
.venv/bin/python -m pytest -c papertrace.pytest.ini test/offline/test_retrieval.py
.venv/bin/python -m pytest -c papertrace.pytest.ini test/offline
.venv/bin/python -m ruff check --config papertrace.ruff.toml src/papertrace test/offline scripts
.venv/bin/python -m mypy --config-file mypy.ini src/papertrace
.venv/bin/python scripts/gates.py --gate schema
```

### 7.2 B0 最小 PaperQA2 离线 smoke

按 `docs/tooling/paperqa-runtime.md` 原样复现，不重算/修改锁文件：

```sh
RUNTIME=.local/unblock/runtime
mkdir -p "$RUNTIME/home" "$RUNTIME/tmp" "$RUNTIME/cache" artifacts/verification
uv venv "$RUNTIME/.venv" --python 3.14
uv pip sync --python "$RUNTIME/.venv/bin/python" requirements-runtime.lock

PYTHONDONTWRITEBYTECODE=1 "$RUNTIME/.venv/bin/python" -m pytest \
  -c papertrace.pytest.ini test/integration/test_paperqa_smoke.py -q

/usr/bin/env -i \
  PATH="$PWD/$RUNTIME/.venv/bin:/usr/bin:/bin" \
  HOME="$PWD/$RUNTIME/home" TMPDIR="$PWD/$RUNTIME/tmp" \
  XDG_CACHE_HOME="$PWD/$RUNTIME/cache" PYTHONNOUSERSITE=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  "$PWD/$RUNTIME/.venv/bin/python" scripts/paperqa_smoke.py --json \
  --report artifacts/verification/module-B-paperqa-smoke.json
```

`uv pip sync` 只允许访问取得锁定包所需的软件包源，遇 hash/版本不符立即停止；不得访问模型/provider API。smoke 使用 synthetic `.txt`、本地 deterministic fake embedding/summary/answer，并断言外部连接为零；不读取学校 LiteLLM Key。输出只证明真实 PaperQA2 本地 API 接线，不证明模型质量或正式 B adapter 已完成。

## 8. 执行与审批顺序

1. 学生本人批准本计划 v2.1、7.1 离线命令及是否批准 7.2 的有界依赖下载/离线 smoke。
2. 复现 B0 smoke，记录真实版本、命令、退出码和报告；失败如实保留，不改锁求绿。
3. 用 `papertrace-build-B` 仅准备 B1 测试/fixtures/设计，确认无 `src/` diff，运行预期 RED。
4. 提交测试提案 PR，绑定精确 commit SHA；由未参与该测试实现的组员在 GitHub 真实 Approve。
5. 从获批测试 head 创建实现分支，完成四个获准 B2 源码文件。
6. 运行模块测试、完整离线回归、Ruff、mypy、schema/frozen 检查，记录真实结果。
7. 创建实现 PR，正文写入精确行 `Test approval PR: #N`，等待独立 reviewer；作者/共同实现者不得自审。

## 9. 停止条件与恢复

出现任一情况立即停止：计划未获本人批准；测试 commit 未获合格组员批准；需要修改共享 contracts、上游、依赖锁、CI 或其他模块；A 无法提供受控源文本；无法生成真实 locator；需真实模型/网络数据外发；测试只能靠 skip/放宽断言通过；分支/审批对象无法绑定精确 commit。

误写 `src/` 或冻结区时停止并恢复，保留事故记录。真实 PaperQA2 环境失败标 `BLOCKED`，不得用 fake 冒充。发现计划测试遗漏时重新提出测试变更并再次批准，不先改实现或测试求绿。

## 10. 证据与 OpenCode 会话

- 正式计划第一次会话 `ses_e169b4591ffe6ljZYYtBqSe34K`：读取规定文件后，学校 LiteLLM 因 `reasoning_text` 多轮兼容错误返回 400；未生成最终计划、未编辑文件。
- 学生明确要求进行一次受控重试；不得自动换模型或无限重试。
- 成功会话 `ses_e169668c3ffe1OL1RT57k4bHVu`：将规定文件作为附件一次发送，禁止工具调用，在首轮输出正式计划；未编辑文件。
- 两次原始会话、失败原因和人工干预应保存在 `transcripts/`；最终数量/命名按教师要求确认，不事后伪造对话。
- 计划、测试设计、测试/实现 PR、精确审批 commit、验证输出及 `docs/ai-use-log.yaml` 均按真实状态更新。
- transcript/日志不得含 API Key、个人绝对路径、未许可论文或模型私有推理。

## 11. 当前真实状态（2026-11-19 更新）

- 学生本人已于 2026-11-18 批准本计划 B0/B1 范围及第 7 节命令，原文与生效边界见 `approval-v2.1.md`；B2 仍须另一位未参与测试实现的学生批准精确测试 commit。
- B0 在 2026-11-19 首次复跑时因缺少 `paperqa.version` 得到 `1 failed`；用户随后批准独立 Git/构建恢复。恢复后使用原样 smoke 集成测试得到 `1 passed in 6.77s`，独立脚本报告 `status=PASS`、`network_connect_attempts=0`。旧失败记录保留；本次只证明真实本地 PaperQA2 API 接线与模拟模型 prompt 边界。
- 当前工作目录为无 `.git` 的 ZIP 副本，缺少由 `setuptools_scm` 生成且未纳入版本控制的 `src/paperqa/version.py`；现有 runtime 锁不含 `setuptools_scm`。不得伪造版本或修改冻结源码来消除错误。
- 本次实际失败与恢复提案见 `artifacts/verification/module-B-b0-blocked-2026-11-19.md`；机器可读状态见同名 `.json`。
- 已执行的恢复及 PR #5 技术复核见 `artifacts/verification/module-B-recovery-and-pr5-review-2026-11-19.md`；本次真实 smoke 结果为 `module-B-paperqa-smoke-recovered-2026-11-19.json`。版本文件只在隔离 Git 副本按原构建配置生成，没有更改受跟踪上游或项目锁。
- B1 测试设计已整理至 `test-design-v2.1.md`，属于 Codex 辅助的设计草稿；OpenCode 测试生成尚未开始，测试文件、测试 PR 与测试审批均未完成。
- B2 源码未创建；真实产品模型/检索质量评估 `NOT_RUN`。本地计划和批准记录尚未上传远端。
- 已核对任务板 A/B 文献身份、版本、受控读取和摄取回执，以及 D/B 生成端口；B 侧交接意见见 `test-design-v2.1.md` 第 7/8 节。对方 owner 的确认及联调尚未发生；不以设计意见冒称集成完成。
- 用户本轮明确要求先完成审核与接口交接，暂不调用开发助手模型；B1 测试生成继续暂停。

本节只修正进度记录，不扩大第 6/7 节权限、不新增依赖、不批准恢复提案或 B2 实现；模型文字、文件存在或角色权限本身均不构成学生审批。

## 12. 2026-11-21 PR #12 Review 修复检查点

- PR #9 的精确测试 head `7833527e2fd069fe61c0c56900949de03d6e3e8f`
  曾获独立批准；PR #12 的实现 head
  `ea1bfed328528d11578980a757c80bef1c7a84b0` 随后被正式
  `REQUEST_CHANGES`，不得合并。
- Review 指出 PR #12 从仍开放的 #9 分支派生，导致测试提案和实现同时进入
  `main` diff。修复后的实现分支必须从当时最新 `main` 创建，只携带四个 B2 源码
  文件及适当 B2 披露；PR #9 继续开放、未合并。
- Review 还指出 page-only 摘录校验及真实 PaperQA2 桥接测试遗漏。本轮先仅更新
  B1 测试提案，不写 `src/`：新增伪造 page-only 摘录负测，以及要求具体
  `PaperQA2Adapter` 调用 `Docs.aadd`、`Docs.aget_evidence`、`Docs.aquery` 的合成
  离线测试。
- 旧批准只绑定 `7833527`，不覆盖新增测试。新增测试必须在 PR #9 对新的精确 head
  重新获得合格非作者 Approve，之后才能修改实现并请求 PR #12 复审。
