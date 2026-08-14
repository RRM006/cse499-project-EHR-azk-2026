"""S38 (ADR-0060) — the date policy, the BMI arithmetic, and the static reference data.

These are pure-function tests: no DB, no network, no LLM. That is the point of the two
modules under test — they are constants and arithmetic, so their behaviour is fully
pinnable, and anything that later needs a patient row does not belong in them.

What is worth pinning here, and why:

  * **The Dhaka boundary.** "Today" changes at 18:00 UTC. The prescription form used to
    stamp the UTC date, so between midnight and 06:00 Dhaka a prescription was dated
    YESTERDAY on a document the patient carries to a pharmacy. The 18:00-UTC crossing is
    tested directly.
  * **Refusal to compute a nonsense BMI.** The brief: *"Do not allow nonsensical values
    to produce misleading BMI."* A number that a person would have to know to distrust
    is worse than no number.
  * **That the glucose reference cannot become a diagnosis.** ``glucose_reference()``
    takes no argument at all, and there is no function anywhere that maps a reading to a
    conclusion. A test asserts the signature, because that absence is a safety property
    (rule #2) and absences are exactly what regress silently.
"""

from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services import clinical_reference as ref
from backend.app.services.clinical_dates import (
    DHAKA_TZ,
    FUTURE_DATE,
    INVALID_DATE,
    PAST_DATE,
    check_authored_now,
    check_scheduled,
    dhaka_today,
    dhaka_today_iso,
    parse_iso_date,
)

client = TestClient(app)


# --------------------------------------------------------------------------
# The Dhaka clock
# --------------------------------------------------------------------------


def test_dhaka_is_utc_plus_six():
    assert DHAKA_TZ.utcoffset(None).total_seconds() == 6 * 3600


def test_today_rolls_over_at_18_00_utc_not_at_midnight_utc():
    """The bug this exists to stop: at 00:30 Dhaka the UTC date is still yesterday."""
    before = datetime(2026, 8, 14, 17, 59, tzinfo=timezone.utc)   # 23:59 Dhaka
    after = datetime(2026, 8, 14, 18, 1, tzinfo=timezone.utc)     # 00:01 Dhaka, next day
    assert dhaka_today(now=before) == date(2026, 8, 14)
    assert dhaka_today(now=after) == date(2026, 8, 15)
    # And the UTC date disagrees at that moment — which is the whole point.
    assert after.date() == date(2026, 8, 14) != dhaka_today(now=after)


def test_offset_less_now_is_read_as_utc_not_local():
    """SQLite hands back naive UTC; reading it as local time is the P2-1 defect."""
    naive = datetime(2026, 8, 14, 18, 1)      # no tzinfo
    assert dhaka_today(now=naive) == date(2026, 8, 15)


def test_today_iso_is_a_plain_date_string():
    assert dhaka_today_iso() == dhaka_today().isoformat()
    assert len(dhaka_today_iso()) == 10


# --------------------------------------------------------------------------
# The date policy (category B: authored now / category C: scheduled forward)
# --------------------------------------------------------------------------


@pytest.fixture()
def noon():
    """A fixed instant: 12:00 UTC on 2026-08-14 = 18:00 Dhaka, same calendar day."""
    return datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)


def test_authored_now_accepts_today_only(noon):
    assert check_authored_now("2026-08-14", now=noon) is None
    assert check_authored_now("2026-08-13", now=noon) == PAST_DATE
    assert check_authored_now("2026-08-15", now=noon) == FUTURE_DATE


def test_authored_now_treats_a_blank_as_absent_not_invalid(noon):
    """An older client that never sent a date must keep working; the route stamps today."""
    assert check_authored_now(None, now=noon) is None
    assert check_authored_now("", now=noon) is None
    assert check_authored_now("   ", now=noon) is None


def test_scheduled_allows_today_and_the_far_future_but_not_the_past(noon):
    assert check_scheduled("2026-08-14", now=noon) is None    # a same-day recheck is real
    assert check_scheduled("2027-08-14", now=noon) is None    # a 12-month recall is real
    assert check_scheduled("2026-08-13", now=noon) == PAST_DATE


def test_garbage_is_reported_as_invalid_not_crashed(noon):
    assert check_authored_now("next tuesday", now=noon) == INVALID_DATE
    assert check_scheduled("14/08/2026", now=noon) == INVALID_DATE
    with pytest.raises(ValueError):
        parse_iso_date("not-a-date")


def test_a_full_timestamp_is_accepted_as_its_date_half(noon):
    """A client that sends more precision than asked is not punished for it."""
    assert check_authored_now("2026-08-14T09:30:00Z", now=noon) is None


# --------------------------------------------------------------------------
# BMI
# --------------------------------------------------------------------------


def test_bmi_is_kg_over_metres_squared():
    # 70 kg at 170 cm -> 70 / 1.7^2 = 24.22...
    assert ref.bmi(70, 170) == 24.2
    assert ref.bmi(80, 160) == 31.2


def test_bmi_refuses_rather_than_misleads():
    """Out-of-range inputs return None. A 1.7 kg adult is a typo, not a finding."""
    assert ref.bmi(None, 170) is None
    assert ref.bmi(70, None) is None
    assert ref.bmi(0.5, 170) is None        # below MIN_WEIGHT_KG
    assert ref.bmi(700, 170) is None        # above MAX_WEIGHT_KG
    assert ref.bmi(70, 17) is None          # cm/inch confusion
    assert ref.bmi(70, 1.7) is None         # metres typed into a cm field
    assert ref.bmi(70, 900) is None
    assert ref.bmi("heavy", 170) is None    # non-numeric never raises


def test_bmi_reports_both_ladders_and_they_can_disagree():
    """A BMI of 24 is 'normal' internationally and 'increased risk' on the Asian action
    points — the reason both are shown to a clinic in Bangladesh."""
    band = ref.bmi_band(ref.bmi(70, 171))
    assert band["bmi"] == 23.9
    assert band["who"] == "normal"
    assert band["asia"] == "increased_risk"


def test_bmi_band_boundaries_follow_the_published_cut_offs():
    assert ref.bmi_band(18.4)["who"] == "underweight"
    assert ref.bmi_band(18.5)["who"] == "normal"
    assert ref.bmi_band(24.9)["who"] == "normal"
    assert ref.bmi_band(25.0)["who"] == "overweight"
    assert ref.bmi_band(30.0)["who"] == "obese"
    assert ref.bmi_band(22.9)["asia"] == "normal"
    assert ref.bmi_band(23.0)["asia"] == "increased_risk"
    assert ref.bmi_band(27.5)["asia"] == "high_risk"
    assert ref.bmi_band(None) is None


def test_every_band_code_is_declared():
    for value in (15, 20, 24, 27, 35):
        band = ref.bmi_band(value)
        assert band["who"] in ref.BMI_BAND_CODES
        assert band["asia"] in ref.BMI_BAND_CODES


# --------------------------------------------------------------------------
# Glucose reference — a chart, never a verdict
# --------------------------------------------------------------------------


def test_glucose_reference_takes_no_patient_reading():
    """The safety property (rule #2), asserted on the signature itself: there is no
    parameter to pass a measurement to, so no caller can ask this module what a
    patient's number 'means'."""
    import inspect

    assert list(inspect.signature(ref.glucose_reference).parameters) == []


def test_every_glucose_context_states_what_it_requires_of_the_sample():
    """The requirement IS the content — 'fasting' bands read off a post-meal sample are
    meaningless, and that is the reason there is no single 'diabetic limit'."""
    data = ref.glucose_reference()
    codes = {c["code"] for c in data["contexts"]}
    assert codes == {"fasting", "ogtt_2h", "random", "hba1c"}
    for context in data["contexts"]:
        assert context["requires_context_en"].strip()
        assert context["requires_context_bn"].strip()
        assert context["source"].strip()
        assert context["bands"], context["code"]


def test_the_who_thresholds_are_the_published_ones():
    contexts = {c["code"]: c for c in ref.glucose_reference()["contexts"]}
    fasting_diabetes = contexts["fasting"]["bands"][-1]
    assert fasting_diabetes["low_mmol_l"] == 7.0
    assert fasting_diabetes["low_mg_dl"] == 126
    ogtt_diabetes = contexts["ogtt_2h"]["bands"][-1]
    assert ogtt_diabetes["low_mmol_l"] == 11.1
    assert ogtt_diabetes["low_mg_dl"] == 200
    hba1c_diabetes = contexts["hba1c"]["bands"][-1]
    assert hba1c_diabetes["low_percent"] == 6.5


def test_the_who_ada_disagreement_is_surfaced_not_resolved():
    """5.8 mmol/L is 'normal' under WHO and 'impaired' under the ADA. Hiding that would
    turn a contested number into an apparent fact."""
    fasting = {c["code"]: c for c in ref.glucose_reference()["contexts"]}["fasting"]
    assert "5.6" in (fasting["note_en"] or "")
    # The note must name the OTHER standard, so a reader can see whose number it is.
    assert "American Diabetes Association" in (fasting["note_source"] or "")
    assert "ADA" in (fasting["note_en"] or "")


def test_the_disclaimer_rides_on_the_payload_not_on_the_caller():
    data = ref.glucose_reference()
    assert "NOT a diagnosis" in data["disclaimer"]
    assert data["disclaimer_bn"].strip()


# --------------------------------------------------------------------------
# Test vocabulary (B4)
# --------------------------------------------------------------------------


def test_the_vocabulary_is_bilingual_and_grouped():
    entries = ref.test_vocabulary()
    assert len(entries) >= 40
    for entry in entries:
        assert entry["name_en"].strip()
        assert entry["name_bn"].strip()
        assert entry["group"].strip()


def test_search_matches_the_abbreviations_a_doctor_actually_types():
    assert any(e["name_en"].startswith("CBC") for e in ref.search_tests("cbc"))
    assert any("Fasting blood sugar" in e["name_en"] for e in ref.search_tests("fbs"))
    assert any("USG" in e["name_en"] for e in ref.search_tests("ultrasound"))
    assert any("ECG" in e["name_en"] for e in ref.search_tests("ekg"))
    assert any("HbA1c" in e["name_en"] for e in ref.search_tests("a1c"))


def test_search_ranks_a_prefix_match_above_a_mere_substring():
    results = ref.search_tests("urine")
    assert results, "no match for a term that is definitely in the list"
    assert results[0]["name_en"].lower().startswith("urine")


def test_a_blank_query_returns_the_head_not_nothing():
    """The field shows suggestions before anything is typed; returning [] would make it
    look broken."""
    assert len(ref.search_tests("")) == 8
    assert ref.search_tests("", limit=3) == ref.test_vocabulary()[:3]


def test_an_unknown_term_returns_nothing_rather_than_a_wrong_guess():
    assert ref.search_tests("zzzzzz") == []


# --------------------------------------------------------------------------
# The routes
# --------------------------------------------------------------------------


def test_bmi_route_computes_and_bands():
    r = client.get("/api/reference/bmi", params={"weight_kg": 70, "height_cm": 170})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["bmi"] == 24.2
    assert body["who"] == "normal"
    assert body["disclaimer"]


def test_bmi_route_returns_null_not_an_error_for_a_half_typed_height():
    """It is called live as a medic types, so '1' must mean 'no BMI yet'."""
    r = client.get("/api/reference/bmi", params={"weight_kg": 70, "height_cm": 1})
    assert r.status_code == 200
    assert r.json()["bmi"] is None


def test_bmi_route_with_nothing_supplied_is_still_a_200():
    r = client.get("/api/reference/bmi")
    assert r.status_code == 200
    assert r.json()["bmi"] is None


def test_glucose_route_serves_the_whole_chart():
    r = client.get("/api/reference/glucose")
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["contexts"]) == 4
    assert body["disclaimer_bn"]


def test_tests_route_filters():
    r = client.get("/api/reference/tests", params={"q": "creatinine"})
    assert r.status_code == 200, r.text
    names = [e["name_en"] for e in r.json()]
    assert "Serum creatinine" in names


def test_reference_routes_carry_no_patient_identifier():
    """Rule #4: these are cacheable static endpoints and must stay that way — no
    patient_id, no visit_uuid, nothing personal in a query string."""
    schema = client.get("/openapi.json").json()
    for path, item in schema["paths"].items():
        if not path.startswith("/api/reference"):
            continue
        for operation in item.values():
            names = {p["name"] for p in operation.get("parameters", [])}
            assert not (names & {"patient_id", "visit_uuid", "doctor_id", "phone"}), path
