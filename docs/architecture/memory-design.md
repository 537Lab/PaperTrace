# 状态、记忆与 AI 上下文设计

> 状态：proposed-awaiting-human。这里的目录、持久化与装配器是 A–E **待实现合同**；不是本轮已有数据库、后台任务或可恢复 Agent。权威正文：[根蓝图](../../architecture-blueprint.md)。

## 1. 三类东西不要混为“记忆”

1. **来源与人审真相**：托管原件/快照、Evidence 原文及 locator、C 的追加审核账本。它们决定什么可以使用；模型摘要不能改它们。
2. **可重建表示与工作状态**：解析结果、embedding、候选摘要、UI 选择、当前阶段、调用预算/请求状态。丢失时可重建或明确终止，不能当人审事实。
3. **历史研究记录**：E 保存问题、当时来源与审核版本、实际发送/引用、草稿/发布结果。保留当时事实，不宣称现在仍有效。

课程项目第 5 页要求跨会话、中断、版本、写/取回政策、ownership、retention、privacy；默认上游 session/轻量响应不自动满足它。`PQASession.filter_content_for_user` 会去原文、媒体、embedding（`types.py:442–472`），因此研究记录需独立证据包，而不是关闭原有过滤。[1][4]

## 2. 计划中的本地存储布局

以下用 `.papertrace/` 表示仓库根下被 Git 排除的私有运行目录；不是允许 coding agent 任意读它。只有合成测试目录对测试角色开放。真实原件通过用户显式选择导入后，由产品管理；不扫描用户 home、个人资料库或上游 `~/.pqa`。

```text
.papertrace/                       # 单机单人，不同步到Git
  sources/<document>/<sha256>/     # A：托管源字节、只读版本
  snapshots/<snapshot_id>.json     # A：不可变文献清单
  state/current.json              # A：当前snapshot指针；单写者原子切换
  evidence/<snapshot>/<evidence>.json  # B：不可变来源/原文；建议摘要另标版本
  review/<snapshot>/<question>/   # C：追加事件、revision、digest投影
  cache/<representation_hash>/    # B：可删除重建的解析/向量/摘要表示
  requests/<request_id>/          # B/D：调用许可、attempt与恢复状态
  reports/<report_id>/            # E：不可变JSON/Markdown和manifest
  annotations/                   # E：追加superseded/损坏/来源失效注记
  events/                        # 脱敏诊断、非证据授权来源
  staging/                       # 未完成写入；从不当作已提交记录
  quarantine/                    # 损坏/不匹配对象，仅人工检查
```

路径片段只由合同验证后的标识派生，不接受用户直接拼路径；resolve 并核 root、拒绝越界 symlink。源文件 display name 不存主机绝对路径。数据存储使用 JSON/文本和明确数组字段；禁止通过 pickle 直接保存 `Docs`/`PQASession` 作为可移交持久状态。

## 3. ownership、写与读取政策

| 状态 | 写入 owner 与时机 | 取回条件 | 跨会话/中断与版本 |
|---|---|---|---|
| 原件 / `DocumentVersion` | A 完成复制与 hash 后；源路径原件不改 | hash 对上才显示/交 B；仅允许本工作区来源 | 始终绑定 logical ID+SHA256；同路径更新为新版本 |
| `CorpusSnapshot` | A 汇总 ready 文献形成新清单，校验后切指针 | schema/hash/清单 membership 全通过 | 不修改旧快照；当前指针损坏则只读，不猜最近的就是当前 |
| `EvidenceRecord` | B 从源 Text+真实 locator 构建 | snapshot/doc/version/原文/locator 验证 | 缺 record 或原件不假造；重新解析产生新表示及必要的新 evidence |
| 候选摘要与 embedding | B，在获批调用后 | 表示指纹完全匹配；永不授 accepted | 变更 parser/chunker/model/prompt/tokenizer 后明确失效；不静默混向量空间 |
| `ReviewDecision` ledger | C，经明确人工命令追加 | 验 event 顺序、范围、schema、revision/digest；按 question 投影 | 无决定 pending；重置为新的 pending 决定；不迁移旧快照的接受状态 |
| 调用/恢复状态 | B 执行计量，D 保存阶段和捕获的 scope | 调用许可未过期且 scope/freshness 复核 | 未知是否出站就标 unknown，禁止自动重发；已花预算不能归零 |
| `AnswerDraft` / `ReleaseDecision` | D，验证后新建对象 | 只有绑定的 scope 与原始回答可作该轮记录 | 改版/审核变化则旧轮 stale；不更改旧决定为 released |
| 报告/manifest | E，经 D→E 临界区提交 | 校验完整性、来源、schema；显示历史/当前标签 | 不覆写，不就地升级；superseded 用额外注记，不改原字节 |
| UI session_state | UI，当前页面选择/进度 | 仅提示与界面缓存 | 刷新可丢；恢复必须从 A/C/E 重读，不能带出自动批准 |

上游 `Docs.delete` 的 tombstone 有部分过滤但不物理删向量，现有 session 又可复用（`docs.py:403–435,476–490,609–647`）。本设计用快照失效与新 session 限定新发布；不宣称实现向量擦除或完整跨存储删除。[3]

## 4. 来源身份与审核账本

### 4.1 身份与 locator

- 文献 ID 表示逻辑文献；version SHA256 表示源文件字节。`snapshot_id` 绑定按文献 ID 排序后的完整 ready 清单；同清单不同捕获时间不应产生不同身份。
- evidence ID 绑定 schema、snapshot、document、version、locator、原文 excerpt；advisory summary、上游 ID、retrieved_at 不授身份。
- 规范 JSON 使用 UTF-8、稳定字段/集合顺序，明确 schema 版本；散列实现以 `contracts.py` 为准，不另造一套算法。
- 现行 `SourceLocator` 要求至少一组完整、1 起始且闭区间的页或行范围，以及 chunk ID、parser 名与版本；不支持只有自由字符串“某处”。字符 offset/bbox 若将来需要须扩展合同/ADR，不能假称现合同已有。
- 页范围是可核 locator，不是精确句子坐标。跨页 chunk 与原文保留完整，检验时按同 parser 的页/行映射核对；若无法复现明确标不可追溯。原 PDF 文字提取与视觉一致性另评估，不能以 hash 证明 PDF 被正确理解。[9]

### 4.2 审核 ledger 的权威与 digest

键域为 `(snapshot_id, question_id, evidence_id)`。只有 C 的交互命令可以追加 `ReviewDecision`；字段 `actor_kind="human"` 只是类型限制，不能证明真实人审；从 JSON 导入的“human”对象也不得自动进入权威账本。每个事件含当前范围、前一修订关联/操作去重引用和决定，具体 ledger envelope 待 C 的获批设计实现。

初始空账本可用正整数 revision 的 genesis（提案从 1 开始）与其 digest，**没有任何 accepted 事件**；这不是虚构人审。每次有效接受/排除/重置后 revision 单调递增，digest 由规范化权威 ledger 投影/链状态计算。相同操作重放应幂等拒绝，不重复推进；真正撤回再接受是两个不同事件，必须推进。

digest 用于检测“生成时看到哪一版”，不是签名、不是对本机恶意用户防篡改的证明。C 必须保存形成 digest 的规范输入与版本，读取时重算；不信调用方传来的 revision/digest。人审理由和内部 reviewer 引用属于本地受控数据，公共样例使用匿名角色代号，不写团队身份。

## 5. 单写者提交、崩溃与恢复

本地应用只有一个写者实例；第二个实例、第二个并发写命令遇锁就明确拒绝/只读，不假称支持多用户。UI 协调 A/C/E 写命令，模块仍各自拥有状态。

1. 写前校验合同/范围/权限；写到私有 staging，完成内容 hash/JSON 可读校验。
2. 写不可变记录的新路径，再原子切换小指针或记录完整性标记；不以原子 rename 宣称完成多个存储引擎全事务。磁盘满或权限错不前移成功状态。
3. 启动时只装载校验完整记录；孤儿 staging 不自动当成功，可保留隔离或由人工清理。schema/hash 不符进入只读 repair-needed。
4. 长模型调用不持写锁：D 捕获 snapshot/review 版本后请求；A/C 可在等待期提交变化。D 在回包后必须重读并判 stale。
5. 最终 freshness 检查与 E 报告提交在同一临界区；任何写入失败均不发“已发布”状态。界面可以显示未发布草稿，但要明确 draft/stale。
6. 重启不续接旧 `PQASession`。从持久请求账目重建只读进度；in-flight/unknown 请求不能自动 retry（可能已计费）。用户重新批准后建立新 request ID，保留前轮未解 usage。
7. 模型调用的全局预算、已发生尝试与剩余额度必须恢复，不能重启归零。无法准确恢复则冻结新外呼，等待人工核账。

## 6. 每次模型调用的七层上下文

这不是模型可自己改写的对话历史。每层由可信代码定位来源，原文与模型内容一律是资料，不成为更高权限消息。

| 顺序与层 | 所有者 / 内容 | 是否可压缩 |
|---|---|---|
| 1 身份 | 版本化 runtime prompt；“只根据获准资料提出草稿”的固定角色 | 不可压缩成另一个身份 |
| 2 站立约束 | 不授 accepted；不补证/用外部常识替代；只用 sent IDs；输出格式、拒答、无工具/提权；预算/deadline | 原样保留并在压缩后重注入 |
| 3 授权摘要 | 代码从 C 投影生成 snapshot、question、review revision/digest、sent IDs 与本轮别名映射 | 不由模型压缩；若不能容纳则减少证据并重建 |
| 4 资料 | 本轮获准原文、真实 locator、可选建议摘要；分隔并标“不可信资料” | 可删低优先证据**整单元**；引用白名单同步减少；不能改 excerpt 后仍冒称原文 |
| 5 历史 | 与本问题有关的用户/助手交互，去掉重复与旧失效证据 | 可作确定性摘要/裁剪；历史结论不加入 accepted |
| 6 恢复状态 | 阶段、已完成项、未决项、attempt/预算；不含私有思维链 | 可缩短描述，权威 IDs/计量保留；恢复需验证不是自报 |
| 7 当前问题 | 原始本轮任务、可选用户显式约束 | 不暗改意图；太长则拒绝并提示缩小 |

候选检索/摘要阶段尚无 accepted，不能伪称有“获准证据”：其授权摘要只写**获准处理的数据与操作范围**，输出仅候选、无发布权。回答阶段资料只取 C 的 current accepted。embedding 文本也受输入政策，不能批量发送所有原件来规避 cap。

## 7. 装配流水线、token 与重新注入

数值是**拟议工程默认，待学生计划审批**：输入硬 cap=**12,000 tokens**，压缩触发=**9,000**，输出上限=**2,000**，不是已测最优值。全部消息封装计入；`input + output reserve + provider 必要安全余量` 必须适配获批模型窗口。更小窗口取更严格限额，不为凑默认扩大窗口。`answer_length` 的“多少字”不是输出 API 硬上限。[5]

算法（每次发送前重新执行，不能仅在 UI 层算一次）：

1. **验证**：核当前 snapshot/ledger、来源可读、问题域、许可、deadline。拒绝模型自报 ID、未知 tokenizer、不可核 parser。
2. **去重**：优先 exact evidence ID；同 ID 不允许冲突原文。不同来源即便文字/摘要相同也保留独立身份，不用相似度合并授权。历史按消息 ID/内容版本去重，不丢不同人工决定。
3. **确定性优先级**：身份/站立限制/授权 IDs/当前问题优先且不可丢；资料按用户明确选择、再稳定排序，相关度仅作非权威排序；历史与恢复描述优先裁剪。固定 tie-break，保留排序政策版本。
4. **预算计数**：使用获批 provider/model 对应 tokenizer 的固定名称、包版本、编码数据 hash 和消息封装版本；工具 schema 若存在亦计入，但 MVP 不向模型开放运行工具。首次 tokenizer 数据下载不是免费/离线默认，须预先准备并校验缓存。
5. **压缩**：达到 9,000 开始，先去冗余历史，再压缩恢复描述，再按整单元删低优先资料，力求回到阈值以下；非关键层已最小时可处于 9,000–12,000，但须显式记录。默认不调用压缩模型。不可改变原文而仍沿用同一 excerpt 身份。
6. **重注入**：从版本化权威常量和当前 ledger **重新生成**身份/站立约束/授权摘要，而非相信压缩摘要“已保留”；核 constraint hash、IDs、question/snapshot/revision/digest。压缩文本中的“忽略限制”只作资料。
7. **最终装配**：按七层顺序组消息、固定模板、转义资料边界；sent 精确对应最终 payload 中存在的 evidence 单元。摘要与原文各标来源，不把摘要当逐字引文。
8. **最终硬门**：在 B transport 前再次计数与核 freshness/预算；>12,000、输入+输出不适合窗口、关键层缺失/被改、sent 映射不一致即拒绝。不得静默截断 system/授权表或仅在 UI 显示较小计数。
9. **响应对账**：记录实际 input/output/缓存/推理 usage（若提供）、finish reason、attempt/HTTP 数、费用已知性；超输出或 usage 不全停止新尝试，不能将其计为0。真实语义结果另评估。

上游默认 serializer 的 top-N/cutoff 并不表达这些规则（`settings.py:1191–1250`）；因此必须走 custom serializer 和网关最后一跳，不能只在 prompt 写数字。[5]

## 8. 表示缓存与版本失效

表示指纹至少覆盖：source version、parser 名/版本/配置、chunk 配置与规范化政策、embedding provider/model/维度/配置、摘要 prompt/model、tokenizer/装配政策版本。此指纹与 snapshot ID **分别记录**，防止“来源没变所以旧 embedding 一定可用”的误判。

只在指纹完全相等时复用表示；缺字段、模型未知或 schema 不兼容都视作 miss，必须在获批预算下重建。候选摘要缓存无审核权；新快照不自动迁移 accepted。旧版本读取以只读兼容层或副本迁移，禁止就地“更新”历史源、决定或报告。

## 9. 留存、删除与隐私

以下为默认**提案**，实际保留期限由学生和数据持有人批准，未经批准不自动删除来源或历史：

| 数据 | 提案保留与清理 | 隐私 / 导出政策 |
|---|---|---|
| 原件、快照、证据、ledger、报告 | 项目期间保留；终止后由持有人决定归档/删除；历史不由日常清缓存修改 | 默认仅本机；默认导出 ID/版本/locator 和必要短引文，不整篇 PDF |
| 可重建 embedding/解析/摘要 cache | 人工或明确策略清理；清理前确认非唯一原文/审核副本 | 可能包含敏感文本表示，不能当无隐私“缓存”公开 |
| requests / attempt 账目 | 至少保留到计费与请求状态核清；unknown 不清零 | 只留必要模型标识/usage/状态/摘要，不存 key/header/完整配置 |
| 普通诊断日志 | 提案滚动 30 日；实际启用前批准；不自动删除安全事故证据 | 白名单字段；禁止完整问题/原文/主机绝对路径/私有推理 |
| staging/quarantine | 不自动加载；人工核实后删除或留证 | 与正常导出隔离，界面不默认暴露 |

用户主动请求删除工作区/敏感记录是独立受控操作：显示会失去哪些追溯信息、得到明确确认后处理；可保留无敏感内容 tombstone 说明缺失，不偷偷改写旧报告为另一来源。MVP 不承诺法务级安全擦除或向量物理清除；如需此能力，重开 ADR 与 INV-05 的保留政策。

导出做字段白名单，不 dump 全配置/环境；异常信息和 URL query 也须脱敏。测试只用合成 sentinel，无真实凭据或成员身份。主机上能改文件的本地用户仍可能破坏数据，hash 检错不等于认证系统。

## Sources

[1] urn:sha256:6af742d3cbc0973b056a084ba54ff413a5885b1bb4d6a97b0b08b93f64f2ef7e — CS5351-2026-2027-project.pdf（本地原文提取，10页）
[3] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/docs.py — 固定基线 src/paperqa/docs.py
[4] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/types.py — 固定基线 src/paperqa/types.py
[5] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/settings.py — 固定基线 src/paperqa/settings.py
[9] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/readers.py — 固定基线 src/paperqa/readers.py
