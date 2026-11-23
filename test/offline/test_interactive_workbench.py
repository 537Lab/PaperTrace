"""Offline RED contract for the shared interactive workbench."""

from __future__ import annotations

import ast
from collections.abc import Sequence
from importlib import import_module
from importlib.util import find_spec
from inspect import signature
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest
from test_app_entrypoint import (
    _ControlledHistoryStore,
    _ControlledLibraryService,
    _ControlledLibraryView,
    _RecordingUI,
)

from papertrace import app

SECTIONS = ("library", "retrieval", "review", "answer", "reports")
ACTIONS = {
    "import": "selected_paths",
    "retry": "retry_document_ids",
    "remove": "remove_document_ids",
    "restore": "restore_document_ids",
}
REDACTION_MARKER = "sk-test-private"
PRIVATE_MARKER = "private-user-home"
SELECTION_ERROR = "The file selection is invalid."
NAVIGATION_ERROR = "The navigation selection is invalid."
RAW_EXCERPT = "RAW_PRIVATE_EXCERPT_DO_NOT_LEAK_77c9"


def workbench_spec() -> Any:
    spec = find_spec("papertrace.workbench")
    assert spec is not None, "IMPLEMENTATION_MISSING: papertrace.workbench"
    return spec


class InteractiveUI(_RecordingUI):
    def __init__(
        self,
        *,
        section: str | None = None,
        expected_section: str | None = None,
        selection: Sequence[str] = (),
        clicks: Sequence[str] = (),
    ) -> None:
        super().__init__()
        self.section = section
        self.expected_section = expected_section or section or "library"
        self.selection = selection
        self.clicks = clicks
        self.navigation: list[tuple[str, ...]] = []
        self.file_options: list[tuple[str, ...]] = []
        self.widget_text: list[Any] = []
        self.action_keys: list[str | None] = []

    def selectbox(
        self, label: str, options: Sequence[str], index: int = 0, *,
        key: str | None = None, format_func: Any = None,
    ) -> str:
        self.navigation.append(tuple(options))
        self.widget_text.extend((label, key, tuple(options)))
        if format_func is not None:
            self.widget_text.extend(format_func(option) for option in options)
        return options[index] if self.section is None else self.section

    def multiselect(
        self, label: str, options: Sequence[str], default: Sequence[str] | None = None, *,
        key: str | None = None, format_func: Any = None,
    ) -> Sequence[str]:
        self.file_options.append(tuple(options))
        self.widget_text.extend((label, key, tuple(options), default))
        if format_func is not None:
            self.widget_text.extend(format_func(option) for option in options)
        # Deliberately permit stale or forged widget responses.
        return self.selection

    def button(
        self, label: str, *, key: str | None = None, disabled: bool = False,
    ) -> bool:
        self.widget_text.extend((label, key))
        self.action_keys.append(key)
        return not disabled and key in self.clicks

    def visible_text(self) -> str:
        return f"{self.rendered_text()}\n{self.widget_text!r}"


class DelegatedPort:
    """Guard every member lookup on an injected A/E object."""

    def __init__(self, target: Any, require_delegate: Any) -> None:
        self._target = target
        self._require_delegate = require_delegate

    def __getattr__(self, name: str) -> Any:
        self._require_delegate()
        member = getattr(self._target, name)
        if not callable(member):
            return member

        def guarded(*args: Any, **kwargs: Any) -> Any:
            self._require_delegate()
            return member(*args, **kwargs)

        return guarded


class WorkbenchHarness:
    def __init__(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self.root = tmp_path / PRIVATE_MARKER / "selected"
        self.alpha = self.root / "alpha.txt"
        self.beta = self.root / "beta.txt"
        self.unselected = self.root / "unselected.txt"
        self.outside = tmp_path / "outside.txt"
        self.service = _ControlledLibraryService(self.root, (self.alpha, self.beta))
        self.initial_snapshot = self.service.current_snapshot().snapshot_id
        self.store = _ControlledHistoryStore(self.initial_snapshot)
        self.history = self.store.list_records()
        self.report_calls: list[tuple[Any, ...]] = []
        self.mutations = {
            name: Mock(wraps=getattr(self.service, name))
            for name in ("import_files", "retry_failed", "remove", "restore")
        }
        for name, spy in self.mutations.items():
            monkeypatch.setattr(self.service, name, spy)

        self.module = import_module("papertrace.workbench")
        real_render_app = app.render_app
        self.render_signature = signature(real_render_app)
        self.in_delegate = False
        self.rendered_state: app.AppRenderState | None = None
        self.view_port = DelegatedPort(_ControlledLibraryView(), self.require_delegate)
        self.service_port = DelegatedPort(self.service, self.require_delegate)
        self.history_port = DelegatedPort(self.store, self.require_delegate)

        def delegate(*args: Any, **kwargs: Any) -> app.AppRenderState:
            assert not self.in_delegate
            self.in_delegate = True
            try:
                self.rendered_state = real_render_app(*args, **kwargs)
                return self.rendered_state
            finally:
                self.in_delegate = False

        self.render_app = Mock(side_effect=delegate)
        monkeypatch.setattr(app, "render_app", self.render_app)
        # Support both module-qualified calls and direct imports.
        for name, value in vars(self.module).items():
            if value is real_render_app:
                monkeypatch.setattr(self.module, name, self.render_app)

    def require_delegate(self) -> None:
        if not self.in_delegate:
            pytest.fail("A/E port accessed outside papertrace.app.render_app")

    def reports_panel(
        self, ui: Any, /, *, store: Any, pending_record: Any,
        current_snapshot_id: str | None, input_error: str | None,
    ) -> None:
        self.require_delegate()
        self.report_calls.append((ui, store, pending_record, current_snapshot_id, input_error))
        ui.subheader("研究历史与来源导出")

    def render(
        self, ui: InteractiveUI, *, pending_record: Any = None,
        pending_input_error: object = None, **widget_inputs: Any,
    ) -> app.AppRenderState:
        ports = app.AppPorts(
            library_view=self.view_port,
            library_service=self.service_port,
            reports_panel=self.reports_panel,
            history_store=self.history_port,
            pending_record=pending_record,
            pending_input_error=pending_input_error,
        )
        self.render_app.reset_mock()
        self.rendered_state = None
        state = self.module.render_interactive_workbench(ui, ports=ports, **widget_inputs)
        assert isinstance(state, app.AppRenderState)
        assert state is self.rendered_state
        assert state.active_section == ui.expected_section
        assert ui.navigation == [SECTIONS]
        self.render_app.assert_called_once()
        self.arguments = self.render_signature.bind(
            *self.render_app.call_args.args, **self.render_app.call_args.kwargs,
        )
        self.arguments.apply_defaults()
        assert self.arguments.arguments["ui"] is ui
        assert self.arguments.arguments["ports"] is ports
        assert self.arguments.arguments["selected_section"] == ui.expected_section
        return state

    def assert_forwarded(self, **expected: Sequence[Any]) -> None:
        for argument in ACTIONS.values():
            assert tuple(self.arguments.arguments[argument]) == tuple(expected.get(argument, ()))

    def assert_no_mutations(self) -> None:
        for spy in self.mutations.values():
            spy.assert_not_called()
        assert self.service.ingest_calls == []
        assert self.service.freshness() == (self.initial_snapshot, 0)
        self.assert_history_unchanged()

    def assert_history_unchanged(self) -> None:
        assert self.store.save_calls == 0
        assert self.store.list_records() == self.history

    def assert_private(self, ui: InteractiveUI, capsys: pytest.CaptureFixture[str]) -> None:
        captured = capsys.readouterr()
        for output in (ui.visible_text(), captured.out, captured.err):
            for value in (self.root, self.outside, PRIVATE_MARKER, REDACTION_MARKER, RAW_EXCERPT):
                assert str(value) not in output


def competing_actions(clicked: str, alpha: Path) -> dict[str, Any]:
    candidates = {
        "import": ("available_paths", (alpha,)),
        "retry": ("failed_document_ids", ("failed-decoy",)),
        "remove": ("removable_document_ids", ("removable-decoy",)),
        "restore": ("restorable_document_ids", ("restorable-decoy",)),
    }
    return dict(candidate for action, candidate in candidates.items() if action != clicked)


def test_initial_render_is_read_only_and_shows_real_snapshot(tmp_path, monkeypatch, capsys):
    workbench_spec()
    wb = WorkbenchHarness(tmp_path, monkeypatch)
    assert isinstance(wb.module.WorkbenchSession, type)
    ui = InteractiveUI()
    state = wb.render(
        ui, available_paths=(wb.alpha,), failed_document_ids=("failed",),
        removable_document_ids=("removable",), restorable_document_ids=("restorable",),
    )
    assert state.snapshot_id == wb.initial_snapshot
    assert state.corpus_revision == 0
    assert state.library_error is None
    assert wb.initial_snapshot in ui.rendered_text()
    wb.assert_forwarded()
    wb.assert_no_mutations()
    assert wb.report_calls == []
    wb.assert_private(ui, capsys)


def test_file_selection_alone_and_empty_action_clicks_are_read_only(tmp_path, monkeypatch, capsys):
    workbench_spec()
    wb = WorkbenchHarness(tmp_path, monkeypatch)
    ui = InteractiveUI(selection=("alpha.txt",))
    state = wb.render(ui, available_paths=(wb.alpha,))
    assert ui.file_options == [("alpha.txt",)]
    assert state.import_feedback is None
    wb.assert_forwarded()
    wb.assert_no_mutations()
    wb.assert_private(ui, capsys)

    for action in ACTIONS:
        ui = InteractiveUI(clicks=(action,))
        kwargs = competing_actions(action, wb.alpha)
        if action == "import":
            kwargs["available_paths"] = (wb.alpha,)
        state = wb.render(ui, **kwargs)
        assert state.import_feedback is None
        wb.assert_forwarded()
        wb.assert_no_mutations()
        wb.assert_private(ui, capsys)


def test_import_click_forwards_only_selected_file_and_hides_private_data(
    tmp_path, monkeypatch, capsys,
):
    workbench_spec()
    wb = WorkbenchHarness(tmp_path, monkeypatch)
    ui = InteractiveUI(selection=("alpha.txt",), clicks=("import",))
    state = wb.render(
        ui, available_paths=(wb.beta, wb.alpha), **competing_actions("import", wb.alpha),
    )
    wb.assert_forwarded(selected_paths=(wb.alpha,))
    wb.mutations["import_files"].assert_called_once()
    assert wb.service.ingest_calls == [wb.alpha.resolve()]
    assert state.import_feedback.complete is True
    assert state.snapshot_id != wb.initial_snapshot
    assert state.snapshot_id == wb.service.current_snapshot().snapshot_id
    assert ui.file_options == [("beta.txt", "alpha.txt")]
    assert "alpha.txt" in ui.rendered_text()
    wb.assert_private(ui, capsys)
    wb.assert_history_unchanged()


def test_invalid_import_batches_fail_closed_without_disclosure(tmp_path, monkeypatch, capsys):
    workbench_spec()
    wb = WorkbenchHarness(tmp_path, monkeypatch)
    duplicate = wb.root.parent / "other" / wb.alpha.name
    control = wb.root / "control\nname.txt"
    backslash = wb.root / "back\\slash.txt"
    candidates = (wb.alpha, duplicate, control, backslash, wb.beta)
    for bad_selection in (wb.alpha.name, control.name, backslash.name, str(wb.outside)):
        forged = InteractiveUI(selection=("beta.txt", bad_selection), clicks=("import",))
        state = wb.render(forged, available_paths=candidates)
        assert forged.file_options == [("beta.txt",)]
        assert [message for kind, message in forged.messages if kind == "error"] == [
            SELECTION_ERROR,
        ]
        wb.assert_forwarded()
        wb.assert_no_mutations()
        assert state.import_feedback is None
        wb.assert_private(forged, capsys)

    # Offered but unauthorized candidates must reach A's batch validation.
    for bad in (wb.unselected, wb.outside):
        wb.mutations["import_files"].reset_mock()
        ui = InteractiveUI(selection=("alpha.txt", bad.name), clicks=("import",))
        state = wb.render(ui, available_paths=(wb.alpha, bad))
        wb.assert_forwarded(selected_paths=(wb.alpha, bad))
        wb.mutations["import_files"].assert_called_once_with(
            (wb.alpha, bad), replacements=None,
        )
        assert wb.service.ingest_calls == []
        assert wb.service.freshness() == (wb.initial_snapshot, 0)
        assert state.library_error
        assert state.import_feedback is None
        assert ("error", state.library_error) in ui.messages
        wb.assert_private(ui, capsys)
        wb.assert_history_unchanged()


def test_partial_failure_retries_only_after_explicit_click(tmp_path, monkeypatch):
    workbench_spec()
    wb = WorkbenchHarness(tmp_path, monkeypatch)
    wb.service.fail_names.add(wb.beta.name)
    candidates = (wb.alpha, wb.beta)
    initial = wb.render(
        InteractiveUI(selection=("alpha.txt", "beta.txt"), clicks=("import",)),
        available_paths=candidates, **competing_actions("import", wb.alpha),
    )
    wb.assert_forwarded(selected_paths=candidates)
    assert initial.import_feedback.complete is False
    failed, = [row for row in initial.import_feedback.rows if row.status == "failed"]
    assert failed.source_name == "beta.txt"
    redraw = wb.render(
        InteractiveUI(selection=("beta.txt",)), available_paths=candidates,
        failed_document_ids=(failed.document_id,),
    )
    wb.assert_forwarded()
    wb.mutations["retry_failed"].assert_not_called()
    wb.mutations["import_files"].assert_called_once()
    assert redraw.corpus_revision == initial.corpus_revision

    retry = wb.render(
        InteractiveUI(clicks=("retry",), selection=("alpha.txt",)),
        failed_document_ids=(failed.document_id,), **competing_actions("retry", wb.alpha),
    )
    wb.assert_forwarded(retry_document_ids=(failed.document_id,))
    wb.mutations["retry_failed"].assert_called_once_with((failed.document_id,))
    assert retry.import_feedback.complete is True
    assert retry.corpus_revision == initial.corpus_revision + 1
    assert wb.service.ingest_calls == [wb.alpha.resolve(), wb.beta.resolve(), wb.beta.resolve()]
    wb.assert_history_unchanged()


def test_remove_and_restore_clicks_advance_revision_and_preserve_history(tmp_path, monkeypatch):
    workbench_spec()
    wb = WorkbenchHarness(tmp_path, monkeypatch)
    initial = wb.render(
        InteractiveUI(selection=("alpha.txt",), clicks=("import",)),
        available_paths=(wb.alpha,), **competing_actions("import", wb.alpha),
    )
    wb.assert_forwarded(selected_paths=(wb.alpha,))
    document, = wb.service.current_snapshot().documents
    target = (document.document_id,)
    redraw = wb.render(InteractiveUI(), removable_document_ids=target)
    wb.assert_forwarded()
    assert redraw.corpus_revision == initial.corpus_revision
    wb.mutations["remove"].assert_not_called()

    removed = wb.render(
        InteractiveUI(clicks=("remove",), selection=("alpha.txt",)),
        removable_document_ids=target, **competing_actions("remove", wb.alpha),
    )
    wb.assert_forwarded(remove_document_ids=target)
    wb.mutations["remove"].assert_called_once_with(target)
    assert removed.corpus_revision == initial.corpus_revision + 1
    assert removed.snapshot_id == wb.initial_snapshot
    assert wb.service.current_snapshot().documents == ()
    wb.assert_history_unchanged()

    redraw = wb.render(InteractiveUI(), restorable_document_ids=target)
    wb.assert_forwarded()
    assert redraw.corpus_revision == removed.corpus_revision
    wb.mutations["restore"].assert_not_called()
    restored = wb.render(
        InteractiveUI(clicks=("restore",), selection=("alpha.txt",)),
        restorable_document_ids=target, **competing_actions("restore", wb.alpha),
    )
    wb.assert_forwarded(restore_document_ids=target)
    wb.mutations["restore"].assert_called_once_with(target)
    assert restored.corpus_revision == removed.corpus_revision + 1
    assert restored.snapshot_id == initial.snapshot_id
    assert wb.service.current_snapshot().documents == (document,)
    wb.assert_history_unchanged()


def test_navigation_switches_all_sections_without_mutations_or_saves(tmp_path, monkeypatch):
    workbench_spec()
    wb = WorkbenchHarness(tmp_path, monkeypatch)
    for section in SECTIONS:
        ui = InteractiveUI(
            section=section, selection=("alpha.txt",),
            clicks=() if section == "library" else tuple(ACTIONS),
        )
        state = wb.render(
            ui, available_paths=(wb.alpha,), failed_document_ids=("failed",),
            removable_document_ids=("removable",), restorable_document_ids=("restorable",),
        )
        assert state.reports_invoked is (section == "reports")
        if section != "library":
            assert ui.file_options == []
            assert not set(ui.action_keys).intersection(ACTIONS)
        wb.assert_forwarded()
        wb.assert_no_mutations()
    assert len(wb.report_calls) == 1

    invalid = InteractiveUI(
        section="forged-section", expected_section="library",
        selection=("alpha.txt",), clicks=tuple(ACTIONS),
    )
    state = wb.render(
        invalid, available_paths=(wb.alpha,), failed_document_ids=("failed",),
        removable_document_ids=("removable",), restorable_document_ids=("restorable",),
    )
    assert [message for kind, message in invalid.messages if kind == "error"] == [
        NAVIGATION_ERROR,
    ]
    assert not state.reports_invoked
    wb.assert_forwarded()
    wb.assert_no_mutations()
    assert len(wb.report_calls) == 1


def test_missing_b_c_d_show_stage_and_blocked_without_release(tmp_path, monkeypatch):
    workbench_spec()
    wb = WorkbenchHarness(tmp_path, monkeypatch)
    for section in ("retrieval", "review", "answer"):
        ui = InteractiveUI(section=section)
        state = wb.render(ui)
        assert state.blocked_stages == ("retrieval", "review", "answer")
        assert any(section in line and "BLOCKED" in line for line in ui.rendered_text().splitlines())
        assert "released" not in ui.visible_text().lower()
        wb.assert_forwarded()
        wb.assert_no_mutations()
    assert wb.report_calls == []


def test_reports_delegates_keyword_only_panel_and_preserves_pending_record(tmp_path, monkeypatch):
    workbench_spec()
    wb = WorkbenchHarness(tmp_path, monkeypatch)
    ui = InteractiveUI(section="reports")
    record = {"record_id": "synthetic-pending", "snapshot_id": wb.initial_snapshot}
    state = wb.render(ui, pending_record=record)
    assert state.reports_invoked
    (panel_ui, store, pending, snapshot_id, error), = wb.report_calls
    assert panel_ui is ui
    assert store is wb.history_port
    assert pending is record
    assert record == {"record_id": "synthetic-pending", "snapshot_id": wb.initial_snapshot}
    assert snapshot_id == wb.initial_snapshot
    assert error is None
    assert "研究历史与来源导出" in ui.rendered_text()
    wb.assert_forwarded()
    wb.assert_no_mutations()


def test_reports_sanitizes_pending_input_error_with_healthy_overview(tmp_path, monkeypatch, capsys):
    workbench_spec()
    wb = WorkbenchHarness(tmp_path, monkeypatch)
    ui = InteractiveUI(section="reports")
    detail = f"Cannot load {wb.alpha} with token {REDACTION_MARKER}"
    state = wb.render(ui, pending_input_error=RuntimeError(detail))
    assert state.library_error is None
    assert state.snapshot_id == wb.initial_snapshot
    (_, _, _, snapshot_id, error), = wb.report_calls
    assert snapshot_id == wb.initial_snapshot
    assert isinstance(error, str) and error.strip()
    assert str(wb.alpha) not in error and REDACTION_MARKER not in error
    wb.assert_private(ui, capsys)
    wb.assert_forwarded()
    wb.assert_no_mutations()


def test_freshness_mismatch_blocks_overview_and_report_snapshot(tmp_path, monkeypatch):
    workbench_spec()
    wb = WorkbenchHarness(tmp_path, monkeypatch)
    wb.service.import_files((wb.alpha,))
    ready_snapshot = wb.service.current_snapshot()
    ready_document, = ready_snapshot.documents
    for spy in wb.mutations.values():
        spy.reset_mock()
    ingested = list(wb.service.ingest_calls)
    wb.service.force_freshness_mismatch = True
    library_ui = InteractiveUI()
    library = wb.render(library_ui)
    assert library.snapshot_id is None and library.library_error
    assert ("error", library.library_error) in library_ui.messages
    assert ready_snapshot.snapshot_id not in library_ui.visible_text()
    assert ready_document.source_name not in library_ui.visible_text()
    wb.assert_forwarded()
    reports = wb.render(InteractiveUI(section="reports"))
    assert reports.snapshot_id is None and reports.library_error
    (_, _, _, snapshot_id, error), = wb.report_calls
    assert snapshot_id is None
    assert isinstance(error, str) and error.strip()
    assert ready_snapshot.snapshot_id not in error
    assert ready_document.source_name not in error
    wb.assert_forwarded()
    for spy in wb.mutations.values():
        spy.assert_not_called()
    assert wb.service.ingest_calls == ingested
    assert wb.service.current_snapshot().snapshot_id == ready_snapshot.snapshot_id
    wb.assert_history_unchanged()


def test_source_has_no_forbidden_imports_or_direct_service_bypass():
    spec = workbench_spec()
    assert spec.origin is not None
    tree = ast.parse(Path(spec.origin).read_text(encoding="utf-8"))
    nested_imports = {
        child
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        for statement in node.body
        for child in ast.walk(statement)
        if isinstance(child, (ast.Import, ast.ImportFrom))
    }
    unsafe_members = {
        "library_view", "library_service", "reports_panel", "history_store",
        "library_overview", "import_selected", "retry_selected", "remove_selected",
        "restore_selected", "render_reports_panel",
    }
    dynamic_access = {"getattr", "importlib", "import_module", "__import__"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            prefix = "." * node.level + (node.module or "")
            separator = "" if prefix.endswith(".") else "."
            names = [prefix, *(f"{prefix}{separator}{alias.name}" for alias in node.names)]
        else:
            if isinstance(node, ast.Attribute):
                assert node.attr not in unsafe_members | dynamic_access
            if isinstance(node, ast.Name):
                assert node.id not in dynamic_access
                if isinstance(node.ctx, ast.Load):
                    assert node.id not in unsafe_members
            continue

        for name in names:
            parts = name.lstrip(".").split(".")
            assert not (dynamic_access | unsafe_members).intersection(parts)
            assert "paperqa" not in parts
            if node not in nested_imports:
                assert "streamlit" not in parts
            assert parts[:2] not in (["papertrace", "library"], ["papertrace", "reports"])
            if name.startswith("."):
                assert name.lstrip(".").split(".")[0] not in {"library", "reports"}
