# Module D slice 1: delivery repair supplement (2026-11-21)

## Current delivery scope and provenance

The student explicitly authorized the previously reviewed local delivery preparation,
local commits and offline verification in this chat on 2026-11-21 HKT. Publishing,
creating a pull request, merging, changing gates/permissions, and product-model calls
are outside this authorization. This is Codex-assisted Git orchestration and a
byte-for-byte re-application, not a new OpenCode student implementation session.

- Approved test proposal: PR #3, head `29b2133829666c25b42688ae7e5b42ac6130cbd8`.
- The GitHub reviews API returned `537Lab` / `APPROVED` on this exact head at
  `2026-11-19T04:03:57Z`; this verifies the account/SHA/time, not an independently
  established real-world identity.
- Previous implementation: PR #6, head `c3817ae676eb7c7a0ee8790b42c04232c19212e6`.
  Its commits preceded the currently visible test approval. They remain historical;
  the delivery branch does not carry those implementation commits as ancestors.
- Base for this preparation: `6235c33d460b48d1ff11a10624d1bcd5919ea4f0`, including C #11.
- Branch: `codex/d-slice1-resubmit`, starting at the approved test head and merging
  the stated base. Commits use the actual current time, without rewritten dates.
- The five `src/papertrace/answer/` files are copied from the prior implementation.
  No adapter, generation path or new tests are introduced.
- The original 303-line approved design file and the three approved test/fixture
  files stay at their exact approved blobs. Its later 93 lines are archived below
  verbatim, preserving the observation dates and limitations stated at that time.
- The shared log preserves all base entries, both prior D entries, and a distinct
  factual disclosure for this local delivery repair.

## Verification of this preparation

Verified on 2026-11-21 HKT using the existing initialized CPython 3.14.8 environment
(pytest 9.2.0); no dependencies or project configuration were changed. `python`
below denotes that existing verification interpreter. Commands ran from the isolated
worktree. The direct mypy run used a temporary cache; pytest's cache provider was
disabled. The full team run was granted the process-tree access required by its
subprocess-cleanup tests and retained the repository's socket-disabled configuration.

| Check | Actual result |
| --- | --- |
| `python -m pytest -c papertrace.pytest.ini -p no:cacheprovider test/offline/test_answer.py` | exit 0; 33 passed |
| `python -m pytest -c papertrace.pytest.ini -p no:cacheprovider test/offline` | exit 0; 387 passed, 2 skipped; both skips are OpenCode-executable-unavailable cases |
| `python -m ruff check --no-cache --config papertrace.ruff.toml src/papertrace test/offline scripts` | exit 1; one I001 at `scripts/paperqa_smoke.py:37`; this file and its configuration are unchanged from base |
| `python -m mypy --config-file mypy.ini --cache-dir <temporary-cache> src/papertrace` | exit 0; no issues in 10 source files |
| `python scripts/gates.py --gate schema --base 6235c33d460b48d1ff11a10624d1bcd5919ea4f0` | exit 0; PASS |
| `python scripts/gates.py --gate ai-log --base 6235c33d460b48d1ff11a10624d1bcd5919ea4f0` | exit 0; PASS, three entries added relative to base (two historical D records and this repair disclosure) |
| `python scripts/gates.py --gate static --scope full --base 6235c33d460b48d1ff11a10624d1bcd5919ea4f0` | exit 1; lint FAIL; types, dependencies, frozen baseline, architecture, contract API, secret heuristic and permissions PASS |
| `python scripts/gates.py --gate test-approval --scope full --base 6235c33d460b48d1ff11a10624d1bcd5919ea4f0` | exit 2; BLOCKED, `missing-pr-number`; no new PR has been created |
| Source and approved-file comparison | Five source files byte-identical to `c3817ae`; all four PR #3 file blobs unchanged; base's 12 AI-use entries and both old D entries preserved, 15 unique entry IDs total |
| Real semantic evaluation | NOT_RUN; authorization and actual evidence remain absent |
| Full upstream/live regression and remote PR checks | NOT_RUN in this preparation; the team offline result does not substitute for these gates |

The two skipped runtime cases are not counted as validated behavior. Existing lint
failure is not waived. No new test or code changes were made in response to it.

## Outstanding review and acceptance conditions

Changes to `answer/model.py`, `errors.py`, `eligibility.py` and `service.py` trigger
safety review. An actually applicable ADR reference and a real independent review
on the new head remain required. ADR-001 is a candidate only; its proposed status
is not changed or represented as accepted.

The current gate can switch to its merged-test rule if GitHub automatically marks
PR #3 as merged after the implementation lands. C #7 demonstrated this sequence.
Maintainers must confirm the process and replay handling before merge; this local
preparation does not guarantee a passing post-merge replay and does not modify gates.

Real product semantic evaluation is not run without authorized provider/model,
data, budget and real evidence. C's successful check does not establish D's result.
C-to-D integration, generation and later freshness/release work remain separate.

## Historical additions preserved verbatim from PR #6

The following text is historical evidence, not a statement of current approval,
branch or CI status. In particular, old review-visibility and pending shared-log
observations are superseded by the current facts above and actual shared log.


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

## 19. CI 失败归因（2026-11-19）

| 检查 | PR #6 结果 | 归因 | 依据 |
|---|---|---|---|
| schema | PASS | — | — |
| static | FAIL | 既有：未修改的 scripts/paperqa_smoke.py:37 I001；其余 8 个子检查 PASS | 本 PR diff 不含 scripts/；明细来自 run 44283642138 |
| regression | FAIL | 既有：完整上游禁网失败/限时，live 未授权 | INITIALIZATION_STATUS.md 第 15、31 行 |
| test-approval | BLOCKED | 记录缺失：GitHub reviews totalCount=0，timeline 无 review 事件 | PR #3 API 查询 |
| ai-log | FAIL → 本提交修复 | 新引入缺项，已追加两条披露 | 本提交 |
| semantic | BLOCKED | 需团队确定评估口径与证据 | gate summary |

本表只用于归因，不构成豁免；既有 static 与 regression 失败仍阻断合并，需由对应共享文件 owner 解决。
