"""Module E test proposal. FR-E-01/02, INV-02/04/05/08, SEC-01.

Synthetic only. Proposed public API awaiting independent test review.
Missing implementation must fail explicitly. No source implementation is supplied.
"""

from __future__ import annotations

import hashlib
import importlib
import importlib.util
import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def reports():
    assert importlib.util.find_spec("papertrace.reports") is not None, (
        "FR-E-01: reports implementation missing; expected RED before source approval"
    )
    return importlib.import_module("papertrace.reports")


def payload():
    """Preserve shared synthetic object identities without inventing digest values."""
    def shared(name):
        wrapper = json.loads((FIXTURES / "contracts" / f"{name}.json").read_text("utf-8"))
        assert wrapper["synthetic"] is True
        return wrapper["data"]

    scenario = json.loads((FIXTURES / "reports" / "scenarios.json").read_text("utf-8"))
    decision = shared("ReviewDecision")
    events = [{"command_id": "synthetic-command-1", "decision": decision}]
    ledger = {
        "schema_version": 1,
        "snapshot_id": decision["snapshot_id"],
        "question_id": decision["question_id"],
        "revision": 1,
        "events": events,
    }
    digest = hashlib.sha256(json.dumps(
        ledger, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()
    draft = shared("AnswerDraft")
    release = shared("ReleaseDecision")
    draft["review_digest"] = digest
    release["review_digest"] = digest
    return {
        "record_schema_version": 1,
        "record_id": "efaf8a8c-97e5-47ea-bada-79a1da14715b",
        "saved_at": "2026-11-20T00:00:00Z",
        "question": scenario["question"],
        "snapshot": shared("CorpusSnapshot"),
        "evidence": [shared("EvidenceRecord")],
        "review_events": events,
        "review_revision": 1,
        "review_digest": digest,
        "draft": draft,
        "release": release,
        "run_metadata": {},
    }


def record():
    return reports().ResearchRecord.model_validate(payload())


def test_shared_fixture_associations():
    """Test-preparation check independent of the future E implementation."""
    data = payload()
    snapshot_id = data["snapshot"]["snapshot_id"]
    for value in (data["evidence"][0], data["draft"], data["release"]):
        assert value["snapshot_id"] == snapshot_id
    assert data["draft"]["answer_id"] == data["release"]["answer_id"]
    assert data["draft"]["review_digest"] == data["release"]["review_digest"]


def test_save_reopen_preserves_original(tmp_path):
    api = reports()
    original = record()
    api.HistoryStore(tmp_path).save(original)
    loaded = api.HistoryStore(tmp_path).load(original.record_id)
    assert loaded.model_dump(mode="json") == original.model_dump(mode="json")


def test_conflicting_save_preserves_bytes(tmp_path):
    api = reports()
    original = record()
    store = api.HistoryStore(tmp_path)
    store.save(original)
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    with pytest.raises(api.RecordConflict):
        store.save(original)
    after = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert before == after


@pytest.mark.parametrize("record_id", ["../escape", "/outside", "C:\\outside", "a/b", ""])
def test_record_id_cannot_escape_root(tmp_path, record_id):
    api = reports()
    with pytest.raises(api.InvalidRecord):
        api.HistoryStore(tmp_path).load(record_id)


@pytest.mark.parametrize("mutation", ["schema", "unknown", "snapshot", "citation"])
def test_invalid_package_is_rejected(mutation):
    api = reports()
    data = payload()
    if mutation == "schema":
        data["record_schema_version"] = 999
    elif mutation == "unknown":
        data["unrecognized"] = True
    elif mutation == "snapshot":
        data["draft"]["snapshot_id"] = "snap-" + "0" * 64
    else:
        data["draft"]["citation_evidence_ids"] = ["ev-" + "0" * 64]
    with pytest.raises(ValueError):
        api.ResearchRecord.model_validate(data)


def test_exports_preserve_blocked_status_and_source_mapping():
    api = reports()
    original = record()
    exported = json.loads(api.export_json(original))
    markdown = api.export_markdown(original)
    assert exported["release"]["status"] == "blocked"
    assert "blocked" in markdown
    evidence_id = original.evidence[0].evidence_id
    assert evidence_id in markdown
    assert evidence_id in json.dumps(exported)
    assert original.evidence[0].document_id in markdown


def test_export_metadata_rejects_credentials():
    api = reports()
    data = payload()
    data["run_metadata"]["api_key"] = "SYNTHETIC_API_KEY_DO_NOT_EXPORT_20261120"
    with pytest.raises(ValueError):
        api.ResearchRecord.model_validate(data)


@pytest.mark.parametrize("status", ["released", "blocked", "abstained", "failed"])
def test_all_outcomes_roundtrip_without_status_promotion(tmp_path, status):
    api = reports()
    data = payload()
    if status == "released":
        data["release"]["status"] = "released"
        data["release"]["reason_codes"] = []
        for name in ("snapshot", "review", "evidence", "citation", "answer"):
            data["release"][f"{name}_check_passed"] = True
    elif status in ("abstained", "failed"):
        data["draft"].update(
            status=status, body="", citation_evidence_ids=[],
            refusal_reason="SYNTHETIC outcome",
        )
    original = api.ResearchRecord.model_validate(data)
    api.HistoryStore(tmp_path).save(original)
    loaded = api.HistoryStore(tmp_path).load(original.record_id)
    assert loaded.draft.status == original.draft.status
    assert loaded.release.status == original.release.status


@pytest.mark.parametrize("field", ["review_digest", "review_revision"])
def test_tampered_ledger_token_rejected(field):
    api = reports()
    data = payload()
    data[field] = "0" * 64 if field == "review_digest" else 2
    with pytest.raises(ValueError):
        api.ResearchRecord.model_validate(data)


def test_changed_current_snapshot_does_not_rewrite_history(tmp_path):
    api = reports()
    original = record()
    store = api.HistoryStore(tmp_path)
    store.save(original)
    before = store.load(original.record_id).model_dump_json()
    detail = api.history_detail(original, current_snapshot_id="snap-" + "0" * 64)
    assert detail["superseded"] is True
    assert store.load(original.record_id).model_dump_json() == before


def test_original_excerpt_requires_export_permission():
    api = reports()
    original = record()
    for exported in (api.export_json(original), api.export_markdown(original)):
        assert original.evidence[0].excerpt not in exported
    with pytest.raises(api.ExportPermissionDenied):
        api.export_json(original, include_excerpts=True)
    permission = api.ExportPermission(
        record_id=original.record_id,
        evidence_ids=(original.evidence[0].evidence_id,),
        purpose="external-export",
        granted_by="reviewer-SYNTHETIC",
    )
    for exporter in (api.export_json, api.export_markdown):
        with pytest.raises(api.ExportPermissionDenied):
            exporter(original, include_excerpts=True, permission=permission)
    # A trusted integration port validates the grant against its private ledger.
    trusted_grants = (permission,)
    service = api.ExportService(permission_verifier=lambda grant: grant is trusted_grants[0])
    for exporter in (service.export_json, service.export_markdown):
        assert original.evidence[0].excerpt in exporter(
            original, include_excerpts=True, permission=permission,
        )


@pytest.mark.parametrize("scope", ["wrong-record", "no-evidence", "internal-read"])
def test_export_permission_must_match_record_evidence_and_purpose(scope):
    api = reports()
    original = record()
    permission = api.ExportPermission(
        record_id="d3a03bf6-88af-4acb-a368-c1a02592192d"
        if scope == "wrong-record" else original.record_id,
        evidence_ids=() if scope == "no-evidence" else (original.evidence[0].evidence_id,),
        purpose="internal-read" if scope == "internal-read" else "external-export",
        granted_by="reviewer-SYNTHETIC",
    )
    for exporter in (api.export_json, api.export_markdown):
        with pytest.raises(api.ExportPermissionDenied):
            exporter(original, include_excerpts=True, permission=permission)


def test_symlink_history_root_cannot_escape(tmp_path):
    api = reports()
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel.txt"
    sentinel.write_text("SYNTHETIC unchanged", encoding="utf-8")
    linked = tmp_path / "history"
    linked.symlink_to(outside, target_is_directory=True)
    with pytest.raises(api.InvalidRecord):
        api.HistoryStore(linked).save(record())
    assert sentinel.read_text("utf-8") == "SYNTHETIC unchanged"
    assert sorted(p.name for p in outside.iterdir()) == ["sentinel.txt"]


@pytest.mark.parametrize("path", ["/Users/SYNTHETIC/private/paper.pdf", "C:\\Users\\SYNTHETIC\\paper.pdf"])
def test_absolute_path_in_metadata_is_rejected(path):
    api = reports()
    data = payload()
    data["run_metadata"]["source_path"] = path
    with pytest.raises(ValueError):
        api.ResearchRecord.model_validate(data)


@pytest.mark.parametrize("path", ["/Users/SYNTHETIC/private/paper.pdf", "C:\\Users\\SYNTHETIC\\paper.pdf"])
def test_absolute_path_in_free_text_is_not_exported(path):
    api = reports()
    data = payload()
    data["draft"]["body"] = f"SYNTHETIC answer from {path}"
    original = api.ResearchRecord.model_validate(data)
    for exporter in (api.export_json, api.export_markdown):
        assert path not in exporter(original)


def test_write_failure_does_not_damage_previous_record(tmp_path, monkeypatch):
    api = reports()
    original = record()
    store = api.HistoryStore(tmp_path)
    store.save(original)
    before = store.load(original.record_id).model_dump_json()
    data = payload()
    data["record_id"] = "d3a03bf6-88af-4acb-a368-c1a02592192d"
    second = api.ResearchRecord.model_validate(data)

    reached = []

    def disk_failure(*args, **kwargs):
        reached.append(True)
        raise OSError("SYNTHETIC disk full")

    # Public injectable boundary receives the serialized bytes for atomic storage.
    store = api.HistoryStore(tmp_path, atomic_writer=disk_failure)
    with pytest.raises(OSError):
        store.save(second)
    assert reached == [True]
    assert store.load(original.record_id).model_dump_json() == before
    assert second.record_id not in [item.record_id for item in store.list_records()]
    assert {p.name for p in tmp_path.iterdir()} == {f"{original.record_id}.json"}


def test_forged_export_grant_is_rejected_by_trusted_verifier():
    api = reports()
    original = record()
    forged = api.ExportPermission(
        record_id=original.record_id,
        evidence_ids=(original.evidence[0].evidence_id,),
        purpose="external-export",
        granted_by="reviewer-SYNTHETIC",
    )
    issued = api.ExportPermission(
        record_id=original.record_id,
        evidence_ids=(original.evidence[0].evidence_id,),
        purpose="external-export",
        granted_by="reviewer-SYNTHETIC",
    )
    checked = []

    def reject_unissued_grant(grant):
        checked.append(grant)
        return grant is issued

    service = api.ExportService(permission_verifier=reject_unissued_grant)
    for exporter in (service.export_json, service.export_markdown):
        with pytest.raises(api.ExportPermissionDenied):
            exporter(
                original, include_excerpts=True, permission=forged,
            )
    assert checked == [forged, forged]


# ---------------------------------------------------------------------------
# REVIEW REGRESSION: nested private-path disclosure in default exports.
# Synthetic only; no real paths, no model runs, no shell. These tests are
# appended proposals and must receive independent precise-head approval before
# any source repair.
# ---------------------------------------------------------------------------

SYNTHETIC_ABSOLUTE_PATHS = (
    "C:\\Users\\SYNTHETIC\\private\\paper.pdf",  # Windows drive
    "\\\\SYNTHETIC-host\\private-share\\paper.pdf",  # UNC
    "/Users/SYNTHETIC/private/paper.pdf",  # POSIX
)


def canonical_sha256(value):
    """Independent canonical JSON digest; never reports' own digest truth helper."""
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_shared(name):
    """Read a shared synthethic contract fixture (raw dict, no model)."""
    wrapper = json.loads((FIXTURES / "contracts" / f"{name}.json").read_text("utf-8"))
    assert wrapper["synthetic"] is True
    return wrapper["data"]


def rebuild_snapshot(documents, created_at="2026-01-01T00:00:00Z"):
    """Rebuild CorpusSnapshot via real validators after removing snapshot_id."""
    from papertrace.contracts import CorpusSnapshot

    return CorpusSnapshot.model_validate(
        {"schema_version": 1, "documents": list(documents), "created_at": created_at}
    )


def rebuild_evidence(fields):
    """Rebuild EvidenceRecord via real validators after removing evidence_id."""
    from papertrace.contracts import EvidenceRecord

    body = {key: value for key, value in fields.items() if key != "evidence_id"}
    return EvidenceRecord.model_validate(body)


def ledger_digest(events, snapshot_id, question_id, revision):
    """Recompute C ledger digest with an independent canonical hash."""
    return canonical_sha256(
        {
            "schema_version": 1,
            "snapshot_id": snapshot_id,
            "question_id": question_id,
            "revision": revision,
            "events": list(events),
        }
    )


def bind_digest(record_data):
    """Bind the C ledger digest to the events, revision and mapped identities.

    Call after ``identity_covered_record`` builds ``data``. This only touches the
    review digest token; it does not select a replacement secret. It does *not*
    rebuild the draft/release graph already mapped by the caller.
    """
    events = record_data["review_events"]
    revision = record_data["review_revision"]
    snapshot_id = record_data["snapshot"]["snapshot_id"]
    # Derive question_id from the draft: safe for empty ``events`` too, so no
    # ``events[0]`` indexing or dynamic decision access is needed.
    question_id = record_data["draft"]["question_id"]
    digest = ledger_digest(events, snapshot_id, question_id, revision)
    record_data["review_digest"] = digest
    record_data["draft"]["review_digest"] = digest
    record_data["release"]["review_digest"] = digest
    return digest


def identity_covered_record(api, mutate):
    """Build a validated ResearchRecord from ``raw_record_data``.

    ``mutate`` sees mutable snapshot documents, evidence fields, review event
    (``command_id`` + nested ``decision``), draft and release. Identity and the
    C ledger digest are recomputed by the shared builder + ``bind_digest``.
    """
    data = raw_record_data(mutate)
    bind_digest(data)
    return api.ResearchRecord.model_validate(data)


def json_contains_path(value, needle):
    """Recursively inspect parsed JSON strings and keys so escapes cannot pass."""
    if isinstance(value, str):
        return needle in value
    if isinstance(value, dict):
        return any(
            json_contains_path(key, needle) or json_contains_path(item, needle)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(json_contains_path(item, needle) for item in value)
    return False


def basename(path):
    """Final path component, so redaction that drops only a prefix cannot pass."""
    return path.replace("\\", "/").rsplit("/", 1)[-1]


def identity_tokens(record_model):
    decision = record_model.review_events[0].decision
    return {
        "snapshot_id": record_model.snapshot.snapshot_id,
        "evidence_id": record_model.evidence[0].evidence_id,
        "review_digest": record_model.review_digest,
        "review_revision": record_model.review_revision,
        "reviewed_snapshot_id": decision.snapshot_id,
        "reviewed_evidence_id": decision.evidence_id,
    }


def assert_export_hides_path(api, original, path, tmp_path, internal_text):
    """JSON (parsed recursively) and Markdown hide path and its basename.

    Identity/digest tokens in the export stay unchanged; internal model and
    saved/reopened data retain the original unredacted text. We do not assert a
    replacement string and do not claim export roundtrip integrity.
    """
    exported_json = json.loads(api.export_json(original))
    markdown = api.export_markdown(original)
    for needle in (path, basename(path)):
        assert not json_contains_path(exported_json, needle)
        assert needle not in markdown
    # Exact JSON field comparisons instead of loose substring search, so escaped
    # tokens cannot pass and the field values must survive the export intact.
    assert exported_json["snapshot"]["snapshot_id"] == original.snapshot.snapshot_id
    assert exported_json["evidence"][0]["evidence_id"] == original.evidence[0].evidence_id
    assert exported_json["review_digest"] == original.review_digest
    assert exported_json["review_revision"] == original.review_revision
    exported_event = exported_json["review_events"][0]
    exported_decision = exported_event["decision"]
    internal_decision = original.review_events[0].decision
    assert exported_decision["snapshot_id"] == internal_decision.snapshot_id
    assert exported_decision["evidence_id"] == internal_decision.evidence_id
    store = api.HistoryStore(tmp_path)
    store.save(original)
    reopened = store.load(original.record_id)
    # Backslash JSON escaping means raw substring checks fail for Windows/UNC.
    assert json_contains_path(reopened.model_dump(mode="json"), internal_text)
    assert identity_tokens(reopened)["review_digest"] == identity_tokens(original)["review_digest"]


@pytest.mark.parametrize("path", SYNTHETIC_ABSOLUTE_PATHS)
def test_review_reason_private_path_is_not_exported(path, tmp_path):
    api = reports()
    decision_box = {}

    def mutate(decision, **parts):
        decision["reason"] = f"SYNTHETIC review {path}"
        decision_box["text"] = decision["reason"]

    original = identity_covered_record(api, mutate)
    # ReviewDecision is a shared contract model: attribute access, not subscript.
    assert path in original.review_events[0].decision.reason
    assert original.review_events[0].decision.reason == decision_box["text"]
    assert_export_hides_path(api, original, path, tmp_path, decision_box["text"])


@pytest.mark.parametrize("path", SYNTHETIC_ABSOLUTE_PATHS)
def test_document_title_private_path_is_not_exported(path, tmp_path):
    api = reports()
    title_box = {}

    def mutate(documents, **parts):
        documents[0]["title"] = f"SYNTHETIC paper {path}"
        title_box["text"] = documents[0]["title"]

    original = identity_covered_record(api, mutate)
    assert path in original.snapshot.documents[0].title
    assert original.snapshot.documents[0].title == title_box["text"]
    assert_export_hides_path(api, original, path, tmp_path, title_box["text"])


NESTED_PATH_FIELDS = (
    "command_id",
    "locator_chunk_id",
    "locator_parser_name",
    "locator_parser_version",
    "upstream_context_id",
    "advisory_summary",
    "draft_body",
    "abstained_refusal_reason",
)


def _set_nested_field(field, event, evidence, draft, text):
    if field == "command_id":
        event["command_id"] = text
    elif field == "locator_chunk_id":
        evidence["locator"]["chunk_id"] = text
    elif field == "locator_parser_name":
        evidence["locator"]["parser_name"] = text
    elif field == "locator_parser_version":
        evidence["locator"]["parser_version"] = text
    elif field == "upstream_context_id":
        evidence["upstream_context_id"] = text
    elif field == "advisory_summary":
        evidence["advisory_summary"] = text
    elif field == "draft_body":
        draft["body"] = text
    elif field == "abstained_refusal_reason":
        draft["status"] = "abstained"
        draft["refusal_reason"] = text
    else:  # pragma: no cover - guards the parameter list
        raise AssertionError(f"unknown nested field {field}")


def _read_nested_field(field, original):
    if field == "command_id":
        return original.review_events[0].command_id
    evidence = original.evidence[0]
    if field == "locator_chunk_id":
        return evidence.locator.chunk_id
    if field == "locator_parser_name":
        return evidence.locator.parser_name
    if field == "locator_parser_version":
        return evidence.locator.parser_version
    if field == "upstream_context_id":
        return evidence.upstream_context_id
    if field == "advisory_summary":
        return evidence.advisory_summary
    if field == "draft_body":
        return original.draft.body
    return original.draft.refusal_reason


def raw_record_data(mutate):
    """Build unvalidated record ``data`` with consistent identity mapping.

    Mirrors ``identity_covered_record`` but returns the raw mapping so callers
    can run ``bind_digest`` last. Snapshot/evidence are rebuilt via shared
    contract validators; references are mapped across evidence/review/draft/
    release. ``mutate`` may adjust documents, evidence, event (``command_id`` and
    nested ``decision``), draft and release before validation.
    """
    base = payload()
    snapshot_fields = {
        key: value
        for key, value in base["snapshot"].items()
        if key not in ("snapshot_id", "documents")
    }
    documents = [dict(document) for document in base["snapshot"]["documents"]]
    evidence_fields = {
        key: value for key, value in base["evidence"][0].items() if key != "evidence_id"
    }
    evidence_fields["locator"] = dict(evidence_fields["locator"])
    event = {
        "command_id": base["review_events"][0]["command_id"],
        "decision": dict(base["review_events"][0]["decision"]),
    }
    draft = dict(base["draft"])
    release = dict(base["release"])
    release["reason_codes"] = list(release["reason_codes"])

    mutate(
        documents=documents,
        evidence=evidence_fields,
        event=event,
        decision=event["decision"],
        draft=draft,
        release=release,
    )

    snapshot = rebuild_snapshot(documents, snapshot_fields["created_at"])
    evidence_fields["snapshot_id"] = snapshot.snapshot_id
    evidence_fields["document_id"] = documents[0]["document_id"]
    evidence_fields["version_sha256"] = documents[0]["version_sha256"]
    evidence = rebuild_evidence(evidence_fields)

    decision = event["decision"]
    decision["snapshot_id"] = snapshot.snapshot_id
    decision["evidence_id"] = evidence.evidence_id
    decision["question_id"] = draft["question_id"]
    revision = draft["review_revision"]
    draft["snapshot_id"] = snapshot.snapshot_id
    draft["review_revision"] = revision
    if draft["status"] == "draft":
        draft["approved_evidence_ids"] = [evidence.evidence_id]
        draft["sent_evidence_ids"] = [evidence.evidence_id]
        draft["citation_evidence_ids"] = [evidence.evidence_id]
    else:
        draft["body"] = ""
        draft["citation_evidence_ids"] = []
        if not draft.get("refusal_reason"):
            draft["refusal_reason"] = "SYNTHETIC abstained without evidence."
    release["snapshot_id"] = snapshot.snapshot_id
    release["question_id"] = draft["question_id"]
    release["review_revision"] = revision

    data = dict(base)
    data["snapshot"] = snapshot.model_dump(mode="json")
    data["evidence"] = [evidence.model_dump(mode="json")]
    data["review_events"] = [event]
    data["review_revision"] = revision
    data["draft"] = draft
    data["release"] = release
    return data


@pytest.mark.parametrize("field", NESTED_PATH_FIELDS)
@pytest.mark.parametrize("path", SYNTHETIC_ABSOLUTE_PATHS)
def test_nested_private_path_is_not_exported(field, path, tmp_path):
    api = reports()
    text_box = {}

    def mutate(event, decision, evidence, draft, **parts):
        text = f"SYNTHETIC {path}"
        _set_nested_field(field, event, evidence, draft, text)
        text_box["text"] = text

    data = raw_record_data(mutate)
    bind_digest(data)
    original = api.ResearchRecord.model_validate(data)
    internal_text = text_box["text"]

    assert path in _read_nested_field(field, original)
    assert json_contains_path(original.model_dump(mode="json"), internal_text)
    assert_export_hides_path(api, original, path, tmp_path, internal_text)


def empty_record_payload(*, status, corpus, refusal_text="SYNTHETIC abstained: no approved evidence."):
    """No-evidence / no-events / revision-0 record built with real contracts.

    ``corpus`` is ``"empty"`` (no documents) or ``"populated"`` (synthetic doc).
    Snapshot and evidence are rebuilt via real ``CorpusSnapshot``/``EvidenceRecord``.
    Review has no events at revision 0, so the independent canonical C-ledger
    digest is the digest of an empty event list. Draft ``abstained``/``failed``
    carries empty body, empty scopes and a synthetic refusal reason. Release is
    ``blocked`` with ``NO_APPROVED_EVIDENCE``. Returns raw validated-model data.
    """
    from papertrace.contracts import AnswerDraft, CorpusSnapshot, ReleaseDecision

    base = payload()
    if corpus == "empty":
        documents = []
    else:
        documents = [dict(document) for document in base["snapshot"]["documents"]]
    snapshot = CorpusSnapshot.model_validate(
        {"schema_version": 1, "documents": documents, "created_at": base["snapshot"]["created_at"]}
    )

    events = []
    revision = 0
    digest = ledger_digest(events, snapshot.snapshot_id, base["draft"]["question_id"], revision)

    draft = AnswerDraft.model_validate({
        "schema_version": 1,
        "answer_id": base["draft"]["answer_id"],
        "snapshot_id": snapshot.snapshot_id,
        "question_id": base["draft"]["question_id"],
        "review_revision": revision,
        "review_digest": digest,
        "approved_evidence_ids": [],
        "sent_evidence_ids": [],
        "citation_evidence_ids": [],
        "status": status,
        "body": "",
        "refusal_reason": refusal_text,
        "generated_at": base["draft"]["generated_at"],
    })
    release = ReleaseDecision.model_validate({
        "schema_version": 1,
        "answer_id": draft.answer_id,
        "snapshot_id": snapshot.snapshot_id,
        "question_id": draft.question_id,
        "review_revision": revision,
        "review_digest": digest,
        "status": "blocked",
        "reason_codes": ["NO_APPROVED_EVIDENCE"],
        "snapshot_check_passed": True,
        "review_check_passed": False,
        "evidence_check_passed": False,
        "citation_check_passed": False,
        "answer_check_passed": True,
        "decided_at": base["release"]["decided_at"],
    })

    data = dict(base)
    data["snapshot"] = snapshot.model_dump(mode="json")
    data["evidence"] = []
    data["review_events"] = events
    data["review_revision"] = revision
    data["review_digest"] = digest
    data["draft"] = draft.model_dump(mode="json")
    data["release"] = release.model_dump(mode="json")
    return data


@pytest.mark.parametrize("status", ["abstained", "failed"])
@pytest.mark.parametrize("corpus", ["empty", "populated"])
def test_no_evidence_abstained_blocked_persists_without_promotion(tmp_path, status, corpus):
    api = reports()
    data = empty_record_payload(status=status, corpus=corpus)

    # Independent shared-contract validation before assembling the record.
    from papertrace.contracts import AnswerDraft, ReleaseDecision

    draft = AnswerDraft.model_validate(data["draft"])
    release = ReleaseDecision.model_validate(data["release"])
    assert draft.status == status
    assert draft.review_revision == 0
    assert draft.approved_evidence_ids == draft.sent_evidence_ids == draft.citation_evidence_ids == ()
    assert release.status == "blocked"
    assert release.reason_codes == ("NO_APPROVED_EVIDENCE",)
    assert data["review_digest"] == canonical_sha256(
        {
            "schema_version": 1,
            "snapshot_id": data["snapshot"]["snapshot_id"],
            "question_id": draft.question_id,
            "revision": 0,
            "events": [],
        }
    )

    original = api.ResearchRecord.model_validate(data)
    store = api.HistoryStore(tmp_path)
    store.save(original)
    before = store.load(original.record_id).model_dump_json()

    reopened = store.load(original.record_id)
    assert reopened.draft.status == status
    assert reopened.draft.review_revision == 0
    assert reopened.release.status == "blocked"
    assert reopened.release.review_revision == 0
    assert [item.record_id for item in store.list_records()] == [original.record_id]

    exported_json = json.loads(api.export_json(original))
    markdown = api.export_markdown(original)
    assert exported_json["draft"]["status"] == status
    assert exported_json["release"]["status"] == "blocked"
    assert exported_json["review_revision"] == 0
    assert exported_json["review_digest"] == original.review_digest
    assert status in markdown
    assert "blocked" in markdown

    # No promotion on reload: previous bytes unchanged.
    assert store.load(original.record_id).model_dump_json() == before


@pytest.mark.parametrize("status", ["abstained", "failed"])
def test_no_evidence_abstained_blocked_export_lists_without_identity_drift(tmp_path, status):
    api = reports()
    original = api.ResearchRecord.model_validate(
        empty_record_payload(status=status, corpus="populated")
    )
    store = api.HistoryStore(tmp_path)
    store.save(original)
    listed = store.list_records()
    assert [item.record_id for item in listed] == [original.record_id]

    exported_json = json.loads(api.export_json(original))
    assert exported_json["snapshot"]["snapshot_id"] == original.snapshot.snapshot_id
    assert exported_json["review_digest"] == original.review_digest
    assert exported_json["review_revision"] == original.review_revision
    assert exported_json["evidence"] == []
    assert exported_json["review_events"] == []


def test_no_reviews_abstained_blocked_rev0_with_candidate_evidence(tmp_path):
    api = reports()
    data = empty_record_payload(status="abstained", corpus="populated")
    # Candidate evidence exists, but no review decision was recorded at revision 0.
    candidate = load_shared("EvidenceRecord")
    candidate["snapshot_id"] = data["snapshot"]["snapshot_id"]
    rebuilt = rebuild_evidence(candidate)
    data["evidence"] = [rebuilt.model_dump(mode="json")]

    original = api.ResearchRecord.model_validate(data)
    assert original.review_events == ()
    assert original.review_revision == 0
    assert original.draft.approved_evidence_ids == ()
    assert original.draft.citation_evidence_ids == ()
    assert original.release.status == "blocked"

    store = api.HistoryStore(tmp_path)
    store.save(original)
    reopened = store.load(original.record_id)
    assert reopened.draft.status == "abstained"
    assert reopened.release.status == "blocked"
    assert reopened.review_revision == 0


EMPTY_RECORD_MUTATIONS = (
    "bad_empty_digest",
    "revision1_no_events",
    "stale_draft_digest",
    "stale_release_digest",
    "unknown_evidence_ref",
    "released_without_checks",
)


@pytest.mark.parametrize("mutation", EMPTY_RECORD_MUTATIONS)
def test_empty_record_negative_variants_are_rejected(mutation):
    api = reports()
    data = empty_record_payload(status="abstained", corpus="populated")
    if mutation == "bad_empty_digest":
        data["review_digest"] = "0" * 64
    elif mutation == "revision1_no_events":
        data["review_revision"] = 1
        data["draft"]["review_revision"] = 1
        data["release"]["review_revision"] = 1
        bind_digest(data)
    elif mutation == "stale_draft_digest":
        data["draft"]["review_digest"] = "0" * 64
    elif mutation == "stale_release_digest":
        data["release"]["review_digest"] = "0" * 64
    elif mutation == "unknown_evidence_ref":
        unknown = "ev-" + "a" * 64
        data["draft"]["approved_evidence_ids"] = [unknown]
        data["draft"]["sent_evidence_ids"] = [unknown]
    else:
        data["release"]["status"] = "released"
        data["release"]["reason_codes"] = []
        for name in ("snapshot", "review", "evidence", "citation", "answer"):
            data["release"][f"{name}_check_passed"] = True
    with pytest.raises(ValueError):
        api.ResearchRecord.model_validate(data)


# ---------------------------------------------------------------------------
# PR18 REVIEW REGRESSION (batch 1): recursive run_metadata inspection.
# Synthetic only. ``_check_metadata`` must recurse list-within-list so nested
# credentials/passwords and nested absolute paths are rejected. These are
# appended proposals and require independent precise-head approval before any
# source repair. No production helpers or validation mocks are used.
# ---------------------------------------------------------------------------

# Contract rejects sensitive KEYS and absolute paths, not arbitrary strings that
# merely look secret. Values are clearly synthetic; names kept neutral (no
# password/token words) to avoid Ruff S105.
SENTINEL_A = "SYNTHETIC_VALUE_A_20261123"
SENTINEL_B = "SYNTHETIC_VALUE_B_20261123"
SENTINEL_C = "SYNTHETIC_VALUE_C_20261123"
SENTINEL_D = "SYNTHETIC_VALUE_D_20261123"
SYNTHETIC_NESTED_POSIX = "/Users/SYNTHETIC/nested/paper.pdf"
SYNTHETIC_NESTED_WINDOWS = "C:\\Users\\SYNTHETIC\\nested\\paper.pdf"
SYNTHETIC_NESTED_UNC = "\\\\SYNTHETIC-host\\nested-share\\paper.pdf"


@pytest.mark.parametrize(
    "case_key, value",
    [
        ("nested_api_key", [{"api_key": SENTINEL_A}]),
        ("nested_password", [[{"password": SENTINEL_B}]]),
        ("nested_posix_path", [[SYNTHETIC_NESTED_POSIX]]),
        ("nested_windows_path", [[{"path": SYNTHETIC_NESTED_WINDOWS}]]),
        ("nested_unc_path", ([SYNTHETIC_NESTED_UNC],)),
        (
            "mixed_containers",
            {"outer": [([{"private_key": SENTINEL_C}],)]},
        ),
    ],
)
def test_nested_metadata_rejects_credentials_and_paths(case_key, value):
    """Initial ``model_validate`` must recurse nested lists/tuples/dicts."""
    api = reports()
    data = payload()
    data["run_metadata"][case_key] = value
    with pytest.raises(ValueError):
        api.ResearchRecord.model_validate(data)


def test_safe_nested_metadata_roundtrips(tmp_path):
    """Arbitrary nested safe metadata survives save/reopen unchanged (JSON)."""
    api = reports()
    data = payload()
    data["run_metadata"] = {
        "synthetic_run": {
            "code_version": "SYNTHETIC-version-1",
            "attempts": [1, 2, 3],
            "nested": [{"latency_ms": 12, "ratio": 0.5}, [True, False]],
            "labels": ["alpha", "beta"],
        },
        "model_name": "SYNTHETIC-model",
        "temperature": 0.0,
    }
    original = api.ResearchRecord.model_validate(data)
    store = api.HistoryStore(tmp_path)
    store.save(original)
    reopened = store.load(original.record_id)
    assert reopened.model_dump(mode="json") == original.model_dump(mode="json")


# ---------------------------------------------------------------------------
# PR18 REVIEW REGRESSION (batch 2): post-construction run_metadata mutation.
# Synthetic only. Mutating a frozen ResearchRecord's run_metadata after
# validation must not let HistoryStore.save persist secrets/absolute paths.
# The injected writer records calls and raises AssertionError if reached, so a
# rejection that still serializes/writes cannot pass. No model_construct/copy
# bypass; no validation mocks. Appended proposals requiring independent
# precise-head approval before any source repair.
# ---------------------------------------------------------------------------

SECOND_RECORD_ID = "0b8f5f0e-2d4c-4f3e-9a51-7c6e2f0d1a23"

SAFE_MUTABLE_METADATA = {
    "synthetic_run": {
        "code_version": "SYNTHETIC-mutated-version",
        "attempts": [4, 5, 6],
        "nested": [{"latency_ms": 7, "ratio": 0.25}, [True]],
    },
}

POISON_MUTATIONS = (
    ("top_level_api_key", lambda meta: meta.__setitem__("api_key", SENTINEL_A)),
    (
        "nested_list_password",
        lambda meta: meta.__setitem__("box", [[{"password": SENTINEL_B}]]),
    ),
    (
        "nested_list_abs_path",
        lambda meta: meta.__setitem__("box", [[{"path": SYNTHETIC_NESTED_POSIX}]]),
    ),
)


def _snapshot_dir_bytes(root):
    return {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def _second_record(api, *, metadata=None):
    data = payload()
    data["record_id"] = SECOND_RECORD_ID
    data["run_metadata"] = dict(SAFE_MUTABLE_METADATA) if metadata is None else metadata
    return api.ResearchRecord.model_validate(data)


@pytest.mark.parametrize("case_key, poison", POISON_MUTATIONS)
def test_mutated_run_metadata_rejected_before_writer(tmp_path, case_key, poison):
    """Poisoned save must raise ValueError and never reach the writer."""
    api = reports()
    predecessor = record()
    store = api.HistoryStore(tmp_path)
    store.save(predecessor)
    before = _snapshot_dir_bytes(tmp_path)

    calls = []

    def sentinel_writer(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("atomic_writer must not be called for rejected metadata")

    poisoned = _second_record(api)
    run_metadata = poisoned.run_metadata
    poison(run_metadata)
    assert isinstance(run_metadata, dict), case_key

    guarded = api.HistoryStore(tmp_path, atomic_writer=sentinel_writer)
    with pytest.raises(ValueError):
        guarded.save(poisoned)

    assert calls == []
    assert _snapshot_dir_bytes(tmp_path) == before
    assert not (tmp_path / f"{SECOND_RECORD_ID}.json").exists()
    assert [item.record_id for item in guarded.list_records()] == [predecessor.record_id]
    assert guarded.load(predecessor.record_id).model_dump(mode="json") == (
        predecessor.model_dump(mode="json")
    )


def test_actual_writer_rejects_poisoned_metadata_without_secret(tmp_path):
    """Default (real) atomic writer path: ValueError, no file, no secret."""
    api = reports()
    predecessor = record()
    api.HistoryStore(tmp_path).save(predecessor)

    poisoned = _second_record(api)
    poisoned.run_metadata["api_key"] = SENTINEL_A

    with pytest.raises(ValueError):
        api.HistoryStore(tmp_path).save(poisoned)

    assert not (tmp_path / f"{SECOND_RECORD_ID}.json").exists()
    for path in (p for p in tmp_path.rglob("*") if p.is_file()):
        assert SENTINEL_A not in path.read_text("utf-8")


def test_external_alias_metadata_mutation_is_not_persisted(tmp_path):
    """Mutating the validated record's metadata dict alias is caught by save."""
    api = reports()
    data = payload()
    data["record_id"] = SECOND_RECORD_ID
    data["run_metadata"] = {
        "synthetic_run": {"nested": {"labels": ["alpha"], "ratio": 0.5}},
    }
    alias = data["run_metadata"]["synthetic_run"]["nested"]
    candidate = api.ResearchRecord.model_validate(data)

    # Poison the original dictionary alias AFTER validation.
    alias["api_key"] = SENTINEL_A

    predecessor = record()
    store = api.HistoryStore(tmp_path)
    store.save(predecessor)
    before = _snapshot_dir_bytes(tmp_path)

    calls = []

    def sentinel_writer(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("atomic_writer must not be called for rejected metadata")

    guarded = api.HistoryStore(tmp_path, atomic_writer=sentinel_writer)

    # Inspect the serialized MODEL metadata (not the input mapping) to select
    # the branch and to prove what save would persist.
    model_metadata = candidate.model_dump(mode="json")["run_metadata"]
    if "api_key" not in json.dumps(model_metadata):
        # Defensive copy: model never saw the poison; save through the DEFAULT
        # store (no sentinel) since safe data must persist.
        store.save(candidate)
        persisted_metadata = json.loads(
            (tmp_path / f"{SECOND_RECORD_ID}.json").read_text("utf-8")
        )["run_metadata"]
        assert "api_key" not in json.dumps(persisted_metadata)
        assert SENTINEL_A not in (tmp_path / f"{SECOND_RECORD_ID}.json").read_text("utf-8")
        reopened = store.load(candidate.record_id)
        assert reopened.model_dump(mode="json") == candidate.model_dump(mode="json")
    else:
        # Shared reference: the model's own metadata carries the poison; save
        # must reject before the writer and leave the directory untouched.
        assert SENTINEL_A in json.dumps(model_metadata)
        with pytest.raises(ValueError):
            guarded.save(candidate)
        assert calls == []
        assert _snapshot_dir_bytes(tmp_path) == before
        assert not (tmp_path / f"{SECOND_RECORD_ID}.json").exists()


def test_safe_mutated_metadata_persists(tmp_path):
    """Safe mutated metadata is valid and must persist through the default store."""
    api = reports()
    predecessor = record()
    store = api.HistoryStore(tmp_path)
    store.save(predecessor)

    candidate = _second_record(api)
    candidate.run_metadata["synthetic_run"]["attempts"] = [7, 8, 9]

    store.save(candidate)
    reopened = store.load(candidate.record_id)
    assert reopened.model_dump(mode="json") == candidate.model_dump(mode="json")
    assert reopened.run_metadata["synthetic_run"]["attempts"] == [7, 8, 9]
    assert [item.record_id for item in store.list_records()] == [
        predecessor.record_id,
        candidate.record_id,
    ]


# ---------------------------------------------------------------------------
# PAGE WIRING PROPOSAL (batch 1): injectable E page component.
# Synthetic only. Proposed API awaiting independent precise-head approval:
#   papertrace.reports.view.render_reports_panel(
#       ui, *, store, pending_record=None, current_snapshot_id=None, input_error=None)
# The view module must NOT import Streamlit; the ``ui`` double is injected by the
# caller. Missing ``view`` module is an ordinary availability assertion (RED), not
# a collection error and not a skip. No source implementation is supplied and no
# production fallback/preview is exercised here. These tests capture writes by
# wrapping the REAL HistoryStore.save, never by pretending a failed write
# succeeded. Appended proposals requiring independent precise-head approval
# before any source implementation.
# ---------------------------------------------------------------------------


def _view_module():
    """Locate ``papertrace.reports.view`` and fail as an ordinary assertion.

    Collection must succeed even before the view exists: we assert both that the
    parent package resolves and that the concrete submodule is importable, so a
    missing implementation reports availability (RED) rather than an import or
    skip during collection. We never fall back to ``papertrace.reports`` itself.
    """
    assert importlib.util.find_spec("papertrace.reports") is not None, (
        "FR-E-01: reports package missing; expected RED before source approval"
    )
    spec = importlib.util.find_spec("papertrace.reports.view")
    assert spec is not None, (
        "PAGE WIRING: papertrace.reports.view missing; expected RED until the "
        "page-wiring tests receive an independent precise-head approval"
    )
    module = importlib.import_module("papertrace.reports.view")
    assert hasattr(module, "render_reports_panel"), (
        "PAGE WIRING: render_reports_panel not implemented in reports.view"
    )
    return module


def _collect_strings(value):
    """Recursively yield every string leaf and dict key inside ``value``.

    Structured widgets may receive dicts/lists/tuples/sets (or objects with a
    mapping/sequence shape); flattening both values *and* keys means a sentinel
    cannot hide as a JSON field name or nesting level that a shallow substring
    test over ``str(obj)`` would miss. Non-container leaves are stringified so
    numbers/booleans still contribute their textual form.
    """
    if isinstance(value, str):
        yield value
    elif isinstance(value, (bytes, bytearray)):
        yield value.decode("utf-8")
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _collect_strings(key)
            yield from _collect_strings(item)
    elif isinstance(value, (list, tuple, set, frozenset)):
        for item in value:
            yield from _collect_strings(item)
    else:
        yield str(value)


class FakeUI:
    """Explicit Streamlit-like double. No silent ``__getattr__`` fallback.

    Only the widgets/display helpers the page is expected to call are exposed;
    any other attribute access raises ``AttributeError`` so an unexpected call
    becomes a hard failure instead of a silently mirrored passthrough. Every
    call is captured verbatim. ``button`` returns a scripted value per label
    (default ``False``). ``selectbox`` returns by index into the injected
    options, which are the real record-id strings.
    """

    def __init__(self, *, button_returns=None, selectbox_index=0):
        # ``button_returns`` maps a label to a bool (or a list of bools consumed
        # in call order) so rerenders can be scripted deterministically.
        self._button_returns = dict(button_returns or {})
        self._button_consumed = {}
        self._selectbox_index = selectbox_index
        self.calls = []

    # ---- widgets -------------------------------------------------------
    def button(self, label, disabled=False, key=None, **kwargs):
        self.calls.append(("button", label, {"disabled": disabled, "key": key, **kwargs}))
        scripted = self._button_returns.get(label, False)
        if isinstance(scripted, list):
            position = self._button_consumed.get(label, 0)
            self._button_consumed[label] = position + 1
            scripted = scripted[position] if position < len(scripted) else False
        # A disabled button cannot be clicked even if scripted True.
        return bool(scripted) and not disabled

    def selectbox(self, label, options, index=0, format_func=None, key=None, **kwargs):
        captured = {
            "options": list(options),
            "index": index,
            "format_func": format_func,
            "key": key,
            **kwargs,
        }
        self.calls.append(("selectbox", label, captured))
        options = list(options)
        return options[self._selectbox_index] if options else None

    def download_button(self, label, data, file_name, mime, key=None, **kwargs):
        captured = {
            "data": data,
            "file_name": file_name,
            "mime": mime,
            "key": key,
            **kwargs,
        }
        self.calls.append(("download_button", label, captured))
        return False

    # ---- display helpers ----------------------------------------------
    def title(self, *args, **kwargs):
        self.calls.append(("title", args, kwargs))

    def header(self, *args, **kwargs):
        self.calls.append(("header", args, kwargs))

    def subheader(self, *args, **kwargs):
        self.calls.append(("subheader", args, kwargs))

    def caption(self, *args, **kwargs):
        self.calls.append(("caption", args, kwargs))

    def info(self, *args, **kwargs):
        self.calls.append(("info", args, kwargs))

    def warning(self, *args, **kwargs):
        self.calls.append(("warning", args, kwargs))

    def error(self, *args, **kwargs):
        self.calls.append(("error", args, kwargs))

    def success(self, *args, **kwargs):
        self.calls.append(("success", args, kwargs))

    def write(self, *args, **kwargs):
        self.calls.append(("write", args, kwargs))

    def markdown(self, *args, **kwargs):
        self.calls.append(("markdown", args, kwargs))

    def json(self, *args, **kwargs):
        self.calls.append(("json", args, kwargs))

    def table(self, *args, **kwargs):
        self.calls.append(("table", args, kwargs))

    def dataframe(self, *args, **kwargs):
        self.calls.append(("dataframe", args, kwargs))

    # ---- observation helpers ------------------------------------------
    def calls_named(self, name):
        return [captured for captured in self.calls if captured[0] == name]

    def display_texts(self):
        """Recursive string leaves/keys of every display call.

        Covers ``json``/``table``/``dataframe`` (which receive structured
        objects) in addition to the plain-text helpers, and walks nested
        dict/list/tuple/set so structured display cannot smuggle a sentinel past
        a raw-substring check. Returns a newline-joined string of every leaf.
        """
        display_names = {
            "title", "header", "subheader", "caption", "info", "warning",
            "error", "success", "write", "markdown", "json", "table",
            "dataframe",
        }
        parts = []
        for name, args, kwargs in self.calls:
            if name in display_names:
                parts.extend(args)
                parts.append(kwargs)
        return "\n".join(_collect_strings(parts))

    def download_strings(self):
        """Recursive string leaves/keys of every captured download argument."""
        payloads = [
            payload
            for (name, _label, payload) in self.calls
            if name == "download_button"
        ]
        return "\n".join(_collect_strings(payloads))

    def captured_strings(self):
        """Every display AND download string leaf/key, for leak assertions."""
        return self.display_texts() + "\n" + self.download_strings()


def _save_calls(store):
    """Wrap the REAL store.save to count writes without faking success.

    Returns ``(counter, records)`` where ``counter`` is a one-element list and
    ``records`` accumulates each record passed to the genuine ``save``. The
    original method still runs, so failures propagate exactly as in production.
    """
    original_save = store.save
    counter = [0]
    records = []

    def counting_save(record_model):
        counter[0] += 1
        records.append(record_model)
        return original_save(record_model)

    store.save = counting_save
    return counter, records


SAVE_LABEL = "保存研究记录"


def _render(view, ui, store, **kwargs):
    view.render_reports_panel(ui, store=store, **kwargs)


def test_page_module_missing_view_fails_as_availability_assertion():
    """Resolving the view is an ordinary assertion: RED when missing, never skip."""
    assert importlib.util.find_spec("papertrace.reports") is not None
    module = _view_module()
    assert callable(module.render_reports_panel)


def test_page_initial_render_does_not_save(tmp_path):
    view = _view_module()
    api = reports()
    store = api.HistoryStore(tmp_path)
    counter, _ = _save_calls(store)
    ui = FakeUI()

    _render(view, ui, store, pending_record=record())

    assert counter[0] == 0
    assert list(tmp_path.iterdir()) == []
    # The save button is rendered but not clicked by the first render.
    assert ui.calls_named("button"), "expected a save button on the panel"


def test_page_click_save_persists_and_reopens_original(tmp_path):
    view = _view_module()
    api = reports()
    original = record()
    store = api.HistoryStore(tmp_path)
    counter, _ = _save_calls(store)
    ui = FakeUI(button_returns={SAVE_LABEL: True})

    _render(view, ui, store, pending_record=original)

    assert counter[0] == 1
    reopened = api.HistoryStore(tmp_path).load(original.record_id)
    assert reopened.model_dump(mode="json") == original.model_dump(mode="json")
    assert store.load(original.record_id).model_dump_json() == original.model_dump_json()


def test_page_rerender_without_click_does_not_save_again(tmp_path):
    view = _view_module()
    api = reports()
    original = record()
    store = api.HistoryStore(tmp_path)
    counter, _ = _save_calls(store)

    # First render clicked -> one save; second render not clicked -> zero extra.
    ui = FakeUI(button_returns={SAVE_LABEL: [True, False]})
    _render(view, ui, store, pending_record=original)
    assert counter[0] == 1

    ui_second = FakeUI(button_returns={SAVE_LABEL: False})
    _render(view, ui_second, store, pending_record=original)
    assert counter[0] == 1


def test_page_duplicate_click_same_uuid_does_not_overwrite(tmp_path):
    view = _view_module()
    api = reports()
    original = record()
    store = api.HistoryStore(tmp_path)
    counter, _ = _save_calls(store)

    ui = FakeUI(button_returns={SAVE_LABEL: [True, True]})
    _render(view, ui, store, pending_record=original)
    first_bytes = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*") if path.is_file()
    }
    assert counter[0] == 1

    # Second click with the same record id must not overwrite or duplicate.
    _render(view, ui, store, pending_record=original)
    second_bytes = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*") if path.is_file()
    }
    assert second_bytes == first_bytes
    ids = [item.record_id for item in api.HistoryStore(tmp_path).list_records()]
    assert ids == [original.record_id]


@pytest.mark.parametrize(
    "kwargs",
    [
        pytest.param({"pending_record": None}, id="missing-pending"),
        pytest.param({"pending_record": None, "input_error": "REVIEW_UNAVAILABLE"}, id="review-unavailable"),
        pytest.param(
            {
                "pending_record": None,
                "input_error": "REVIEW_UNAVAILABLE "
                + SYNTHETIC_ABSOLUTE_PATHS[0]
                + " "
                + SYNTHETIC_ABSOLUTE_PATHS[2],
            },
            id="malicious-error-with-synthetic-paths",
        ),
    ],
)
def test_page_unavailable_or_input_error_cannot_write(tmp_path, kwargs):
    view = _view_module()
    api = reports()
    store = api.HistoryStore(tmp_path)
    counter, _ = _save_calls(store)
    ui = FakeUI(button_returns={SAVE_LABEL: True})

    _render(view, ui, store, **kwargs)

    assert counter[0] == 0
    assert list(tmp_path.iterdir()) == []
    rendered = ui.display_texts()
    for path in SYNTHETIC_ABSOLUTE_PATHS:
        assert path not in rendered, "page must not leak a synthetic private path"
        assert basename(path) not in rendered, "page must not leak a path basename"


# ---------------------------------------------------------------------------
# PAGE WIRING PROPOSAL (batch 2): outcome labels, history selection/download,
# superseded warning, storage-failure safety, writer-failure safety, and a
# structural (stdlib AST) guard that the view never imports Streamlit. All
# synthetic. These are appended proposals; the view module must receive an
# independent precise-head approval before any source implementation. No
# preview module is exercised here.
# ---------------------------------------------------------------------------

PUBLICATION_BLOCKED_REASON = "PUBLICATION_COMMIT_UNAVAILABLE"
BLOCKED_LABEL = "发布受阻"
E_UI_PRIVATE = "E_UI_PRIVATE_SENTINEL_DO_NOT_DISPLAY_20261123"
E_UI_PRIVATE_REASON = "E_UI_PRIVATE review reason 20261123"

HISTORY_SECOND_ID = "7c1d2e3f-4a5b-4c6d-8e90-1a2b3c4d5e6f"
HISTORY_SECOND_QUESTION = "SYNTHETIC second question with a distinct body."
HISTORY_SECOND_BODY = "SYNTHETIC second answer body that differs from the first."


def _dir_bytes(root):
    return {
        path.relative_to(root): path.read_bytes()
        for path in root.rglob("*") if path.is_file()
    }


def _assert_generic_failure(ui, *, needles):
    """Failure surface must be generic: a warning/error shown, no success.

    ``needles`` (private-path/basename sentinels) must not appear in any
    captured display or download string.
    """
    captured = ui.captured_strings()
    for needle in needles:
        assert needle not in captured, f"page leaked {needle!r}"
    assert ui.calls_named("warning") or ui.calls_named("error"), (
        "storage failure must surface a generic warning/error"
    )
    assert not ui.calls_named("success"), "storage failure must not claim success"


def _release_status_record(api, status="blocked", *, reason_codes=None):
    """Build a validated record whose release carries ``status``.

    ``released`` uses the canonical valid shape: every check passed and empty
    reason codes. ``blocked``/others keep the fixture's blocked constraints.
    """
    from papertrace.contracts import ReleaseDecision

    data = payload()
    if status == "released":
        data["release"]["status"] = "released"
        data["release"]["reason_codes"] = []
        for name in ("snapshot", "review", "evidence", "citation", "answer"):
            data["release"][f"{name}_check_passed"] = True
    else:
        data["release"]["status"] = status
        if reason_codes is not None:
            data["release"]["reason_codes"] = list(reason_codes)
    # Sanity: the shared contract accepts this release shape.
    ReleaseDecision.model_validate(data["release"])
    return api.ResearchRecord.model_validate(data)


# ---- outcome labels -------------------------------------------------------

@pytest.mark.parametrize("reason_codes", [None, ["PUBLICATION_COMMIT_UNAVAILABLE"], ["PUBLICATION_COMMIT_UNAVAILABLE", "NO_APPROVED_EVIDENCE"]])
def test_page_blocked_shows_publication_blocked_label_and_reason(tmp_path, reason_codes):
    view = _view_module()
    api = reports()
    store = api.HistoryStore(tmp_path)
    counter, _ = _save_calls(store)
    blocked = _release_status_record(api, "blocked", reason_codes=reason_codes)
    ui = FakeUI()

    _render(view, ui, store, pending_record=blocked)

    captured = ui.captured_strings()
    assert BLOCKED_LABEL in captured, "blocked records must show 发布受阻"
    if reason_codes and PUBLICATION_BLOCKED_REASON in reason_codes:
        assert PUBLICATION_BLOCKED_REASON in captured, "page must give an understandable reason"
    # Rendering never writes.
    assert counter[0] == 0
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("status", ["abstained", "failed"])
@pytest.mark.parametrize("corpus", ["empty", "populated"])
def test_page_abstained_failed_blocked_click_persists_unchanged(tmp_path, status, corpus):
    view = _view_module()
    api = reports()
    store = api.HistoryStore(tmp_path)
    counter, _ = _save_calls(store)
    original = api.ResearchRecord.model_validate(
        empty_record_payload(status=status, corpus=corpus)
    )
    assert original.review_revision == 0
    assert original.release.status == "blocked"
    ui = FakeUI(button_returns={SAVE_LABEL: True})

    _render(view, ui, store, pending_record=original)

    # An explicit click saves exactly once through the real store.
    assert counter[0] == 1
    reopened = api.HistoryStore(tmp_path).load(original.record_id)
    assert reopened.draft.status == status
    assert reopened.release.status == "blocked"  # never promoted to released
    assert reopened.review_revision == 0
    assert reopened.model_dump(mode="json") == original.model_dump(mode="json")
    assert [item.record_id for item in api.HistoryStore(tmp_path).list_records()] == [
        original.record_id
    ]


def test_page_released_keeps_declared_status(tmp_path):
    view = _view_module()
    api = reports()
    store = api.HistoryStore(tmp_path)
    counter, _ = _save_calls(store)
    released = _release_status_record(api, "released")
    assert released.release.status == "released"
    ui = FakeUI()

    _render(view, ui, store, pending_record=released)

    captured = ui.captured_strings()
    assert "released" in captured
    # The page does not make publication decisions or write on render.
    assert counter[0] == 0
    assert list(tmp_path.iterdir()) == []


# ---- history selection + download binding ---------------------------------

def _two_history_records(api):
    first = record()
    data = payload()
    data["record_id"] = HISTORY_SECOND_ID
    # ``question`` is a plain string in the fixture, not a mapping.
    data["question"] = HISTORY_SECOND_QUESTION
    data["draft"]["body"] = HISTORY_SECOND_BODY
    second = api.ResearchRecord.model_validate(data)
    return first, second


@pytest.mark.parametrize("select_index", [0, 1])
def test_page_history_selection_and_download_bind_same_id(tmp_path, select_index):
    view = _view_module()
    api = reports()
    first, second = _two_history_records(api)
    by_id = {first.record_id: first, second.record_id: second}
    store = api.HistoryStore(tmp_path)
    store.save(first)
    store.save(second)
    before = _dir_bytes(tmp_path)

    ui = FakeUI(selectbox_index=select_index)
    _render(view, ui, store)

    # The selectbox offered both real record IDs; the selected ID is the one
    # the UI double returned at ``select_index`` (no assumed ordering).
    select_calls = ui.calls_named("selectbox")
    assert select_calls, "history list must render a selectbox"
    offered = list(select_calls[0][2]["options"])
    assert set(offered) == {first.record_id, second.record_id}
    selected_id = offered[select_index]
    expected = by_id[selected_id]
    other = second if expected is first else first

    downloads = ui.calls_named("download_button")
    json_download = next(
        (call for call in downloads
         if "json" in str(call[2]["mime"]).lower()
         or str(call[2]["file_name"]).lower().endswith(".json")),
        None,
    )
    md_download = next(
        (call for call in downloads
         if "markdown" in str(call[2]["mime"]).lower()
         or str(call[2]["file_name"]).lower().endswith(".md")),
        None,
    )
    assert json_download is not None, "expected a JSON download bound to the selection"
    assert md_download is not None, "expected a Markdown download bound to the selection"

    # The captured download payload is the selection's real export, exactly.
    captured_json = json_download[2]["data"]
    captured_md = md_download[2]["data"]
    expected_json_text = api.export_json(expected)
    expected_md_text = api.export_markdown(expected)
    if isinstance(captured_json, bytes | bytearray):
        captured_json = captured_json.decode("utf-8")
    if isinstance(captured_md, bytes | bytearray):
        captured_md = captured_md.decode("utf-8")
    assert json.loads(captured_json) == json.loads(expected_json_text)
    assert captured_md == expected_md_text
    parsed = json.loads(captured_json)
    assert parsed["release"]["status"] == expected.release.status

    # Default export hides the excerpt; the page must not show it either.
    excerpt = expected.evidence[0].excerpt if expected.evidence else None
    if excerpt:
        assert excerpt not in captured_md
        assert excerpt not in ui.captured_strings()
    # The unselected record's distinct body must not leak into the shown page.
    assert other.draft.body not in ui.captured_strings()
    assert _dir_bytes(tmp_path) == before, "selection and downloads must not write"


# ---- superseded warning ----------------------------------------------------

def test_page_superseded_warning_without_rewrite(tmp_path):
    view = _view_module()
    api = reports()
    original = record()
    store = api.HistoryStore(tmp_path)
    store.save(original)
    before = _dir_bytes(tmp_path)
    ui = FakeUI()

    _render(view, ui, store, current_snapshot_id="snap-" + "0" * 64)

    assert ui.calls_named("warning"), "superseded history must warn"
    assert "superseded" in ui.captured_strings().lower()
    assert _dir_bytes(tmp_path) == before, "superseded warning must not rewrite stored bytes"


# ---- storage load/list failure (narrow monkeypatch boundary) ---------------

_STORAGE_PRIVATE = "C:\\Users\\SYNTHETIC\\load-failure\\paper.pdf"


@pytest.mark.parametrize("method", ["list_records", "load"])
def test_page_storage_failure_shows_generic_safe_error(tmp_path, monkeypatch, method):
    view = _view_module()
    api = reports()
    first, second = _two_history_records(api)
    store = api.HistoryStore(tmp_path)
    store.save(first)
    store.save(second)
    ui = FakeUI()

    # Preserve a real, readable list before injecting a selected-record failure.
    # Otherwise list_records internally calls the patched load, skips both
    # entries, and never reaches the selected-record loading boundary.
    listed = store.list_records()
    if method == "load":
        monkeypatch.setattr(store, "list_records", lambda: listed)

    def failing(*_args, **_kwargs):
        raise api.InvalidRecord(f"SYNTHETIC read failure at {_STORAGE_PRIVATE}")

    monkeypatch.setattr(store, method, failing)

    _render(view, ui, store, pending_record=None)

    _assert_generic_failure(ui, needles=(_STORAGE_PRIVATE, basename(_STORAGE_PRIVATE)))
    # Must not fake an empty-success list or fall back to showing another record.
    captured = ui.captured_strings()
    assert first.draft.body not in captured
    assert second.draft.body not in captured
    assert first.record_id not in captured
    assert second.record_id not in captured


# ---- writer failure (real atomic_writer raising OSError) -------------------

def test_page_writer_failure_reports_no_success_and_no_files(tmp_path):
    view = _view_module()
    api = reports()
    original = record()
    reached = []

    def disk_failure(*_args, **_kwargs):
        reached.append(True)
        raise OSError(f"SYNTHETIC disk full at {_STORAGE_PRIVATE}")

    store = api.HistoryStore(tmp_path, atomic_writer=disk_failure)
    ui = FakeUI(button_returns={SAVE_LABEL: True})

    _render(view, ui, store, pending_record=original)

    # The writer was actually reached (try-save happened) but must not be faked.
    assert reached == [True]
    assert not (tmp_path / f"{original.record_id}.json").exists()
    assert list(tmp_path.iterdir()) == []
    _assert_generic_failure(ui, needles=(_STORAGE_PRIVATE, basename(_STORAGE_PRIVATE)))


# ---- poison metadata rejection without secret leak ------------------------

def test_page_poison_metadata_save_rejected_without_secret(tmp_path):
    view = _view_module()
    api = reports()
    poisoned = _second_record(api)
    poisoned.run_metadata["api_key"] = SENTINEL_A
    store = api.HistoryStore(tmp_path)
    counter, _ = _save_calls(store)
    ui = FakeUI(button_returns={SAVE_LABEL: True})

    _render(view, ui, store, pending_record=poisoned)

    # The page may reject during pre-validation (0 writes) or attempt one save
    # that the store then rejects (1 write); never more.
    assert counter[0] <= 1
    assert not (tmp_path / f"{poisoned.record_id}.json").exists()
    assert list(tmp_path.iterdir()) == []
    captured = ui.captured_strings()
    assert SENTINEL_A not in captured, "page must not leak the secret"
    assert not ui.calls_named("success"), "rejected save must not claim success"
    assert ui.calls_named("warning") or ui.calls_named("error")


# ---- input_error blocks save even with a VALID pending record --------------

@pytest.mark.parametrize(
    "input_error",
    [
        "REVIEW_UNAVAILABLE",
        "INPUT_UNAVAILABLE",
        "REVIEW_UNAVAILABLE " + E_UI_PRIVATE,
    ],
)
def test_page_input_error_with_valid_pending_prevents_save(tmp_path, input_error):
    view = _view_module()
    api = reports()
    valid = record()
    store = api.HistoryStore(tmp_path)
    counter, _ = _save_calls(store)
    ui = FakeUI(button_returns={SAVE_LABEL: True})

    _render(view, ui, store, pending_record=valid, input_error=input_error)

    assert counter[0] == 0, "input_error must block the save even with a valid record"
    assert list(tmp_path.iterdir()) == []
    assert E_UI_PRIVATE not in ui.captured_strings()


# ---- PRIVATE path leak test (draft body + review reason) ------------------

# Unique path segments; ordinary text like a bare token is NOT private and must
# not be redacted, so we prove non-display of these absolute-path sentinels.
E_UI_BODY_PATH = "/Users/E_UI_PRIVATE_SENTINEL_DO_NOT_DISPLAY_20261123/body.txt"
E_UI_REASON_PATH = "C:\\E_UI_PRIVATE_REASON\\review.txt"


def _path_leak_record(api):
    """Build a validated record whose body and review reason carry unique paths."""

    def mutate(decision, draft, **parts):
        draft["body"] = f"SYNTHETIC answer {E_UI_BODY_PATH}"
        decision["reason"] = f"SYNTHETIC review {E_UI_REASON_PATH}"

    return identity_covered_record(api, mutate)


def test_page_private_paths_in_body_and_reason_are_not_displayed(tmp_path):
    view = _view_module()
    api = reports()
    original = _path_leak_record(api)
    # The paths are genuinely present in the internal model.
    assert E_UI_BODY_PATH in original.draft.body
    assert E_UI_REASON_PATH in original.review_events[0].decision.reason
    store = api.HistoryStore(tmp_path)
    store.save(original)

    ui = FakeUI()
    _render(view, ui, store, current_snapshot_id=original.snapshot.snapshot_id)

    captured = ui.captured_strings()
    for needle in (E_UI_BODY_PATH, E_UI_REASON_PATH):
        assert needle not in captured, f"private path {needle!r} leaked into UI"
        assert basename(needle) not in captured, "path basename leaked into UI"
    assert "E_UI_PRIVATE_SENTINEL_DO_NOT_DISPLAY_20261123" not in captured
    assert "E_UI_PRIVATE_REASON" not in captured


# ---- structural guard: no top-level Streamlit/provider imports -----------

def test_view_module_has_no_streamlit_or_provider_imports():
    """Parse the eventual view source with stdlib ``ast`` (no importing it).

    The page component must take an injected ``ui`` and must not import
    Streamlit or a provider/model SDK at module top level. This stays valid with
    the view absent: we use the lazy resolver so collection reports availability
    as an ordinary assertion instead of an import error.
    """
    import ast
    import importlib.util

    spec = importlib.util.find_spec("papertrace.reports.view")
    assert spec is not None, (
        "PAGE WIRING: papertrace.reports.view missing; availability RED until "
        "the page-wiring tests receive an independent precise-head approval"
    )

    source = Path(spec.origin).read_text("utf-8")
    tree = ast.parse(source, filename=str(spec.origin))
    forbidden_roots = {"streamlit", "st"}
    forbidden_chars = ("provider", "openai", "anthropic", "paperqa", "litellm", "google")
    for node in tree.body:  # top-level statements only
        roots = []
        if isinstance(node, ast.Import):
            roots = [alias.name.split(".")[0] for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots = [node.module.split(".")[0]]
        for root in roots:
            assert root not in forbidden_roots, f"view must not import {root!r}"
            lowered = root.lower()
            assert not any(token in lowered for token in forbidden_chars), (
                f"view must not import provider SDK {root!r}"
            )


# ---------------------------------------------------------------------------
# PAGE WIRING PROPOSAL (batch 2, view-independent): fixture sanity.
# These build every page fixture through the REAL contracts/validators so a
# defect in the page test data fails NOW, independent of whether the view module
# exists. Reuses the shared helpers; no view import.
# ---------------------------------------------------------------------------


def test_page_fixtures_validate_independently():
    api = reports()

    # Released: valid canonical shape, status retained, no promotion.
    released = _release_status_record(api, "released")
    assert released.release.status == "released"
    for name in ("snapshot", "review", "evidence", "citation", "answer"):
        assert getattr(released.release, f"{name}_check_passed") is True
    assert released.release.reason_codes == ()

    # Blocked with PUBLICATION_COMMIT_UNAVAILABLE reason.
    blocked = _release_status_record(
        api, "blocked", reason_codes=[PUBLICATION_BLOCKED_REASON]
    )
    assert blocked.release.status == "blocked"
    assert PUBLICATION_BLOCKED_REASON in blocked.release.reason_codes

    # Two history records: distinct ids, distinct questions/bodies.
    first, second = _two_history_records(api)
    assert first.record_id != second.record_id
    assert first.question != second.question
    assert first.draft.body != second.draft.body
    assert second.question == HISTORY_SECOND_QUESTION
    assert second.draft.body == HISTORY_SECOND_BODY

    # Empty-corpus / empty-evidence abstained + failed at revision 0, blocked.
    for status in ("abstained", "failed"):
        for corpus in ("empty", "populated"):
            empty = api.ResearchRecord.model_validate(
                empty_record_payload(status=status, corpus=corpus)
            )
            assert empty.draft.status == status
            assert empty.release.status == "blocked"
            assert empty.review_revision == 0
            assert empty.release.review_revision == 0

    # Path-leak record carries the unique body/reason paths internally.
    leak = _path_leak_record(api)
    assert E_UI_BODY_PATH in leak.draft.body
    assert E_UI_REASON_PATH in leak.review_events[0].decision.reason
