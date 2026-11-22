"""Explicit source selection and bounded, no-symlink local byte reads."""

import os
import stat
from pathlib import Path


def lexical(path: Path) -> Path:
    """Make absolute without resolving links or erasing traversal components."""
    return path if path.is_absolute() else Path.cwd() / path


def authorize(path: Path, root: Path, selected: frozenset[Path]) -> Path:
    """Check selection and every existing component before any source read."""
    path = lexical(path)
    if ".." in path.parts or ".." in root.parts or path not in selected:
        raise ValueError("SOURCE_NOT_AUTHORIZED")
    if not path.is_relative_to(root) or path == root:
        raise ValueError("SOURCE_NOT_AUTHORIZED")
    for component in (path, *path.parents):
        if component.is_symlink():
            raise ValueError("SOURCE_NOT_AUTHORIZED")
    return path


def read_selected(path: Path, limit: int) -> bytes:
    """Walk absolute components using no-follow directory descriptors.

    No directory scanning occurs. Descriptor traversal also rejects links swapped
    into a checked path before opening it. This is not an OS sandbox.
    """
    directory = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in path.parts[1:-1]:
            child = os.open(
                part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory
            )
            os.close(directory)
            directory = child
        descriptor = os.open(
            path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory
        )
        with os.fdopen(descriptor, "rb") as source:
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                raise ValueError("SOURCE_NOT_AUTHORIZED")
            return source.read(limit + 1)
    finally:
        os.close(directory)
