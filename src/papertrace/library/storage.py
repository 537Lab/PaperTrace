"""Single-writer A-local immutable records with a final atomic current pointer."""

import json
import os
import re
import stat
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import uuid4

from papertrace.contracts import CorpusSnapshot

from .ports import FaultHook
from .sources import lexical


def encoded(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


_STORAGE_FOLDERS = ("sources", "snapshots", "manifests")
_EMPTY_CURRENT = encoded({"schema_version": 1, "empty": True})


class Storage:
    """No scanning, replay, automatic fallback, or overwriting history."""

    def __init__(self, root: Path, fault_hook: FaultHook | None) -> None:
        self.root = lexical(root)
        self.fault_hook = fault_hook
        self.check(self.root)
        if ".." in self.root.parts:
            raise ValueError("PERSISTENCE_FAILED")

    @staticmethod
    def check(path: Path) -> None:
        if any(part.is_symlink() for part in (path, *path.parents)):
            raise ValueError("PERSISTENCE_FAILED")

    def path(self, folder: str, name: str) -> Path:
        if folder not in _STORAGE_FOLDERS:
            raise ValueError("PERSISTENCE_FAILED")
        if not name or Path(name).name != name or name in {".", ".."}:
            raise ValueError("PERSISTENCE_FAILED")
        path = self.root / folder / name
        self.check(path)
        return path

    def fault(self, stage: str) -> None:
        if self.fault_hook is not None:
            self.fault_hook(stage)

    @staticmethod
    def _write_synced(path: Path, payload: bytes) -> None:
        with path.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())

    @staticmethod
    def _sync_directory(directory: Path) -> None:
        descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    @staticmethod
    def read(path: Path) -> bytes:
        Storage.check(path)
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError("PERSISTENCE_FAILED")
            return stream.read()

    def immutable(self, path: Path, payload: bytes) -> None:
        self.check(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.check(path)
        temporary = path.parent / (".pending-" + uuid4().hex)
        try:
            self._write_synced(temporary, payload)
            try:
                os.link(temporary, path)
            except FileExistsError:
                if self.read(path) != payload:
                    raise ValueError("PERSISTENCE_FAILED") from None
        finally:
            temporary.unlink(missing_ok=True)

    def snapshot(self, snapshot_id: str) -> CorpusSnapshot:
        if re.fullmatch(r"snap-[0-9a-f]{64}", snapshot_id) is None:
            raise ValueError("SNAPSHOT_MEMBERSHIP")
        snapshot = CorpusSnapshot.model_validate_json(
            self.read(self.path("snapshots", snapshot_id + ".json"))
        )
        if snapshot.snapshot_id != snapshot_id:
            raise ValueError("SOURCE_INTEGRITY")
        return snapshot

    def source(self, digest: str) -> bytes:
        if re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise ValueError("SOURCE_INTEGRITY")
        try:
            payload = self.read(self.path("sources", digest))
            if sha256(payload).hexdigest() != digest:
                raise ValueError("SOURCE_INTEGRITY")
            return payload
        except (OSError, ValueError):
            raise ValueError("SOURCE_INTEGRITY") from None

    def load(self) -> dict[str, Any] | None:
        pointer = self.root / "current"
        try:
            self.check(pointer)
            if not pointer.exists():
                # Older first imports could leave empty directories before any write.
                for folder in _STORAGE_FOLDERS:
                    directory = self.root / folder
                    self.check(directory)
                    if directory.exists() and (
                        not directory.is_dir() or next(directory.iterdir(), None) is not None
                    ):
                        raise ValueError("PERSISTENCE_FAILED")
                return None
            payload = self.read(pointer)
            if payload == _EMPTY_CURRENT:
                return None
            record = json.loads(payload)
            name = record["manifest"]
            if not isinstance(name, str) or re.fullmatch(r"[0-9a-f]{32}\.json", name) is None:
                raise ValueError("PERSISTENCE_FAILED")
            payload = self.read(self.path("manifests", name))
            if sha256(payload).hexdigest() != record["sha256"]:
                raise ValueError("PERSISTENCE_FAILED")
            state = json.loads(payload)
            if not isinstance(state, dict):
                raise ValueError("PERSISTENCE_FAILED")
            return state
        except (OSError, ValueError, KeyError, TypeError):
            raise ValueError("PERSISTENCE_FAILED") from None

    def commit(
        self, state: dict[str, Any], snapshot: CorpusSnapshot, sources: dict[str, bytes]
    ) -> None:
        """Publish only after every immutable record is complete and fsynced."""
        temporary = self.root / (".current-" + uuid4().hex)
        current = self.root / "current"
        try:
            self.check(self.root)
            self.root.mkdir(parents=True, exist_ok=True)
            self.check(current)
            if not current.exists():
                if state["revision"] != 1:
                    raise ValueError("PERSISTENCE_FAILED")
                self.load()  # A missing pointer may be initialized only in a fresh store.
                # Durably publish the empty state before creating any managed records.
                self._write_synced(temporary, _EMPTY_CURRENT)
                os.replace(temporary, current)
                self._sync_directory(self.root)
            directories = [self.root / folder for folder in _STORAGE_FOLDERS]
            for directory in directories:
                self.check(directory)
                directory.mkdir(exist_ok=True)
            for digest, payload in sources.items():
                self.fault("copy_source")
                if sha256(payload).hexdigest() != digest:
                    raise ValueError("PERSISTENCE_FAILED")
                self.immutable(self.path("sources", digest), payload)
            self.immutable(
                self.path("snapshots", snapshot.snapshot_id + ".json"),
                snapshot.model_dump_json().encode(),
            )
            self.fault("write_manifest")
            name = uuid4().hex + ".json"
            payload = encoded(state)
            self.immutable(self.path("manifests", name), payload)
            pointer = encoded({"manifest": name, "sha256": sha256(payload).hexdigest()})
            self._write_synced(temporary, pointer)
            for directory in (*directories, self.root):
                self._sync_directory(directory)
            self.fault("replace_current")
            self.check(current)
            os.replace(temporary, current)
            # Publication is the commit point. Do not raise a false rollback after it.
            try:
                self._sync_directory(self.root)
            except OSError:
                pass
        except (OSError, ValueError, TypeError):
            raise ValueError("PERSISTENCE_FAILED") from None
        finally:
            if temporary.exists():
                temporary.unlink()
