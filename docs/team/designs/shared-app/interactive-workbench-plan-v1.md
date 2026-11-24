# 交互式公共工作台测试提案 v1

基于 PR #41 的 `f64baad3668f2ec996d97cd6d66d72d8744d9428`。该版本提供框架中立的 `papertrace.app.render_app` 和严格回环启动壳。本轮交付测试、计划与验证记录，具体测试版本待独立人工审查。

## 公共契约

目标模块为 `src/papertrace/workbench.py`，复用 `papertrace.app` 的 `AppPorts`、`AppRenderState` 和 `NAV_SECTIONS`。

```python
def render_interactive_workbench(
    ui: Any,
    *,
    ports: AppPorts,
    available_paths: Sequence[Path] = (),
    failed_document_ids: Sequence[str] = (),
    removable_document_ids: Sequence[str] = (),
    restorable_document_ids: Sequence[str] = (),
) -> AppRenderState: ...
```

`WorkbenchSession` 是本次渲染的临时控件状态载体，包含当前导航值和本轮已校验的动作参数。可用空选择初始化，不承担授权、持久化或跨重绘重放。入口每轮根据调用方控件值和候选参数生成状态，调用一次 `render_app(ui, ports=ports, selected_section=..., ...)`，原样返回该次装配的同一个 `AppRenderState` 对象。调用方注入的 UI 满足 Streamlit 风格控件及既有 A/E 展示方法的签名。

- 唯一导航使用 `ui.selectbox`，选项为 `library`、`retrieval`、`review`、`answer`、`reports`，默认 `library`。无效导航值显示固定错误 `The navigation selection is invalid.`，四个动作参数全部为空，并委托一次 `selected_section="library"` 进行只读回退。
- 仅在 `library` 绘制文件多选和库动作按钮。文件多选使用 `ui.multiselect`，显示和返回安全纯文件名字符串 `path.name`，保留候选输入顺序。重名无法消歧时排除所有冲突项，收到冲突或未知的选择值时拒绝整批并显示固定错误 `The file selection is invalid.`。空文件名、`.`、`..`、带路径分隔符或控制字符的名称均不可成为控件选项。仅内部映射持有原 `Path`。控件标签、选项、键、错误和 stdout/stderr 均不可泄露绝对私密路径、原始字节或凭据。
- 四个按钮键为 `import`、`retry`、`remove`、`restore`，可见文案分别表示导入、重试失败项、移除、恢复。仅当对应按钮本轮返回 `True` 且对应输入非空时转发。导入转发选中名称对应的原始 `Path` 为 `selected_paths`。重试、移除和恢复分别把调用方当轮提供的对应 ID 序列作为操作选择，传给 `retry_document_ids`、`remove_document_ids`、`restore_document_ids`。仅切换导航、勾选或重绘均保持动作参数为空。
- 文件候选列表只限定控件可选范围，A 服务仍是路径与文献状态授权方。即使候选中有未授权路径，选中后也由 `render_app` 转交 A 服务做整批校验。拒绝不产生摄取，界面采用脱敏错误。移除和恢复经 A 推进 `corpus_revision`，既有历史保持原样。
- 缺失的 B/C/D 阶段沿用 `render_app` 显示阶段名和 `BLOCKED`。研究历史与导出使用 `ports.reports_panel` 注入真实 E 面板，由 `render_app` 传入位置参数 `ui` 和仅关键字参数 `store`、`pending_record`、`current_snapshot_id`、`input_error`。工作台原样传递 `ports` 和非空 `pending_record`，由装配层脱敏上游 `pending_input_error`。A 发生 `FRESHNESS_MISMATCH` 时不显示健康概览，E 收到 `current_snapshot_id=None` 与非空脱敏错误。切到 E 或重绘均不隐式保存。E 自己处理用户显式的保存与导出操作。
- 工作台直接通过 `papertrace.app.render_app` 装配，禁止直接读取或调用 A/E 端口，禁止通过 `getattr`、`importlib`、`import_module` 或 `__import__` 动态访问或导入，禁止顶层导入 `streamlit` 或在任何作用域导入 `paperqa`。实际启动继续使用 `papertrace.app.main()` 已获批的绑定校验。若后续接入启动壳，复用该检查，在控件绘制前对严格字符串执行 `strip().lower()` 并仅接受 `127.0.0.1`、`localhost`、`::1`，缺失、读取异常和其他地址一律拒绝。本轮纯函数从调用方接收 UI，无端口绑定职责。

## 需求与验收

| 追踪 | 可测量结果 |
| --- | --- |
| FR-A-01/02、INV-02/05/06 | 正向显示真实共享契约生成的快照 ID。空操作计数为零。有效点击只转发对应选择。部分失败仅显式重试，移除和恢复各推进一次 revision 并保持历史不变。 |
| SEC-01、INV-06/08 | 未提供的名称在工作台拒绝，已提供但未授权的路径由 A 拒绝。两条路径摄取均为零，UI 和输出无合成敏感值。 |
| INV-03/04、FR-E-01/02、INV-05/08 | B/C/D 缺失时显示阶段名与阻断状态。E 收到原样待保存对象和健康快照或脱敏错误，五段导航期保存计数为零。 |
| QA-01、COST-01、GOV-01 | 12 个离线节点。AST 检查静态导入和直接端口引用，运行时 spy 检查真实装配委托，模型和网络调用预算为零。 |

测试复用入口提案的合成 A 服务、视图与历史存储，通过真实 `render_app` 驱动，E 使用签名严格的 spy。文件路径和错误详情均为合成数据。真实 Streamlit 点击、A/E 实体接入和完整回归属于后续验收。回环值矩阵已在现有入口测试覆盖。本轮收集应成功，执行应有且仅有 12 个 `IMPLEMENTATION_MISSING: papertrace.workbench` 失败。缺失检查位于每个用例体开头。重名与非法文件名、无效导航回退、单按钮隔离和首次渲染脱敏均在现有节点内验证。合成 A/E 端口守卫仅在真实 `render_app` 委托期间允许成员访问或调用。

仅写当前计划、`test/offline/test_interactive_workbench.py` 和 `docs/ai-use-log.yaml`。执行定向 Ruff、pytest 收集、pytest RED 与差异检查，记录真实退出码，提交具体测试版本供非作者审查。收到绑定该版本的独立人工批准后，才在后续实现轮接入控件和装配层，复跑本套测试与既有回归。如需撤回本轮提案，仅撤销本轮三文件差异。

### 跨平台夹具说明（独立复审反馈）
同一 `back\\slash.txt` 字符串在 POSIX 是含反斜杠的非法 basename，在 Windows 原生 Path 中则被解释为路径，basename 为合法的 `slash.txt`。测试按实际 basename 判断候选展示，同时在两种平台均直接伪造含反斜杠的控件选择字符串并要求整批拒绝。保留重名、控制字符、越界路径、零写入与脱敏检查；不缩窄 Windows 支持范围。修订前12节点不变，修订后完整 pytest/Ruff 仍需执行。
