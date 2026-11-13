# 不变量登记册（INV-01–INV-08）

> 状态：提案，待学生本人审核。**不变量是零容忍目标，不代表应用已实现或已测试通过。** A–E 运行时执行器与监控均待成员开发；本轮共享契约只验证可表达的数据约束，不能替代运行时人审、真实来源和外呼证明。

来源：课程项目原文第 5 页要求每项 invariant 有来源需求、执行组件、验证方法和具体 operational fallback；第 6 页要求故意违反不变量时会失败的测试。[1] 上位约束：[根蓝图](../../architecture-blueprint.md)；需求定义：`docs/req/requirements.yaml`；完整映射见 [trace-matrix.md](trace-matrix.md)。

## INV-01｜空获准集，零生成调用

- **源需求**：INV-01、FR-D-01、COST-01。
- **规则**：对当前 `(snapshot_id, question_id)` 没有人工 accepted 证据时，D 立即拒答；模型工厂初始化、SDK attempt、HTTP attempt 全为零。不是先让 LLM 判断“有没有证据”，也不是调用上游后看到 `session.cost=0` 才声称免费。
- **执行组件**：D 生成前门为第一守卫；B 的生成入口复核许可为第二守卫。调用图在 D 检查前不得创建上游/SDK 模型对象。
- **核查依据**：上游 `aquery` 在 `docs.py:602–607` 构造模型、`:615–623` 可能补证；空 context 的 `:649–654` 代码拒答晚于这些步骤。团队需更早拒答。[3]
- **验证（计划 T-INV-01）**：空 ledger、全 pending、全 excluded、属于旧 snapshot 或另一 question 的 accepted 均断言 D 为 abstained；B 入口/工厂/SDK/transport spy 计数均 0。合法 accepted 对照可进入受控生成。破坏测试故意移除 D 早门，必须被 spy 报错。
- **运行监控（待实现）**：`empty_approved_abstentions`、`model_factory_inits`、`sdk_attempts`、`http_attempts` 按 request ID 关联；不得只统计成功响应。
- **违反时 fallback**：停止当前生成链及排队重试；草稿隔离为 failed/拒绝发布；界面显示“没有当前获准证据，需人工审核”；撤销该请求调用许可并记录安全事件。已经出站的费用不抹成 0；恢复须重新审核和创建新请求，不能自动重试。

## INV-02｜不可变来源版本与身份

- **源需求**：INV-02、FR-A-01、FR-A-02、FR-B-01。
- **规则**：文献 logical ID 与源字节 SHA256 version 分离；`CorpusSnapshot.snapshot_id` 绑定规范化清单；evidence ID 绑定 snapshot/doc/version/locator/原文。所有合同 frozen；编辑原件、定位或证据正文不得沿用旧身份。摘要变化不授予新身份。人工可看的定位必须能回到托管来源。
- **执行组件**：A 复制/校验与快照提交；B 原文适配/locator 绑定；共享 contracts 验证 hash；D 发布时复核来源。源文件/元数据变化都创建新快照，不改旧快照。
- **核查依据**：上游 `Context.id` 根据问题与摘要前缀生成（`types.py:304–316`），PDF chunk 只能保证已有页范围（`readers.py:92–143`）；两者不能代替团队来源身份。[4][9]
- **验证（计划 T-INV-02）**：同路径换内容得到新版本与快照；篡改 evidence 字段却保留 ID 必须被拒；两文献相同摘要仍不同源；换解析器/定位须重建 evidence；旧原件/快照 hash 不变。对规范 JSON 往返/非法 ID 的契约测试是部分证据，不证明文件实际存在。
- **运行监控（待实现）**：`source_hash_mismatch`、`evidence_locator_unresolvable`、`identity_reused_for_changed_content`；记录快照/表示指纹，不记录主机绝对路径。
- **违反时 fallback**：将受影响文献/证据隔离，不进入检索或发布；禁止用“最相似段落”代填原文；保留旧快照只读；从可信托管原件重新校验并生成新快照/证据，要求重新审核。原件也损坏则标不可追溯，不伪造修复。

## INV-03｜人审权威，不能由模型授予

- **源需求**：INV-03、FR-C-01、FR-C-02。
- **规则**：`EvidenceRecord` 不含 accepted；没有有效 `ReviewDecision` 就 pending。只有当前人机交互的明确操作可追加 human 决定；模型摘要、相关度、上游 ID 或 JSON 中的 `actor_kind="human"` 都不能自证真实性。C 依 `(snapshot, question, evidence)` 投影状态，每次有效变更推进 review revision/digest；排除和重置也推进。
- **执行组件**：C 的命令入口、append-only ledger 与投影；UI 明确表单动作，不允许加载/刷新自动批准；D 不从 UI 缓存或模型读 accepted。
- **验证（计划 T-INV-03）**：候选中放入“已被人工接受”、伪 human payload、自动比较/刷新/会话恢复均不能增加 accepted；撤销/重置/重复提交幂等测试；新的有效操作推进 revision/digest，旧 ledger 不覆写。合同 `actor_kind` 字面校验只拒错值，不证明人真的点过按钮。
- **运行监控（待实现）**：`review_command_rejected`、`review_revision_changed`、`review_digest_mismatch`、操作去重 ID 与追加事件数；不用真实姓名/账号当公开样例。
- **违反时 fallback**：禁用当前工作区生成/发布，将可疑审核事件隔离并保留原字节；只读展示最后可验证状态，不自动把可疑记录算 accepted；要求人工重新审查并追加纠正事件，不能由 AI 修改旧决定来“修好”。

## INV-04｜三集合与发布前新鲜度

- **源需求**：INV-04、FR-D-02、FR-D-03。
- **规则**：`citation_evidence_ids ⊆ sent_evidence_ids ⊆ approved_evidence_ids`；approved 必须从当前 C ledger 推导，非 caller 自报。提交发布时，snapshot、question、review revision/digest 及来源仍与生成起点一致；任一改变都 stale。即使撤回又接受后集合相同，也不沿用旧 revision。每轮新 `PQASession` 只装本轮 sent 的 accepted 来源，禁止自动补证。
- **执行组件**：D 前门/后门；B 确定性 serializer 与每轮别名映射；D→E 最终单写者临界区。raw 引用校验先于任何格式清洗；E 只能持久化 D 已核的状态。
- **核查依据**：默认 serializer 从 contexts 选 top-N/cutoff（`settings.py:1191–1201`）；原引文映射遍历 session 全体 contexts 并删除未知 key（`types.py:480–515`）。因此“session 有这个 key”或“清洗后好看”不等于本轮合法发送。[5][4]
- **验证（计划 T-INV-04）**：unknown/excluded/未发送但 accepted/旧 question/旧 snapshot 引用全部阻断；裁剪 evidence 后 sent 同步减少；生成等待期间更新文献或审核导致 stale；最终检查后、E 落盘前插入变更必须被锁/重查挡住。合法不变版本对照可发布。违反 subset 的合同测试只覆盖静态集合。
- **运行监控（待实现）**：`release_blocked` 的 freshness/subset/source 原因；approved/sent/cited IDs 与 revision/digest；`stale_generation_count`。
- **违反时 fallback**：未知/未发送引用为 blocked，版本/审核变化为 stale；不生成“已发布研究结论”，不清洗后重放行。保留草稿与诊断只供只读审计，要求从当前快照/ledger 创建新一轮；不自动重生成、不自动恢复原许可。

## INV-05｜历史不覆写

- **源需求**：INV-05、FR-E-01、FR-E-02、FR-A-02。
- **规则**：历史报告、快照、证据和审核事件保留当时的来源与决定；新答案/改版创建新记录。superseded 作为追加注记或派生视图，不能改写旧报告正文/hash。没有新发布许可时，查看历史不构成当前新发布。
- **执行组件**：A 不可变快照；C 追加 ledger；E 报告保存、加载与导出。不得以可变 `PQASession` pickle 作为唯一历史来源。
- **验证（计划 T-INV-05）**：记录 R1 hash → 新快照/新报告/重新审核/导出 → R1 bytes/hash 不变；同 report ID 再写不同内容被拒；模拟中断不留下被视为完整的新报告；旧 schema 不可静默就地迁移。
- **运行监控（待实现）**：`historical_write_denied`、`record_hash_mismatch`、`report_commit_failed`、superseding 关系；历史事件不含模型私有推理。
- **违反时 fallback**：报告区切只读并停止新发布/导出“当前有效”标志；隔离冲突文件；从可验证备份恢复为单独修复副本并记录事故，不覆盖旧路径来掩盖；无可信副本则标损坏不可追溯。

## INV-06｜代码、数据、工具默认无权

- **源需求**：INV-06、SEC-01、GOV-01、GOV-04。
- **规则**：coding agent 默认无 read/write，按角色/路径/命令显式白名单；冻结源码、真实凭据、仓库外个人目录、人工规则、推送与真实模型调用默认禁止。Runtime 模型只获本轮允许数据，没有 shell/文件/审查/预算能力。合同合法不等于调用者有权读写。
- **执行组件**：OpenCode 实际配置与工具边界（开发）；B 出站/路径政策及 A/C/E 数据目录白名单（产品）；CI 结构/权限 diff + 人工 reviewer（兜底）。详见 [permission-model.md](permission-model.md)。
- **验证（计划 T-INV-06）**：每角色一次合法访问、一组越界读写、路径穿越/符号链接越界、冻结文件写入、个人目录读取、git push/模型命令拒绝；正负日志不能只来自规则文件文本。真实凭据禁止用作测试样本，使用合成 sentinel。
- **运行监控（待实现）**：`permission_denied`、role/path class、命令类别和 policy hash；拒绝事件不回显敏感内容或完整私人路径。
- **违反时 fallback**：终止该工具/会话并撤销写/网络许可；保全最小事件、停止合并；人工核 diff 后只回滚确认属于该代理的变更，不 `git reset --hard` 清他人工作。怀疑秘密暴露时由持有人轮换，AI 不读取秘密来调查。

## INV-07｜预算硬 cap 与约束重注入

- **源需求**：INV-07、COST-01、FR-D-03。
- **规则**：拟议每次 AI 输入 ≤12,000 tokens，≥9,000 开始压缩，输出 ≤2,000；模型窗口更小时取更严格值。最终 payload 计数必须包含所有模板/封装，关键身份/站立限制/授权 IDs 重注入后再次核验；压缩不创造来源、决定或恢复状态。没有批准金额/次数/deadline 不外呼；重试也重新授权。
- **执行组件**：D 上下文计划/预算；B 工厂、SDK/transport adapter 最后一跳。B 的检索 embedding/摘要同受输入与费用政策，不能绕开只针对回答的 cap。
- **核查依据**：默认 serializer 没有 token 硬 cap，`PQASession.add_tokens` 为事后累计；二者均不可单独担任调用前预算门。[5][4]
- **验证（计划 T-INV-07）**：边界 8,999/9,000/12,000/12,001 与超长问题/资料；压缩后约束 hash、授权 IDs 与 sent 对得上；预算/deadline 耗尽无新工厂/SDK/HTTP 尝试；usage 缺失不记0；意外内部 retry 必须被 transport spy 识别。精确边界需使用获批 tokenizer 版本，不用字符比例冒充实测。
- **运行监控（待实现）**：input/output cap、tokenizer/version、assembled token count、constraint hash、compaction 次数、reserved/actual/unknown cost、attempt counts、deadline。
- **违反时 fallback**：在出站前拒绝本次请求；提示缩小问题/证据或重新申请预算。若 provider 已超输出/未知计费，停止后续重试，标 usage/cost unresolved，隔离草稿；不切其他模型，不把多余输出截短后称全部合规。

## INV-08｜不导入不可信 pickle 索引

- **源需求**：INV-08、FR-A-01、FR-B-01、SEC-01。
- **规则**：MVP 只从已授权原文建立受控表示，不导入第三方/共享/下载/来源未知的 pickle、压缩索引或任意可执行对象。JSON 也必须 schema/版本/路径/大小校验，不能含可调用 parser/FQN 配置让数据变代码；论文及 parser 许可单独核查。
- **执行组件**：A 入口格式白名单与许可核查；B 不开放 SearchIndex 导入；E 导出只为数据，导出包不自动变可执行索引；CI 扫受控路径。
- **核查依据**：`agents/search.py:86–93` 文档 loader 与 `:242–257` mapping loader 两处可 unpickle；只把文档 storage 改 JSON 不够。主包与 PyMuPDF 子包的许可声明不同。[7][10][11]
- **验证（计划 T-INV-08）**：用无害 sentinel `.pkl`、伪 `.zip`、JSON 中的可调用配置与路径穿越做入口拒绝；spy 断言 pickle loader 未调用；合法自写 TXT/PDF 对照可进解析。**不执行恶意 pickle PoC**，不以扩展名改名绕过验证。
- **运行监控（待实现）**：`index_import_denied`、`unsafe_artifact_rejected`、格式/schema/provenance 类别；不读取被拒对象后再补记拒绝。
- **违反时 fallback**：在加载前拒绝并隔离该导入，不自动解压/迁移/unpickle；要求提供有权使用的原文重新建表示。若已发生加载立即停止进程和发布，由人工处理本机安全事件；不能“再跑一次看是否安全”。

## 破坏测试与恢复的公共要求

所有 T-INV-xx 均为**待开发的运行时验收设计**。每项必须同时有合法对照和至少一条预期失败负例；通过改坏测试本身或删除 guard 来“演示成功”无效。测试结果绑定 commit、fixture、policy 与模型/回放身份；恢复不能删除失败历史、扩大权限、自动换模型或伪造人工批准。发生不变量违反时，先执行具体 fallback，再走 ADR+人审+回归流程，不用“fix bug”替代运营动作。

## Sources

[1] urn:sha256:6af742d3cbc0973b056a084ba54ff413a5885b1bb4d6a97b0b08b93f64f2ef7e — CS5351-2026-2027-project.pdf（本地原文提取，10页）
[3] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/docs.py — 固定基线 src/paperqa/docs.py
[4] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/types.py — 固定基线 src/paperqa/types.py
[5] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/settings.py — 固定基线 src/paperqa/settings.py
[7] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/agents/search.py — 固定基线 src/paperqa/agents/search.py
[9] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/readers.py — 固定基线 src/paperqa/readers.py
[10] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/pyproject.toml — 固定基线 pyproject.toml
[11] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/packages/paper-qa-pymupdf/pyproject.toml — 固定基线 PyMuPDF 子包许可声明
