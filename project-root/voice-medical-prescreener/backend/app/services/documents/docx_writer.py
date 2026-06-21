"""DOCX writer (python-docx).

Builds a Word document for one completed session: a metadata header, the verbatim
RAW transcript, and the SEPARATE corrected transcript. Pure Python, so it runs the
same on the Windows desktop and the Arch laptop with no Word/LibreOffice installed.

Bangla note: Bengali is a *complex script*, so we set the font on both the Latin
(``w:ascii``/``w:hAscii``) and complex-script (``w:cs``) slots of the Normal style.
That makes the saved file request a Bengali-capable font (Noto Sans Bengali, with
Nikosh / Vrinda as common fallbacks) regardless of the reader's default. We only
set the rendering font — the patient's words (rule #1) are written exactly as stored.
"""

from __future__ import annotations

from io import BytesIO

from docx import Document as DocxDocument
from docx.oxml.ns import qn
from docx.shared import Pt

from backend.app.db.models import Utterance
from backend.app.services.documents.base import DocumentWriter

# First name is the primary request; readers fall back to whatever Bengali font
# they have. All are common on Windows/Linux or free to install.
BENGALI_FONT = "Noto Sans Bengali"


def _apply_bengali_font(style, font_name: str = BENGALI_FONT, size_pt: int = 11) -> None:
    """Set ``font_name`` on a style for Latin AND complex (Bengali) script slots."""
    style.font.name = font_name
    style.font.size = Pt(size_pt)
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = rpr.makeelement(qn("w:rFonts"), {})
        rpr.append(rfonts)
    for slot in ("w:ascii", "w:hAnsi", "w:cs"):
        rfonts.set(qn(slot), font_name)


def _fmt_dt(value) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S UTC") if value else "—"


class DocxWriter(DocumentWriter):
    format = "docx"

    def render(self, utterance: Utterance) -> bytes:
        doc = DocxDocument()
        _apply_bengali_font(doc.styles["Normal"])

        doc.add_heading("Voice Medical Pre-Screener — Session Transcript", level=1)

        # --- metadata header ---
        meta = [
            ("Session ID", str(utterance.id)),
            ("Source", utterance.source or "—"),
            ("STT provider", utterance.stt_provider or "—"),
            ("Correction", f"{utterance.correction_provider or '—'} / {utterance.correction_model or '—'}"),
            ("Recorded at", _fmt_dt(utterance.created_at)),
            ("Corrected at", _fmt_dt(utterance.corrected_at)),
        ]
        table = doc.add_table(rows=0, cols=2)
        table.style = "Light List Accent 1"
        for label, value in meta:
            row = table.add_row().cells
            row[0].text = label
            row[1].text = value

        # --- RAW (verbatim, never edited — rule #1) ---
        doc.add_heading("Raw transcript (verbatim)", level=2)
        doc.add_paragraph(utterance.raw_text)

        # --- CORRECTED (separate field) ---
        doc.add_heading("Corrected transcript", level=2)
        corrected = utterance.corrected_text
        if corrected:
            doc.add_paragraph(corrected)
        else:
            note = doc.add_paragraph("(not corrected)")
            note.runs[0].italic = True

        buffer = BytesIO()
        doc.save(buffer)
        return buffer.getvalue()
