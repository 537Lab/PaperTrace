# Gate 5：完整既往回归合同（未执行）

初始化环境只有共享契约及CI基础，不包含PaperQA2全套运行依赖。`--gate regression --scope initialization`执行**全部团队离线**测试并读取新生成JUnit：非零退出、空集合、错误、失败、skip均不作为通过。`--scope full`即使这些通过仍返回BLOCKED/2；本轮没有完整既往套件/真实live结果的可信校验器，不读取仓库内自写成功报告。

后续批准后在独立、符合固定上游`uv.lock`的环境中先执行原版已存在的CI范围（不要删除/改名原套件，也不能把初始化配置套给上游）：

```sh
# 仅运行合同示例，本轮未执行，uv sync会下载上游完整依赖
uv sync --frozen
uv run pytest -n auto -m 'offline and not live_api' tests
uv run pytest -n auto -m 'offline and not live_api' packages
```

这两条只覆盖原版CI离线选择，**仍不等于full**。正式full还须枚举并执行上游其余所有prior测试、`packages/*/tests`、后续每轮团队offline/live套件。固定基线工作流中的Python矩阵及各包支持版本需一并保留并记录。先用该环境的pytest collect-only建立不丢失的item清单（收集可能导入上游代码，仍须隔离与批准）；按实际marker把离线、live/API、需要外部资源的测试分组，不能随意漏选。测试项目ID/数量、环境指纹、代码/tests/prompt SHA、开始结束时间、命令、退出码、JUnit、失败/跳过/xfail/xpass及原因均保存；每项需真实通过或明确仍BLOCKED，不能将skip算通过。基线已有失败也不能被描述为零回归全部通过；须保留前后差异并经人审处理。

真正live或可能下载模型/调用提供商的部分必须先取得单独数据、provider/model/version、费用/次数及网络范围授权，再从批准的密钥服务注入；不得粘贴密钥或把私人环境复制进测试。完整命令必须由已经实现并审核的adapter与具体测试入口确定，目前没有这种命令可合法跑通，不能虚构一个runner。见`test/live/README.md`。
