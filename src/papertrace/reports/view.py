"""Module E page component: save, browse and download research history.

FR-E-01/02, INV-02/04/05/08, SEC-01, QA-01. The panel takes an injected ``ui``
object, so this module never imports Streamlit or a provider SDK; the public
assembly and the local preview supply the real widgets. Saving happens only on an
explicit button click, through the real :class:`~papertrace.reports.store.HistoryStore`,
which revalidates the exact serialized bytes before publishing. Rendering,
selection, rerender and downloads never write, never overwrite an existing record
id and never upgrade ``blocked``/``abstained``/``failed`` to ``released``. Only a
sanitized projection is displayed: original excerpts stay hidden unless a trusted
verifier grants export, nested local paths and credential-like metadata do not
appear, and every failure surfaces one fixed message instead of raw exceptions.
"""

from __future__ import annotations

from typing import Any, Final

from .export import export_json, export_markdown, history_detail, render_record
from .record import (
    InvalidRecord,
    RecordConflict,
    ResearchRecord,
    parse_record,
)
from .store import HistoryStore

__all__ = ["render_reports_panel"]

SAVE_LABEL: Final = "保存研究记录"
SAVE_KEY: Final = "papertrace-reports-save"
HISTORY_LABEL: Final = "历史研究记录"
HISTORY_KEY: Final = "papertrace-reports-history"
JSON_DOWNLOAD_LABEL: Final = "下载 JSON"
MARKDOWN_DOWNLOAD_LABEL: Final = "下载 Markdown"

RELEASE_LABELS: Final = {
    "released": "已发布",
    "blocked": "发布受阻",
}
DRAFT_LABELS: Final = {
    "draft": "已生成答案",
    "abstained": "拒答",
    "failed": "生成失败",
}
PUBLICATION_BLOCKED_REASON: Final = "PUBLICATION_COMMIT_UNAVAILABLE"
REASON_LABELS: Final = {
    PUBLICATION_BLOCKED_REASON: "发布提交不可用，记录保持发布受阻",
    "NO_APPROVED_EVIDENCE": "没有已批准的可用证据，记录保持发布受阻",
}

RELEASE_STATUS_NOTE: Final = "发布状态仅表示记录中模块 D 当时的宣告；本页面不授予或重建发布权。"
EXCERPT_NOTE: Final = "按默认策略隐藏原文摘录；本页面不提供勾选即授权的入口。"

STORAGE_UNAVAILABLE: Final = "历史记录当前不可读取，请检查历史存储后重试。"
RECORD_UNAVAILABLE: Final = "所选历史记录无法加载，未展示其他记录。"
SAVE_UNAVAILABLE: Final = "研究记录未能归档：记录可能已存在、无效或写入失败。"
PENDING_UNUSABLE: Final = "当前待保存包没有通过校验，已阻止归档。"
INPUT_UNAVAILABLE: Final = "当前输入或审核记录不可用，已阻止归档。"
NO_PENDING: Final = "当前没有可保存的研究记录；刷新或重新打开页面不会产生归档。"


def _text(ui: Any, kind: str, message: str) -> None:
    """Call an injected display helper; a missing one is a real wiring bug.

    The ``ui`` facade must expose the display helpers this panel uses, so a typo
    or a stale double fails loudly here instead of silently dropping a message.
    """
    method = getattr(ui, kind)
    method(message)


def _release_label(status: str) -> str:
    """Human label with the raw recorded enum kept visible for traceability."""
    return f"{RELEASE_LABELS.get(status, status)} ({status})"


def _draft_label(status: str) -> str:
    return f"{DRAFT_LABELS.get(status, status)} ({status})"


def _reason_text(code: str) -> str:
    explanation = REASON_LABELS.get(code)
    return f"{code}：{explanation}" if explanation else code


def _pending_is_usable(record: object) -> ResearchRecord | None:
    """Revalidate the serialized pending package before anything is displayed.

    A validated ``ResearchRecord`` deliberately shares its ``run_metadata`` dict,
    so a caller may poison it after construction. Re-parsing the serialized bytes
    proves that what would be published is still valid, and later renders the
    projection of that parsed copy rather than the caller's mutable object.
    """
    if not isinstance(record, ResearchRecord):
        return None
    try:
        serialized = record.model_dump_json(indent=None)
        reparsed = parse_record(serialized.encode("utf-8"))
    except (InvalidRecord, ValueError):
        return None
    except Exception:  # noqa: BLE001 - non-serializable metadata is also unusable
        return None
    if reparsed.record_id != record.record_id:
        return None
    return reparsed


def _render_summary(ui: Any, record: ResearchRecord, *, current_snapshot_id: str | None) -> None:
    """Show the sanitized status summary only; never raw model or caller text.

    The superseded flag comes from ``history_detail``, but ``current_snapshot_id``
    is caller-provided text and is deliberately not echoed into the page.
    """
    detail = history_detail(record, current_snapshot_id=current_snapshot_id)
    _text(ui, "write", f"问题：{record.question}")
    _text(ui, "write", f"发布状态：{_release_label(detail['release_status'])}")
    _text(
        ui,
        "write",
        f"回答状态：{_draft_label(detail['draft_status'])}；审核修订 {detail['review_revision']}",
    )
    _text(ui, "write", f"保存时间：{detail['saved_at']}")
    if detail["release_status"] == "blocked":
        for code in record.release.reason_codes:
            _text(ui, "write", f"原因：{_reason_text(code)}")
    _text(ui, "caption", RELEASE_STATUS_NOTE)
    if detail["superseded"]:
        _text(ui, "warning", "该记录的研究快照已被当前快照取代（superseded）；原始记录保持不变。")


def _render_history(
    ui: Any,
    store: HistoryStore,
    *,
    current_snapshot_id: str | None,
) -> str:
    """List and show one selected record; never writes.

    Returns ``"shown"`` when a record was displayed, ``"empty"`` when history is
    genuinely empty, and ``"failed"`` when listing/loading/projection failed. A
    failure is terminal for the panel: the pending area is not rendered, so a
    storage fault can never be masked by showing an unrelated record or body.
    """
    try:
        listed = store.list_records()
    except Exception:  # noqa: BLE001 - storage errors must not leak details
        _text(ui, "error", STORAGE_UNAVAILABLE)
        return "failed"

    if not listed:
        _text(ui, "info", "历史中还没有研究记录。")
        return "empty"

    options = [item.record_id for item in listed]
    selected = ui.selectbox(
        HISTORY_LABEL,
        options,
        index=0,
        format_func=lambda record_id: record_id,
        key=HISTORY_KEY,
    )
    if selected not in options:
        _text(ui, "error", RECORD_UNAVAILABLE)
        return "failed"

    try:
        loaded = store.load(selected)
    except Exception:  # noqa: BLE001 - never substitute another record
        _text(ui, "error", RECORD_UNAVAILABLE)
        return "failed"

    try:
        projection = render_record(loaded)
        json_body = export_json(loaded)
        markdown_body = export_markdown(loaded)
    except Exception:  # noqa: BLE001 - projection failures must fail closed
        _text(ui, "error", RECORD_UNAVAILABLE)
        return "failed"

    _render_summary(ui, loaded, current_snapshot_id=current_snapshot_id)
    _text(ui, "caption", EXCERPT_NOTE)
    ui.download_button(
        JSON_DOWNLOAD_LABEL,
        json_body,
        f"{loaded.record_id}.json",
        mime="application/json",
        key=f"{HISTORY_KEY}-json",
    )
    ui.download_button(
        MARKDOWN_DOWNLOAD_LABEL,
        markdown_body,
        f"{loaded.record_id}.md",
        mime="text/markdown",
        key=f"{HISTORY_KEY}-markdown",
    )
    ui.json(projection)
    return "shown"


def _render_pending(
    ui: Any,
    store: HistoryStore,
    *,
    pending_record: ResearchRecord | None,
    current_snapshot_id: str | None,
    input_error: object,
    show_summary: bool,
) -> None:
    """Render the save control, and the pending body only when safe to show.

    The save control is always present so an existing history never removes the
    ability to archive a new pending record. ``show_summary`` is False when a
    history record is already displayed, so an unselected pending body is never
    echoed next to it. Only the sanitized ``render_record`` projection is shown,
    never raw model fields.
    """
    if input_error is not None:
        _text(ui, "warning", INPUT_UNAVAILABLE)
        ui.button(SAVE_LABEL, disabled=True, key=SAVE_KEY)
        return

    if pending_record is None:
        _text(ui, "info", NO_PENDING)
        ui.button(SAVE_LABEL, disabled=True, key=SAVE_KEY)
        return

    pending = _pending_is_usable(pending_record)
    if pending is None:
        _text(ui, "error", PENDING_UNUSABLE)
        ui.button(SAVE_LABEL, disabled=True, key=SAVE_KEY)
        return

    if show_summary:
        _text(ui, "subheader", "待保存的研究记录")
        _render_summary(ui, pending, current_snapshot_id=current_snapshot_id)
        _text(ui, "caption", EXCERPT_NOTE)
        try:
            ui.json(render_record(pending))
        except Exception:  # noqa: BLE001 - projection failures fail closed
            _text(ui, "error", PENDING_UNUSABLE)
            ui.button(SAVE_LABEL, disabled=True, key=SAVE_KEY)
            return
    else:
        _text(ui, "caption", "已显示历史记录；新研究记录可直接归档，不会在此展开其正文。")

    if not ui.button(SAVE_LABEL, disabled=False, key=SAVE_KEY):
        return

    # Only an explicit click reaches the store; it revalidates the exact bytes.
    try:
        target = store.save(pending)
    except RecordConflict:
        _text(ui, "warning", SAVE_UNAVAILABLE)
        return
    except InvalidRecord:
        _text(ui, "warning", SAVE_UNAVAILABLE)
        return
    except Exception:  # noqa: BLE001 - fixed safe message, no local paths
        _text(ui, "error", SAVE_UNAVAILABLE)
        return
    _text(ui, "success", f"研究记录已归档：{target.name}")
    # Refresh so the newly saved record becomes visible, without ever rendering a
    # second copy of the already-displayed selectbox/download widgets in this
    # same rerun (which would raise a duplicate widget id in real Streamlit).
    if show_summary:
        # History was empty, so no history widgets exist yet: safe to render now.
        try:
            _render_history(ui, store, current_snapshot_id=current_snapshot_id)
        except Exception:  # noqa: BLE001 - display layer failures stay generic
            _text(ui, "error", STORAGE_UNAVAILABLE)
        return
    # History widgets were already shown this rerun. Rerun explicitly when the
    # host supports it; the injected test double has no ``rerun`` and must not be
    # given a fabricated success, so we defer the refresh explicitly and tell the
    # user how to see the new record, instead of duplicating widgets.
    rerun = getattr(ui, "rerun", None)
    if callable(rerun):
        rerun()
        return
    _text(
        ui,
        "info",
        "研究记录已归档；请刷新页面后即可在历史中查看这条新记录（本条消息不代表历史已列出该记录）。",
    )


def render_reports_panel(
    ui: Any,
    *,
    store: HistoryStore,
    pending_record: ResearchRecord | None = None,
    current_snapshot_id: str | None = None,
    input_error: object = None,
) -> None:
    """Render the E research-history panel with a caller-injected ``ui`` facade.

    ``ui`` supplies ``button``, ``selectbox``, ``download_button``, ``json`` and
    the display helpers (``write``/``caption``/``info``/``warning``/``error``/
    ``success``/``subheader``). Rerendering, switching history and downloading
    never persist anything. ``input_error`` only blocks saving with one fixed
    neutral message and its raw text is never displayed. The save control is
    always rendered, but when history already exists the selected record's detail
    is shown while the unselected pending body is not, so no unselected body can
    leak. A storage failure stops the panel rather than substituting another
    record. After a successful save from an empty history the list is rendered
    immediately; when history widgets were already shown, the host's ``rerun`` is
    used if present, otherwise the refresh is deferred explicitly (never a second
    copy of the same widgets in one rerun).
    """
    _text(ui, "subheader", "研究历史与来源导出")

    try:
        outcome = _render_history(ui, store, current_snapshot_id=current_snapshot_id)
    except Exception:  # noqa: BLE001 - display layer failures stay generic
        _text(ui, "error", STORAGE_UNAVAILABLE)
        return
    if outcome == "failed":
        # Never fall back to an unrelated record or an unverified pending body.
        return

    _render_pending(
        ui,
        store,
        pending_record=pending_record,
        current_snapshot_id=current_snapshot_id,
        input_error=input_error,
        show_summary=outcome == "empty",
    )
