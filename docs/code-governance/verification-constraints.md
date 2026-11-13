# 验证约束（D4）

任何“通过”必须绑定代码/测试/需求/配置版本、命令、运行环境、退出码及实际日志。课程Project p6要求三级验证，p10要求六类阻断门禁；本轮仅初始化基础，不能称D4/D7完整达成。

## 三级验证
1. **结构**：需求schema、所有必需文件非空、显式模块import/API表面、冻结源码完整性、类型/lint、依赖锁一致性、角色权限及敏感文件排除。依赖版本一致不是漏洞库扫描；权限pattern测试不是OS沙箱。
2. **回归**：运行本次以及全部既往suite，不得将未执行、skip、缺依赖或旧模型cassette回放当成新的完整PASS。初始化命令：`.venv/bin/python -m pytest -c papertrace.pytest.ini test/offline`；上游`tests/`与`packages/*/tests/`完整历史suite和live测试仍待依赖/授权，详见`docs/ci/gates.md`。
3. **行为**：固定数据集评估语义支持/相关性及零授权外逃；真实prompt/model变化需新的真实评估。合成fixture与fake transport只验证逻辑，不证明科学质量、模型连接或性能提升。

每条fit criterion至少一条可定位测试或明确待实现用例。每条不变量必须有故意违反的负例，确保会失败；每个功能至少一个负测。测试注明REQ/INV标识，使用自写fixture，非作者批准测试版本后才开始实现；安全代码测试不能由生成实现的同一代理单独自证。

共享契约验证JSON往返、schema、非法身份/版本/定位、重复记录、越权状态、时间时区、引用集合及拒答。业务开发补齐：空获准集0出站；模型伪造授权；已排除/未发送/未知引用；生成中语料或审核变化；错误模型JSON；超时/限额；上下文压缩后约束重注入；历史导出脱敏；中断恢复和可重放性。合约已能拒绝某些形状，不等于这些业务测试已经实现。

## 独立性与记录
- 保存真实RED与GREEN，不修改测试来迎合实现；修改预期须先回到批准人。
- 生产阈值先批准/冻结。不得把缺真实评估填0再让阈值过关，不以HTTP 200、空content或reasoning代替有效答案。
- 每PR在`docs/reviews/`存memo，并在`docs/review-memo.md`索引；结论仅APPROVE/CHANGES REQUIRED/REJECT，只有真实审查者能给人工APPROVE。
- 显著bug记`docs/bug-diary.md`，技术债记`docs/debt-register.md`。未经真实学生监督的初始化日志不能当D5会话。
- 远端管理员设置required checks/安全路径人审及ADR后，必须用单一故意违规PR与合法对照核验真实阻断。没有GitHub回读证据，只能称“文件已准备”。
