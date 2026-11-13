"""Synthetic contract tests; no model call or human approval is represented.

Architecture: ADR-001. Traceability: QA-01 shared contracts; INV-01 empty-evidence
refusal, INV-02 immutable/versioned provenance, INV-03 human review authority,
INV-04 declared evidence scope/release record, INV-05 immutable history envelope,
SEC-01 portable metadata. These tests do not implement runtime or persistent gates.
"""

from importlib import import_module
from importlib.util import find_spec

import pytest
from pydantic import ValidationError


def contract(name):
    """Expose a missing contract as an intentional assertion, not import error."""
    package = find_spec("papertrace")
    assert package is not None, "QA-01: papertrace package is missing"
    spec = find_spec("papertrace.contracts")
    assert spec is not None, "QA-01: shared contracts module is missing"
    model = getattr(import_module("papertrace.contracts"), name, None)
    assert model is not None, f"QA-01: {name} public contract is missing"
    return model


def test_document_version_json_round_trip():
    """QA-01 / INV-02: logical document identity is not content identity."""
    model = contract("DocumentVersion")
    document = model(
        schema_version=1,
        document_id="doc-synthetic-a",
        version_sha256="a" * 64,
        title="合成文献 α（非真实论文）",
        source_name="synthetic-α.pdf",
        status="ready",
    )
    assert model.model_validate_json(document.model_dump_json()) == document
    assert document.document_id != document.version_sha256
    assert "合成文献" in document.model_dump_json()


def document_payload(**changes):
    """Handwritten synthetic metadata, unrelated to any actual paper."""
    payload = {
        "schema_version": 1,
        "document_id": "doc-synthetic-a",
        "version_sha256": "a" * 64,
        "title": "合成文献 α（非真实论文）",
        "source_name": "synthetic-α.pdf",
        "status": "ready",
    }
    return payload | changes


def test_shared_envelope_is_frozen_and_forbids_extra():
    """QA-01 / SEC-01: no mutable state or shadow authority fields."""
    model = contract("DocumentVersion")
    with pytest.raises(ValidationError, match="extra_forbidden"):
        model(**document_payload(accepted=True))
    document = model(**document_payload())
    with pytest.raises(ValidationError, match="frozen_instance"):
        document.title = "changed"


@pytest.mark.parametrize("version", [None, 0, 2, "1", True])
def test_schema_version_requires_explicit_integer_one(version):
    """QA-01 / INV-02: silent/coerced protocol upgrades are forbidden."""
    payload = document_payload(schema_version=version)
    if version is None:
        payload.pop("schema_version")
    with pytest.raises(ValidationError):
        contract("DocumentVersion")(**payload)


@pytest.mark.parametrize(
    "field,value",
    [
        ("version_sha256", "a" * 63),
        ("version_sha256", "G" * 64),
        ("version_sha256", "A" * 64),
        ("document_id", "a" * 64),
        ("document_id", "doc-../secret"),
        ("document_id", "doc-"),
        ("source_name", "../synthetic.pdf"),
        ("source_name", "/synthetic.pdf"),
        ("source_name", "dir\\synthetic.pdf"),
        ("source_name", ".."),
        ("source_name", "bad\x00.pdf"),
        ("title", "  "),
        ("status", "processing"),
    ],
)
def test_document_identity_and_safe_ready_metadata(field, value):
    """QA-01 / INV-02, SEC-01: immutable ready versions, never filesystem paths."""
    with pytest.raises(ValidationError):
        contract("DocumentVersion")(**document_payload(**{field: value}))


def test_snapshot_identity_is_canonical_and_round_trips():
    """QA-01 / INV-02: order and capture time cannot change identity."""
    import hashlib
    import json

    model = contract("CorpusSnapshot")
    documents = [
        document_payload(document_id="doc-synthetic-b", version_sha256="b" * 64),
        document_payload(),
    ]
    snapshot = model(schema_version=1, documents=documents, created_at="2026-01-01T08:00:00+08:00")
    canonical = json.dumps(
        {"schema_version": 1, "documents": sorted(documents, key=lambda item: item["document_id"])},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    assert snapshot.snapshot_id == "snap-" + hashlib.sha256(canonical).hexdigest()
    reordered = model(
        schema_version=1, documents=list(reversed(documents)), created_at="2026-02-01T00:00:00Z"
    )
    assert snapshot.snapshot_id == reordered.snapshot_id
    assert [doc.document_id for doc in snapshot.documents] == ["doc-synthetic-a", "doc-synthetic-b"]
    assert isinstance(snapshot.documents, tuple)
    assert snapshot.created_at.isoformat() == "2026-01-01T00:00:00+00:00"
    assert model.model_validate_json(snapshot.model_dump_json()) == snapshot


@pytest.mark.parametrize(
    "changes",
    [
        {"snapshot_id": "snap-" + "0" * 64},
        {"documents": [document_payload(), document_payload()]},
        {"documents": [document_payload(), document_payload(version_sha256="b" * 64)]},
        {"created_at": "2026-01-01T00:00:00"},
        {"documents": [document_payload(status="failed")]},
    ],
)
def test_snapshot_rejects_mismatch_duplicate_versions_and_naive_time(changes):
    """QA-01 / INV-02: supplied identity cannot forge a corpus."""
    payload = {
        "schema_version": 1,
        "documents": [document_payload()],
        "created_at": "2026-01-01T00:00:00Z",
    } | changes
    with pytest.raises(ValidationError):
        contract("CorpusSnapshot")(**payload)


def locator_payload(**changes):
    """Explicit synthetic page coordinates, not a recovered real source."""
    return {
        "schema_version": 1,
        "page_start": 1,
        "page_end": 2,
        "line_start": None,
        "line_end": None,
        "chunk_id": "chunk-synthetic-a",
        "parser_name": "synthetic-parser",
        "parser_version": "1.0",
    } | changes


@pytest.mark.parametrize(
    "changes", [{}, {"page_start": None, "page_end": None, "line_start": 4, "line_end": 7}]
)
def test_source_locator_round_trips_page_or_line_coordinates(changes):
    """QA-01 / INV-02, INV-04: 1-based source coordinates and parser provenance."""
    model = contract("SourceLocator")
    locator = model(**locator_payload(**changes))
    assert model.model_validate_json(locator.model_dump_json()) == locator


@pytest.mark.parametrize(
    "changes",
    [
        {"page_start": None, "page_end": None},
        {"page_start": 0},
        {"page_start": -1},
        {"page_end": 0},
        {"page_start": 3, "page_end": 2},
        {"page_end": None},
        {"line_start": 2, "line_end": 1},
        {"line_end": 2},
        {"line_start": 0, "line_end": 1},
        {"page_start": True},
        {"page_start": "1"},
        {"chunk_id": " "},
        {"parser_version": ""},
    ],
)
def test_source_locator_rejects_missing_or_invalid_ranges(changes):
    """QA-01 / INV-02, INV-04: empty, partial, reverse or nonpositive ranges fail."""
    with pytest.raises(ValidationError):
        contract("SourceLocator")(**locator_payload(**changes))


def evidence_payload(**changes):
    """All evidence is handwritten synthetic data with no review authority."""
    return {
        "schema_version": 1,
        "snapshot_id": "snap-" + "a" * 64,
        "document_id": "doc-synthetic-a",
        "version_sha256": "a" * 64,
        "locator": locator_payload(),
        "excerpt": "合成原文摘录 α；不构成科学结论。",
        "retrieved_at": "2026-01-01T00:00:00Z",
        "advisory_summary": "synthetic 摘要（无授权）",
        "upstream_context_id": "synthetic-upstream-context",
    } | changes


def test_evidence_identity_excludes_advisory_summary_and_upstream_id():
    """QA-01 / INV-03, INV-02, INV-04: only exact source provenance determines ID."""
    import hashlib
    import json

    model = contract("EvidenceRecord")
    payload = evidence_payload()
    evidence = model(**payload)
    identity = {
        key: payload[key]
        for key in (
            "schema_version",
            "snapshot_id",
            "document_id",
            "version_sha256",
            "locator",
            "excerpt",
        )
    }
    expected = (
        "ev-"
        + hashlib.sha256(
            json.dumps(
                identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
            ).encode("utf-8")
        ).hexdigest()
    )
    assert evidence.evidence_id == expected
    advisory_change = model(
        **evidence_payload(
            advisory_summary="另一个 synthetic 摘要",
            upstream_context_id="other",
            retrieved_at="2026-02-01T00:00:00Z",
        )
    )
    assert advisory_change.evidence_id == evidence.evidence_id
    assert not hasattr(evidence, "status")
    assert not hasattr(evidence, "accepted")
    assert model.model_validate_json(evidence.model_dump_json()) == evidence


@pytest.mark.parametrize(
    "changes",
    [
        {"evidence_id": "ev-" + "0" * 64},
        {"evidence_id": "context-123"},
        {"excerpt": "  "},
        {"version_sha256": "not-a-version"},
        {"snapshot_id": "snapshot-1"},
        {"status": "accepted"},
        {"accepted": True},
        {"retrieved_at": "2026-01-01T00:00:00"},
        {"locator": locator_payload(page_start=None, page_end=None)},
    ],
)
def test_evidence_rejects_forged_identity_and_authority(changes):
    """QA-01 / INV-03, INV-02, INV-04: no self-approval or substituted evidence ID."""
    with pytest.raises(ValidationError):
        contract("EvidenceRecord")(**evidence_payload(**changes))


def review_payload(**changes):
    """Synthetic review event only; does not represent anyone's actual approval."""
    return {
        "schema_version": 1,
        "evidence_id": "ev-" + "a" * 64,
        "snapshot_id": "snap-" + "a" * 64,
        "question_id": "q-synthetic-a",
        "status": "accepted",
        "actor_kind": "human",
        "reviewer_ref": "reviewer-A",
        "revision": 1,
        "reason": "synthetic：用于契约测试，不是真实审批。",
        "decided_at": "2026-01-01T08:00:00+08:00",
    } | changes


@pytest.mark.parametrize("status", ["pending", "accepted", "excluded"])
def test_review_decision_round_trips_human_event(status):
    """QA-01 / INV-03: authority is represented only by a review event."""
    model = contract("ReviewDecision")
    review = model(**review_payload(status=status))
    assert review.decided_at.isoformat() == "2026-01-01T00:00:00+00:00"
    assert model.model_validate_json(review.model_dump_json()) == review


@pytest.mark.parametrize(
    "changes",
    [
        {"actor_kind": "model"},
        {"actor_kind": "agent"},
        {"status": "released"},
        {"status": "approved"},
        {"reviewer_ref": ""},
        {"reviewer_ref": "Person Name"},
        {"revision": 0},
        {"revision": True},
        {"revision": "1"},
        {"reason": " "},
        {"decided_at": "2026-01-01T00:00:00"},
        {"evidence_id": "upstream-context-id"},
        {"question_id": ""},
    ],
)
def test_review_rejects_nonhuman_or_unaccountable_decisions(changes):
    """QA-01 / INV-03: models and summaries cannot grant acceptance."""
    with pytest.raises(ValidationError):
        contract("ReviewDecision")(**review_payload(**changes))


def answer_payload(**changes):
    """Synthetic output envelope, never a real model response or release."""
    return {
        "schema_version": 1,
        "answer_id": "ans-synthetic-a",
        "snapshot_id": "snap-" + "a" * 64,
        "question_id": "q-synthetic-a",
        "review_revision": 1,
        "review_digest": "d" * 64,
        "approved_evidence_ids": ["ev-" + "a" * 64, "ev-" + "b" * 64],
        "sent_evidence_ids": ["ev-" + "a" * 64],
        "citation_evidence_ids": ["ev-" + "a" * 64],
        "status": "draft",
        "body": "synthetic：仅用于序列化测试的非科学占位正文。",
        "refusal_reason": None,
        "generated_at": "2026-01-01T00:00:00Z",
    } | changes


def test_answer_draft_round_trip_binds_review_scope():
    """QA-01 / INV-04, INV-02: explicit approved/sent/cited scopes."""
    model = contract("AnswerDraft")
    answer = model(**answer_payload())
    assert model.model_validate_json(answer.model_dump_json()) == answer
    assert isinstance(answer.approved_evidence_ids, tuple)
    assert isinstance(answer.sent_evidence_ids, tuple)
    assert isinstance(answer.citation_evidence_ids, tuple)
    assert (
        set(answer.citation_evidence_ids)
        <= set(answer.sent_evidence_ids)
        <= set(answer.approved_evidence_ids)
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"approved_evidence_ids": ["ev-" + "a" * 64] * 2},
        {"sent_evidence_ids": ["ev-" + "a" * 64] * 2},
        {"citation_evidence_ids": ["ev-" + "a" * 64] * 2},
        {"sent_evidence_ids": ["ev-" + "c" * 64]},
        {"citation_evidence_ids": ["ev-" + "b" * 64]},
        {"citation_evidence_ids": ["ev-" + "c" * 64]},
        {"approved_evidence_ids": []},
        {"review_digest": "bad-ledger-hash"},
        {"review_revision": 0},
        {"status": "released"},
        {"generated_at": "2026-01-01T00:00:00"},
    ],
)
def test_answer_rejects_duplicate_or_noncurrent_scope(changes):
    """QA-01 / INV-04, INV-02: no references outside declared current scope.

    This checks only the envelope, not a real ledger or a remote/current corpus.
    """
    with pytest.raises(ValidationError):
        contract("AnswerDraft")(**answer_payload(**changes))


@pytest.mark.parametrize(
    "changes",
    [
        {"body": ""},
        {"body": " "},
        {"sent_evidence_ids": [], "citation_evidence_ids": []},
        {"approved_evidence_ids": [], "sent_evidence_ids": [], "citation_evidence_ids": []},
        {"refusal_reason": "unexpected refusal on draft"},
        {"status": "abstained", "refusal_reason": "synthetic refusal"},
        {"status": "failed", "body": "", "citation_evidence_ids": [], "refusal_reason": None},
        {"status": "abstained", "body": "", "citation_evidence_ids": [], "refusal_reason": " "},
    ],
)
def test_answer_fail_closed_state_rejects_empty_draft_or_leaked_answer(changes):
    """QA-01 / INV-01: no evidence means no scientific answer/citations."""
    with pytest.raises(ValidationError):
        contract("AnswerDraft")(**answer_payload(**changes))


@pytest.mark.parametrize("status", ["abstained", "failed"])
def test_answer_no_approved_evidence_is_empty_refusal(status):
    """QA-01 / INV-01: honest refusal envelope is serializable."""
    model = contract("AnswerDraft")
    answer = model(
        **answer_payload(
            status=status,
            body="",
            refusal_reason="synthetic：没有获准证据。",
            approved_evidence_ids=[],
            sent_evidence_ids=[],
            citation_evidence_ids=[],
        )
    )
    assert answer.body == "" and answer.citation_evidence_ids == ()
    assert model.model_validate_json(answer.model_dump_json()) == answer


CHECK_FIELDS = (
    "snapshot_check_passed",
    "review_check_passed",
    "evidence_check_passed",
    "citation_check_passed",
    "answer_check_passed",
)


def release_payload(**changes):
    """Synthetic decision only; all booleans are test inputs, not real checks."""
    return {
        "schema_version": 1,
        "answer_id": "ans-synthetic-a",
        "snapshot_id": "snap-" + "a" * 64,
        "question_id": "q-synthetic-a",
        "review_revision": 1,
        "review_digest": "d" * 64,
        "status": "released",
        "reason_codes": [],
        **{field: True for field in CHECK_FIELDS},
        "decided_at": "2026-01-01T00:00:00Z",
    } | changes


@pytest.mark.parametrize(
    "changes",
    [{}, {"status": "blocked", "review_check_passed": False, "reason_codes": ["STALE_REVIEW"]}],
)
def test_release_decision_round_trips_explicit_checks(changes):
    """QA-01 / INV-04: a decision record, not the release engine."""
    model = contract("ReleaseDecision")
    decision = model(**release_payload(**changes))
    assert model.model_validate_json(decision.model_dump_json()) == decision
    assert isinstance(decision.reason_codes, tuple)


@pytest.mark.parametrize(
    "changes",
    [
        *[{field: False} for field in CHECK_FIELDS],
        {"reason_codes": ["STALE_REVIEW"]},
        {"status": "blocked", "reason_codes": []},
        {"status": "blocked", "reason_codes": [" "]},
        {"status": "blocked", "reason_codes": ["STALE_REVIEW"] * 2},
        {"review_check_passed": "true"},
        {"review_check_passed": 1},
        {"review_digest": "invalid"},
        {"status": "approved"},
        {"decided_at": "2026-01-01T00:00:00"},
    ],
)
def test_release_rejects_inappropriate_release_or_false_check_claims(changes):
    """QA-01 / INV-04: every structural claim must pass for released."""
    with pytest.raises(ValidationError):
        contract("ReleaseDecision")(**release_payload(**changes))


MAIN_MODELS = (
    (
        "CorpusSnapshot",
        lambda: {
            "schema_version": 1,
            "documents": [document_payload()],
            "created_at": "2026-01-01T00:00:00Z",
        },
    ),
    ("EvidenceRecord", evidence_payload),
    ("ReviewDecision", review_payload),
    ("AnswerDraft", answer_payload),
    ("ReleaseDecision", release_payload),
)


@pytest.mark.parametrize("name,payload_factory", MAIN_MODELS)
def test_all_main_models_share_closed_frozen_versioned_schema(name, payload_factory):
    """QA-01 / INV-02, SEC-01: inherited guards are regression checked per model."""
    model = contract(name)
    payload = payload_factory()
    valid = model(**payload)
    with pytest.raises(ValidationError, match="frozen_instance"):
        valid.schema_version = 1
    for changes in ({"schema_version": 2}, {"schema_version": True}, {"forged_authority": True}):
        with pytest.raises(ValidationError):
            model(**(payload | changes))
    missing_version = dict(payload)
    missing_version.pop("schema_version")
    with pytest.raises(ValidationError):
        model(**missing_version)
    schema = model.model_json_schema()
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == 1
    assert "schema_version" in schema["required"]
    assert model.model_validate_json(valid.model_dump_json()) == valid


def test_revalidate_untrusted_constructed_model_instances():
    """QA-01 / SEC-01: frozen objects are not proof of validation."""
    document_model = contract("DocumentVersion")
    forged = document_model.model_construct(**document_payload(status="processing"))
    with pytest.raises(ValidationError):
        document_model.model_validate(forged)
    with pytest.raises(ValidationError):
        contract("CorpusSnapshot")(
            schema_version=1,
            documents=(forged,),
            created_at="2026-01-01T00:00:00Z",
        )


@pytest.mark.parametrize("name", ["C:synthetic.pdf", "file:synthetic.pdf"])
def test_document_source_rejects_drive_relative_paths(name):
    """QA-01 / SEC-01: a portable basename cannot be a drive or URI."""
    with pytest.raises(ValidationError):
        contract("DocumentVersion")(**document_payload(source_name=name))


@pytest.mark.parametrize(
    "name,fields",
    [
        ("AnswerDraft", ("approved_evidence_ids", "sent_evidence_ids", "citation_evidence_ids")),
        ("ReleaseDecision", ("reason_codes",)),
    ],
)
def test_json_schema_declares_identity_collection_uniqueness(name, fields):
    """QA-01 / INV-04, INV-02: schema consumers see uniqueness constraints."""
    schema = contract(name).model_json_schema()
    for field in fields:
        assert schema["properties"][field].get("uniqueItems") is True


@pytest.mark.parametrize(
    "name", ["DocumentVersion", "SourceLocator", *(name for name, _ in MAIN_MODELS)]
)
def test_published_json_schemas_match_models(name):
    """QA-01 / INV-02: checked-in schema documents cannot drift silently."""
    import json
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "docs" / "contracts" / f"{name}.schema.json"
    assert path.is_file(), f"missing published schema: {name}"
    assert json.loads(path.read_text(encoding="utf-8")) == contract(name).model_json_schema()


@pytest.mark.parametrize(
    "name", ["DocumentVersion", "SourceLocator", *(name for name, _ in MAIN_MODELS)]
)
def test_handwritten_synthetic_fixtures_round_trip(name):
    """QA-01 / INV-02: fixtures label provenance instead of fabricating AI."""
    import json
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "fixtures" / "contracts" / f"{name}.json"
    assert path.is_file(), f"missing handwritten synthetic fixture: {name}"
    wrapper = json.loads(path.read_text(encoding="utf-8"))
    assert wrapper["synthetic"] is True
    assert (
        wrapper["provenance"]
        == "handwritten; not a model response, human approval, or runtime release"
    )
    assert wrapper["contract"] == name
    model = contract(name)
    record = model.model_validate(wrapper["data"])
    assert model.model_validate_json(record.model_dump_json()) == record


def test_synthetic_fixture_source_bytes_and_references_are_consistent():
    """QA-01 / INV-02, INV-04: integrity of examples only, not a runtime verifier."""
    import hashlib
    import json
    from pathlib import Path

    directory = Path(__file__).resolve().parents[1] / "fixtures" / "contracts"
    records = {
        name: json.loads((directory / f"{name}.json").read_text(encoding="utf-8"))["data"]
        for name, _ in MAIN_MODELS
    }
    snapshot, evidence, review, answer, release = (records[name] for name, _ in MAIN_MODELS)
    document = snapshot["documents"][0]
    source = (directory / document["source_name"]).read_bytes()
    assert document["version_sha256"] == hashlib.sha256(source).hexdigest()
    assert evidence["excerpt"] == source.decode("utf-8").splitlines()[0]
    assert {
        evidence["snapshot_id"],
        review["snapshot_id"],
        answer["snapshot_id"],
        release["snapshot_id"],
    } == {snapshot["snapshot_id"]}
    assert document["document_id"] == evidence["document_id"]
    assert document["version_sha256"] == evidence["version_sha256"]
    assert review["evidence_id"] == evidence["evidence_id"]
    assert answer["citation_evidence_ids"] == [evidence["evidence_id"]]
    assert answer["review_digest"] == release["review_digest"]
    assert release["status"] == "blocked"


@pytest.mark.parametrize(
    "name", ["DocumentVersion", "SourceLocator", *(name for name, _ in MAIN_MODELS)]
)
def test_json_schema_is_valid_and_accepts_synthetic_record(name):
    """QA-01 / INV-02: real JSON Schema validation, in addition to model validators."""
    import json
    from pathlib import Path

    from jsonschema import Draft202012Validator

    model = contract(name)
    schema = model.model_json_schema()
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)
    path = Path(__file__).resolve().parents[1] / "fixtures" / "contracts" / f"{name}.json"
    data = json.loads(path.read_text(encoding="utf-8"))["data"]
    validator.validate(data)
    assert not validator.is_valid(data | {"unknown_field": True})
    assert not validator.is_valid(data | {"schema_version": 2})


@pytest.mark.parametrize("status", ["abstained", "failed"])
def test_refusal_cannot_keep_a_body_when_all_evidence_is_empty(status):
    """QA-01 / INV-01: a refusal is not a channel for an unapproved answer."""
    with pytest.raises(ValidationError, match="empty body"):
        contract("AnswerDraft")(
            **answer_payload(
                status=status,
                body="synthetic：不可作为科学回答输出。",
                refusal_reason="synthetic refusal",
                approved_evidence_ids=[],
                sent_evidence_ids=[],
                citation_evidence_ids=[],
            )
        )


@pytest.mark.parametrize("field", CHECK_FIELDS)
def test_release_check_results_have_no_implicit_defaults(field):
    """QA-01 / INV-04: no omitted check silently becomes a successful check."""
    payload = release_payload()
    payload.pop(field)
    with pytest.raises(ValidationError, match="Field required"):
        contract("ReleaseDecision")(**payload)


@pytest.mark.parametrize(
    "changes",
    [
        {"snapshot_id": "snap-" + "b" * 64},
        {"document_id": "doc-synthetic-b"},
        {"version_sha256": "b" * 64},
        {"locator": locator_payload(page_end=3)},
        {"excerpt": "不同的 synthetic 摘录"},
    ],
)
def test_old_evidence_hash_cannot_authorize_changed_source(changes):
    """QA-01 / INV-02, INV-04: a stale ID cannot survive provenance changes."""
    model = contract("EvidenceRecord")
    original = model(**evidence_payload())
    changed = model(**evidence_payload(**changes))
    assert original.evidence_id != changed.evidence_id
    with pytest.raises(ValidationError, match="evidence_id"):
        model(**evidence_payload(**(changes | {"evidence_id": original.evidence_id})))
