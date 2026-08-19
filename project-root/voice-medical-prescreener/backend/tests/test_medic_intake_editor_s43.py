"""S43 — "the Sugar reference / Edit interaction does not work" on the medic's
Intake & Vitals card, before the referral.

THREE defects, all measured in a real browser at 1280x720 against the shipped portal,
all in the same card. None of them is the button being unwired — every handler was
correctly attached, which is why reading the code found nothing.

1. THE SAVE CLICK WAS LANDING ON A DIV.
   ``#bmi-live`` is 15.7px tall while empty and 45.6px once the ``/api/reference/bmi``
   answer arrives, and it sat directly ABOVE the Save/Cancel row. So Save moved DOWN
   **29.9px — 94% of its own 31.6px height** — roughly 250ms (the liveBmi debounce)
   plus one network round-trip after the medic stopped typing, i.e. exactly while
   their hand was travelling to the button. An instrumented click then reported
   ``click -> DIV`` instead of the button: no request was sent, no error appeared, the
   form stayed open with the values still in it. Indistinguishable from a dead button.
   The fix is the DOM order — the readout now follows the action row, so nothing
   interactive can be displaced at any width in either language. Reserving space with
   a min-height was rejected: the box is 3 lines at 800px in English and more in Bangla
   at a narrow width, so any fixed reservation is a guess that fails on the layout it
   was not measured on.

2. THE LANGUAGE TOGGLE CLOSED THE SUGAR REFERENCE CHART.
   Measured: display ``block -> none``, 2186 characters -> 0. Both staff portals call
   ``renderGlucosePanel()`` on a language change *precisely* so the chart follows the
   toggle, and it returned immediately every time, because whether the panel was open
   had been inferred from ``panel.style.display`` — a property on an element that the
   card's ``innerHTML`` rebuild had just destroyed and recreated from a template saying
   ``display:none``. The state now lives outside the thing that gets thrown away.

3. THE LANGUAGE TOGGLE SILENTLY DISCARDED UNSAVED VITALS.
   Measured: a weight of 63.5 typed into the open editor read 62.5 again afterwards.
   ``renderIntakeCard()`` re-opens the editor from the STORED patient, so every unsaved
   keystroke was overwritten with no warning — and a medic who does not notice then
   saves the old numbers over their own reading.

⚠ NO backend change was needed or made for any of this. The route, the schema, the
validation, the audit trail and the referral are untouched; the reading/context pairing
stays pinned by ``test_intake_vitals_glucose.py`` and the identity/leak rules by
``test_medic_intake_editor_s41.py``. The backend assertions here are only the two that
prove the four fields still round-trip and still reach the doctor.

Synthetic data only (rule #4).
"""

from __future__ import annotations

import pathlib
import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.database import Base, get_db
from backend.app.db.models import Clinic, Patient, User, Visit
from backend.app.main import app

PROJECT = pathlib.Path(__file__).resolve().parents[2]
MEDIC_HTML = PROJECT / "frontend_medic" / "index.html"
DOCTOR_HTML = PROJECT / "frontend_doctor" / "index.html"
STAFF_JS = PROJECT / "frontend_shared" / "staff.js"


def medic_src() -> str:
    return MEDIC_HTML.read_text(encoding="utf-8")


def fn_body(name: str, source: str) -> str:
    marker = f"function {name}("
    assert marker in source, f"{name}() is gone from the shipped portal"
    return source.split(marker)[1].split("\n    }")[0]


# --- 1. the action row must not be displaced by an async readout ---------------------


def test_the_live_bmi_readout_comes_AFTER_the_save_button():
    """The whole reported bug in one assertion.

    ``#bmi-live`` is filled from a debounced network call. Anything interactive that
    sits below it moves under the medic's pointer when that call lands.
    """
    src = medic_src()
    save = src.index('onclick="saveIntake(this)"')
    live = src.index('id="bmi-live"')
    assert live > save, (
        "#bmi-live is above the Save button again — when the BMI arrives it will push "
        "Save down by ~30px and the click will land on the wrapper div"
    )


def test_cancel_is_protected_by_the_same_ordering():
    src = medic_src()
    assert src.index('onclick="closeIntakeEditor()"') < src.index('id="bmi-live"')


def test_nothing_else_interactive_sits_below_the_live_readout():
    """A control added after the readout would inherit the defect. The editor ends at
    the readout on purpose."""
    src = medic_src()
    tail = src[src.index('id="bmi-live"'):src.index('id="bmi-live"') + 400]
    assert "<button" not in tail and "<input" not in tail and "<select" not in tail


def test_the_live_readout_is_still_rendered_nothing_was_removed():
    """Order changed; the BMI, its two band ladders and its rule-#2 disclaimer are all
    still shown — showBmi() is the single renderer for both."""
    src = medic_src()
    assert 'id="bmi-live"' in src
    assert "showBmi('bmi-live'" in src
    assert "showBmi('bmi-readout'" in src


# --- 2. the sugar reference chart survives a re-render -------------------------------


def test_the_open_chart_is_not_tracked_on_the_element_that_gets_destroyed():
    """``panel.style.display`` is read off a node that innerHTML re-creates. Whatever
    replaces it must not be a property of that node."""
    src = STAFF_JS.read_text(encoding="utf-8")
    toggle = fn_body("toggleGlucosePanel", src) if "function toggleGlucosePanel(" in src else ""
    assert "glucoseOpenMounts" in src, "the open/closed state must live outside the DOM"
    assert "panel.style.display === 'none'" not in src.split("function renderGlucosePanel(")[1], (
        "renderGlucosePanel still decides from the freshly-reset inline style"
    )
    assert "glucoseOpenMounts" in toggle or "glucoseOpenMounts" in src


def test_render_reasserts_the_disclosure_after_a_rebuild():
    src = STAFF_JS.read_text(encoding="utf-8")
    body = src.split("function renderGlucosePanel(")[1].split("\n}")[0]
    assert "glucoseOpenMounts.has(mountId)" in body
    assert "panel.style.display = 'block'" in body


def test_each_portal_discloses_independently():
    """One Set keyed by mount id — the doctor opening their chart must not open the
    medic's, and closing one must not close the other."""
    src = STAFF_JS.read_text(encoding="utf-8")
    assert "new Set()" in src.split("glucoseOpenMounts")[1][:40]
    assert "toggleGlucosePanel('glucose-panel')" in medic_src()
    assert "toggleGlucosePanel('pd-glucose-panel')" in DOCTOR_HTML.read_text(encoding="utf-8")


@pytest.mark.parametrize("portal", [MEDIC_HTML, DOCTOR_HTML])
def test_both_portals_still_ask_the_chart_to_follow_the_language(portal):
    """The call was always there; it just could not do anything. It must stay."""
    assert "renderGlucosePanel(" in portal.read_text(encoding="utf-8")


# --- 3. unsaved vitals survive a re-render -------------------------------------------


def test_a_rerender_captures_what_the_medic_typed_before_destroying_the_form():
    body = fn_body("renderIntakeCard", medic_src())
    capture = body.index("readIntakeDraft(")
    rebuild = body.index("card.innerHTML")
    assert capture < rebuild, "the draft is read after the inputs have been destroyed"


def test_the_draft_is_stamped_with_the_patient_it_was_typed_for():
    """The editor stays open across a patient switch, so an unstamped draft would put
    one patient's typed weight into another patient's form — the leak S41 pinned."""
    src = medic_src()
    assert "readIntakeDraft(p.id)" in fn_body("renderIntakeCard", src)
    assert "draft.patientId === p.id" in fn_body("openIntakeEditor", src)


def test_the_draft_is_handed_back_when_the_editor_is_reopened():
    body = fn_body("renderIntakeCard", medic_src())
    assert "openIntakeEditor(p, age, draft)" in body


def test_a_fresh_open_still_prefills_from_the_stored_patient():
    """Clicking Edit passes no draft, so the form opens on the record — unchanged."""
    body = fn_body("renderIntakeCard", medic_src())
    assert "onclick = () => openIntakeEditor(p, age)" in body


@pytest.mark.parametrize(
    "field_id",
    ["in-name", "in-age", "in-sex", "in-height", "in-weight", "in-bp",
     "in-glucose", "in-glucose-context"],
)
def test_every_intake_field_is_covered_by_the_one_id_list(field_id):
    """S41 pinned that every field is written on every open, because the editor stays
    open across a patient switch and a missed field would carry the previous patient's
    value into a save. That guarantee now runs through INTAKE_FIELD_IDS, so the list
    itself is what has to be complete."""
    src = medic_src()
    id_list = src.split("const INTAKE_FIELD_IDS = [")[1].split("];")[0]
    assert f"'{field_id}'" in id_list
    # …and the id names a control the editor template really builds. Text inputs and
    # selects carry a literal id=""; number inputs go through the num() helper, whose
    # id is an argument. A typo in the list matches neither.
    assert f'id="{field_id}"' in src or f"num('{field_id}'" in src, (
        f"{field_id} is listed but no control with that id is rendered"
    )


def test_the_draft_only_refills_the_form_and_never_writes_a_record():
    """A draft is unsaved typing. It must not be able to reach the PATCH by itself."""
    body = fn_body("openIntakeEditor", medic_src())
    assert "api(" not in body and "PATCH" not in body


def test_saving_still_closes_the_editor_so_no_stale_draft_survives_a_save():
    body = fn_body("saveIntake", medic_src())
    assert body.index("closeIntakeEditor()") < body.index("renderIntakeCard()")


# --- 4. the backend round-trip for the four fields, and what the doctor sees ---------


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False},
        poolclass=StaticPool, future=True,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, future=True)
    db = TestSession()
    clinic = Clinic(name="S43 Clinic")
    db.add(clinic)
    db.flush()
    medic = User(clinic_id=clinic.id, name="Medic S43", role="medic")
    doctor = User(clinic_id=clinic.id, name="Doctor S43", role="doctor")
    other = Patient(clinic_id=clinic.id, external_ref="+8801900000043", weight_kg=50.0)
    patient = Patient(clinic_id=clinic.id, external_ref="+8801900000044")
    db.add_all([medic, doctor, other, patient])
    db.flush()
    visit = Visit(clinic_id=clinic.id, uuid="s43-visit", patient_id=patient.id,
                  status="awaiting_review")
    db.add(visit)
    db.commit()
    ids = {"medic": medic.id, "doctor": doctor.id, "patient": patient.id,
           "other": other.id, "other_weight": other.weight_kg, "visit": visit.uuid}
    db.close()

    def override_get_db():
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app), ids
    app.dependency_overrides.clear()


def test_the_medic_can_record_all_four_vitals_before_the_referral(client):
    api, ids = client
    resp = api.patch(
        f"/api/patients/{ids['patient']}/vitals",
        json={"editor_id": ids["medic"], "weight_kg": 62.5, "height_cm": 165.0,
              "bp": "120/80", "blood_glucose_mmol_l": 6.1,
              "blood_glucose_context": "fasting"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert (body["weight_kg"], body["height_cm"], body["bp"]) == (62.5, 165.0, "120/80")
    assert (body["blood_glucose_mmol_l"], body["blood_glucose_context"]) == (6.1, "fasting")


@pytest.mark.parametrize(
    "field,first,second",
    [
        ("weight_kg", 62.5, 63.5),
        ("height_cm", 165.0, 166.0),
        ("bp", "120/80", "118/76"),
    ],
)
def test_each_recorded_vital_can_then_be_CORRECTED(client, field, first, second):
    """The reported requirement is editing, not first entry: a medic who mistypes must
    be able to fix it before the doctor sees the case."""
    api, ids = client
    url = f"/api/patients/{ids['patient']}/vitals"
    assert api.patch(url, json={"editor_id": ids["medic"], field: first}).status_code == 200
    resp = api.patch(url, json={"editor_id": ids["medic"], field: second})
    assert resp.status_code == 200
    assert resp.json()[field] == second


def test_a_blood_sugar_correction_still_carries_its_context(client):
    api, ids = client
    url = f"/api/patients/{ids['patient']}/vitals"
    api.patch(url, json={"editor_id": ids["medic"], "blood_glucose_mmol_l": 6.1,
                         "blood_glucose_context": "fasting"})
    # The unchanged S39 rule: the value cannot be corrected without restating how it
    # was measured, because a fasting 5.4 and a random 5.4 are different facts.
    assert api.patch(url, json={"editor_id": ids["medic"],
                                "blood_glucose_mmol_l": 5.4}).status_code == 400
    ok = api.patch(url, json={"editor_id": ids["medic"], "blood_glucose_mmol_l": 5.4,
                              "blood_glucose_context": "random"})
    assert ok.status_code == 200
    assert (ok.json()["blood_glucose_mmol_l"], ok.json()["blood_glucose_context"]) == (5.4, "random")


def test_editing_one_patient_changes_no_other_patient(client):
    api, ids = client
    api.patch(f"/api/patients/{ids['patient']}/vitals",
              json={"editor_id": ids["medic"], "weight_kg": 62.5, "bp": "120/80"})
    assert api.get(f"/api/visits/{ids['visit']}").json()["patient"]["weight_kg"] == 62.5
    # The untouched patient still holds exactly what it was created with. Asserted
    # through the same PATCH endpoint's response, which returns the row it read.
    untouched = api.patch(f"/api/patients/{ids['other']}/vitals",
                          json={"editor_id": ids["medic"], "bp": "130/85"})
    assert untouched.status_code == 200
    assert untouched.json()["weight_kg"] == ids["other_weight"]
    assert untouched.json()["blood_glucose_mmol_l"] is None


def test_the_doctor_reads_the_values_the_medic_recorded(client):
    """The point of recording them before the referral."""
    api, ids = client
    api.patch(f"/api/patients/{ids['patient']}/vitals",
              json={"editor_id": ids["medic"], "weight_kg": 62.5, "height_cm": 165.0,
                    "bp": "120/80", "blood_glucose_mmol_l": 6.1,
                    "blood_glucose_context": "fasting"})
    patient = api.get(f"/api/visits/{ids['visit']}").json()["patient"]
    assert patient["height_cm"] == 165.0
    assert patient["bp"] == "120/80"
    assert patient["blood_glucose_context"] == "fasting"


def test_the_referral_still_works_after_the_vitals_are_edited(client):
    """'Do NOT change referral behavior' — so prove the whole medic path end to end:
    record the four vitals, then forward the case to a doctor."""
    api, ids = client
    api.patch(f"/api/patients/{ids['patient']}/vitals",
              json={"editor_id": ids["medic"], "weight_kg": 62.5, "height_cm": 165.0,
                    "bp": "120/80", "blood_glucose_mmol_l": 6.1,
                    "blood_glucose_context": "fasting"})
    assert ids["doctor"] in [d["id"] for d in api.get("/api/users?role=doctor").json()]
    forwarded = api.post(f"/api/visits/{ids['visit']}/assign",
                         json={"doctor_id": ids["doctor"], "editor_id": ids["medic"]})
    assert forwarded.status_code == 200
    # …and the vitals travelled with it.
    patient = api.get(f"/api/visits/{ids['visit']}").json()["patient"]
    assert (patient["weight_kg"], patient["height_cm"]) == (62.5, 165.0)
    assert patient["blood_glucose_mmol_l"] == 6.1


# --- 5. no duplicate wiring introduced by the fix ------------------------------------


def test_there_is_exactly_one_save_handler_and_one_editor_opener():
    src = medic_src()
    assert src.count('onclick="saveIntake(this)"') == 1
    assert len(re.findall(r"\bfunction saveIntake\(", src)) == 1
    assert len(re.findall(r"\bfunction openIntakeEditor\(", src)) == 1
    assert len(re.findall(r"\bfunction readIntakeDraft\(", src)) == 1


def test_the_glucose_panel_has_exactly_one_implementation_front_end_wide():
    """Same rule S39 established when the chart moved into staff.js."""
    everywhere = "".join(
        p.read_text(encoding="utf-8")
        for p in (MEDIC_HTML, DOCTOR_HTML, STAFF_JS, PROJECT / "frontend_shared" / "shared.js")
    )
    assert len(re.findall(r"\bfunction renderGlucosePanel\(", everywhere)) == 1
    assert len(re.findall(r"\basync function toggleGlucosePanel\(", everywhere)) == 1
