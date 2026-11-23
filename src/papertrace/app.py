"""Single shared public application entrypoint for PaperTrace (A -> E wiring).

Architecture: docs/team/integration-contract.md section 1, Issue #37, PR #39.
This module provides one framework-neutral navigation and dependency-injection
assembly layer. It never imports ``paperqa``, never performs top-level
``streamlit`` imports, never fabricates a ``ResearchRecord`` or ``released``
status when upstream B/C/D ports are absent, and never bypasses A or E
server-side authorization and persistence invariants.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

__all__ = [
    "NAV_SECTIONS",
    "AppPorts",
    "AppRenderState",
    "main",
    "render_app",
]

NAV_SECTIONS: Final[tuple[str, ...]] = (
    "library",
    "retrieval",
    "review",
    "answer",
    "reports",
)

LIBRARY_ACTION_BLOCKED: Final = (
    "文献库操作被安全策略拒绝或执行失败，请检查所选路径与状态后重试。"
)
SNAPSHOT_MISMATCH_ERROR: Final = (
    "当前文献快照与新鲜度令牌不一致，已阻止展示与归档。"
)
UPSTREAM_INPUT_ERROR: Final = (
    "上游阶段输入或审核状态不可用，已阻止归档。"
)
PARTIAL_IMPORT_WARNING: Final = (
    "批次导入未全部就绪（complete=False），请检查失败项阶段与原因码。"
)
STREAMLIT_UNAVAILABLE: Final = (
    "本地公共页面启动壳需要可选依赖 streamlit；当前环境未安装，已安全退出。\n"
)
NON_LOOPBACK_REFUSED: Final = (
    "公共应用本地预览仅允许绑定本机回环地址（127.0.0.1 / localhost / ::1）。\n"
)


@dataclass(frozen=True, slots=True)
class AppPorts:
    """Explicit dependency-injection container for the shared public entrypoint."""

    library_view: Any
    library_service: Any
    reports_panel: Any
    history_store: Any
    pending_record: Any = None
    pending_input_error: object = None
    retrieval_port: Any = None
    review_port: Any = None
    answer_port: Any = None


@dataclass(frozen=True, slots=True)
class AppRenderState:
    """Sanitized return projection for callers and offline verification."""

    active_section: str
    snapshot_id: str | None
    corpus_revision: int | None
    library_error: str | None
    import_feedback: Any
    blocked_stages: tuple[str, ...]
    reports_invoked: bool


def _blocked_stages(ports: AppPorts) -> tuple[str, ...]:
    """Enumerate upstream stages whose real ports are currently absent."""
    missing: list[str] = []
    if ports.retrieval_port is None:
        missing.append("retrieval")
    if ports.review_port is None:
        missing.append("review")
    if ports.answer_port is None:
        missing.append("answer")
    return tuple(missing)


def _render_library_section(
    ui: Any,
    *,
    overview: Any,
    import_feedback: Any,
    library_error: str | None,
) -> None:
    """Render sanitized A library overview and explicit batch import feedback."""
    ui.subheader("文献库管理（模块 A）")
    if library_error is not None:
        ui.error(library_error)
    if overview is not None:
        ui.caption(
            f"当前快照 snapshot_id={overview.snapshot_id} | revision={overview.corpus_revision}"
        )
        for row in overview.rows:
            ui.write(
                f"{row.document_id} | {row.title} | {row.source_name} | status={row.status}"
            )
    if import_feedback is not None:
        if not import_feedback.complete:
            ui.warning(PARTIAL_IMPORT_WARNING)
        for item in import_feedback.rows:
            summary = (
                f"{item.source_name} | status={item.status} "
                f"| stage={item.stage} | reason={item.reason_code}"
            )
            if item.status != "ready":
                ui.error(summary)
            else:
                ui.write(summary)


def _render_blocked_stage(ui: Any, stage: str) -> None:
    """Render an explicit visible BLOCKED notice for an absent B/C/D stage."""
    ui.subheader(f"阶段 {stage}（BLOCKED / 未接通）")
    ui.warning(
        f"阶段 {stage} 当前处于 BLOCKED（受阻/未接通）状态："
        "尚未注入真实模块端口，不会合成研究记录，也不会发起外部模型或网络调用。"
    )


def render_app(
    ui: Any,
    *,
    ports: AppPorts,
    selected_section: str = "library",
    selected_paths: Sequence[Path] = (),
    retry_document_ids: Sequence[str] = (),
    remove_document_ids: Sequence[str] = (),
    restore_document_ids: Sequence[str] = (),
) -> AppRenderState:
    """Render the single shared PaperTrace entrypoint using injected module ports.

    Rendering or switching navigation sections never triggers implicit imports
    or history writes. Explicit library actions delegate exclusively to the
    injected A view adapter; reports rendering delegates to the injected E
    panel using its keyword-only signature.
    """
    active_section = selected_section if selected_section in NAV_SECTIONS else "library"
    blocked = _blocked_stages(ports)
    library_error: str | None = None
    import_feedback: Any = None
    overview: Any = None

    if active_section == "library":
        try:
            if selected_paths:
                import_feedback = ports.library_view.import_selected(
                    ports.library_service, tuple(selected_paths)
                )
            if retry_document_ids:
                import_feedback = ports.library_view.retry_selected(
                    ports.library_service, tuple(retry_document_ids)
                )
            if remove_document_ids:
                overview = ports.library_view.remove_selected(
                    ports.library_service, tuple(remove_document_ids)
                )
            if restore_document_ids:
                overview = ports.library_view.restore_selected(
                    ports.library_service, tuple(restore_document_ids)
                )
        except Exception:  # noqa: BLE001 - fail closed without leaking raw paths/secrets
            library_error = LIBRARY_ACTION_BLOCKED

    if overview is None:
        try:
            overview = ports.library_view.library_overview(ports.library_service)
        except Exception:  # noqa: BLE001 - fail closed on FRESHNESS_MISMATCH or service error
            overview = None
            library_error = SNAPSHOT_MISMATCH_ERROR

    snapshot_id: str | None = overview.snapshot_id if overview is not None else None
    corpus_revision: int | None = overview.corpus_revision if overview is not None else None
    reports_invoked = False

    if active_section == "library":
        _render_library_section(
            ui,
            overview=overview,
            import_feedback=import_feedback,
            library_error=library_error,
        )
    elif active_section == "reports":
        effective_input_error: str | None = None
        if snapshot_id is None:
            effective_input_error = SNAPSHOT_MISMATCH_ERROR
        elif ports.pending_input_error is not None:
            effective_input_error = UPSTREAM_INPUT_ERROR
        ports.reports_panel(
            ui,
            store=ports.history_store,
            pending_record=ports.pending_record,
            current_snapshot_id=snapshot_id,
            input_error=effective_input_error,
        )
        reports_invoked = True
    elif active_section in blocked:
        _render_blocked_stage(ui, active_section)
    else:
        ui.subheader(f"阶段 {active_section}")
        ui.info(f"阶段 {active_section} 端口已注入。")

    return AppRenderState(
        active_section=active_section,
        snapshot_id=snapshot_id,
        corpus_revision=corpus_revision,
        library_error=library_error,
        import_feedback=import_feedback,
        blocked_stages=blocked,
        reports_invoked=reports_invoked,
    )


def _streamlit() -> Any:
    """Load optional local-only Streamlit without dynamic imports or CI stubs."""
    if TYPE_CHECKING:
        st: Any = None
    else:
        import streamlit as st

    return st


def _is_loopback(address: str | None) -> bool:
    """Allow local-only loopback bindings for the optional Streamlit shell."""
    return address in {None, "", "127.0.0.1", "localhost", "::1"}


def main(argv: Sequence[str] | None = None) -> int:
    """Optional local loopback Streamlit shell; fails closed when Streamlit is absent."""
    del argv
    try:
        st = _streamlit()
    except Exception:  # noqa: BLE001 - Streamlit is an optional local convenience
        sys.stderr.write(STREAMLIT_UNAVAILABLE)
        return 2
    try:
        address = st.config.get_option("server.address")
    except Exception:  # noqa: BLE001 - treat unreadable config as unset
        address = None
    if not _is_loopback(address):
        sys.stderr.write(NON_LOOPBACK_REFUSED)
        return 2
    st.title("PaperTrace 科研证据审核台（公共入口）")
    st.info(
        "请通过应用装配工厂注入已验证的模块 A/E 端口运行 render_app；"
        "未接入的 B/C/D 阶段保持 BLOCKED 状态。"
    )
    return 0
