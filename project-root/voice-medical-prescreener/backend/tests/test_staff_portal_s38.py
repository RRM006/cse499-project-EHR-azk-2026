"""S38 — static-source assertions over the S38 staff-portal changes (ADR-0060/0061).

Same method as ``test_staff_portal_ui.py`` and the whole ``test_kiosk_*`` family: there
is still no JS test runner (the S28 decision — frontend tests are static-source
assertions only, no vitest/jsdom), so these read the SERVED files and assert properties
of the shipped source.

These are deliberately about PROPERTIES THAT WOULD REGRESS SILENTLY, not about wording:

  * **The auto-refresh must not eat a search.** The 15-second timer used to overwrite a
    phone-search result with the full queue. Nothing on screen would show the
    regression — the medic would just find the list "randomly resetting" again.
  * **The clock must not be the UTC clock.** ``toISOString().slice(0,10)`` looks
    completely correct and is wrong for six hours of every Dhaka day.
  * **The 12-hour rule.** A single ``hour: '2-digit'`` without ``hour12`` silently
    reverts a portal to a 24-hour clock under the en-GB locale.
  * **The workspace empty state.** Its whole bug was an early ``return`` that skipped
    the render; a future refactor could reintroduce exactly that.
"""

import re

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def _served(path: str) -> str:
    resp = client.get(path)
    assert resp.status_code == 200, f"{path} -> {resp.status_code}"
    return resp.text


def _match(source: str, start: int, opener: str, closer: str) -> int:
    """Index of the delimiter closing the one at ``start``."""
    depth, i = 0, start
    while True:
        if source[i] == opener:
            depth += 1
        elif source[i] == closer:
            depth -= 1
            if depth == 0:
                return i
        i += 1


def _fn_body(source: str, declaration: str) -> str:
    """The body of one function, by DELIMITER MATCHING rather than by guessing where it
    ends. Two earlier drafts of this helper were wrong in instructive ways, so both
    mistakes are named here:

      1. Slicing on ``"\\n}"`` or on a hand-written "next function" marker made the test
         fail when a blank line moved — that tests the file's layout, not its behaviour.
      2. Taking the first ``{`` after the name grabbed the PARAMETER LIST of a
         destructuring arrow function (``({ scope, searching }) => {``), so the "body"
         came back as ``{ scope, searching }`` and the assertion failed on correct code.

    So: skip the parameter list by matching its parentheses first, then match the braces
    of whatever follows.
    """
    start = source.index(declaration)
    paren = source.find("(", start)
    brace = source.find("{", start)
    if paren != -1 and paren < brace:
        brace = source.index("{", _match(source, paren, "(", ")"))
    return source[brace: _match(source, brace, "{", "}") + 1]


MEDIC = _served("/medic/")
DOCTOR = _served("/doctor/")
STAFF_JS = _served("/shared/staff.js")
SHARED_JS = _served("/shared/shared.js")
MOTION = _served("/shared/motion.css")
KIOSK = _served("/kiosk.html")


# ---------------------------------------------------------------------------
# A7 — the clock is real, local to Dhaka, and 12-hour
# ---------------------------------------------------------------------------


def test_both_portals_show_a_live_clock_driven_by_the_system_time():
    for name, html in (("medic", MEDIC), ("doctor", DOCTOR)):
        assert 'id="clock-time"' in html, name
        assert 'id="clock-date"' in html, name
        assert "dhakaNowParts()" in html, f"{name} does not read the real clock"
        assert "setInterval(tickClock, 1000)" in html, f"{name}'s clock does not tick"


def test_no_date_or_time_is_hard_coded_in_the_clock_markup():
    """A literal date in the markup is the exact 'fake/static time' this replaces."""
    for name, html in (("medic", MEDIC), ("doctor", DOCTOR)):
        clock = html[html.index('id="live-clock"'):]
        clock = clock[: clock.index("</div>", clock.index('id="clock-date"'))]
        assert not re.search(r"\b20\d\d\b", clock), f"{name} hard-codes a year"
        assert not re.search(r"\b\d{1,2}:\d{2}\b", clock), f"{name} hard-codes a time"


def test_every_dhaka_formatter_is_a_12_hour_clock():
    """en-GB defaults to 24-hour; only an explicit hour12 keeps AM/PM."""
    for fn in ("function dhakaTime", "function dhakaDateTime", "function dhakaNowParts"):
        assert "hour12: true" in _fn_body(SHARED_JS, fn), f"{fn} is not a 12-hour clock"


def test_today_is_read_from_dhaka_never_from_toisostring():
    """`toISOString()` is the UTC date — yesterday for the first six hours of every
    Dhaka day, which is how a prescription got dated the day before it was written."""
    assert "function dhakaTodayIso" in SHARED_JS
    today = _fn_body(SHARED_JS, "function dhakaTodayIso")
    assert "toISOString" not in today
    # The zone arrives via the shared DHAKA constant, which must BE Asia/Dhaka.
    assert "DHAKA" in today
    assert "const DHAKA = 'Asia/Dhaka'" in SHARED_JS


# ---------------------------------------------------------------------------
# A2 — the auto-refresh is visible, and cannot destroy the medic's own work
# ---------------------------------------------------------------------------


def test_the_timer_is_shared_and_the_portals_no_longer_own_one():
    """Two copies of a timer is how one portal gets a fix and the other does not."""
    assert "function startQueueAutoRefresh" in STAFF_JS
    for name, html in (("medic", MEDIC), ("doctor", DOCTOR)):
        assert "startQueueAutoRefresh()" in html, name
        assert "setInterval(loadQueue" not in html, f"{name} still owns a private timer"


def test_the_auto_refresh_holds_while_a_search_result_is_on_screen():
    """THE bug: a phone lookup was silently replaced by the full queue 15s later."""
    body = _fn_body(STAFF_JS, "function autoRefreshQueue")
    assert "queueIsSearchResult" in body, "the timer does not check for a search result"
    assert "document.hidden" in body, "the timer does not check tab visibility"
    # And it must RETURN before reloading, not merely notice.
    guard = body[: body.index("loadQueue()")]
    assert "return" in guard


def test_returning_to_the_tab_refreshes_immediately():
    body = _fn_body(STAFF_JS, "function startQueueAutoRefresh")
    assert "visibilitychange" in body
    assert "!document.hidden" in body


def test_the_timer_cannot_be_stacked_by_a_second_login():
    assert "if (queueTimer !== null) return" in _fn_body(
        STAFF_JS, "function startQueueAutoRefresh")


def test_a_background_refresh_does_not_re_run_the_entrance_animation():
    """Re-staggering the same rows every 15 seconds reads as an error, not freshness."""
    assert "queueAnimateNext" in STAFF_JS
    assert "queueAnimateNext = false" in _fn_body(STAFF_JS, "function autoRefreshQueue")
    # ...and the class is applied conditionally rather than unconditionally.
    assert "(queueAnimateNext ? ' fx-queue' : '')" in STAFF_JS


def test_both_portals_report_the_refresh_state_to_the_user():
    for name, html in (("medic", MEDIC), ("doctor", DOCTOR)):
        assert "function onQueueRefreshState" in html, name
        assert 'id="refresh-line"' in html, name
        # "paused" must be a state the user can SEE, not just an internal flag.
        assert "paused" in html, name


# ---------------------------------------------------------------------------
# A3 — the completeness indicator is a control, not a line
# ---------------------------------------------------------------------------


def test_the_meter_is_keyboard_reachable_and_labelled():
    body = _fn_body(STAFF_JS, "function buildCompletenessMeter")
    assert "meter.tabIndex = 0" in body
    assert "aria-label" in body, "the count must not be conveyed by the bar alone"
    assert "role" in body


def test_clicking_the_meter_does_not_open_the_case():
    """The meter asks a question ABOUT the row; the row's click chooses it. Without
    stopPropagation the two are the same gesture."""
    body = _fn_body(STAFF_JS, "function buildCompletenessMeter")
    assert "e.stopPropagation()" in body
    assert "e.preventDefault()" in body


def test_the_meter_distinguishes_verified_from_merely_filled():
    """'The model wrote something' and 'a person agreed' are different facts."""
    body = _fn_body(STAFF_JS, "function buildCompletenessMeter")
    assert "fields_verified" in body
    assert "verified" in body and "filled" in body and "empty" in body
    for cls in (".seg-tick.verified", ".seg-tick.filled", ".seg-tick.empty"):
        assert cls in MOTION, f"{cls} has no colour — the state would be invisible"


def test_the_meter_detail_names_the_missing_fields_from_the_server():
    """`fields_empty` comes from the same call that produced the count, so the panel
    cannot disagree with the bar above it."""
    assert "fields_empty" in STAFF_JS
    assert "STAFF_FIELD_LABELS" in _fn_body(STAFF_JS, "function fillMeterDetail")


def test_fields_empty_is_actually_served():
    schema = client.get("/openapi.json").json()
    item = schema["components"]["schemas"]["DashboardItemOut"]["properties"]
    assert "fields_empty" in item
    assert "fields_verified" in item


# ---------------------------------------------------------------------------
# A1 — "Triage" is explained
# ---------------------------------------------------------------------------


def test_the_medic_portal_explains_what_triage_means():
    assert 'id="triage-info"' in MEDIC
    assert "function renderTriageInfo" in MEDIC
    body = _fn_body(MEDIC, "function renderTriageInfo")
    # The definition itself, in both languages, and the actual ordering rule.
    assert "order they need to be seen" in body
    assert "ট্রায়াজ" in body
    assert "longest" in body


def test_the_explainer_is_collapsed_by_default_and_is_a_disclosure():
    """The brief: 'Do not create a large tutorial.' It must start closed."""
    header = MEDIC[MEDIC.index('id="triage-info-btn"'):]
    assert 'aria-expanded="false"' in header[:400]
    mount = MEDIC[MEDIC.index('id="triage-info"', MEDIC.index("triage-info-btn")):]
    assert "display:none" in mount[:120]


def test_the_doctor_portal_does_not_carry_the_triage_explainer():
    """Role separation (ADR-0058): triage ordering is the medic's job, not the doctor's."""
    assert "triage-info" not in DOCTOR


# ---------------------------------------------------------------------------
# B7 — the workspace says why it is empty
# ---------------------------------------------------------------------------


def test_the_workspace_empty_state_is_shared_and_both_portals_supply_copy():
    assert "function renderWorkspaceState" in STAFF_JS
    for name, html in (("medic", MEDIC), ("doctor", DOCTOR)):
        assert "emptyWorkspace:" in html, f"{name} supplies no empty-workspace copy"


def test_the_empty_branch_of_the_queue_still_renders_the_workspace():
    """THE bug: renderQueue returned early when the list was empty — which is exactly
    the case B7 reports — so the right-hand panel kept saying 'select a patient'."""
    body = _fn_body(STAFF_JS, "function renderQueue(items)")
    empty_branch = body[body.index("if (!items.length)"): body.index("items.forEach")]
    assert "renderWorkspaceState()" in empty_branch


def test_the_doctor_distinguishes_an_empty_queue_from_no_completed_cases():
    """'No one is assigned to me' and 'I have completed nothing' need different words."""
    body = _fn_body(DOCTOR, "emptyWorkspace:")
    assert "No assigned cases" in body
    assert "No completed consultations" in body
    assert "scope === 'recent'" in body


def test_an_open_case_is_never_snatched_away_by_a_queue_refresh():
    """A doctor reading a completed case must keep it when the working queue empties."""
    body = _fn_body(STAFF_JS, "function renderWorkspaceState")
    assert "if (currentCase) return;" in body
    assert "workspaceBusy" in body, "a portal's own full-width screen must win too"


def test_switching_scope_puts_the_previous_case_away():
    assert "currentCase = null" in _fn_body(DOCTOR, "function switchScope")


# ---------------------------------------------------------------------------
# A4 / A5 / A6 — Intake & Vitals is a working form
# ---------------------------------------------------------------------------


def test_the_intake_form_is_labelled_not_placeholder_only():
    """The old version was five bare inputs whose meaning lived only in a placeholder,
    which vanishes the moment anything is typed into it."""
    body = _fn_body(MEDIC, "function renderIntakeCard")
    for field_id in ("in-name", "in-age", "in-sex", "in-height", "in-weight", "in-bp"):
        assert field_id in body, f"{field_id} missing from the intake form"
    # Every control is built through the `field()` helper, and that helper is what
    # emits the visible <label>. Asserting both is what makes "labelled" true rather
    # than "a <label> exists somewhere in the file".
    assert "const field = (label, control, hint)" in body
    assert "<label" in body
    assert body.count("${field(") >= 6, "a control was added outside the labelled helper"


def test_the_units_are_stated_on_the_form_not_only_in_a_placeholder():
    """A BMI computed from pounds and inches is a plausible-looking wrong number."""
    body = _fn_body(MEDIC, "function renderIntakeCard")
    assert "centimetres (cm)" in body
    assert "kilograms (kg)" in body


def test_the_button_says_edit_once_something_has_been_recorded():
    """'Record' on a case that already has vitals made staff guess that it also meant
    'edit'. A4: existing values must be visibly editable."""
    body = _fn_body(MEDIC, "function renderIntakeCard")
    assert "anyRecorded" in body
    assert "'Edit'" in body and "'Record'" in body


def test_the_editor_prefills_with_what_is_already_stored():
    body = _fn_body(MEDIC, "function openIntakeEditor")
    for pair in ("p.display_name", "p.sex", "p.height_cm", "p.weight_kg", "p.bp"):
        assert pair in body, f"{pair} is not prefilled — the medic would retype it"


def test_the_editor_survives_a_language_toggle_mid_edit():
    """renderIntakeCard rebuilds the card's innerHTML; without this the form would
    close (and lose what was typed) whenever the medic switched language."""
    assert "let intakeOpen" in MEDIC
    body = _fn_body(MEDIC, "function renderIntakeCard")
    assert "if (intakeOpen) openIntakeEditor" in body


def test_bmi_is_derived_from_the_server_not_recomputed_in_the_portal():
    """The cut-offs are published clinical constants; a second copy in JS is how the
    portal and services/clinical_reference quietly start disagreeing."""
    body = _fn_body(STAFF_JS, "async function showBmi")
    assert "/api/reference/bmi" in body
    # No local arithmetic, and no local ladder.
    assert "/ (metres" not in STAFF_JS
    assert "18.5" not in STAFF_JS and "27.5" not in STAFF_JS


def test_bmi_updates_live_as_height_and_weight_are_typed():
    body = _fn_body(MEDIC, "function openIntakeEditor")
    assert "'in-height', 'in-weight'" in body
    assert "oninput = liveBmi" in body
    assert "setTimeout" in _fn_body(MEDIC, "function liveBmi"), "unthrottled per-keystroke fetch"


def test_an_unusable_bmi_says_so_instead_of_going_blank():
    """The server returns null rather than a misleading number; a silently blank
    readout would look like a broken page instead of a rejected input."""
    body = _fn_body(STAFF_JS, "async function showBmi")
    assert "res.bmi === null" in body
    assert "BMI not shown" in body


def test_bmi_reports_both_ladders():
    """A BMI of 24 is 'normal' internationally and 'increased risk' on the Asian action
    points — for a clinic in Bangladesh, showing only the first understates risk."""
    body = _fn_body(STAFF_JS, "async function showBmi")
    assert "res.who" in body and "res.asia" in body
    assert "Asian" in body


def test_no_bmi_value_is_ever_sent_to_a_write_endpoint():
    """ADR-0060: derived, never stored. The property is about the PAYLOAD, so it is
    asserted on the payload construction — an earlier draft grepped for the substring
    'bmi' and tripped over the word in a comment, which is a test of prose, not code."""
    for name, html in (("medic", MEDIC), ("doctor", DOCTOR)):
        save = _fn_body(html, "async function saveIntake") if "saveIntake" in html \
            else _fn_body(html, "async function saveVitals")
        code = re.sub(r"//.*", "", save)          # strip line comments
        assert "body.bmi" not in code, f"{name} sends a BMI to the server"
        assert re.search(r"\bbmi\s*:", code) is None, f"{name} puts a bmi key in a payload"
    # And the schema has no field to receive one even if a client tried.
    schema = client.get("/openapi.json").json()["components"]["schemas"]
    assert not [k for k in schema["VitalsEditRequest"]["properties"] if "bmi" in k.lower()]


def test_both_portals_can_record_a_height():
    """Both roles legitimately touch the same patients row (ADR-0058)."""
    assert "in-height" in MEDIC
    assert "vitals-height" in DOCTOR
    assert "height_cm" in MEDIC and "height_cm" in DOCTOR


# ⚠ S39 (ADR-0064) moved the glucose panel from the medic portal into the SHARED
# staff.js so the doctor — who is the one interpreting the reading S39 added — sees
# the same chart rather than a second copy of published thresholds. These three tests
# are unchanged in what they assert; only the file they read moved. See
# test_staff_portal_s39.test_the_glucose_chart_lives_in_exactly_one_place.


def test_the_glucose_panel_refuses_to_be_a_single_number():
    """A6: the human asked for 'a diabetic limit'. Shipping one would be the most
    dangerous thing in this session — the panel shows the chart and says why."""
    body = _fn_body(STAFF_JS, "function renderGlucosePanel")
    assert 'There is no single "diabetic limit"' in body
    assert "requires_context_en" in body, "the bands are shown without their preconditions"
    assert "ctx.source" in body, "no source is quoted for a clinical threshold"
    assert "disclaimer" in body


def test_the_glucose_panel_never_reads_a_patient_value():
    """Rule #2: it is a wall chart, not an interpreter. Nothing about the open case
    may reach it."""
    body = _fn_body(STAFF_JS, "function renderGlucosePanel")
    for forbidden in ("currentCase", "patient", "weight_kg", "profile"):
        assert forbidden not in body, f"the glucose chart reads {forbidden}"


def test_glucose_bands_carry_both_unit_systems():
    """Both mmol/L and mg/dL are in daily use in Bangladeshi labs; converting at the
    bedside invites exactly the error this is meant to prevent."""
    body = _fn_body(STAFF_JS, "function bandRange")
    assert "mmol/L" in body and "mg/dL" in body


# ---------------------------------------------------------------------------
# containment — the kiosk pays for none of this
# ---------------------------------------------------------------------------


def test_the_kiosk_loads_no_staff_chrome():
    assert "/shared/motion.css" not in KIOSK
    assert "/shared/staff.js" not in KIOSK


def test_the_new_motion_rules_stay_behind_the_reduced_motion_guard():
    """ADR-0059's outranking rule still holds after S38 added several styles."""
    stripped = re.sub(r"/\*.*?\*/", lambda m: " " * len(m.group(0)), MOTION, flags=re.S)
    start = stripped.index("{", stripped.index("@media (prefers-reduced-motion: no-preference)"))
    depth, i = 0, start
    while True:
        if stripped[i] == "{":
            depth += 1
        elif stripped[i] == "}":
            depth -= 1
            if depth == 0:
                break
        i += 1
    stray = [
        stripped[:m.start()].count("\n") + 1
        for m in re.finditer(r"animation\s*:|@keyframes", stripped)
        if not (start < m.start() < i)
    ]
    assert not stray, f"motion declared outside the guard, line(s) {stray}"
