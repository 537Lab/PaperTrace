# PaperTrace 编码代理唯一入口

本项目在固定 PaperQA2 基线上扩展，不替换原实现。先读本文，再读 `Prompt.md`，先交计划，等学生真实批准测试及计划，才能开发该次授权范围。文件中的“必须”是约束，不是已经满足的证据。

## 阅读顺序
1. `docs/sources/course-compliance.md`：课程原文口径、工具及学生本人环节。
2. `architecture-blueprint.md`、`docs/architecture/adr/001-architecture.md`。
3. `docs/architecture/invariants.md`、`permission-model.md`、`memory-design.md`、`runtime-policy-catalog.md`（后四者均在 `docs/architecture/`）。
4. `docs/req/prd.yaml`、`docs/req/requirements.yaml`、`docs/contracts/schema.md`。
5. `docs/code-governance/structural-constraints.md`、`verification-constraints.md`、`mcp-tool-manifest.md`。
6. `.opencode/rules.md`（仅限人工修改）、`.agent/rules.md`、`docs/team/integration-contract.md`，再读对应 `docs/team/module-A.md` 至 `module-E.md`。

## 基线、目录与权威
- 基线：`c692d0dfeac4a0296599f7fe21a253a58b7ac12a`，tag `papertrace-upstream-baseline`。
- 冻结：`src/paperqa/`、`packages/`、`tests/`、`pyproject.toml`、`uv.lock`、`LICENSE`。上游README与自动发布工作流原样保存在 `docs/upstream/`，旧工作流不自动执行。
- 新代码只放 `src/papertrace/`；共享定义仅 `contracts.py`。A=library，B=retrieval，C=review，D=answer，E=reports。只有B适配器允许直接导入PaperQA2；D经B的受控回答端口使用它，不绕过审批过滤。成员开发前不创建这些业务实现。
- 团队测试在 `test/offline/`、`test/live/`；旧 `tests/` 原样保留，初始化通过不等于完整上游回归通过。
- 模型只给建议。人工决定授予证据；D的确定性检查决定是否可发布；UI和合约序列化都不能替代运行时授权。
- 不读取 `.local/`、凭据、环境秘密、私人目录；不推送，不改Git设置/工作流/权限/人工规则，不导入第三方pickle索引，不自行增加依赖或收费调用。

## 可执行验证
```sh
.venv/bin/python -m pytest -c papertrace.pytest.ini test/offline
.venv/bin/python -m ruff check --config papertrace.ruff.toml src/papertrace test/offline scripts
.venv/bin/python -m mypy --config-file mypy.ini src/papertrace
.venv/bin/python scripts/gates.py --gate schema
```
这些命令不授权代理获得shell权限；由学生批准具体运行。模型/完整回归/远端人审的未完成状态见 `docs/ci/gates.md` 和 `INITIALIZATION_STATUS.md`。

## 人工检查点
需求分类与测试方案 → **非实现者批准测试，学生批准计划** → OpenCode受限构建 → 三级验证 → 独立人工PR审查。每一阶段保留实际输入/输出/干预，不能补造审批或将本轮Hermes初始化称为学生OpenCode开发。安全路径与共享契约修改须ADR及受影响模块的人工同意；本轮ADR仍是待批准提案。
