# A→B UTF-8 TXT 摄取回执测试提案

A 侧对请求和回执的书面确认见 [Issue #29](https://github.com/537Lab/PaperTrace/issues/29#issuecomment-7108692559)。A #17 调用注入的同步 `ingest(request)`。本提案基于 B #34，拟新增公开端口 `Gateway.ingest(request)`。实现时可把其绑定方法注入 A 的现有构造器。当前提交仅包含测试、计划和披露。

- 输入沿用 `document_id`、`version_sha256`、`source_name`、`source_bytes`、`metadata` 和 `policy_ref`。B 重新对实际字节做 SHA-256 校验，并接受 A 传入的空 `metadata` 和大写 `.TXT` 文件名。
- 首轮 `ready` 表示合法 UTF-8 TXT 已通过解析前置校验。在 `parse` 阶段返回可重现的 `txt-validated:{document_id}:{version_sha256}`。重复提交同一版本得到相同引用，替换后的版本得到不同引用。A 将 `ready` 版本加入快照，B 按需读取对应托管字节。后续的按需检索仍可能失败，由检索端口报告结果。
- 格式、解码、空内容或哈希不符返回 `failed`，原因码分别为 `UNSUPPORTED_FORMAT`、`INVALID_UTF8`、`EMPTY_TEXT`、`HASH_MISMATCH`。回执只含身份、状态、阶段、原因和逻辑引用。失败测试检查回执、标准输出、标准错误和日志均不含合成原文或私有路径标记。
- 测试注入有计数的读取、检索和模型替身，要求验证过程不触发这些端口。pytest-socket 禁止外部连接。PDF、持久化索引、真实模型、A 源码及共享契约在本次范围之外。

需求对应 FR-A-01、FR-B-01、INV-02、COST-01 和 SEC-01。测试与后续 B 实现提案均以包含 #34 的 `codex/b-generation-accounting-implementation-v2` 为目标分支。独立人审批准测试提交后再进入实现。测试提案应保持开放供后续引用。
