# 课程原文核对与适用边界

核对日期：2026-11-13；读取本地PDF原件，未实时向Canvas核查修订。PDF内有xref/重复字典定义警告，通用抽取器失败后改用pypdf成功提取Project10页、Introduction27页；未擅自修复原件。摘要/交接指令不能替代原文。文件名、Canvas文件ID、SHA256与大小见`materials-manifest.json`。两份原件与审计交接zip只在本机忽略目录`.local/materials/`保全，未放进Git/团队交付包。

- Project p3：真实AI组件+至少一个由确定性代码约束AI输出的安全边界。
- Project p5：YAML PRD与registry都要有；分别为`docs/req/prd.yaml`与`requirements.yaml`。根blueprint是唯一正文，`docs/architecture/architecture-blueprint.md`指向它，兼顾p5与p9布局。
- Project p5–6：架构、状态、上下文cap/压缩/关键约束重注入、默认无读写、Human-only规则、三级验证、每PRmemo、技术债与bug diary。
- Project p2与p6：p2概述要求五份annotated transcript；p6 D5写一份完整raw/from scratch。采用每成员保留一份完整真实OpenCode会话的较充分方案；最终口径由教师确认，不伪造会话填空。
- Project p4：建议轮换过程角色。五人固定功能ownership不变，测试批准/独立review/集成检查等过程角色轮换，避免把功能任务退化为只有管理。
- Introduction p5、p20：考核基于OpenCode；明确期待AI生成、学生把精力放在控制与监督，不接受事后虚构人工控制。本轮初始化由Hermes辅助生成，**不是学生正式OpenCode开发/事前批准证据**。学生须确认其作为共享起点的使用边界，必要时在真实OpenCode监督会话中再生成/采纳；这不是已经完成。
- Introduction p20：允许选择类似复杂度的其他项目，不仅限股票Agent。PaperQA2与五模块已由本轮委托确定，但教师对具体范围/扩展基线的最终认可仍需学生确认。
- Introduction p7仅写Week13项目截止，未给精确日期。本材料不猜DDL；学生核对Canvas/教师最新通知。
- Introduction p23：最终ZIP不含demo视频，另交10分钟demo，比较有/无新增需求的行为效果，并展示追溯与治理。初始化不伪造性能对照。
- Project p6–7 D6：最终Report须真实姓名/学号、相对贡献（平均1.0）、每人反思；最多10000词（不含图），原文另写12pt单倍行距超过15页。300–500词是反思的举例，不自行改成硬区间。**本轮共享团队材料匿名，最终课程报告的真实身份与贡献必须由学生本人填写/确认**。
- Project p10：六类门禁及分支保护是实际行为要求，不是文件名清单。本轮远端未创建、未生效；见`docs/ci/gates.md`。

## 本轮交付不代表
D1/D2/D3/D4/D7的基础材料已能建立；D5个人监督过程、D6正式报告、D8五模块业务及真实AI评估、D7远端保护仍有学生/授权/开发依赖。不能称“课程全部完成”或“拿去直接提交”。
