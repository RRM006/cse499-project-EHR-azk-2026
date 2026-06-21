"""Document routes: list generated session exports and download them.

Documents are derived artifacts (see services/documents). The DB row records what
was generated; the bytes live in the configured storage. ``/download`` streams the
file back with the right Word media type so the browser saves a .docx.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.app.db import repository as repo
from backend.app.db.database import get_db
from backend.app.schemas.document import DocumentOut
from backend.app.services.documents.storage import build_storage

router = APIRouter(prefix="/api/documents", tags=["documents"])

_MEDIA_TYPES = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
}


@router.get("", response_model=list[DocumentOut])
def list_documents(limit: int = 50, db: Session = Depends(get_db)) -> list[DocumentOut]:
    return repo.list_documents(db, limit=limit)


@router.get("/{document_id}/download")
def download_document(document_id: str, db: Session = Depends(get_db)) -> FileResponse:
    document = repo.get_document(db, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")

    path = build_storage().resolve(document.rel_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Document file is missing from storage")

    media_type = _MEDIA_TYPES.get(document.format, "application/octet-stream")
    return FileResponse(path, media_type=media_type, filename=document.filename)
