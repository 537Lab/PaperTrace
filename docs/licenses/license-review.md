# 许可证与再分发审查

核对日期2026-11-13；这是已读取许可证/元数据及明确限制的工程清单，不是法律意见或全供应链认证。

| 组件 | 本轮证据/许可 | 决策 |
|---|---|---|
| 原paper-qa核心 | 固定提交根LICENSE为Apache-2.0 | 保留完整原文、版权/归因与Git历史；新增团队代码不冒充上游作者 |
| paper-qa-pypdf | 子包LICENSE/pyproject，Apache-2.0；其PyPDF依赖另有自身许可 | 后续文本PDF首选，显式固定parser；本轮未安装/运行该解析链 |
| paper-qa-pymupdf / PyMuPDF | 子包声明AGPLv3，PyMuPDF有自身AGPL/商业条件 | 不纳入初始化环境；分发/提供网络服务前另审，不由根Apache许可推出可无条件闭源再分发 |
| Docling / Nemotron | 子包LICENSE及pyproject；底层模型/服务/依赖另审 | 不装可选extra、不下载权重、不启用服务；子包许可不覆盖模型/数据/服务条款 |
| 初始化venv | `initialization-environment-licenses.json`为真实安装元数据扫描 | Pydantic/pytest/ruff/mypy等以MIT为主；pathspec是MPL-2.0，packaging可Apache-2.0或BSD-2-Clause，typing_extensions是PSF-2.0；不把它们统称Apache |
| Streamlit | 仅架构选型，本轮未安装；最终精确版本需核官方LICENSE及传递依赖 | 成员接入UI前锁版本/归因/审查 |
| 模型/API | 未批准任何供应商/模型，未读密钥、未调用 | 后续核provider服务条款/权重许可、文献传输授权、计价/预算，不能据开源代码许可推导可使用模型 |
| 上游tests里的论文PDF/图表/Office/录制 | 位于原基线本地Git；主项目LICENSE不自动证明每件再分发许可 | 本轮不将这些放入团队材料包，不上传不明权利数据；公开/私有GitHub上传完整历史前先审。仅私有也不是免除版权义务 |
| 课程原PDF/审计handover | 本地原件hash保全，审计报告含私人绝对路径/环境信息 | `.local/materials/`忽略，不放Git或可分享包；团队文档仅记录必要来源/页码/摘要 |
| 团队合成fixtures | 初始化自写，无真实论文或成员数据 | 明示synthetic、仅测试逻辑，不能当真实模型或科研评估证据 |

本轮依赖锁不做全环境软件分发：不打包venv、wheel或模型。将来需要再分发依赖时，按精确版本收集并保留许可证/NOTICE；扫描器声明的license字符串不是全部义务。根上游完整Git历史含旧资料，不能在未审查时直接公开推送；保留原历史与清理受限数据如果冲突，须学生决定受限来源隔离/可追溯引用方案，并保证不丢原始基线证据。

漏洞检查与许可证检查不同。本轮只核版本锁、元数据/已知限制；未访问完整漏洞库，不能宣称供应链没有漏洞。LiteLLM上游声明排除的版本限制保留在原pyproject，不为初始化擅自升级/替换。
