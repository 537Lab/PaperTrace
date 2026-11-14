# 六类门禁入口索引

- [状态、命令、退出码与信任边界](README.md)
- [**六类门禁最小落地方案（学生团队，2026-11-14）**](minimal-gates.md)
- [Gate 1：可信事前测试批准合同（严格参考）](test-approval.md)
- [Gate 4：固定合成评估集与真实模型运行合同（未执行）](../../test/evaluation/README.md)
- [Gate 5：完整既往回归合同（未执行）](full-regression.md)
- [Live测试授权与运行边界](../../test/live/README.md)

当前本地初始化基础与远端六个 CI 检查均已真实执行；static/schema/ai-log 在 GitHub Actions 首跑中为 success，test-approval/semantic-evaluation/regression 为 BLOCKED（fail-closed）。事前批准、真实语义评估、完整既往回归以及远端规则均不得据此宣称完成。`--gate all`仍fail-closed，详见上述状态表。TDD真实输出见`artifacts/verification/gates-tdd.txt`；路径已作脱敏，不合成测试结果。

直接使用文档中的pytest命令时，pytest自动加载锁定的pytest-socket插件；隔离运行时设置`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`并显式加`-p pytest_socket`。门禁子进程已经采用后者，避免第三方插件影响。
