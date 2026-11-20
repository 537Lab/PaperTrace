"""Module E test proposal. FR-E-01/02, INV-02/04/05/08, SEC-01.

Synthetic only. Proposed public API awaiting independent test review.
Missing implementation must fail explicitly. No source implementation is supplied.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import hashlib
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
    assert original.evidence[0].excerpt in api.export_json(
        original, include_excerpts=True,
    )


def test_write_failure_does_not_damage_previous_record(tmp_path, monkeypatch):
    api = reports()
    original = record()
    store = api.HistoryStore(tmp_path)
    store.save(original)
    before = store.load(original.record_id).model_dump_json()
    data = payload()
    data["record_id"] = "d3a03bf6-88af-4acb-a368-c1a02592192d"
    second = api.ResearchRecord.model_validate(data)

    def disk_failure(*args, **kwargs):
        raise OSError("SYNTHETIC disk full")

    monkeypatch.setattr("os.write", disk_failure)
    with pytest.raises(OSError):
        store.save(second)
    assert store.load(original.record_id).model_dump_json() == before
    assert second.record_id not in [item.record_id for item in store.list_records()]
