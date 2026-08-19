"""S39 — static-source assertions over the S39 portal changes (ADR-0064).

Same method as ``test_staff_portal_s38.py`` and the whole ``test_kiosk_*`` family:
there is still no JS test runner (the S28 decision — frontend tests are static-source
assertions only, no vitest/jsdom), so these read the SERVED files and assert
properties of the shipped source.

Deliberately about PROPERTIES THAT WOULD REGRESS SILENTLY, not wording:

  * **The name must never be rendered without its origin.** The whole reported bug was
    a name presented as this visit's when it came from an earlier one. Nothing on
    screen would show a regression — the name would simply look authoritative again.
  * **The duplicate editors must stay gone.** They wrote the same `patients` row
    through the same PATCH as the intake form but covered fewer fields; re-adding one
    would recreate two screens that disagree about one patient.
  * **Reading and context must be sent together.** Splitting them looks harmless and
    puts an uninterpretable number in a medical record.
  * **The mg/dL constant must match the server's.** A drift prints a conversion that
    disagrees with the chart directly beneath it.
  * **One glucose chart, not two.** The thresholds are published clinical constants;
    a second copy in the doctor portal is how the two quietly diverge.
"""

import re

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def _served(path: str) -> str:
    resp = client.get(path)
    assert resp.status_code == 200, f"{path} -> {resp.status_code}"
    return resp.text


# --- 1. patient-name provenance -----------------------------------------------------


def test_both_portals_render_the_name_origin_beside_the_name():
    for path, mount in (("/medic/", "intake-name-origin"), ("/doctor/", "pd-name-origin")):
        source = _served(path)
        assert f'id="{mount}"' in source, f"{path} has no mount for the name origin"
        assert f"renderNameProvenance('{mount}'" in source, (
            f"{path} renders a patient name without asking where it came from"
        )


def test_the_provenance_renderer_never_guesses_an_earlier_visit():
    """`from_this_visit` is null when the origin visit is unknown. Only an explicit
    False may print the earlier-visit warning — `!prov.from_this_visit` would fire on
    null too and assert something the server did not say."""
    staff = _served("/shared/staff.js")
    assert "prov.from_this_visit === false" in staff
    assert "!prov.from_this_visit" not in staff


def test_an_unknown_origin_is_shown_as_unknown():
    staff = _served("/shared/staff.js")
    body = staff[staff.index("function renderNameProvenance"):]
    body = body[:body.index("\n}")]
    assert "not recorded" in body, "an unrecorded origin must say so, not stay silent"


def test_there_is_exactly_one_not_provided_label_and_the_portals_use_it():
    shared = _served("/shared/shared.js")
    assert "function patientNameLabel(" in shared
    for path in ("/medic/", "/doctor/"):
        source = _served(path)
        assert "patientNameLabel(" in source, f"{path} still renders a bare name"
    # The old ad-hoc placeholders are gone from the identity slots.
    assert "'(no name)'" not in _served("/medic/")


# --- 2. blood glucose ---------------------------------------------------------------


def test_the_intake_form_has_a_reading_and_a_context_control():
    """The ids are produced by the form's own `num()`/field builders, so the source
    carries the id as an argument rather than as literal markup."""
    medic = _served("/medic/")
    assert "num('in-glucose'" in medic
    assert 'id="in-glucose-context"' in medic
    # S43 moved the PREFILL of these two controls into one loop over INTAKE_FIELD_IDS,
    # so the literal getElementById lines are gone. What this test is really about —
    # that the form reads BOTH controls — is asserted on the save path, which is where
    # it actually matters and is a stronger claim than the prefill was.
    assert "'in-glucose'" in medic.split("const INTAKE_FIELD_IDS = [")[1].split("];")[0]
    assert "'in-glucose-context'" in medic.split("const INTAKE_FIELD_IDS = [")[1].split("];")[0]
    assert "val('in-glucose')" in medic
    assert "val('in-glucose-context')" in medic
    # The dropdown is built from the shared map, not from a second hard-coded list.
    assert "Object.keys(GLUCOSE_CONTEXTS)" in medic


def test_the_form_refuses_to_send_a_reading_without_its_context():
    medic = _served("/medic/")
    body = medic[medic.index("async function saveIntake"):]
    body = body[:body.index("\n    }")]
    assert "blood_glucose_mmol_l" in body and "blood_glucose_context" in body
    assert "if (!sugarContext)" in body, (
        "the form can send a reading with no measurement context"
    )


def test_the_frontend_mg_dl_constant_matches_the_server():
    from backend.app.services.clinical_reference import MMOL_TO_MGDL

    staff = _served("/shared/staff.js")
    match = re.search(r"const MMOL_TO_MGDL\s*=\s*([0-9.]+)", staff)
    assert match, "the conversion constant is gone from staff.js"
    assert float(match.group(1)) == MMOL_TO_MGDL, (
        "the portal and services/clinical_reference disagree about mmol/L -> mg/dL"
    )


def test_the_reading_is_displayed_with_its_context_and_no_verdict():
    staff = _served("/shared/staff.js")
    body = staff[staff.index("function glucoseText("):]
    body = body[:body.index("\n}")]
    assert "glucoseContextLabel(context)" in body
    for verdict in ("diabet", "impaired", "normal", "high"):
        assert verdict not in body.lower(), (
            f"glucoseText classifies the reading as '{verdict}' (rule #2)"
        )


def test_the_doctor_sees_the_reading_read_only():
    doctor = _served("/doctor/")
    assert "'pd-sugar'" in doctor       # the row id, passed to the row() builder
    # The doctor's vitals editor covers height/weight/BP; blood sugar is intake data
    # the medic owns, so there must be no second editor for it here.
    assert 'id="vitals-glucose"' not in doctor
    assert "blood_glucose_mmol_l:" not in doctor, (
        "the doctor portal writes a glucose value — intake is the medic's to own"
    )


# --- 3. one glucose chart, shared ----------------------------------------------------


def test_the_glucose_chart_lives_in_exactly_one_place():
    staff = _served("/shared/staff.js")
    assert "function renderGlucosePanel(" in staff
    assert "function bandRange(" in staff
    medic = _served("/medic/")
    assert "function renderGlucosePanel(" not in medic, "a second copy of the chart"
    assert "function bandRange(" not in medic


def test_both_portals_mount_the_same_chart():
    medic, doctor = _served("/medic/"), _served("/doctor/")
    assert "toggleGlucosePanel('glucose-panel')" in medic
    assert "toggleGlucosePanel('pd-glucose-panel')" in doctor
    assert 'id="glucose-panel"' in medic
    assert 'id="pd-glucose-panel"' in doctor


def test_the_chart_still_takes_no_patient_value():
    """ADR-0060's rule, now that a reading exists on the same screen: the panel is a
    printed chart, and nothing feeds a measurement into it."""
    staff = _served("/shared/staff.js")
    body = staff[staff.index("function renderGlucosePanel("):]
    body = body[:body.index("\n  panel.appendChild(disc);")]
    for leak in ("blood_glucose", "currentCase", "patient."):
        assert leak not in body, f"the reference chart reads a patient value ({leak})"


# --- 4. the duplicate editors stay gone ---------------------------------------------


def test_the_post_referral_screen_has_no_second_editor():
    medic = _served("/medic/")
    for dead in ("identity-edit-btn", "weight-edit-btn", "ident-name", "ident-age",
                 "ident-gender", "weight-input", "identity-editor", "weight-editor"):
        assert f'id="{dead}"' not in medic, (
            f"'{dead}' is back — two forms writing one patients row through one PATCH"
        )


def test_there_is_one_intake_save_path():
    medic = _served("/medic/")
    assert medic.count("async function saveIntake(") == 1
    assert "function saveIdentity(" not in medic
    assert "function saveWeight(" not in medic
    # Exactly one CALL SITE for the vitals PATCH (the other occurrence of the path is
    # in a comment, which is why this counts the api() call and not the string).
    assert medic.count("await api('PATCH', `/api/patients/${p.id}/vitals`") == 1, (
        "more than one place writes patient vitals"
    )


def test_the_post_referral_screen_says_where_editing_happens():
    """A read-only screen that used to be editable must say so, or it reads as broken."""
    medic = _served("/medic/")
    assert "Recorded before the referral" in medic


# --- 5. the EHR exports ---------------------------------------------------------------


def test_the_doctor_offers_both_ehr_formats_through_one_function():
    doctor = _served("/doctor/")
    assert "downloadEhrExport(this, 'ehr_bundle')" in doctor
    assert "downloadEhrExport(this, 'ehr_pdf')" in doctor
    assert doctor.count("async function downloadEhrExport(") == 1, (
        "two download implementations is how the two exports start behaving differently"
    )
    assert "downloadEhrBundle" not in doctor, "a stale call to the removed name"


def test_the_accept_path_still_writes_the_fhir_record():
    doctor = _served("/doctor/")
    assert "downloadEhrExport(document.getElementById('btn-ehr'), 'ehr_bundle', { silent: true })" in doctor
