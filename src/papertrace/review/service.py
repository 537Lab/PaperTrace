"""Append-only human review ledger for one ``(snapshot_id, question_id)`` scope.

Traceability: FR-C-01; INV-02/INV-03/INV-04/INV-05/INV-06; QA-01; SEC-01.

The ledger stores one canonical JSON line per effective human command. Reads
validate the whole file and fail closed; rejected commands never create or
extend a file. No model, network, import, or UI cache path can append here.
"""

from __future__ import annotations

import fcntl
import json
import os
import uuid
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal

from pydantic import ValidationError

from papertrace.contracts import CorpusSnapshot, DocumentVersion, EvidenceRecord, ReviewDecision

Clock = Callable[[], datetime]
ReviewStatus = Literal["pending", "accepted", "excluded"]

_ACTION_STATUS: Mapping[str, ReviewStatus] = {
    "accept": "accepted",
    "exclude": "excluded",
    "reset": "pending",
}


# --------------------------------------------------------------------------- #
# Explicit failure modes. Every path fails closed; none repairs the ledger.
# --------------------------------------------------------------------------- #
class ReviewLedgerError(Exception):
    """Base class for deterministic review-ledger failures."""


class ReviewScopeError(ReviewLedgerError):
    """Evidence is outside the configured snapshot/question scope."""


class ReviewRevisionConflict(ReviewLedgerError):
    """The caller's expected revision is not the current revision."""


class ReviewNoop(ReviewLedgerError):
    """The requested status already applies, so no event is appended."""


class ReviewTokenStale(ReviewLedgerError):
    """A review token refers to an older revision."""


class ReviewDigestMismatch(ReviewLedgerError):
    """A review token digest does not match the current projection."""


class ReviewLedgerCorrupted(ReviewLedgerError):
    """The on-disk ledger is damaged; it is never silently repaired."""


# --------------------------------------------------------------------------- #
# Immutable in-memory projections and prepared intents.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ReviewEvent:
    """One append-only ledger line."""

    command_id: str
    decision: ReviewDecision


@dataclass(frozen=True)
class ReviewProjection:
    """Replayable view of the current ledger revision."""

    snapshot_id: str
    question_id: str
    revision: int
    events: tuple[ReviewEvent, ...]
    accepted_evidence_ids: tuple[str, ...]
    digest: str
    status_by_evidence: Mapping[str, str]
    latest_reason_by_evidence: Mapping[str, str | None]
    latest_revision_by_evidence: Mapping[str, int | None]


@dataclass(frozen=True)
class _DecisionIntent:
    """Validated preparation result; it has no authority until committed."""

    question_id: str
    evidence_id: str
    action: str
    status: ReviewStatus
    reviewer_ref: str
    reason: str
    expected_revision: int
    command_id: str


# --------------------------------------------------------------------------- #
# Canonical serialization and digest.
# --------------------------------------------------------------------------- #
def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _digest(snapshot_id: str, question_id: str, events: Sequence[ReviewEvent]) -> str:
    """INV-04/INV-05/QA-01: the exact canonical digest approved by the plan."""

    ordered = sorted(events, key=lambda event: event.decision.revision)
    payload: dict[str, object] = {
        "schema_version": 1,
        "snapshot_id": snapshot_id,
        "question_id": question_id,
        "revision": len(ordered),
        "events": [
            {"command_id": event.command_id, "decision": event.decision.model_dump(mode="json")}
            for event in ordered
        ],
    }
    return sha256(_canonical_bytes(payload)).hexdigest()


def _latest_status(events: Sequence[ReviewEvent], evidence_id: str) -> ReviewStatus:
    status: ReviewStatus = "pending"
    for event in events:
        if event.decision.evidence_id == evidence_id:
            status = event.decision.status
    return status


# --------------------------------------------------------------------------- #
# Ledger service.
# --------------------------------------------------------------------------- #
class ReviewLedger:
    """Append-only ledger scoped to one snapshot and per-question file."""

    def __init__(
        self,
        *,
        ledger_root: Path | str,
        snapshot: CorpusSnapshot,
        candidates: Iterable[EvidenceRecord],
        clock: Clock,
    ) -> None:
        self._root = Path(ledger_root)
        self._snapshot = snapshot
        self._clock = clock
        self._documents: dict[str, DocumentVersion] = {
            document.document_id: document for document in snapshot.documents
        }
        records = tuple(candidates)
        by_id: dict[str, EvidenceRecord] = {}
        for record in records:
            if record.snapshot_id != snapshot.snapshot_id:
                raise ReviewScopeError("evidence does not belong to the current snapshot")
            document = self._documents.get(record.document_id)
            if document is None:
                raise ReviewScopeError("evidence document is not part of the snapshot")
            if record.version_sha256 != document.version_sha256:
                raise ReviewScopeError("evidence version is not part of the snapshot")
            if record.evidence_id in by_id:
                raise ReviewScopeError("duplicate evidence identity")
            by_id[record.evidence_id] = record
        self._candidates = records
        self._by_id = by_id

    # -- public read-only accessors --------------------------------------- #
    def evidence_record(self, evidence_id: str) -> EvidenceRecord:
        """Return one in-scope candidate or raise ``ReviewScopeError``."""

        record = self._by_id.get(evidence_id)
        if record is None:
            raise ReviewScopeError("unknown evidence identity")
        return record

    def document(self, document_id: str) -> DocumentVersion:
        """Return one snapshot document or raise ``ReviewScopeError``."""

        document = self._documents.get(document_id)
        if document is None:
            raise ReviewScopeError("document is not part of the snapshot")
        return document

    def projection(self, question_id: str) -> ReviewProjection:
        """Replay the ledger without writing anything."""

        events = self._read_events(question_id)
        return self._projection_from_events(question_id, events)

    def verify_current(self, question_id: str, revision: int, digest: str) -> None:
        """INV-04: accept only the exact current revision/digest pair."""

        projection = self.projection(question_id)
        if revision != projection.revision:
            raise ReviewTokenStale("review token revision is no longer current")
        if digest != projection.digest:
            raise ReviewDigestMismatch("review token digest does not match the ledger")

    # -- decide ----------------------------------------------------------- #
    def prepare_decision(
        self,
        *,
        question_id: str,
        evidence_id: str,
        action: str,
        reviewer_ref: str,
        reason: str,
        expected_revision: int,
        command_id: str,
    ) -> _DecisionIntent:
        """Validate a human command and return an intent without touching disk."""

        status = _ACTION_STATUS.get(action)
        if status is None:
            raise ValueError("action must be one of accept, exclude, reset")
        self.evidence_record(evidence_id)
        if not reason.strip():
            raise ValueError("a human review command needs a non-empty reason")
        if not command_id.strip():
            raise ValueError("a human review command needs a command_id")
        if not isinstance(expected_revision, int) or expected_revision < 0:
            raise ValueError("expected_revision must be a non-negative integer")
        self._ledger_path(question_id)
        return _DecisionIntent(
            question_id=question_id,
            evidence_id=evidence_id,
            action=action,
            status=status,
            reviewer_ref=reviewer_ref,
            reason=reason,
            expected_revision=expected_revision,
            command_id=command_id,
        )

    def commit_decision(self, intent: object) -> ReviewProjection:
        """Append exactly one event, or return the current projection on retry."""

        if not isinstance(intent, _DecisionIntent):
            raise TypeError("commit_decision requires an intent from prepare_decision")
        self.evidence_record(intent.evidence_id)
        if not intent.reason.strip():
            raise ValueError("a human review command needs a non-empty reason")
        path = self._ledger_path(intent.question_id)

        # Never create a file for an immediately rejected command.
        if not path.exists():
            if intent.expected_revision != 0:
                raise ReviewRevisionConflict("expected revision is not current")
            if intent.status == "pending":
                raise ReviewNoop("evidence is already pending")

        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a+b") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                handle.seek(0)
                events = self._parse_events(intent.question_id, handle.read())
                existing = next(
                    (event for event in events if event.command_id == intent.command_id), None
                )
                if existing is not None:
                    if not self._same_command(existing, intent):
                        raise ReviewRevisionConflict(
                            "command_id was already used with different content"
                        )
                    if intent.expected_revision != len(events):
                        raise ReviewRevisionConflict("expected revision is not current")
                    return self._projection_from_events(intent.question_id, events)

                if intent.expected_revision != len(events):
                    raise ReviewRevisionConflict("expected revision is not current")
                if _latest_status(events, intent.evidence_id) == intent.status:
                    raise ReviewNoop("evidence already has the requested status")

                decision = ReviewDecision(
                    schema_version=1,
                    evidence_id=intent.evidence_id,
                    snapshot_id=self._snapshot.snapshot_id,
                    question_id=intent.question_id,
                    status=intent.status,
                    actor_kind="human",
                    reviewer_ref=intent.reviewer_ref,
                    revision=len(events) + 1,
                    reason=intent.reason,
                    decided_at=self._clock(),
                )
                event = ReviewEvent(command_id=intent.command_id, decision=decision)
                new_events = (*events, event)
                digest_after = _digest(self._snapshot.snapshot_id, intent.question_id, new_events)
                line = _canonical_bytes(
                    {
                        "command_id": intent.command_id,
                        "decision": decision.model_dump(mode="json"),
                        "digest_after": digest_after,
                    }
                ) + b"\n"
                handle.seek(0, os.SEEK_END)
                handle.write(line)
                handle.flush()
                os.fsync(handle.fileno())
                return self._projection_from_events(intent.question_id, new_events)
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    # -- internals -------------------------------------------------------- #
    def _ledger_path(self, question_id: str) -> Path:
        if (
            not question_id
            or question_id in {".", ".."}
            or "/" in question_id
            or "\\" in question_id
        ):
            raise ReviewScopeError("question identity cannot be used as a filename")
        snapshot_hex = self._snapshot.snapshot_id.removeprefix("snap-")
        return self._root / f"{snapshot_hex}-{question_id}.jsonl"

    def _read_events(self, question_id: str) -> tuple[ReviewEvent, ...]:
        path = self._ledger_path(question_id)
        if not path.exists():
            return ()
        return self._parse_events(question_id, path.read_bytes())

    def _parse_events(self, question_id: str, data: bytes) -> tuple[ReviewEvent, ...]:
        if data and not data.endswith(b"\n"):
            raise ReviewLedgerCorrupted("ledger ends with a partial line")
        events: list[ReviewEvent] = []
        for expected_revision, raw in enumerate(data.splitlines(), start=1):
            if not raw:
                raise ReviewLedgerCorrupted("ledger contains a blank line")
            try:
                payload: Any = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ReviewLedgerCorrupted("ledger line is not valid canonical JSON") from exc
            if not isinstance(payload, dict):
                raise ReviewLedgerCorrupted("ledger line is not a JSON object")
            command_id = payload.get("command_id")
            decision_payload = payload.get("decision")
            digest_after = payload.get("digest_after")
            if (
                not isinstance(command_id, str)
                or not isinstance(decision_payload, dict)
                or not isinstance(digest_after, str)
            ):
                raise ReviewLedgerCorrupted("ledger line is missing required fields")
            try:
                decision = ReviewDecision.model_validate(decision_payload)
            except ValidationError as exc:
                raise ReviewLedgerCorrupted("ledger decision does not match contracts") from exc
            if decision.snapshot_id != self._snapshot.snapshot_id:
                raise ReviewLedgerCorrupted("ledger decision belongs to another snapshot")
            if decision.question_id != question_id:
                raise ReviewLedgerCorrupted("ledger decision belongs to another question")
            if decision.evidence_id not in self._by_id:
                raise ReviewLedgerCorrupted("ledger decision references out-of-scope evidence")
            if decision.revision != expected_revision:
                raise ReviewLedgerCorrupted("ledger revisions are not contiguous")
            events.append(ReviewEvent(command_id=command_id, decision=decision))
            if digest_after != _digest(self._snapshot.snapshot_id, question_id, events):
                raise ReviewLedgerCorrupted("ledger digest_after does not match its events")
        return tuple(events)

    def _projection_from_events(
        self, question_id: str, events: Sequence[ReviewEvent]
    ) -> ReviewProjection:
        statuses: dict[str, ReviewStatus] = {
            record.evidence_id: "pending" for record in self._candidates
        }
        reasons: dict[str, str | None] = {record.evidence_id: None for record in self._candidates}
        revisions: dict[str, int | None] = {record.evidence_id: None for record in self._candidates}
        for event in events:
            decision = event.decision
            statuses[decision.evidence_id] = decision.status
            reasons[decision.evidence_id] = decision.reason
            revisions[decision.evidence_id] = decision.revision
        accepted = tuple(
            sorted(
                evidence_id
                for evidence_id, status in statuses.items()
                if status == "accepted"
            )
        )
        return ReviewProjection(
            snapshot_id=self._snapshot.snapshot_id,
            question_id=question_id,
            revision=len(events),
            events=tuple(events),
            accepted_evidence_ids=accepted,
            digest=_digest(self._snapshot.snapshot_id, question_id, events),
            status_by_evidence=MappingProxyType(statuses),
            latest_reason_by_evidence=MappingProxyType(reasons),
            latest_revision_by_evidence=MappingProxyType(revisions),
        )

    def _same_command(self, event: ReviewEvent, intent: _DecisionIntent) -> bool:
        decision = event.decision
        return (
            event.command_id == intent.command_id
            and decision.evidence_id == intent.evidence_id
            and decision.question_id == intent.question_id
            and decision.snapshot_id == self._snapshot.snapshot_id
            and decision.status == intent.status
            and decision.reviewer_ref == intent.reviewer_ref
            and decision.reason == intent.reason
        )


def submit_decision(
    ledger: ReviewLedger,
    *,
    question_id: str,
    evidence_id: str,
    action: str,
    reviewer_ref: str,
    reason: str,
    expected_revision: int,
) -> ReviewProjection:
    """Service entry used by the view: prepare and append one human decision."""

    intent = ledger.prepare_decision(
        question_id=question_id,
        evidence_id=evidence_id,
        action=action,
        reviewer_ref=reviewer_ref,
        reason=reason,
        expected_revision=expected_revision,
        command_id="cmd-" + uuid.uuid4().hex,
    )
    return ledger.commit_decision(intent)
