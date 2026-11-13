# 技术债登记（D4）

以下为真实已知缺口，不是已发生生产故障。状态均OPEN；关闭须附测试与批准证据。

| ID/类别 | 债务 | 责任功能/关闭条件 |
|---|---|---|
| DEBT-01 evaluation debt | 无真实模型连通及语义基线 | B/D：批准provider/model/文献/预算，真实固定评估及usage回执 |
| DEBT-02 guardrail debt | GitHub保护和可信测试事前批准未部署 | 全组/获授权管理员：回读规则，六类失败PR+合法对照 |
| DEBT-03 hidden dependencies | 未安装/执行完整PaperQA2及其解析extra测试环境 | B：单独锁定环境，完整prior suite结果及skip/failure清单 |
| DEBT-04 prompt rot | 运行prompt只为架构契约初稿，未有真实质量验证 | D：真实对照与阈值、每次模型/prompt变更重跑 |
| DEBT-05 hallucinated dependencies | 需防止Agent添加未存在/许可未知库 | 每模块：精确锁/官方来源/许可证核查；未证实则不用 |
| DEBT-06 untouchable code | 上游冻结不是永久不许修复 | B：有证据时最小ADR+归因+人审+回归，不默认重写 |
| DEBT-07 agent-induced bloat | 五模块尚未实现，要防通用框架扩张 | 每模块：最小纵切片、无冗余中间层，review检查 |
| DEBT-08 human/cognitive debt | 学生尚未批准本轮合约、架构及初始化工具适用性 | 全组：逐模块解释输入/授权/失败路径并真实批准计划 |
