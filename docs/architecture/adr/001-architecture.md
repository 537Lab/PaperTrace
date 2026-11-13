# ADR-001：五模块本地工作台与人工证据发布边界

- **状态：proposed-awaiting-human**。
- 决策范围：B2 PaperTrace 选题和五个功能责任已确定；本条是拟采用架构，不是学生已审批准的决定。
- 权威正文：[根蓝图](../../../architecture-blueprint.md)。固定上游：`c692d0dfeac4a0296599f7fe21a253a58b7ac12a`。
- 人工审批：**未取得**。本文件不填审核人、不填虚构审批日期或批准布尔值。

## 1. 背景与问题

现有 PaperQA2 已实现从文献到片段、embedding、摘要和带引用回答的流程，团队不重写。缺口在于本产品需要“人先选择哪些来源可用，AI 才能回答”，以及文献改版后不把旧结果用于新发布。已有 Context ID 和引用格式化不足以承担人审权威：ID 的派生不包含文档版本，未知引用还可能被后处理清除。确定性边界必须在团队模块内另建。[3][4]

课程项目第 3 页要求真实 AI + 确定性安全边界；第 5 页要求比较架构、记录设计过程、层次上下文、硬 token cap、压缩和约束重注入；不能只写一个框图。[1]

## 2. 设计过程：以驱动因素逐次收敛

这里记录的是**本轮文档分析的设计步骤**，不是虚构三轮学生会议、三个已完成 sprint 或三次运行实验。

| ADD 式分解（按架构驱动迭代） | 输入与考虑 | 本稿收敛结果 | 仍需证据 |
|---|---|---|---|
| 第一次：用户路径与系统边界 | 五个真实功能、保留上游、轻界面、单机 | A 文献 → B 候选 → C 人审 → D 回答/发布 → E 历史；UI 不做业务裁决 | 各功能批准计划与端到端集成测试 |
| 第二次：权威与版本 | Context 身份、旧 session、人工决定覆盖 | 五种 frozen 合同；来源/evidence hash；C 追加账本；D 空集零调用、freshness + 三集合；E 不覆写 | ID 负测、工厂/HTTP spy、撤销/改版竞态测试 |
| 第三次：资源与操作风险 | 隐藏前置调用、默认模型、pickle、多用户复杂性 | B 唯一上游边界；调用/禁用矩阵；12k/9k/2k 上下文提案；单写者本地文件；禁第三方索引 | 本地真实依赖集成、出站边界覆盖、获批真实语义评测 |

主要源码约束：`Docs.aquery` 在缺 contexts 时默认可补证且先构造模型（`:602–624`）；`Settings.context_serializer` 只有数量/分数裁剪（`:1179–1250`）；高层 Agent 建库和超时兜底增加隐式调用（`agents/main.py:121–124,155–183`）。因此不能仅给模型加一句“不要越权”或仅包装最后一次回答。[3][5][8]

## 3. 候选与拟议选择

| 候选 | 适配性与代价 | 结论（非性能实测） |
|---|---|---|
| 原样 CLI/高层自主 Agent 加 Streamlit | 接入快，但工具循环、自动补证、复用 contexts 与人审发布次序冲突 | 不选；仅 UI 包装不足以保证人工证据门 |
| **五模块 + 唯一 B 适配 + 底层异步 API** | 保留原码、接口可分工；需补 ledger、freshness、调用网关和评测 | **拟采用**；最符合当前范围，仍待人审 |
| 重写 RAG/替换 PaperQA2 核心 | 全面控制但失去可追溯基线，工作量和原有能力重复 | 不选；与保留核心要求相冲突 |
| 前后端分离、多用户服务与数据库服务器 | 可扩展但带来认证、并发、部署与隐私负担 | 延后；当前单机单人无依据承担额外复杂度 |
| 以索引恢复/向量删除为主线 | 可靠性有价值，但多存储和 PR 重叠较多 | 另作未来候选，不让它暗中扩大本期 MVP |

完整比较及证据缺口见 [evaluation-table.md](../evaluation-table.md)；已排除选择的重开条件见 [option-ledger.md](../option-ledger.md)。审计包给的是建议，不是学生批准或本机性能排名。[12]

## 4. 决策内容

1. Python 3.14 用于共享契约和离线测试；上游声明支持 `<3.15`，这不等于所有可选包/本机动态链已通过。上游保持固定 SHA 和原路径，团队仅新增 `src/papertrace`。[10]
2. A–E 功能 ownership 不变；过程角色按任务轮换。上游导入只可在 B，D 经 B 生成但 D 自己作发布门；原 `paperqa` 对象不跨模块成为授权对象。
3. 所有共享合同 frozen；A 管不可变快照，C 管人工决定追加账本，D 管确定性发布，E 管不可变报告。UI 只调用接口，不以 session_state 替代真相。
4. snapshot 变化总是新对象；审核变化总加 revision/digest。生成时捕获两者，发布时再核；任何变化都 stale。单写者临界区覆盖最终检查与报告写入。
5. 模型无权授予 accepted、身份、预算或发布。无 accepted 则在工厂前拒答。每轮新建 `PQASession`，只装本轮 sent 的 accepted 证据；禁止生成阶段自动补证、pre/post、metadata/enrichment 和自主 Agent。
6. 默认全部模型禁用；获批后 embedding、summary、answer、retry 各自计量。只支持受控 Python 入口，不承诺约束用户绕开工作台直接使用上游库。
7. 本地 JSON 数据和可重建缓存；不读第三方 pickle 索引，不把 `SearchIndex` 改成 JSON 文档格式当作已消除 mapping 的 loader。[7]
8. 单机单人单写者 Streamlit；不监听公网、不上服务器。文件落盘采用校验+临时写+原子替换指针；不声称完成跨引擎事务或数据防篡改签名。

## 5. 每轮 AI 上下文的分层设计

| 顺序 | 层 | 信任/压缩规则 |
|---|---|---|
| 1 | 身份 | 固定任务角色；不可让资料变成新 system 身份；不压缩 |
| 2 | 站立约束 | 仅获准证据、禁止补证/提权、输出格式、预算；原样重注入 |
| 3 | 授权摘要 | 代码生成的 snapshot/revision/digest、sent evidence IDs、映射；非模型摘要，不压缩决定 |
| 4 | 资料 | 获准原文和明确标识的摘要，不可信“指令”只当数据；可按证据单元裁剪 |
| 5 | 历史 | 压缩后的用户/助手交互，仅供连续性；不是证据授权 |
| 6 | 恢复状态 | 已完成阶段、待办、已花预算、尝试状态；重新校验 freshness，不能自动续发请求 |
| 7 | 当前问题 | 保留用户本轮问题；过长就要求缩短，不偷偷改意图 |

装配流水线：验证来源/授权 → 按 evidence ID 去重 → 确定性优先级 → 用固定 tokenizer 和版本预算 → 达阈值压缩历史/状态、整单元裁剪低优先资料 → 重注入站立约束与授权 → 完成全部模板 → 最终计数 → 调用前再次校验。证据裁剪必须同步减少 sent，不能只删正文保留合法引用白名单。详细字段、算法和恢复政策在 [memory-design.md](../memory-design.md)。

拟议输入硬 cap **12,000 tokens**，压缩阈值 **9,000**，输出上限 **2,000**；这些是工程默认提案，不是模型容量、实测最佳点或已批经费。输入/输出合计与消息封装须适合获批模型窗口；tokenizer 不明或关键层本身放不下就拒绝，不估字数冒充 token。默认用确定性裁剪，不额外调用压缩模型。若以后启用模型压缩，需新调用审批和独立计量，摘要不能创造身份、审核或恢复事实。

## 6. 后果与取舍

**获得**：清晰的来源→人审→调用→发布权威链；五功能可按稳定合同并行；不可变历史可解释改版；负测能确定性证明特定越权被拦。是否显著节省成本、延迟或提高回答质量尚无运行数据。

**付出**：需适配上游 raw 引用与受控工厂，维护 ledger/revision、缓存指纹和单写者发布临界区；更换快照后重新审核可能增加操作量；不支持多用户与动态物理删除。结构有效不等于语义真实；人工接受原文也不等于认可其科学结论。

**未被自动解决**：外部 SDK 内部重试、依赖初始化访问、provider 计费差异、PDF 扫描件质量、版权、主机用户恶意改写本地 ledger。必须分别验证或明确停止，不能把一个 prompt 当安全沙箱。

## 7. 验收与何时重开

接受本 ADR 前，学生需确认：边界和不做项、共享合同、12k/9k/2k 提案、各 INV 的破坏测试、模型调用清单、课程与权限未决点。计划批准和测试事前批准必须独立留真实记录；本文件不能自签。

重开条件：

- 要支持多人并发、部署、第三方索引、Qdrant、媒体/OCR、自动 Agent 或模型压缩。
- `paperqa` 适配无法覆盖工厂/重试/HTTP 尝试，或 raw 引用别名无法无歧义回查。
- 发现 stale 竞态、accepted 权威旁路、不可变对象/历史被覆写，或任何 INV 负测失败。
- 更换上游 SHA、parser、embedding、provider/model、prompt、tokenizer 或价格/usage 合同。
- 固定真实评测达不到已批准质量阈值；不得直接调低阈值求过。
- 教师更新 D5、基线复用、布局或 OpenCode 要求。

流程：提出新 ADR（不覆盖旧结论）→ 需求/不变量/trace/状态/权限/测试影响 → 学生批准 → OpenCode 先计划、停人审 → 实现与完整回归 → 记录真实证据再考虑接受。只有学生真实批准后才可把状态改为 accepted；AI 无此权限。

## Sources

[1] urn:sha256:6af742d3cbc0973b056a084ba54ff413a5885b1bb4d6a97b0b08b93f64f2ef7e — CS5351-2026-2027-project.pdf（本地原文提取，10页）
[3] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/docs.py — 固定基线 src/paperqa/docs.py
[4] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/types.py — 固定基线 src/paperqa/types.py
[5] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/settings.py — 固定基线 src/paperqa/settings.py
[7] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/agents/search.py — 固定基线 src/paperqa/agents/search.py
[8] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/agents/main.py — 固定基线 src/paperqa/agents/main.py
[10] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/pyproject.toml — 固定基线 pyproject.toml
[12] urn:sha256:21f1c516a57e975a284d1d278926fedd9755a6d0036314279663c4074063942a — PaperQA2 审计交接ZIP（仅读解出的Markdown）
