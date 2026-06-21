"""Storage abstraction for generated document files.

Today this writes to the local filesystem under a configurable base directory
(``settings.resolved_documents_dir``). Everything else in the app talks only to
this small interface, so swapping in S3 / MinIO later is a one-file change and the
call sites (the docx writer, the download route) never need to know.

Paths handed around are RELATIVE (e.g. "ab12.docx"); the base directory is resolved
here. That keeps the stored DB rows portable when the base dir moves.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from backend.app.core.config import Settings, get_settings


class DocumentStorage(ABC):
    @abstractmethod
    def save_bytes(self, rel_path: str, data: bytes) -> None:
        """Persist ``data`` at ``rel_path`` (relative to the storage root)."""
        raise NotImplementedError

    @abstractmethod
    def resolve(self, rel_path: str) -> Path:
        """Return a local filesystem path for ``rel_path`` (for FileResponse)."""
        raise NotImplementedError

    @abstractmethod
    def exists(self, rel_path: str) -> bool:
        raise NotImplementedError


class FilesystemStorage(DocumentStorage):
    """Writes files under a single base directory, created on demand."""

    def __init__(self, base_dir: Path) -> None:
        self._base = base_dir

    def _full(self, rel_path: str) -> Path:
        return self._base / rel_path

    def save_bytes(self, rel_path: str, data: bytes) -> None:
        full = self._full(rel_path)
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_bytes(data)

    def resolve(self, rel_path: str) -> Path:
        return self._full(rel_path)

    def exists(self, rel_path: str) -> bool:
        return self._full(rel_path).is_file()


def build_storage(settings: Settings | None = None) -> DocumentStorage:
    """Build the configured storage backend (filesystem today)."""
    settings = settings or get_settings()
    return FilesystemStorage(settings.resolved_documents_dir)
