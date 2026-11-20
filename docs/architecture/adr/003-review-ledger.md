# ADR-003：模块 C 追加式人工审核账本

- **状态：proposed-awaiting-human**。
- 决策范围：模块 C 用追加账本记录人对证据的接受、排除和重置。本条记录这个实现选择，不是对源码 PR 的第二次人工批准。
- 测试批准：GitHub PR #2，批准人 yafeili39-arch，批准的是测试提交 `3339b75a6b87e3463465bf4b6a896723e02ab4f2`。该批准不覆盖本文件，也不代替实现 PR 上的另一次 Approve。
- 设计记录：[review-ledger.md](../../team/designs/module-C/review-ledger.md)。

## 决定

1. 审核状态只追加到每个 `(snapshot_id, question_id)` 的 jsonl。重置追加 `pending`，不删除旧事件。
2. 调用者不能传入现成的 `ReviewDecision`。服务自己填写 `actor_kind=human`、`revision` 和 `decided_at`。
3. 比较视图只读。少于两个独立文献时不给出比较。
4. 损坏、半行、重复 revision 或 digest 不符时拒绝读取，不自动修复。
5. 本模块不调用模型，不改共享契约，不决定回答能否发布。

## 未决

实现 PR 仍需要另一位没有编写这些源码的同学，对那个 PR 的最新提交点 Approve。点完不要合并。
