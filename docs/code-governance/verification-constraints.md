# 验证约束（D4）

任何“通过”须绑定同一代码/测试/需求/配置版本、命令、运行环境、退出码与原始日志。课程 Project p6 要求三级验证，p10 要求六类阻断门禁；本文件不声称 D4/D7 已完整达成。

## 三级验证

1. **结构：**需求 schema、模块/import 边界、冻结基线差异、类型/lint、依赖一致性、路径/权限、安全规则与敏感文件检查。静态检查不是 OS 沙箱，配置解析不是工具拦截。
2. **回归：**初始化环境的 `.venv/bin/python -m pytest -c papertrace.pytest.ini test/offline` 只覆盖 `test/offline/`，不等于 full regression。完整既往回归须分开收集并报告三类来源：①团队 `test/offline/` 全跑；②仓库 `test/` 中 offline 以外的 runtime tests；③固定上游项目配置下的 `tests/` 与 `packages/*/tests/`。上游完整 collection 须与固定基线 node IDs 对照，不能漏项或静默标记；未授权 live 项须逐项列为 BLOCKED，不可冒充 skip-as-pass。只有显式 operator 选择 `--run-live` 且已有独立人审数据/provider/model/预算授权，才可执行 live；默认绝不外网。实际入口/命令以主控同步的 runner 和真实回执为准。
3. **行为：**固定案例检查来源、人工授权、三集合、新鲜度、失败策略和模型语义。fake 仅证明确定性代码与输入边界；真实 prompt/model 评估须用获批数据和 provider、固定集及真实阈值，未获批/未执行即 BLOCKED。

每项 feature 至少一个正例与一个可定位负测；每条不变量须有故意违反会失败的断言。测试标注真实 `FR-*` / `INV-*`；事前由非作者批准测试版本，测试语义变化后重审。安全代码不可由同一生成代理自证。保留真实 RED/GREEN，不删除失败断言或调阈值求绿。

六类门禁必须全部保留：实现前测试批准、静态/安全/依赖检查、需求 schema、真实语义评估、完整 prior regression、代码/prompt 变化的 AI-use log。任何门禁不可删、降级、用 skip/fake/空 suite 冒充通过；远端 required checks 只有配置回读并用违规/合法对照验证后才算启用。

## 独立性与记录

- 每个 PR 用 `docs/review-memo.md` 的真实独立审查；结论仅 `APPROVE` / `CHANGES REQUIRED` / `REJECT`。
- 显著 bug 记 `docs/bug-diary.md`，技术债记 `docs/debt-register.md`；没有事实不编造条目。
- 真实学生 OpenCode session /人工干预才是 D5 证据；Hermes 初始化、synthetic fixture 或脚本输出不能代替。
- 远端保护须授权后配置、读回，并用故意违规 PR 和合法对照验证；未有读回证据标待处理。
