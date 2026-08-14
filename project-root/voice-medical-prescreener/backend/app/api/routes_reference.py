"""S38 — static clinical reference endpoints (ADR-0060).

GET /api/reference/bmi?weight_kg=&height_cm= — compute one BMI + its bands
GET /api/reference/glucose                   — the whole glucose reference chart
GET /api/reference/tests?q=                  — diagnostic-test typing suggestions

⚠ Three properties hold for every route here, and each is deliberate:

  * **No patient is involved.** Nothing takes a patient_id, reads a patients row, or
    writes anything. The BMI route takes two loose numbers a human typed into a form —
    which is why it can be a GET, and why it can never accidentally publish a patient's
    measurements into a URL (rule #4: no personal data in query strings).
  * **No LLM, no network, no quota.** All three answer from constants in
    ``services/clinical_reference``.
  * **No conclusion is returned.** The glucose route deliberately has no input at all:
    an endpoint that accepted a reading and returned a band would be one refactor from
    printing a finding beside a patient's name (rule #2).
"""

from fastapi import APIRouter, Query

from backend.app.schemas.reference import (
    BmiOut,
    GlucoseReferenceOut,
    TestSuggestionOut,
)
from backend.app.services.clinical_reference import (
    REFERENCE_DISCLAIMER,
    REFERENCE_DISCLAIMER_BN,
    bmi,
    bmi_band,
    glucose_reference,
    search_tests,
)

router = APIRouter(prefix="/api/reference", tags=["reference"])


@router.get("/bmi", response_model=BmiOut)
def get_bmi(
    weight_kg: float | None = Query(None, description="Weight in KILOGRAMS."),
    height_cm: float | None = Query(None, description="Height in CENTIMETRES."),
) -> BmiOut:
    """BMI for two typed measurements, or an all-null result when they cannot support one.

    Out-of-range inputs return ``bmi: null`` rather than a 400: this is called live as a
    medic types a height, so a half-entered "1" must produce "no BMI yet", not an error
    banner. The units are named in the parameters and echoed in the UI, because a BMI
    computed from pounds and inches is a plausible-looking wrong number.
    """
    value = bmi(weight_kg, height_cm)
    band = bmi_band(value) or {}
    return BmiOut(
        bmi=value,
        who=band.get("who"),
        asia=band.get("asia"),
        source_who=band.get("source_who"),
        source_asia=band.get("source_asia"),
        disclaimer=REFERENCE_DISCLAIMER,
        disclaimer_bn=REFERENCE_DISCLAIMER_BN,
    )


@router.get("/glucose", response_model=GlucoseReferenceOut)
def get_glucose_reference() -> GlucoseReferenceOut:
    """The published glucose thresholds, by measurement context, in both unit systems."""
    return GlucoseReferenceOut(**glucose_reference())


@router.get("/tests", response_model=list[TestSuggestionOut])
def get_test_suggestions(
    q: str = Query("", description="What the doctor has typed so far; blank returns the head."),
    limit: int = Query(8, ge=1, le=50),
) -> list[TestSuggestionOut]:
    """Typing suggestions for the Required Tests field. Assistance, never an order."""
    return [TestSuggestionOut(**entry) for entry in search_tests(q, limit=limit)]
