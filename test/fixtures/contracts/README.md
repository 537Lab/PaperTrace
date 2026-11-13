# 自写合成契约样例（synthetic）

全部内容都是初始化时手写的工程测试数据，不来自真实论文、模型回复、人工审批、发布运行或学生课程贡献。`reviewer-A` 只是非姓名代号，不是签名。

- 七个 `<ModelName>.json` 分别对应五个主契约以及 `DocumentVersion`、`SourceLocator`。
- 每个 JSON 外壳显式带 `synthetic: true`、`provenance`、`contract`；只有 `data` 字段的值可以传给对应 Pydantic 模型。元信息不是业务字段。
- `synthetic-paper-a.txt` 为自写的一行非科学文字。`DocumentVersion.version_sha256` 是该文件精确 UTF-8 字节（包含末尾 LF）的真实哈希；摘录不包含末尾换行。
- 文献、快照、证据、审核、草稿间 ID 有一致的示例关联。`ReviewDecision.status="accepted"` 仅展示数据形状，不代表真人实际接受。`ReleaseDecision` 明确为 `blocked`，原因 `SYNTHETIC_NOT_RUNTIME_VERIFIED`，五个检查标志均为 false。
- 示例 `review_digest` 是 `{"synthetic": true, "reviews": [示例审核]}` 规范 JSON 的 SHA-256，仅用于保持示例引用一致；不是 C/D 权威账本算法或认证证明。
- 完整字段、规范哈希与未实现的权威核验见 `docs/contracts/schema.md`。

不要把本目录复制为真实研究证据或语义评估结果。业务模块的真实模型评估、人工审批和运行时发布均尚未开发。
