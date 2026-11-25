# E 页面接线精确计划

状态：学生已在本聊天回复“批准”，授权本轮测试准备；具体测试head仍需非作者独立批准后才可写源码。
基线：PR26，871ecd0a456fa7cf99138a81171adc6ae7bbfa84，已有独立Approve，88项E测试通过。

## 要交付的实际操作

用户可在E页面点击“保存研究记录”，随后查看历史、打开记录并下载默认隐藏原文的
JSON/Markdown。blocked显示“发布受阻”，PUBLICATION_COMMIT_UNAVAILABLE显示明确原因。
拒答、失败、零证据记录照常保留；页面不授予发布权。

当前main及打开的PR没有公共app.py或公共导航。集成合同由A的首个装配PR负责公共入口。
本轮先交付同一个可注入E页面组件及本地可点击合成预览；公共入口未来直接调用该组件。
不创建第二套公共导航，不改其他成员源码。

## 精确范围与接口

测试准备：追加test/offline/test_reports.py，保留现有88项；必要时新增
test/fixtures/reports/明确标注synthetic的页面fixture；新设计记录
docs/team/designs/module-E/page-wiring-plan.md；如实追加docs/ai-use-log.yaml。

新测试具体head独立获批后，才允许OpenCode新增：
- src/papertrace/reports/view.py
- src/papertrace/reports/preview.py

页面入口拟为：
render_reports_panel(ui, *, store, pending_record=None, current_snapshot_id=None, input_error=None)

ui由调用方注入，view不导入Streamlit；store为E真实HistoryStore；pending_record为已经
构造的ResearchRecord。公共编排负责从C/D收集原始数据及构造待保存包。
input_error仅接受中立的输入不可用/审核不可用信号，页面不显示异常原文。

本地preview通过现有Streamlit运行，只绑定127.0.0.1，明确提示合成模式，要求显式
synthetic输入和历史输出目录，不调用模型、不读私人论文、不签发真实导出许可。
监督侧已确认本机可找到Streamlit；这不代表项目锁文件已声明该依赖。公共应用最终
依赖由公共装配负责人决定，本轮不安装包、不修改依赖或冻结文件。

## 操作与安全语义

需求映射：FR-E-01/02、INV-02/04/05/08、SEC-01、QA-01。
可测验收是用户点击后真实保存和重开；历史选中项与两种下载正文一致；
未经点击、输入不可用、敏感元数据或磁盘失败均不得产生新归档；
换版不改历史字节，默认页面及下载都不暴露摘录和嵌套绝对路径。

1. 页面刷新、切换历史、下载不会保存；只有用户明确点保存才调用save。
2. 无待保存记录或输入报告审核错误时禁止归档，不编造零审核来代替损坏账本。
3. 保存仍经过E的准确字节校验。污染元数据、冲突或写失败显示固定安全提示，不显示本机路径。
4. 相同UUID不重复归档或覆盖；页面不在每次刷新自动生成新UUID。
5. 历史列表使用list_records，选定记录通过load重新读取，详情与下载绑定同一ID。
6. 存储接口报告失败或选中记录加载失败时明确提示，不静默展示别的记录。
   本轮不重定义既有list_records对非法条目的处理，也不额外扫描私人目录。
7. 页面显示render_record的脱敏投影，默认不显示/下载证据原文，不提供“勾选即授权”的入口。
8. released仅表示记录中D的声明；blocked、failed、abstained不得升级为released。
9. 当前快照变化只展示superseded，旧记录原始字节不变。
10. session_state仅缓存显示选择，不能充当审核、快照、发布或许可的权威。

## 先测试后实现

使用真实E模型/HistoryStore和UI double验证：未点击不写；点击保存/重开；重复点击冲突；
无输入/输入错误不写；blocked原因标签；零审核拒答/失败；released不重新授权；历史切换
与下载ID一致；superseded不覆盖；默认无摘录、嵌套路径无泄漏；污染元数据及写失败拒绝；
安全错误提示不泄漏异常。测试模块缺view时仍可收集，缺实现以明确断言报告，不skip。

测试PR从feat/E-metadata-repair创建，并以该分支为目标。
后续实现从独立获批的测试head创建另一个实现分支，目标仍为feat/E-metadata-repair，
不是以测试分支为目标；保持获批测试/计划blob不变，避免目标分支不一致的门禁错误。
PR26及旧测试PR8的head不改动，所有PR保持开放、不合并。

实现后运行全部E测试、相关团队离线回归、Ruff/mypy/schema/披露检查；如果已有
Streamlit AppTest可用则用它验证实际按钮，再启动仅本地预览供用户点击。
完整C/B/D流水线、真实许可和真实模型质量仍单独验收，不能以合成预览代替。

## 记录与停止条件

本轮概念Plan由OpenCode papertrace-plan会话ses_df89e39c8ffegMIJZhG8PDH1AQ产生。
其读取reports源码被权限拒绝，未重试放权；随后仅依据任务描述输出概念计划。
监督侧已读取相关E接口与集成合同，并纠正分支目标和错误处理边界，形成本精确版本。
不冒称Plan会话完成了源码检查。原始输出保留于Team/E-opencode-page-plan.jsonl。

产品模型调用为0，无新依赖、无公共入口/共享契约/规则变更。权限拒绝、需要越界、
缺实际输入或缺独立测试批准时停止相应操作，记录BLOCKED/NOT_RUN，不编造批准。

先由学生确认本计划，然后准备并提交测试；再由非作者批准具体测试head，最后才实现。
依据Prompt.md：“只给计划，然后停止并等待学生本人批准本次精确计划。”

## 本轮测试提案与复核结果（2026-11-23）

保留原88项测试，新增29项参数展开后的用例，共117项。
最终本地结果：89 passed / 28 failed / 0 skipped，无收集错误。
89项包括原88项和一项独立于view的样例校验；28项全部在缺少
papertrace.reports.view的明确可用性断言处失败，页面行为断言尚未执行。
不将这些结果称为页面功能通过。Ruff、E源码mypy、schema和ai-log通过。

UI double固定保存按钮文字为“保存研究记录”，历史selectbox提供record_id字符串，
可通过format_func显示友好名称；download_button接收实际JSON和Markdown正文。
历史顺序不写死，按实际选项确定预期记录。使用真实HistoryStore，不模拟保存成功。
绝对路径的独特片段同时覆盖结构化展示及下载；普通无路径文本不要求脱敏。
预览的真实Streamlit按钮与loopback检查在获批后的实现阶段运行，本提案不声称已完成。

其余团队离线测试单独运行：280 passed / 74 failed / 2 skipped。
失败按文件：ci_events=4、contracts=1、full_regression=16、gate_evidence=1、
gates=6、opencode_configuration=1、review=24、semantic_evidence=21。
其中含Windows无fcntl/WSL bash不可用、换行敏感fixture及子进程验证环境问题；
这些属于共享回归待诊断/环境阻塞，不属于28项页面预期RED，也不代表全量验收通过。
上游完整回归、真实模型、真实论文导出许可与公共入口端到端验收本轮NOT_RUN。

复核命令（沿用获准的离线验证环境）：
```text
python -m pytest -c papertrace.pytest.ini -p pytest_socket test/offline/test_reports.py -q
python -m ruff check --config papertrace.ruff.toml test/offline/test_reports.py
python -m mypy --config-file mypy.ini src/papertrace/reports
python scripts/gates.py --gate schema --base 871ecd0a456fa7cf99138a81171adc6ae7bbfa84
python scripts/gates.py --gate ai-log --base 871ecd0a456fa7cf99138a81171adc6ae7bbfa84
```
