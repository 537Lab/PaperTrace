"""A-local corpus service using real immutable shared models.

PROPOSED_INTEGRATION: callable receipts, partial batches, failed replacement
projection, retry policy and ABA revisions are local semantics, not a B API.
No parser, PaperQA, network client or product model is initialized here.
"""

from collections.abc import Sequence
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import uuid4

from papertrace.contracts import CorpusSnapshot, DocumentVersion

from .ports import FaultHook, Ingest, ingest_result
from .sources import authorize, lexical, read_selected
from .storage import Storage


def origin_key(path: Path) -> str:
    """Persist an opaque origin key, never an absolute external path."""
    return sha256(str(path).encode()).hexdigest()


def display_name(path: Path) -> str:
    name = "".join(
        "_" if ord(character) < 32 or ord(character) == 127 or character in "/\\:"
        else character for character in path.name
    )
    return name if name.strip() and name not in {".", ".."} else "source"


class CorpusService:
    """Single-writer local library; successful persistence precedes memory updates."""

    def __init__(
        self, *, storage_root: Path, allowed_root: Path,
        selected_files: tuple[Path, ...], ingest: Ingest, policy_ref: str,
        max_bytes: int = 20 * 1024 * 1024, fault_hook: FaultHook | None = None,
    ) -> None:
        if type(max_bytes) is not int or max_bytes < 1:
            raise ValueError("INVALID_LIMIT")
        if not isinstance(policy_ref, str) or not policy_ref.strip():
            raise ValueError("INVALID_POLICY")
        self._root = lexical(allowed_root)
        self._selected = frozenset(lexical(path) for path in selected_files)
        self._ingest = ingest
        self._policy_ref = policy_ref
        self._limit = max_bytes
        self._storage = Storage(storage_root, fault_hook)
        self._state: dict[str, Any] = {
            "schema_version": 1, "revision": 0, "origins": {}, "records": {},
            "members": {}, "snapshots": [], "snapshot_id": "",
        }
        self._snapshot = CorpusSnapshot(
            schema_version=1, documents=(), created_at=datetime.now(timezone.utc)
        )
        state = self._storage.load()
        if state is not None:
            self._recover(state)

    def _recover(self, state: dict[str, Any]) -> None:
        """Validate exactly the pointed manifest; never scan or replay ingest."""
        try:
            if state["schema_version"] != 1:
                raise ValueError
            if type(state["revision"]) is not int or state["revision"] < 1:
                raise ValueError
            if not all(
                isinstance(state[key], dict) for key in ("origins", "records", "members")
            ):
                raise ValueError
            if not isinstance(state["snapshots"], list):
                raise ValueError
            if state["snapshot_id"] not in state["snapshots"]:
                raise ValueError
            snapshot = self._storage.snapshot(state["snapshot_id"])
            members = tuple(
                DocumentVersion.model_validate(doc) for doc in state["members"].values()
            )
            expected = CorpusSnapshot(
                schema_version=1, documents=members, created_at=snapshot.created_at
            )
            if expected != snapshot:
                raise ValueError
            for key, document_id in state["origins"].items():
                if (
                    not isinstance(key, str) or len(key) != 64
                    or document_id not in state["records"]
                ):
                    raise ValueError
            for document_id, record in state["records"].items():
                attempts = record["attempts"]
                if not isinstance(attempts, list) or not attempts:
                    raise ValueError
                for item in attempts:
                    if (
                        item["document_id"] != document_id
                        or item["status"] not in {"ready", "failed"}
                    ):
                        raise ValueError
                    # Validate identity and display fields even on failure records.
                    DocumentVersion(
                        schema_version=1, document_id=document_id,
                        version_sha256=item["version_sha256"] or "0" * 64,
                        title=item["source_name"], source_name=item["source_name"], status="ready",
                    )
                    if item["version_sha256"]:
                        self._storage.source(item["version_sha256"])
                if "retry_origin" in record and (
                    not isinstance(record["retry_origin"], str)
                    or record["retry_origin"] not in state["origins"]
                    or attempts[-1]["status"] != "failed"
                    or attempts[-1]["version_sha256"]
                ):
                    raise ValueError
                if document_id in state["members"]:
                    member = state["members"][document_id]
                    if member["document_id"] != document_id or not any(
                        item["status"] == "ready"
                        and item["version_sha256"] == member["version_sha256"]
                        and item["source_name"] == member["source_name"]
                        for item in attempts
                    ):
                        raise ValueError
            if not set(state["members"]).issubset(state["records"]):
                raise ValueError
            for snapshot_id in state["snapshots"]:
                historical = self._storage.snapshot(snapshot_id)
                for doc in historical.documents:
                    self._storage.source(doc.version_sha256)
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            raise ValueError("PERSISTENCE_FAILED") from None
        self._state = state
        self._snapshot = snapshot

    def _publish(self, state: dict[str, Any], sources: dict[str, bytes]) -> None:
        snapshot = CorpusSnapshot(
            schema_version=1,
            documents=tuple(
                DocumentVersion.model_validate(doc) for doc in state["members"].values()
            ),
            created_at=datetime.now(timezone.utc),
        )
        same_snapshot = snapshot.snapshot_id == self._snapshot.snapshot_id
        if same_snapshot:
            snapshot = self._snapshot
        if not same_snapshot or self._state["revision"] == 0:
            # The first interrupted commit may have written this immutable snapshot.
            existing = self._storage.path("snapshots", snapshot.snapshot_id + ".json")
            if existing.exists():
                try:
                    snapshot = self._storage.snapshot(snapshot.snapshot_id)
                except (ValueError, OSError):
                    raise ValueError("PERSISTENCE_FAILED") from None
        state["revision"] = self._state["revision"] + 1
        state["snapshot_id"] = snapshot.snapshot_id
        if snapshot.snapshot_id not in state["snapshots"]:
            state["snapshots"].append(snapshot.snapshot_id)
        self._storage.commit(state, snapshot, sources)
        self._state, self._snapshot = state, snapshot

    def _input(self, path: Path) -> tuple[bytes | None, str | None]:
        if path.suffix.lower() not in {".txt", ".pdf"}:
            return None, "UNSUPPORTED_TYPE"
        try:
            payload = read_selected(path, self._limit)
        except FileNotFoundError:
            return None, "SOURCE_MISSING"
        except OSError:
            # Recheck authorization when traversal fails after selection was checked.
            authorize(path, self._root, self._selected)
            return None, "SOURCE_UNREADABLE"
        if not payload:
            return None, "EMPTY_SOURCE"
        if len(payload) > self._limit:
            return None, "SOURCE_TOO_LARGE"
        return payload, None

    def _attempt(
        self, document_id: str, name: str, payload: bytes | None, reason: str | None,
    ) -> dict[str, Any]:
        digest = sha256(payload).hexdigest() if payload is not None else ""
        status, stage = "failed", "source"
        if reason is None and payload is not None:
            status, stage, reason = ingest_result(self._ingest, {
                "document_id": document_id, "version_sha256": digest,
                "source_name": name, "source_bytes": payload,
                "metadata": {}, "policy_ref": self._policy_ref,
            })
        return {
            "source_name": name, "document_id": document_id,
            "version_sha256": digest, "status": status, "stage": stage,
            "reason_code": reason,
        }

    @staticmethod
    def _append(state: dict[str, Any], item: dict[str, Any], origin: str | None) -> None:
        document_id = item["document_id"]
        record = state["records"][document_id]
        record["attempts"].append(deepcopy(item))
        if origin is not None and not item["version_sha256"]:
            record["retry_origin"] = origin
        else:
            record.pop("retry_origin", None)
        if item["status"] == "ready":
            doc = DocumentVersion(
                schema_version=1, document_id=document_id,
                version_sha256=item["version_sha256"], title=item["source_name"],
                source_name=item["source_name"], status="ready",
            )
            state["members"][document_id] = doc.model_dump(mode="json")
        else:
            # PROPOSED_INTEGRATION: a failed replacement is not the old ready version.
            state["members"].pop(document_id, None)

    def _batch(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "items": deepcopy(items), "snapshot": self._snapshot,
            "complete": all(item["status"] == "ready" for item in items),
        }

    def import_files(
        self, paths: Sequence[Path], replacements: dict[Path, str] | None = None,
    ) -> dict[str, Any]:
        """Authorize the entire request before reading or calling the ingest port."""
        authorized = [authorize(path, self._root, self._selected) for path in paths]
        replacement_map = {
            lexical(path): value for path, value in (replacements or {}).items()
        }
        if not set(replacement_map).issubset(authorized):
            raise ValueError("INVALID_REPLACEMENT")
        if any(value not in self._state["records"] for value in replacement_map.values()):
            raise ValueError("INVALID_REPLACEMENT")
        # Open and validate each source before any call to the ingest port.
        inputs = {path: self._input(path) for path in dict.fromkeys(authorized)}
        state = deepcopy(self._state)
        origins: dict[str, str] = state["origins"]
        items: list[dict[str, Any]] = []
        sources: dict[str, bytes] = {}
        changed = False
        for path in authorized:
            payload, reason = inputs[path]
            origin = origin_key(path)
            document_id = replacement_map.get(path) or origins.get(origin)
            if document_id is None:
                document_id = "doc-" + uuid4().hex
                state["records"][document_id] = {"attempts": []}
            record = state["records"][document_id]
            history = record["attempts"]
            digest = sha256(payload).hexdigest() if payload is not None else ""
            last_origin = record.get("retry_origin")
            if history and not digest and last_origin is None:
                # Resolve a legacy failure against the bindings before rebinding.
                last_origin = self._unique_origin(origins, document_id)
            origins[origin] = document_id
            if history and history[-1]["version_sha256"] == digest and (
                payload is not None
                or (history[-1]["reason_code"] == reason and last_origin == origin)
            ):
                # Ready reuse verifies the managed source too; never silently repair it.
                if digest and digest not in sources:
                    self._storage.source(digest)
                items.append(deepcopy(history[-1]))
                continue
            item = self._attempt(document_id, display_name(path), payload, reason)
            if payload is not None:
                sources[digest] = payload
            self._append(state, item, origin)
            items.append(item)
            changed = True
        # A byte-identical explicit replacement may only add/rebind an origin.
        # Persist that mapping through the same atomic commit without ingesting
        # again or appending an attempt. _publish reuses the unchanged snapshot.
        if changed or state["origins"] != self._state["origins"]:
            self._publish(state, sources)
        return self._batch(items)

    @staticmethod
    def _unique_origin(origins: dict[str, str], document_id: str) -> str | None:
        bindings = [key for key, target in origins.items() if target == document_id]
        return bindings[0] if len(bindings) == 1 else None

    def _retry_path(self, document_id: str, origin: str | None) -> Path:
        origins: dict[str, str] = self._state["origins"]
        if origin is None:
            # Older manifests have no origin for a failed read. Use a unique binding.
            origin = self._unique_origin(origins, document_id)
        if origin is not None and origins.get(origin) == document_id:
            for path in self._selected:
                if origin_key(path) == origin:
                    return authorize(path, self._root, self._selected)
        raise ValueError("SOURCE_NOT_AUTHORIZED")

    def retry_failed(self, document_ids: Sequence[str]) -> dict[str, Any]:
        """Explicit retry appends attempts; it cannot re-ingest ready records."""
        ids = list(document_ids)
        if len(ids) != len(set(ids)):
            raise ValueError("NOT_FAILED")
        for document_id in ids:
            record = self._state["records"].get(document_id)
            if record is None or record["attempts"][-1]["status"] != "failed":
                raise ValueError("NOT_FAILED")
        retries: list[tuple[str, str, bytes | None, str | None, str | None]] = []
        for document_id in ids:
            record = self._state["records"][document_id]
            previous = record["attempts"][-1]
            digest = previous["version_sha256"]
            origin = None
            if digest:
                payload: bytes | None = self._storage.source(digest)
                reason: str | None = None
            else:
                path = self._retry_path(document_id, record.get("retry_origin"))
                payload, reason = self._input(path)
                origin = origin_key(path)
            retries.append((document_id, previous["source_name"], payload, reason, origin))
        state = deepcopy(self._state)
        sources: dict[str, bytes] = {}
        items: list[dict[str, Any]] = []
        for document_id, name, payload, reason, origin in retries:
            item = self._attempt(document_id, name, payload, reason)
            if payload is not None:
                sources[item["version_sha256"]] = payload
            self._append(state, item, origin)
            items.append(item)
        if ids:
            self._publish(state, sources)
        return self._batch(items)

    def current_snapshot(self) -> CorpusSnapshot:
        return self._snapshot

    def attempts(self, document_id: str) -> list[dict[str, Any]]:
        record = self._state["records"].get(document_id)
        if record is None:
            raise ValueError("UNKNOWN_DOCUMENT")
        result: list[dict[str, Any]] = deepcopy(record["attempts"])
        return result

    def read_source(
        self, *, snapshot_id: str, document_id: str, version_sha256: str
    ) -> bytes:
        if snapshot_id not in self._state["snapshots"]:
            raise ValueError("SNAPSHOT_MEMBERSHIP")
        try:
            snapshot = self._storage.snapshot(snapshot_id)
        except (OSError, ValueError):
            raise ValueError("SOURCE_INTEGRITY") from None
        if not any(
            doc.document_id == document_id and doc.version_sha256 == version_sha256
            for doc in snapshot.documents
        ):
            raise ValueError("SNAPSHOT_MEMBERSHIP")
        return self._storage.source(version_sha256)

    def freshness(self) -> tuple[str, int]:
        return self._snapshot.snapshot_id, self._state["revision"]

    def remove(self, document_ids: Sequence[str]) -> CorpusSnapshot:
        if any(document_id not in self._state["records"] for document_id in document_ids):
            raise ValueError("UNKNOWN_DOCUMENT")
        state = deepcopy(self._state)
        for document_id in document_ids:
            state["members"].pop(document_id, None)
        if state["members"] != self._state["members"]:
            self._publish(state, {})
        return self._snapshot

    def restore(self, document_ids: Sequence[str]) -> CorpusSnapshot:
        state = deepcopy(self._state)
        for document_id in document_ids:
            record = state["records"].get(document_id)
            if record is None:
                raise ValueError("UNKNOWN_DOCUMENT")
            ready = next(
                (item for item in reversed(record["attempts"]) if item["status"] == "ready"),
                None,
            )
            if ready is None:
                raise ValueError("NO_READY_VERSION")
            self._storage.source(ready["version_sha256"])
            doc = DocumentVersion(
                schema_version=1, document_id=document_id,
                version_sha256=ready["version_sha256"], title=ready["source_name"],
                source_name=ready["source_name"], status="ready",
            )
            state["members"][document_id] = doc.model_dump(mode="json")
        if state["members"] != self._state["members"]:
            self._publish(state, {})
        return self._snapshot
