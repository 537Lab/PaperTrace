# Bug日记（D4）

当前没有可声称已复现并修复的PaperTrace业务bug，因为五模块尚未开发。契约RED/GREEN的真实输出保存在`artifacts/verification/`，它们不是生产事故。

## ENV-001：课程PDF的通用抽取器失败
- 症状：read_file报告0页/无文本；并非课程材料不存在。
- 复现：对两份指定原件调用通用抽取器失败；pypdf实际读取分别10/27页。
- 分类/根因：环境兼容性，PDF含xref和重复字典项警告；不能据单一抽取工具推断原件无内容。
- 处理：用已有pypdf只读提取；保留原字节和SHA256，不改原件。
- 不变量缺口：来源核验不能等同于某一种抽取器成功；与产品INV执行无关。
- 状态：本轮材料读取已恢复；未声称PDF格式修复。

## CONTRACT-001：初始空审核状态无法序列化
- 症状/复现：真实账本尚无人工事件时revision=0，最初AnswerDraft/ReleaseDecision仅接受>=1，合法拒答/阻断也被拒绝。
- 分类/根因：共享数据边界遗漏初始状态；不是模型故障或已发生业务发布事故。
- 修复：共享ReviewRevision允许严格整数>=0；draft/released仍要求非零。ReviewDecision事件revision仍从1开始。
- 暴露不变量：INV-01/03不能为了序列化虚构人工审核事件。新增独立负测及合法对照，真实RED与GREEN保存在artifacts/verification；同步两份Schema及C/D任务书。
- 状态：170项离线测试通过；账本和发布运行时业务尚未开发。

## UNBLOCK-001：开发/门禁死结（工程问题，不是学生业务）
实测修复全provider拒绝、测试未批不能生成测试、永久BLOCKED入口及full漏项/超时/标记绕过；每类负例先RED后GREEN。真实OpenCode测试准备曾写到非自有测试路径被正确拒绝，改为test_library；嵌套fixture显式pytest.ini防继承上游配置。SCM/egg-info真实构建元数据仅窄豁免，新增上游源码仍FAIL。

## UNBLOCK-002：上游完整回归仍未通过
实际安装固定uv.lock；377个base/current节点一致，首个索引测试在默认禁网下尝试API被socket拒绝，完整执行有真实失败/限时，9个live待授权。保留FAIL、原测试和清单，不解封网络、不用私人key或假结果。250团队离线和1runtime通过不代表full。

## CLOSEOUT-001：语义报告误放行与无关配置误阻断
- 复现：重算请求/报告哈希可掩盖固定问题/获准正文/发送ID不一致；runtime改锁并刷新head记录仍可能使用旧环境；纯Ruff/pytest修改被要求真实模型评估。均由实际离线负测先观察失败。
- 根因/修复：自报哈希不验证材料来源，配置摘要漏runtime输入，触发只看文件名。改为精确请求合同、v3运行锁及实际解释器版本核对、生产依赖闭包内容判定；保留未知/畸形配置的保守触发和B/D/上游模型代码覆盖。
- 回归：全部299项团队离线、0 skip；PaperQA2离线集成1项；Ruff/mypy/static/schema通过。不是正式业务实现、真人事前批准或真实模型质量证据；原full失败不变。本轮证据见artifacts/verification/closeout-semantic.json。

后续显著bug必须留症状、最小复现、根因证据、修复diff和防回归测试，禁止把假设写成复现。
