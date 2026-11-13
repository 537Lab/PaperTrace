# 风险与未确认事项

> 状态：真实已知边界 + 拟议应对，**不是已经发生的事故清单，也不是风险已关闭证明**。责任用模块/过程角色表示，不预设个人职务。学生批准前不得把风险表当作“已接受风险”。

| Risk ID | 假设 / 风险与证据等级 | 触发复审条件 | 具体行动与owner | 关闭需要什么 |
|---|---|---|---|---|
| R-01 | B薄适配可覆盖PaperQA2全部声称受控入口；当前仅源码依据 | 工厂/SDK/HTTP spy看到未列尝试；隐藏retry或预处理绕行 | B立即禁该路径、D停止发布；收窄入口或重开ADR | 每条调用/禁用矩阵的真实正负探针，非只测answer |
| R-02 | 人审字段可被JSON伪造；合同human字面值不证明真实性 | 非UI人工命令能进入ledger；刷新/恢复自动accepted | C隔离事件、工作区只读、要求真实重新审核 | C交互/重放/ledger测试 + D不信caller投影 |
| R-03 | freshness检查与落盘之间可能TOCTOU | A/C在检查后更新而E仍保存为released | D→E单写者临界区重查；旧结果stale | 可控调度/故障注入覆盖生成中和提交前两窗口 |
| R-04 | SHA与locator只能检身份/定位，不能证明PDF理解或科学真 | 同parser不能回原文；人工发现表格/扫描/语义错误 | B阻断不可定位证据；C核原文；D显示不确定 | 固定parser/定位用例 + 人工质量rubric；真实语义评测另批 |
| R-05 | 本地文件只适合单写者，非多用户数据库 | 第二写者、锁异常、崩溃半写、磁盘满 | A/C/E拒写或只读，保留staging，不伪造提交成功 | 锁/半写/恢复/历史hash测试，必要时新ADR |
| R-06 | 默认“本地PDF”仍可能触发模型/metadata/enrichment；源码已证实 | 调入默认aadd/aquery、factory初始化发生网络 | B显式配置/受控对象，默认关所有模型；COST门失败即停 | 工厂/SDK/transport分层计量、许可前0尝试 |
| R-07 | 外部SDK retry、usage、价格与取消行为未核全 | HTTP数多于reservation、缺usage、provider越上限 | B冻结新增请求、标unknown账目，不自动重试/换模型 | 获批provider/model协议测试和账目对齐，不靠session.cost |
| R-08 | 12k/9k/2k是工程提案，不是实测最优 | 获批模型窗口/封装不适配，关键层自身太大 | D取更严格限额或拒绝，B最后payload再计数 | tokenizer固定、边界与重注入测试、学生批准 |
| R-09 | 第三方索引pickle加载有执行风险，mapping另有loader；源码已证实路径 | 导入共享/下载索引或自动解包迁移需求 | A/B在loader前拒绝，要求原文；不跑恶意PoC | 拒绝负测+loader spy；若要格式迁移另ADR |
| R-10 | 编码权限规则未必等于真实执行边界 | shell/插件绕过路径、写冻结源、读取仓外sentinel | 停会话、核diff、撤权；配置owner做当前版本正负验证 | OpenCode实际版本/schema/规则加载和无害探针回执，不能文档自证 |
| R-11 | 文献原文、问题、配置或日志可能含秘密/版权数据 | 导出出现主机路径/全文/真实身份/配置秘密 | E白名单阻断导出；最小事件不回显秘密；持有人处理 | 合成sentinel+受控路径扫描+许可逐项核查 |
| R-12 | 主包Apache不覆盖全部parser/论文许可；源码声明不同 | 准备安装PyMuPDF/Docling/模型包、公开分发PDF | 依赖owner/学生先核许可；MVP固定最小文本parser | dependency与数据许可清单，不用根license一概放行 |
| R-13 | 完整prior suites需要额外依赖/live预算 | 只跑团队tests却声称全回归，skip/xfail混算 | Verify保留完整清单和BLOCKED；不能自行删课程门 | 所有既往suite真实执行/认可范围及教师解释 |
| R-14 | prompt/model变化的真实语义评测尚未完成 | 拿stub/旧cassette/自填PASS当新语义结果 | GOV-02阻断生产/合并，申请明确预算与固定eval | 模型/数据/prompt/usage/阈值身份完整真实回执 |
| R-15 | GitHub required checks/分支保护需管理员 | 本地脚本通过就宣传已保护或自行push | 不作远端完成声明；请求明确私有仓库owner/权限 | 回读精确规则、失败PR无法合并、合法对照 |
| R-16 | 课程D5数量/“from scratch”与基线复用有歧义 | 正式开发/提交前仍无教师口径 | 学生核原文/最新通知，不让AI选方便版本 | 原文第2/6页差异的真实澄清记录 |
| R-17 | 指定OpenCode与本轮初始化工具不同 | 将初始化文档/辅助AI记录改名作D5 | 保留真实AI-use披露；未来由学生监督真实OpenCode会话 | 教学介绍第5/20页适用性核对和真实原始transcript |
| R-18 | 截止只见Week13，D6最终身份/排版与本轮匿名不同 | 填确切日、学生身份、贡献或反思但无事实 | 学生核当前通知，最终提交本人补真实身份/反思；本轮不造 | Week13确切截止与D6格式/真实贡献确认 |
| R-19 | 新快照/重审增加操作量，不能靠自动迁移省事 | 计划把旧accepted复制新snapshot或复用旧session | C不迁移授权，D新轮；需要优化先提显式人工迁移流程 | 真实用户需求与新ledger操作测试，ADR审批 |
| R-20 | 各角色并行编写文件时产生合同/需求/文档漂移 | 字段、INV编号、模块路径、状态枚举不一致 | 集成按contracts和registry核对；安全差异先停，不各自修一套 | 跨文档检查、单一canonical、精确commit/版本验证 |

## 来源与课程待确认点

R-01/06/07 来自 `docs.py:171–311,360–386,492–624`、`core.py:233–400` 与 `types.py:414–433`；这些是静态调用点，不是已测损失。[3][6][4] R-09 的两个 loader 见 `agents/search.py:86–93,242–257`。[7]

R-12 的许可差异由根与PyMuPDF子包的声明支撑，但尚不是全部依赖法务审查。[10][11]

课程项目第 2/6 页 D5、5/9 页蓝图布局、6–7 页 D6、10 页六类 gate 需要区分事实和解释；教学介绍第 5/20 页 OpenCode、第 7 页 Week13、第 23 页视频/密钥要求都已读原文，未据此猜截止或伪造审批。[1][2]

## 使用政策

触发就执行相应停止/隔离/拒绝动作，再形成ADR或验证任务；表中未标任何风险已关闭。不使用未经真实核验的“概率5%、影响10分”加权数字。每个风险的消除证据应写入 [evaluation-logbook.md](evaluation-logbook.md)，由真实执行与学生审核决定是否关闭，不由模型宣称风险已接受。

## Sources

[1] urn:sha256:6af742d3cbc0973b056a084ba54ff413a5885b1bb4d6a97b0b08b93f64f2ef7e — CS5351-2026-2027-project.pdf（本地原文提取，10页）
[2] urn:sha256:16d399f7ca14e0c49dea382cec3893bbee8f589edcaee5131f10fad257d3acb5 — cs5351-2026-2027-introduction.pdf（本地原文提取，27页）
[3] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/docs.py — 固定基线 src/paperqa/docs.py
[4] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/types.py — 固定基线 src/paperqa/types.py
[6] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/core.py — 固定基线 src/paperqa/core.py
[7] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/agents/search.py — 固定基线 src/paperqa/agents/search.py
[10] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/pyproject.toml — 固定基线 pyproject.toml
[11] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/packages/paper-qa-pymupdf/pyproject.toml — 固定基线 PyMuPDF 子包许可声明
