"""Module E append-only history store. FR-E-01/02, INV-05/08, SEC-01.

Records live as one ``<record_id>.json`` file each. Publishing is exclusive and
atomic: serialize, write a sibling temp file, fsync, then link into place so an
interrupted or failing write leaves the previous history intact and never writes
outside the history root. Symlinked roots and symlinked record files are refused.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Final

from .record import InvalidRecord, RecordConflict, ResearchRecord, parse_record

__all__ = ["HistoryStore"]

# Serialized bytes -> write them atomically. Injected only for deterministic
# offline failure tests; the default implementation is ``_atomic_write``.
AtomicWriter = Callable[[Path, bytes], None]

_SUFFIX: Final = ".json"


def _atomic_write(target: Path, data: bytes) -> None:
    """INV-05/08: temp file + fsync + exclusive publish; no partial record ever visible."""
    parent = target.parent
    handle, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temp_path, target)
        except FileExistsError:
            raise RecordConflict(f"history record already exists: {target.name}") from None
        except (OSError, NotImplementedError):
            # SEC-01, INV-08: fail closed. Publishing by copying would expose a
            # partial/corrupt record if the second write or fsync fails, so an
            # unsupported hard link propagates the original error and the temp
            # file is removed below without ever touching the target.
            raise
    finally:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass


class HistoryStore:
    """Append-only research history rooted at a single directory."""

    def __init__(self, root: str | Path, *, atomic_writer: AtomicWriter | None = None) -> None:
        self._root = Path(root)
        self._atomic_writer = atomic_writer

    @property
    def root(self) -> Path:
        """The configured history root; never resolved through a symlink."""
        return self._root

    def _checked_root(self) -> Path:
        """SEC-01: refuse a symlinked root so writes cannot escape the history boundary."""
        root = self._root
        if root.is_symlink():
            raise InvalidRecord("history root cannot be a symbolic link")
        if root.exists() and not root.is_dir():
            raise InvalidRecord("history root must be a directory")
        try:
            root.mkdir(parents=False, exist_ok=True)
        except OSError:
            raise InvalidRecord("history root cannot be created") from None
        if root.is_symlink():
            raise InvalidRecord("history root cannot be a symbolic link")
        return root

    @staticmethod
    def _target_for(root: Path, record_id: str) -> Path:
        """Record ids are UUID-shaped, so no separator, drive or dot-dot can survive."""
        if not _is_record_id(record_id):
            raise InvalidRecord("record id is not a safe history file name")
        return root / f"{record_id}{_SUFFIX}"

    def save(self, record: ResearchRecord) -> Path:
        """Persist a validated record once; an existing id is a conflict, never an overwrite."""
        root = self._checked_root()
        target = self._target_for(root, record.record_id)
        if target.is_symlink() or target.exists():
            raise RecordConflict(f"history record already exists: {target.name}")
        data = record.model_dump_json(indent=None).encode("utf-8")
        writer = self._atomic_writer or _atomic_write
        try:
            writer(target, data)
        except RecordConflict:
            raise
        except OSError:
            raise
        return target

    def load(self, record_id: str) -> ResearchRecord:
        """FR-E-01: read back exactly the saved package; never repair or substitute."""
        root = self._checked_root()
        target = self._target_for(root, record_id)
        if target.is_symlink():
            raise InvalidRecord("history record cannot be a symbolic link")
        try:
            raw = target.read_bytes()
        except FileNotFoundError:
            raise InvalidRecord(f"history record not found: {record_id}") from None
        except OSError:
            raise InvalidRecord(f"history record unreadable: {record_id}") from None
        record = parse_record(raw)
        if record.record_id != record_id:
            raise InvalidRecord("history record id does not match its file name")
        return record

    def list_records(self) -> tuple[ResearchRecord, ...]:
        """INV-05: enumerate readable records newest first; unsafe entries are skipped."""
        root = self._checked_root()
        found: list[ResearchRecord] = []
        try:
            entries = sorted(root.iterdir())
        except OSError:
            raise InvalidRecord("history root is unreadable") from None
        for entry in entries:
            if entry.suffix != _SUFFIX or entry.name.startswith("."):
                continue
            if entry.is_symlink() or not entry.is_file():
                continue
            record_id = entry.name[: -len(_SUFFIX)]
            if not _is_record_id(record_id):
                continue
            try:
                found.append(self.load(record_id))
            except InvalidRecord:
                continue
        found.sort(key=lambda item: (item.saved_at, item.record_id), reverse=True)
        return tuple(found)


def _is_record_id(value: str) -> bool:
    """Mirror record.RecordId geometry without trusting caller-supplied paths."""
    if len(value) != 36:
        return False
    groups = (8, 4, 4, 4, 12)
    parts = value.split("-")
    if len(parts) != len(groups):
        return False
    allowed = set("0123456789abcdef")
    return all(
        len(part) == size and all(char in allowed for char in part)
        for part, size in zip(parts, groups, strict=True)
    )
