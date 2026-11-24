# B 侧 QUAL-02 回答请求测试提案

基线为 B 生成调用账目 PR #34 的 `a9440e6767e9ba90642dbe5cf2bb46a526125540`。本轮在正常 B 端口 `Gateway.generate` 上执行真实 PaperQA2 `Docs.aquery`，以合成模型捕获 `call_single` 的消息。契约对应 FR-D-03、INV-01 和 INV-07。

## 测试与验收

- 使用仓库固定集 `QUAL-02` 的问题与证据原文，覆盖正序、逆序和裁剪子集。模型入口只收到 system、user 两条消息。Gate 4 的请求检查逐项核对问题、获准证据正文和实际发送顺序。测试使用该合成用例生成的规范证据 ID 来核对 B 生产路径。评估工具接入固定集时需要在发送前绑定固定集 ID。
- 模型收到的 system 正文须逐字等于 `prompts/answer-system-v1.0.txt`。D 已确认从 `prompt_v1.0.yaml` 取六行 system 原文，保存为 UTF-8 并保留末尾换行。
- 测试同时核对预算计数输入、实际发送 ID、引用映射和调用账目。空获准集、选择待审证据及超预算各有零调用对照。
- 本轮仅提交测试、计划及 AI 使用披露。当前分支的模板正文和缺失的提示词文件分别触发三项和一项预期失败。测试提案获独立同学在 GitHub 对具体提交批准后，再进入 B 侧源码实现。

## 离线复跑

```sh
LITELLM_LOCAL_MODEL_COST_MAP=True .venv/bin/python -m pytest -q -c papertrace.pytest.ini test/offline/test_retrieval.py test/offline/test_b_answer_request.py --tb=short
.venv/bin/python -m ruff check --config papertrace.ruff.toml test/offline/test_b_answer_request.py
```

当前预期为 73 通过和 4 失败。真实模型调用为零。
