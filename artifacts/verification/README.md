# 初始化验证证据说明

- `final-offline.xml`：真实最终pytest JUnit，170项，0失败/0错误/0跳过；不是PaperQA2完整上游回归。
- `offline-tests.txt`：实际离线通过输出；时间可能来自更早的同版本复跑，以final-offline.xml和最终提交绑定回执为最新记录。
- `contracts-tdd.txt`、`gates-tdd.txt`：真实RED/GREEN过程；`*-red*.txt`故意保留失败实验，不是当前失败状态。
- `opencode-runtime.json`：实际项目配置回读和13个真实许可引擎探针；不执行模型或read/edit/shell工具，不等同工具端到端。
- `*-gate.json`、`all-gates-initialization.json`：初始化局部门禁与完整课程缺口。all为exit2/BLOCKED，不把未执行部分标PASS。
- `delivery-audit.json`：必需文件/链接/追踪/源码冻结/匿名和小样例计时的程序检查；不是人工APPROVE。

为共享隐私，部分真实日志只把本机home路径替换为`<HOME>`，不改变断言、错误、通过数或时间；原日志保留在本机忽略目录`.local/raw-evidence/`，不随材料包分发。错误实验、修复后通过、未执行范围分别记录，不能把本目录的存在当作全部课程要求完成。
