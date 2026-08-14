"""S38 — API contracts for the STATIC clinical reference data (ADR-0060).

These endpoints carry no patient data in either direction, which is the property that
makes them cacheable, safe to expose, and impossible to turn into a diagnosis surface:
:class:`GlucoseReferenceOut` has no field for a reading, and
:class:`BmiOut` is computed only from two numbers a human just typed into a form.

Bands and groups are CODES; the bilingual labels a user reads live in the portals'
own maps (ADR-0030 f) — except inside the glucose chart, where the label *is* the
content and shipping it once server-side keeps the two languages from drifting.
"""

from pydantic import BaseModel, Field


class BmiOut(BaseModel):
    """One computed BMI plus the band it falls in under both WHO ladders.

    ``bmi`` is null when the inputs cannot support one — missing, or outside plausible
    human bounds. A null is a refusal to compute, never a zero.
    """

    bmi: float | None = Field(None, description="kg/m², one decimal; null if not computable.")
    who: str | None = Field(None, description="WHO international band code.")
    asia: str | None = Field(
        None, description="WHO Asian action-point band code — the relevant ladder here."
    )
    source_who: str | None = None
    source_asia: str | None = None
    disclaimer: str
    disclaimer_bn: str


class GlucoseBandOut(BaseModel):
    """One band of one measurement context. Glucose bands carry mmol/L and mg/dL;
    the HbA1c context carries percent instead — hence every bound is optional."""

    label_en: str
    label_bn: str
    low_mmol_l: float | None = None
    high_mmol_l: float | None = None
    low_mg_dl: int | None = None
    high_mg_dl: int | None = None
    low_percent: float | None = None
    high_percent: float | None = None


class GlucoseContextOut(BaseModel):
    """One measurement context (fasting, OGTT, random, HbA1c).

    ``requires_context_*`` is not decoration: it states what must be true of the SAMPLE
    for the bands to mean anything, which is the whole reason this is a chart rather
    than a single "diabetic limit".
    """

    code: str
    name_en: str
    name_bn: str
    requires_context_en: str
    requires_context_bn: str
    source: str
    bands: list[GlucoseBandOut]
    note_en: str | None = None
    note_bn: str | None = None
    note_source: str | None = None


class GlucoseReferenceOut(BaseModel):
    contexts: list[GlucoseContextOut]
    disclaimer: str
    disclaimer_bn: str


class TestSuggestionOut(BaseModel):
    """One entry of the diagnostic-test typing aid (B4).

    Selecting one ORDERS NOTHING — it inserts text into a field the doctor is writing.
    """

    name_en: str
    name_bn: str
    group: str
    aliases: list[str] = []
