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
from backend.app.db.models import Document, Patient, Prescription, Utterance, Visit
from backend.app.services.documents.base import DocumentKind, DocumentWriter
from backend.app.services.documents.docx_writer import DocxWriter
from backend.app.services.documents.storage import DocumentStorage, build_storage
from backend.app.services.documents.visit_docx import (
    VISIT_DOCUMENT_FORMATS,
    VISIT_DOCUMENT_KINDS,
    render_prescription,
    render_visit_summary_report,
    render_visit_transcript,
)

__all__ = [
    "DocumentKind",
    "DocumentWriter",
    "DocxWriter",
    "VISIT_DOCUMENT_KINDS",
    "build_writer",
    "generate_prescription_document",
    "generate_session_document",
    "generate_visit_document",
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


def generate_visit_document(
    db: Session,
    visit: Visit,
    *,
    kind: str,
    storage: DocumentStorage | None = None,
) -> Document:
    """Render a VISIT-grain export (rev 0010): the full raw ``transcript`` (KIOSK-4),
    the staff ``summary_report`` (MEDIC-7), or the ``ehr_bundle`` FHIR R4 document
    (S38 / B1). Stores the file and records a row with ``visit_id`` set and
    ``utterance_id`` NULL.

    Every kind is LOCAL — no API call, no quota. ``summary_report`` assembles a fresh
    M12 report every time and ``ehr_bundle`` is assembled fresh per request too, so
    both always reflect staff edits and overrides made after any earlier export.
    """
    if kind not in VISIT_DOCUMENT_KINDS:
        raise ValueError(
            f"Unknown visit document kind '{kind}'. Expected one of: "
            f"{', '.join(VISIT_DOCUMENT_KINDS)}."
        )

    # Local imports: keep the module import-light and avoid a services cycle.
    from backend.app.db.repository_visits import list_visit_utterances
    from backend.app.services.ehr_export import render_fhir_bundle
    from backend.app.services.report import generate_report

    patient = db.get(Patient, visit.patient_id) if visit.patient_id else None
    if kind == "transcript":
        utterances = list_visit_utterances(db, visit_id=visit.id)
        data = render_visit_transcript(visit, patient, utterances)
    elif kind == "ehr_bundle":
        # S38 (B1): NOT a .docx — a FHIR R4 document Bundle as JSON. It is assembled
        # from rows that already exist and writes nothing (services/ehr_export).
        data = render_fhir_bundle(db, visit)
    else:  # summary_report
        # Always assemble FRESH (local + free): the download must reflect staff
        # field edits and risk overrides made after any earlier report (MEDIC-7).
        # Report rows are append-only, so history is preserved, not replaced.
        report = generate_report(db, visit)
        data = render_visit_summary_report(visit, patient, report.sections or {})

    storage = storage or build_storage()
    doc_format = VISIT_DOCUMENT_FORMATS[kind]
    doc_id = str(uuid.uuid4())
    rel_path = f"{doc_id}.{doc_format}"
    storage.save_bytes(rel_path, data)

    stamp = visit.started_at.strftime("%Y%m%d") if visit.started_at else "visit"
    # S36 (ADR-0057), Finding 6: the transcript kind is downloaded automatically at the
    # end of every screening now, so its NAME has to carry the one distinction this
    # project is built on. "transcript" is ambiguous once a corrected text exists;
    # "raw-transcript" says which of the two a doctor is holding without opening it.
    # The stored `kind` is unchanged — this is the human-facing download name only.
    # Deliberately carries no name and no phone number: a filename ends up in a
    # downloads folder, an email subject and a file listing (rule #4).
    # S38: "ehr_bundle" says nothing about what is inside to someone holding the file,
    # so the download is named for the standard it implements.
    _LABELS = {"transcript": "raw-transcript", "ehr_bundle": "ehr-fhir-r4"}
    label = _LABELS.get(kind, kind)
    return repo.create_document(
        db,
        utterance_id=None,
        visit_id=visit.id,
        filename=f"{label}-visit-{visit.uuid[:8]}-{stamp}.{doc_format}",
        rel_path=rel_path,
        kind=kind,
        doc_format=doc_format,
        doc_id=doc_id,
    )


def generate_prescription_document(
    db: Session,
    visit: Visit,
    *,
    doctor_id: int,
    payload: dict,
    storage: DocumentStorage | None = None,
) -> Prescription:
    """DOCTOR-6: render the doctor's prescription ``payload`` to a .docx, store it,
    and persist a ``prescriptions`` row linked to that document.

    Self-contained + LOCAL — no API call, and the Diagnosis is whatever the doctor
    typed (never AI-filled; rule #2). A new prescription + document is created per
    Submit (documents are append-only). The caller commits/audits.
    """
    data = render_prescription(payload)

    storage = storage or build_storage()
    doc_id = str(uuid.uuid4())
    rel_path = f"{doc_id}.docx"
    storage.save_bytes(rel_path, data)

    stamp = visit.started_at.strftime("%Y%m%d") if visit.started_at else "visit"
    document = repo.create_document(
        db,
        utterance_id=None,
        visit_id=visit.id,
        filename=f"prescription-visit-{visit.uuid[:8]}-{stamp}.docx",
        rel_path=rel_path,
        kind="prescription",
        doc_format="docx",
        doc_id=doc_id,
    )

    prescription = Prescription(
        visit_id=visit.id, doctor_id=doctor_id, payload=payload, document_id=document.id
    )
    db.add(prescription)
    db.flush()  # assign prescription.id; the route commits
    return prescription
