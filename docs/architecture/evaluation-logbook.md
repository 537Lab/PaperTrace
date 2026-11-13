# 架构证据日志

> 这份日志区分**读到的事实、设计推断、计划验收与真实执行**。不代替 D5 原始 OpenCode 会话、学生干预/批准、逐PR memo 或 D6 贡献记录。课程项目第 5 页把 evaluation logbook 列为 optional，本轮提供以方便审计；不伪称已经做过完整运行实验。[1]

## 1. 本轮实际材料与结果

| Evidence ID | 实际工作 / 可复核定位 | 允许结论 | 不允许升级成 |
|---|---|---|---|
| EV-ARCH-01 | 完整读取课程 `project.txt`（PDF页1–10）与 `introduction.txt`（PDF页1–27）；来源摘要见source-register | 架构和待确认点依据课程原文，引用使用PDF页码 | 未实时核Canvas更新，不给确切截止日或复用许可保证 |
| EV-ARCH-02 | 只读 `git rev-parse HEAD` 返回 `c692d0dfeac4a0296599f7fe21a253a58b7ac12a`；当时 `git diff --name-only <baseline> -- src/paperqa packages tests` 无输出 | 架构起草开始时核心/包/上游测试未见相对基线差异 | 不代表整个初始化最终diff、依赖兼容或模型运行 |
| EV-ARCH-03 | 直接读固定 `docs.py:156–721`、`types.py:155–526`、`settings.py`指定段、`core.py:227–400`、`readers.py:92–143`、SearchIndex两个loader、Agent控制链 | 基线调用点、Context身份、sent缺口、隐式调用和pickle范围可定位 | 不是本机PaperQA2集成测试、漏洞利用或供应链完整审计 |
| EV-ARCH-04 | 读取解包审计Markdown：01–06及最终scope/technical review；没有改审计原件 | 复用既有分析输入，保留候选/范围/证据等级教训 | 审计历史窄探针/上游CI不是本轮新运行 |
| EV-ARCH-05 | 读取共享contracts与registry及已有contract/gate测试定义，对齐字段、INV与需求ID | 可核对架构和当前初始化合同语义；完整trace覆盖目标明确 | 测试定义存在不等于已运行或A–E已实现 |
| EV-ARCH-06 | 根canonical、指向页及本目录架构Markdown由本任务创建；文件工具返回verified | 文档真实落盘、非只有计划 | 文档创建不等于学生批准、OpenCode强制权限或远端门禁 |

源码与审计引用见 [source-register.md](source-register.md)。本轮没有 import/运行 `paperqa`、没有运行模型/embedding/metadata API、没有读取凭据、没有改原课程/审计文件、没有git commit/push；这是本架构子任务的动作范围，不冒充对其他并行任务的全局网络审计。

## 2. 设计结论与证据缺口

| 结论 | 当前等级 | 下一项验收 / 停止条件 |
|---|---|---|
| 五模块薄适配比重写/多用户服务更适合当前范围 | 定性设计推断；非测量 | 学生审核ADR，模块计划/测试事前批准 |
| 人审ledger+来源hash+freshness能约束定义好的发布边界 | 可检验设计，待实现 | T-INV-01…08的运行时正负例，不能只看Pydantic |
| 12k/9k/2k可作为工程默认 | 未批准的提案；非实测最优 | 固定tokenizer边界/重注入；模型窗口/输出参数真实核对 |
| B网关覆盖工厂/SDK/HTTP与所有表示调用 | 设计合同，外部依赖内部未核 | 调用清单逐项spy；发现旁路就保持该路径关闭 |
| 本地单写者文件存储可用于MVP | 设计假设 | 半写/锁/竞态/恢复测试；失败则收窄或重开持久化ADR |
| 历史可定位且默认匿名安全导出 | 设计合同 | 原件hash/locator/导出脱敏与许可测试；不能猜论文许可 |
| 编码角色路径表能落入OpenCode2配置 | 主控工具事实+计划约束；本子任务未执行权限探针 | 实际版本/schema/加载与允许/拒绝回执，shell旁路亦核 |

## 3. 真实模型与性能结果：不填假数据

| 项目 | 本文状态 | 为什么不能写PASS |
|---|---|---|
| PaperQA2完整依赖安装/底层API真实离线集成 | 本架构子任务未执行 | 源码支持Python3.14不等于全部native/parser运行兼容 |
| 新旧方案延迟/token/成本改善 | **未测量** | 无相同数据/模型/硬件的真实对照，不填百分比 |
| PERF-01 合同100次往返≤2秒 | 以主控真实基准回执为准；本文未代跑 | 不从设计阈值或单测存在推断达标，也不外推为RAG速度 |
| 真实embedding/summary/answer及固定语义eval | **未授权/未执行本子任务** | 需provider/model/数据/金额与请求数批准；stub只测策略 |
| D5 OpenCode原始监督会话与学生干预 | **未产生于本子任务** | 不能从架构起草日志合成学生会话或审批 |
| 六类GitHub gate全部远端阻断及分支保护 | **本子任务未验证** | 本地脚本或YAML不能替代required checks与失败PR证据 |

## 4. 证据追加规则

新的真实验证条目必须含：执行范围、命令/工具、源码commit或文件版本、fixture/eval版本、模型/回放身份、环境、真实输出定位、失败/skip/unknown、结论与不能外推范围。涉及模型还需实际provider/model、attempt/usage/finish reason和费用已知性；涉及审批需可信人审来源，不自填approved。

文档校验、契约测试、上游离线集成、真实语义eval、远端门禁各自一条证据链，不互相替代。修订后按新版本核验，保留旧失败，不把计划改写成过去完成时。

## 5. 本次文档校验记录

已执行一次必要的文档一致性检查：13份Markdown均非空；相对链接与围栏检查无错误；27项registry需求对应27行trace；INV-01至08齐全；13个来源编号均可解析、Sources映射一致；未发现私人绝对路径。只读Git检查返回固定baseline，`src/paperqa`、`packages`、原`tests`相对baseline变更路径为空。检查进程退出码0、errors为空。该结果仅覆盖文档/追踪/引用/链接与冻结路径，不代表应用运行、模型评测、实际OpenCode权限或远端门禁已通过。

## Sources

[1] urn:sha256:6af742d3cbc0973b056a084ba54ff413a5885b1bb4d6a97b0b08b93f64f2ef7e — CS5351-2026-2027-project.pdf（本地原文提取，10页）
