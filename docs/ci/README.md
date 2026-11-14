# 六类门禁：执行入口与真实边界

依据：本学期 Project Requirement Sheet p10；p6 D4 要求完整既往测试。实现是 `scripts/gates.py`，细节分别见 [事前批准](test-approval.md)、[真实语义评估](../../test/evaluation/README.md)、[完整回归](full-regression.md)。

| 门禁 | 可执行逻辑 | 不得误读 |
|---|---|---|
| test-approval | 原生 GitHub 测试提案/实现 PR、独立 review、SHA/blobs、服务器时序、安全 ADR/人审 | 没有真实学生批准仍 BLOCKED |
| static | Ruff/mypy、依赖锁闭包、固定上游、AST/API 契约、敏感启发式、实际 OpenCode 配置 | 静态 PASS 不是安全认证或运行时沙箱 |
| schema | 实际 JSON Schema、唯一 ID、invariant ==0、来源可定位、禁止外部 refs | 不证明业务 fit criterion 已实现 |
| semantic | 产品 AI 差异触发、GitHub artifact 与真实授权/逐项评分/原阈值 | 不适用差异 NOT_REQUIRED；mock 不证明质量 |
| regression | 三来源全收集/执行、base node 清单、live 授权、skip/xfail/xpass 拒绝 | initialization 永远不是 full |
| ai-log | base 后真实新增语义披露；禁止只换 ID/删旧记录 | 内容真实性仍需人审 |

```sh
.venv/bin/python scripts/gates.py --gate schema --base <上一轮完整40位SHA>
.venv/bin/python scripts/gates.py --gate static --scope full --base <baseSHA>
.venv/bin/python scripts/gates.py --gate all --scope full --base <baseSHA> --head <headSHA> --pr-number <PR号> --runtime-python <runtime解释器> --upstream-python <上游解释器>
```
占位符必须替换。`--head` 省略时检查实际 worktree；提供时执行输入须与该 head 相同。base 不是祖先时明确 BLOCKED 提示同步分支，模块本地开发不必因此停下。退出码 0=选定范围全部 PASS/确不适用；1=FAIL；2=证据/授权/环境 BLOCKED。`all` 不再硬编码永远失败，也不抹掉任一未满足项。

## CI 信任与首次采纳

六个稳定 job 均从精确 base checkout `.control` 执行验证器，candidate 放 `target`。GitHub 只读 token 只进入元数据核对步骤，不带 token 跑目标测试；不使用 pull_request_target。PR/review/push 会触发检查。回归在 macOS runner 执行真实 OpenCode sandbox 测试，使用核实存在的 `@opencode/cli@2.0.12`，会消耗现有 Actions 配额，不开启新套餐/自动购买额度。目标测试的 socket guard 不是 OS 隔离。

工作流本身仍可能被 PR 修改，不能把 base 脚本读回说成不可绕过保护。私有仓库分支保护当前 API 403，Actions 可见红绿不等于 required checks 生效。最简路线是人工独立 PR review；学生/教师自行核实 Education 的 Pro/Team 权益后再启用、读回并做真实违规/合法对照。

首次修复 PR 的 base 尚是旧验证器，不能由新代码自发批准自己；真实缺失的事前批准/模型证据/完整上游结果都保留。须真人审查采纳后，未来 PR 才由这版 base verifier 验证。不伪造追溯批准，不合并 main。

当前结果只在 [INITIALIZATION_STATUS.md](../../INITIALIZATION_STATUS.md) 维护；历史日志在 artifacts 保留，不冒充本次结果。
