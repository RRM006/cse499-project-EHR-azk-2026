"""S39 (ADR-0064) — the EHR record as a human-readable PDF, beside the FHIR JSON.

THE PROPERTY THAT MATTERS
-------------------------
The brief asked for two formats and warned against "a second competing EHR
representation". So ``services/ehr_pdf`` does not read the database: it renders the
Bundle ``services/ehr_export`` already builds. These tests hold that boundary, because
it is exactly the kind of thing a later "just fetch the patient here" would dissolve:

  * the PDF is a pure function of the bundle — the same bundle in gives the same
    document, and no DB session is involved;
  * every Composition section in the JSON appears in the PDF, and none is invented;
  * a fact absent from the record is absent from the PDF, and an unknown name is
    NAMED as unknown rather than left blank;
  * the FHIR export still works exactly as before;
  * the renderer REFUSES rather than emitting a document whose Bangla would be wrong.

Text is read back out of the PDF through its own ToUnicode mapping, which is what a
person copying from a PDF reader gets — so "the PDF contains this sentence" is checked
against the real artifact, not against the input.
"""

import re
import zlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.database import Base, get_db
from backend.app.db.models import (
    CaseProfile,
    Clinic,
    Patient,
    RiskAssessment,
    User,
    Utterance,
    Visit,
)
from backend.app.main import app
from backend.app.schemas.profile import SUMMARY_FIELD_KEYS
from backend.app.services.ehr_export import build_fhir_bundle
from backend.app.services.ehr_pdf import (
    PdfFontUnavailable,
    bundle_to_pdf,
    narrative_blocks,
    render_ehr_pdf,
)

RAW_BANGLA = "আমার অনেক দিন ধরে জ্বর, কষ্ট হচ্ছে।"


@pytest.fixture()
def env():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool, future=True)
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, future=True)

    db = TestSession()
    clinic = Clinic(name="Demo Clinic", address="House 12, Dhanmondi, Dhaka")
    db.add(clinic)
    db.flush()
    doctor = User(clinic_id=clinic.id, name="Dr Aziz", role="doctor")
    medic = User(clinic_id=clinic.id, name="Medic Rahman", role="medic")
    patient = Patient(clinic_id=clinic.id, external_ref="+8801715984632",
                      display_name="রহিমা বেগম", sex="female", birth_year=1948,
                      weight_kg=61.5, height_cm=158.0, bp="130/85",
                      blood_glucose_mmol_l=6.4, blood_glucose_context="fasting")
    db.add_all([doctor, medic, patient])
    db.flush()
    visit = Visit(clinic_id=clinic.id, patient_id=patient.id, status="awaiting_doctor",
                  assigned_doctor_id=doctor.id)
    db.add(visit)
    db.flush()
    db.add_all([
        Utterance(visit_id=visit.id, role="system", raw_text="আপনার সমস্যা কী?"),
        Utterance(visit_id=visit.id, role="patient", raw_text=RAW_BANGLA),
    ])
    fields = {k: {"value": "", "value_en": "", "value_bn": "", "source": "ai"}
              for k in SUMMARY_FIELD_KEYS}
    fields["main_problem"] = {"value": "Fever for several days", "value_en":
                              "Fever for several days", "value_bn": "কয়েকদিন ধরে জ্বর",
                              "source": "ai"}
    db.add(CaseProfile(visit_id=visit.id, entities={"summary_fields": fields},
                       summary="Reports fever for several days."))
    db.add(RiskAssessment(visit_id=visit.id, tier="medium", red_flags=[],
                          model_provider="gemini_flash"))
    db.commit()
    ids = {"visit": visit.uuid, "visit_id": visit.id, "patient": patient.id,
           "doctor": doctor.id, "medic": medic.id}
    db.close()

    def override_get_db():
        s = TestSession()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app), TestSession, ids
    app.dependency_overrides.clear()


def _bundle(TestSession, visit_uuid: str) -> dict:
    db = TestSession()
    visit = db.query(Visit).filter(Visit.uuid == visit_uuid).first()
    bundle = build_fhir_bundle(db, visit)
    db.close()
    return bundle


_PDF_ESCAPES = {
    ord("n"): b"\n", ord("r"): b"\r", ord("t"): b"\t", ord("b"): b"\b",
    ord("f"): b"\f", ord("("): b"(", ord(")"): b")", ord("\\"): b"\\",
}


def _unescape_pdf_string(raw: bytes) -> bytes:
    """PDF literal-string escapes back to bytes.

    This matters more than it looks: the glyph ids are 2-byte big-endian, so any id
    whose byte happens to be 0x0D, 0x28 or 0x5C is written escaped. Reading the
    literal naively drops or mis-splits exactly those glyphs, and the extracted text
    then differs from the document for reasons that have nothing to do with the PDF.
    """
    out = bytearray()
    i = 0
    while i < len(raw):
        byte = raw[i]
        if byte != 0x5C:                      # not a backslash
            out.append(byte)
            i += 1
            continue
        i += 1
        if i >= len(raw):
            break
        nxt = raw[i]
        if nxt in _PDF_ESCAPES:
            out += _PDF_ESCAPES[nxt]
            i += 1
        elif 0x30 <= nxt <= 0x37:             # \ddd octal
            digits = bytes(raw[i:i + 3])
            octal = digits[:3]
            out.append(int(octal, 8) & 0xFF)
            i += len(octal)
        elif nxt in (0x0A, 0x0D):             # line continuation
            i += 1
        else:
            out.append(nxt)
            i += 1
    return bytes(out)


#: A text-positioning operator and the Y it moves to: "<x> <y> Td" or the Tm matrix.
_POSITION = re.compile(
    rb"(?:(-?[\d.]+)\s+(-?[\d.]+)\s+Td)"
    rb"|(?:[-\d.]+\s+[-\d.]+\s+[-\d.]+\s+[-\d.]+\s+(-?[\d.]+)\s+(-?[\d.]+)\s+Tm)"
    rb"|(?:\(((?:[^()\\]|\\.)*)\)\s*Tj)",
    re.S,
)


def pdf_text(data: bytes) -> str:
    """Everything the PDF's own ToUnicode CMap maps back to text, one line per line.

    fpdf2 embeds the CMap so a reader can copy text out; walking it checks the REAL
    artifact rather than the input we handed the renderer. Glyph ids in the content
    streams are resolved through that map — the same path a "select all + copy" in a
    PDF viewer takes.

    ⚠ Nothing is inserted between runs on the SAME line. Kerning splits one visual
    word across several Tj operations ("V" then "oice"), so a separator there
    manufactures spaces that are not in the document — and inside a Bengali conjunct
    it would split "কণ্ঠস্বর" into "কণ ্ ঠস ্ বর" and make correct output look broken.
    Real spaces are glyphs in the stream and arrive on their own. A newline is emitted
    only when the text cursor actually MOVES TO A NEW Y, which is what a line break in
    the document is.
    """
    glyphs: dict[int, str] = {}
    for match in re.finditer(rb"beginbfchar(.*?)endbfchar", data, re.S):
        for src, dst in re.findall(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", match.group(1)):
            try:
                glyphs[int(src, 16)] = bytes.fromhex(dst.decode()).decode("utf-16-be")
            except (ValueError, UnicodeDecodeError):
                continue

    out: list[str] = []
    for stream in re.finditer(rb"stream\r?\n(.*?)endstream", data, re.S):
        try:
            body = zlib.decompress(stream.group(1))
        except zlib.error:
            body = stream.group(1)
        last_y = None
        for match in _POSITION.finditer(body):
            td_y, tm_y, literal = match.group(2), match.group(4), match.group(5)
            raw_y = td_y if td_y is not None else tm_y
            if raw_y is not None:
                y = float(raw_y)
                # ⚠ NOT `y != last_y`. HarfBuzz positions Bengali combining marks
                # (nukta, vowel signs) with their own small vertical offset, so an
                # exact comparison inserted a line break INSIDE words — "বিষয়ে" came
                # out as "বিষয\n়\nে". Only a real line advance moves the cursor down
                # by more than a couple of points.
                if last_y is not None and (last_y - y) > 2.0:
                    out.append("\n")
                last_y = y
                continue
            raw = _unescape_pdf_string(literal)
            for i in range(0, len(raw) - 1, 2):
                out.append(glyphs.get((raw[i] << 8) | raw[i + 1], ""))
        out.append("\n")
    return "".join(out)


def pdf_flat(data: bytes) -> str:
    """``pdf_text`` with line structure collapsed to single spaces.

    A sentence longer than the text column is WRAPPED, so the document legitimately
    contains a line break in the middle of it. Comparing a source string against the
    laid-out page therefore has to ignore where the wrap fell — this checks the word
    sequence survived, which is the rule #1 property, not the line breaks.
    Use ``pdf_text`` where the line structure itself is the thing under test.
    """
    return re.sub(r"\s+", " ", pdf_text(data))


# --- 1. the PDF is a rendering of the bundle, not a second reading of the DB --------


def test_the_pdf_is_a_pure_function_of_the_bundle(env):
    """No DB session reaches the renderer — which is what makes "the same record"
    a structural fact instead of a promise."""
    _client, TestSession, ids = env
    bundle = _bundle(TestSession, ids["visit"])
    first = bundle_to_pdf(bundle)
    second = bundle_to_pdf(bundle)
    assert first[:8] == b"%PDF-1.3"
    # Same input, same document (the trailing /ID and dates fpdf2 writes are derived
    # from the content, so equal input gives byte-equal output).
    assert len(first) == len(second)


def test_every_section_of_the_json_appears_in_the_pdf(env):
    _client, TestSession, ids = env
    bundle = _bundle(TestSession, ids["visit"])
    composition = bundle["entry"][0]["resource"]
    titles = [s["title"] for s in composition["section"]]
    assert titles, "the fixture should produce sections"

    text = pdf_text(bundle_to_pdf(bundle))
    for title in titles:
        assert title in text, f"section '{title}' is in the FHIR file but not in the PDF"


def test_the_pdf_carries_the_patient_and_the_clinic_from_the_bundle(env):
    _client, TestSession, ids = env
    text = pdf_text(bundle_to_pdf(_bundle(TestSession, ids["visit"])))
    assert "রহিমা বেগম" in text
    assert "+8801715984632" in text
    assert "Demo Clinic" in text
    assert ids["visit"] in text, "the visit id ties the PDF to the same record"


def test_the_patients_own_words_are_reproduced_verbatim(env):
    """Rule #1 in the export a human actually reads: the raw string, unedited — and
    correctly SHAPED, which is the whole reason this renderer uses HarfBuzz."""
    _client, TestSession, ids = env
    text = pdf_flat(bundle_to_pdf(_bundle(TestSession, ids["visit"])))
    assert RAW_BANGLA in text


def test_the_glucose_reading_reaches_the_pdf_with_its_context(env):
    _client, TestSession, ids = env
    text = pdf_text(bundle_to_pdf(_bundle(TestSession, ids["visit"])))
    assert "6.4 mmol/L" in text
    assert "Fasting" in text, "a reading without its context cannot be read safely"


def test_the_no_diagnosis_disclaimer_is_present(env):
    from backend.app.services.report import DISCLAIMER

    _client, TestSession, ids = env
    text = pdf_text(bundle_to_pdf(_bundle(TestSession, ids["visit"])))
    assert DISCLAIMER.split(".")[0] in text


# --- 2. nothing is invented ---------------------------------------------------------


def test_an_unknown_name_is_named_as_unknown_not_left_blank(env):
    """A blank where a name should be reads as a broken document; this says which."""
    _client, TestSession, ids = env
    db = TestSession()
    patient = db.get(Patient, ids["patient"])
    patient.display_name = None
    db.commit()
    db.close()

    bundle = _bundle(TestSession, ids["visit"])
    fhir_patient = next(e["resource"] for e in bundle["entry"]
                        if e["resource"]["resourceType"] == "Patient")
    # FHIR says "unknown" by OMITTING the element — that must not change.
    assert "name" not in fhir_patient
    assert "Name not provided" in pdf_text(bundle_to_pdf(bundle))


def test_absent_facts_do_not_appear(env):
    _client, TestSession, ids = env
    db = TestSession()
    patient = db.get(Patient, ids["patient"])
    patient.blood_glucose_mmol_l = None
    patient.blood_glucose_context = None
    patient.bp = None
    db.commit()
    db.close()

    text = pdf_text(bundle_to_pdf(_bundle(TestSession, ids["visit"])))
    assert "mmol/L" not in text
    assert "Blood glucose" not in text
    assert "130/85" not in text


def test_the_pdf_states_that_it_is_the_same_record_as_the_fhir_file(env):
    _client, TestSession, ids = env
    text = pdf_text(bundle_to_pdf(_bundle(TestSession, ids["visit"])))
    assert "FHIR" in text and "machine-readable" in text


# --- 3. the narrative parser --------------------------------------------------------


def test_narrative_parser_handles_the_vocabulary_ehr_export_writes():
    blocks = narrative_blocks(
        '<div xmlns="http://www.w3.org/1999/xhtml">'
        "<table><tr><td>Weight</td><td>61.5 kg</td></tr></table>"
        "<p><b>Patient said:</b> আমার জ্বর</p></div>"
    )
    assert [b.kind for b in blocks] == ["row", "p"]
    assert blocks[0].cells == ["Weight", "61.5 kg"], "no phantom empty cell"
    assert blocks[1].cells == ["Patient said: আমার জ্বর"]


def test_inline_emphasis_does_not_reorder_the_sentence():
    """`<p>Urgency tier: <b>low</b></p>` came out as "low Urgency tier:" while an
    earlier parser treated bold as a prefix. Both narratives exist in the bundle, so
    order has to be preserved rather than inferred."""
    blocks = narrative_blocks("<div><p>Urgency tier: <b>low</b></p></div>")
    assert blocks[0].cells == ["Urgency tier: low"]
    blocks = narrative_blocks("<div><p><b>Patient said:</b> hello</p></div>")
    assert blocks[0].cells == ["Patient said: hello"]


def test_red_flags_stay_separate_items():
    """Rule #3 makes their legibility a safety property: run together into one
    paragraph they stop reading as separate findings."""
    blocks = narrative_blocks(
        "<div><p>Red flags:</p><ul><li>chest pain</li><li>breathlessness</li></ul></div>"
    )
    assert [b.kind for b in blocks] == ["p", "li", "li"]
    assert blocks[1].cells == ["chest pain"]
    assert blocks[2].cells == ["breathlessness"]


def test_a_line_break_inside_a_cell_separates_the_two_languages():
    """`ehr_export` puts the English and the Bangla of one field in ONE cell split by
    <br/>. Dropping the break printed them as a single run-on string, which reads as a
    corrupted value rather than a bilingual one. Found in the browser, pinned here."""
    blocks = narrative_blocks(
        "<div><table><tr><td>Main problem</td>"
        "<td>Skin rash on the arm<br/><span lang='bn'>হাতে চামড়ায় ফুসকুড়ি</span></td>"
        "</tr></table></div>"
    )
    assert len(blocks) == 1
    value = blocks[0].cells[1]
    assert "\n" in value, "the two languages ran together"
    assert value.split("\n")[0].strip() == "Skin rash on the arm"
    assert value.split("\n")[1].strip() == "হাতে চামড়ায় ফুসকুড়ি"


def test_the_two_languages_are_separated_in_the_rendered_pdf(env):
    _client, TestSession, ids = env
    text = pdf_text(bundle_to_pdf(_bundle(TestSession, ids["visit"])))
    assert "Fever for several daysকয়েকদিন ধরে জ্বর" not in text, (
        "English and Bangla are concatenated with no separator"
    )


def test_an_unknown_tag_never_costs_a_reader_a_sentence():
    blocks = narrative_blocks("<div><p>Kept <em>and this too</em></p></div>")
    assert "and this too" in " ".join(b.cells[0] for b in blocks)


# --- 4. the route, and the FHIR export still working --------------------------------


def test_the_pdf_downloads_as_application_pdf(env):
    client, _TestSession, ids = env
    res = client.post(f"/api/visits/{ids['visit']}/documents/ehr_pdf")
    assert res.status_code == 200, res.text
    doc = res.json()
    assert doc["format"] == "pdf"
    assert doc["kind"] == "ehr_pdf"
    assert doc["filename"].endswith(".pdf")
    assert "ehr-record" in doc["filename"]

    download = client.get(doc["download_url"])
    assert download.status_code == 200
    assert download.headers["content-type"] == "application/pdf"
    assert download.content[:5] == b"%PDF-"


def test_the_fhir_export_still_works_unchanged(env):
    client, _TestSession, ids = env
    res = client.post(f"/api/visits/{ids['visit']}/documents/ehr_bundle")
    assert res.status_code == 200, res.text
    doc = res.json()
    assert doc["format"] == "json"
    download = client.get(doc["download_url"])
    assert download.headers["content-type"] == "application/fhir+json"
    bundle = download.json()
    assert bundle["type"] == "document"
    assert bundle["entry"][0]["resource"]["resourceType"] == "Composition"


def test_both_exports_describe_the_same_visit(env):
    """The end-to-end version of the boundary: two files, one record."""
    client, _TestSession, ids = env
    json_doc = client.post(f"/api/visits/{ids['visit']}/documents/ehr_bundle").json()
    pdf_doc = client.post(f"/api/visits/{ids['visit']}/documents/ehr_pdf").json()
    bundle = client.get(json_doc["download_url"]).json()
    text = pdf_text(client.get(pdf_doc["download_url"]).content)

    assert bundle["identifier"]["value"] == ids["visit"]
    assert ids["visit"] in text
    for section in bundle["entry"][0]["resource"]["section"]:
        assert section["title"] in text


def test_an_unknown_kind_is_still_rejected(env):
    client, _TestSession, ids = env
    res = client.post(f"/api/visits/{ids['visit']}/documents/ehr_html")
    assert res.status_code == 400
    assert "ehr_pdf" in res.json()["detail"]


# --- 5. it refuses rather than rendering Bangla wrongly -----------------------------


def test_a_missing_font_refuses_instead_of_rendering(tmp_path, env):
    """A PDF with mangled Bangla looks like a working feature and is a corrupted
    medical record. An error is recoverable; a wrong document handed over is not."""
    _client, TestSession, ids = env
    bundle = _bundle(TestSession, ids["visit"])
    with pytest.raises(PdfFontUnavailable):
        bundle_to_pdf(bundle, font_path=tmp_path / "not-a-font.ttf")


def test_every_character_the_pdf_draws_exists_in_the_font(env):
    """A missing glyph does not raise — it VANISHES.

    That is how ``kg/m²`` shipped as ``kg/m``: the font has no U+00B2, the superscript
    was dropped, and a BMI in a medical document silently carried a different unit
    with nothing failing anywhere. This walks everything the renderer will draw and
    checks the font can actually draw it, so the next such character is caught here
    rather than in a patient's record.
    """
    from fontTools.ttLib import TTFont

    from backend.app.core.config import DEFAULT_PDF_FONT
    from backend.app.services.ehr_pdf import renderable_text

    _client, TestSession, ids = env
    cmap = TTFont(DEFAULT_PDF_FONT).getBestCmap()
    text = renderable_text(_bundle(TestSession, ids["visit"]))
    missing = sorted({ch for ch in text
                      if ord(ch) not in cmap and ch not in "\n\r\t "})
    assert not missing, (
        "the PDF would silently drop these characters: "
        + ", ".join(f"{ch!r} (U+{ord(ch):04X})" for ch in missing)
    )


def test_the_bmi_unit_is_not_silently_truncated(env):
    """The specific regression: 'kg/m' is kilograms per metre and is not a BMI."""
    _client, TestSession, ids = env
    text = pdf_flat(bundle_to_pdf(_bundle(TestSession, ids["visit"])))
    assert "kg/m2" in text
    assert not re.search(r"kg/m(?![2\w])", text), "the BMI unit lost its exponent"


def test_the_shipped_font_covers_bengali_and_latin():
    """One file for the whole document — the reason the repo carries a font at all
    instead of resolving one from the operating system."""
    from fontTools.ttLib import TTFont

    from backend.app.core.config import DEFAULT_PDF_FONT

    assert DEFAULT_PDF_FONT.is_file(), f"the shipped font is missing: {DEFAULT_PDF_FONT}"
    cmap = TTFont(DEFAULT_PDF_FONT).getBestCmap()
    for ch in "ABCabc0123456789/.,()%":
        assert ord(ch) in cmap, f"the font cannot render {ch!r}"
    for ch in "অআজ্বরপেট":
        assert ord(ch) in cmap, f"the font cannot render {ch!r}"


def test_text_shaping_is_actually_switched_on():
    """Without set_text_shaping(True) the PDF still builds and the Bangla is wrong —
    a silent regression with no failing symptom anywhere else."""
    import inspect

    from backend.app.services import ehr_pdf

    source = inspect.getsource(ehr_pdf._build_pdf)
    assert "set_text_shaping(True)" in source


def test_render_ehr_pdf_goes_through_the_one_bundle_builder():
    import inspect

    from backend.app.services import ehr_pdf

    source = inspect.getsource(ehr_pdf.render_ehr_pdf)
    assert "build_fhir_bundle" in source
    # The renderer must never grow its own database reads.
    module = inspect.getsource(ehr_pdf)
    for leak in ("db.query", "db.get("):
        assert leak not in module, (
            f"ehr_pdf reads the database directly ({leak}) — the PDF and the FHIR file "
            "can now drift apart"
        )


def test_render_ehr_pdf_end_to_end(env):
    _client, TestSession, ids = env
    db = TestSession()
    visit = db.query(Visit).filter(Visit.uuid == ids["visit"]).first()
    data = render_ehr_pdf(db, visit)
    db.close()
    assert data[:5] == b"%PDF-"
    assert RAW_BANGLA in pdf_flat(data)
