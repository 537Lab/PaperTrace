# Gate 5：完整既往回归

执行器是 [`scripts/full_regression.py`](../../scripts/full_regression.py)，`gates.py --gate regression --scope full` 调用同一实现。**没有恒定 BLOCKED 分支**：完整合成仓库的正例能通过，漏项、失败、跳过和未获准 live 的负例被阻断；它们是验证器测试，不是 PaperQA2 全套已通过的证据。

## 三个来源，全量收集而不是只选 offline marker

| 来源 | 解释器与配置 | 收集范围 |
|---|---|---|
| 团队离线 | 初始化 `.venv`；`papertrace.pytest.ini` | `test/offline/` 全部测试 |
| 团队运行/集成/live | 独立运行环境；同一团队配置 | `test/`，只排除已执行的 `test/offline/`，因此以后新目录也进入清单 |
| 上游 | 固定 `uv.lock` 的独立环境；**原 `pyproject.toml`** | `tests/` 和 `packages/`，保留其 doctest/typeguard 设置 |

不传 `-m offline` 或 `-k`。所有未标记测试也收集并在默认无网络环境执行；`live`/`live_api` 项只列入 `pending_live`，未经授权不执行、整门为 BLOCKED。任何其他 deselection、collection error、空的已存在套件、skip、XFAIL、XPASS、setup/call/teardown 失败，都不是零回归。

执行前还从**上一轮真实 Git base**生成临时只读快照，用对应解释器和原配置收集 prior node IDs；当前清单必须包含这些节点。这样即使没有删文件、只删掉一个测试函数或参数化用例，也不会悄悄通过。baseline 的 collection-only 明确不是执行成功。Git archive 不含 setuptools_scm 生成的 ignored version.py；runner 仅将本次真实构建的这些元数据复制到临时 base，记录路径与 SHA，不替换任何 base 测试或业务源码。超时保留已收集节点/已执行结果并终止本轮进程组，不把部分执行算完成。环境依赖缺失为 BLOCKED，代码/断言失败为 FAIL；不把缺依赖换成 initialization 来放行。

## 可复现命令

初始化环境仍按 [团队入口](../../TEAM_START_HERE.md) 安装。团队真实运行环境见 [PaperQA2 验证说明](../tooling/paperqa-runtime.md)。上游完整开发依赖按原锁安装到另一环境（下载体积可能较大，但不授权模型/API）：

```sh
UV_PROJECT_ENVIRONMENT=.venv-upstream uv sync --frozen
uv pip install --python .venv-upstream/bin/python --no-deps --require-hashes -r requirements-upstream-test.lock
```

在正确分支上，用真实上一轮提交替换 `<base-40字符SHA>`，不要照抄占位符：

```sh
.venv/bin/python scripts/full_regression.py \
  --base <base-40字符SHA> \
  --runtime-python .venv-runtime/bin/python \
  --upstream-python .venv-upstream/bin/python \
  --output .local/full-regression
```

Windows 使用对应环境的 `Scripts/python.exe`；也可直接给 `--*-python` 传绝对路径。默认不读取 `.env`、个人 HOME、全局 pytest 插件或私人 provider 凭据，离线时在 **conftest 导入前**阻断 Python sockets；Unix domain socket 仅供本地 asyncio 使用。这个 Python 级防护不是 OS 沙箱，不能宣称抵抗恶意 subprocess 或所有外部程序。

`--run-live` 只供操作者在**真实独立测试/计划审批、数据/模型/次数/预算批准后**显式使用；会允许网络并仅转交已列明 provider 的环境变量，可能产生费用。不搜索或读取密钥文件。自动 CI 不传这个开关；它不构成批准记录，Gate 1 和独立 PR review 仍须满足。当前项目没有获准的真实模型验证，不得运行该开关求绿。

## 输出与验收

`.local/full-regression/full-regression.json` 是本轮新生成的汇总，各来源保存 exact command、完整 collected/selected/pending_live、outcomes、stdout/stderr 及摘要。还记录代码/测试/配置输入 SHA256，执行期间输入改变会失败。退出码：0=本次完整范围 PASS；1=FAIL；2=BLOCKED。所有 PASS 都只覆盖记录中的解释器、平台和版本，不代表跨 Python/OS 的上游矩阵全过。

GitHub `regression` job 安装运行锁和上游冻结环境后走 **full**，不使用 `continue-on-error`、不以 initialization 替代。安装/collection/实际断言的缺口在 Actions 和本地记录中如实保留。私有仓库套餐下 CI 运行仍不等于强制合并保护；见 [门禁状态](gates.md)。
