# PaperTrace 模块 B 开发计划 v1（待审批）

> 负责人：李亚飞  
> 模块：B｜证据检索、PaperQA2 适配与中立端口  
> 状态：待本人确认及独立组员审批；本计划不授权直接编写业务源码

## 1. 目标与验收标准

实现模块 B：接收固定的 `CorpusSnapshot`、研究问题和获批检索配置，通过固定 PaperQA2 异步接口检索候选证据，并转换为现有共享契约 `EvidenceRecord`；同时向模块 D 提供中立生成端口，但不决定证据是否被接受，也不决定答案是否发布。

- `FR-B-01`：所有候选证据均绑定正确的 snapshot、document、version、原文和可回查 locator；合格率必须为 100%。
- `FR-B-02`：明确区分空结果、超时、解析错误和调用失败；不得伪造证据或静默切换模型，未报告失败数必须为 0。
- `INV-02`：证据身份、论文版本和 locator 可稳定复核。
- `INV-08`：不加载不可信第三方 pickle/index。
- 与 D 协作：返回实际 `sent` 证据 ID、raw 输出、引用别名映射和调用计数；空 approved 集合不得进入模型工厂、SDK 或 HTTP。

## 2. 输入、输出与职责边界

**输入：**A 提供的不可变 `CorpusSnapshot`、研究问题、获批检索/生成配置；D 在生成阶段提供的已审核证据集合。

**输出：**符合现有 `EvidenceRecord` 的候选证据；明确的空结果/错误状态；生成端口的实际 sent ID、raw 输出、引用映射及尝试记录。

**不属于 B：**论文导入和版本管理（A）、人工接受/排除（C）、prompt/预算/裁剪和发布决定（D）、历史保存与报告导出（E）。B 不给 `EvidenceRecord` 增加 accepted/status，不把 `Context.id` 当作团队证据身份，不向其他模块传递可变 `Docs` 或 `PQASession`。

## 3. 精确路径范围

### 只读

- `AGENTS.md`、`Prompt.md`
- `docs/team/module-B.md`
- `docs/team/integration-contract.md`
- `docs/req/requirements.yaml`
- `src/papertrace/contracts.py`
- `src/paperqa/docs.py`、`src/paperqa/types.py`、`src/paperqa/core.py`

### 计划批准后，仅测试准备阶段可写

- `docs/team/designs/module-B/plan-v1.md`
- `test/offline/test_retrieval.py`
- `test/fixtures/retrieval/`

此阶段严禁修改任何 `src/` 文件。

### 测试 commit 获独立组员批准后才可写

- `src/papertrace/retrieval/`：PaperQA2 adapter、检索/生成 port、映射、调用账目和 B 自己的 view。

### 禁止擅自修改

- `src/papertrace/contracts.py`、共享 fixtures、其他成员模块目录
- `src/paperqa/`、`packages/`、原 `tests/`、`pyproject.toml`、`uv.lock`
- CI、Prompt、依赖锁、共享需求和团队规则

如确需越界、增加依赖、访问网络/模型或修改公共数据，立即停止并另行申请审批。

## 4. 测试与最小 PaperQA2 基线

先用本地 synthetic fixtures 和 fake model，不使用私人凭据、不收费、不访问网络：

1. 正常 Context 能转换为原文与摘要分离、身份稳定、locator 可回查的 `EvidenceRecord`。
2. snapshot/version 不匹配、locator 无法验证时必须拒绝，不能猜页码或行号。
3. 空结果、超时、解析错误和调用失败必须分别显示；重试有界，不静默换模型。
4. 摘要变化不改变证据身份；模型评分或恶意 excerpt 不能产生人工接受状态。
5. 不可信 pickle/index 必须拒绝。
6. 生成端口记录实际 sent、raw 输出和引用映射；未知引用原样交给 D，不能偷偷删除。
7. D 传入空 approved 集合时，模型工厂、SDK、HTTP 和生成调用计数全部为 0。
8. 最小技术基线核实 `Docs.aadd`、`aget_evidence`、`aquery` 的本地离线路径，并检查自动补证、citation inference、embedding、pre/post 和 session 复用风险；fake 成功不宣称真实模型质量通过。

## 5. 实现顺序与验证

1. 本人确认本计划；推荐由模块 C 负责人进行独立审阅。
2. 在 OpenCode `papertrace-plan` 阶段输出精确计划并停止，保存真实会话。
3. 计划获批后，仅创建测试、synthetic fixtures 和设计记录，运行 RED 测试。
4. 创建测试提案 PR；由未参与测试实现的组员批准该精确 commit。
5. 从获批测试 head 创建实现分支，再编写 `src/papertrace/retrieval/`。
6. 运行模块测试、全部离线测试、Ruff、mypy 和 schema gate；如实记录命令、退出码与未运行项。
7. 创建实现 PR，并在正文写入 `Test approval PR: #实际编号`，等待独立审查。

建议验证命令：

```sh
.venv/bin/python -m pytest -c papertrace.pytest.ini test/offline/test_retrieval.py
.venv/bin/python -m pytest -c papertrace.pytest.ini test/offline
.venv/bin/python -m ruff check --config papertrace.ruff.toml src/papertrace test/offline scripts
.venv/bin/python -m mypy --config-file mypy.ini src/papertrace
.venv/bin/python scripts/gates.py --gate schema
```

## 6. 停止条件与证据

遇到公共契约不够用、A 输出不符合现有 `CorpusSnapshot`、无法得到真实 locator、需要新增依赖/网络/收费模型、或测试要求修改其他模块时，停止并请团队审批，不自行修改数据或规则。

保留证据：`docs/team/designs/module-B/plan-v1.md`、OpenCode raw/annotated transcript、计划批准记录、测试 PR 及精确 commit 审批、实现 PR、验证输出和本人 AI-use log。未真实执行的项目标记为 `NOT_RUN` 或 `BLOCKED`，不得补造。
