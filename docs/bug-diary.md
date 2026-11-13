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

后续显著bug的记录必须包含症状、最小复现、分类、根因证据、修复diff、暴露的INV缺口和防回归测试。禁止把假设写成已复现。
