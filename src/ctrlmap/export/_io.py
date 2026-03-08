"""Shared I/O utilities for ctrlmap export formatters.

Centralizes the atomic-write helper that was previously duplicated
across ``csv_formatter``, ``markdown_formatter``, and ``oscal_formatter``.
"""

from __future__ import annotations

import tempfile
from pathlib import Path


def atomic_write(path: Path, content: str) -> None:
    """Write content to a file atomically via temp file + rename.

    Creates parent directories if they don't exist.  Uses a temporary
    file in the same directory as the target to ensure the rename is
    atomic on POSIX filesystems.

    Args:
        path: Destination file path.
        content: UTF-8 string content to write.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        suffix=".tmp",
        delete=False,
    ) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    tmp_path.rename(path)
