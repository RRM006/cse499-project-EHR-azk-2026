"""Offline checks for the .docx export writer.

These never touch the network or a real DB: they build a writer over a plain
in-memory ``Utterance`` and inspect the produced bytes with python-docx. The key
guard is rule #1 — the RAW text must appear in the document verbatim.
"""

from datetime import datetime, timezone
from io import BytesIO

from docx import Document as DocxDocument

from backend.app.db.models import Utterance
from backend.app.services.documents import build_writer
from backend.app.services.documents.docx_writer import DocxWriter


def _sample_utterance() -> Utterance:
    utt = Utterance(
        raw_text="ami onek jor onuvob korchi   ",  # trailing spaces are part of raw
        corrected_text="আমি অনেক জ্বর অনুভব করছি",
        source="mic",
        stt_provider="browser_webspeech",
        correction_provider="gemini",
        correction_model="gemini-flash-latest",
    )
    utt.id = 12
    utt.created_at = datetime(2026, 6, 21, 9, 30, tzinfo=timezone.utc)
    utt.corrected_at = datetime(2026, 6, 21, 9, 31, tzinfo=timezone.utc)
    return utt


def _all_text(docx_bytes: bytes) -> str:
    doc = DocxDocument(BytesIO(docx_bytes))
    parts = [p.text for p in doc.paragraphs]
    for table in doc.tables:
        for row in table.rows:
            parts.extend(cell.text for cell in row.cells)
    return "\n".join(parts)


def test_build_writer_returns_docx_writer():
    writer = build_writer("docx")
    assert isinstance(writer, DocxWriter)
    assert writer.format == "docx"


def test_render_produces_a_valid_docx_with_raw_and_corrected():
    utt = _sample_utterance()
    data = DocxWriter().render(utt)

    # Valid enough that python-docx can re-open it.
    text = _all_text(data)

    assert utt.raw_text in text  # RAW verbatim (rule #1), spaces and all
    assert utt.corrected_text in text  # the separate corrected field
    assert str(utt.id) in text  # session id in the metadata header
    assert "browser_webspeech" in text


def test_render_handles_missing_correction():
    utt = _sample_utterance()
    utt.corrected_text = None
    text = _all_text(DocxWriter().render(utt))
    assert utt.raw_text in text
    assert "(not corrected)" in text


def test_build_writer_rejects_unknown_format():
    import pytest

    with pytest.raises(ValueError):
        build_writer("xlsx")
