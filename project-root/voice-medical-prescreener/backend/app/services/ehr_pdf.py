"""S39 (ADR-0064) — the EHR record as a HUMAN-READABLE PDF.

--------------------------------------------------------------------------------
ONE RECORD, TWO RENDERINGS — NOT TWO RECORDS
--------------------------------------------------------------------------------

The brief asked for the EHR export in two formats and, correctly, warned against
creating "a second competing EHR representation". So this module does not read the
database. It takes the **FHIR document Bundle that ``services/ehr_export`` already
builds** and renders it.

That is the whole design, and it is what makes the guarantee real rather than
aspirational: the PDF cannot contain a fact the FHIR file lacks, cannot omit a section
the FHIR file has, and cannot disagree with it — because there is nothing else for it
to read. A change to the bundle changes both outputs at once, and a test asserts the
two carry the same sections.

Concretely: a FHIR document Bundle is *defined* as a Composition whose sections each
carry a human-readable XHTML narrative (``text.div``). That narrative is the
standard's own answer to "what should a person see", and it is exactly what this
renders. The PDF is therefore not a re-interpretation of the data — it is the
document's own narrative, typeset.

--------------------------------------------------------------------------------
WHY fpdf2 + HarfBuzz, AND WHY THE FONT IS IN THE REPO
--------------------------------------------------------------------------------

No PDF library existed here before; ``services/documents`` had reserved the seam
("``# \"pdf\": PdfWriter,  # future``") since rev 0010. The choice was decided by
Bangla, not by the PDF features:

* Bengali is a complex script. "জ্বর" is not three glyphs in three slots — it needs
  conjunct formation and vowel-sign reordering. A library that lays out one glyph per
  codepoint prints the patient's own words wrongly, which is a **rule #1 defect in the
  one export a human actually reads**. fpdf2 can delegate shaping to HarfBuzz
  (``set_text_shaping``); ReportLab cannot shape Bengali at all.
* The font ships in ``assets/fonts/`` instead of being found on the machine.
  ``Nirmala.ttf`` exists on Windows and is not redistributable and not on Arch; a
  clean Arch box may have no Bengali font at all. A medical document must render
  identically on both dev machines, so the repo carries one OFL-licensed file (Noto
  Sans Bengali, which covers Bengali AND Latin — one font for the whole document).

⚠ **The renderer REFUSES rather than degrades.** If HarfBuzz is missing or the font
cannot be loaded it raises :class:`PdfFontUnavailable`, and the route returns an
error. A PDF with mangled Bangla looks like a working feature and is a corrupted
medical record; an error message is recoverable, a wrong document handed to a patient
is not.

--------------------------------------------------------------------------------
WHAT IT DOES NOT DO
--------------------------------------------------------------------------------

* It computes nothing. Every number, name and sentence comes from the bundle.
* It fills nothing in. A section absent from the bundle is absent here; where the
  bundle has no patient name the PDF says "Name not provided" — the portals' own
  wording for an absence — rather than leaving a blank a reader would take for a
  rendering fault.
* It adds no clinical content of any kind: no band, no interpretation, no summary of
  the summary. The no-diagnosis disclaimer is printed verbatim from the same
  ``services/report.DISCLAIMER`` constant every other export uses.
"""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.db.models import Visit
from backend.app.services.ehr_export import _TRANSLATION_URL, build_fhir_bundle
from backend.app.services.report import DISCLAIMER

#: Registered font family name inside the PDF.
_FONT_FAMILY = "noto"

#: Page geometry, in millimetres (fpdf2's default unit).
_MARGIN = 15.0
_LINE = 5.2

#: What the portals say when a record carries no name. Repeated here rather than
#: imported from the frontend for the obvious reason, and kept identical on purpose:
#: a reader who sees one wording on screen and another on paper has to wonder whether
#: they are looking at the same patient.
_NO_NAME = "Name not provided"


class PdfFontUnavailable(RuntimeError):
    """Raised when the PDF cannot be typeset CORRECTLY, so it is not typeset at all."""


# --- the narrative parser ------------------------------------------------------


class _Block:
    """One renderable thing: a paragraph, a bullet, or a table row."""

    __slots__ = ("kind", "cells")

    def __init__(self, kind: str, cells: list[str]) -> None:
        self.kind = kind          # "p" | "li" | "row"
        self.cells = cells


class _NarrativeParser(HTMLParser):
    """Turn one FHIR ``text.div`` into blocks.

    The narratives this project generates use a deliberately tiny vocabulary —
    ``<p>``, ``<b>``, ``<i>``, ``<br/>``, ``<ul>/<li>``, ``<table>/<tr>/<td>`` —
    because ``ehr_export`` writes all of them. Anything else is treated as flowing
    text rather than dropped: an unknown tag must never cost a reader a sentence of a
    medical record.

    ⚠ Text is captured in DOCUMENT ORDER, and emphasis is deliberately not tracked.
    An earlier draft collected ``<b>`` into a separate "prefix" bucket, which works
    for ``<p><b>Patient said:</b> …</p>`` and silently REVERSES
    ``<p>Urgency tier: <b>low</b></p>`` into "low Urgency tier:". This renderer draws
    one weight anyway, so the bold distinction bought nothing and cost correctness.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[_Block] = []
        self._text: list[str] = []
        self._row: list[str] | None = None

    # -- helpers
    def _flush_text(self, kind: str = "p") -> None:
        text = "".join(self._text).strip()
        self._text = []
        if text:
            self.blocks.append(_Block(kind, [text]))

    def _flush_cell(self, *, only_if_pending: bool = False) -> None:
        if self._row is None:
            return
        text = "".join(self._text).strip()
        self._text = []
        # `only_if_pending` is for </tr>: the last </td> has already flushed, so an
        # unconditional flush there appends a phantom empty cell to every row.
        if only_if_pending and not text:
            return
        self._row.append(text)

    # -- HTMLParser interface
    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._flush_text()
            self._row = []
        elif tag in ("td", "th"):
            self._text = []
        elif tag in ("p", "li"):
            self._flush_text()
        elif tag == "br":
            # ⚠ Not cosmetic. `ehr_export` puts the English and the Bangla of one
            # field in a SINGLE cell separated by <br/>; dropping the break rendered
            # them as one run-on string ("Skin rash on the arm" + the Bangla with no
            # gap), which reads as a corrupted value rather than a bilingual one.
            self._text.append("\n")

    def handle_endtag(self, tag):
        if tag in ("td", "th"):
            self._flush_cell()
        elif tag == "tr":
            self._flush_cell(only_if_pending=True)
            if self._row:
                self.blocks.append(_Block("row", self._row))
            self._row = None
        elif tag == "p":
            self._flush_text()
        elif tag == "li":
            # Red flags are the one list `ehr_export` emits, and rule #3 makes their
            # legibility a safety property: run together into one paragraph they stop
            # reading as separate findings.
            self._flush_text("li")

    def handle_data(self, data):
        self._text.append(data)

    def close(self):
        super().close()
        self._flush_text()


def narrative_blocks(div_html: str) -> list[_Block]:
    parser = _NarrativeParser()
    parser.feed(div_html or "")
    parser.close()
    return parser.blocks


# --- reading the bundle --------------------------------------------------------


def _bn_of(primitive: dict | None) -> str:
    """The Bangla carried by a ``_title``-style primitive extension, or ''."""
    for ext in (primitive or {}).get("extension", []):
        if ext.get("url") != _TRANSLATION_URL:
            continue
        parts = {e.get("url"): e for e in ext.get("extension", [])}
        if parts.get("lang", {}).get("valueCode") == "bn":
            return str(parts.get("content", {}).get("valueString") or "")
    return ""


def _resources(bundle: dict, resource_type: str) -> list[dict]:
    return [e["resource"] for e in bundle.get("entry", [])
            if e.get("resource", {}).get("resourceType") == resource_type]


def _first(bundle: dict, resource_type: str) -> dict:
    found = _resources(bundle, resource_type)
    return found[0] if found else {}


def _patient_lines(bundle: dict) -> list[tuple[str, str]]:
    """The identity block, from the bundle's Patient resource only.

    An absent element stays absent: FHIR omits what is unknown, and this prints that
    omission as a dash rather than inventing a placeholder value.
    """
    patient = _first(bundle, "Patient")
    names = patient.get("name") or []
    name = str((names[0] if names else {}).get("text") or "").strip() or _NO_NAME
    phone = next((str(t.get("value") or "") for t in patient.get("telecom") or []
                  if t.get("system") == "phone"), "") or "—"
    return [
        ("Patient", name),
        ("Phone", phone),
        ("Sex", str(patient.get("gender") or "—")),
        ("Born", str(patient.get("birthDate") or "—")),
    ]


# --- rendering -----------------------------------------------------------------


def _build_pdf(bundle: dict, font_path: Path):
    """Typeset ``bundle``. Imported lazily so a missing optional dependency is an
    error from THIS function rather than an ImportError at application startup."""
    try:
        from fpdf import FPDF
        from fpdf.enums import XPos, YPos
    except ImportError as exc:                        # pragma: no cover - env guard
        raise PdfFontUnavailable(f"fpdf2 is not installed: {exc}") from exc
    try:
        import uharfbuzz  # noqa: F401  (presence check only — fpdf2 uses it internally)
    except ImportError as exc:                        # pragma: no cover - env guard
        raise PdfFontUnavailable(
            "uharfbuzz is not installed, so Bengali text cannot be shaped. Refusing to "
            "render a PDF whose Bangla would be wrong."
        ) from exc
    if not font_path.is_file():
        raise PdfFontUnavailable(f"PDF font not found at {font_path}")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=_MARGIN)
    pdf.set_margins(_MARGIN, _MARGIN, _MARGIN)
    try:
        pdf.add_font(_FONT_FAMILY, "", str(font_path))
    except Exception as exc:                          # pragma: no cover - env guard
        raise PdfFontUnavailable(f"Could not load the PDF font {font_path}: {exc}") from exc
    # THE line this module exists for: without it, Bengali conjuncts and vowel signs
    # are laid out one glyph per codepoint and the patient's own words come out wrong.
    pdf.set_text_shaping(True)
    pdf.add_page()

    width = pdf.w - 2 * _MARGIN

    def line(text: str, *, size: float = 10.0, gap: float = _LINE,
             colour: tuple[int, int, int] = (17, 24, 39)) -> None:
        pdf.set_font(_FONT_FAMILY, size=size)
        pdf.set_text_color(*colour)
        pdf.multi_cell(width, gap, text=text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def rule() -> None:
        pdf.set_draw_color(203, 213, 225)
        y = pdf.get_y() + 1
        pdf.line(_MARGIN, y, pdf.w - _MARGIN, y)
        pdf.set_y(y + 2.5)

    composition = _first(bundle, "Composition")
    organization = _first(bundle, "Organization")

    # --- letterhead ---
    line(str(organization.get("name") or "Clinic"), size=15)
    address = (organization.get("address") or [{}])[0].get("text")
    if address:
        line(str(address), size=8.5, gap=4.2, colour=(100, 116, 139))
    title_en = str(composition.get("title") or "Clinical record")
    title_bn = _bn_of(composition.get("_title"))
    line(title_en + (f"  ·  {title_bn}" if title_bn else ""), size=11.5, colour=(15, 118, 110))
    rule()

    # --- identity + encounter ---
    for label, value in _patient_lines(bundle):
        line(f"{label}: {value}", size=9.5, gap=4.6)
    encounter = _first(bundle, "Encounter")
    period = (encounter.get("period") or {}).get("start")
    if period:
        line(f"Visit started: {period}", size=9.5, gap=4.6)
    identifier = (bundle.get("identifier") or {}).get("value")
    if identifier:
        line(f"Visit ID: {identifier}", size=8.5, gap=4.2, colour=(100, 116, 139))
    status = composition.get("status")
    if status:
        line(f"Document status: {status}", size=8.5, gap=4.2, colour=(100, 116, 139))
    practitioners = _resources(bundle, "Practitioner")
    if practitioners:
        who = (practitioners[0].get("name") or [{}])[0].get("text")
        if who:
            line(f"Attending doctor: {who}", size=9.5, gap=4.6)
    rule()

    # --- one block per Composition section, in the bundle's own order ---
    for section in composition.get("section") or []:
        heading = str(section.get("title") or "")
        heading_bn = _bn_of(section.get("_title"))
        pdf.ln(1.5)
        line(heading + (f"  ·  {heading_bn}" if heading_bn else ""),
             size=11.5, gap=5.6, colour=(15, 118, 110))
        div = (section.get("text") or {}).get("div") or ""
        blocks = narrative_blocks(div)
        if not blocks:
            line("—", size=9.5, gap=4.6, colour=(100, 116, 139))
        for block in blocks:
            if block.kind == "row":
                label = block.cells[0]
                value = "  ".join(c for c in block.cells[1:] if c) or "—"
                pdf.set_font(_FONT_FAMILY, size=9.5)
                pdf.set_text_color(100, 116, 139)
                pdf.multi_cell(52, 4.8, text=label, new_x=XPos.RIGHT, new_y=YPos.TOP)
                pdf.set_text_color(17, 24, 39)
                pdf.multi_cell(width - 52, 4.8, text=value,
                               new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            elif block.kind == "li":
                line(f"\u2022  {block.cells[0]}", size=9.5, gap=4.8)
            else:
                line(block.cells[0], size=9.5, gap=4.8)

    # --- the disclaimer every export carries, verbatim (rule #2) ---
    pdf.ln(2)
    rule()
    line(DISCLAIMER, size=8.5, gap=4.2, colour=(180, 83, 9))
    line(
        "This PDF is a human-readable rendering of the same record as the FHIR R4 "
        "document Bundle exported for this visit. The FHIR file is the machine-readable "
        "form; both are generated from the same stored data.",
        size=7.8, gap=3.8, colour=(100, 116, 139),
    )
    return pdf


def renderable_text(bundle: dict) -> str:
    """Every string this module will DRAW, concatenated.

    Exists for one test, and that test earned its place: the shipped font has no
    U+00B2, so ``kg/m²`` in a narrative was rendered as ``kg/m`` — a silently
    different unit in a medical document, with no error anywhere. A missing glyph
    does not fail; it simply disappears. So the glyph coverage of what we actually
    draw is asserted instead of assumed.
    """
    parts: list[str] = [DISCLAIMER, _NO_NAME]
    composition = _first(bundle, "Composition")
    organization = _first(bundle, "Organization")
    parts.append(str(organization.get("name") or ""))
    parts.append(str((organization.get("address") or [{}])[0].get("text") or ""))
    parts.append(str(composition.get("title") or ""))
    parts.append(_bn_of(composition.get("_title")))
    for label, value in _patient_lines(bundle):
        parts.extend([label, value])
    for section in composition.get("section") or []:
        parts.append(str(section.get("title") or ""))
        parts.append(_bn_of(section.get("_title")))
        for block in narrative_blocks((section.get("text") or {}).get("div") or ""):
            parts.extend(block.cells)
    return "".join(parts)


def bundle_to_pdf(bundle: dict, font_path: Path | None = None) -> bytes:
    """Typeset an already-built FHIR document Bundle. Pure function of ``bundle`` —
    which is what lets a test assert that the PDF and the JSON say the same thing."""
    font = font_path or get_settings().resolved_pdf_font
    pdf = _build_pdf(bundle, Path(font))
    output = pdf.output()
    return bytes(output)


def render_ehr_pdf(db: Session, visit: Visit) -> bytes:
    """The visit's EHR record as PDF bytes, via the ONE bundle builder."""
    return bundle_to_pdf(build_fhir_bundle(db, visit))
