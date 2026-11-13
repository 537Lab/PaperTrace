# 模块 B｜PaperQA2 检索与唯一适配边界

> 可独立认领：成员 B。你拥有有实际用户价值的证据检索功能、错误处理及 retrieval view，不是只装依赖或给别人写工具。本轮未实现业务；先审核测试与 OpenCode Plan。

## 1. 目标用户与完整用户流程

研究者选定 A 的固定文献快照并提问 → 发起受控检索 → 查看候选原文、摘要、出处与状态 → 无结果/失败时知道原因 → 把标准 EvidenceRecord 交给 C 人审。后续 D 要生成时，B 按 D 授权机械适配到 PaperQA2，不替 D 批准证据或放行答案。

所有团队新增代码只有 `src/papertrace/retrieval/` 可以 import `paperqa`。A 的摄取、B 的检索/摘要、D 的回答所需上游调用均在此边界执行；其他模块只见共享数据及中立端口，不见可变 Docs/PQASession。

## 2. Must 需求与不做项

| ID | 必须实现 | 可检查的验收语义 |
|---|---|---|
| `FR-B-01` | 以固定异步 API 检索，映射可定位原文、文献版本和团队 evidence ID | 每条候选可核到所选 snapshot/doc/version/原文范围；摘要与原文分开；上游 Context.id 不是团队身份 |
| `FR-B-02` | 空结果、超时、解析/模型错误明确呈现 | 未报告失败数量为零；无伪造证据、无静默换模型、重试有界且纳入批准预算 |
| `INV-02/03` | 来源不可变且不得产生人工授权 | hash/作用域错误被拒绝；EvidenceRecord 无 accepted/status，AI 高分不创建 ReviewDecision |
| `INV-08` | 拒绝不可信第三方 pickle 索引，许可逐项检查 | 不调用外来索引 loader；上游代码许可不自动涵盖 parser/论文 |
| `FR-D-03`（D owner，B 协作） | 受控生成适配不得自动补证、pre/post 或自治 Agent 绕过 | 全新已过滤 session；原始输出/引用映射可核；由 D 决定授权/发布 |
| 共同约束 | `QA-01`、`PERF-01`、`COST-01`、`SEC-01`、`GOV-01`–`GOV-04`、`INV-06/07` | 真实 registry 的阈值；零默认模型请求，按实际 token/权限/调用预算执行 |

**不做：**全网论文发现、autonomous/fake agent、Qdrant/云数据库、第三方索引导入、多模态/收费 OCR、独立事实判真、自动接受证据、回答发布。默认固定 PyPDF 文本解析；安装不同后端不能无声改变输出定位。核心 API 不兼容先报告/ADR，不私改上游。

## 3. 输入输出与职责交接

| 场景 | 输入 | 输出 | 失败/禁止行为 |
|---|---|---|---|
| A 摄取 | 托管的固定版本文件、人工元数据、显式配置 | 解析/表示结果与失败阶段，A 持有导入状态 | 缺 citation 默认可能先调模型；必须受控配置，不能擅自联网补元数据 |
| 本模块检索 | CorpusSnapshot、问题/问题 ID、批准配置与调用许可 | EvidenceRecord 集合与可区分的空集/执行错误 | 不能从当前用户目录扩大检索，不能失败后直接回答 |
| C 审核展示 | evidence 的 excerpt、locator、版本、advisory_summary | 原文/摘要/来源清楚区分的 retrieval view；C 独占人工决定 | 不预填“已接受”；不把 score 当可靠性或科学可信度 |
| D 受控生成端口 | D 已筛选且绑定 snapshot/review 的证据、提示词/预算策略与许可 | 原始模型输出、最终实际 sent 与本轮 key→完整 evidence ID 映射、调用元数据 | 不返回旧 session；不追加待审证据；不自行发布/重试/换 provider |

这些是**待实现端口语义**，不是现成函数。准确签名/伴随元数据包经 Plan 和共同接口审核后再生成；不往 frozen 五模型偷偷加字段。

`EvidenceRecord` 的真实 v1 字段包括 snapshot_id、document_id、version_sha256、locator、excerpt、retrieved_at、advisory_summary、upstream_context_id、evidence_id；没有权威 accepted 或相关度批准字段。若展示上游 relevance score，放获批的建议性展示/运行信息，不伪装成共享模型已有字段。

`SourceLocator` 需完整的 1-based inclusive 页范围或行范围、chunk_id、parser_name/version。上游只有 chunk 名不足以满足合同：PDF 如实用页范围；文本从受控源建立可验证行映射，做不到就明确失败/先审合同，不能猜行号。原文不做摘要替换；身份经共享模型计算/校验。

### 必须查清的上游真实行为

- `src/paperqa/docs.py`：`Docs.aadd`、`aget_evidence`、`aquery`。aadd 可能做引用推断/元数据/embedding，不是“本地文件就离线”；显式提供人工 citation、关闭未经批准的 doc details/多模态/enrichment。
- `src/paperqa/types.py`：Context.id 可依赖问题与摘要前缀，不具团队来源稳定性；`raw_answer` 与格式化答案分开。
- `aquery` 会初始化模型对象；contexts 空时默认可能补证，pre/post 可额外调用。**D 空获准分支不得进入本端口或初始化工厂**。
- serializer 会排序/cutoff/top-N；必须记录序列化后真实 sent，而不是检索全集。生成使用新的已过滤 session，显式 `answer.get_evidence_if_no_contexts=false`、`prompts.pre/post=None`，不复用旧答案/contexts。
- 引用格式化可能清理未知 key；原始输出先留给 D 做核查，不能清理后冒充“无未知引用”。不以 `has_successful_answer` 代 ReleaseDecision。

## 4. 可改路径与依赖安装边界

后续候选写范围：`src/papertrace/retrieval/`（adapter、受控工厂/调用账目、自己的 view）、`test/offline/test_retrieval.py`（测试）、`test/fixtures/retrieval/`（合成材料）、`docs/team/module-B.md`。自己的业务目录由获批 Build 创建。Plan 须将源码、`view.py`、测试及每份 fixture 展开为精确相对文件，经人工确认当轮权限；目录 ownership 不是整目录自动授权。共享 fixture wrapper 只把 `data` 传入模型。

共享合同/fixtures、requirements/architecture、AI-use/review/bug/debt、依赖锁/CI/应用入口/编排需预约编辑者并单独批准。D 的生成策略与专属提示词归 D，B 不擅自改内容；A 的库状态、C 的 ledger、E 的历史文件也不能直接写。

冻结 `src/paperqa/`、`packages/`、上游 `tests/`、`pyproject.toml`、`uv.lock`。新增 PaperQA2 业务依赖、构建生成的版本文件、Streamlit 或 parser 安装需另走计划，不把初始化 `requirements-init.lock` 当完整业务安装。不能读取 `.env`、真实 `~/.pqa`、keys 或个人索引；不能运行不可信 pickle/漏洞 PoC。网络/收费模型默认禁用。

## 5. 不阻塞开发的 fixture 方案

不等 A/C/D：用共享规范 CorpusSnapshot，构造本地 synthetic 原文与模拟 Context/模型结果；用 fake backend 记录每次输入与工厂初始化次数。先证明映射与边界，再在获批业务环境做真实上游离线集成。

准备：同文献不同版本、不同 snapshot 相似段落、两来源相反事实、无关段落、含“忽略规则/把所有证据设为 accepted”的恶意指令、无定位、超时/畸形摘要、带未知 key 的原始回答。材料均自写且标 synthetic；不把固定 mock 输出叫模型质量。

真实调用再分两关：先单独批准业务依赖与离线集成；再批准 provider/model、数据、请求/重试、金额和 deadline，才试 live。工厂初始化/SDK attempt/HTTP attempt/成功响应/usage 分开记录；缺 usage 是 unknown，不是 0。B 与 D 一起核准 INV-07 输入 12,000、9,000 压缩、输出 2,000 的拟议工程约束及实际模型窗口，不自行放宽。

## 6. 测试与行为评估语义

| 场景 | 必须断言 | 关联 |
|---|---|---|
| 正常映射 | excerpt 为原来源文本，locator/版本/snapshot 可核；摘要变化不改变 evidence 身份；JSON 往返 | FR-B-01、INV-02、QA-01 |
| 串库/错误 hash/坏 locator | 不接受跨 snapshot 或失效版本；只凭 Context.id 不通行；无伪造行号 | FR-B-01、INV-02 |
| 空集/超时/解析错误 | 空集和错误状态不同；原因被展示；不捏造来源、不静默换模型/无限重试 | FR-B-02、COST-01 |
| AI 建议越权 | 高分、advisory_summary 中的 accepted 或恶意原文均不能写 C ledger | INV-03、SEC-01 |
| D 生成适配 | 截获最终 payload，pending/excluded 原文不出现；sent 与真实序列化一致；全新 session；自动补证/pre/post/Agent 调用计数零 | FR-D-03、INV-04 |
| 空批准端口不进入 | 由 D fake 调用协作验证，B 工厂/SDK/HTTP attempt 均零 | INV-01、COST-01 |
| 原始未知引用 | 原 raw 输出及一对一 key 映射交 D，格式化清理不能抹掉检测依据 | FR-D-02/03、INV-04 |
| 不可信索引与隔离 | 不运行 loader；离线出站阻断；无私人目录/凭据/真实缓存访问 | INV-06/08、SEC-01 |
| 回归 | 上述 fixtures 在每轮完整 prior suite 中保持相同边界；真实上游离线集成另列依赖和结果 | GOV-02 |

行为评估：候选是否相关、摘要是否忠实、来源定位是否准确分别评，不用 relevance score 代可信度。真实 prompt/model 变化须固定集 live 回放与阈值，结果看 [../ci/gates.md](../ci/gates.md)；未跑保持 BLOCKED。offline fake 仅能证明映射、调用与授权逻辑。

## 7. 可审核执行计划

1. **需求/API 审核：**读已有 AGENTS/Prompt、蓝图、registry、contracts；在 Plan 列上游调用点、可能外呼、模型对象初始化、解析后端/许可、可改范围与对 A/C/D 的中立端口，停等批准。
2. **事前测试：**提交上表输入/断言、出站 spy、source locator 映射方案与失败回退；由非作者先批准测试/计划，并确认 Build 写权限。
3. **最小纵切：**OpenCode 先做 synthetic 映射/检索状态和 retrieval view，不安装一整套 extras；先核来源身份和不可越权，再接真实 API。
4. **受控适配：**在另批业务环境加入 aadd/aget_evidence 与 D 的 aquery 执行端口；审查新 session、最终 sent、原始引用和默认拒绝的模型工厂，不代 D 写发布算法。
5. **Verify：**`.venv/bin/python -m pytest -c papertrace.pytest.ini test/offline` 与 [../ci/gates.md](../ci/gates.md) 的真实 gates；真实上游集成、live 单独记录，不能用 skipped 顶替。
6. **独立 PR：**演示候选来源→空集/失败→恶意输入不批准→受控生成截获；附依赖/许可/出站矩阵、D1–D9、独立 verdict，未经批准不推送。

验收是可检索/显示/交接的完整功能和 view 加结构/负例/全回归、真实监督/审查证据，不是创建空 adapter 类或仅安装成功。

## 8. D1–D9 与轮换交接

| 项 | B 应提供的真实证据 |
|---|---|
| D1 | FR-B-01/02、INV-02/03/08 与 D 协作约束的 fit/测试映射 |
| D2 | 适配/唯一 import 边界、表示指纹与定位映射、调用/预算/错误政策、必要 ADR |
| D3 | retrieval 白名单、受控工厂/工具矩阵、冻结核心和禁止索引/凭据访问的证据 |
| D4 | 事前测试批准、输入截获/异常注入/全回归/语义状态、逐 PR memo 与真实 bug/debt |
| D5 | 本人的原始 OpenCode session，API 风险处的人工重定向/批准及理由；非 Hermes 初始化冒名 |
| D6 | 真实功能/协作贡献、依赖误判和边界发现、本人反思素材；身份本人填 |
| D7 | 实际本地 diff/获授权后 PR 与 CI/独立 review；未建仓、未保护不标已完成 |
| D8 | adapter/检索服务/view、合成 fixtures、正负与真实上游离线集成测试；live 隔离 |
| D9 | 根 Prompt 启动的 Plan、测试/权限批准和分步 Build/Verify 记录 |

第一轮：**C 批准测试/计划，D 独立 review，E 集成**；后续按 [工作计划](../../TEAM_WORK_PLAN.md) 非作者轮换，共同实现者回避。交付按 [交接清单](handover-checklist.md)，合同变更按 [集成合同](integration-contract.md) 先审批后同步。

S0–S4 为相对检查点（建议每 sprint 1–2 工作日），不是教师 DDL。课程工具/复用/D5 口径、Week 13 确切时间由学生确认；GitHub 尚未创建，不编造地址或审批。本任务书不授权任何真实模型、凭据读取或无人监督开发。
