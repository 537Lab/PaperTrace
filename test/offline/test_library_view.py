"""A-only library view/command test proposal, using synthetic local inputs.

FR-A-01/02; INV-02/05/06; QA-01; SEC-01; COST-01.
The tested A view does NOT yet exist. Behavioral assertions are blocked at
IMPLEMENTATION_MISSING until this exact test proposal is independently approved.
No PaperQA2, provider, network, global page/entrypoint or other-module writes.
"""

from importlib import import_module
from importlib.util import find_spec

import pytest

from papertrace.contracts import CorpusSnapshot


def view_api():
    """Delay loading the proposed view so all tests can be collected as RED."""
    assert find_spec("papertrace.library.view") is not None, (
        "IMPLEMENTATION_MISSING: papertrace.library.view; ASSERTIONS_NOT_REACHED"
    )
    return import_module("papertrace.library.view")


@pytest.fixture
def library(tmp_path):
    """Real A service; fake only the external B ingest callback."""
    service_class = import_module("papertrace.library.service").CorpusService
    root = tmp_path / "user-selected"
    root.mkdir()
    first, second = root / "synthetic-alpha.txt", root / "synthetic-beta.txt"
    first.write_bytes(b"Original research source A.\n")
    second.write_bytes(b"Original research source B.\n")
    calls = []
    failures = set()

    def ingest(request):
        calls.append(dict(request))
        return {
            "document_id": request["document_id"],
            "version_sha256": request["version_sha256"],
            "status": "failed" if request["source_name"] in failures else "ready",
            "stage": "parse" if request["source_name"] in failures else "representation",
            "reason_code": "PARSE_FAILED" if request["source_name"] in failures else None,
            "representation_ref": "fake:synthetic" if request["source_name"] not in failures else None,
        }

    service = service_class(
        storage_root=tmp_path / "managed",
        allowed_root=root,
        selected_files=(first, second),
        ingest=ingest,
        policy_ref="synthetic-view-test",
    )
    return service, (first, second), calls, failures


def test_empty_overview_uses_real_empty_snapshot_and_revision(library):
    service, _, calls, _ = library
    overview = view_api().library_overview(service)
    assert isinstance(service.current_snapshot(), CorpusSnapshot)
    assert overview.snapshot_id == service.current_snapshot().snapshot_id
    assert overview.corpus_revision == 0
    assert overview.rows == ()
    assert calls == []


def test_selected_import_displays_real_ready_identity_not_fake_identity(library):
    service, paths, calls, _ = library
    feedback = view_api().import_selected(service, (paths[0],))
    member = service.current_snapshot().documents[0]
    assert len(calls) == 1
    assert feedback.complete is True
    assert feedback.snapshot_id == service.current_snapshot().snapshot_id
    assert len(feedback.rows) == 1
    row = feedback.rows[0]
    assert row.document_id == member.document_id
    assert row.version_sha256 == member.version_sha256
    assert row.source_name == member.source_name
    assert row.status == "ready" and row.reason_code is None


def test_batch_partial_failure_visible_not_ready(library):
    service, paths, calls, failures = library
    failures.add(paths[1].name)
    feedback = view_api().import_selected(service, paths)
    assert len(calls) == 2
    assert feedback.complete is False
    assert [row.status for row in feedback.rows] == ["ready", "failed"]
    assert feedback.rows[1].stage == "parse"
    assert feedback.rows[1].reason_code == "PARSE_FAILED"
    assert len(service.current_snapshot().documents) == 1


def test_overview_reads_ready_only_current_snapshot(library):
    service, paths, _, failures = library
    failures.add(paths[1].name)
    api = view_api()
    api.import_selected(service, paths)
    overview = api.library_overview(service)
    assert overview.snapshot_id == service.current_snapshot().snapshot_id
    assert overview.corpus_revision == service.freshness()[1]
    assert len(overview.rows) == 1
    member = service.current_snapshot().documents[0]
    row = overview.rows[0]
    assert (row.document_id, row.version_sha256) == (
        member.document_id, member.version_sha256
    )
    assert row.status == "ready"



def test_overview_refuses_snapshot_freshness_token_mismatch(library, monkeypatch):
    """INV-02/05: inconsistent snapshot and freshness token must fail closed."""
    service, paths, calls, _ = library
    service.import_files((paths[0],))
    snapshot = service.current_snapshot()
    snapshot_id, revision = service.freshness()
    assert snapshot_id == snapshot.snapshot_id
    wrong_snapshot_id = "snap-" + "0" * 64
    if wrong_snapshot_id == snapshot_id:
        wrong_snapshot_id = "snap-" + "1" * 64
    monkeypatch.setattr(service, "freshness", lambda: (wrong_snapshot_id, revision))

    with pytest.raises(ValueError, match="FRESHNESS_MISMATCH"):
        view_api().library_overview(service)
    assert service.current_snapshot() == snapshot
    assert len(calls) == 1


def test_unselected_in_root_rejected_without_import_or_record(library):
    service, paths, calls, _ = library
    unselected = paths[0].parent / "not-selected.txt"
    unselected.write_text("SYNTHETIC PRIVATE SOURCE", encoding="utf-8")
    with pytest.raises(ValueError, match="SOURCE_NOT_AUTHORIZED"):
        view_api().import_selected(service, (unselected,))
    assert calls == [] and service.current_snapshot().documents == ()


def test_whole_batch_authorization_before_any_ingest(library):
    service, paths, calls, _ = library
    outside = paths[0].parent.parent / "outside.txt"
    outside.write_text("UNAUTHORIZED SYNTHETIC", encoding="utf-8")
    with pytest.raises(ValueError, match="SOURCE_NOT_AUTHORIZED"):
        view_api().import_selected(service, (paths[0], outside))
    assert calls == [] and service.current_snapshot().documents == ()


def test_duplicate_selection_does_not_repeat_ingest(library):
    service, paths, calls, _ = library
    api = view_api()
    first = api.import_selected(service, (paths[0],))
    second = api.import_selected(service, (paths[0],))
    assert len(calls) == 1
    assert first.rows == second.rows
    assert first.snapshot_id == second.snapshot_id


def test_explicit_retry_does_not_convert_a_ready_item(library):
    service, paths, calls, _ = library
    api = view_api()
    feedback = api.import_selected(service, (paths[0],))
    with pytest.raises(ValueError, match="NOT_FAILED"):
        api.retry_selected(service, (feedback.rows[0].document_id,))
    assert len(calls) == 1


def test_failed_item_requires_explicit_retry(library):
    service, paths, calls, failures = library
    api = view_api()
    failures.add(paths[1].name)
    feedback = api.import_selected(service, (paths[1],))
    doc_id = feedback.rows[0].document_id
    assert feedback.rows[0].status == "failed"
    failures.clear()
    again = api.import_selected(service, (paths[1],))
    assert again.rows[0].status == "failed" and len(calls) == 1
    retried = api.retry_selected(service, (doc_id,))
    assert retried.rows[0].status == "ready" and len(calls) == 2
    assert [item["status"] for item in service.attempts(doc_id)] == ["failed", "ready"]


def test_remove_restore_preserve_history_and_show_new_corpus_revision(library):
    service, paths, calls, _ = library
    api = view_api()
    feedback = api.import_selected(service, (paths[0],))
    doc_id = feedback.rows[0].document_id
    old = service.current_snapshot()
    before = api.library_overview(service)
    removed = api.remove_selected(service, (doc_id,))
    assert removed.rows == ()
    assert removed.corpus_revision > before.corpus_revision
    restored = api.restore_selected(service, (doc_id,))
    assert restored.snapshot_id == old.snapshot_id
    assert restored.corpus_revision > removed.corpus_revision
    assert restored.rows[0].document_id == doc_id
    assert len(calls) == 1


def test_source_change_exposes_new_sha_and_snapshot_not_overwritten(library):
    service, paths, calls, _ = library
    api = view_api()
    old_feedback = api.import_selected(service, (paths[0],))
    old = service.current_snapshot()
    old_doc = old.documents[0]
    paths[0].write_bytes(b"Original research source A, revised.\n")
    new_feedback = api.import_selected(
        service, (paths[0],), replacements={paths[0]: old_doc.document_id}
    )
    member = service.current_snapshot().documents[0]
    assert len(calls) == 2
    assert new_feedback.snapshot_id != old_feedback.snapshot_id
    assert member.document_id == old_doc.document_id
    assert member.version_sha256 != old_doc.version_sha256
    assert service.read_source(
        snapshot_id=old.snapshot_id,
        document_id=old_doc.document_id,
        version_sha256=old_doc.version_sha256,
    ) == b"Original research source A.\n"


def test_view_models_do_not_expose_raw_source_or_private_paths(library):
    service, paths, _, _ = library
    api = view_api()
    feedback = api.import_selected(service, paths)
    overview = api.library_overview(service)
    for exported in (repr(feedback), repr(overview)):
        assert str(paths[0].parent) not in exported
        assert "Original research source A." not in exported
        assert "Original research source B." not in exported
        assert "source_bytes" not in exported


def test_view_never_promotes_failure_to_success_on_authority_error(library):
    service, paths, _, _ = library
    api = view_api()
    feedback = api.import_selected(service, (paths[0],))
    old_snapshot = service.current_snapshot()
    with pytest.raises(ValueError, match="UNKNOWN_DOCUMENT"):
        api.remove_selected(service, ("doc-not-in-library",))
    assert service.current_snapshot() == old_snapshot
    assert api.library_overview(service).snapshot_id == feedback.snapshot_id


def test_display_projection_contains_no_raw_source_bytes(library):
    service, paths, _, _ = library
    api = view_api()
    api.import_selected(service, paths)
    overview = api.library_overview(service)
    for row in overview.rows:
        assert isinstance(row.source_name, str) and row.source_name in {
            "synthetic-alpha.txt", "synthetic-beta.txt"
        }
        assert isinstance(row.version_sha256, str) and len(row.version_sha256) == 64
        assert not hasattr(row, "source_bytes")
        assert not hasattr(row, "external_path")


def test_contract_view_test_uses_real_corpus_snapshot(library):
    """Baseline contract control; this should pass before view implementation."""
    service, paths, _, _ = library
    service.import_files((paths[0],))
    snapshot = service.current_snapshot()
    assert isinstance(snapshot, CorpusSnapshot)
    assert CorpusSnapshot.model_validate_json(snapshot.model_dump_json()) == snapshot
