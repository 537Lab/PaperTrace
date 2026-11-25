"""Shared application entrypoint and framework-neutral panel wiring."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

NAV_SECTIONS = ("library", "retrieval", "review", "answer", "reports")

_LIBRARY_ERROR = "The library operation could not be completed safely."
_REPORT_INPUT_ERROR = "Report input is unavailable or invalid."
_LOOPBACK_ERROR = "PaperTrace requires an explicit local loopback server.address."


class _ReportsPanel(Protocol):
    def __call__(
        self,
        ui: Any,
        /,
        *,
        store: Any,
        pending_record: Any,
        current_snapshot_id: str | None,
        input_error: str | None,
    ) -> object: ...


@dataclass(frozen=True, slots=True)
class AppPorts:
    library_view: Any
    library_service: Any
    reports_panel: _ReportsPanel
    history_store: Any
    pending_record: Any = None
    pending_input_error: object = None
    retrieval_port: Any = None
    review_port: Any = None
    answer_port: Any = None


@dataclass(frozen=True, slots=True)
class AppRenderState:
    active_section: str
    snapshot_id: str | None
    corpus_revision: int
    library_error: str | None
    import_feedback: Any
    blocked_stages: tuple[str, ...]
    reports_invoked: bool


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
    """Render one section and delegate explicit library actions to A."""
    if selected_section not in NAV_SECTIONS:
        raise ValueError("Unknown application section.")

    blocked_stages = tuple(
        stage
        for stage, port in (
            ("retrieval", ports.retrieval_port),
            ("review", ports.review_port),
            ("answer", ports.answer_port),
        )
        if port is None
    )
    view = ports.library_view
    service = ports.library_service
    feedback = []
    snapshot_id: str | None = None
    corpus_revision = 0
    library_error = None
    try:
        if selected_section == "library":
            if selected_paths:
                feedback.append(view.import_selected(service, tuple(selected_paths)))
            if retry_document_ids:
                feedback.append(view.retry_selected(service, tuple(retry_document_ids)))
            if remove_document_ids:
                view.remove_selected(service, tuple(remove_document_ids))
            if restore_document_ids:
                view.restore_selected(service, tuple(restore_document_ids))
        overview = view.library_overview(service)
        snapshot_id, corpus_revision = overview.snapshot_id, overview.corpus_revision
    except Exception:
        library_error = _LIBRARY_ERROR
        ui.error(library_error)

    reports_invoked = selected_section == "reports"
    if selected_section == "library":
        if library_error is None:
            ui.caption(f"Snapshot: {snapshot_id}")
            for row in overview.rows:
                ui.json({"file": row.source_name, "status": row.status})
        for batch in feedback:
            if not batch.complete:
                ui.warning("The library import is incomplete.")
            for row in batch.rows:
                if row.status == "failed":
                    ui.json(
                        {
                            "file": row.source_name,
                            "status": row.status,
                            "stage": row.stage,
                            "reason_code": row.reason_code,
                        }
                    )
    elif reports_invoked:
        effective_input_error = library_error
        if effective_input_error is None and ports.pending_input_error is not None:
            effective_input_error = _REPORT_INPUT_ERROR
        ports.reports_panel(
            ui,
            store=ports.history_store,
            pending_record=ports.pending_record,
            current_snapshot_id=snapshot_id,
            input_error=effective_input_error,
        )
    elif selected_section in blocked_stages:
        ui.warning(f"{selected_section}: BLOCKED. The stage is unavailable.")
    else:
        ui.info(f"{selected_section}: Panel integration is pending.")

    return AppRenderState(
        active_section=selected_section,
        snapshot_id=snapshot_id,
        corpus_revision=corpus_revision,
        library_error=library_error,
        import_feedback=feedback[-1] if feedback else None,
        blocked_stages=blocked_stages,
        reports_invoked=reports_invoked,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Start the optional Streamlit shell after validating its bind address."""
    try:
        if TYPE_CHECKING:
            st: Any = None
        else:
            import streamlit as st
    except ImportError:
        print("The PaperTrace UI requires streamlit.", file=sys.stderr)
        return 2

    try:
        address = st.config.get_option("server.address")
    except Exception:
        address = None
    if type(address) is not str or address.strip().lower() not in {"127.0.0.1", "localhost", "::1"}:
        st.error(_LOOPBACK_ERROR)
        print(_LOOPBACK_ERROR, file=sys.stderr)
        return 2

    st.title("PaperTrace")
    st.info("The application panels require configured module ports.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
