# 选项账本：拒绝什么，何时再考虑

> 所有条目均为本架构提案的取舍，不是学生已批准的决定。课程项目第 5 页把 option ledger 列为 optional，第 9 页树又列出；本轮提供实质内容以便追溯，但不据此擅改评分口径。[1]

| Option ID | 选项 / 当前处理 | 拒绝或延后的理由 | 明确重开条件 / 所需证据 |
|---|---|---|---|
| OPT-01 | 用原样CLI/高层Agent直接生成并发布：不采用 | 自动补证/工具循环、前置建库、timeout外fallback与人工先审次序不一致（`docs.py:602–624`、`agents/main.py:121–183`）[3][8] | 仅在能证明所有工具/工厂/SDK/HTTP均受控，空集零调用、三集合和freshness仍成立后；新ADR+负测+人工批准 |
| OPT-02 | 修改/替换 `src/paperqa` 核心：本期禁止 | 保留可追溯baseline，避免把上游已有能力重写成团队创新 | 薄适配无法满足明确Must，提供最小失败证据与替代比较，学生明确重开冻结范围后再谈 |
| OPT-03 | 运行中物理删除向量/多存储强事务：排除MVP | tombstone与检索过滤已有，物理删除与恢复是额外跨引擎问题；不能借薄快照门暗中包全量（`docs.py:403–490`）[3] | 用户明确需要安全擦除/存储回收或大量语料；限定后端、故障模型、独立预算/工期与实跑证据 |
| OPT-04 | 第三方pickle索引导入/自动迁移：禁止 | 文档和mapping两个loader；先unpickle再检验已太晚（`agents/search.py:86–93,242–257`）[7] | 先设计非执行数据格式、schema/大小/路径/来源合同；不默认提供legacy可执行迁移；独立ADR与安全审查 |
| OPT-05 | Qdrant/数据库服务器/云存储：延后 | 本期单机单人单写者没有服务化需求；引入部署/网络/一致性成本 | 单机已测资源瓶颈或明确多人需求；先真实测量，再比较本地文件/SQLite/服务方案，不凭想象上云 |
| OPT-06 | 大型Web前端/公开部署/登录系统：延后 | 不能让五功能任务变成UI/运维；公网/多用户权限模型与当前威胁边界不同 | 真实目标用户与并发需求被批准、核心不变量/测试完成；新部署/认证/数据/隐私设计 |
| OPT-07 | 自动metadata/citation inference/media enrichment/pre-post：默认关闭 | 额外外呼、费用和raw引用变化增加受控面；None才是pre/post真正关闭（`docs.py:180–311,626–639,694–711`）[3] | 明确产品需求、逐路径计量覆盖与许可证/数据批准；任何最后加工仍必须重过D发布门 |
| OPT-08 | 模型摘要自动接受、score当置信度：拒绝 | 模型无审核权；相关度不是科学真实性或人审记录 | 不能在现INV-03下重开；若产品要改变权威边界，必须公开改需求/不变量，取得学生和课程允许，不以prompt偷偷放权 |
| OPT-09 | LLM上下文压缩/Reflexion自主重试：MVP不做 | 可多耗调用、污染身份/决定、隐藏反复生成；固定流水线足够 | 确定性裁剪已被数据证明不足；单独批准模型/金额/数据/次数；压缩保真/约束重注入与终止负测齐全 |
| OPT-10 | 自动证明所有科学断言/找全矛盾：不承诺 | 引用/quote可定位不等于语义蕴含或事实正确 | 可添加明确限定的人工rubric/评测或辅助冲突提示，但不得升级为代码零容忍真理认证 |
| OPT-11 | 旧快照接受状态自动迁到新快照：不采用 | 新快照有新evidence身份；同摘要/同正文不代表当前审核授权 | 先定义可验证迁移提案、用户显式逐项确认和新ledger事件；不能把批量复制视作原决定仍生效 |
| OPT-12 | 两份完整blueprint分别维护：拒绝 | 课程布局有两处入口，双正文易漂移 | 只有教师明确要求两份完整副本，才考虑由单源生成并设一致性gate；默认根canonical+指向页 |

重开不是“已经许可”：提交触发证据 → 比较更小替代 → ADR/需求/合同/测试/trace/权限影响 → 学生本人批准 → OpenCode先计划再停人审。旧条目保留，新结论追加；不删掉当初拒绝理由来掩饰范围扩大。

## Sources

[1] urn:sha256:6af742d3cbc0973b056a084ba54ff413a5885b1bb4d6a97b0b08b93f64f2ef7e — CS5351-2026-2027-project.pdf（本地原文提取，10页）
[3] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/docs.py — 固定基线 src/paperqa/docs.py
[7] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/agents/search.py — 固定基线 src/paperqa/agents/search.py
[8] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/agents/main.py — 固定基线 src/paperqa/agents/main.py
