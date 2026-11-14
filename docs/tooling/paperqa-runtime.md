# PaperQA2 离线 runtime smoke

## 目的与边界

此 smoke 在固定上游 PaperQA2 checkout 上调用真实 `Docs.aadd` → `Docs.aget_evidence` → `Docs.aquery` 路径，验证依赖/API 接线和证据进入最终 prompt 的边界。上游基线标识为 `c692d0dfeac4a0296599f7fe21a253a58b7ac12a`；脚本通过 `src/` 与 `packages/paper-qa-pypdf/src/` 直接导入源码，不做 editable install，避免 `setuptools_scm` 改写 `src/paperqa/version.py`。

这不是正式业务功能或真实模型测试：只有一个手写的合成 `.txt` 证据文件；embedding、summary、answer 都是本地确定性 test double，answer 明确标记为 `SIMULATED_OFFLINE_ANSWER:`。不使用私人密钥、真实论文、真实 LLM/provider 或收费调用；不验证回答质量、实际 PDF 解析、Docling/OCR、检索服务或 A–E 业务适配器。

## 运行环境与锁定依赖

测试时环境为 Python `3.14.6`、uv `0.12.9`（`aarch64-apple-darwin`）。`requirements-runtime.lock` 由 `requirements-runtime.in` 与 `.local/unblock/runtime/baseline-uv-constraints.txt` 解析，当前为 **83 个带 hash 的精确锁定包**。完整传递依赖版本以该 lock 为准；直接依赖的实测版本如下：

| 用途 | 发行包版本 |
|---|---|
| PaperQA API/runtime | `fhaviary==0.34.0`, `fhlmi==1.10.0`, `litellm==1.84.1`, `numpy==2.4.3`, `pydantic==2.12.5`, `pydantic-settings==2.16.1`, `pypdf==6.9.1` |
| 其余 runtime 直接依赖 | `anyio==4.12.1`, `html2text==2025.4.15`, `httpx==0.28.1`, `httpx-aiohttp==0.1.12`, `pybtex==0.25.1`, `rich==14.3.3`, `setuptools==82.0.1`, `tantivy==0.25.1`, `tenacity==9.1.4`, `tiktoken==0.12.0` |
| pytest / 轻量 collection | `pytest==9.0.2`, `pytest-asyncio==1.3.0`, `pytest-recording==0.13.4`, `pytest-socket==0.8.1`, `pytest-subtests==0.15.0`, `pytest-timeout==2.4.0`, `typeguard==4.5.1` |

没有安装大范围上游 dev/test extras、ML/Docling 包或模型权重。`pytest-socket` 是必要项：`papertrace.pytest.ini` 使用 `--disable-socket`，且上游 offline 测试导入 `pytest_socket`。该配置文件名不是 pytest 自动发现的默认文件名，因此执行 smoke 时要显式 `-c papertrace.pytest.ini`。

## 从仓库根目录复现

```bash
cd <你克隆的PaperTrace目录>
RUNTIME=.local/unblock/runtime
mkdir -p "$RUNTIME/home" "$RUNTIME/tmp" "$RUNTIME/cache" artifacts/verification
uv venv "$RUNTIME/.venv" --python 3.14
# 使用已提交且带hash的锁；日常安装不重算、不依赖本机辅助constraints。
uv pip sync --python "$RUNTIME/.venv/bin/python" requirements-runtime.lock

PYTHONDONTWRITEBYTECODE=1 "$RUNTIME/.venv/bin/python" -m pytest \
  -c papertrace.pytest.ini \
  test/integration/test_paperqa_smoke.py -q

/usr/bin/env -i \
  PATH="$PWD/$RUNTIME/.venv/bin:/usr/bin:/bin" \
  HOME="$PWD/$RUNTIME/home" \
  TMPDIR="$PWD/$RUNTIME/tmp" \
  XDG_CACHE_HOME="$PWD/$RUNTIME/cache" \
  PYTHONNOUSERSITE=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  "$PWD/$RUNTIME/.venv/bin/python" \
  scripts/paperqa_smoke.py --json \
  --report artifacts/verification/unblock-paperqa-smoke.json \
  | tee artifacts/verification/unblock-paperqa-smoke.txt
```

测试子进程使用白名单环境，不继承调用者的 dotenv、用户 site-packages 或 API key。脚本自行把上游 `src/` 和 `packages/paper-qa-pypdf/src/` 放到 `sys.path`；本 smoke 不需要 `uv pip install --no-deps . ./packages/paper-qa-pypdf`。若其他 runner 需要显式模块路径，可用 `PYTHONPATH=src:packages/paper-qa-pypdf/src`，不要为这个 smoke 做 editable install。

## 离线保证

- `LITELLM_LOCAL_MODEL_COST_MAP=True` 在导入 `lmi` / PaperQA 前设置，强制 LiteLLM 使用随包附带的本地 cost map，避免其默认的 import-time 远程 cost-map 请求。JSON 记录 `source=local`、`url=null`、`is_env_forced=true`、`fallback_reason=null`，并断言没有落到远程失败 fallback。
- 执行期间 patch `socket.socket.connect` 与 `connect_ex`：任何连接尝试都会立即失败并计数。实际报告 `network_connect_attempts=0`。pytest runner 同时通过 `papertrace.pytest.ini` 的 `--disable-socket` 及 `pytest-socket` 禁网。
- LLM 和 embedding 调用都由本地 fake 实现截获；没有 provider API 调用。真实调用路径仅覆盖 PaperQA 的本地文档、证据和 prompt 组装。

## 已验证行为

正向场景向同一个 `Docs` 添加 approved/excluded/pending 三条合成来源，真实检索获得三条 candidate contexts，然后用仅含 approved context 的新 `PQASession` 调用真实 aquery。实际最终 user prompt（完整文本保存在 JSON）包含 approved fact；`excluded_marker_in_final_prompt=false`、`pending_marker_in_final_prompt=false`。模型方法调用计数以本次 JSON 实际输出为准；answer 是模拟输出，不代表模型质量。

空 approved 场景仍保留同一 Docs 中三篇文献，但传入新的零 contexts 会话，返回拒答；embedding、summary、answer、lazy retrieval 调用全为 `0`。`get_evidence_if_no_contexts=false`，因此不会回退到隐式检索；pre、post 和 answer-iteration prompt 均设为 `None`。空场景返回的 session ID 不同于正向结果且没有 contexts（`session_is_fresh=true`），不复用先前的正向会话证据。

## 实际结果与证据文件

- `artifacts/verification/unblock-paperqa-pytest.txt`：使用上述指定 ini 的集成 smoke，结果 **1 passed**。
- `artifacts/verification/unblock-paperqa-smoke.json`：脚本实际输出的机器可读报告，`status=PASS`，含运行时版本、完整最终 prompt、正负向调用计数、LiteLLM cost-map 来源及 socket 连接计数。
- `artifacts/verification/unblock-paperqa-smoke.txt`：同一次脚本运行的 JSON stdout。
- `artifacts/verification/unblock-paperqa-collection.txt`：使用相同 runtime 与 ini 对 `test/` 执行的轻量 `--collect-only` 输出：**历史快照 207 tests collected（非当前总数）**，无 collection errors。这里只验证 collection，未执行整个上游/项目测试套件，不应解读为 207 个测试通过。

轻量 collection 命令：

```bash
RUNTIME=.local/unblock/runtime
/usr/bin/env -i \
  PATH="$PWD/$RUNTIME/.venv/bin:/usr/bin:/bin" \
  HOME="$PWD/$RUNTIME/home" \
  TMPDIR="$PWD/$RUNTIME/tmp" \
  XDG_CACHE_HOME="$PWD/$RUNTIME/cache" \
  PYTHONNOUSERSITE=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  "$PWD/$RUNTIME/.venv/bin/python" -m pytest \
  -c papertrace.pytest.ini --collect-only -q -p no:cacheprovider test
```
