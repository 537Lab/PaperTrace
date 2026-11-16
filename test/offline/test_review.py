"""Synthetic offline tests for module C: append-only review ledger + read-only comparison.

Traceability: FR-C-01/02; INV-02/03/04/05 (C-side support only); INV-06 (service
boundary only); QA-01; SEC-01; COST-01.

Every case uses ``tmp_path`` and the handwritten fixtures in
``test/fixtures/review/``. No model, network, credential, real paper, or real human
approval is represented. Before ``src/papertrace/review/`` exists these tests are
expected to be RED; they must not be made green by editing shared contracts or src.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from importlib import import_module
from importlib.util import find_spec
from pathlib import Path

import pytest
from pydantic import ValidationError

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "review"
QUESTION = "q-synthetic-a"
OTHER_QUESTION = "q-synthetic-b"
REVIEWER = "reviewer-SYNTHETIC"
REASON = "synthetic：测试用人工命令，不代表真实审批。"
RESET_REASON = "synthetic：重置理由，不代表真实审批。"
_MISSING = object()


# --------------------------------------------------------------------------- #
# Lazy public-port access: a missing module is an assertion, not a hidden skip.
# --------------------------------------------------------------------------- #
def module(name):
    spec = find_spec(name)
    assert spec is not None, f"FR-C-01: {name} is missing (expected RED before implementation)"
    return import_module(name)


def contracts():
    return module("papertrace.contracts")


def review_symbol(name):
    package = module("papertrace.review")
    value = getattr(package, name, None)
    if value is None:
        for submodule in ("service", "view"):
            if find_spec(f"papertrace.review.{submodule}") is not None:
                value = getattr(import_module(f"papertrace.review.{submodule}"), name, None)
                if value is not None:
                    break
    assert value is not None, f"FR-C-01: papertrace.review.{name} is not a public port"
    return value


# --------------------------------------------------------------------------- #
# Handwritten synthetic fixtures -> real shared contracts.
# --------------------------------------------------------------------------- #
def load_wrapper(filename):
    wrapper = json.loads((FIXTURE_DIR / filename).read_text(encoding="utf-8"))
    assert wrapper["synthetic"] is True
    assert wrapper["provenance"].startswith("handwritten")
    return wrapper


def snapshot():
    wrapper = load_wrapper("corpus.json")
    assert wrapper["contract"] == "CorpusSnapshot"
    assert "snapshot_id" not in wrapper["data"], "FR-C-01: snapshot identity must be computed"
    return contracts().CorpusSnapshot.model_validate(wrapper["data"])


def snapshot_variant():
    """Same synthetic documents plus one extra version -> a different snapshot ID."""
    data = load_wrapper("corpus.json")["data"]
    extra = {
        "schema_version": 1,
        "document_id": "doc-synthetic-extra",
        "version_sha256": "8899aabbccddeeff8899aabbccddeeff8899aabbccddeeff8899aabbccddeeff",
        "title": "合成文献 X：额外版本样例（不是真实论文）",
        "source_name": "synthetic-extra.txt",
        "status": "ready",
    }
    return contracts().CorpusSnapshot.model_validate(
        {**data, "documents": [*data["documents"], extra]}
    )


def evidence_candidates(snap):
    wrapper = load_wrapper("evidence_candidates.json")
    assert wrapper["contract"] == "review-candidate-template"
    documents = {document.document_id: document for document in snap.documents}
    records = []
    for template in wrapper["data"]:
        assert "snapshot_id" not in template, "QA-01: fixture must not hardcode snapshot scope"
        assert "evidence_id" not in template, "QA-01: identity comes from the shared algorithm"
        document = documents[template["document_id"]]
        assert template["version_sha256"] == document.version_sha256
        records.append(
            contracts().EvidenceRecord(
                **(template | {"snapshot_id": snap.snapshot_id})
            )
        )
    assert len({record.evidence_id for record in records}) == len(records)
    return tuple(records)


def rebuild_evidence(evidence, **changes):
    payload = evidence.model_dump(mode="json")
    payload.pop("evidence_id")
    payload.update(changes)
    return contracts().EvidenceRecord(**payload)


# --------------------------------------------------------------------------- #
# Deterministic ledger helpers.
# --------------------------------------------------------------------------- #
def stepping_clock():
    state = {"tick": 0}

    def clock():
        state["tick"] += 1
        return datetime(2026, 3, 1, tzinfo=timezone.utc) + timedelta(seconds=state["tick"])

    return clock


def command_number(value):
    return "cmd-" + f"{value:032x}"


def make_ledger(root, *, snap=None, candidates=None, clock=None):
    snap = snapshot() if snap is None else snap
    return review_symbol("ReviewLedger")(
        ledger_root=Path(root),
        snapshot=snap,
        candidates=evidence_candidates(snap) if candidates is None else candidates,
        clock=stepping_clock() if clock is None else clock,
    )


def prepare(
    ledger,
    evidence_id,
    *,
    cmd,
    expected_revision,
    action="accept",
    reason=REASON,
    reviewer_ref=REVIEWER,
    question_id=QUESTION,
):
    return ledger.prepare_decision(
        question_id=question_id,
        evidence_id=evidence_id,
        action=action,
        reviewer_ref=reviewer_ref,
        reason=reason,
        expected_revision=expected_revision,
        command_id=cmd,
    )


def ledger_bytes(root):
    return {path.name: path.read_bytes() for path in sorted(Path(root).glob("*.jsonl"))}


def status_map(projection):
    return dict(projection.status_by_evidence)


def canonical_bytes(value):
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def recompute_digest(projection):
    """INV-05/QA-01: the exact canonical ledger digest from the approved plan."""
    events = sorted(projection.events, key=lambda event: event.decision.revision)
    payload = {
        "schema_version": 1,
        "snapshot_id": projection.snapshot_id,
        "question_id": projection.question_id,
        "revision": len(events),
        "events": [
            {"command_id": event.command_id, "decision": event.decision.model_dump(mode="json")}
            for event in events
        ],
    }
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def field(value, *names):
    """Read a required field from an object or mapping; missing fields fail loudly."""
    for name in names:
        if isinstance(value, Mapping) and name in value:
            return value[name]
        found = getattr(value, name, _MISSING)
        if found is not _MISSING:
            return found
    raise AssertionError(f"FR-C-02: missing required field among {names}")


def rows_of(view):
    for name in ("rows", "entries", "items"):
        value = getattr(view, name, None)
        if value is not None:
            return list(value)
    raise AssertionError("FR-C-02: ComparisonView exposes no rows/entries/items collection")


# --------------------------------------------------------------------------- #
# Normal behaviour.
# --------------------------------------------------------------------------- #
def test_empty_ledger_is_revision_zero_and_all_pending(tmp_path):
    """FR-C-01/INV-03: no decision means no accepted evidence and revision 0."""
    snap = snapshot()
    candidates = evidence_candidates(snap)
    ledger = make_ledger(tmp_path, snap=snap, candidates=candidates)

    projection = ledger.projection(QUESTION)
    assert projection.snapshot_id == snap.snapshot_id
    assert projection.question_id == QUESTION
    assert projection.revision == 0
    assert tuple(projection.events) == ()
    assert projection.accepted_evidence_ids == ()
    assert projection.digest == recompute_digest(projection)

    statuses = status_map(projection)
    reasons = dict(projection.latest_reason_by_evidence)
    for evidence in candidates:
        assert statuses.get(evidence.evidence_id, "pending") == "pending"
        assert reasons.get(evidence.evidence_id) is None

    assert all(path.stat().st_size == 0 for path in tmp_path.glob("*.jsonl"))


def test_accept_exclude_reset_append_monotonic_events(tmp_path):
    """FR-C-01/INV-05: explicit human commands append 1..N, never overwrite."""
    snap = snapshot()
    candidates = evidence_candidates(snap)
    support, oppose = candidates[0], candidates[1]
    ledger = make_ledger(tmp_path, snap=snap, candidates=candidates)

    accepted = ledger.commit_decision(
        prepare(ledger, support.evidence_id, cmd=command_number(1), expected_revision=0)
    )
    assert accepted.revision == 1
    assert status_map(accepted)[support.evidence_id] == "accepted"
    assert accepted.accepted_evidence_ids == (support.evidence_id,)
    first = accepted.events[-1]
    assert first.decision.status == "accepted"
    assert first.decision.revision == 1
    assert first.decision.actor_kind == "human"
    assert first.decision.reviewer_ref == REVIEWER

    excluded = ledger.commit_decision(
        prepare(
            ledger,
            oppose.evidence_id,
            cmd=command_number(2),
            action="exclude",
            expected_revision=1,
        )
    )
    assert excluded.revision == 2
    assert status_map(excluded)[oppose.evidence_id] == "excluded"
    assert excluded.events[-1].decision.revision == 2

    reset = ledger.commit_decision(
        prepare(
            ledger,
            support.evidence_id,
            cmd=command_number(3),
            action="reset",
            expected_revision=2,
            reason=RESET_REASON,
        )
    )
    assert reset.revision == 3
    assert status_map(reset)[support.evidence_id] == "pending"
    assert reset.accepted_evidence_ids == ()
    assert [event.decision.revision for event in reset.events] == [1, 2, 3]


def test_digest_recomputed_and_token_changes_after_each_effective_decision(tmp_path):
    """INV-04/INV-05: digest is recomputable and every decision yields a new token."""
    snap = snapshot()
    candidates = evidence_candidates(snap)
    ledger = make_ledger(tmp_path, snap=snap, candidates=candidates)

    empty = ledger.projection(QUESTION)
    assert empty.digest == recompute_digest(empty)

    first = ledger.commit_decision(
        prepare(ledger, candidates[0].evidence_id, cmd=command_number(101), expected_revision=0)
    )
    assert first.digest == recompute_digest(first)

    second = ledger.commit_decision(
        prepare(
            ledger,
            candidates[1].evidence_id,
            cmd=command_number(102),
            action="exclude",
            expected_revision=1,
        )
    )
    assert second.digest == recompute_digest(second)

    assert (empty.revision, first.revision, second.revision) == (0, 1, 2)
    assert len({empty.digest, first.digest, second.digest}) == 3
    ledger.verify_current(QUESTION, second.revision, second.digest)


def test_same_command_retry_is_idempotent_without_append(tmp_path):
    """FR-C-01: retrying an identical command returns the projection, no append."""
    snap = snapshot()
    candidates = evidence_candidates(snap)
    ledger = make_ledger(tmp_path, snap=snap, candidates=candidates)

    first = ledger.commit_decision(
        prepare(ledger, candidates[0].evidence_id, cmd=command_number(1), expected_revision=0)
    )
    before = ledger_bytes(tmp_path)

    again = ledger.commit_decision(
        prepare(ledger, candidates[0].evidence_id, cmd=command_number(1), expected_revision=1)
    )
    assert again.revision == first.revision == 1
    assert again.digest == first.digest
    assert ledger_bytes(tmp_path) == before


def test_reset_appends_pending_and_keeps_previous_events(tmp_path):
    """INV-05: reset appends pending and preserves accepted/excluded history."""
    snap = snapshot()
    candidates = evidence_candidates(snap)
    evidence = candidates[0]
    ledger = make_ledger(tmp_path, snap=snap, candidates=candidates)

    ledger.commit_decision(
        prepare(ledger, evidence.evidence_id, cmd=command_number(1), expected_revision=0)
    )
    reset = ledger.commit_decision(
        prepare(
            ledger,
            evidence.evidence_id,
            cmd=command_number(2),
            action="reset",
            expected_revision=1,
            reason=RESET_REASON,
        )
    )
    assert reset.revision == 2
    assert [event.decision.status for event in reset.events] == ["accepted", "pending"]
    assert status_map(reset)[evidence.evidence_id] == "pending"
    assert dict(reset.latest_reason_by_evidence)[evidence.evidence_id] == RESET_REASON


def test_compare_two_independent_sources_shows_all_required_fields(tmp_path):
    """FR-C-02: two independent documents render every required comparison field."""
    snap = snapshot()
    candidates = evidence_candidates(snap)
    support, oppose = candidates[0], candidates[1]
    documents = {document.document_id: document for document in snap.documents}
    assert support.document_id != oppose.document_id
    ledger = make_ledger(tmp_path, snap=snap, candidates=candidates)
    before = ledger_bytes(tmp_path)

    view = review_symbol("comparison_view")(
        ledger, QUESTION, [support.evidence_id, oppose.evidence_id]
    )
    rows = rows_of(view)
    assert len(rows) == 2
    assert {field(row, "document_id") for row in rows} == {
        support.document_id,
        oppose.document_id,
    }

    by_document = {field(row, "document_id"): row for row in rows}
    for evidence in (support, oppose):
        row = by_document[evidence.document_id]
        document = documents[evidence.document_id]
        assert field(row, "evidence_id", "id") == evidence.evidence_id
        assert field(row, "title") == document.title
        assert field(row, "source_name") == document.source_name
        assert field(row, "version_sha256") == evidence.version_sha256
        assert field(row, "excerpt") == evidence.excerpt
        assert field(row, "advisory_summary") == evidence.advisory_summary
        assert field(row, "status") == "pending"
        assert field(row, "reason", "latest_reason") is None
        assert field(row, "revision", "decision_revision", "latest_revision") in (None, 0)
        locator = field(row, "locator")
        assert field(locator, "parser_name")
        assert field(locator, "parser_version")
        assert field(locator, "chunk_id")
        assert field(locator, "page_start") == evidence.locator.page_start
        assert field(locator, "page_end") == evidence.locator.page_end
        assert field(locator, "line_start") == evidence.locator.line_start
        assert field(locator, "line_end") == evidence.locator.line_end

    assert ledger_bytes(tmp_path) == before, "FR-C-02: comparison must not write the ledger"


def test_similar_excerpts_remain_distinct_evidence(tmp_path):
    """FR-C-02/INV-02: equal excerpt text with another locator stays a distinct row."""
    snap = snapshot()
    candidates = evidence_candidates(snap)
    support, oppose, similar = candidates[0], candidates[1], candidates[3]
    assert similar.document_id == support.document_id
    assert similar.excerpt == support.excerpt
    assert similar.locator != support.locator
    assert similar.evidence_id != support.evidence_id

    ledger = make_ledger(tmp_path, snap=snap, candidates=candidates)
    view = review_symbol("comparison_view")(
        ledger, QUESTION, [support.evidence_id, oppose.evidence_id, similar.evidence_id]
    )
    rows = rows_of(view)
    assert len(rows) == 3
    assert len({field(row, "evidence_id", "id") for row in rows}) == 3

    same_document = [
        row for row in rows if field(row, "document_id") == support.document_id
    ]
    assert len(same_document) == 2
    assert sorted(field(row, "excerpt") for row in same_document) == sorted(
        [support.excerpt, similar.excerpt]
    )
    page_starts = sorted(
        field(field(row, "locator"), "page_start") for row in same_document
    )
    assert page_starts == sorted([support.locator.page_start, similar.locator.page_start])


def test_view_refresh_and_sort_do_not_write_ledger(tmp_path):
    """FR-C-02/INV-06: refresh/sort/read never write; only explicit submit appends."""
    snap = snapshot()
    candidates = evidence_candidates(snap)
    support, oppose = candidates[0], candidates[1]
    ledger = make_ledger(tmp_path, snap=snap, candidates=candidates)
    ledger.commit_decision(
        prepare(ledger, support.evidence_id, cmd=command_number(1), expected_revision=0)
    )
    before = ledger_bytes(tmp_path)
    evidence_ids = [support.evidence_id, oppose.evidence_id]
    comparison_view = review_symbol("comparison_view")

    first = rows_of(comparison_view(ledger, QUESTION, evidence_ids))
    second = rows_of(comparison_view(ledger, QUESTION, list(reversed(evidence_ids))))
    ledger.projection(QUESTION)
    prompt = review_symbol("decision_prompt")(ledger, QUESTION, oppose.evidence_id)
    assert field(prompt, "expected_revision") == 1
    actions = set(field(prompt, "allowed_actions", "actions"))
    assert {"accept", "exclude"} <= actions

    assert ledger_bytes(tmp_path) == before
    assert {field(row, "evidence_id", "id") for row in first} == {
        field(row, "evidence_id", "id") for row in second
    }

    current = ledger.projection(QUESTION)
    submitted = review_symbol("submit_decision")(
        ledger,
        question_id=QUESTION,
        evidence_id=oppose.evidence_id,
        action="accept",
        reviewer_ref=REVIEWER,
        reason=REASON,
        expected_revision=current.revision,
    )
    assert submitted.revision == current.revision + 1
    after = ledger_bytes(tmp_path)
    assert len(before) == len(after) == 1
    (name, old_bytes), = before.items()
    assert after[name].startswith(old_bytes)
    assert len(after[name].splitlines()) == len(old_bytes.splitlines()) + 1


# --------------------------------------------------------------------------- #
# Negative behaviour.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("reason", ["", " ", "\n\t", "\u3000"])
def test_empty_or_whitespace_reason_is_rejected(tmp_path, reason):
    """FR-C-01: every human command needs a non-empty reason."""
    snap = snapshot()
    candidates = evidence_candidates(snap)
    ledger = make_ledger(tmp_path, snap=snap, candidates=candidates)
    error = review_symbol("ReviewLedgerError")
    with pytest.raises((ValueError, error)):
        prepare(
            ledger,
            candidates[0].evidence_id,
            cmd=command_number(1),
            expected_revision=0,
            reason=reason,
        )
    assert ledger_bytes(tmp_path) == {}


def test_forged_model_import_or_prebuilt_decision_cannot_write(tmp_path):
    """INV-03: no import path, model actor, or prebuilt decision grants acceptance."""
    snap = snapshot()
    candidates = evidence_candidates(snap)
    ledger = make_ledger(tmp_path, snap=snap, candidates=candidates)
    package = module("papertrace.review")
    for forbidden in ("import_decisions", "restore_ledger", "accept_all", "auto_approve"):
        assert not hasattr(package, forbidden), f"INV-03: {forbidden} must not be a public entry"
        assert not hasattr(ledger, forbidden), f"INV-03: {forbidden} must not be a ledger method"

    with pytest.raises(ValidationError):
        contracts().ReviewDecision(
            schema_version=1,
            evidence_id=candidates[0].evidence_id,
            snapshot_id=snap.snapshot_id,
            question_id=QUESTION,
            status="accepted",
            actor_kind="model",
            reviewer_ref=REVIEWER,
            revision=1,
            reason=REASON,
            decided_at="2026-03-01T00:02:00Z",
        )

    prebuilt = contracts().ReviewDecision(
        schema_version=1,
        evidence_id=candidates[0].evidence_id,
        snapshot_id=snap.snapshot_id,
        question_id=QUESTION,
        status="accepted",
        actor_kind="human",
        reviewer_ref=REVIEWER,
        revision=1,
        reason=REASON,
        decided_at="2026-03-01T00:02:00Z",
    )
    error = review_symbol("ReviewLedgerError")
    with pytest.raises((TypeError, ValueError, AttributeError, error)):
        ledger.commit_decision(prebuilt)
    assert ledger_bytes(tmp_path) == {}


def test_advisory_summary_and_upstream_id_do_not_grant_acceptance(tmp_path):
    """INV-03: advisory text and upstream IDs never imply an accepted status."""
    snap = snapshot()
    candidates = evidence_candidates(snap)
    assert all(evidence.advisory_summary for evidence in candidates)
    assert all(evidence.upstream_context_id for evidence in candidates)
    assert not hasattr(candidates[0], "status")
    assert not hasattr(candidates[0], "accepted")

    ledger = make_ledger(tmp_path, snap=snap, candidates=candidates)
    projection = ledger.projection(QUESTION)
    assert projection.accepted_evidence_ids == ()
    statuses = status_map(projection)
    assert all(
        statuses.get(evidence.evidence_id, "pending") == "pending" for evidence in candidates
    )

    altered = rebuild_evidence(
        candidates[0],
        advisory_summary="synthetic：另一个摘要，不授予任何状态。",
        upstream_context_id="synthetic-other-context",
    )
    assert altered.evidence_id == candidates[0].evidence_id
    assert statuses.get(altered.evidence_id, "pending") == "pending"


def test_evidence_outside_snapshot_or_unknown_document_is_rejected(tmp_path):
    """FR-C-01/INV-02: candidates must belong to the current snapshot and document set."""
    snap = snapshot()
    candidates = evidence_candidates(snap)
    ledger = make_ledger(tmp_path, snap=snap, candidates=candidates)
    error = review_symbol("ReviewScopeError")

    outside_snapshot = rebuild_evidence(candidates[0], snapshot_id="snap-" + "0" * 64)
    unknown_document = rebuild_evidence(candidates[0], document_id="doc-synthetic-ghost")
    for bad_evidence in (outside_snapshot, unknown_document):
        try:
            bad_ledger = review_symbol("ReviewLedger")(
                ledger_root=tmp_path / bad_evidence.evidence_id,
                snapshot=snap,
                candidates=[*candidates, bad_evidence],
                clock=stepping_clock(),
            )
        except error:
            continue
        with pytest.raises(error):
            prepare(
                bad_ledger,
                bad_evidence.evidence_id,
                cmd=command_number(1),
                expected_revision=0,
            )

    with pytest.raises(error):
        prepare(ledger, "ev-" + "a" * 64, cmd=command_number(2), expected_revision=0)
    assert ledger_bytes(tmp_path) == {}


def test_decision_from_another_question_or_snapshot_is_not_visible(tmp_path):
    """FR-C-01/INV-02: ledgers are scoped to one (snapshot_id, question_id)."""
    snap = snapshot()
    candidates = evidence_candidates(snap)
    ledger = make_ledger(tmp_path, snap=snap, candidates=candidates)
    ledger.commit_decision(
        prepare(ledger, candidates[0].evidence_id, cmd=command_number(1), expected_revision=0)
    )
    assert len(ledger_bytes(tmp_path)) == 1

    other_question = ledger.projection(OTHER_QUESTION)
    assert other_question.revision == 0
    assert other_question.accepted_evidence_ids == ()

    variant = snapshot_variant()
    other_ledger = make_ledger(tmp_path, snap=variant)
    other_snapshot = other_ledger.projection(QUESTION)
    assert other_snapshot.revision == 0
    assert other_snapshot.accepted_evidence_ids == ()


def test_stale_expected_revision_is_rejected_without_overwrite(tmp_path):
    """FR-C-01: a stale expected_revision conflicts instead of overwriting."""
    snap = snapshot()
    candidates = evidence_candidates(snap)
    ledger = make_ledger(tmp_path, snap=snap, candidates=candidates)
    ledger.commit_decision(
        prepare(ledger, candidates[0].evidence_id, cmd=command_number(1), expected_revision=0)
    )
    before = ledger_bytes(tmp_path)
    conflict = review_symbol("ReviewRevisionConflict")

    with pytest.raises(conflict):
        intent = prepare(
            ledger, candidates[1].evidence_id, cmd=command_number(2), expected_revision=0
        )
        ledger.commit_decision(intent)

    assert ledger_bytes(tmp_path) == before
    assert ledger.projection(QUESTION).revision == 1


def test_noop_repeat_decision_is_rejected(tmp_path):
    """FR-C-01: an identical latest decision is a no-op, not a new event."""
    snap = snapshot()
    candidates = evidence_candidates(snap)
    evidence = candidates[0]
    ledger = make_ledger(tmp_path, snap=snap, candidates=candidates)
    ledger.commit_decision(
        prepare(ledger, evidence.evidence_id, cmd=command_number(1), expected_revision=0)
    )
    before = ledger_bytes(tmp_path)

    noop = review_symbol("ReviewNoop")
    with pytest.raises(noop):
        intent = prepare(
            ledger, evidence.evidence_id, cmd=command_number(2), expected_revision=1
        )
        ledger.commit_decision(intent)

    assert ledger_bytes(tmp_path) == before
    assert ledger.projection(QUESTION).revision == 1


def test_cross_snapshot_old_acceptance_does_not_migrate(tmp_path):
    """INV-02: a new snapshot does not inherit acceptance from an old one."""
    snap = snapshot()
    candidates = evidence_candidates(snap)
    ledger = make_ledger(tmp_path, snap=snap, candidates=candidates)
    accepted = ledger.commit_decision(
        prepare(ledger, candidates[0].evidence_id, cmd=command_number(1), expected_revision=0)
    )
    assert accepted.accepted_evidence_ids == (candidates[0].evidence_id,)

    variant = snapshot_variant()
    assert variant.snapshot_id != snap.snapshot_id
    new_ledger = make_ledger(tmp_path, snap=variant)
    fresh = new_ledger.projection(QUESTION)
    assert fresh.revision == 0
    assert fresh.accepted_evidence_ids == ()

    scope_error = review_symbol("ReviewScopeError")
    with pytest.raises(scope_error):
        prepare(
            new_ledger,
            candidates[0].evidence_id,
            cmd=command_number(2),
            expected_revision=0,
        )


def test_old_review_token_is_stale_after_any_new_decision(tmp_path):
    """INV-04: any effective decision invalidates earlier revision/digest tokens."""
    snap = snapshot()
    candidates = evidence_candidates(snap)
    ledger = make_ledger(tmp_path, snap=snap, candidates=candidates)

    first = ledger.commit_decision(
        prepare(ledger, candidates[0].evidence_id, cmd=command_number(1), expected_revision=0)
    )
    ledger.verify_current(QUESTION, first.revision, first.digest)

    second = ledger.commit_decision(
        prepare(
            ledger,
            candidates[1].evidence_id,
            cmd=command_number(2),
            action="exclude",
            expected_revision=1,
        )
    )

    stale = review_symbol("ReviewTokenStale")
    mismatch = review_symbol("ReviewDigestMismatch")
    with pytest.raises((stale, mismatch)):
        ledger.verify_current(QUESTION, first.revision, first.digest)
    with pytest.raises(mismatch):
        ledger.verify_current(QUESTION, second.revision, "0" * 64)
    ledger.verify_current(QUESTION, second.revision, second.digest)


def test_corrupt_digest_partial_line_or_duplicate_revision_fails_closed(tmp_path):
    """INV-05: damaged ledgers fail closed and are never auto-repaired."""
    corrupted = review_symbol("ReviewLedgerCorrupted")

    def build(root):
        snap = snapshot()
        candidates = evidence_candidates(snap)
        ledger = make_ledger(root, snap=snap, candidates=candidates)
        ledger.commit_decision(
            prepare(ledger, candidates[0].evidence_id, cmd=command_number(1), expected_revision=0)
        )
        ledger.commit_decision(
            prepare(
                ledger,
                candidates[1].evidence_id,
                cmd=command_number(2),
                action="exclude",
                expected_revision=1,
            )
        )
        files = sorted(Path(root).glob("*.jsonl"))
        assert len(files) == 1
        return snap, candidates, files[0]

    # 1. Tampered digest_after on the final event.
    root = tmp_path / "digest"
    snap, candidates, path = build(root)
    lines = path.read_text(encoding="utf-8").splitlines()
    tampered = json.loads(lines[-1])
    tampered["digest_after"] = "0" * 64
    lines[-1] = canonical_bytes(tampered).decode("utf-8")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    before = path.read_bytes()
    with pytest.raises(corrupted):
        make_ledger(root, snap=snap, candidates=candidates).projection(QUESTION)
    assert path.read_bytes() == before

    # 2. Truncated final line.
    root = tmp_path / "partial"
    snap, candidates, path = build(root)
    path.write_bytes(path.read_bytes()[:-12])
    before = path.read_bytes()
    with pytest.raises(corrupted):
        make_ledger(root, snap=snap, candidates=candidates).projection(QUESTION)
    assert path.read_bytes() == before

    # 3. Duplicate revision line.
    root = tmp_path / "duplicate"
    snap, candidates, path = build(root)
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join([lines[0], lines[1], lines[0]]) + "\n", encoding="utf-8")
    before = path.read_bytes()
    with pytest.raises(corrupted):
        make_ledger(root, snap=snap, candidates=candidates).projection(QUESTION)
    assert path.read_bytes() == before


def test_compare_requires_two_distinct_independent_documents(tmp_path):
    """FR-C-02: comparison needs >=2 distinct evidence IDs from >=2 documents."""
    snap = snapshot()
    candidates = evidence_candidates(snap)
    ledger = make_ledger(tmp_path, snap=snap, candidates=candidates)
    insufficient = review_symbol("InsufficientIndependentSources")
    comparison_view = review_symbol("comparison_view")
    before = ledger_bytes(tmp_path)

    with pytest.raises(insufficient):
        comparison_view(ledger, QUESTION, [candidates[0].evidence_id])
    with pytest.raises(insufficient):
        comparison_view(ledger, QUESTION, [candidates[0].evidence_id] * 2)
    with pytest.raises(insufficient):
        comparison_view(ledger, QUESTION, [candidates[0].evidence_id, candidates[3].evidence_id])

    assert ledger_bytes(tmp_path) == before


def test_direct_service_call_still_enforces_scope_and_revision(tmp_path):
    """INV-06: bypassing the view does not bypass human/scope/revision checks."""
    snap = snapshot()
    candidates = evidence_candidates(snap)
    ledger = make_ledger(tmp_path, snap=snap, candidates=candidates)
    scope_error = review_symbol("ReviewScopeError")
    revision_error = review_symbol("ReviewRevisionConflict")

    with pytest.raises(scope_error):
        prepare(ledger, "ev-" + "f" * 64, cmd=command_number(1), expected_revision=0)

    ledger.commit_decision(
        prepare(ledger, candidates[0].evidence_id, cmd=command_number(2), expected_revision=0)
    )
    with pytest.raises(revision_error):
        intent = prepare(
            ledger, candidates[1].evidence_id, cmd=command_number(3), expected_revision=0
        )
        ledger.commit_decision(intent)
    assert ledger.projection(QUESTION).revision == 1


def test_historical_ledger_prefix_is_never_rewritten(tmp_path):
    """INV-05: every append extends the file; earlier bytes are immutable."""
    snap = snapshot()
    candidates = evidence_candidates(snap)
    ledger = make_ledger(tmp_path, snap=snap, candidates=candidates)
    sequence = (
        (candidates[0], "accept", REASON),
        (candidates[1], "exclude", REASON),
        (candidates[0], "reset", RESET_REASON),
    )

    checks = []
    for index, (evidence, action, reason) in enumerate(sequence, start=1):
        ledger.commit_decision(
            prepare(
                ledger,
                evidence.evidence_id,
                cmd=command_number(index),
                action=action,
                expected_revision=index - 1,
                reason=reason,
            )
        )
        checks.append(ledger_bytes(tmp_path))

    assert len(checks) == 3
    for previous, current in zip(checks, checks[1:]):
        (name, old_bytes), = previous.items()
        assert current[name].startswith(old_bytes)
        assert len(current[name].splitlines()) == len(old_bytes.splitlines()) + 1

    final = ledger.projection(QUESTION)
    assert [event.decision.revision for event in final.events] == [1, 2, 3]
