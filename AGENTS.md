# PaperTrace 编码代理唯一入口

本项目在固定 PaperQA2 基线上扩展，不替换原实现。先读本文，再读 `Prompt.md`，先交计划，等学生真实批准测试及计划，才能开发该次授权范围。文件中的“必须”是约束，不是已经满足的证据。

## 阅读顺序
1. `Prompt.md`、`architecture-blueprint.md`、`.opencode/rules.md`（仅限人工维护）与 `.agent/rules.md`。
2. 本人 `docs/team/module-A.md` 至 `module-E.md` 中的一份、相关 `docs/req/requirements.yaml` 条目、`src/papertrace/contracts.py` 与集成合同相关部分。
3. 涉及的 ADR、不变量、权限、状态、验证和课程原文按需读取，不为一个小变更通读整个治理目录；课程依据见 `docs/sources/course-compliance.md`。

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
学生一次确认本轮模块范围与常用离线工具后，范围内日常编辑、新文件及配置中的精确离线命令不逐次审批；其他 shell 默认 ask，高影响操作仍须单独确认。模型/完整回归/远端人审的真实状态见 `docs/ci/gates.md` 和 `INITIALIZATION_STATUS.md`。

## 人工检查点
需求分类/计划 → **监督学生批准计划** → 仅生成本模块测试/合成fixtures/计划记录（禁止业务实现）→ **非实现者事前批准具体测试版本** → OpenCode受限实现 → 三级验证 → 独立人工PR审查。测试准备可使用对应模块角色，但没有源码实现授权；审批是学生真实行为，角色选择本身不证明批准。每阶段保留真实记录，不补造审批，不将本轮Hermes工程修复称为学生OpenCode贡献。安全路径与共享契约修改须ADR及受影响owner人审；普通模块细节不逐项新增ADR。原基线例外流程见ADR-002，当前仍由frozen_check保护。
