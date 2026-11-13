# 架构来源登记册

本目录编号使用本轮独立登记表，不沿用审计稿编号。所有源码链接锁定提交 `c692d0dfeac4a0296599f7fe21a253a58b7ac12a`。课程与审计的 `urn:sha256` 是材料指纹，不是下载地址；指纹来自已读 source manifest，本子任务未重新计算原PDF/ZIP的hash，不在团队文件记录私人绝对路径。

| 来源 | 实际读取 / 直接定位 | 证据边界 |
|---|---|---|
| [1] 项目原文 | `CS5351-2026-2027-project.pdf` 的授权提取全文，PDF页1–10；p3真实AI/确定性边界；p4角色轮换；p5架构；p6治理/三级验证/D5；p6–7 D6；p9布局；p10六gate | 本地原文快照，不是实时Canvas；D5数量/基线复用与蓝图位置歧义待学生确认 |
| [2] 教学介绍 | `cs5351-2026-2027-introduction.pdf` 的授权提取全文，PDF页1–27；p5/20 OpenCode；p6评估模型；p7 Week13；p23视频/密钥；p25 ADD/低耦合/token | Week13没有确切日期；指定工具不等于模型/金额/数据外发授权 |
| [3] `src/paperqa/docs.py` | 171–311入库/前置外呼；340–386 embedding；437–585检索/摘要；588–721回答/工厂/补证/pre/post | 静态源码，不是本机完整运行 |
| [4] `src/paperqa/types.py` | 155–235 Text；238–316 Context身份；319–433 session/事后计量；442–526过滤/引用格式化 | 合法key不等于人工授权；格式化不是语义证明 |
| [5] `src/paperqa/settings.py` | 148–154自动补证；169–184 parser；235–275 details/media/defer；411–421 pre/post；756–830默认配置；915–955工厂；1179–1250 serializer | top-N/cutoff不是token硬cap；模型默认字符串未获本项目调用批准 |
| [6] `src/paperqa/core.py` | 227–400 摘要/JSON/Context/局部重试 | 有重试不等于全程预算或质量已通过 |
| [7] `src/paperqa/agents/search.py` | 63–93文档pickle；118–145 storage默认；242–274 mapping loader与filecheck | 两个loader；本轮未执行恶意PoC |
| [8] `src/paperqa/agents/main.py` | 91–216 建库、runner、timeout外fallback、fake-agent入口 | fake-agent不是fake模型或免费 |
| [9] `src/paperqa/readers.py` | 92–143 PDF chunk页范围 | 不保证精确句子坐标/bbox |
| [10] `pyproject.toml` | 19–49版本/依赖；53–61许可/发行信息 | Python支持声明不是本机全依赖兼容证明 |
| [11] PyMuPDF子包 `pyproject.toml` | 9–12 AGPL声明；21–27依赖/许可 | 根Apache不自动覆盖可选包或论文 |
| [12] 审计交接包 | 只读解出的01–06报告及最终scope/technical review | 审计建议/历史窄探针/上游CI不冒充本轮新运行 |
| [13] `src/paperqa/agents/env.py` | 243–272 初始状态清Docs；309–345工具流程 | 不是人审ledger或完整持久恢复 |

## 标签规则

“源码已证实”只指固定源码控制流；“已定义测试”不等于已执行；“待开发监控”没有运行回执；“12k/9k/2k默认”是待批工程提案；`proposed-awaiting-human` 不是 accepted。全部审批、真实OpenCode会话、真实模型评测和远端保护必须保留真实证据，不由AI补造。

## Sources

[1] urn:sha256:6af742d3cbc0973b056a084ba54ff413a5885b1bb4d6a97b0b08b93f64f2ef7e — CS5351-2026-2027-project.pdf（本地原文提取，10页）
[2] urn:sha256:16d399f7ca14e0c49dea382cec3893bbee8f589edcaee5131f10fad257d3acb5 — cs5351-2026-2027-introduction.pdf（本地原文提取，27页）
[3] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/docs.py — 固定基线 src/paperqa/docs.py
[4] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/types.py — 固定基线 src/paperqa/types.py
[5] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/settings.py — 固定基线 src/paperqa/settings.py
[6] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/core.py — 固定基线 src/paperqa/core.py
[7] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/agents/search.py — 固定基线 src/paperqa/agents/search.py
[8] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/agents/main.py — 固定基线 src/paperqa/agents/main.py
[9] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/readers.py — 固定基线 src/paperqa/readers.py
[10] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/pyproject.toml — 固定基线 pyproject.toml
[11] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/packages/paper-qa-pymupdf/pyproject.toml — 固定基线 PyMuPDF 子包许可声明
[12] urn:sha256:21f1c516a57e975a284d1d278926fedd9755a6d0036314279663c4074063942a — PaperQA2 审计交接ZIP（仅读解出的Markdown）
[13] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/agents/env.py — 固定基线 src/paperqa/agents/env.py
