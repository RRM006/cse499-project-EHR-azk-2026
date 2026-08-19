"""S41 — "clicking Edit does not work" on the medic's Intake & Vitals card.

WHAT WAS ACTUALLY WRONG
-----------------------
The button always worked. Measured in a real browser at 1280x720: clicking it set the
form to ``display: flex`` at y=461, and the form's **Save button landed at y=727** —
below a 720px fold, inside a case workspace that scrolls independently and was sitting
at ``scrollTop: 0``. The medic clicked Edit, nothing they could see changed, and there
was no visible way to save. That is indistinguishable from a dead button, and it is the
same defect the kiosk read-back panel had in S34.

So the fix is a scroll, not a rewire, and these tests pin the two halves that would
regress silently:

  * the editor is handed to ``bringIntoView()`` **after** it is shown — before it is
    shown the layout is stale and the scroll is a silent no-op;
  * every field is written from the patient object on **every** open, which is what
    makes a patient switch safe. This one is not theoretical: the editor stays open
    across a switch by design (``intakeOpen``), so if a single field were left out of
    ``openIntakeEditor`` the previous patient's value would sit in a form the medic is
    about to save onto somebody else.

The backend rules for the reading itself (value and context refused apart, no band, who
may write) are already pinned by ``test_intake_vitals_glucose.py`` and are not repeated
here. What is added below is the one BACKEND property that file does not cover: a
reading recorded for one patient must not appear on another.

Synthetic data only (rule #4).
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.database import Base, get_db
from backend.app.db.models import Clinic, Patient, User, Visit
from backend.app.main import app

client = TestClient(app)


def medic_html() -> str:
    resp = client.get("/medic/")
    assert resp.status_code == 200
    return resp.text


def fn_body(name: str, source: str) -> str:
    marker = f"function {name}("
    assert marker in source, f"{name}() is gone from the shipped portal"
    return source.split(marker)[1].split("\n    }")[0]


# --- 1. the form must actually become visible ---------------------------------------


def test_opening_the_editor_brings_it_into_view():
    """The whole reported bug in one assertion."""
    body = fn_body("openIntakeEditor", medic_html())
    assert "bringIntoView(editor)" in body, (
        "the intake form is shown but never scrolled to; its Save button sits below the "
        "fold on a 720px screen, which is what 'clicking Edit does nothing' actually was"
    )


def test_it_is_scrolled_only_after_it_has_been_shown():
    """Order is the whole point: in the same tick the element is still `display: none`
    the layout is stale and scrollIntoView() is a silent no-op."""
    body = fn_body("openIntakeEditor", medic_html())
    assert body.index("editor.style.display = 'flex'") < body.index("bringIntoView(editor)")


def test_the_medic_portal_loads_the_file_that_defines_the_helper():
    """bringIntoView lives in shared.js (S41). The portal must load it, and must not
    carry a private copy that could drift from the kiosk's behaviour."""
    html = medic_html()
    assert '<script src="/shared/shared.js"></script>' in html
    assert "function bringIntoView(" not in html


# --- 2. a patient switch must not leave the previous patient's numbers in the form ---


def test_every_editor_field_is_rewritten_from_the_patient_on_each_open():
    """The editor deliberately stays open across a patient switch (`intakeOpen`), and
    renderPatientCard re-opens it for the newly-selected patient. That is only safe if
    EVERY control is re-seeded — a field left out would keep the previous patient's
    value in a form the medic is about to save onto somebody else.

    ⚠ S43 rewrote HOW the seeding happens (one `stored` map written through
    INTAKE_FIELD_IDS, instead of eight hand-written getElementById lines) so that an
    unsaved draft could survive a language toggle. The requirement is unchanged and is
    asserted here against the new shape: every field still has a value derived from the
    patient object, and the write still covers every field in the list."""
    html = medic_html()
    body = fn_body("openIntakeEditor", html)
    id_list = html.split("const INTAKE_FIELD_IDS = [")[1].split("];")[0]
    for field in ("in-name", "in-age", "in-sex", "in-height", "in-weight", "in-bp",
                  "in-glucose", "in-glucose-context"):
        assert f"'{field}':" in body, f"{field} has no value derived from the patient"
        assert f"'{field}'" in id_list, f"{field} is never written on open"
    # The one loop that does the writing, over that one list.
    assert "INTAKE_FIELD_IDS.forEach" in body
    assert "el.value =" in body


def test_a_draft_from_another_patient_is_discarded_rather_than_restored():
    """S43's draft-preservation must not become the very leak this file was written
    about: the form stays open across a patient switch, so a draft is only ever handed
    back to the patient it was typed for."""
    body = fn_body("openIntakeEditor", medic_html())
    assert "draft.patientId === p.id" in body, (
        "a draft is restored without checking whose it is"
    )


def test_an_absent_value_is_written_as_empty_rather_than_left_alone():
    """`p.x || ''` / the null checks matter more than they look: assigning nothing at all
    for a missing value is exactly how the previous patient's number survives."""
    body = fn_body("openIntakeEditor", medic_html())
    assert "p.blood_glucose_mmol_l != null ? p.blood_glucose_mmol_l : ''" in body
    assert "p.blood_glucose_context || ''" in body


def test_the_editor_is_reopened_for_the_newly_selected_patient():
    """The pairing that makes the above true — the card re-opens the form with the NEW
    patient object, rather than leaving the old form on screen.

    S43 added a third argument (the unsaved draft); `p` is still the patient the form
    is re-seeded from, which is what this test is about."""
    html = medic_html()
    assert "if (intakeOpen) openIntakeEditor(p, age, draft);" in html


# --- 3. backend: one patient's reading must never appear on another ------------------


@pytest.fixture()
def two_patients():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool, future=True)
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, future=True)

    db = TestSession()
    clinic = Clinic(name="Demo Clinic")
    db.add(clinic)
    db.flush()
    medic = User(clinic_id=clinic.id, name="Medic Rahman", role="medic")
    a = Patient(clinic_id=clinic.id, external_ref="+8801700000001")
    b = Patient(clinic_id=clinic.id, external_ref="+8801700000002")
    db.add_all([medic, a, b])
    db.flush()
    va = Visit(clinic_id=clinic.id, patient_id=a.id, status="awaiting_review")
    vb = Visit(clinic_id=clinic.id, patient_id=b.id, status="awaiting_review")
    db.add_all([va, vb])
    db.commit()
    ids = {"medic": medic.id, "a": a.id, "b": b.id, "va": va.uuid, "vb": vb.uuid}
    db.close()

    def override_get_db():
        s = TestSession()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app), ids
    app.dependency_overrides.clear()


def test_a_reading_recorded_for_one_patient_does_not_appear_on_the_other(two_patients):
    c, ids = two_patients
    resp = c.patch(
        f"/api/patients/{ids['a']}/vitals",
        json={"blood_glucose_mmol_l": 6.5, "blood_glucose_context": "fasting",
              "editor_id": ids["medic"]},
    )
    assert resp.status_code == 200, resp.text

    a_detail = c.get(f"/api/visits/{ids['va']}").json()
    b_detail = c.get(f"/api/visits/{ids['vb']}").json()
    assert a_detail["patient"]["blood_glucose_mmol_l"] == 6.5
    assert a_detail["patient"]["blood_glucose_context"] == "fasting"
    assert b_detail["patient"]["blood_glucose_mmol_l"] is None, (
        "the other patient's case is carrying a reading nobody recorded for them"
    )
    assert b_detail["patient"]["blood_glucose_context"] is None


def test_correcting_one_patient_leaves_the_other_untouched(two_patients):
    c, ids = two_patients
    for pid, value in ((ids["a"], 6.5), (ids["b"], 9.1)):
        assert c.patch(
            f"/api/patients/{pid}/vitals",
            json={"blood_glucose_mmol_l": value, "blood_glucose_context": "random",
                  "editor_id": ids["medic"]},
        ).status_code == 200
    # correct A only
    assert c.patch(
        f"/api/patients/{ids['a']}/vitals",
        json={"blood_glucose_mmol_l": 5.2, "blood_glucose_context": "fasting",
              "editor_id": ids["medic"]},
    ).status_code == 200

    a = c.get(f"/api/visits/{ids['va']}").json()["patient"]
    b = c.get(f"/api/visits/{ids['vb']}").json()["patient"]
    assert (a["blood_glucose_mmol_l"], a["blood_glucose_context"]) == (5.2, "fasting")
    assert (b["blood_glucose_mmol_l"], b["blood_glucose_context"]) == (9.1, "random"), (
        "correcting one patient's reading changed another patient's record"
    )
