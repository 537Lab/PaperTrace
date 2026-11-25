# B 侧固定评估 ID 与原始请求捕获测试提案

本地基线为 `4c6eca85f2e858fb56f9453104854e729e7c6356`，包含已获独立源码批准的 B→D #59 与 A→B #60。范围对应 FR-D-03、INV-01、INV-04 和 INV-07。评估组已确认固定集 ID 在组装前绑定，现有 Gate 4 保持原口径。

## 提议供 #53 对齐的 B 入口

评估侧先从可信固定集确定 `dataset_sha256`、`case_id`、问题、获准正文与绑定的运行时快照。B 的独立评估入口候选是在构建每次评估用例专用 `Gateway` 时，注入 `EvaluationCaseBinding` 和一个 `request_observer`。绑定包含 `dataset_sha256`、`case_id`、`snapshot_id`、`question`、`fixed_evidence` 字段及 `fixed_to_runtime` 字段。后两项分别为固定 ID 与原文、固定 ID 与规范 ID 的有序二元组。Gateway 继续经现有 `generate()` 接收 D 已授权的运行时对象。普通生产 Gateway 无需提供评估参数。

数据集可信版本、用例选择与运行授权由 evaluator 的预检负责。B 校验本次生成请求的快照、问题、获准证据、原文和一对一绑定。正常授权与裁剪使用规范 ID。裁剪后用固定 ID 组装最终出站请求，预算和模型入口的一致性检查都使用这份最终正文。观察器在一致性检查后、实际调用之前得到由 `(role, content)` 二元组组成的原始消息元组。观察器出错时返回本地拒绝，账目为零。报告从同一份原始捕获派生请求、实际 sent 和摘要。B 返回 D 的 sent 和 citation 目标仍为规范 ID。

这一入口形状是 B 的候选，供 A/D 与 #53 确认。保持现有共享合同、Gate 4、数据集、上游源码与 #47/#57 获批测试。方案中 #53 的运行级证明与报告落地仍属 evaluator 范围。

## B 验收矩阵

| 用例 | 验收 |
| --- | --- |
| 常规生产入口 | 通过真实 PaperQA2 查询，出站和已发送证据保留规范 ID。 |
| QUAL-02 正序、逆序、裁剪 | 原始捕获与模型实参相同，捕获先行且只有一次。现有 Gate 4 请求函数按固定 ID 验证成功。B 返回规范 sent 与固定到规范的引用映射。 |
| 无效绑定 | 缺项、双射重复、待审记录、正文不符、快照错误与问题不符均拒绝。捕获、模型入口与调用账目均为零。 |
| 裁剪后的引用 | 固定 ID 引用未发送证据时，B 保留未知引用诊断。未发送证据不出现在引用映射。 |
| 入口失败 | 空获准集、超预算或实际消息校验失败时，观察器和模型均未进入。观察器自身抛错时，模型零调用，拒绝继续发送。 |

测试使用真实 B Gateway、PaperQA2 和合成回答模型。当前累计基线的生产路径保持绿，评估用例均在缺失专用入口的断言处按预期失败。pytest 只允许 asyncio 的本地 Unix socketpair，并阻断连接。

## 复跑和审批

```sh
LITELLM_LOCAL_MODEL_COST_MAP=True .venv/bin/python -m pytest -q -c papertrace.pytest.ini test/offline/test_retrieval.py test/offline/test_b_answer_request.py test/offline/test_b_evaluation_boundary.py --tb=short
.venv/bin/python -m ruff check --config papertrace.ruff.toml test/offline/test_b_evaluation_boundary.py
```

当前 B 定向结果为 86 通过、14 项预期失败。A/D 和 evaluator 确认入口后，对精确测试候选进行非作者复审，再按课程序进入 B 源码实现。仅从拥有共享 evaluator 的最终累计版本记录可供 D 正式复跑的完整 SHA。
