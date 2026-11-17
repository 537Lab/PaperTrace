# 模块 C｜追加式审核账本设计记录

本记录说明 `src/papertrace/review/` 的追加账本与只读视图，不替代任何真实审批记录；文中不虚构批准人。实现只依赖共享 `contracts.py` 中的 `CorpusSnapshot`、`EvidenceRecord`、`ReviewDecision`，不调用模型、网络或 PaperQA。

## 作用域

- 一个 `ReviewLedger` 绑定一个不可变 `CorpusSnapshot` 和调用者传入的 `ledger_root`。
- 每个 `(snapshot_id, question_id)` 对应根目录下唯一的 `*.jsonl` 文件，文件名为「snapshot 的 64 位十六进制 + `-` + question_id」。不创建子目录。
- 没有有效决定时不创建文件；任何被拒绝的命令也不创建或改动文件。
- 只接受候选人集合内、属于当前 snapshot 且 document/version 匹配的证据。scope 不符统一抛 `ReviewScopeError`。

## 追加事件

人类命令只有三种：`accept`、`exclude`、`reset`，分别写入 `accepted`、`excluded`、`pending`。`prepare_decision` 只做校验并返回意图对象，不落盘；`commit_decision` 才追加。

- `actor_kind` 固定为 `human`，`decided_at` 来自注入的 `clock()`，`revision` 由服务按当前事件数 + 1 填写，调用者不能指定。
- 每个有效决定恰好追加一行；旧行字节不变。写入时对文件加 `fcntl.flock` 排他锁，追加后 `flush` 并 `fsync`。
- 传入现成的 `ReviewDecision`（而非 `prepare_decision` 返回的意图）直接 `TypeError`，不写文件。
- 理由去空白后必须非空；空串、空格、换行/制表、全角空格均在准备阶段拒绝。

## 幂等、冲突与 no-op

- 相同 `command_id`、相同命令内容且 `expected_revision` 等于当前 revision：返回当前投影，不追加。
- 新命令但 `expected_revision` 与当前 revision 不符：抛 `ReviewRevisionConflict`，不写文件。
- 新命令但该证据最新状态已等于目标状态：抛 `ReviewNoop`，不写文件。
- 重置只追加 `pending`，不删除历史 accepted/excluded 事件。

## 行格式与 digest

每行是 UTF-8 canonical JSON（`ensure_ascii=False`、`sort_keys=True`、分隔符 `,` 与 `:`、禁止 NaN），至少包含 `command_id`、`decision`、`digest_after`；`decision` 为 `ReviewDecision.model_dump(mode="json")`。

digest 使用以下 payload 的 SHA-256：

- `schema_version = 1`
- `snapshot_id`、`question_id`
- `revision = 事件条数`
- `events` 按 `decision.revision` 排序，每项只含 `command_id` 与 `decision`

空账本 revision 为 0，digest 同样按上述 payload 计算。读取时逐行校验 revision 连续（从 1 开始）、snapshot/question/evidence scope、以及每行 `digest_after` 与截至该行重算的 digest 一致。损坏、半行、空行、重复 revision 或 digest 不符均抛 `ReviewLedgerCorrupted`，不修复文件。

## token 校验

`verify_current(question_id, revision, digest)` 仅在 revision 与 digest 都对应当前投影时通过。旧 revision 抛 `ReviewTokenStale`；revision 是当前值但 digest 不符抛 `ReviewDigestMismatch`。

## 只读比较与提示

- `comparison_view` 只读账本。要求至少两条不同 evidence，且来自至少两个不同 document，否则抛 `InsufficientIndependentSources`。每行展示 document/evidence 身份、标题、来源名、版本、原文、advisory 摘要、当前状态、理由、最近决定 revision 与完整 locator。
- 相似原文但 locator 不同仍是不同 evidence，不合并。
- `decision_prompt` 只读返回当前 `expected_revision` 和允许动作（`accept`、`exclude`、`reset`）。
- `submit_decision` 走与 `prepare_decision` + `commit_decision` 相同的 scope/revision/no-op 检查，仅追加一行。

## 边界

本模块不决定发布，不读写 A/B/D/E 业务文件，不从 UI 缓存、模型输出或导入文件获取 accepted 权威。`actor_kind="human"` 与匿名 `reviewer_ref` 只是 schema 形状，本机单人流程不声称身份认证或对抗本机管理员。
