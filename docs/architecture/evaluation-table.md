# 架构候选比较表

> 状态：**定性工程比较，非实测排名；拟采用方案待学生批准。** 本表比较的是如何实现已确定的 PaperTrace 选题，不重新选题，不承诺节省多少时间/token。

## 1. 评估依据与硬条件

课程项目原文第 3、5 页要求真实 AI、确定性边界、候选比较与架构约束；第 6、10 页要求完整治理和验证。教学介绍第 25 页倡导低耦合、清晰责任、多个 ADD 设计轮次与减少浪费，不给任何本项目性能数字。[1][2]

硬条件先于便利性：保留固定 PaperQA2 基线；A–E 都有真实功能；只人工决定 accepted；空获准集零生成；三集合+新鲜度；历史不覆写；默认拒绝代码/数据/模型权限；12k上下文提案需可强制；禁不可信pickle。任一硬条件无法落实就不能只凭“接入快”胜出。

## 2. 同一口径比较

| 维度 | O1 原样高层Agent/CLI + UI | O2 五模块薄适配（拟采用） | O3 重写/改造上游核心 | O4 多用户前后端+数据库服务 | O5 索引恢复/物理撤销主线 |
|---|---|---|---|---|---|
| 固定基线复用 | 保留源码，但默认行为须拦 | 原码冻结，B唯一边界 | 大量改/替换，与本轮约束冲突 | 可复用但部署层新增大 | 深入索引/生命周期热点，易动原码 |
| 人审→生成的硬次序 | 自动补证/工具循环需另控 | D前门、C ledger、B受控session直连 | 能做，但重建现成能力 | 可做，还需多人授权/冲突设计 | 需额外补人审/发布门，不能只修缓存 |
| 空集零工厂/HTTP | 原aquery早期工厂需避开 | D在B前拦；仍需真实spy验 | 可设计，代价高 | 可设计，服务启动副作用更需核 | 仍须独立D前门 |
| 三集合与freshness | 上游contexts与sent不完全等价 | 自定义serializer+raw映射+final锁 | 自己维护全链 | 需跨请求/多写者并发控制 | 易扩大为多索引事务 |
| 五功能ownership | 容易沦为UI包装/配置任务 | A–E稳定合同，端到端职责明确 | 热点冲突、任务界限更难 | 人力可能被部署/前端吃掉 | 多人改同SearchIndex热点 |
| 部署/依赖负担 | 低，但隐式调用/索引多 | 本地Streamlit+文件、单写者 | 高，兼容回归负担 | 高，认证/服务/数据迁移 | 中高，native索引与多存储 |
| 离线确定性验收 | 可做局部但需额外截断旁路 | 合同/出站spy/时钟/来源/竞态清楚 | 可做但测试面大 | 需额外并发/网络/部署测试 | 故障注入适合，但native细节须实跑 |
| 费用与隐私边界 | 默认元数据/enrichment/Agent额外路径 | 默认关，明确受控调用清单 | 需重审全部自建路径 | 增加网络与多用户秘密管理 | 大多可靠性可离线，RAG仍需批准 |
| 上游工作重复风险 | 已有能力多，不可称原创 | 人审/授权/追溯为应用增量 | 重造现成RAG风险高 | 大型UI/服务非课程主贡献 | 多个Bug已有公开PR，归因负担高 |
| 本期取舍 | 不直接采用 | **拟采用，条件化** | 拒绝 | 延后 | 未来选项，不并入MVP |

评价不是按未经论证的加权分数相加，没有“快30%”或“更省50%”等虚构指标。O2 的低耦合/可检验性来自边界设计，不是运行性能已优于所有方案。

## 3. 源码如何影响取舍

| 证据 | 对候选的影响 |
|---|---|
| `docs.py:602–624`先工厂、可自动补证；`:626–639,694–711` pre/post额外调用[3] | 不能直接用高层流程替代人工授权链；O2先D门、后受控B |
| `settings.py:1179–1250`只按相关度/数量选contexts[5] | token cap和sent记录需团队实现，不把现成serializer当硬预算 |
| `types.py:304–316,400–402,480–515`ID/used_contexts/格式清洗[4] | 新来源ID和raw校验必要，避免把合法key等同授权/真实发送 |
| `agents/search.py:86–93,242–257`两个pickle入口[7] | 本期不导第三方索引，而非全格式迁移；O5完整方案另估 |
| `agents/main.py:121–124,155–183`建库与timeout外兜底[8] | 高层Agent额外外呼难全控；默认禁用，不用fake-agent名称推断免费 |
| 主包/可选parser许可不同[10][11] | 最小显式PyPDF文本路线；额外parser、论文分发另审 |

## 4. O2 的接受条件与实验计划

| 决策假设 | 需要的真实验证 | 失败时如何收敛 |
|---|---|---|
| B能在不改上游下接入底层API | 独立环境离线adapter smoke、显式模型对象、raw别名一对一映射 | 先缩小上游入口；无法覆盖则重开ADR，不擅自改核心 |
| 唯一网关覆盖全部声称受控调用 | 工厂/SDK/HTTP spies，包括入库embedding/summary/retry | 默认保持禁用，逐路径闭合再授权，不宣称全链已安全 |
| 单写者文件适合MVP | crash/半写/锁冲突/发布TOCTOU负测 | 缩小并发；真需多用户才重新评估数据库 |
| 12k/9k/2k适合所选模型 | 固定tokenizer的边界/重注入离线测试，再获批模型协议验收 | 取更小窗口/缩小数据；不把输入截断后继续发布 |
| 真实回答满足质量要求 | 固定eval集、人工标注rubric、获批真实模型回执；基线后冻结阈值 | 明示不达标，调整设计/证据，再复评；不得补造PASS |
| 功能分工与角色轮换可兼容 | 每模块计划/测试/PR + 轮换记录的真实人审 | 保留功能ownership，轮换过程责任，不设永久管理岗 |

当前状态：本表没有进行动态候选性能比较，也没有真实模型语义数据。契约、基础检查的实际结果由主控执行回执提供；课程D5、测试/计划批准、远端门禁与模型预算仍分别待学生确认/授权。

## 5. 决策边界

拟采用 O2 并不是已经 accepted 的 ADR。学生批准前仅能做本轮限定的初始化；批准后每位成员仍须通过 OpenCode 先计划、停人审，再构建。未来重开条件与历史选项在 [ADR-001](adr/001-architecture.md) 和 [option-ledger.md](option-ledger.md)。

## Sources

[1] urn:sha256:6af742d3cbc0973b056a084ba54ff413a5885b1bb4d6a97b0b08b93f64f2ef7e — CS5351-2026-2027-project.pdf（本地原文提取，10页）
[2] urn:sha256:16d399f7ca14e0c49dea382cec3893bbee8f589edcaee5131f10fad257d3acb5 — cs5351-2026-2027-introduction.pdf（本地原文提取，27页）
[3] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/docs.py — 固定基线 src/paperqa/docs.py
[4] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/types.py — 固定基线 src/paperqa/types.py
[5] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/settings.py — 固定基线 src/paperqa/settings.py
[7] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/agents/search.py — 固定基线 src/paperqa/agents/search.py
[8] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/agents/main.py — 固定基线 src/paperqa/agents/main.py
[10] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/pyproject.toml — 固定基线 pyproject.toml
[11] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/packages/paper-qa-pymupdf/pyproject.toml — 固定基线 PyMuPDF 子包许可声明
