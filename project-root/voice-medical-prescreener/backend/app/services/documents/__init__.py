"""Document export service (derived artifacts: .docx now, PDF later).

The DB stays the source of truth; this layer turns a stored session into a
downloadable file. It is structured like ``services/correction/``: a small
interface (``DocumentWriter``), swappable implementations, and a ``build_writer``
seam — so adding a PDF writer or a cloud storage backend never ripples outward.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from backend.app.db import repository as repo
from backend.app.db.models import Document, Utterance
from backend.app.services.documents.base import DocumentKind, DocumentWriter
from backend.app.services.documents.docx_writer import DocxWriter
from backend.app.services.documents.storage import DocumentStorage, build_storage

__all__ = [
    "DocumentKind",
    "DocumentWriter",
    "DocxWriter",
    "build_writer",
    "generate_session_document",
]

_WRITERS: dict[str, type[DocumentWriter]] = {
    "docx": DocxWriter,
    # "pdf": PdfWriter,  # future — same interface, drops in here
}


def build_writer(doc_format: str = "docx") -> DocumentWriter:
    """Return a writer for ``doc_format`` (raises ValueError if unknown)."""
    writer_cls = _WRITERS.get(doc_format.lower().strip())
    if writer_cls is None:
        raise ValueError(
            f"Unknown document format '{doc_format}'. Expected one of: "
            f"{', '.join(sorted(_WRITERS))}."
        )
    return writer_cls()


def _download_name(utterance: Utterance, kind: str, doc_format: str) -> str:
    """Human-facing filename (the on-disk name is the opaque UUID)."""
    stamp = utterance.created_at.strftime("%Y%m%d") if utterance.created_at else "session"
    return f"{kind}-session-{utterance.id}-{stamp}.{doc_format}"


def generate_session_document(
    db: Session,
    utterance: Utterance,
    *,
    kind: DocumentKind,
    doc_format: str = "docx",
    storage: DocumentStorage | None = None,
) -> Document:
    """Render the ``kind`` ("raw" | "corrected") side of ``utterance`` to a file,
    persist it via storage, and record the row.

    Raw and corrected are generated independently, so each call produces its own
    file + row. Returns the created Document. Raises on failure — callers that must
    not fail the main request (e.g. the correction route) should wrap best-effort.
    """
    storage = storage or build_storage()
    writer = build_writer(doc_format)

    doc_id = str(uuid.uuid4())
    rel_path = f"{doc_id}.{writer.format}"

    storage.save_bytes(rel_path, writer.render(utterance, kind=kind))

    return repo.create_document(
        db,
        utterance_id=utterance.id,
        filename=_download_name(utterance, kind, writer.format),
        rel_path=rel_path,
        kind=kind,
        doc_format=writer.format,
        doc_id=doc_id,
    )
