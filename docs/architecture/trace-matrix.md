# 需求 → 执行组件 → 测试/证据 → 运行监控

> 状态：证据已回填（2026-11-25 21:45 HKT）。六条过程性需求（INV-06、COST-01、SEC-01、GOV-01、GOV-03、GOV-04）已按真实证据标为 I；GOV-02 待真实语义评估证据，仍为 P。需求唯一定义是 [`docs/req/requirements.yaml`](../req/requirements.yaml)，本表只做追踪，不另改阈值。**“已定义测试”不是“已通过”；“合同能表示”不是“运行时已执行”。** A–E 均待成员开发；所有 runtime monitor 同样待开发。

课程项目第 5 页要求覆盖每项需求的 component/test/monitor；第 6 页规定结构、回归、行为三级验证和每项 fit criterion 的测试；第 10 页规定真正阻断门。[1] 上位设计：[根蓝图](../../architecture-blueprint.md)、[ADR-001](adr/001-architecture.md)、[不变量](invariants.md)。

## 1. 状态口径

- **C（contract）**：现有 `test/offline/test_contracts.py` 中已定义对应静态契约测试；本架构子任务未运行，真实结果以主控保存的执行回执为准。
- **G（governance）**：现有 `test/offline/test_gates.py` 有部分本地故障注入测试；不能外推为远端权限/分支保护或全部课程 gate 已通过。
- **P（planned）**：设计了测试意图与标识，业务或集成用例待开发，**没有测试结果**。所有 T-A/B/C/D/E、T-INV、T-COST/SEC/PERF 编号在此为计划 ID，不是假造已有 pytest node。
- 运行监控为上线后的观测合同；治理需求的 runtime 指 CI/工具会话/PR事件，不硬塞进产品模型日志。

## 2. 完整需求覆盖

| Requirement ID | 核心 fit criterion（沿 registry） | Enforcer / 权威执行者 | Test / 证据及状态 | Runtime monitor（待实现或待接线） |
|---|---|---|---|---|
| FR-A-01 | 合法/非法导入用例通过率=1；每文件状态与SHA版本分离 | A 导入协调/路径门；B 受控解析 | P T-A-01：合法TXT/PDF、坏/空/越界/重复/失败原因；C `test_document_identity_and_safe_ready_metadata` 仅字段部分 | `import_total/ready/failed`、`import_denied`、每批 `complete` |
| FR-A-02 | 被改写历史快照数=0 | A 快照提交与current指针；E 历史读取 | P T-A-02：同路径换内容/移除/元数据变更、hash不变的旧快照；C `test_snapshot_identity_is_canonical_and_round_trips` | `snapshot_changed`、`historical_write_denied`、manifest hash mismatch |
| FR-B-01 | 具合法来源的候选比例=1 | B 唯一 PaperQA2 适配；contracts ID/locator | P T-B-01：真实上游离线适配、原文定位；C `test_evidence_identity_excludes_advisory_summary_and_upstream_id`、`test_source_locator_rejects_missing_or_invalid_ranges` 仅合同 | `candidate_valid/invalid`、`locator_unresolvable`、representation fingerprint |
| FR-B-02 | 未报告的检索失败数=0 | B 异常分类/有界尝试 | P T-B-02：超时、空结果、429、摘要JSON错误、禁止静默切模型；不能拿固定stub当真实检索质量 | `retrieval_empty/failed`、error kind、attempt count、model switch denied |
| FR-C-01 | 未授权accepted决定=0；变更推进revision/digest | C human命令入口/追加ledger | P T-C-01：交互真实性、重放/伪造/排除/重置；C `test_review_rejects_nonhuman_or_unaccountable_decisions` 仅字段 | `review_command_rejected`、revision/digest、idempotency outcome |
| FR-C-02 | 两条证据比较所需字段比例=1 | C 比较视图；只读 B 来源数据 | P T-C-02：至少两条反向论点，来源/版本/locator/原文/摘要/理由可见；比较不改ledger | comparison fields missing、`comparison_viewed`、unexpected ledger writes |
| FR-D-01 | 空获准集生成尝试=0 | D 前门 + B 受控入口复核 | P T-D-01/T-INV-01：工厂/SDK/HTTP spies均0；C `test_answer_no_approved_evidence_is_empty_refusal` 仅拒答对象 | `empty_approved_abstention` + factory/SDK/HTTP attempts |
| FR-D-02 | 未授权或陈旧发布=0 | D raw引用门/freshness门 + D→E 临界区 | P T-D-02/T-INV-04：未知/未发送/排除/跨域引用，生成中与落盘前变化；C `test_answer_rejects_duplicate_or_noncurrent_scope`、`test_release_rejects_inappropriate_release_or_false_check_claims` 仅声明一致性 | released/blocked、`release_stale`、cited/sent/approved IDs、当前/捕获revision |
| FR-D-03 | 非受控外呼尝试=0 | D 调用计划；B factory/serializer/SDK/transport | P T-D-03：真 adapter+spy，自动补证/pre/post/metadata/Agent均被禁，raw映射不丢；静态导入检查只是部分 | unexpected outbound attempt、operation/model、context payload hash、attempt lineage |
| FR-E-01 | JSON/Markdown导出必需字段往返比例=1 | E 证据包manifest/格式化/加载 | P T-E-01：问题/快照/审核/approved/sent/cited/答案/发布结果/locator完整；跨会话/版本/中断；C 合同往返仅对象部分 | `export_completed/failed`、bundle missing fields、record integrity |
| FR-E-02 | 敏感或未许可导出字段=0 | E 白名单导出、历史注记；A 许可元数据 | P T-E-02：合成秘密/绝对路径/全文脱敏、旧报告hash不变；C portable source_name 仅字段 | `export_policy_denied`、`historical_write_denied`、superseded annotation |
| INV-01 | 空获准集生成尝试=0 | D 生成前门；B 工厂前门 | P T-INV-01：移除guard必须触发spy失败；C refusal测试不证明0请求 | empty-approved request → factory/SDK/HTTP counts=0 |
| INV-02 | 来源身份/版本不匹配=0 | A 源字节/快照；B locator；D 来源复核；contracts | P T-INV-02：原件损坏/同路径改版/定位失配；C snapshot/evidence identity与frozen测试部分 | source/evidence hash mismatch、locator failure、snapshot identity |
| INV-03 | AI授予审核权限=0 | C ledger唯一写入口；D只消费投影 | P T-INV-03：模型自称human/accepted、比较/恢复/刷新都不授权；C human-only/forbidden-field测试部分 | accepted事件来源、review revision/digest、command rejected |
| INV-04 | 已发布非法引用=0 | D 三集合/freshness，B sent日志与别名映射，E最终提交 | P T-INV-04：裁剪后旧key、同集不同revision、生成/提交竞态；C subset/ReleaseDecision显式checks部分 | subset violation、`release_stale`、publish conflict、完整scope IDs |
| INV-05 | 被覆盖历史记录=0 | A/C/E 不可变/追加存储 | P T-INV-05：写相同ID不同字节、崩溃、superseded不改旧正文；C frozen只验证对象非磁盘 | history hash mismatch、write denied、state commit failure |
| INV-06 | 越权工具效果=0 | 实际OpenCode工具/权限层、路径门、CI + 人审 | **I** `.opencode/permissions.jsonc` 设 `default_read: deny-except-explicit-or-ask`、`default_write: deny-except-owned-build-scope` 并按角色白名单；负例证据 `artifacts/verification/opencode-config-red.txt`；测试 `test/offline/test_opencode_configuration.py`、`test/offline/test_opencode_workflow.py`；G `test_architecture_and_frozen_tree_faults` | tool permission denied、out-of-scope diff、role/policy version |
| INV-07 | 上下文预算或重注入违反=0 | D budget/assembler；B最后出站跳 | P T-INV-07：8999/9000/12000/12001、约束被压缩、未知usage、耗尽重试；不是字数近似 | final tokens/caps/tokenizer、constraint hash、attempt/cost/deadline |
| INV-08 | 不可信索引加载=0 | A格式门；B不开放SearchIndex导入；E数据导出 | P T-INV-08：无害pkl/zip/可执行配置拒绝且loader spy=0；禁止恶意PoC | `index_import_denied`、unsafe format/schema/provenance |
| QA-01 | 合同JSON往返及非法输入通过率=1 | 五种共享模型 + 嵌套DocumentVersion/SourceLocator；contracts | C `test_all_main_models_share_closed_frozen_versioned_schema`、`test_published_json_schemas_match_models`、`test_handwritten_synthetic_fixtures_round_trip`、`test_json_schema_is_valid_and_accepts_synthetic_record`；执行回执由主控提供 | schema version、validation failures、contract drift；产品接线待开发 |
| PERF-01 | 合成小样例100次合同往返总耗时≤2秒 | 仅契约基准执行器，不是PaperQA运行性能 | P T-PERF-01：独立计时，记录硬件/Python/Pydantic/样例/循环/环境；需真实回执，不从测试文件推断达标 | benchmark wall time/environment/fixture version；不作为在线SLA |
| COST-01 | 产品初始化验证/离线测试的模型请求=0；live需独立批准 | 无外呼契约导入；测试网络门；B 受控调用许可 | **I** 离线套件以 `--disable-socket` 运行；真实评估需独立授权 review（#85 上 7 条 `Evaluation authorization` 记录）；2026-11-25 两次派发在 preflight/collect 校验阶段终止，0 次模型调用；编码助手用量另记 `docs/ai-use-log.yaml` | factory/SDK/HTTP counts、reserved/actual/unknown usage、permission scope |
| SEC-01 | 交付中真实秘密/成员身份字段=0 | 受控路径内容扫描 + 人工审阅；E 导出门 | **I** 2026-11-25 21:42 HKT 对 main 全部 430 个跟踪文件按 `sk-…`、`AKIA…`、`ghp_…`、`BEGIN * PRIVATE KEY`、`xox?-…` 扫描，fixtures 之外命中 0；G `test_contract_surface_and_scoped_secret_faults` 合成 sentinel 部分 | secret/identity scan findings（不回显秘密）、export denied |
| GOV-01 | 未事前批准实现合并=0 | 可信人审时序；CI approval gate | **I** 五对已核「批准早于实现 PR 创建」：#49 03:54Z→#50 04:39Z、#67 03:20Z→#72 04:52Z、#73 06:47Z→#80 07:23Z、#84 08:46Z→#85 09:12Z、#55 16:09Z→#86 次日09:34Z；G `test_approval_and_semantic_reports_cannot_self_authorize` | trusted approval absent/stale、implementation-before-approval、merge blocked |
| GOV-02 | 未验prompt/model生产合并=0；三级验证 | 结构/回归/语义gate + required checks + reviewer | G `test_real_lint_type_dependency_and_timeout_faults`、`test_regression_executes_every_team_offline_test_and_rejects_fail_skip_empty`；P 全prior/真实live语义/远端保护；缺授权即blocked | suite IDs/result/skip/xfail、eval identity/threshold、required-check blocking |
| GOV-03 | code/prompt PR缺新AI日志=0 | diff驱动AI-use-log gate；PR memo/bug/debt/transcript人审 | **I** `docs/ai-use-log.yaml` 109 条；`ai-log` 是每个代码/prompt PR 的必需检查（#83/#85/#92 近期均 PASS）；五份标注会话已交付，仓库 `transcripts/` 目前仅 README，其余随 ZIP 交付 | changed-code/prompt with log-update、memo verdict、transcript provenance |
| GOV-04 | 未批安全变更/过时规则=0 | 安全路径检查、ADR + 学生review、规则版本/需求关联 | **I** `docs/architecture/adr/001-architecture.md`；安全路径 PR 正文均含 `Architecture decision:` 行（#50/#70/#72/#80/#83/#85/#86/#92 抽查 8/8）；需求登记处随 ADR-001 修订同步 | safety diff without approved ADR、rules age/sprint、requirement-policy mismatch |

## 3. 计划测试如何落盘

| 计划 ID | 目标测试文件（批准计划后才建） | 正向与负向最少要求 |
|---|---|---|
| T-A-01/02 | `test/offline/test_library.py` | 合法导入/新快照；坏文件、越界、同路径改版、重复/删除、历史不变 |
| T-B-01/02 | `test/offline/test_retrieval.py` | 固定上游离线适配+source locator；空/异常/JSON/无许可与未知ID |
| T-C-01/02 | `test/offline/test_review.py` | 明确人工命令与比较；伪human/重放/恢复/旧scope不获准 |
| T-D-01/02/03 | `test/offline/test_answer.py` | 合法获准→受控草稿→发布；空集、bad引用、出站旁路、stale竞态 |
| T-E-01/02 | `test/offline/test_reports.py` | 合法新报告/往返；覆写、损坏、半写、导出秘密/未许可内容 |
| T-INV-01…08 | 上述模块tests + 经批准的新集成测试精确路径 | 每个INV有合法对照、破坏后会失败的负例；不能仅断言文字包含某词 |
| T-PERF/COST/SEC | 依获批验证计划添加独立脚本/测试 | 真计时、无外连证据、仅合成敏感sentinel；不读取私人目录 |
| 真实语义评测 | `test/live/` 与固定evaluation数据/报告合同 | 批准provider/model/数据/费用后真跑；保存真实标识、usage、结果与阈值，不mock替代 |

上述是目标落点，不隐含对实现或路径写权限的审批；精确文件白名单按权限文档另审。

## 4. 不能互相替代的证据

1. Pydantic 拒绝 `actor_kind="model"` 不能证明一条 `human` 记录真的来自人；C 的交互/账本测试仍必须做。
2. `AnswerDraft` 的 subset 验证不能证明 approved 来自当前 ledger，也不能证明 sent 真在 HTTP payload；D/B 集成测试必须观察真正边界。
3. frozen 对象不等于磁盘历史不覆写；manifest/字节hash与故障注入仍必须做。
4. 假模型可以证明确定性守卫，不能证明科学质量；上游已有引用/摘要能力也不自动成为团队新增贡献。
5. 本地 schema/lint/log 测试通过不等于完整回归、真实语义评测或 GitHub 保护已启用。六类 gate 分别报告真实状态，缺一项不可统称全部完成。

需求变更时，先更 registry，再同步本矩阵/ADR/不变量/权限/状态/政策和测试；规则须在一 sprint 内跟随人审需求更新。测试输出需保留真实 commit/版本与执行范围，不把这里的 P 编号改成 PASS 代替开发。

## Sources

[1] urn:sha256:6af742d3cbc0973b056a084ba54ff413a5885b1bb4d6a97b0b08b93f64f2ef7e — CS5351-2026-2027-project.pdf（本地原文提取，10页）
