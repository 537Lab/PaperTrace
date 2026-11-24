"""A-local test proposal; no A implementation or human approval is simulated.

FR-A-01/02, INV-02/05/06, QA-01, SEC-01, COST-01.
PROPOSED_INTEGRATION: every ingest receipt, partial/current failure policy and
ABA revision below awaits owner agreement. This does not freeze a shared B API.
Missing service => IMPLEMENTATION_MISSING / ASSERTIONS_NOT_REACHED, not observed
business-behavior RED. No skips, xfails, model calls or custom pytest markers.
"""

from copy import deepcopy
from hashlib import sha256
from importlib import import_module
from importlib.util import find_spec
from pathlib import Path

import pytest
from pydantic import ValidationError

from papertrace.contracts import CorpusSnapshot, DocumentVersion

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "library"
NAMES = ("normal-alpha.txt", "normal-beta.txt", "normal-gamma.pdf", "broken-delta.txt")


def service_class():
    """Delay lookup so absent business implementation does not prevent collection."""
    for name in ("papertrace", "papertrace.library", "papertrace.library.service"):
        assert find_spec(name) is not None, (
            f"IMPLEMENTATION_MISSING: {name}; ASSERTIONS_NOT_REACHED"
        )
    cls = getattr(import_module("papertrace.library.service"), "CorpusService", None)
    assert cls is not None, "IMPLEMENTATION_MISSING: CorpusService; ASSERTIONS_NOT_REACHED"
    return cls


class FakeIngest:
    """PROPOSED_INTEGRATION: callable receiving one dict, not a fake A service."""

    def __init__(self):
        self.calls = []
        self.scripts = {"broken-delta.txt": ["parse_failed"]}

    def __call__(self, request):
        self.calls.append(deepcopy(request))
        script = self.scripts.get(request["source_name"], [])
        action = script.pop(0) if script else "ready"
        if action == "timeout":
            raise TimeoutError("private-parser-path=/synthetic-private/token-example")
        if action == "exception":
            raise RuntimeError("private-parser-path=/synthetic-private/token-example")
        if action == "missing":
            return None
        receipt = {
            "document_id": request["document_id"],
            "version_sha256": request["version_sha256"],
            "status": "ready",
            "stage": "representation",
            "reason_code": None,
            "representation_ref": "fake:synthetic-representation",
        }
        if action == "parse_failed":
            receipt.update(status="failed", stage="parse", reason_code="PARSE_FAILED")
        elif action == "wrong_id":
            receipt["document_id"] = "doc-wrong"
        elif action == "wrong_version":
            receipt["version_sha256"] = "0" * 64
        elif action == "unknown_status":
            receipt["status"] = "probably_ready"
        return receipt


@pytest.fixture
def make_service(tmp_path):
    """All disk writes are pytest temporary synthetic data, never repository state."""
    root = tmp_path / "selected-root"
    root.mkdir()
    paths = []
    for name in NAMES:
        path = root / name
        path.write_bytes((FIXTURES / name).read_bytes())
        paths.append(path)

    def make(*, selected=None, max_bytes=20 * 1024 * 1024, fault_hook=None):
        fake = FakeIngest()
        storage = tmp_path / "managed"
        service = service_class()(
            storage_root=storage,
            allowed_root=root,
            selected_files=tuple(paths if selected is None else selected),
            ingest=fake,
            policy_ref="offline-test",
            max_bytes=max_bytes,
            fault_hook=fault_hook,
        )
        return service, fake, paths, storage

    return make


def item_for(batch, name):
    return next(item for item in batch["items"] if item["source_name"] == name)


def one_ready(service, paths):
    batch = service.import_files([paths[0]])
    item = batch["items"][0]
    assert item["status"] == "ready"
    return batch, item


def read(service, snapshot, item):
    return service.read_source(
        snapshot_id=snapshot.snapshot_id,
        document_id=item["document_id"],
        version_sha256=item["version_sha256"],
    )


def test_synthetic_pdf_integrity():
    """QA-01: fixture-only baseline; does not test A or a real parser."""
    payload = (FIXTURES / NAMES[2]).read_bytes()
    assert len(payload) == 634
    assert sha256(payload).hexdigest() == (
        "970046dfe2ba98dcfde18be259a7d72fc2554c9b92fd8cb1b62d15c75b966ed6"
    )
    assert payload[451:455] == b"xref"
    stream = payload.split(b"stream\n", 1)[1].split(b"endstream", 1)[0]
    assert len(stream) == 91
    assert b"/Type /Page " in payload and payload.endswith(b"%%EOF\n")


def test_real_snapshot_contract_rejects_batch_complete():
    """QA-01 / INV-02: complete belongs to A-local batch, not frozen snapshot."""
    source = (FIXTURES / NAMES[0]).read_bytes()
    doc = DocumentVersion(
        schema_version=1, document_id="doc-alpha", version_sha256=sha256(source).hexdigest(),
        title="Synthetic alpha", source_name=NAMES[0], status="ready",
    )
    payload = dict(schema_version=1, documents=(doc,), created_at="2026-11-17T00:00:00Z")
    snapshot = CorpusSnapshot(**payload)
    assert CorpusSnapshot.model_validate_json(snapshot.model_dump_json()) == snapshot
    assert "complete" not in snapshot.model_dump()
    with pytest.raises(ValidationError, match="extra_forbidden"):
        CorpusSnapshot(**payload, complete=False)


def test_four_inputs_partial_ready_snapshot_and_real_requests(make_service):
    """FR-A-01 / INV-02; PROPOSED_INTEGRATION partial library + receipt."""
    service, fake, paths, _ = make_service()
    batch = service.import_files(paths)
    assert len(batch["items"]) == 4 and batch["complete"] is False
    assert [x["status"] for x in batch["items"]].count("ready") == 3
    failed = item_for(batch, NAMES[3])
    assert (failed["status"], failed["stage"], failed["reason_code"]) == (
        "failed", "parse", "PARSE_FAILED",
    )
    snapshot = batch["snapshot"]
    assert isinstance(snapshot, CorpusSnapshot) and len(snapshot.documents) == 3
    assert {d.source_name for d in snapshot.documents} == set(NAMES[:3])
    assert CorpusSnapshot.model_validate_json(snapshot.model_dump_json()) == snapshot
    assert len(fake.calls) == 4
    for path in paths:
        request = next(r for r in fake.calls if r["source_name"] == path.name)
        item = item_for(batch, path.name)
        assert request["source_bytes"] == path.read_bytes()
        assert request["version_sha256"] == sha256(path.read_bytes()).hexdigest()
        assert (request["document_id"], request["version_sha256"]) == (
            item["document_id"], item["version_sha256"],
        )
        assert request["metadata"] == {} and request["policy_ref"] == "offline-test"


def test_duplicate_batch_reuses_success_and_does_not_retry_failure(make_service):
    """FR-A-01 / INV-05; PROPOSED_INTEGRATION retry policy."""
    service, fake, paths, _ = make_service()
    first = service.import_files(paths)
    before = deepcopy([service.attempts(i["document_id"]) for i in first["items"]])
    second = service.import_files(paths)
    assert len(fake.calls) == 4
    assert second["items"] == first["items"]
    assert second["snapshot"].snapshot_id == first["snapshot"].snapshot_id
    assert [service.attempts(i["document_id"]) for i in first["items"]] == before


def test_explicit_retry_only_failed_appends_attempt(make_service):
    """FR-A-01 / INV-05; PROPOSED_INTEGRATION explicit retry only."""
    service, fake, paths, _ = make_service()
    first = service.import_files(paths)
    failed = item_for(first, NAMES[3])
    old = deepcopy(service.attempts(failed["document_id"]))
    assert len(old) == 1 and old[0]["status"] == "failed"
    retried = service.retry_failed([failed["document_id"]])
    assert len(fake.calls) == 5 and fake.calls[-1]["source_name"] == NAMES[3]
    assert retried["complete"] is True and len(retried["snapshot"].documents) == 4
    history = service.attempts(failed["document_id"])
    assert history[:-1] == old and history[-1]["status"] == "ready"


def test_ready_cannot_be_retried_as_failed(make_service):
    """FR-A-01: explicit retry is not arbitrary re-ingestion."""
    service, fake, paths, _ = make_service()
    batch, item = one_ready(service, paths)
    with pytest.raises(ValueError, match="NOT_FAILED"):
        service.retry_failed([item["document_id"]])
    assert len(fake.calls) == 1
    assert service.current_snapshot() == batch["snapshot"]


def test_same_path_changed_bytes_keeps_id_changes_version(make_service):
    """FR-A-02 / INV-02/05: explicit replacement, not basename identity."""
    service, fake, paths, _ = make_service()
    old, item = one_ready(service, paths)
    paths[0].write_bytes(b"Synthetic alpha second actual byte version.\n")
    new = service.import_files([paths[0]], replacements={paths[0]: item["document_id"]})
    updated = new["items"][0]
    assert updated["document_id"] == item["document_id"]
    assert updated["version_sha256"] == sha256(paths[0].read_bytes()).hexdigest()
    assert updated["version_sha256"] != item["version_sha256"]
    assert new["snapshot"].snapshot_id != old["snapshot"].snapshot_id
    assert len(fake.calls) == 2


def test_same_basename_other_selected_source_does_not_overwrite(make_service):
    """FR-A-01 / INV-02: two selected origins are not one logical document."""
    service, fake, paths, _ = make_service()
    other = paths[0].parent / "other" / paths[0].name
    other.parent.mkdir()
    other.write_bytes(b"Synthetic independent origin.\n")
    service, fake, paths, _ = make_service(selected=[paths[0], other])
    first, old = one_ready(service, paths)
    second = service.import_files([other])
    assert second["items"][0]["document_id"] != old["document_id"]
    assert len(second["snapshot"].documents) == 2 and len(fake.calls) == 2
    assert read(service, first["snapshot"], old) == paths[0].read_bytes()


def test_failed_replacement_excludes_old_current_but_keeps_history(make_service):
    """FR-A-02 / INV-05; PROPOSED_INTEGRATION failed-version projection."""
    service, fake, paths, _ = make_service()
    old, item = one_ready(service, paths)
    original = paths[0].read_bytes()
    history = deepcopy(service.attempts(item["document_id"]))
    paths[0].write_bytes(b"Synthetic failing replacement.\n")
    fake.scripts[NAMES[0]] = ["parse_failed"]
    failed = service.import_files([paths[0]], replacements={paths[0]: item["document_id"]})
    assert failed["items"][0]["status"] == "failed" and failed["complete"] is False
    assert failed["snapshot"].documents == ()
    assert service.attempts(item["document_id"])[:-1] == history
    assert read(service, old["snapshot"], item) == original


def test_old_snapshot_disk_bytes_and_source_survive_external_mutation(make_service):
    """FR-A-02 / INV-05: compare real on-disk history, not fake snapshots."""
    service, _, paths, storage = make_service()
    old, item = one_ready(service, paths)
    snapshot = old["snapshot"]
    snapshot_path = storage / "snapshots" / f"{snapshot.snapshot_id}.json"
    serialized = snapshot_path.read_bytes()
    original = paths[0].read_bytes()
    paths[0].write_bytes(b"Synthetic external mutation.\n")
    assert read(service, snapshot, item) == original
    service.import_files([paths[0]], replacements={paths[0]: item["document_id"]})
    assert snapshot_path.read_bytes() == serialized
    assert CorpusSnapshot.model_validate_json(serialized) == snapshot
    assert read(service, snapshot, item) == original


@pytest.mark.parametrize("damage", ["missing", "hash_mismatch"])
def test_managed_source_missing_or_corrupted_read_refuses(make_service, damage):
    """INV-02/06: storage and SHA are real, not supplied by FakeIngest."""
    service, _, paths, storage = make_service()
    batch, item = one_ready(service, paths)
    managed = storage / "sources" / item["version_sha256"]
    assert managed.read_bytes() == paths[0].read_bytes()
    if damage == "missing":
        managed.unlink()
    else:
        managed.write_bytes(b"Synthetic tampered managed bytes.\n")
    with pytest.raises(ValueError, match="SOURCE_INTEGRITY"):
        read(service, batch["snapshot"], item)


def test_selected_legal_absolute_path_is_accepted(make_service):
    """FR-A-01 / INV-06: absolute is not synonymous with unauthorized."""
    service, fake, paths, _ = make_service()
    assert paths[0].is_absolute()
    batch, item = one_ready(service, paths)
    assert batch["complete"] is True and len(fake.calls) == 1
    assert read(service, batch["snapshot"], item) == paths[0].read_bytes()


@pytest.mark.parametrize("attack", ["unselected", "outside", "traversal", "file_link", "dir_link"])
def test_direct_service_path_authorization_refuses_unsafe_sources(make_service, tmp_path, attack):
    """FR-A-01 / INV-06 / SEC-01: direct service calls cannot bypass selection."""
    _, _, paths, _ = make_service()
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel.txt"
    sentinel.write_bytes(b"Synthetic outside sentinel; must not reach ingest.\n")
    root = paths[0].parent
    candidate = root / "unselected.txt"
    candidate.write_bytes(b"Synthetic unselected within allowed root.\n")
    selected = paths
    if attack == "outside":
        candidate = sentinel
        selected = [candidate]
    elif attack == "traversal":
        candidate = root / ".." / "outside" / sentinel.name
        selected = [candidate]
    elif attack == "file_link":
        candidate = root / "linked.txt"
        candidate.symlink_to(sentinel)
        selected = [candidate]
    elif attack == "dir_link":
        link = root / "linked-directory"
        link.symlink_to(outside, target_is_directory=True)
        candidate = link / sentinel.name
        selected = [candidate]
    service, fake, _, storage = make_service(selected=selected)
    before = sentinel.read_bytes()
    with pytest.raises(ValueError, match="SOURCE_NOT_AUTHORIZED"):
        service.import_files([candidate])
    assert fake.calls == [] and sentinel.read_bytes() == before
    assert not (storage / "current").exists()


@pytest.mark.parametrize("kind", ["empty", "unsupported", "oversize", "missing"])
def test_selected_invalid_file_never_reaches_ingest(make_service, kind):
    """FR-A-01: size/type/existence validation precedes external ingestion."""
    _, _, paths, _ = make_service()
    candidate = paths[0].parent / ("invalid.bin" if kind == "unsupported" else "invalid.txt")
    if kind != "missing":
        content = {"empty": b"", "unsupported": b"synthetic", "oversize": b"x" * 129}
        candidate.write_bytes(content[kind])
    service, fake, _, _ = make_service(selected=[candidate], max_bytes=128)
    batch = service.import_files([candidate])
    assert batch["items"][0]["status"] == "failed"
    assert batch["items"][0]["reason_code"] == {
        "empty": "EMPTY_SOURCE", "unsupported": "UNSUPPORTED_TYPE",
        "oversize": "SOURCE_TOO_LARGE", "missing": "SOURCE_MISSING",
    }[kind]
    assert batch["complete"] is False and batch["snapshot"].documents == ()
    assert fake.calls == []


@pytest.mark.parametrize("receipt", ["missing", "wrong_id", "wrong_version", "unknown_status"])
def test_invalid_receipt_cannot_become_ready(make_service, receipt):
    """FR-A-01 / INV-02; PROPOSED_INTEGRATION untrusted receipt validation."""
    service, fake, paths, _ = make_service()
    fake.scripts[NAMES[0]] = [receipt]
    batch = service.import_files(paths[:2])
    assert len(fake.calls) == 2
    assert item_for(batch, NAMES[0])["status"] == "failed"
    assert item_for(batch, NAMES[0])["reason_code"] == "INVALID_RECEIPT"
    assert item_for(batch, NAMES[1])["status"] == "ready"
    assert [d.source_name for d in batch["snapshot"].documents] == [NAMES[1]]
    assert batch["complete"] is False


@pytest.mark.parametrize("action,reason", [("timeout", "INGEST_TIMEOUT"), ("exception", "INGEST_ERROR")])
def test_ingest_exception_isolated_sanitized_and_not_retried(make_service, action, reason):
    """FR-A-01 / SEC-01; PROPOSED_INTEGRATION failure mapping, no auto retry."""
    service, fake, paths, _ = make_service()
    fake.scripts[NAMES[0]] = [action]
    batch = service.import_files(paths[:2])
    failed = item_for(batch, NAMES[0])
    assert failed["status"] == "failed" and failed["reason_code"] == reason
    assert item_for(batch, NAMES[1])["status"] == "ready"
    assert len(fake.calls) == 2 and len(batch["snapshot"].documents) == 1
    assert batch["complete"] is False
    public_text = repr(batch) + repr(service.attempts(failed["document_id"]))
    for private in (str(paths[0].parent), "synthetic-private", "token-example", "RuntimeError"):
        assert private not in public_text


@pytest.mark.parametrize("stage", ["copy_source", "write_manifest", "replace_current"])
def test_persistence_interruption_does_not_advance_or_overwrite(make_service, stage):
    """FR-A-02 / INV-05: injectable interruption, real disk/current comparison."""
    armed = False

    def fail_at(actual_stage):
        if armed and actual_stage == stage:
            raise OSError("synthetic persistence interruption")

    service, _, paths, storage = make_service(fault_hook=fail_at)
    old, item = one_ready(service, paths)
    pointer = (storage / "current").read_bytes()
    historical = {
        p: p.read_bytes() for folder in ("snapshots", "manifests", "sources")
        for p in (storage / folder).rglob("*") if p.is_file()
    }
    assert historical
    history = deepcopy(service.attempts(item["document_id"]))
    armed = True
    with pytest.raises(ValueError, match="PERSISTENCE_FAILED"):
        service.import_files([paths[1]])
    assert (storage / "current").read_bytes() == pointer
    assert service.current_snapshot() == old["snapshot"]
    assert service.attempts(item["document_id"]) == history
    assert all(path.read_bytes() == payload for path, payload in historical.items())
    armed = False
    restarted, fresh_fake, _, _ = make_service()
    assert restarted.current_snapshot() == old["snapshot"] and fresh_fake.calls == []


def test_read_rejects_document_or_version_not_in_snapshot(make_service):
    """INV-02/06: source possession alone cannot bypass exact snapshot membership."""
    service, _, paths, _ = make_service()
    old, item = one_ready(service, paths)
    later = service.import_files([paths[1]])
    other = later["items"][0]
    with pytest.raises(ValueError, match="SNAPSHOT_MEMBERSHIP"):
        read(service, old["snapshot"], other)
    forged = item | {"version_sha256": "0" * 64}
    with pytest.raises(ValueError, match="SNAPSHOT_MEMBERSHIP"):
        read(service, old["snapshot"], forged)


def test_freshness_revision_detects_aba_without_changing_shared_snapshot(make_service):
    """FR-A-02 / INV-02; PROPOSED_INTEGRATION A-local ABA token, not shared field."""
    service, fake, paths, _ = make_service()
    original, item = one_ready(service, paths)
    before = service.freshness()
    service.remove([item["document_id"]])
    removed = service.freshness()
    restored = service.restore([item["document_id"]])
    after = service.freshness()
    assert restored.snapshot_id == original["snapshot"].snapshot_id
    assert before[0] == after[0] and removed[0] != before[0]
    assert before[1] < removed[1] < after[1] and len(fake.calls) == 1
    assert "corpus_revision" not in restored.model_dump()
    assert "complete" not in restored.model_dump()
