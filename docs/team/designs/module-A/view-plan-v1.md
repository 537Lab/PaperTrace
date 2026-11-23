# A 文库展示与页面接线：测试提案 v1（待独立审核）

日期：2026-11-23。此 PR 仅包含测试与设计，不包含 A view 实现或公共入口修改。

## 起点和职责

- A 实现 PR #17 的精确 HEAD 是 02357afe90f39b7bbd40ddd9adf9da50f5043a5f；核心 CorpusService 已获独立源码 Approve，但远端 static-analysis 和 regression 尚失败，不能合并。
- A 以前的 plan-v1.md 明确排除 A view 和公共装配。此前 PR #5 的测试批准不能替代本次新功能的测试批准。
- 新测试文件 test/offline/test_library_view.py 共 15 个合成测试。本提案 PR 以 feat/A-library-implementation 为 base；没有修改已批准 A 核心测试或业务源码，也不修改 C/D/E、共享契约、入口或 CI。
- E 交接包（PR #26，HEAD 871ecd0a456fa7cf99138a81171adc6ae7bbfa84）需要真实的历史 CorpusSnapshot 和原版本关联；A 不得用当前快照回填历史，也不负责判断全文导出许可。

## A 已实现、可直接提供的端口

1. CorpusService.current_snapshot()：返回原始真实 CorpusSnapshot，仅含 ready 文件。
2. CorpusService.read_source(snapshot_id=..., document_id=..., version_sha256=...)：严格校验历史快照成员及托管原文字节哈希；可以提供受控读取，**不等于允许 E 导出全文**。
3. CorpusService.freshness()：返回 (snapshot_id, corpus_revision)，供应用在生成/发布前核对；A 不负责 D 的发布门。
4. CorpusService.import_files(...)、attempts(document_id)：提供逐项状态、失败/历史信息；complete 属于 A batch，不得添加到冻结共享快照。

A→B 的摄取回执仍标记 PROPOSED_INTEGRATION，正式公共注入端口需 B 确认；现有 A 原文读取接口此前已进行合成 TXT + fake 模型隔离联调，不等于真实产品全流程通过。

## 新 A-only view 的拟议端口

待批准测试通过后，**单独实现** src/papertrace/library/view.py。它只依赖现有 CorpusService 和共享模型，不直接 import PaperQA2 或其他模块源码、不自造授权状态、不增加 Streamlit 或其他新依赖。公共 UI 以后只调用它的中立输入/命令：

- library_overview(service) 返回不可变 LibraryOverview：snapshot_id、corpus_revision、rows。行包含 document_id、title、source_name、version_sha256、status=ready；只从 current_snapshot/freshness 读取，不携带源字节或外部绝对路径；若两个 token 不一致，必须 fail closed。
- import_selected(service, paths, replacements=None) 返回 ImportFeedback：snapshot_id、complete、rows，每行包含 document_id、source_name、version_sha256、status、stage、reason_code。只将用户明确选择文件转交 A 服务，所有路径校验仍由服务完成；不扫描目录、吞错或替失败伪造成功。
- retry_selected(service, document_ids) 返回 ImportFeedback：只重试失败项，ready 项拒绝。
- remove_selected(service, document_ids) 和 restore_selected(...) 返回 LibraryOverview：通过已有 A 服务接口改变当前成员，保留历史，重新读取 snapshot/revision；不得静默重新摄取。

这些 view functions 是可测试的 A 自有展示/操作适配层，**不是**已运行的 Streamlit 页面。公共 Streamlit 入口、导航、依赖注入和 E 按钮属于后续独立的公共编排 PR，不应未经批准混入 A 代码。

## 验证与不变量

测试：test/offline/test_library_view.py（15 test nodes），真实 A CorpusService + synthetic TXT + fake B ingest；不造假的 A 结果，不调用模型或网络。

覆盖：空库、ready-only 页面行、实际快照 SHA/revision、批次部分失败、未选中和越界文件在整批授权时零摄取、重复导入不重复调用、显式失败重试、ready 重试拒绝、移除恢复不覆盖历史、同 logical ID 换版旧字节保留、未知对象 fail closed、页面不泄露原文或外部路径。映射 FR-A-01/02、INV-02/05/06、QA-01、SEC-01、COST-01。

独立隔离环境使用 E 合成包中的真实共享 contracts.py 已验证 Python 语法和 pytest collection：15 collected，0 collection error。由于该环境没有 A checkout，未实际执行 A 行为断言、Ruff/mypy、完整 regression 或远端 CI；**不得称行为测试通过**。当前 view.py 不存在，预期 14 个新行为用例首先达到 IMPLEMENTATION_MISSING 前置条件，这不是业务行为 RED 的证明。

## 人工审核与停止点

本轮测试及设计由 ChatGPT GPT-6 协助起草/发布，并不冒称 OpenCode 学生监督会话、D5 原始 transcript 或学生批准。仅使用合成数据，无真实私人论文、产品 LLM、模型调用或新依赖。

请未参与编写的另一位组员在 GitHub 审核**精确测试 HEAD**，如无问题正式 Approve。A 作者本人核实本方案/路径权限后，方可监督 OpenCode 从获批测试头的单独实现分支创建 A view，记录真实会话、模块检查、完整回归、独立源码审核。

本提案、原 A 实现 #17 与测试 #5 均保持开放，不合并 RED 测试、不自行 Approve、不改共享入口/其他模块。
