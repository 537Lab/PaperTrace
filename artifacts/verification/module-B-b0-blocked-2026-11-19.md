# B0 离线基线：实际失败记录与恢复提案

- 日期：2026-11-19（Asia/Hong_Kong）。
- 执行者：当前 Codex 会话；不是 OpenCode 业务代码生成或学生独立审核。
- 依据：已获本人批准的 Plan v2.1，第 7.2 节。
- 结果：**BLOCKED；1 failed，退出码 1，pytest 耗时 5.94 秒**。

## 实际执行

```sh
PYTHONDONTWRITEBYTECODE=1 .local/unblock/runtime/.venv/bin/python -m pytest \
  -c papertrace.pytest.ini test/integration/test_paperqa_smoke.py -q
```

失败链（个人路径已替换为 `<repo>`）：

```text
scripts/paperqa_smoke.py:42  from paperqa import Docs, Settings
src/paperqa/__init__.py → agents → settings → readers → types
src/paperqa/types.py:50  from paperqa.version import __version__ as pqa_version
ModuleNotFoundError: No module named 'paperqa.version'
test/integration/test_paperqa_smoke.py:40: AssertionError
1 failed in 5.94s
```

## 已确认与未验证

- 当前目录是 ZIP 副本，没有 `.git`；`src/paperqa/version.py` 缺失。
- `pyproject.toml` 使用 `setuptools.build_meta`，构建依赖为 `setuptools>=64` 与 `setuptools_scm>=8`，配置将版本写到 `src/paperqa/version.py`。
- runtime 已按既有锁安装；该锁和当前 runtime 均未提供 `setuptools_scm`。
- 导入时失败，尚未到 `_exercise()`：真实 `Docs.aadd/aget_evidence/aquery` 接线、正负向 prompt、socket 计数均未得到本次运行报告。不能把未到达的计数器写为实测 0。
- 未使用真实产品模型或学校 Key；没有更改源码、测试、共享契约或依赖锁。
- 仓库已有 `unblock-paperqa-smoke.*` 是历史证据，不得覆盖或当成本次复现通过。

## 下一步恢复提案（待学生确认，尚未执行）

优先恢复可追溯的构建环境，不手写任意版本字符串，也不注入假 `paperqa.version` 模块。

1. 在独立临时工作目录获取 `537Lab/PaperTrace` 的真实 Git checkout，明确记录所用分支和 commit；不覆盖当前 ZIP 副本。保留现有个人计划文件，只复制经过核对的 B 模块文档。
2. 从该 checkout 的 Git 元数据及既有构建配置确定版本。仅在独立构建副本中，使用上游声明的构建机制生成版本元数据；所有受版本控制的上游文件须保持逐字不变。生成文件不得提交进模块 PR。
3. 若需下载构建工具，限定软件包源、固定并记录实际构建工具版本与 hash，使用独立构建环境；既有 runtime 锁保持不变。构建依赖下载不授予任何产品模型调用权限。
4. 使用原样 smoke 脚本与原样集成测试重跑，保存完整真实结果和调用计数；若仍失败，保留错误并停止，不自动换模型、改锁或改断言。
5. 若无法在上述范围内完成，则提出单独的上游兼容 ADR/PR，由团队按既有流程处理，不能将兼容修改混入 B 业务实现。

这项提案涉及新增 Git 获取网络范围、隔离构建环境及生成版本文件，因此不把原第 7.2 节的 runtime 安装许可当作已经批准本提案。

## 可继续的工作

B1 测试设计已整理；A/C/D/E 可继续按共享契约使用 synthetic 数据。B1 测试代码仍须通过已授权的 OpenCode 开发流程产生，具体测试 commit 获独立 Approve 后才能进入 B2。当前工作副本没有 Git 历史，尚不能产生可供远端人审的 commit。
