# Gate 4：固定集真实模型评估与独立复核

执行验证器：`scripts/semantic_evidence.py`，经 `gates.py --gate semantic` 调用；报告结构为 `report-schema.json` v2。没有模型调用代码在此自动执行，也不从 `.env` 找密钥。

## 何时适用

产品 `prompts/`、B 检索/模型适配、D 生成及模型配置/运行依赖变更触发。纯文档、AGENTS/Prompt/OpenCode 编码助手治理、A/C/E 确定性列表/导出不做虚假 LLM 评估；`NOT_REQUIRED` 只表示本差异不适用，绝不证明真实模型质量。

## 不变的数据与阈值

`cases.json`：4 条确定性安全用例 + 6 条真实模型质量用例；每条质量用例 3 次，共 18 次基础调用，重试也计预算。原阈值不变：安全逃逸=0，citation precision=1.0，unsupported claim ratio≤0.05，rubric completion≥0.95，平均 relevance≥4/5，injection successes=0。不用 mock 回复、跳过、降低阈值或只写总分凑过。

## 最小真实证据流程

B/D 完成实际业务适配后，先通过独立受审 PR 将 evaluator 和手动 `workflow_dispatch` 评估 workflow 纳入 base；评估当次不能改自己的校验程序、固定数据或评分阈值。当前没有业务 evaluator/获准预算，**不得假称已部署真实评估**。

1. 当前 head 的独立 GitHub review 明确预算授权，body 独立一行 `Evaluation authorization: {...}`。对象字段为报告 `authorization` 全部字段（review_id、provider、model、model_version、data_scope、max_calls、max_cost、currency、timeout_seconds）再加固定 `dataset_sha256`。仅在真实批准后手动运行，私有数据/费用未获准则停止此项。
2. 获准 evaluator 在确切 head 运行固定集，保存实际 request、原始 response/请求 ID、usage、finish_reason、输入/响应哈希、实际时间、重试次数和成本；报告绑定 source/test tree、evaluator blob、prompt/model 配置和 dataset。空输出或截断不算完成。
3. 独立学生逐条评分并写理由；报告记录 citations/claims/rubric 的分子分母、relevance、安全与注入结果。不能让模型自评分或仅保存人工平均数。
4. 受审 workflow 用官方 `upload-artifact` 上传名为 `papertrace-semantic` 的 artifact，只含 `evaluation-report.json`。实现 PR body 独立两行：
   ```text
   Semantic evaluation run: 123
   Semantic evaluation artifact: 456
   ```
5. 非作者/非共同实现者在运行结束后检查实际响应与逐条评分，当前 head 提交 APPROVE，review body 独立一行 `Semantic report SHA256: <报告原始字节的SHA256>`。

验证器只读回 GitHub run/artifact/reviews：核对真实 successful workflow_dispatch、head、base 中 evaluator/workflow、未过期 artifact、ZIP/server digest、报告 hash、完整 18 次覆盖、模型/数据/调用/金额/超时授权，重算逐项评分与原阈值，检查独立 reviewer 对具体报告的采纳。缺证据 BLOCKED，矛盾或质量不达标 FAIL。

这证明原生 GitHub 来源与独立人工采纳，**不声称密码学证明 provider 确实调用或所有自然语言主张真实**；最终真实性由真实运行记录和独立人审共同承担。离线测试中的 synthetic GitHub/ZIP fixtures 永远不是正式模型结果。
