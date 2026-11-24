"""Framework-neutral explicit UI actions; authorization stays in render_app."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from papertrace.app import NAV_SECTIONS, AppPorts, AppRenderState, render_app

_SELECTION_ERROR = "The file selection is invalid."
_NAVIGATION_ERROR = "The navigation selection is invalid."


@dataclass(frozen=True, slots=True)
class WorkbenchSession:
    selected_section: str = "library"
    selected_paths: tuple[Path, ...] = ()
    retry_document_ids: tuple[str, ...] = ()
    remove_document_ids: tuple[str, ...] = ()
    restore_document_ids: tuple[str, ...] = ()


def _safe_name(name: str) -> bool:
    return (
        bool(name)
        and name not in {".", ".."}
        and "/" not in name
        and "\\" not in name
        and all(not (ord(char) < 32 or 127 <= ord(char) <= 159) for char in name)
    )


def _file_options(paths: Sequence[Path]) -> dict[str, Path]:
    counts = Counter(path.name for path in paths)
    return {
        path.name: path
        for path in paths
        if counts[path.name] == 1 and _safe_name(path.name)
    }


def _library_actions(
    ui: Any,
    paths: Sequence[Path],
    failed: Sequence[str],
    removable: Sequence[str],
    restorable: Sequence[str],
) -> WorkbenchSession:
    options = _file_options(paths)
    selected = ui.multiselect("Files to import", tuple(options), key="library-files")
    clicks = (
        ui.button("Import selected files", key="import"),
        ui.button("Retry failed imports", key="retry"),
        ui.button("Remove documents", key="remove"),
        ui.button("Restore documents", key="restore"),
    )
    if sum(bool(clicked) for clicked in clicks) != 1:
        return WorkbenchSession()
    if clicks[0]:
        if (
            not isinstance(selected, Sequence)
            or isinstance(selected, (str, bytes))
            or any(type(name) is not str or name not in options for name in selected)
            or len(set(selected)) != len(selected)
        ):
            ui.error(_SELECTION_ERROR)
            return WorkbenchSession()
        return WorkbenchSession(selected_paths=tuple(options[name] for name in selected))
    if clicks[1]:
        return WorkbenchSession(retry_document_ids=tuple(failed))
    if clicks[2]:
        return WorkbenchSession(remove_document_ids=tuple(removable))
    return WorkbenchSession(restore_document_ids=tuple(restorable))


def render_interactive_workbench(
    ui: Any,
    *,
    ports: AppPorts,
    available_paths: Sequence[Path] = (),
    failed_document_ids: Sequence[str] = (),
    removable_document_ids: Sequence[str] = (),
    restorable_document_ids: Sequence[str] = (),
) -> AppRenderState:
    """Map one explicit widget action to the existing application delegate."""
    section = ui.selectbox("Section", NAV_SECTIONS, key="workbench-section")
    if type(section) is not str or section not in NAV_SECTIONS:
        ui.error(_NAVIGATION_ERROR)
        state = WorkbenchSession()
    elif section == "library":
        state = _library_actions(
            ui, available_paths, failed_document_ids, removable_document_ids,
            restorable_document_ids,
        )
    else:
        state = WorkbenchSession(selected_section=section)
    return render_app(
        ui,
        ports=ports,
        selected_section=state.selected_section,
        selected_paths=state.selected_paths,
        retry_document_ids=state.retry_document_ids,
        remove_document_ids=state.remove_document_ids,
        restore_document_ids=state.restore_document_ids,
    )
