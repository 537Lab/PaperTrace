# 共享应用唯一公共入口（A→E 接线与 B/C/D 显式阻断）：测试提案 v1（待独立审核）

日期：2026-11-23。关联 Issue：#37。本 PR **仅包含设计与离线测试提案**，不包含 `src/papertrace/app.py` 实现源码，不修改任何模块既有业务源码、共享契约、上游基线或 CI 门禁。

## 1. 边界与职责依据

- 依据 `docs/team/integration-contract.md` 第 1 节：
  - 模块 A（`537Lab`）负责**唯一公共应用入口**的导航与依赖注入装配；其他成员不另建第二套公共导航，也不互相修改对方模块源码。
  - UI 只负责展示状态、收集显式用户操作并调用注入的模块视图/服务，绝不自建影子审批或发布状态机；绕过 UI 直接调服务时授权与发布边界保持不变。
- 关联上游依赖（当前均处于独立分支/PR，尚未合并进 `main`）：
  - A 文献库核心（PR #17）与中立视图适配层（PR #30 / PR #36：`library_overview`、`import_selected`、`retry_selected`、`remove_selected`、`restore_selected`）。
  - E 保存/历史/导出面板（PR #31 / PR #35）：必须严格按关键字参数签名调用 `render_reports_panel(ui, *, store=..., pending_record=..., current_snapshot_id=..., input_error=...)`（注意 `*` 之后的 keyword-only 约束，避免位置参数调用导致 `TypeError`）。
  - B（检索/摄取回执）、C（人工审核 ledger）、D（受控回答与确定性发布门）：在本公共入口未获正式端到端接入前，不得用伪造结果或假 `ResearchRecord` 冒充全流程跑通。

## 2. 拟议公共入口契约（`src/papertrace/app.py`）

待本测试提案获非作者独立 Approve 后，再通过独立实现 PR 编写 `src/papertrace/app.py`：

1. **唯一公共导航常量**：
   - `NAV_SECTIONS: tuple[str, ...]`：至少包含 `"library"`（文献库 A）、`"reports"`（研究历史与导出 E），以及显式阻断状态的 `"retrieval"`、`"review"`、`"answer"`。
   - 不额外引入第二套公共导航或替代页面。
2. **依赖注入容器 `AppPorts`（`frozen=True`）**：
   - `library_view`: 符合 A 视图适配契约的对象（提供 `library_overview`、`import_selected`、`retry_selected`、`remove_selected`、`restore_selected`）。
   - `library_service`: 符合 A `CorpusService` 契约的实例（授权/拒绝仍全部在服务端执行）。
   - `reports_panel`: 符合 E `render_reports_panel(ui, *, store=..., pending_record=..., current_snapshot_id=..., input_error=...)` 的可调用对象。
   - `history_store`: 符合 E `HistoryStore` 契约的存储实例。
   - `pending_record: Any = None`：可选待保存研究记录；当真实 C/D 尚未产出时必须为 `None`，公共入口绝不合成假 `ResearchRecord` 或把 `blocked` 升级为 `released`。
   - `pending_input_error: object = None`：外部输入错误信号，安全透传给 E 面板以阻断归档。
   - `retrieval_port: Any = None`、`review_port: Any = None`、`answer_port: Any = None`：B/C/D 可选端口；缺失时页面显式标注 `BLOCKED`，不得静默发起外部模型或网络请求。
3. **框架中立装配渲染函数**：
   ```python
   render_app(
       ui: Any,
       *,
       ports: AppPorts,
       selected_section: str = "library",
       selected_paths: Sequence[Path] = (),
       retry_document_ids: Sequence[str] = (),
       remove_document_ids: Sequence[str] = (),
       restore_document_ids: Sequence[str] = (),
   ) -> AppRenderState
   ```
   - `AppRenderState`（`frozen=True`）暴露脱敏后的页面状态：`active_section`、`snapshot_id`、`corpus_revision`、`library_error`、`import_feedback`、`blocked_stages`（例如缺失端口对应的 `("retrieval", "review", "answer")`）、`reports_invoked`。
   - **安全与一致性规则**：
     - 渲染或切换导航绝不隐式触发导入、重试、移除、恢复或保存研究记录。
     - 显式传入 `selected_paths` 时仅转发给 `library_view.import_selected(ports.library_service, selected_paths)`；未选/越界文件仍由 A 服务整批拒绝（零摄取），UI 捕获异常并仅展示脱敏通用错误，不泄露本地绝对路径或凭据字符串。
     - 部分导入失败时保持 `complete=False`，清晰向用户渲染失败项文件名、状态（`failed`）、阶段（`stage`）、原因码（`reason_code`）与未完成警示（`warning`/`error`），不伪造 ready，也不允许空白页面。
     - 每次读取概览执行 `library_view.library_overview(ports.library_service)` 并向用户展示真实 `snapshot_id`；若触发 `FRESHNESS_MISMATCH` 或服务异常，fail-closed 阻断概览显示，并将 `current_snapshot_id=None` 与非空通用 `input_error` 传入 E 面板，阻止在一致性破损状态下保存。
     - 调用 E 面板时必须使用关键字参数 `reports_panel(ui, store=ports.history_store, pending_record=ports.pending_record, current_snapshot_id=..., input_error=...)`：
       - 当 `ports.pending_record` 非 `None` 时，必须将该对象原样传给 E 面板，不得静默丢弃或隐式写入；
       - 当 A 概览健康但 `ports.pending_input_error` 非 `None` 时，必须向 E 面板传入非空脱敏通用 `input_error`，且绝不将原始异常/路径/凭据值渲染泄露到 UI；
       - 公共入口自身不得写入 `history_store`，也不得在 `snapshot_id` 漂移后迁移或篡改已有历史记录。
     - 当 `retrieval_port` / `review_port` / `answer_port` 任一为 `None` 时，`blocked_stages` 必须显式包含缺失阶段；用户切换至缺失阶段时必须在 UI 中真实渲染包含该阶段标识与明确阻断/不可用提示的可见消息（`warning`/`info`/`error`），绝不允许空白页面，绝不合成 `ResearchRecord`、`released` 或调用外部模型/网络。
     - `src/papertrace/app.py` 顶层不得直接 `import paperqa` 或强依赖 `import streamlit`（本地可选 Streamlit 启动壳 `main(argv=None) -> int` 仅在显式运行时加载；**严格 fail-closed 仅接受明确配置为 `str` 类型且经首尾空白裁剪与小写归一化后命中三值白名单 `{"127.0.0.1", "localhost", "::1"}` 的本机回环地址**，当 `server.address` 为 `None`、空字符串/纯空白、非 `str` 对象（即使 `__str__` 仿冒回环地址）、`127.0.0.2` / `localhost.example` / `0.0.0.0` / `::` / 局域网 IP、`st.config` 为 `None` 或缺属性、或配置读取抛异常时，一律拒绝继续渲染页面并返回退出码 `2`，且不向 stdout/stderr/UI 泄露原始异常消息、路径或凭据；无 `streamlit` 环境导入模块不报错且 `main()` 安全返回退出码 `2` 并向 stderr 输出包含 `streamlit` 说明的固定安全提示，干净 CI 环境 `mypy`/`ruff`/`architecture` 均需通过）。

## 3. 读写路径、工具与依赖边界

- 本提案 PR 仅新增/修改：
  - `docs/team/designs/shared-app/entrypoint-plan-v1.md`
  - `test/offline/test_app_entrypoint.py`
  - `docs/ai-use-log.yaml`
- 不新增任何第三方依赖，不修改 `pyproject.toml`、`uv.lock`、`requirements*.lock`、`contracts.py` 或任何已有模块源码。
- 全程离线合成数据，使用 `--disable-socket` 断言零网络与零付费模型调用。

## 4. 离线测试清单与不变量映射（17 项测试函数 / 32 个收集节点 RED 测试）

位于 `test/offline/test_app_entrypoint.py`，使用真实 `papertrace.contracts.CorpusSnapshot` / `DocumentVersion` 与严格匹配 A（PR #36）/ E（PR #35）真实签名的离线受控桩（`_RecordingUI` 已对齐 `button(disabled=...)`、`selectbox(index=...)`、`download_button(label, data, file_name, mime, ...)` 控件签名，但仍仅作为单元/装配边界替身，不替代真 A/E 组件联调与真实 Streamlit 点击验收）：

1. `test_entrypoint_exposes_single_navigation_and_renders_real_snapshot_without_saving`（FR-A-01、FR-E-01、INV-02/05）：唯一导航、真实快照身份向用户真实渲染、渲染零导入零保存。
2. `test_entrypoint_forwards_only_explicit_selection_and_rejects_unselected_or_outside_paths`（FR-A-01、SEC-01）：未选中/越界路径零摄取，fail-closed 且不泄露绝对路径。
3. `test_entrypoint_surfaces_partial_import_failure_without_claiming_complete`（FR-A-02、INV-06）：部分失败保持 `complete=False`，且正向断言失败文件名、状态、阶段、原因码及警告消息真正渲染给用户。
4. `test_entrypoint_fails_closed_on_snapshot_freshness_mismatch_and_blocks_e_save`（INV-02/05、QA-01）：`FRESHNESS_MISMATCH` 时阻断概览并向 E 传 `current_snapshot_id=None` + `input_error`。
5. `test_entrypoint_passes_keyword_only_arguments_to_reports_panel_and_preserves_blocked_history`（FR-E-01/02、INV-04/08）：强校验 E 关键字参数调用契约、不升级 `blocked` 为 `released`、不自动写历史。
6. `test_entrypoint_snapshot_drift_does_not_migrate_or_mutate_historical_records`（INV-02/05）：A 快照变化后传递新 `current_snapshot_id`，但历史记录保持原绑定快照且不被篡改。
7. `test_entrypoint_blocks_missing_b_c_d_ports_without_synthesizing_research_record_or_release`（INV-03/04、GOV-01）：B/C/D 缺失时正向断言 UI 渲染阶段名与阻断提示消息，绝不空白，绝不合成假 `ResearchRecord` 或 `released`。
8. `test_entrypoint_redacts_private_paths_and_source_bytes_from_ui_and_errors`（SEC-01、QA-01）：UI 文本与错误提示均不含绝对私密路径、凭据字样或原文原始字节。
9. `test_entrypoint_delegates_explicit_retry_remove_restore_without_bypassing_service`（FR-A-02、INV-02）：显式重试/移除/恢复经 A 视图层委托执行，拒绝重试 ready 项。
10. `test_entrypoint_navigation_switch_never_triggers_write_or_implicit_save`（FR-E-01、INV-05）：在各导航页间切换零写入、零保存。
11. `test_entrypoint_makes_zero_external_network_or_provider_calls`（COST-01、SEC-01）：全程无外部网络与模型调用。
12. `test_entrypoint_module_has_no_top_level_streamlit_or_paperqa_import`（ADR-001、B-only 架构边界）：静态 AST 校验无顶层 `streamlit` 与任意 `paperqa` 导入。
13. `test_entrypoint_forwards_non_none_pending_record_identically_to_reports_panel`（FR-E-01、INV-04/05）：A 概览健康时，明确标注为合成对象的非空 `pending_record` 原样（同对象引用）传给 E 面板，且零隐式保存。
14. `test_entrypoint_forwards_upstream_input_error_when_library_healthy_without_leaking_raw_value`（FR-E-01、SEC-01、INV-04）：A 概览健康时，非空上游 `pending_input_error` 转为非空脱敏通用错误传给 E 面板，且原始敏感路径/凭据不泄露到 UI 或错误值中。
15. `test_entrypoint_main_refuses_unset_empty_unreadable_or_non_loopback_address`（计划 §2、SEC-01 防泄漏，13 组参数化负测）：当 `server.address` 为 `None`、空字符串、纯空白、配置读取抛异常、`st.config` 为 `None`、`st.config` 属性缺失、整型、仿冒 `__str__` 的非字符串对象、`0.0.0.0`、`::`、`127.0.0.2`、`localhost.example` 或局域网 IP 时，均拒绝渲染（零 `title`/`info` 调用）、返回退出码 `2` 且 stdout/stderr/UI 均不泄露原始异常标记、路径或凭据。
16. `test_entrypoint_main_accepts_explicit_loopback_address`（计划 §2，4 组参数化正测）：明确配置的 `127.0.0.1`、`localhost`、`::1`（含大小写与首尾空白归一化）允许渲染并返回 `0`。
17. `test_entrypoint_main_fails_closed_when_streamlit_missing`（计划 §2、SEC-01）：在全新模块导入前注入缺失 `streamlit` 哨兵，验证顶层导入成功且 `main()` 返回退出码 `2`、stdout 为空、stderr 含固定 `streamlit` 提示且无 Traceback。

## 5. 验证口径与限制

- 本提案 PR 为 RED 测试提案：在 `src/papertrace/app.py` 存在前，所有 32 个测试节点可无错收集并在 `IMPLEMENTATION_MISSING: papertrace.app` 处明确失败，不宣称任何实现功能已通过。
- 本离线单元测试使用受控桩验证单元与装配契约，不替代真实 A/E 合并后的真实组件集成验收与真实 Streamlit 点击验收；该端到端验收将在后续阶段单独执行。
- 后续实现 PR 需在非作者独立 Approve 本提案精确 HEAD 后重新基于该新 HEAD 创建（避免早于新批准时间触发门禁错误）；因受保护的 `opencode.jsonc` 目前仅放行 5 个模块子目录、未对 `src/papertrace/app.py` 授权 `edit`，需由项目负责人/团队明确确认是走受保护配置的窄权限放行后再跑受限 OpenCode 会话，还是批准受监督 AI 替代实现方案。
