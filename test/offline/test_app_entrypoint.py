"""Shared public application entrypoint (A->E wiring + B/C/D explicit blocking) test proposal.

FR-A-01/02; FR-E-01/02; INV-02/03/04/05/06/08; QA-01; SEC-01; COST-01; GOV-01.
The tested public entrypoint ``papertrace.app`` does NOT yet exist. Behavioral
assertions are blocked at IMPLEMENTATION_MISSING until this exact test proposal
is independently approved by a non-author reviewer.
No PaperQA2, provider, network, or other-module source writes.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from importlib import import_module
from importlib.util import find_spec
from pathlib import Path
from typing import Any

import pytest

from papertrace.contracts import CorpusSnapshot, DocumentVersion


def app_api() -> Any:
    """Delay loading ``papertrace.app`` so all 12 tests collect cleanly as RED."""
    assert find_spec("papertrace.app") is not None, (
        "IMPLEMENTATION_MISSING: papertrace.app; ASSERTIONS_NOT_REACHED"
    )
    return import_module("papertrace.app")


@dataclass(frozen=True, slots=True)
class _StubLibraryRow:
    document_id: str
    title: str
    source_name: str
    version_sha256: str
    status: str


@dataclass(frozen=True, slots=True)
class _StubLibraryOverview:
    snapshot_id: str
    corpus_revision: int
    rows: tuple[_StubLibraryRow, ...]


@dataclass(frozen=True, slots=True)
class _StubImportRow:
    document_id: str
    source_name: str
    version_sha256: str
    status: str
    stage: str
    reason_code: str | None


@dataclass(frozen=True, slots=True)
class _StubImportFeedback:
    snapshot_id: str
    complete: bool
    rows: tuple[_StubImportRow, ...]


class _RecordingUI:
    """Minimal caller-injected UI facade matching Streamlit widget signatures."""

    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []
        self.writes: list[Any] = []
        self.buttons: list[str] = []

    def subheader(self, text: str) -> None:
        self.messages.append(("subheader", str(text)))

    def caption(self, text: str) -> None:
        self.messages.append(("caption", str(text)))

    def info(self, text: str) -> None:
        self.messages.append(("info", str(text)))

    def warning(self, text: str) -> None:
        self.messages.append(("warning", str(text)))

    def error(self, text: str) -> None:
        self.messages.append(("error", str(text)))

    def success(self, text: str) -> None:
        self.messages.append(("success", str(text)))

    def write(self, payload: Any) -> None:
        self.writes.append(payload)

    def json(self, payload: Any) -> None:
        self.writes.append(payload)

    def button(self, label: str, *, key: str | None = None) -> bool:
        self.buttons.append(f"{label}:{key or ''}")
        return False

    def selectbox(
        self,
        label: str,
        options: list[Any],
        *,
        key: str | None = None,
        format_func: Any = None,
    ) -> Any:
        del label, key, format_func
        return options[0] if options else None

    def download_button(
        self,
        label: str,
        *,
        data: Any,
        file_name: str,
        mime: str,
        key: str | None = None,
    ) -> bool:
        del label, data, file_name, mime, key
        return False

    def rendered_text(self) -> str:
        parts = [text for _, text in self.messages]
        parts.extend(str(item) for item in self.writes)
        return "\n".join(parts)


class _ControlledLibraryService:
    """Offline A-contract service using real ``CorpusSnapshot`` identity rules."""

    def __init__(self, allowed_root: Path, selected_files: tuple[Path, ...]) -> None:
        self.allowed_root = allowed_root.resolve()
        self.selected_files = tuple(path.resolve() for path in selected_files)
        self.ingest_calls: list[Path] = []
        self.fail_names: set[str] = set()
        self.force_freshness_mismatch = False
        self._revision = 0
        self._ready: dict[str, DocumentVersion] = {}
        self._removed: dict[str, DocumentVersion] = {}
        self._failed: dict[str, Path] = {}
        self._raw_secret_bytes = b"RAW_PRIVATE_EXCERPT_DO_NOT_LEAK_77c9"

    def current_snapshot(self) -> CorpusSnapshot:
        return CorpusSnapshot(
            schema_version=1,
            documents=tuple(self._ready.values()),
            created_at=datetime(2026, 11, 23, 12, 0, tzinfo=timezone.utc),
        )

    def freshness(self) -> tuple[str, int]:
        snapshot = self.current_snapshot()
        if self.force_freshness_mismatch:
            return ("snap-" + "0" * 64, self._revision)
        return (snapshot.snapshot_id, self._revision)

    def import_files(
        self,
        paths: tuple[Path, ...],
        *,
        replacements: dict[Path, str] | None = None,
    ) -> dict[str, Any]:
        del replacements
        resolved_batch = [path.resolve() for path in paths]
        for target in resolved_batch:
            if not target.is_relative_to(self.allowed_root) or target not in self.selected_files:
                raise PermissionError(
                    f"PATH_NOT_AUTHORIZED: {target} (secret token=sk-test-private)"
                )
        items = []
        all_ready = True
        for index, target in enumerate(resolved_batch, start=1):
            self.ingest_calls.append(target)
            digest = sha256(self._raw_secret_bytes + target.name.encode("utf-8")).hexdigest()
            doc_id = f"doc-item-{index}"
            if target.name in self.fail_names:
                all_ready = False
                self._failed[doc_id] = target
                items.append(
                    {
                        "document_id": doc_id,
                        "source_name": target.name,
                        "version_sha256": digest,
                        "status": "failed",
                        "stage": "parse",
                        "reason_code": "PARSE_FAILED",
                    }
                )
            else:
                self._ready[doc_id] = DocumentVersion(
                    schema_version=1,
                    document_id=doc_id,
                    version_sha256=digest,
                    title=target.stem,
                    source_name=target.name,
                    status="ready",
                )
                self._failed.pop(doc_id, None)
                items.append(
                    {
                        "document_id": doc_id,
                        "source_name": target.name,
                        "version_sha256": digest,
                        "status": "ready",
                        "stage": "representation",
                        "reason_code": None,
                    }
                )
        self._revision += 1
        return {
            "snapshot": self.current_snapshot(),
            "complete": all_ready,
            "items": items,
        }

    def retry_failed(self, document_ids: tuple[str, ...]) -> dict[str, Any]:
        items = []
        for doc_id in document_ids:
            if doc_id in self._ready:
                raise ValueError("READY_CANNOT_RETRY")
            if doc_id not in self._failed:
                raise KeyError("UNKNOWN_DOCUMENT_ID")
            target = self._failed[doc_id]
            self.ingest_calls.append(target)
            digest = sha256(self._raw_secret_bytes + target.name.encode("utf-8")).hexdigest()
            self._ready[doc_id] = DocumentVersion(
                schema_version=1,
                document_id=doc_id,
                version_sha256=digest,
                title=target.stem,
                source_name=target.name,
                status="ready",
            )
            self._failed.pop(doc_id, None)
            items.append(
                {
                    "document_id": doc_id,
                    "source_name": target.name,
                    "version_sha256": digest,
                    "status": "ready",
                    "stage": "representation",
                    "reason_code": None,
                }
            )
        self._revision += 1
        return {"snapshot": self.current_snapshot(), "complete": True, "items": items}

    def remove(self, document_ids: tuple[str, ...]) -> None:
        for doc_id in document_ids:
            removed = self._ready.pop(doc_id)
            self._removed[doc_id] = removed
        self._revision += 1

    def restore(self, document_ids: tuple[str, ...]) -> None:
        for doc_id in document_ids:
            restored = self._removed.pop(doc_id)
            self._ready[doc_id] = restored
        self._revision += 1


class _ControlledLibraryView:
    """Matches PR #36 ``src/papertrace/library/view.py`` neutral function contract."""

    def library_overview(self, service: _ControlledLibraryService) -> _StubLibraryOverview:
        snapshot = service.current_snapshot()
        freshness_snapshot_id, revision = service.freshness()
        if freshness_snapshot_id != snapshot.snapshot_id:
            raise ValueError("FRESHNESS_MISMATCH")
        return _StubLibraryOverview(
            snapshot_id=snapshot.snapshot_id,
            corpus_revision=revision,
            rows=tuple(
                _StubLibraryRow(
                    document_id=member.document_id,
                    title=member.title,
                    source_name=member.source_name,
                    version_sha256=member.version_sha256,
                    status=member.status,
                )
                for member in snapshot.documents
            ),
        )

    def _feedback(self, batch: dict[str, Any]) -> _StubImportFeedback:
        return _StubImportFeedback(
            snapshot_id=batch["snapshot"].snapshot_id,
            complete=batch["complete"],
            rows=tuple(
                _StubImportRow(
                    document_id=item["document_id"],
                    source_name=item["source_name"],
                    version_sha256=item["version_sha256"],
                    status=item["status"],
                    stage=item["stage"],
                    reason_code=item["reason_code"],
                )
                for item in batch["items"]
            ),
        )

    def import_selected(
        self,
        service: _ControlledLibraryService,
        paths: tuple[Path, ...],
        replacements: dict[Path, str] | None = None,
    ) -> _StubImportFeedback:
        return self._feedback(service.import_files(tuple(paths), replacements=replacements))

    def retry_selected(
        self,
        service: _ControlledLibraryService,
        document_ids: tuple[str, ...],
    ) -> _StubImportFeedback:
        return self._feedback(service.retry_failed(tuple(document_ids)))

    def remove_selected(
        self,
        service: _ControlledLibraryService,
        document_ids: tuple[str, ...],
    ) -> _StubLibraryOverview:
        service.remove(tuple(document_ids))
        return self.library_overview(service)

    def restore_selected(
        self,
        service: _ControlledLibraryService,
        document_ids: tuple[str, ...],
    ) -> _StubLibraryOverview:
        service.restore(tuple(document_ids))
        return self.library_overview(service)


class _ControlledHistoryStore:
    """Immutable historical record fixture verifying zero implicit writes or drift migration."""

    def __init__(self, initial_snapshot_id: str) -> None:
        self.save_calls = 0
        self.records: list[dict[str, Any]] = [
            {
                "record_id": "rec-0001",
                "snapshot_id": initial_snapshot_id,
                "release_status": "blocked",
                "reason_code": "NO_APPROVED_EVIDENCE",
            }
        ]

    def save(self, record: Any) -> None:
        self.save_calls += 1
        self.records.append(record)

    def list_records(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self.records]


class _SpyReportsPanel:
    """Enforces PR #35 ``render_reports_panel(ui, *, store=..., ...)`` keyword-only contract."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def __call__(
        self,
        ui: Any,
        *,
        store: Any,
        pending_record: Any = None,
        current_snapshot_id: str | None = None,
        input_error: object = None,
    ) -> None:
        self.calls.append(
            {
                "ui": ui,
                "store": store,
                "pending_record": pending_record,
                "current_snapshot_id": current_snapshot_id,
                "input_error": input_error,
            }
        )
        ui.subheader("研究历史与来源导出")


@pytest.fixture
def harness(tmp_path: Path) -> dict[str, Any]:
    allowed_root = tmp_path / "private-user-home" / "selected"
    allowed_root.mkdir(parents=True)
    alpha = allowed_root / "alpha.txt"
    beta = allowed_root / "beta.txt"
    unselected = allowed_root / "unselected.txt"
    outside = tmp_path / "outside.txt"
    for target in (alpha, beta, unselected, outside):
        target.write_bytes(b"synthetic content\n")

    service = _ControlledLibraryService(allowed_root, (alpha, beta))
    initial_snapshot_id = service.current_snapshot().snapshot_id
    store = _ControlledHistoryStore(initial_snapshot_id)
    reports_panel = _SpyReportsPanel()
    view = _ControlledLibraryView()
    return {
        "ui": _RecordingUI(),
        "service": service,
        "view": view,
        "store": store,
        "reports_panel": reports_panel,
        "alpha": alpha,
        "beta": beta,
        "unselected": unselected,
        "outside": outside,
        "initial_snapshot_id": initial_snapshot_id,
    }


def _make_ports(api: Any, harness: dict[str, Any], **overrides: Any) -> Any:
    kwargs: dict[str, Any] = {
        "library_view": harness["view"],
        "library_service": harness["service"],
        "reports_panel": harness["reports_panel"],
        "history_store": harness["store"],
        "pending_record": None,
        "pending_input_error": None,
        "retrieval_port": None,
        "review_port": None,
        "answer_port": None,
    }
    kwargs.update(overrides)
    return api.AppPorts(**kwargs)


def test_entrypoint_exposes_single_navigation_and_renders_real_snapshot_without_saving(
    harness: dict[str, Any],
) -> None:
    """FR-A-01, FR-E-01, INV-02/05: single navigation, real snapshot, zero implicit writes."""
    api = app_api()
    assert "library" in api.NAV_SECTIONS
    assert "reports" in api.NAV_SECTIONS
    ports = _make_ports(api, harness)
    state = api.render_app(harness["ui"], ports=ports, selected_section="library")

    expected_snapshot = harness["service"].current_snapshot()
    assert state.active_section == "library"
    assert state.snapshot_id == expected_snapshot.snapshot_id
    assert state.corpus_revision == 0
    assert state.library_error is None
    assert harness["service"].ingest_calls == []
    assert harness["store"].save_calls == 0


def test_entrypoint_forwards_only_explicit_selection_and_rejects_unselected_or_outside_paths(
    harness: dict[str, Any],
) -> None:
    """FR-A-01, SEC-01: unselected/outside inputs never ingest and fail closed safely."""
    api = app_api()
    ports = _make_ports(api, harness)
    for bad_path in (harness["unselected"], harness["outside"]):
        ui = _RecordingUI()
        state = api.render_app(
            ui,
            ports=ports,
            selected_section="library",
            selected_paths=(harness["alpha"], bad_path),
        )
        assert harness["service"].ingest_calls == []
        assert state.library_error is not None
        assert str(bad_path) not in ui.rendered_text()
        assert "sk-test-private" not in ui.rendered_text()


def test_entrypoint_surfaces_partial_import_failure_without_claiming_complete(
    harness: dict[str, Any],
) -> None:
    """FR-A-02, INV-06: partial import stays incomplete with visible stage and reason."""
    api = app_api()
    harness["service"].fail_names.add(harness["beta"].name)
    ports = _make_ports(api, harness)
    state = api.render_app(
        harness["ui"],
        ports=ports,
        selected_section="library",
        selected_paths=(harness["alpha"], harness["beta"]),
    )

    assert state.import_feedback is not None
    assert state.import_feedback.complete is False
    assert [row.status for row in state.import_feedback.rows] == ["ready", "failed"]
    assert state.import_feedback.rows[1].stage == "parse"
    assert state.import_feedback.rows[1].reason_code == "PARSE_FAILED"
    assert len(harness["service"].current_snapshot().documents) == 1


def test_entrypoint_fails_closed_on_snapshot_freshness_mismatch_and_blocks_e_save(
    harness: dict[str, Any],
) -> None:
    """INV-02/05, QA-01: FRESHNESS_MISMATCH fails closed and blocks E panel archiving."""
    api = app_api()
    harness["service"].force_freshness_mismatch = True
    ports = _make_ports(api, harness)
    state = api.render_app(harness["ui"], ports=ports, selected_section="reports")

    assert state.snapshot_id is None
    assert state.library_error is not None
    assert state.reports_invoked is True
    assert len(harness["reports_panel"].calls) == 1
    call = harness["reports_panel"].calls[0]
    assert call["current_snapshot_id"] is None
    assert call["input_error"] is not None
    assert harness["store"].save_calls == 0


def test_entrypoint_passes_keyword_only_arguments_to_reports_panel_and_preserves_blocked_history(
    harness: dict[str, Any],
) -> None:
    """FR-E-01/02, INV-04/08: keyword-only handoff to E, blocked history preserved."""
    api = app_api()
    ports = _make_ports(api, harness)
    state = api.render_app(harness["ui"], ports=ports, selected_section="reports")

    assert state.reports_invoked is True
    assert len(harness["reports_panel"].calls) == 1
    call = harness["reports_panel"].calls[0]
    assert call["store"] is harness["store"]
    assert call["pending_record"] is None
    assert call["current_snapshot_id"] == harness["initial_snapshot_id"]
    assert harness["store"].save_calls == 0
    assert harness["store"].list_records()[0]["release_status"] == "blocked"


def test_entrypoint_snapshot_drift_does_not_migrate_or_mutate_historical_records(
    harness: dict[str, Any],
) -> None:
    """INV-02/05: corpus snapshot changes must never migrate historical records."""
    api = app_api()
    ports = _make_ports(api, harness)
    api.render_app(
        harness["ui"],
        ports=ports,
        selected_section="library",
        selected_paths=(harness["alpha"],),
    )
    new_snapshot_id = harness["service"].current_snapshot().snapshot_id
    assert new_snapshot_id != harness["initial_snapshot_id"]

    api.render_app(harness["ui"], ports=ports, selected_section="reports")
    call = harness["reports_panel"].calls[-1]
    assert call["current_snapshot_id"] == new_snapshot_id
    assert harness["store"].list_records()[0]["snapshot_id"] == harness["initial_snapshot_id"]
    assert harness["store"].save_calls == 0


def test_entrypoint_blocks_missing_b_c_d_ports_without_synthesizing_research_record_or_release(
    harness: dict[str, Any],
) -> None:
    """INV-03/04, GOV-01: absent B/C/D stages remain visibly blocked without fake outputs."""
    api = app_api()
    ports = _make_ports(api, harness)
    for stage in ("retrieval", "review", "answer"):
        ui = _RecordingUI()
        state = api.render_app(ui, ports=ports, selected_section=stage)
        assert stage in state.blocked_stages
        assert harness["store"].save_calls == 0
        assert "released" not in ui.rendered_text().lower()

    api.render_app(harness["ui"], ports=ports, selected_section="reports")
    assert harness["reports_panel"].calls[-1]["pending_record"] is None


def test_entrypoint_redacts_private_paths_and_source_bytes_from_ui_and_errors(
    harness: dict[str, Any],
) -> None:
    """SEC-01, QA-01: never expose absolute private paths, credentials, or raw bytes."""
    api = app_api()
    ports = _make_ports(api, harness)
    api.render_app(
        harness["ui"],
        ports=ports,
        selected_section="library",
        selected_paths=(harness["alpha"],),
    )
    rendered = harness["ui"].rendered_text()
    assert str(harness["alpha"].parent) not in rendered
    assert "private-user-home" not in rendered
    assert "RAW_PRIVATE_EXCERPT_DO_NOT_LEAK_77c9" not in rendered


def test_entrypoint_delegates_explicit_retry_remove_restore_without_bypassing_service(
    harness: dict[str, Any],
) -> None:
    """FR-A-02, INV-02: retry/remove/restore route through A view without bypassing checks."""
    api = app_api()
    harness["service"].fail_names.add(harness["beta"].name)
    ports = _make_ports(api, harness)

    api.render_app(
        harness["ui"],
        ports=ports,
        selected_section="library",
        selected_paths=(harness["alpha"], harness["beta"]),
    )
    harness["service"].fail_names.clear()
    retry_state = api.render_app(
        harness["ui"],
        ports=ports,
        selected_section="library",
        retry_document_ids=("doc-item-2",),
    )
    assert retry_state.import_feedback is not None
    assert retry_state.import_feedback.complete is True
    assert len(harness["service"].current_snapshot().documents) == 2

    bad_retry = api.render_app(
        harness["ui"],
        ports=ports,
        selected_section="library",
        retry_document_ids=("doc-item-1",),
    )
    assert bad_retry.library_error is not None

    removed = api.render_app(
        harness["ui"],
        ports=ports,
        selected_section="library",
        remove_document_ids=("doc-item-1",),
    )
    assert len(harness["service"].current_snapshot().documents) == 1
    assert removed.corpus_revision > retry_state.corpus_revision

    restored = api.render_app(
        harness["ui"],
        ports=ports,
        selected_section="library",
        restore_document_ids=("doc-item-1",),
    )
    assert len(harness["service"].current_snapshot().documents) == 2
    assert restored.corpus_revision > removed.corpus_revision


def test_entrypoint_navigation_switch_never_triggers_write_or_implicit_save(
    harness: dict[str, Any],
) -> None:
    """FR-E-01, INV-05: navigating across all sections never writes or imports."""
    api = app_api()
    ports = _make_ports(api, harness)
    for section in api.NAV_SECTIONS:
        api.render_app(_RecordingUI(), ports=ports, selected_section=section)
    assert harness["service"].ingest_calls == []
    assert harness["store"].save_calls == 0


def test_entrypoint_makes_zero_external_network_or_provider_calls(
    harness: dict[str, Any],
) -> None:
    """COST-01, SEC-01: full library + reports render works completely offline."""
    api = app_api()
    ports = _make_ports(api, harness)
    lib_state = api.render_app(harness["ui"], ports=ports, selected_section="library")
    rep_state = api.render_app(harness["ui"], ports=ports, selected_section="reports")
    assert lib_state.snapshot_id == rep_state.snapshot_id
    assert harness["store"].save_calls == 0


def test_entrypoint_module_has_no_top_level_streamlit_or_paperqa_import() -> None:
    """ADR-001: shared entrypoint must never import paperqa or hard-import streamlit at top level."""
    api = app_api()
    source_path = Path(api.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("paperqa")
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith("paperqa")
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("streamlit")
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith("streamlit")
